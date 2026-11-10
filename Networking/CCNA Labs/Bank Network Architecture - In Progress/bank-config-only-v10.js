/* Gurutech Project 5 bank network, CONFIG-ONLY v10: run ONCE on the project built by bank-build-only-v9, after devices finished booting. Guard: all 56 required names must exist exactly once (extra Power Distribution Devices are tolerated). SCALED DEMO. No passwords here. No double-slash comments. Not verified end to end. */
var DOMAIN   = "radeon.local";
var BANNER   = "Authorized access only - Radeon Company Ltd, Nairobi";
var FAILS = [];
function note(label, e) { FAILS.push(label + " " + e); }
function dAdd(n, m, x, y) { }
function dMod(n, slot, m) { }
function dLink(a, ai, b, bi, t) { }
function dIos(n, c)              { try { configureIosDevice(n, c); } catch (e) { note("configureIosDevice", n + " ERROR " + e); } }
function dPc(n, d, ip, mk, gw)   { try { configurePcIp(n, d, ip, mk, gw); } catch (e) { note("configurePcIp", n + " ERROR " + e); } }
var SV = [];
function svc(label, fn) { try { SV.push(label + ": " + fn()); } catch (eS) { SV.push(label + ": ERROR " + eS); } }
function proc(dev, name) { return ipc.network().getDevice(dev).getProcess(name); }
function base(host, isRouter) {
  var c = "no ip domain-lookup\nhostname " + host + "\nservice password-encryption\n" +
          "banner motd #" + BANNER + "#\n";
  if (isRouter) { c += "ip domain-name " + DOMAIN + "\nip ssh version 2\n"; }
  return c;
}
var DEPTS = [
  ["MGT",   10, "192.168.10.0",    1, "FLOOR-1-MGT-SW"],
  ["RSC",   20, "192.168.10.64",   1, "FLOOR-1-RSC-SW"],
  ["HR",    30, "192.168.10.128",  1, "FLOOR-1-HR-SW"],
  ["MKT",   40, "192.168.10.192",  2, "FLOOR-2-MKT-SW"],
  ["ACC",   50, "192.168.11.0",    2, "FLOOR-2-ACC-SW"],
  ["FINC",  60, "192.168.11.64",   2, "FLOOR-2-FINANCE-SW"],
  ["LOG",   70, "192.168.11.128",  3, "FLOOR-3-LOG-SW"],
  ["CUST",  80, "192.168.11.192",  3, "FLOOR-3-CUST-SW"],
  ["GST",   90, "192.168.12.0",    3, "FLOOR-3-GST-SW"],
  ["ADMIN", 100, "192.168.12.64",  4, "FLOOR-4-ADMIN-SW"],
  ["ICT",   110, "192.168.12.128", 4, "FLOOR-4-ICT-SW"],
  ["SVR",   120, "192.168.12.192", 4, "FLOOR-4-SVR-SW"]
];
var MASK26 = "255.255.255.192";
var VLANNAME = {MGT:"MANAGEMENT",RSC:"RESEARCH",HR:"HUMAN-RESOURCE",MKT:"MARKETING",ACC:"ACCOUNTS",FINC:"FINANCE",
                LOG:"LOGISTICS",CUST:"CUSTOMER",GST:"GUEST",ADMIN:"ADMIN",ICT:"ICT",SVR:"SERVER-ROOM"};
