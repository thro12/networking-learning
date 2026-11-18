#!/usr/bin/env python3
"""Create a new complete static/default routing GNS3 lab from scratch.
Python standard library only. Run with GNS3 open. No manual device placement.
Creates no Cloud/NAT bridge nodes. Creates a separate new project without changing any existing project or shared template.
"""
import argparse
import base64
import configparser
from datetime import datetime
import ipaddress
import json
from pathlib import Path
import re
import socket
import sys
import subprocess
import time
import urllib.error
import urllib.request
import uuid

BASE = "http://127.0.0.1:3080"
ROUTERS = ("R1", "R3", "R4", "R5")
POSITIONS = {"R3": (0, -300), "R4": (-300, -100), "R5": (300, -100), "R1": (0, 180), "Switch1": (0, 380), "PC1": (-100, 530)}
ADDRESS = {
    "R1": {"GigabitEthernet1/0": "192.168.1.100", "GigabitEthernet2/0": "192.168.14.1", "GigabitEthernet3/0": "192.168.15.1"},
    "R3": {"GigabitEthernet1/0": "192.168.34.3", "GigabitEthernet2/0": "192.168.35.3"},
    "R4": {"GigabitEthernet1/0": "192.168.34.4", "GigabitEthernet2/0": "192.168.14.4"},
    "R5": {"GigabitEthernet1/0": "192.168.35.5", "GigabitEthernet2/0": "192.168.15.5"},
}
LINKS = [("R1", "GigabitEthernet2/0", "R4", "GigabitEthernet2/0"), ("R1", "GigabitEthernet3/0", "R5", "GigabitEthernet2/0"), ("R4", "GigabitEthernet1/0", "R3", "GigabitEthernet1/0"), ("R5", "GigabitEthernet1/0", "R3", "GigabitEthernet2/0"), ("R1", "GigabitEthernet1/0", "Switch1", "Ethernet1"), ("Switch1", "Ethernet0", "PC1", "Ethernet0")]


class LabError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class API:
    def __init__(self):
        self.auth = None
        self.project = None
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def saved_auth(self):
        path = Path.home() / ".config/GNS3/2.2/gns3_server.conf"
        c = configparser.ConfigParser(interpolation=None)
        try:
            if path.is_symlink() or path.stat().st_size > 1_000_000:
                raise LabError("Local settings file needs review. No credentials displayed.")
            with path.open(encoding="utf-8") as f:
                c.read_file(f)
            s = c["Server"]
            if s.get("host", "127.0.0.1").strip() not in ("127.0.0.1", "localhost", "0.0.0.0") or int(s.get("port", "3080")) != 3080 or s.get("protocol", "http").strip() != "http" or s.getboolean("ssl", fallback=False):
                raise LabError("Saved server endpoint does not match local port 3080. No credentials used.")
            u, p = s.get("user", ""), s.get("password", "")
            if not u or not p or ":" in u:
                raise LabError("Local login unavailable. Do not send passwords or settings files.")
            self.auth = "Basic " + base64.b64encode((u + ":" + p).encode()).decode()
        except (OSError, ValueError, KeyError, configparser.Error):
            raise LabError("Cannot safely read local login settings. No credentials displayed.") from None

    def call(self, method, path, body=None, raw=False):
        # All mutations are constrained to the one newly created project.
        if method != "GET" and path != "/v2/projects":
            if not self.project or not path.startswith("/v2/projects/" + self.project + "/"):
                raise LabError("Refusing to modify anything outside the new lab project.")
        headers = {"Accept": "application/json"}
        if self.auth:
            headers["Authorization"] = self.auth
        data = body if isinstance(body, bytes) else None if body is None else json.dumps(body).encode()
        if data is not None:
            headers["Content-Type"] = "application/octet-stream" if isinstance(body, bytes) else "application/json"
        raw_response = raw
        req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=40) as response:
                raw = response.read(8_000_001)
                if len(raw) > 8_000_000:
                    raise LabError("Unexpectedly large server response.")
                return raw.decode("utf-8") if raw_response else json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            if method == "GET" and path == "/v2/version" and exc.code == 401 and not self.auth and exc.headers.get("WWW-Authenticate", "").lower().startswith("basic "):
                self.saved_auth()
                return self.call(method, path, body, raw)
            raise LabError("GNS3 %s %s returned HTTP %s. No automatic retry of writes; inspect the new lab before retrying." % (method, path, exc.code)) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise LabError("GNS3 connection failed during %s %s. A write might have landed; this run will not retry it." % (method, path)) from None
        except (ValueError, UnicodeError):
            raise LabError("Unexpected non-JSON reply from GNS3.") from None


