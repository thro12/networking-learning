#!/usr/bin/env python3
"""Offline tests for gns3_static_default_builder.py[.txt].
All GNS3 and IOS/VPCS responses are simulated test fixtures, NOT real lab output.
Run: python3 test_static_builder.py [path-to-builder]
"""
import contextlib
import importlib.machinery
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SOURCE = Path(sys.argv.pop(1)) if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else Path(__file__).with_name('gns3_static_default_builder.py.txt')
lab = importlib.machinery.SourceFileLoader('builder_under_test', str(SOURCE)).load_module()

def ios_config(text):
    """Render intended fixture config with IOS-like section indentation."""
    result = []
    sub = False
    for line in text.splitlines():
        if line == 'exit':
            result.append('!'); sub = False
        elif line.startswith(('interface ', 'router ', 'line ', 'route-map ', 'ip dhcp pool ')):
            result.append(line); sub = True
        else:
            result.append((' ' if sub else '') + line)
    return '\n'.join(result)

class Fixture:
    def __init__(self, **faults):
        self.faults = faults
        self.nodes = {}
        self.calls = []
        self.commands = []
        self.stored = {}
        self.down = False
        self.client_id = None
        self.reservation = False
        self.dhcp_requests = 0
        self.saved = set()
        fixture = self
        class API:
            project = None
            def call(self, method, path, body=None, raw=False):
                fixture.calls.append((method, path, body))
                if method != 'GET':
                    assert path == '/v2/projects' or (self.project and path.startswith('/v2/projects/' + self.project + '/')), 'write escaped new project'
                if path == '/v2/version': return {'version': '2.2.61'}
                if path == '/v2/templates': return [{'template_id': 'r', 'template_type': 'dynamips', 'name': 'c7200'}, {'template_id': 's', 'template_type': 'ethernet_switch'}, {'template_id': 'p', 'template_type': 'vpcs'}]
                if path == '/v2/computes': return [{'compute_id': 'local', 'connected': True}]
                if path == '/v2/projects': return {'project_id': body['project_id']}
                if '/templates/' in path:
                    name = body['name']
                    names = list(lab.ADDRESS[name]) if name in lab.ROUTERS else ['Ethernet0', 'Ethernet1'] if name == 'Switch1' else ['Ethernet0']
                    node = {'name': name, 'node_id': name, 'status': 'stopped', 'console': 5000, 'properties': {'dynamips_id': len(fixture.nodes) + 1}, 'ports': [{'name': n, 'adapter_number': i, 'port_number': 0} for i, n in enumerate(names)]}
                    fixture.nodes[name] = node
                    return node
                if '/files/' in path:
                    if method == 'POST': fixture.stored[path] = body.decode(); return ''
                    return fixture.stored[path] + ('CORRUPTED' if fixture.faults.get('bad_startup_upload') else '')
                if path.endswith('/start'):
                    fixture.nodes[path.split('/nodes/')[1].split('/')[0]]['status'] = 'started'; return {}
                if '/nodes/' in path: return fixture.nodes[path.rsplit('/', 1)[-1]]
                if path.endswith('/nodes'): return list(fixture.nodes.values())
                return {}
        class Console:
            def __init__(self, host, port, logfile, name): self.name = name
            def sync(self): pass
            def close(self): pass
            def command(self, text, timeout=30, strict=True):
                fixture.commands.append((self.name, text))
                if text == 'shutdown': fixture.down = True
                if text == 'no shutdown' and self.name == 'R1': fixture.down = False
                if text.startswith('client-identifier '): fixture.client_id = text.split()[1]
                if text == 'ip dhcp pool PC1-RESERVATION': fixture.reservation = True
                if text in ('show running-config', 'show startup-config'):
                    conf = ios_config(lab.config(self.name))
                    if self.name == 'R1' and fixture.reservation:
                        conf += '\nip dhcp pool PC1-RESERVATION\n host 192.168.1.1 255.255.255.0\n client-identifier ' + str(fixture.client_id) + '\n!'
                    if text == 'show startup-config' and fixture.faults.get('missing_saved_route') and self.name in fixture.saved:
                        conf = '\n'.join(line for line in conf.splitlines() if not line.startswith('ip route '))
                    return conf
                if text == 'show ip':
                    mac = '' if fixture.faults.get('missing_mac') else '\nMAC : 00:50:79:66:68:00'
                    ip = '192.168.1.2/24' if fixture.faults.get('wrong_lease') else '192.168.1.1/24'
                    return 'IP/MASK : ' + ip + '\nGATEWAY : 192.168.1.100' + mac
                if text == 'ip dhcp':
                    fixture.dhcp_requests += 1
                    assert fixture.reservation and fixture.client_id == '0100.5079.6668.00', 'DHCP requested before matching reservation'
                if text.startswith('show ip route'):
                    return 'Routing entry for 0.0.0.0/0\nKnown via "static", distance %d, metric 0\n * %s' % (20 if fixture.down else 10, '192.168.15.5' if fixture.down else '192.168.14.4')
                if text.startswith('show ip cef'):
                    if fixture.faults.get('bad_cef'): return '% Network not in table'
                    return '0.0.0.0/0, version 25\n nexthop %s %s' % (('192.168.15.5', 'GigabitEthernet3/0') if fixture.down else ('192.168.14.4', 'GigabitEthernet2/0'))
                if text.startswith('ping '):
                    if fixture.faults.get('fail_backup') and fixture.down and '8.8.8.8' in text: return '100% packet loss'
                    return '\n'.join('84 bytes from %s icmp_seq=%d' % (text.split()[1], i) for i in range(1, 6))
                if text == 'show ip nat translations':
                    return 'icmp %s:1 192.168.1.1:1 8.8.8.8:1 8.8.8.8:1' % ('192.168.15.1' if fixture.down else '192.168.14.1')
                if text == 'write memory':
                    fixture.saved.add(self.name)
                    return 'save failed' if fixture.faults.get('bad_save') else '[OK]'
                return self.name + '#'
        self.API = API
        self.Console = Console