var ROUTERS = ["FLOOR-1-ROUTER","FLOOR-2-ROUTER","FLOOR-3-ROUTER","FLOOR-4-ROUTER"];
var L3SW    = ["FLOOR-1-L3SW","FLOOR-2-L3SW","FLOOR-3-L3SW","FLOOR-4-L3SW"];
var REQ = ROUTERS.concat(L3SW); for (var rq = 0; rq < DEPTS.length; rq++) { REQ.push(DEPTS[rq][4]); if (DEPTS[rq][0] != "SVR") { REQ.push(DEPTS[rq][0] + "-PC", DEPTS[rq][0] + "-Printer", DEPTS[rq][0] + "-AP"); } } REQ.push("DHCP-SERVER", "EMAIL-SERVER", "HTTPS-SERVER"); var CNTN = {}, totN = ipc.network().getDeviceCount(); for (var gi = 0; gi < totN; gi++) { var gn = ipc.network().getDeviceAt(gi).getName(); CNTN[gn] = (CNTN[gn] || 0) + 1; } var badN = []; for (var gj = 0; gj < REQ.length; gj++) { if (CNTN[REQ[gj]] !== 1) { badN.push(REQ[gj] + "x" + (CNTN[REQ[gj]] || 0)); } } if (REQ.length !== 56 || badN.length > 0) { throw "STOP, nothing was configured. Required names=" + REQ.length + ", not exactly once: " + badN.length + (badN.length ? " first: " + badN.slice(0, 5).join(",") : "") + ". Use File > New, run the build file once, then this file."; }
dAdd("FLOOR-1-ROUTER","2911",1000,150);
dAdd("FLOOR-2-ROUTER","2911",1000,450);
dAdd("FLOOR-3-ROUTER","2911",1350,150);
dAdd("FLOOR-4-ROUTER","2911",1350,450);
for (var r = 0; r < 4; r++) { dMod(ROUTERS[r], "0/2", "HWIC-2T"); }
dAdd("FLOOR-1-L3SW","3650-24PS",750,150);
dAdd("FLOOR-2-L3SW","3650-24PS",750,450);
dAdd("FLOOR-3-L3SW","3650-24PS",1600,150);
dAdd("FLOOR-4-L3SW","3650-24PS",1600,450);
var xs = {1:300, 2:300, 3:1900, 4:1900};
var yBase = {1:50, 2:350, 3:50, 4:350};
var cnt = {1:0, 2:0, 3:0, 4:0};
for (var d = 0; d < DEPTS.length; d++) {
  var D = DEPTS[d], fl = D[3], n = D[0];
  var y = yBase[fl] + cnt[fl] * 110; cnt[fl]++;
  var sx = xs[fl];
  dAdd(D[4], "2960-24TT", sx, y);
  if (n == "SVR") {
    dAdd("DHCP-SERVER", "Server-PT", sx + 150, y + 60);
    dAdd("EMAIL-SERVER","Server-PT", sx + 250, y + 60);
    dAdd("HTTPS-SERVER","Server-PT", sx + 350, y + 60);
  } else {
    dAdd(n + "-PC",      "PC-PT",         sx + 150, y);
    dAdd(n + "-Printer", "Printer-PT",    sx + 250, y);
    dAdd(n + "-AP",      "AccessPoint-PT",sx + 350, y);
  }
}
var used = {};
for (var i = 0; i < 4; i++) { used[L3SW[i]] = 3; }
function nextGig(sw) { var p = "GigabitEthernet1/0/" + used[sw]; used[sw]++; return p; }
for (var k = 0; k < DEPTS.length; k++) {
  var E = DEPTS[k], f = E[3], nm = E[0], sw = E[4];
  var own = L3SW[f - 1];
  var partner = (f == 1) ? L3SW[1] : (f == 2) ? L3SW[0] : (f == 3) ? L3SW[3] : L3SW[2];
  dLink(sw, "FastEthernet0/1", own, nextGig(own), "straight");
  dLink(sw, "FastEthernet0/2", partner, nextGig(partner), "straight");
  if (nm == "SVR") {
    dLink(sw, "FastEthernet0/3", "DHCP-SERVER", "FastEthernet0", "straight");
    dLink(sw, "FastEthernet0/4", "EMAIL-SERVER", "FastEthernet0", "straight");
    dLink(sw, "FastEthernet0/5", "HTTPS-SERVER", "FastEthernet0", "straight");
  } else {
    dLink(sw, "FastEthernet0/3", nm + "-AP", "Port 0", "straight");
    dLink(sw, "FastEthernet0/4", nm + "-Printer", "FastEthernet0", "straight");
    dLink(sw, "FastEthernet0/5", nm + "-PC", "FastEthernet0", "straight");
  }
}
dLink("FLOOR-1-L3SW","GigabitEthernet1/0/1","FLOOR-1-ROUTER","GigabitEthernet0/1","straight");
dLink("FLOOR-1-L3SW","GigabitEthernet1/0/2","FLOOR-2-ROUTER","GigabitEthernet0/1","straight");
dLink("FLOOR-2-L3SW","GigabitEthernet1/0/1","FLOOR-1-ROUTER","GigabitEthernet0/2","straight");
dLink("FLOOR-2-L3SW","GigabitEthernet1/0/2","FLOOR-2-ROUTER","GigabitEthernet0/2","straight");
dLink("FLOOR-3-L3SW","GigabitEthernet1/0/1","FLOOR-3-ROUTER","GigabitEthernet0/1","straight");
dLink("FLOOR-3-L3SW","GigabitEthernet1/0/2","FLOOR-4-ROUTER","GigabitEthernet0/1","straight");
dLink("FLOOR-4-L3SW","GigabitEthernet1/0/1","FLOOR-3-ROUTER","GigabitEthernet0/2","straight");
dLink("FLOOR-4-L3SW","GigabitEthernet1/0/2","FLOOR-4-ROUTER","GigabitEthernet0/2","straight");
dLink("FLOOR-1-ROUTER","Serial0/2/1","FLOOR-2-ROUTER","Serial0/2/0","serial");
dLink("FLOOR-2-ROUTER","Serial0/2/1","FLOOR-4-ROUTER","Serial0/2/0","serial");
dLink("FLOOR-1-ROUTER","Serial0/2/0","FLOOR-3-ROUTER","Serial0/2/0","serial");
dLink("FLOOR-3-ROUTER","Serial0/2/1","FLOOR-4-ROUTER","Serial0/2/1","serial");
dLink("FLOOR-1-ROUTER","GigabitEthernet0/0","FLOOR-4-ROUTER","GigabitEthernet0/0","cross");
dLink("FLOOR-2-ROUTER","GigabitEthernet0/0","FLOOR-3-ROUTER","GigabitEthernet0/0","cross");
function ip30(base, host) { return "10.10.10." + (base + host) + " 255.255.255.252"; }
function net30(base) { return "10.10.10." + base + " 0.0.0.3"; }
dIos("FLOOR-1-ROUTER",
  base("FLOOR-1-ROUTER", true) +
  "interface GigabitEthernet0/1\nip address " + ip30(0,2) + "\nno shutdown\nexit\n" +
  "interface GigabitEthernet0/2\nip address " + ip30(8,2) + "\nno shutdown\nexit\n" +
  "interface Serial0/2/1\nip address " + ip30(16,1) + "\nclock rate 64000\nno shutdown\nexit\n" +
  "interface Serial0/2/0\nip address " + ip30(32,1) + "\nclock rate 64000\nno shutdown\nexit\n" +
  "interface GigabitEthernet0/0\nip address " + ip30(20,1) + "\nno shutdown\nexit\n" +
  "router ospf 1\nrouter-id 1.1.1.1\nnetwork " + net30(0) + " area 0\nnetwork " + net30(8) + " area 0\nnetwork " + net30(16) + " area 0\nnetwork " + net30(32) + " area 0\nnetwork " + net30(20) + " area 0\nexit");