def config(name):
    lines = ["hostname " + name, "no ip domain-lookup", "ip routing"]
    for interface, address in ADDRESS[name].items():
        lines += ["interface " + interface, "description Lab link " + address,
                  "ip address " + address + " 255.255.255.0", "no shutdown"]
        if name == "R1":
            lines += ["ip nat inside" if interface == "GigabitEthernet1/0" else "ip nat outside"]
        lines += ["exit"]
    if name == "R1":
        lines += ["ip dhcp excluded-address 192.168.1.100 192.168.1.102",
                  "ip dhcp pool SBI-Bank", "network 192.168.1.0 255.255.255.0",
                  "default-router 192.168.1.100", "dns-server 192.168.1.101 192.168.1.102", "exit",
                  "access-list 10 permit 192.168.1.0 0.0.0.255",
                  "route-map NAT-AIRTEL permit 10", "match ip address 10",
                  "match interface GigabitEthernet2/0", "exit",
                  "route-map NAT-TATA permit 10", "match ip address 10",
                  "match interface GigabitEthernet3/0", "exit",
                  "ip nat inside source route-map NAT-AIRTEL interface GigabitEthernet2/0 overload",
                  "ip nat inside source route-map NAT-TATA interface GigabitEthernet3/0 overload",
                  "ip route 0.0.0.0 0.0.0.0 GigabitEthernet2/0 192.168.14.4 10",
                  "ip route 0.0.0.0 0.0.0.0 GigabitEthernet3/0 192.168.15.5 20"]
    elif name == "R3":
        lines += ["interface Loopback0", "description SIMULATED target - NOT real Internet",
                  "ip address 8.8.8.8 255.255.255.255", "no shutdown", "exit",
                  "ip route 192.168.1.0 255.255.255.0 GigabitEthernet1/0 192.168.34.4 10",
                  "ip route 192.168.1.0 255.255.255.0 GigabitEthernet2/0 192.168.35.5 20",
                  "ip route 192.168.14.0 255.255.255.0 GigabitEthernet1/0 192.168.34.4",
                  "ip route 192.168.15.0 255.255.255.0 GigabitEthernet2/0 192.168.35.5"]
    elif name == "R4":
        lines += ["ip route 8.8.8.8 255.255.255.255 GigabitEthernet1/0 192.168.34.3",
                  "ip route 192.168.1.0 255.255.255.0 GigabitEthernet2/0 192.168.14.1"]
    elif name == "R5":
        lines += ["ip route 8.8.8.8 255.255.255.255 GigabitEthernet1/0 192.168.35.3",
                  "ip route 192.168.1.0 255.255.255.0 GigabitEthernet2/0 192.168.15.1"]
    return "\n".join(lines) + "\n"


def configure(c, lines):
    c.command("configure terminal")
    for line in lines:
        c.command(line)
    c.command("end")


def migration_lines(name, running):
    # Only this lab's old routes may be removed, never an unknown user route.
    allowed = {
        "R1": {("0.0.0.0", "0.0.0.0"), ("8.8.8.8", "255.255.255.255")},
        "R3": {("192.168.1.0", "255.255.255.0"), ("192.168.14.0", "255.255.255.0"), ("192.168.15.0", "255.255.255.0")},
        "R4": {("192.168.1.0", "255.255.255.0"), ("8.8.8.8", "255.255.255.255")},
        "R5": {("192.168.1.0", "255.255.255.0"), ("8.8.8.8", "255.255.255.255")},
    }
    lines = []
    for line in running.splitlines():
        if line.startswith("ip route "):
            words = line.split()
            if len(words) < 5 or tuple(words[2:4]) not in allowed[name]:
                raise LabError(name + " has an unexpected static route. Backup retained; no migration started.")
            lines.append("no " + line)
        if line.startswith("router ") and line != "router ospf 1":
            raise LabError(name + " has an unexpected routing process; no migration started.")
    if "router ospf 1" in running.splitlines():
        lines += ["no router ospf 1"]
    for interface in ADDRESS[name]:
        lines += ["interface " + interface, "no ip ospf cost", "exit"]
    if name == "R1":
        pools = re.findall(r"^ip dhcp pool (.+)$", running, re.M)
        if any(pool not in ("Canara-Bank", "SBI-Bank", "DHCP") for pool in pools):
            raise LabError("R1 has an unexpected DHCP pool; no migration started.")
        lines += ["no ip dhcp pool " + pool for pool in pools]
    return lines + config(name).splitlines()


