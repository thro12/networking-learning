# pcs-lab3.py - sets IPs on PC1..PC6 of the 3-router OSPF lab, tests them, and ONLY if every test passes saves them (VPCS "save").
# Run it AFTER ssh-ospf-lab3.py has finished OK (the routers must already be configured, or the pings cannot pass).
# Reads the PC console ports from the GNS3 server on this Mac. Plain telnet to the PC consoles. Routers are not touched.
# No passwords. Run with any Python 3:  python3 pcs-lab3.py
import os
import re
import sys
import json
import time
import socket
import datetime
import urllib.request

GNS3_URL = os.environ.get("GNS3_URL", "http://localhost:3080")
HOST = "127.0.0.1" if os.environ.get("GNS3_URL","").startswith("http://127") else "localhost"
PCS = [("PC1", "10.20.1.11", "10.20.1.1"), ("PC2", "10.20.1.12", "10.20.1.1"),
       ("PC3", "10.20.2.11", "10.20.2.1"), ("PC4", "10.20.2.12", "10.20.2.1"),
       ("PC5", "10.20.3.11", "10.20.3.1"), ("PC6", "10.20.3.12", "10.20.3.1")]
PROMPT_RE = re.compile(r"(?m)^[\w\-\.\/]+(?:\([\w\-\.\/]+\))?[#>]\s*$")
LOG = []
def log(text):
    LOG.append(text)