class WorkflowTests(unittest.TestCase):
    def run_fixture(self, **faults):
        fixture = Fixture(**faults)
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(lab.Path, 'home', return_value=Path(temp)), patch.object(lab, 'API', fixture.API), patch.object(lab, 'Console', fixture.Console), patch.object(lab.time, 'sleep'), patch.object(lab.sys, 'argv', ['builder']), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = lab.main()
            folder = next((Path(temp) / 'GNS3-AutoLab-Reports').iterdir())
            checks = json.loads((folder / 'checks.json').read_text())
            files = {p.name: p.read_text() for p in folder.iterdir() if p.is_file()}
        return code, checks, fixture, files

    def test_full_mocked_workflow(self):
        code, checks, f, files = self.run_fixture()
        self.assertEqual(code, 0)
        self.assertEqual(len(checks), 30)
        self.assertTrue(all(c['status'] == 'PASS' for c in checks))
        self.assertEqual(sum(m == 'POST' and p == '/v2/projects' for m, p, b in f.calls), 1)
        self.assertEqual(sum(m == 'POST' and '/templates/' in p for m, p, b in f.calls), 6)
        self.assertEqual(sum(m == 'POST' and p.endswith('/links') for m, p, b in f.calls), 6)
        self.assertEqual(len(f.stored), 4)
        self.assertFalse(any(m in ('PUT', 'DELETE') for m, p, b in f.calls))
        self.assertEqual(f.client_id, '0100.5079.6668.00')
        self.assertEqual(f.dhcp_requests, 1)
        self.assertEqual(f.saved, set(lab.ROUTERS))
        self.assertFalse(f.down)
        self.assertIn('RESULTS.txt', files)
        self.assertNotIn('ERROR.txt', files)

    def test_missing_mac_stops_before_dhcp_or_failover(self):
        code, checks, f, files = self.run_fixture(missing_mac=True)
        self.assertEqual(code, 1)
        self.assertEqual(f.dhcp_requests, 0)
        self.assertFalse(f.saved)
        self.assertFalse(any(c == 'shutdown' for n, c in f.commands))
        self.assertIn('Cannot establish', files['ERROR.txt'])

    def test_wrong_lease_not_success(self):
        code, checks, f, files = self.run_fixture(wrong_lease=True)
        self.assertEqual(code, 1)
        self.assertEqual(f.dhcp_requests, 3)
        self.assertFalse(f.saved)
        self.assertTrue(any(c['status'] == 'FAIL' for c in checks))

    def test_bad_cef_prevents_failover_and_save(self):
        code, checks, f, files = self.run_fixture(bad_cef=True)
        self.assertEqual(code, 1)
        self.assertFalse(any(c == 'shutdown' for n, c in f.commands))
        self.assertFalse(f.saved)

    def test_backup_failure_restores_primary_without_save(self):
        code, checks, f, files = self.run_fixture(fail_backup=True)
        self.assertEqual(code, 1)
        self.assertFalse(f.down)
        self.assertFalse(f.saved)
        self.assertTrue(any(c['status'] == 'FAIL' for c in checks))
        self.assertTrue(any(c == 'shutdown' for n, c in f.commands))
        self.assertTrue(any(c == 'no shutdown' for n, c in f.commands))

    def test_failed_save_cannot_report_zero_failures(self):
        code, checks, f, files = self.run_fixture(bad_save=True)
        self.assertEqual(code, 2)
        self.assertEqual(sum(c['status'] == 'FAIL' and 'save acknowledged' in c['check'] for c in checks), 4)
        self.assertIn('Do not treat this run as fully verified', files['RESULTS.txt'])
        self.assertNotIn('Final state:', files['RESULTS.txt'])

    def test_missing_saved_routes_cannot_pass_readback(self):
        code, checks, f, files = self.run_fixture(missing_saved_route=True)
        self.assertEqual(code, 2)
        self.assertEqual(sum(c['status'] == 'FAIL' and 'startup contains' in c['check'] for c in checks), 4)

    def test_corrupt_upload_never_boots(self):
        code, checks, f, files = self.run_fixture(bad_startup_upload=True)
        self.assertEqual(code, 1)
        self.assertFalse(any(p.endswith('/start') for m, p, b in f.calls))
        self.assertIn('readback did not match', files['ERROR.txt'])