class Console:
    # Minimal Telnet negotiation, without telnetlib (removed in Python 3.13).
    def __init__(self, host, port, logfile, name, timeout=300):
        if host not in ("127.0.0.1", "localhost", "0.0.0.0", "::", "::1"):
            raise LabError("Refusing nonlocal device console.")
        deadline = time.monotonic() + timeout
        while True:
            try:
                self.s = socket.create_connection(("127.0.0.1", int(port)), timeout=3)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise LabError(name + " console did not become reachable.") from None
                time.sleep(2)
        self.s.settimeout(0.5)
        self.state = "data"
        self.verb = None
        self.logfile = logfile
        self.name = name

    def decode(self, data):
        out = bytearray()
        for b in data:
            if self.state == "data":
                if b == 255:
                    self.state = "iac"
                else:
                    out.append(b)
            elif self.state == "iac":
                if b == 255:
                    out.append(255); self.state = "data"
                elif b in (251, 252, 253, 254):
                    self.verb = b; self.state = "option"
                elif b == 250:
                    self.state = "sub"
                else:
                    self.state = "data"
            elif self.state == "option":
                # Accept remote ECHO and suppress-go-ahead, reject others.
                if self.verb == 251:
                    self.s.sendall(bytes((255, 253 if b in (1, 3) else 254, b)))
                elif self.verb == 253:
                    self.s.sendall(bytes((255, 252, b)))
                self.state = "data"
            elif self.state == "sub":
                if b == 255:
                    self.state = "subiac"
            elif self.state == "subiac":
                self.state = "data" if b == 240 else "sub"
        return out.decode("utf-8", errors="replace").replace("\r", "")

    def send(self, text):
        self.s.sendall(text.encode() + b"\r")

    def read_prompt(self, timeout=30, expected=None, allow_save_confirm=False):
        deadline = time.monotonic() + timeout
        text = ""
        save_confirmed = False
        next_enter = time.monotonic() + 3
        prompt = re.compile(r"(?:^|\n)(?:[A-Za-z0-9_.-]+(?:\([^\n]*\))?[#>]|[A-Za-z0-9_.-]+\[\d+\]>)[ \t]*$")
        while time.monotonic() < deadline:
            try:
                data = self.s.recv(65536)
                if not data:
                    raise LabError(self.name + " console closed.")
                chunk = self.decode(data)
                text += chunk
                if len(text) > 4_000_000:
                    raise LabError(self.name + " console output exceeded limit.")
                if "--More--" in text[-100:]:
                    self.s.sendall(b" ")
                if re.search(r"(?i)(?:password|username):\s*$", text):
                    raise LabError(self.name + " requests credentials; stopped without guessing.")
                if "Would you like to enter the initial configuration dialog?" in text[-500:]:
                    raise LabError(self.name + " did not load the generated startup config. Stop here and send the error.")
                if "Press RETURN to get started" in text[-500:]:
                    self.send("")
                if allow_save_confirm and not save_confirmed and expected == "write memory" and expected in text:
                    confirmation = r"Warning: Attempting to overwrite an NVRAM configuration previously written\s+by a different version of the system image\.\s+Overwrite the previous NVRAM configuration\?\[confirm\]\s*$"
                    if re.search(confirmation, text):
                        self.logfile.write("\n[Approved save confirmation: this identified lab router only]\n")
                        self.logfile.flush()
                        self.s.sendall(b"\r")
                        save_confirmed = True
                if prompt.search(text) and (expected is None or expected in text):
                    self.logfile.write(text); self.logfile.flush()
                    return text
            except socket.timeout:
                # Initial attach may replay old boot logs before it accepts input.
                # Only initial sync retries an empty Enter, never a real command.
                if expected is None and time.monotonic() >= next_enter:
                    self.s.sendall(b"\r")
                    next_enter = time.monotonic() + 3
        self.logfile.write(text); self.logfile.flush()
        raise LabError(self.name + " prompt timeout. Inspect the console log; no success assumed.")

    def command(self, text, timeout=30, strict=True):
        print("[%s] %s" % (self.name, text), flush=True)
        self.logfile.write("\n>>> " + text + "\n"); self.logfile.flush()
        self.drain()
        self.send(text)
        output = self.read_prompt(timeout, expected=text, allow_save_confirm=(text == "write memory"))
        print(output, flush=True)
        if strict and re.search(r"%\s*(?:Invalid input|Incomplete command|Ambiguous command|Error|Unrecognized command)", output, re.I):
            raise LabError(self.name + " rejected command: " + text)
        return output

    def drain(self, quiet=0.7, maximum=4):
        # Consume old banners/prompts before sending a command. Never count these
        # bytes as the response to the new command.
        deadline = time.monotonic() + maximum
        old_timeout = self.s.gettimeout()
        self.s.settimeout(quiet)
        try:
            while time.monotonic() < deadline:
                try:
                    data = self.s.recv(65536)
                    if not data:
                        raise LabError(self.name + " console closed while synchronizing.")
                    self.logfile.write(self.decode(data)); self.logfile.flush()
                except socket.timeout:
                    break
        finally:
            self.s.settimeout(old_timeout)

    def sync(self):
        self.drain()
        # Cancel a still-pending old save with Ctrl-U plus Enter before new commands.
        # This was observed to cancel the exact stale confirmation in the actual log.
        # Never automatically confirm a historical replay during initial attachment.
        self.s.sendall(b"\x15\r")
        self.read_prompt(timeout=420)
        self.drain()

    def close(self):
        self.s.close()


