#!/usr/bin/env python3
"""ONE-FILE LAB: 3 routers (SSH) + 6 PCs (console). Save as a NEW file: lab3-all.py
Run:  ~/router-ssh-venv/bin/python lab3-all.py        (forget saved passwords: add --forget)

What it does, in this order:
  1. READ-ONLY checks. Logs in to R1/R2/R3 over SSH (usernames r1admin / r2admin / r3admin), finds the six PC
     console ports from the GNS3 server, and reads every router interface and every PC. Stops, changing nothing, if
     a device already has a DIFFERENT IP than the plan, a PC console is the wrong device, or another OSPF process exists.
     A device that already has the planned setting is fine (safe to run again).
  2. Prints the plan and waits for you to type  yes
  3. Sets router IPs + OSPF area 0 (over SSH), then sets the six PC IPs (console).
  4. Tests everything: router interfaces, OSPF neighbours, routes, router pings, each PC to its gateway, and every PC to
     every other PC (30 pings), with a result table.
  Also prints raw OSPF neighbour/route output and PC traces (information only) in the report.
  5. Saves ONLY if every test passed: write memory on the 3 routers and VPCS save on the 6 PCs.
Management ports (R1 Gi2/0, R2 Gi3/0, R3 Gi3/0) are never touched and are not in OSPF.
Host keys: connections only trust keys already in ~/.ssh/known_hosts (accepted at your first manual login). Their
fingerprints were not checked against the routers, so this pins the key, it does not verify it.
Passwords: the first run asks for each router password (hidden, typed twice by macOS 'security') and saves it in your Mac
login Keychain; later runs ask nothing. Nothing is written to a file or put on a command line. Forget them with --forget.
If a check fails nothing is saved and nothing is undone: the routers and PCs keep the new settings until restart/close."""
import getpass, sys, os, re, time, datetime, shutil, subprocess, json, socket, urllib.request
import paramiko
if int(paramiko.__version__.split(".")[0]) >= 5:
    sys.exit("Paramiko %s cannot talk to these routers (SHA-1 key exchange removed).\n"
             "Run with ~/router-ssh-venv/bin/python instead." % paramiko.__version__)
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException

TEST = os.environ.get("LAB3_TEST") == "1"          # only used for local mock tests
PLAN = {
 "R1": {"host": "172.16.100.11", "user": "r1admin", "rid": "1.1.1.1",
        "ifs": [("FastEthernet0/0", "10.20.1.1", "255.255.255.0", True),
                ("GigabitEthernet1/0", "10.20.12.1", "255.255.255.252", False)],
        "nets": [("10.20.1.0", "0.0.0.255"), ("10.20.12.0", "0.0.0.3")],
        "routes": ["10.20.2.0", "10.20.3.0", "10.20.23.0"], "pings": ["10.20.3.1", "10.20.2.1"]},
 "R2": {"host": "172.16.100.12", "user": "r2admin", "rid": "2.2.2.2",
        "ifs": [("GigabitEthernet1/0", "10.20.12.2", "255.255.255.252", False),
                ("FastEthernet0/0", "10.20.23.1", "255.255.255.252", False),
                ("GigabitEthernet2/0", "10.20.2.1", "255.255.255.0", True)],
        "nets": [("10.20.12.0", "0.0.0.3"), ("10.20.23.0", "0.0.0.3"), ("10.20.2.0", "0.0.0.255")],
        "routes": ["10.20.1.0", "10.20.3.0"], "pings": ["10.20.1.1", "10.20.3.1"]},
 "R3": {"host": "172.16.100.13", "user": "r3admin", "rid": "3.3.3.3",
        "ifs": [("FastEthernet0/0", "10.20.23.2", "255.255.255.252", False),
                ("GigabitEthernet1/0", "10.20.3.1", "255.255.255.0", True)],
        "nets": [("10.20.23.0", "0.0.0.3"), ("10.20.3.0", "0.0.0.255")],
        "routes": ["10.20.1.0", "10.20.2.0", "10.20.12.0"], "pings": ["10.20.1.1", "10.20.2.1"]},
}
NEIGHBORS = {"R1": 1, "R2": 2, "R3": 1}
MAC_LEGACY = ("ssh -o KexAlgorithms=+diffie-hellman-group14-sha1 -o HostKeyAlgorithms=+ssh-rsa "
              "-o Ciphers=+aes256-cbc %s@%s")