dIos("FLOOR-2-ROUTER",
  base("FLOOR-2-ROUTER", true) +
  "interface GigabitEthernet0/1\nip address " + ip30(4,2) + "\nno shutdown\nexit\n" +
  "interface GigabitEthernet0/2\nip address " + ip30(12,2) + "\nno shutdown\nexit\n" +
  "interface Serial0/2/0\nip address " + ip30(16,2) + "\nno shutdown\nexit\n" +
  "interface Serial0/2/1\nip address " + ip30(24,1) + "\nclock rate 64000\nno shutdown\nexit\n" +
  "interface GigabitEthernet0/0\nip address " + ip30(28,1) + "\nno shutdown\nexit\n" +
  "router ospf 1\nrouter-id 2.2.2.2\nnetwork " + net30(4) + " area 0\nnetwork " + net30(12) + " area 0\nnetwork " + net30(16) + " area 0\nnetwork " + net30(24) + " area 0\nnetwork " + net30(28) + " area 0\nexit");
dIos("FLOOR-3-ROUTER",
  base("FLOOR-3-ROUTER", true) +
  "interface GigabitEthernet0/1\nip address " + ip30(40,2) + "\nno shutdown\nexit\n" +
  "interface GigabitEthernet0/2\nip address " + ip30(48,2) + "\nno shutdown\nexit\n" +
  "interface Serial0/2/0\nip address " + ip30(32,2) + "\nno shutdown\nexit\n" +
  "interface Serial0/2/1\nip address " + ip30(36,1) + "\nclock rate 64000\nno shutdown\nexit\n" +
  "interface GigabitEthernet0/0\nip address " + ip30(28,2) + "\nno shutdown\nexit\n" +
  "router ospf 1\nrouter-id 3.3.3.3\nnetwork " + net30(40) + " area 0\nnetwork " + net30(48) + " area 0\nnetwork " + net30(32) + " area 0\nnetwork " + net30(36) + " area 0\nnetwork " + net30(28) + " area 0\nexit");