def port(node, wanted):
    for p in node.get("ports", []):
        name = str(p.get("name", "")).lower()
        if name == wanted.lower() or (wanted == "Ethernet0" and name in ("e0", "eth0")) or (wanted == "Ethernet1" and name in ("e1", "eth1")):
            return {"node_id": node["node_id"], "adapter_number": p["adapter_number"], "port_number": p["port_number"]}
    raise LabError(node["name"] + " lacks diagram interface " + wanted + ". No guessed port mapping.")


def choose(templates, kind, name=None):
    candidates = [t for t in templates if t.get("template_type") == kind and (name is None or t.get("name", "").lower() == name)]
    if len(candidates) != 1:
        raise LabError("Need exactly one %s template%s; found %d." % (kind, " named " + name if name else "", len(candidates)))
    return candidates[0]


def ping_ok(text):
    if re.search(r"(?<![0-9])0% packet loss", text):
        return True
    return len(re.findall(r"bytes from 8\.8\.8\.8.*?icmp_seq=", text)) >= 5


def gateway_ping_ok(text):
    if re.search(r"(?<![0-9])0% packet loss", text):
        return True
    return len(re.findall(r"bytes from 192\.168\.1\.100.*?icmp_seq=", text)) >= 5


def check(summary, label, ok, detail):
    result = {"check": label, "status": "PASS" if ok else "FAIL", "detail": detail}
    summary.append(result)
    print("%s: %s - %s" % (result["status"], label, detail), flush=True)