RLOG = []
def say(s=""):
    print(s); RLOG.append(s)

def target(name):
    p = PLAN[name]
    if TEST:
        return "127.0.0.1", 2200 + int(name[1])
    return p["host"], 22

KC_SERVICE = "gns3-lab3-ssh"          # macOS Keychain item name; account = "username@ip"

def kc_ok():
    return shutil.which("security") is not None

def kc_get(acct):
    """Read a saved password from the login Keychain. The password comes back on a pipe, never on a command line."""
    try:
        r = subprocess.run(["security", "find-generic-password", "-a", acct, "-s", KC_SERVICE, "-w"],
                           capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    return r.stdout.rstrip("\n") if r.returncode == 0 and r.stdout.strip() else None

def kc_add(acct):
    """Let macOS 'security' ask for the password itself (hidden, typed twice). Nothing secret goes through this script or a command line."""
    try:
        r = subprocess.run(["security", "add-generic-password", "-a", acct, "-s", KC_SERVICE, "-U", "-w"], timeout=300)
    except Exception:
        return False
    return r.returncode == 0

def kc_del(acct):
    try:
        subprocess.run(["security", "delete-generic-password", "-a", acct, "-s", KC_SERVICE],
                       capture_output=True, timeout=30)
    except Exception:
        pass

def login(name):
    p = PLAN[name]
    u = p["user"]
    acct = "%s@%s" % (u, p["host"])
    pw, saved = None, False
    if kc_ok():
        pw = kc_get(acct)
        saved = pw is not None
        if pw is None:
            print("%s (%s): no saved password yet. Type it now (hidden, twice). It is stored in your Mac login Keychain, not in any file." % (name, acct))
            if kc_add(acct):
                pw = kc_get(acct)
                saved = pw is not None
    if pw is None:
        pw = getpass.getpass("%s password for %s (hidden, not saved): " % (name, u))
    host, port = target(name)
    dev = {"device_type": "cisco_ios", "host": host, "port": port, "username": u, "password": pw,
           "timeout": 40, "conn_timeout": 20, "ssh_strict": True, "system_host_keys": True,
           "fast_cli": False, "global_delay_factor": 1,
           "read_timeout_override": 20 if TEST else 120}   # simulated routers can take >10 s to answer; Netmiko default is 10 s
    try:
        c = ConnectHandler(**dev)
        if not c.find_prompt().strip().endswith("#"):
            c.disconnect()
            sys.exit("%s: this login is privilege 1 (prompt ends with >), so it cannot change config over SSH.\n"
                     "Fix on that router's GNS3 console: username %s privilege 15 secret <your password>, then write memory. Nothing was changed." % (name, u))
        return c
    except NetmikoAuthenticationException:
        if saved:
            kc_del(acct)
            sys.exit("%s: login failed as %s. The saved Keychain password for it was removed. Run again and type the right one. Nothing was changed." % (name, u))
        sys.exit("%s: login failed as %s (wrong password, or no such user). Nothing was changed." % (name, u))
    except Exception as e:
        if "known_hosts" in str(e):
            print("%s: its host key is not in ~/.ssh/known_hosts. Log in once by hand, then rerun:" % name)
            sys.exit("  " + MAC_LEGACY % (u, p["host"]))
        if isinstance(e, NetmikoTimeoutException):
            sys.exit("%s: timed out reaching %s. Check ping and the management cable. Nothing was changed." % (name, p["host"]))
        sys.exit("%s: SSH error (no password in this text): %s" % (name, e))

def parse_brief(text):
    d = {}
    for ln in text.splitlines():
        f = ln.split()
        if len(f) >= 6 and re.match(r"^[A-Za-z]+\d+/\d+", f[0]):
            d[f[0]] = (f[1], " ".join(f[4:-1]), f[-1])
    return d

def short(n):   # GigabitEthernet1/0 -> Gi1/0 style key used by 'show ip int brief' (full names on this IOS)
    return n


GNS3_URL = os.environ.get("GNS3_URL", "http://localhost:3080")
HOST = "127.0.0.1" if os.environ.get("GNS3_URL", "").startswith("http://127") else "localhost"
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
        self.broken = False

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
    ok, out = con.run(cmd, timeout, VP)
    if not ok:
        # command still running (or console stuck): Ctrl+C, then wait for a real prompt before anything else is sent
        try:
            con.s.sendall(b"\x03")
            got, _ = con.wait_for(r"(?m)^\S+>\s*$", 10)
            if not got:
                con.send("")
                got, _ = con.wait_for(r"(?m)^\S+>\s*$", 10)
        except ConnectionError:
            got = False
        if not got:
            con.broken = True
    return ok, out


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



CONNS = []
PCONS = []
APPLIED = [False]
SAVED_RT = []
SAVED_PC = []


def main():
    say("Lab: %s" % datetime.datetime.now())
    conns = {}
    for n in PLAN:
        conns[n] = login(n)
        CONNS.append(conns[n])
    ports, status, proj = discover_ports()
    if ports:
        say("GNS3 project '%s' found. PC console ports: %s" % (proj, ", ".join("%s=%s" % (k, ports[k]) for k in ports)))
        stopped = [k for k, v in status.items() if v != "started"]
        if stopped:
            sys.exit("Start these PCs first: " + ", ".join(stopped) + ". Nothing was changed.")
    else:
        ports = ask_ports()
        if len(set(ports.values())) != len(PCS):
            sys.exit("The six console ports must be different. Nothing changed.")
    cons = {}
    try:
        for name, ip, gw in PCS:
            cons[name] = vpcs_session(name, ports[name])
            PCONS.append(cons[name])
    except ConnectionError as e:
        sys.exit(str(e) + " Nothing changed.")
    problems = []
    # ---- 1. read-only preflight
    for n, p in PLAN.items():
        c = conns[n]
        brief = parse_brief(c.send_command("show ip interface brief"))
        for ifn, ip, mask, lan in p["ifs"]:
            cur = brief.get(ifn)
            if cur is None:
                problems.append("%s: interface %s not found on this router" % (n, ifn))
            elif cur[0] not in ("unassigned", ip):
                problems.append("%s: %s already has IP %s (plan wants %s). Not changing it." % (n, ifn, cur[0], ip))
        osp = c.send_command("show ip protocols | include Routing Protocol is")
        other = [l.strip() for l in osp.splitlines() if "ospf" in l.lower() and re.search(r'ospf\s+(\d+)', l, re.I) and re.search(r'ospf\s+(\d+)', l, re.I).group(1) != "1"]
        if other:
            problems.append("%s: another OSPF process exists: %s" % (n, ", ".join(other)))
    for name, ip, gw in PCS:
        nm, mask, g, raw = vpcs_show(cons[name])
        if not nm.startswith(name):
            problems.append("%s: the console on port %d says its name is '%s'. Wrong port?" % (name, ports[name], nm))
        elif mask not in ("", "0.0.0.0/0") and not mask.startswith(ip + "/"):
            problems.append("%s already has IP %s (plan wants %s). Not changing it." % (name, mask, ip))
    if problems:
        say("STOPPED before any change:")
        for x in problems:
            say("  - " + x)
        sys.exit(1)
    # ---- 2. plan + confirm
    say("\nPLAN (OSPF process 1, area 0, router IDs 1.1.1.1 / 2.2.2.2 / 3.3.3.3)")
    for n, p in PLAN.items():
        say("  %s (%s)" % (n, p["host"]))
        for ifn, ip, mask, lan in p["ifs"]:
            say("     %-20s %s %s%s" % (ifn, ip, mask, "  passive (LAN)" if lan else ""))
    say("  PCs (gateway = the router port on their LAN):")
    for name, ip, gw in PCS:
        say("     %s  %s/24  gateway %s" % (name, ip, gw))
    say("  Management ports are not touched. Everything is saved only if all tests pass.")
    if input("\nType yes to apply this to R1, R2, R3 and PC1-PC6: ").strip().lower() != "yes":
        sys.exit("Cancelled. Nothing was changed.")
    # ---- 3. apply
    APPLIED[0] = True
    for n, p in PLAN.items():
        cmds = []
        for ifn, ip, mask, lan in p["ifs"]:
            cmds += ["interface " + ifn, "ip address %s %s" % (ip, mask), "no shutdown", "exit"]
        cmds += ["router ospf 1", "router-id " + p["rid"]]
        cmds += ["network %s %s area 0" % nm for nm in p["nets"]]
        cmds += ["passive-interface " + ifn for ifn, ip, mask, lan in p["ifs"] if lan]
        out = conns[n].send_config_set(cmds, read_timeout=60)
        bad = [l for l in out.splitlines() if l.startswith("%")]
        say("%s: applied %d lines%s" % (n, len(cmds), ("  IOS warnings: " + " | ".join(bad)) if bad else ""))
    for name, ip, gw in PCS:
        vpcs_cmd(cons[name], "ip %s/24 %s" % (ip, gw), 15)
    say("PCs: IPs sent to all six.")
    # ---- 4. tests
    fails = []
    def check(label, ok, detail=""):
        say("  [%s] %s%s" % ("OK" if ok else "FAIL", label, ("  " + detail) if detail and not ok else ""))
        if not ok:
            fails.append(label)
    say("\nROUTER TESTS (waiting up to 120 s for OSPF neighbours FULL and all routes learned)")
    end = time.time() + (15 if TEST else 120)
    nbr = {}
    while time.time() < end:
        for n in PLAN:
            t = conns[n].send_command("show ip ospf neighbor")
            nbr[n] = len(re.findall(r"FULL/", t))
        rok = True
        for n, p in PLAN.items():
            rt0 = conns[n].send_command("show ip route ospf")
            rok = rok and all(re.search(r"\bO\b.*\b%s\b" % re.escape(r), rt0) for r in p["routes"])
        if all(nbr[n] >= NEIGHBORS[n] for n in PLAN) and rok:
            break
        time.sleep(5)
    for n, p in PLAN.items():
        brief = parse_brief(conns[n].send_command("show ip interface brief"))
        for ifn, ip, mask, lan in p["ifs"]:
            cur = brief.get(ifn, ("?", "?", "?"))
            check("%s %s %s up/up" % (n, ifn, ip), cur[0] == ip and cur[1].endswith("up") and cur[2] == "up",
                  "now: %s %s %s (up/up needs the right cable on that port)" % cur)
        check("%s OSPF neighbours FULL = %d" % (n, NEIGHBORS[n]), nbr.get(n, 0) == NEIGHBORS[n], "found %d" % nbr.get(n, 0))
        rt = conns[n].send_command("show ip route ospf")
        for r in p["routes"]:
            check("%s learned %s via OSPF" % (n, r), re.search(r"\bO\b.*\b%s\b" % re.escape(r), rt) is not None)
        for dst in p["pings"]:
            pg = conns[n].send_command("ping %s repeat 5 timeout 2" % dst, read_timeout=60)
            m = re.search(r"Success rate is (\d+) percent", pg)
            check("%s ping %s" % (n, dst), bool(m) and int(m.group(1)) >= 60, "no reply" if not m or int(m.group(1)) < 60 else "")
    say("\nPC TESTS")
    for name, ip, gw in PCS:
        nm, mask, g, raw = vpcs_show(cons[name])
        check("%s has %s/24 gateway %s" % (name, ip, gw), mask == ip + "/24" and g == gw, "shows IP/MASK=%s GATEWAY=%s" % (mask, g))
    gwres = {}
    for name, ip, gw in PCS:
        got, cnt, out = ping_pc(cons[name], gw, 5)
        gwres[name] = got
        check("%s -> its gateway %s" % (name, gw), got >= 3, "%d of %d replies" % (got, cnt))
    say("  (30 PC-to-PC pings, a few seconds each)")
    mat = {}
    for a, aip, agw in PCS:
        for b, bip, bgw in PCS:
            if a == b:
                continue
            got, cnt, out = ping_pc(cons[a], bip, 5)
            mat[(a, b)] = got
            check("%s -> %s (%s)" % (a, b, bip), got >= 3, "%d of %d replies" % (got, cnt))
    say("\nPING TABLE (replies out of 5; row = from, column = to)")
    say("        " + "".join("%-6s" % b for b, i, g in PCS))
    for a, aip, agw in PCS:
        say("  %-6s" % a + "".join(("%-6s" % ("-" if a == b else "%d/5" % mat.get((a, b), 0))) for b, i, g in PCS))
    say("\nIP TABLE")
    for name, ip, gw in PCS:
        say("  %s  %s/24  gateway %s" % (name, ip, gw))
    for n, p in PLAN.items():
        for ifn, ip, mask, lan in p["ifs"]:
            say("  %s %s  %s %s" % (n, ifn, ip, mask))
    say("\nOSPF RESULTS (raw router output, for the report)")
    for n in PLAN:
        say("--- %s: show ip ospf neighbor" % n)
        say(conns[n].send_command("show ip ospf neighbor").strip())
        say("--- %s: show ip route ospf" % n)
        say(conns[n].send_command("show ip route ospf").strip())
    say("\nTRACE RESULTS (PC console 'trace', one PC per LAN to the other LANs; information only, not a pass/fail test,")
    say("a trace can print * * * on VPCS even when ping works, each is limited to 40 s)")
    for a, b in [("PC1", "PC3"), ("PC1", "PC5"), ("PC3", "PC1"), ("PC3", "PC5"), ("PC5", "PC1"), ("PC5", "PC3")]:
        tip = dict((x, i) for x, i, g in PCS)[b]
        ok, out = vpcs_cmd(cons[a], "trace %s" % tip, 8 if TEST else 40)
        say("--- %s trace to %s (%s)%s" % (a, b, tip, "" if ok else "  [no prompt back within 40 s]"))
        say(out.strip())
    for name, ip, gw in PCS:
        if cons[name].broken:
            fails.append(name + " console not responding after a command")
            say("  [FAIL] %s console did not return to its prompt after Ctrl+C. Not saving anything." % name)
    # ---- 5. save only if everything passed
    if fails:
        say("\n%d check(s) FAILED. NOTHING WAS SAVED and nothing was undone." % len(fails))
        say("The routers and PCs keep the new settings only until they are restarted or the project is closed.")
        say("Send me this whole screen (no passwords are in it).")
    else:
        say("\nAll checks passed. Saving the three routers and six PCs.")
        for n in PLAN:
            c = conns[n]
            o = c.send_command_timing("write memory", read_timeout=60)
            for _ in range(3):
                if "confirm" in o or "Destination filename" in o:
                    o = c.send_command_timing("\n", read_timeout=60)
            if "[OK]" not in o:
                say("%s: save did NOT show [OK]: %s" % (n, o.strip()[-200:]))
                fails.append(n + " save")
                continue
            SAVED_RT.append(n)      # [OK] seen: recorded as saved before the read-back can fail
            rb = c.send_command("show startup-config | include ^router ospf|ip address 10.20")
            ok = rb.count("ip address 10.20") >= len(PLAN[n]["ifs"]) and "router ospf 1" in rb
            say("%s: saved [OK], startup-config read-back %s" % (n, "matches" if ok else "DOES NOT MATCH"))
            if not ok:
                fails.append(n + " readback")
        for name, ip, gw in PCS:
            ok, msg = save_pc(cons[name], name)
            say("  " + ("SAVED. " if ok else "NOT SAVED. ") + msg)
            if ok:
                SAVED_PC.append(name)
            else:
                fails.append(name + " save")
        if fails:
            say("PARTIAL SAVE. Saved routers: %s. Saved PCs: %s. Not saved: %s." % (
                ", ".join(SAVED_RT) or "none", ", ".join(SAVED_PC) or "none",
                ", ".join([n for n in PLAN if n not in SAVED_RT] + [n for n, i, g in PCS if n not in SAVED_PC]) or "none"))
        say("Reopen persistence of the PC startup.vpc files is not tested by this script.")
    for c in conns.values():
        c.disconnect()
    for c in cons.values():
        c.close()
    fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lab3-all-report-%s.txt" % datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    with open(fn, "w") as f:
        f.write("\n".join(RLOG) + "\n")
    say("\nReport saved: " + fn)
    sys.exit(1 if fails else 0)


def run():
    if "--forget" in sys.argv:
        for n, p in PLAN.items():
            kc_del("%s@%s" % (p["user"], p["host"]))
        sys.exit("Removed the saved Keychain passwords for R1, R2 and R3.")
    try:
        main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\nInterrupted by you.")
        code = 2
    except Exception as e:
        print("\nStopped by an error: %s: %s" % (type(e).__name__, str(e).strip().splitlines()[0] if str(e).strip() else ""))
        code = 1
    else:
        return
    finally:
        for c in CONNS:
            try:
                c.disconnect()
            except Exception:
                pass
        for c in PCONS:
            try:
                c.close()
            except Exception:
                pass
    if APPLIED[0]:
        print("Configuration commands had already been sent. The routers and PCs may have PARTIAL new settings.")
        print("Saved before the error: routers %s, PCs %s. Anything else is NOT saved." % (", ".join(SAVED_RT) or "none", ", ".join(SAVED_PC) or "none"))
        print("Send me this screen. Do not run the script again until we look.")
    else:
        print("Nothing was changed (the script stopped during read-only checks).")
    sys.exit(code)


run()