class ParserAndSafetyTests(unittest.TestCase):
    def test_cef_parser(self):
        for text in ('% Network not in table', '8.8.8.8/32\n192.168.14.4 GigabitEthernet2/0', '0.0.0.0/0\n192.168.15.5 GigabitEthernet3/0', '0.0.0.0/0\n192.168.14.4 GigabitEthernet2/0 unresolved'):
            self.assertFalse(lab.cef_default_ok(text, '192.168.14.4', 'GigabitEthernet2/0'))
        self.assertTrue(lab.cef_default_ok('0.0.0.0/0, version 3\n nexthop 192.168.14.4 GigabitEthernet2/0', '192.168.14.4', 'GigabitEthernet2/0'))

    def test_loss_is_not_success(self):
        self.assertFalse(lab.ping_ok('100% packet loss'))
        self.assertFalse(lab.gateway_ping_ok('100% packet loss'))
        self.assertFalse(lab.ping_ok('84 bytes from 8.8.8.8 icmp_seq=1'))

    def test_unknown_routes_and_pools_refused(self):
        for text in ('ip route 10.0.0.0 255.0.0.0 192.168.14.4', 'ip dhcp pool custom'):
            with self.assertRaises(lab.LabError): lab.migration_lines('R1', text)

    def test_write_scope_guard(self):
        api = lab.API(); api.project = 'new-project'
        for path in ('/v2/templates/a', '/v2/projects/another-project/nodes/a', '/v2/computes/local'):
            with self.assertRaises(lab.LabError): api.call('POST', path, {})

    def test_static_configs_preserve_diagram_addresses(self):
        for name, interfaces in lab.ADDRESS.items():
            conf = lab.config(name)
            self.assertNotIn('router ospf', conf)
            for interface, address in interfaces.items():
                self.assertIn('interface ' + interface + '\n', conf)
                self.assertIn('ip address ' + address + ' 255.255.255.0', conf)

class SocketTests(unittest.TestCase):
    def pair(self):
        a, b = socket.socketpair(); a.settimeout(.05)
        c = lab.Console.__new__(lab.Console)
        c.s = a; c.state = 'data'; c.verb = None; c.name = 'R1'; c.logfile = io.StringIO()
        self.addCleanup(a.close); self.addCleanup(b.close)
        return c, b

    def test_command_uses_single_cr(self):
        c, b = self.pair(); c.send('show ip route')
        self.assertEqual(b.recv(100), b'show ip route\r')

    def test_prompt_requires_own_command_echo(self):
        c, b = self.pair(); b.sendall(b'R1#')
        with self.assertRaises(lab.LabError): c.read_prompt(.1, expected='write memory')

    def test_actual_prompt_forms(self):
        for prompt in (b'R1#', b'R1(config)#', b'PC1> ', b'PC1[1]>'):
            c, b = self.pair(); b.sendall(b'cmd\r\n' + prompt)
            self.assertIn('cmd', c.read_prompt(1, expected='cmd'))

    def test_password_prompt_stops(self):
        c, b = self.pair(); b.sendall(b'Password: ')
        with self.assertRaises(lab.LabError): c.read_prompt(1)

    def test_eof_stops_without_command_retry(self):
        c, b = self.pair(); b.close()
        with self.assertRaises(lab.LabError): c.read_prompt(1)

    def test_telnet_split_negotiation(self):
        c, b = self.pair()
        self.assertEqual(c.decode(b'hello\xff'), 'hello')
        self.assertEqual(c.decode(bytes((251, 1))), '')
        self.assertEqual(b.recv(3), bytes((255, 253, 1)))
        self.assertEqual(c.decode(bytes((255, 253, 24))), '')
        self.assertEqual(b.recv(3), bytes((255, 252, 24)))
        self.assertEqual(c.decode(b'world'), 'world')

    def test_exact_save_confirmation_only_for_write_memory(self):
        c, b = self.pair()
        confirmation = b'write memory\r\nWarning: Attempting to overwrite an NVRAM configuration previously written\r\nby a different version of the system image.\r\nOverwrite the previous NVRAM configuration?[confirm]'
        b.sendall(confirmation)
        received = []
        def peer():
            b.settimeout(2)
            received.append(b.recv(10))
            b.sendall(b'\r\n[OK]\r\nR1#')
        thread = threading.Thread(target=peer); thread.start()
        output = c.read_prompt(2, expected='write memory', allow_save_confirm=True)
        thread.join(3)
        self.assertEqual(received, [b'\r'])
        self.assertIn('[OK]', output)

if __name__ == '__main__':
    unittest.main(verbosity=2)