class Console:
    def __init__(self, name, port):
        self.name = name
        self.port = port
        try:
            self.s = socket.create_connection((HOST, port), timeout=10)
        except OSError:
            raise ConnectionError("%s console (port %d) refused the connection. Is %s started and the port right?" % (name, port, name))
        self.s.settimeout(0.5)
        self.buf = ""
        self.pending = b""
        self.last_raw = ""

    def _read(self):
        try:
            data = self.s.recv(4096)
        except socket.timeout:
            return ""
        except OSError:
            raise ConnectionError(self.name + " console (port %d) closed the connection." % self.port)
        if not data:
            raise ConnectionError(self.name + ": console closed")
        data = self.pending + data
        self.pending = b""
        out = bytearray()
        i = 0
        n = len(data)
        while i < n:
            b = data[i]
            if b != 255:
                out.append(b)
                i += 1
                continue
            if i + 1 >= n:                       # IAC split across reads: keep for next read
                self.pending = data[i:]
                break
            cmd = data[i + 1]
            if cmd == 255:                       # escaped 0xFF data byte
                out.append(255)
                i += 2
            elif cmd in (251, 252, 253, 254):    # WILL/WONT/DO/DONT + option
                if i + 2 >= n:
                    self.pending = data[i:]
                    break
                opt = data[i + 2]
                if cmd == 253:
                    self.s.sendall(bytes([255, 252, opt]))   # DO -> WONT
                elif cmd == 251:
                    self.s.sendall(bytes([255, 254, opt]))   # WILL -> DONT
                i += 3
            elif cmd == 250:                     # subnegotiation: skip to IAC SE
                end = data.find(bytes([255, 240]), i + 2)
                if end < 0:
                    self.pending = data[i:]
                    break
                i = end + 2
            else:                                # other 2-byte command
                i += 2
        text = out.decode("utf-8", "replace")
        text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text).replace("\x00", "")
        text = text.replace("\r\r\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
        self.buf += text
        log(text)
        return text

    def send(self, line):
        self.s.sendall((line + "\r\n").encode())

    def wait_for(self, pattern, timeout=30):
        """Wait until regex matches the unread buffer. Returns (matched, text consumed)."""
        end = time.time() + timeout
        rx = re.compile(pattern) if isinstance(pattern, str) else pattern
        while time.time() < end:
            self._read()
            if rx.search(self.buf):
                text, self.buf = self.buf, ""
                return True, text
        text, self.buf = self.buf, ""
        return False, text

    def drain(self, quiet=0.4):
        """Read and discard anything still arriving (stale prompts, banners)."""
        end = time.time() + quiet
        while time.time() < end:
            if self._read():
                end = time.time() + quiet
        self.buf = ""

    def run(self, cmd, timeout=30, prompt=None):
        """Send a command and return its output. Works whether or not the console echoes the command."""
        rx = prompt or PROMPT_RE
        self.drain()
        self.send(cmd)
        start = time.time()
        end = start + timeout
        ok = False
        while time.time() < end:
            self._read()
            lines = [l for l in self.buf.split("\n") if l.strip()]
            if lines and rx.search(lines[-1]):
                content = [l for l in lines if not rx.search(l)]
                echoed = cmd and any(cmd in l for l in lines)
                if content or (time.time() - start > 2.5):
                    ok = True
                    break
        raw = self.buf
        self.buf = ""
        self.last_raw = raw
        lines = raw.split("\n")
        # drop the echoed command (on its own line, or after a prompt) and the trailing prompt
        out = []
        for l in lines:
            t = l.strip()
            if not t:
                continue
            if cmd and rx.search(t.split(cmd)[0].strip() if cmd in t else "<<none>>") and t.endswith(cmd):
                continue
            if cmd and t == cmd:
                continue
            if rx.search(t):
                continue
            out.append(l)
        return ok, "\n".join(out).strip()

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass



def vpcs_session(name, port):
    for attempt in range(3):
        try:
            return vpcs_session_once(name, port)
        except ConnectionError:
            if attempt == 2:
                raise
            time.sleep(3)


def vpcs_session_once(name, port):
    con = Console(name, port)
    con.send("")
    ok, text = con.wait_for(r"(?m)^\S+>\s*$", 20)
    if not ok:
        con.send("")
        ok, text = con.wait_for(r"(?m)^\S+>\s*$", 20)
    if not ok:
        sys.exit(name + " console gave no prompt. Is " + name + " started?")
    return con


VP = re.compile(r"(?m)^\S+>\s*$")


def vpcs_cmd(con, cmd, timeout=30):
    return con.run(cmd, timeout, VP)


def pcs_raw(con):
    return con.last_raw[-400:]


def save_pc(con, name):
    """VPCS 'save' writes startup.vpc, which VPCS runs again when the PC starts. Success text ends with 'done'."""
    ok, out = vpcs_cmd(con, "save", 30)
    if ok and re.search(r"\bdone\b", out.lower()) and "startup.vpc" in out:
        return True, name + ": saved to startup.vpc"
    return False, name + ": save not confirmed. Console said: " + repr(out[-200:])



def ping_pc(con, ip, count=5):
    ok, out = vpcs_cmd(con, "ping %s -c %d" % (ip, count), 40)
    got = len(re.findall(r"bytes from", out))
    return got, count, out



def discover_ports():
    """Read console ports from the GNS3 server. Trusts exactly one open project with exactly one node named
    PC1..PC6 each (type vpcs). Anything else: returns None."""
    for api in ("v2", "v3"):
        try:
            def get(path):
                with urllib.request.urlopen(GNS3_URL + "/" + api + path, timeout=5) as r:
                    return json.load(r)
            opened = [p for p in get("/projects") if p.get("status") == "opened"]
            if len(opened) != 1:
                return None, None, None
            nodes = get("/projects/" + opened[0]["project_id"] + "/nodes")
            ports, status = {}, {}
            for name, ip, gw in PCS:
                match = [n for n in nodes if n.get("name") == name]
                if len(match) != 1 or match[0].get("node_type") != "vpcs" or not match[0].get("console"):
                    return None, None, None
                ports[name] = match[0]["console"]
                status[name] = match[0].get("status")
            if len(set(ports.values())) != len(PCS):
                return None, None, None
            return ports, status, opened[0]["name"]
        except Exception:
            continue
    return None, None, None


def ask_ports():
    print("Could not read the ports from GNS3 automatically. Type each PC console port")
    print("(right-click the PC > Show node information > 'Console is on port ...').")
    return {name: int(input("  " + name + " console port: ").strip()) for name, ip, gw in PCS}


def vpcs_show(con):
    ok, shown = vpcs_cmd(con, "show ip", 10)
    nm = re.search(r"NAME\s*:\s*(\S+)", shown)
    mm = re.search(r"IP/MASK\s*:\s*(\S+)", shown)
    gg = re.search(r"GATEWAY\s*:\s*(\S+)", shown)
    return (nm.group(1) if nm else "", mm.group(1) if mm else "", gg.group(1) if gg else "", shown)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    ports, status, proj = discover_ports()
    if ports:
        print("GNS3 project '%s' found. PC console ports: %s" % (proj, ", ".join("%s=%s" % (k, ports[k]) for k in ports)))
        stopped = [k for k, v in status.items() if v != "started"]
        if stopped:
            sys.exit("Start these PCs first: " + ", ".join(stopped))
    else:
        ports = ask_ports()
        if len(set(ports.values())) != len(PCS):
            sys.exit("The six console ports must be different. Nothing changed.")
    cons = {}
    try:
        for name, ip, gw in PCS:
            cons[name] = vpcs_session(name, ports[name])
    except ConnectionError as e:
        sys.exit(str(e) + " Nothing changed.")
    # preflight: right device on each port, and no different IP already there
    problems = []
    for name, ip, gw in PCS:
        nm, mask, g, raw = vpcs_show(cons[name])
        if not nm.startswith(name):
            problems.append("%s: the console on port %d says its name is '%s'. Wrong port? " % (name, ports[name], nm))
        elif mask not in ("", "0.0.0.0/0") and not mask.startswith(ip + "/"):
            problems.append("%s already has IP %s (plan wants %s). Not changing it." % (name, mask, ip))
    if problems:
        print("STOPPED before any change:")
        for p in problems:
            print("  - " + p)
        sys.exit(1)
    print("\nPLAN: set these on the PCs, test, and save only if every test passes:")
    for name, ip, gw in PCS:
        print("  %s  ip %s/24  gateway %s" % (name, ip, gw))
    if input("Type yes to apply: ").strip().lower() != "yes":
        sys.exit("Stopped. Nothing was changed.")
    report = ["pcs-lab3 report " + stamp, ""]
    fails = []
    def check(label, ok, extra=""):
        line = "  [%s] %s%s" % ("OK" if ok else "FAIL", label, ("  " + extra) if (extra and not ok) else "")
        print(line); report.append(line)
        if not ok:
            fails.append(label)
    print("\nSETTING IPs")
    for name, ip, gw in PCS:
        ok, out = vpcs_cmd(cons[name], "ip %s/24 %s" % (ip, gw), 15)
        nm, mask, g, raw = vpcs_show(cons[name])
        check("%s has %s/24 gateway %s" % (name, ip, gw), mask == ip + "/24" and g == gw, "shows IP/MASK=%s GATEWAY=%s" % (mask, g))
    print("\nPING TESTS (a few seconds each)")
    for name, ip, gw in PCS:
        got, cnt, out = ping_pc(cons[name], gw, 5)
        check("%s -> its gateway %s" % (name, gw), got >= 3, "%d of %d replies" % (got, cnt))
    for i, (a, aip, agw) in enumerate(PCS):
        for b, bip, bgw in PCS[i + 1:]:
            got, cnt, out = ping_pc(cons[a], bip, 5)
            check("%s -> %s (%s)" % (a, b, bip), got >= 3, "%d of %d replies" % (got, cnt))
    saved = []
    if fails:
        print("\n%d check(s) FAILED. NOT SAVED." % len(fails))
        print("The PCs keep these IPs only until they are restarted or the project is closed. This script does not undo them.")
        print("If the failures are cross-LAN pings, check the routers first (OSPF neighbours, ssh-ospf-lab3 report).")
    else:
        print("\nAll checks passed. Saving the six PCs (VPCS save writes startup.vpc).")
        for name, ip, gw in PCS:
            ok, msg = save_pc(cons[name], name)
            print("  " + ("SAVED. " if ok else "NOT SAVED. ") + msg)
            report.append(("PASS " if ok else "FAIL ") + "save " + msg)
            if ok:
                saved.append(name)
            else:
                fails.append(name + " save")
        if fails:
            print("PARTIAL SAVE: saved %s; NOT saved %s." % (", ".join(saved) or "none", ", ".join(n for n, i, g in PCS if n not in saved)))
        print("Reopen persistence of startup.vpc is not tested by this script.")
    fn = os.path.join(here, "pcs-lab3-report-%s.txt" % stamp)
    with open(fn, "w") as f:
        f.write("\n".join(report) + "\n")
    print("Report saved: " + fn)
    for c in cons.values():
        c.close()
    sys.exit(1 if fails else 0)


main()