def cef_default_ok(output, hop, interface):
    # Require a real FIB entry plus its next hop/interface, not command echo or RIB error.
    return bool(re.search(r"^0\.0\.0\.0/0(?:,|\s)", output, re.M)) and hop in output and interface in output and not re.search(r"(?:unresolved|drop adjacency|no route|not running)", output, re.I)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="read-only preflight, no new project")
    args = parser.parse_args()
    api = API()
    out = None
    consoles = {}
    files = []
    checks = []
    manifest = {}
    shutdown_pending = False
    def save_state():
        if out:
            (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
            (out / "checks.json").write_text(json.dumps(checks, indent=2))
    try:
        version = api.call("GET", "/v2/version")
        if not isinstance(version, dict) or not str(version.get("version", "")).startswith("2.2."):
            raise LabError("This builder supports GNS3 2.2 only.")
        templates = api.call("GET", "/v2/templates")
        computes = api.call("GET", "/v2/computes")
        if not any(c.get("compute_id") == "local" and c.get("connected") is True for c in computes):
            raise LabError("A connected local compute is required.")
        router = choose(templates, "dynamips", "c7200")
        if router.get("platform") not in (None, "c7200") or router.get("compute_id") not in (None, "local"):
            raise LabError("The c7200 template is not on the local compute.")
        switch = choose(templates, "ethernet_switch")
        pc = choose(templates, "vpcs")
        print("Preflight: GNS3 %s, local compute connected, c7200 + Ethernet switch + VPCS found." % version["version"])
        print("Creates one separate new project. Existing projects and shared templates are untouched.")
        if args.check_only:
            print("CHECK ONLY complete. Image boot and exact runtime port names remain untested.")
            return 0
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        out = Path.home() / "GNS3-AutoLab-Reports" / stamp
        out.mkdir(parents=True, exist_ok=False)
        for name in ROUTERS:
            (out / (name + "-applied-startup.cfg")).write_text(config(name))
            print("\n=== %s COMPLETE STARTUP CONFIGURATION ===\n%s" % (name, config(name)))
        project_id = str(uuid.uuid4())
        manifest.update({"project_id": project_id, "project_name": "Static-Default-" + stamp, "gns3_version": version["version"], "nodes": {}, "stage": "creating project", "report_directory": str(out)})
        save_state()
        project = api.call("POST", "/v2/projects", {"name": manifest["project_name"], "project_id": project_id, "auto_close": False, "show_interface_labels": True, "scene_width": 1500, "scene_height": 1200})
        if project.get("project_id") != project_id:
            raise LabError("Unexpected project ID; no further writes.")
        api.project = project_id
        manifest["project_path"] = project.get("path")
        manifest["project_filename"] = project.get("filename")
        save_state()
        prefix = "/v2/projects/" + project_id
        nodes = {}
        for name in ("R3", "R4", "R5", "R1", "Switch1", "PC1"):
            template = router if name in ROUTERS else switch if name == "Switch1" else pc
            x, y = POSITIONS[name]
            if name in manifest["nodes"]:
                node = api.call("GET", prefix + "/nodes/" + manifest["nodes"][name])
            else:
                node = api.call("POST", prefix + "/templates/" + template["template_id"], {"name": name, "x": x, "y": y, "compute_id": "local"})
            nodes[name] = node
            manifest["nodes"][name] = node["node_id"]
            save_state()
            if name in ROUTERS:
                # Do not PUT startup_config_content: GNS3 2.2 rejects it on updates.
                # The verified template already has the correct PA-GE modules.
                node = api.call("GET", prefix + "/nodes/" + node["node_id"])
                if node.get("status") != "stopped":
                    raise LabError(name + " is not stopped; refusing to overwrite its config.")
                for expected in ADDRESS[name]:
                    port(node, expected)
                props = node.get("properties", {})
                dynamips_id = props.get("dynamips_id")
                if isinstance(dynamips_id, bool) or not isinstance(dynamips_id, int) or dynamips_id < 0:
                    raise LabError(name + " did not return a valid Dynamips instance ID.")
                # Exact GNS3 v2.2.61 router.py startup_config_path and start() contract.
                # This field is derived by the server, not returned as startup_config.
                config_path = "configs/i%d_startup-config.cfg" % dynamips_id
                file_url = prefix + "/nodes/" + node["node_id"] + "/files/" + config_path
                startup = "!\n" + config(name) + "end\n"
                api.call("POST", file_url, startup.encode(), raw=True)
                readback = api.call("GET", file_url, raw=True)
                if readback.replace("\r\n", "\n") != startup:
                    raise LabError(name + " startup file readback did not match; no boot attempted.")
                nodes[name] = node
        # Resolve and validate every port before linking or starting anything.
        endpoints = [(port(nodes[a], ap), port(nodes[b], bp)) for a, ap, b, bp in LINKS]
        used = set()
        for pair in endpoints:
            for p in pair:
                key = (p["node_id"], p["adapter_number"], p["port_number"])
                if key in used:
                    raise LabError("Duplicate port in plan.")
                used.add(key)
        for a, b in endpoints:
            api.call("POST", prefix + "/links", {"nodes": [a, b]})
        annotations = [(-480, -400, 960, 440, "#ffe4a3", "SERVICE PROVIDERS - simulated private WAN"), (-480, 100, 960, 580, "#dceeff", "ENTERPRISE - DHCP gateway 192.168.1.100/24"), (400, -380, 550, 120, "#f5f5f5", "8.8.8.8/32 is R3 Loopback0 - NOT real Internet"), (400, -220, 550, 120, "#f5f5f5", "Static default: Airtel AD10 primary / TATA AD20 backup")]
        for x, y, w, h, fill, text in annotations:
            svg = '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d"><rect width="100%%" height="100%%" rx="8" fill="%s" stroke="#708090"/><text x="14" y="28" font-family="Arial" font-size="16">%s</text></svg>' % (w, h, fill, text)
            api.call("POST", prefix + "/drawings", {"x": x, "y": y, "z": -10, "svg": svg})
        manifest["stage"] = "starting nodes"
        save_state()
        for name in (*ROUTERS, "Switch1", "PC1"):
            api.call("POST", prefix + "/nodes/" + nodes[name]["node_id"] + "/start", {})
        print("\nNew project: " + manifest["project_name"])
        print("Reports: " + str(out))
        print("The new topology is saved separately from all existing labs.")
        project_dir = manifest.get("project_path")
        project_file = manifest.get("project_filename")
        if isinstance(project_dir, str) and isinstance(project_file, str):
            candidate = Path(project_dir) / project_file
            if candidate.is_absolute() and candidate.suffix == ".gns3" and candidate.is_file() and sys.platform == "darwin":
                subprocess.run(["open", "-a", "GNS3", str(candidate)], check=False)
                print("Asked GNS3 to display the new project. If a dialog appears, choose this new project, not an older lab.")
            else:
                print("To view it, use File > Open Project in GNS3 and select " + manifest["project_name"])
        else:
            print("To view it, use File > Open Project in GNS3 and select " + manifest["project_name"])
        manifest["stage"] = "attaching consoles; boot can take several minutes"
        save_state()
        for name in (*ROUTERS, "PC1"):
            node = api.call("GET", prefix + "/nodes/" + nodes[name]["node_id"])
            f = (out / (name + "-console.txt")).open("a", buffering=1)
            files.append(f)
            c = Console(node.get("console_host", "127.0.0.1"), node["console"], f, name)
            consoles[name] = c
            c.sync()
            if name in ROUTERS:
                c.command("enable")
                c.command("terminal length 0")
                c.command("terminal width 512", strict=False)
                c.command("show ip interface brief")
        r1 = consoles["R1"]
        vpc = consoles["PC1"]
        # Attach every console and collect every backup before the first config change.
        backups = {}
        plans = {}
        for name in ROUTERS:
            running = consoles[name].command("show running-config", timeout=90)
            if not re.search(r"^hostname " + re.escape(name) + r"\s*$", running, re.M):
                raise LabError(name + " running hostname differs; no migration started.")
            for interface, address in ADDRESS[name].items():
                pattern = r"^interface " + re.escape(interface) + r"\n(?:(?!^interface |^!).)*?^ ip address " + re.escape(address) + r" 255\.255\.255\.0\s*$"
                if not re.search(pattern, running, re.M | re.S):
                    raise LabError(name + " running interface/IP differs; no migration started.")
            backups[name] = running
            (out / (name + "-before-running.txt")).write_text(running)
            startup = consoles[name].command("show startup-config", timeout=90)
            (out / (name + "-before-startup.txt")).write_text(startup)
            plans[name] = migration_lines(name, running)
            (out / (name + "-change-commands.txt")).write_text("\n".join(plans[name]) + "\n")
        manifest["stage"] = "backups captured; applying static/default revision"
        save_state()
        for name in ("R3", "R4", "R5", "R1"):
            configure(consoles[name], plans[name])
        # Exact address through a reservation established before PC's first DHCP request.
        pc_identity = vpc.command("show ip")
        mac_match = re.search(r"MAC\s*:\s*((?:[0-9a-f]{2}:){5}[0-9a-f]{2})", pc_identity, re.I)
        if not mac_match:
            raise LabError("Cannot establish the new PC's MAC for its DHCP reservation.")
        hex_id = "01" + mac_match.group(1).replace(":", "").lower()
        client_id = ".".join(hex_id[i:i+4] for i in range(0, len(hex_id), 4))
        configure(r1, ["ip dhcp pool PC1-RESERVATION", "host 192.168.1.1 255.255.255.0", "client-identifier " + client_id, "default-router 192.168.1.100", "dns-server 192.168.1.101 192.168.1.102", "exit"])
        lease = ""
        for _ in range(3):
            vpc.command("ip dhcp", timeout=60)
            lease = vpc.command("show ip")
            if re.search(r"192\.168\.1\.1(?:/24|\s)", lease) and "192.168.1.100" in lease:
                break
            time.sleep(3)
        check(checks, "PC DHCP exact diagram address and gateway", bool(re.search(r"192\.168\.1\.1(?:/24|\s)", lease)) and "192.168.1.100" in lease, "Expected 192.168.1.1/24 gateway .100; no static-IP substitute")
        if checks[-1]["status"] != "PASS":
            raise LabError("DHCP did not match the diagram. Configuration backups retained.")
        vpc.command("save")

        def verify_stage(label, next_hop, distance, global_ip):
            manifest["stage"] = label
            save_state()
            print("\n========== " + label + " ==========", flush=True)
            rt = r1.command("show ip route 0.0.0.0")
            selected = r1.command("show ip cef 8.8.8.8 detail")
            r1.command("show ip cef exact-route 192.168.1.1 8.8.8.8", strict=False)
            check(checks, label + " default AD/next hop", 'Known via "static"' in rt and ("distance %d," % distance) in rt and next_hop in rt, "Expected default AD%d via %s" % (distance, next_hop))
            expected_interface = "GigabitEthernet2/0" if next_hop == "192.168.14.4" else "GigabitEthernet3/0"
            check(checks, label + " target forwarding uses default", cef_default_ok(selected, next_hop, expected_interface), "CEF default forwarding via " + next_hop + " on " + expected_interface)
            r1.command("clear ip nat translation *")
            gateway = vpc.command("ping 192.168.1.100 -c 5", timeout=45)
            if not gateway_ping_ok(gateway):
                gateway = vpc.command("ping 192.168.1.100 -c 5", timeout=45)
            ping = vpc.command("ping 8.8.8.8 -c 5", timeout=45)
            if not ping_ok(ping):
                ping = vpc.command("ping 8.8.8.8 -c 5", timeout=45)
            check(checks, label + " PC to gateway", gateway_ping_ok(gateway), "Measured VPCS replies")
            check(checks, label + " PC to simulated 8.8.8.8", ping_ok(ping), "R3 loopback, not Internet")
            nat = r1.command("show ip nat translations")
            nat_ok = any(global_ip in line and "192.168.1.1:" in line and "8.8.8.8" in line for line in nat.splitlines())
            check(checks, label + " provider-specific PAT", nat_ok, "Expected inside global " + global_ip + " for PC .1")
            vpc.command("trace 8.8.8.8", timeout=90, strict=False)
            save_state()
            if any(c["status"] == "FAIL" for c in checks if c["check"].startswith(label)):
                raise LabError(label + " failed a measured check. No success assumed.")

        verify_stage("1 Primary Airtel", "192.168.14.4", 10, "192.168.14.1")
        # Set the flag before writing: a timeout can happen after shutdown landed.
        shutdown_pending = True
        try:
            configure(r1, ["interface GigabitEthernet2/0", "shutdown", "exit"])
            time.sleep(5)
            verify_stage("2 Backup TATA with R1 Airtel interface down", "192.168.15.5", 20, "192.168.15.1")
        finally:
            configure(r1, ["interface GigabitEthernet2/0", "no shutdown", "exit"])
            shutdown_pending = False
        time.sleep(5)
        verify_stage("3 Airtel restored", "192.168.14.4", 10, "192.168.14.1")
        for name in ROUTERS:
            c = consoles[name]
            for command in ["show version", "show ip interface brief", "show interfaces description", "show ip route", "show ip route static", "show ip route 8.8.8.8", "show ip protocols", "show running-config"]:
                output = c.command(command, timeout=90)
                if command == "show running-config":
                    (out / (name + "-after-running.txt")).write_text(output)
                    check(checks, name + " no OSPF process", not re.search(r"^router ospf ", output, re.M), "Static/default exercise only")
            if name == "R1":
                for command in ["show ip dhcp pool", "show ip dhcp binding", "show ip dhcp conflict", "show ip nat statistics", "show ip nat translations", "show access-lists", "show route-map"]:
                    c.command(command, strict=False)
            saved = c.command("write memory", timeout=90)
            check(checks, name + " save acknowledged", "[OK]" in saved or "configuration saved" in saved.lower(), "Actual save response captured")
            startup = c.command("show startup-config", timeout=90)
            if name == "R1":
                check(checks, "PC1 reservation saved", "ip dhcp pool PC1-RESERVATION" in startup and "host 192.168.1.1 255.255.255.0" in startup and ("client-identifier " + client_id) in startup, "Actual startup reservation checked")
            (out / (name + "-after-startup.txt")).write_text(startup)
            stored = {line.strip() for line in startup.splitlines()}
            required = {line for line in config(name).splitlines() if line.startswith(("hostname ", "ip route ", "ip nat inside source ", "ip address ", "network ", "default-router ", "dns-server "))}
            check(checks, name + " startup contains intended configuration", required.issubset(stored) and not re.search(r"^router ospf ", startup, re.M), "Compare actual startup readback with intended static/DHCP/PAT settings")
        final_nodes = api.call("GET", prefix + "/nodes")
        check(checks, "all required emulators started", all(any(n.get("node_id") == nodes[name]["node_id"] and n.get("status") == "started" for n in final_nodes) for name in (*ROUTERS, "PC1")), "Switch is built-in, not an IOS managed switch")
        (out / "ERROR.txt").unlink(missing_ok=True)
        manifest["stage"] = "verification finished; inspect checks for pass/fail"
        save_state()
        failed = sum(x["status"] == "FAIL" for x in checks)
        summary = "\n".join("%s | %s | %s" % (c["status"], c["check"], c["detail"]) for c in checks)
        (out / "RESULTS.txt").write_text("Project: " + manifest["project_name"] + "\n" + summary + ("\n\nAll measured checks passed in this run.\n" if not failed else "\n\nWARNING: %d checks failed. Do not treat this run as fully verified.\n" % failed) + "Intended configuration: static/default routing, Airtel AD10 primary, TATA AD20 backup. Review restoration and save checks above for the measured outcome.\nPAT retained as an explicit correction to the PDF's return-path limitation.\nOnly new probe flows after a local interface shutdown tested; no upstream failure tracking or session continuity claim.\nNo physical network/Internet/DNS service tested. DHCP DNS .101/.102 are placeholders from the PDF, not running servers.\nOriginal six-node topology and diagram IPs retained; PDF's unconfigured R2/PC2 omitted.\n")
        print("\nFinished with %d failed checks. Reports: %s" % (failed, out))
        print("Send RESULTS.txt and any error, not your GNS3 server settings file.")
        return 2 if failed else 0
    except (LabError, KeyboardInterrupt, OSError, KeyError, TypeError) as exc:
        message = "Stopped by user" if isinstance(exc, KeyboardInterrupt) else str(exc) if isinstance(exc, LabError) else "Unexpected local/API response error (%s). Partial lab preserved for inspection." % type(exc).__name__
        print("\nSTOPPED: " + message, file=sys.stderr)
        if out:
            manifest["error"] = message
            save_state()
            (out / "ERROR.txt").write_text(message + "\nPartial new lab preserved. Do not rerun blindly: each fresh run makes a new project.\nProject: " + manifest.get("project_name", "unknown") + "\n")
            print("Partial new lab preserved. Reports: " + str(out), file=sys.stderr)
        return 1
    finally:
        if shutdown_pending and "R1" in consoles:
            try:
                configure(consoles["R1"], ["interface GigabitEthernet2/0", "no shutdown", "exit"])
                print("Recovery: Airtel no shutdown acknowledged; inspect link status before further work.", flush=True)
            except Exception:
                print("RESTORATION UNVERIFIED: R1 GigabitEthernet2/0 may remain shut. Stop and send ERROR.txt and R1-console.txt.", file=sys.stderr)
                if out:
                    (out / "RESTORE-NEEDED.txt").write_text("R1 GigabitEthernet2/0 restoration was not acknowledged. Do not assume primary path restored.\n")
        for c in consoles.values():
            c.close()
        for f in files:
            f.close()


if __name__ == "__main__":
    sys.exit(main())