dIos("FLOOR-4-ROUTER",
  base("FLOOR-4-ROUTER", true) +
  "interface GigabitEthernet0/1\nip address " + ip30(44,2) + "\nno shutdown\nexit\n" +
  "interface GigabitEthernet0/2\nip address " + ip30(52,2) + "\nno shutdown\nexit\n" +
  "interface Serial0/2/0\nip address " + ip30(24,2) + "\nno shutdown\nexit\n" +
  "interface Serial0/2/1\nip address " + ip30(36,2) + "\nno shutdown\nexit\n" +
  "interface GigabitEthernet0/0\nip address " + ip30(20,2) + "\nno shutdown\nexit\n" +
  "router ospf 1\nrouter-id 4.4.4.4\nnetwork " + net30(44) + " area 0\nnetwork " + net30(52) + " area 0\nnetwork " + net30(24) + " area 0\nnetwork " + net30(36) + " area 0\nnetwork " + net30(20) + " area 0\nexit");
var DHCP_IP = "192.168.12.194", SVR_GW = "192.168.12.193";
function lastOct(s) { return parseInt(s.split(".")[3], 10); }
function gwOf(s) { var p = s.split("."); return p[0] + "." + p[1] + "." + p[2] + "." + (parseInt(p[3], 10) + 1); }
var l3upl = {
  "FLOOR-1-L3SW": [["GigabitEthernet1/0/1", 0, 1], ["GigabitEthernet1/0/2", 4, 1]],
  "FLOOR-2-L3SW": [["GigabitEthernet1/0/1", 8, 1], ["GigabitEthernet1/0/2", 12, 1]],
  "FLOOR-3-L3SW": [["GigabitEthernet1/0/1", 40, 1], ["GigabitEthernet1/0/2", 44, 1]],
  "FLOOR-4-L3SW": [["GigabitEthernet1/0/1", 48, 1], ["GigabitEthernet1/0/2", 52, 1]]
};
for (var s3 = 0; s3 < 4; s3++) {
  var swn = L3SW[s3], fl3 = s3 + 1;
  var c = base(swn, false) + "ip routing\n";
  for (var v = 0; v < DEPTS.length; v++) { c += "vlan " + DEPTS[v][1] + "\nname " + VLANNAME[DEPTS[v][0]] + "\nexit\n"; }
  var ul = l3upl[swn], ospfNets = "";
  for (var u = 0; u < ul.length; u++) {
    c += "interface " + ul[u][0] + "\nno switchport\nip address " + ip30(ul[u][1], ul[u][2]) + "\nno shutdown\nexit\n";
    ospfNets += "network " + net30(ul[u][1]) + " area 0\n";
  }
  for (var g = 3; g < used[swn]; g++) { c += "interface GigabitEthernet1/0/" + g + "\nswitchport mode trunk\nno shutdown\nexit\n"; }
  for (var v2 = 0; v2 < DEPTS.length; v2++) {
    if (DEPTS[v2][3] != fl3) continue;
    var gw = (DEPTS[v2][0] == "SVR") ? SVR_GW : gwOf(DEPTS[v2][2]);
    c += "interface vlan " + DEPTS[v2][1] + "\nip address " + gw + " " + MASK26 + "\n";
    if (DEPTS[v2][0] != "SVR") c += "ip helper-address " + DHCP_IP + "\n";
    c += "no shutdown\nexit\n";
    ospfNets += "network " + DEPTS[v2][2] + " 0.0.0.63 area 0\n";
  }
  c += "router ospf 1\nrouter-id 10.0.0." + fl3 + "\n" + ospfNets + "exit";
  dIos(swn, c);
}
for (var a = 0; a < DEPTS.length; a++) {
  var A = DEPTS[a];
  dIos(A[4],
    base(A[4], false) +
    "vlan " + A[1] + "\nname " + VLANNAME[A[0]] + "\nexit\n" +
    "interface FastEthernet0/3\nswitchport mode access\nswitchport access vlan " + A[1] + "\nexit\n" +
    "interface range FastEthernet0/" + (A[0] == "SVR" ? "3" : "4") + " - 5\nswitchport mode access\nswitchport access vlan " + A[1] + "\nswitchport port-security\nswitchport port-security mac-address sticky\nswitchport port-security violation shutdown\nexit\n" +
    "interface range FastEthernet0/1 - 2\nswitchport mode trunk\nexit");
}
dPc("DHCP-SERVER",  false, "192.168.12.194", MASK26, SVR_GW);
dPc("EMAIL-SERVER", false, "192.168.12.195", MASK26, SVR_GW);
dPc("HTTPS-SERVER", false, "192.168.12.196", MASK26, SVR_GW);
for (var p = 0; p < DEPTS.length; p++) {
  if (DEPTS[p][0] == "SVR") continue;
  dPc(DEPTS[p][0] + "-PC", true);
  svc("printer-dhcp " + DEPTS[p][0], function () { dPc(DEPTS[p][0] + "-Printer", true); return "OK called (not read back)"; });
}
function addPools() {
  var per = proc("DHCP-SERVER", "DhcpServerMain").getDhcpServerProcessByPortName("FastEthernet0");
  per.setEnable(true);
  for (var q = 0; q < DEPTS.length; q++) {
    if (DEPTS[q][0] == "SVR") continue;
    (function (dq) {
      svc("pool " + dq[0], function () {
        var pn = "POOL-" + dq[0], net = dq[2], pr = net.split("."), o = parseInt(pr[3], 10), pre = pr[0] + "." + pr[1] + "." + pr[2] + ".";
        try { per.removePool(pn); } catch (eR) { } per.addPool(pn);
        var pool = per.getPool(pn);
        pool.setNetworkAddress(net);
        pool.setNetworkMask(net, MASK26);
        pool.setDefaultRouter(pre + (o + 1));
        pool.setStartIp(pre + (o + 2));
        pool.setEndIp(pre + (o + 62));
        pool.setMaxUsers(61);
        var good = pool.getNetworkAddress() == net && pool.getSubnetMask() == MASK26 && pool.getDefaultRouter() == pre + (o + 1) &&
                   pool.getStartIp() == pre + (o + 2) && pool.getEndIp() == pre + (o + 62);
        return good ? "OK" : "MISMATCH " + pool.getNetworkAddress() + " " + pool.getSubnetMask() + " " + pool.getDefaultRouter() + " " + pool.getStartIp() + " " + pool.getEndIp();
      });
    })(DEPTS[q]);
  }
}
svc("dhcp server enable+pools", function () { addPools(); return "OK stage finished"; });
svc("http", function () { var h = proc("HTTPS-SERVER", "HttpServer"); h.setEnable(true); return h.isEnabled() ? "OK enabled" : "NOT ENABLED"; });
svc("https", function () { var h = proc("HTTPS-SERVER", "HttpsServer"); h.setEnable(true); return h.isEnabled() ? "OK enabled" : "NOT ENABLED"; });
svc("email-process", function () { var m = proc("EMAIL-SERVER", "EmailServer"); return "OK reachable, accounts=" + m.getAllEmailAcctAsStrings(); });
for (var w = 0; w < DEPTS.length; w++) {
  if (DEPTS[w][0] == "SVR") continue;
  (function (dn) {
    var ssid = dn + "-WIFI";
    svc("ssid " + dn, function () {
      var ws = proc(dn + "-AP", "WirelessServer");
      try { ws.setPort("Port 1"); } catch (ep) { }
      ws.setSsid(ssid);
      var rb = ws.getSsid();
      return (rb == ssid ? "OK " : "MISMATCH ") + rb;
    });
  })(DEPTS[w][0]);
}
var bad = [], good = 0;
for (var f = 0; f < FAILS.length; f++) { SV.push("BUILD " + FAILS[f] + " ERROR"); }
for (var z = 0; z < SV.length; z++) { if (SV[z].indexOf(": OK") >= 0 && SV[z].indexOf("ERROR") < 0 && SV[z].indexOf("MISMATCH") < 0) { good++; } else { bad.push(SV[z]); } }
try { configureIosDevice("FLOOR-1-ROUTER", "banner exec #SERVICES ok=" + good + " notok=" + bad.length + (bad.length ? " | " + bad.join(" | ") : "") + "#"); } catch (eF) { try { print("SERVICES banner failed: " + eF + " | " + bad.join(" | ")); } catch (eP) { } }
try { print("SERVICES ok=" + good + " notok=" + bad.length + "\n" + bad.join("\n")); } catch (e5) { }
throw "CONFIG DONE. services ok=" + good + " notok=" + bad.length + (bad.length ? " | " + bad.join(" | ") : "");
