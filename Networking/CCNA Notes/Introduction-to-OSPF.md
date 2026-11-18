# CCNA Notes - Introduction to OSPF

*CCNA 200-301 study notes · 19 November 2026*

## 1. Why dynamic routing exists

Static routing works - until the network grows. Every route needs the destination network, mask and next hop typed by hand on every router. A provider like Airtel runs thousands of routers across India; nobody can maintain that by hand, and every link change would mean manual edits everywhere.

**Dynamic routing protocols** solve this: you advertise your local networks once, and the routers learn the rest from each other automatically.

## 2. What a dynamic routing protocol does

1. Discovers neighboring routers on its interfaces.
2. Exchanges the routes each router knows.
3. Runs an algorithm to pick the best path to every destination.
4. Installs the best paths in the routing table.
5. Detects topology changes (link up/down) and recalculates.

| Advantages | Disadvantages |
| --- | --- |
| Adapts to topology changes by itself; far less administrative work than static routes; less error-prone; scales to large networks. | Harder to configure correctly than static routes; costs router CPU and RAM to run. |

## 3. EGP vs IGP - the two families

An **Autonomous System (AS)** is a set of routers under one administration - one company's network. Airtel, Jio, Tata and Google each run their own AS, identified by an **AS number (ASN)**.

- **IGP (Interior Gateway Protocol)** - routing **inside** one AS. Examples: RIP, EIGRP, OSPF, IS-IS.
- **EGP (Exterior Gateway Protocol)** - routing **between** autonomous systems over the Internet. BGP (a path-vector protocol) is the EGP in use today.

**ASN formats:** the classic 2-byte ASN is a 16-bit number (0-65535); a 4-byte format exists for larger allocations. The 16-bit ranges, per the IANA registry:

| 16-bit ASN range | Use |
| --- | --- |
| 0 | Reserved (RFC 7607) |
| 1 - 64495 | Public allocations - with one exception: **23456 is reserved as AS_TRANS** (RFC 6793) |
| 64496 - 64511 | Reserved for documentation and sample code (RFC 5398) |
| 64512 - 65534 | Reserved for private use (RFC 6996) |
| 65535 | Reserved (RFC 7300) |

**Correction vs class handout:** the source material gives "public 1-64511, private 64512-65535". The IANA registry is more precise - the table above corrects and replaces that line.

## 4. Inside the IGP family

| Type | Protocols | How it thinks |
| --- | --- | --- |
| Distance vector | RIP, IGRP | "Routing by rumor": each router trusts what neighbors tell it. RIP's metric is hop count; IGRP uses a composite of bandwidth, delay, reliability and load. |
| Advanced distance vector | EIGRP | Cisco's improved distance vector with faster convergence and a composite metric (bandwidth, delay, reliability, load). |
| Link-state | OSPF, IS-IS | Every router builds a complete map of the area and computes shortest paths itself (cost metric). |
| Path vector (EGP) | BGP | Tracks the full AS path; used between organizations/ISPs. |

OSPF and IS-IS use the same link-state approach; IS-IS is also common in service providers. These notes cover OSPF.

## 5. OSPF - Open Shortest Path First

- **Link-state protocol:** every OSPF router in an area holds the same complete topology map (the **link-state database**) - every router and every link.
- **Dijkstra SPF algorithm:** each router independently runs Shortest Path First over that map to compute the best route to every destination.
- **Triggered updates:** OSPF floods an update as soon as something changes (a link up/down), instead of periodically re-broadcasting whole tables like distance-vector protocols. OSPF is not entirely "event-only", though: every router also re-originates each LSA it owns every **30 minutes** (LSRefreshTime, RFC 2328) as a background refresh.
- **Areas:** large OSPF networks are split into areas to keep databases small. Area 0 is the backbone; all other areas connect to it. A router sitting on the border between areas is an **ABR (Area Border Router)**; routes learned from another area show as **O IA** (inter-area) in the routing table.
- **Router-ID:** each router's OSPF identity - a 32-bit number chosen at startup from the configured `router-id`, else the highest loopback IP, else the highest active physical interface IP.
- **AD 110:** OSPF routes show as **O** in the routing table. OSPF runs directly over IP protocol 89, using multicast 224.0.0.5 (all OSPF routers) and 224.0.0.6 (the DR/BDR).
- **Metric = cost:** derived from interface bandwidth (default reference 100 Mbps, so a 100-Mbps link costs 1); the lowest total path cost wins.

**Neighbors, timers and the DR/BDR**

Routers discover each other with **Hello packets** and declare a neighbor down after the **dead interval** without Hellos. The defaults depend on link type: on Cisco routers the hello interval is **10 s on Ethernet (broadcast / point-to-point)** and **30 s on nonbroadcast (NBMA) networks**, and the dead interval defaults to 4x hello (40 s / 120 s). RFC 2328 likewise lists 10 s as the sample value for a LAN and 30 s for an X.25 packet-data network.

On a shared multi-access network (e.g. Ethernet with many routers), routers elect a **Designated Router (DR)** and **Backup DR**: everyone else syncs only with the DR/BDR (updates to 224.0.0.6, DR floods to 224.0.0.5) instead of forming adjacencies with every peer. Election: highest interface **priority** (default 1; 0 = never DR), ties broken by highest Router-ID. The election is **nonpreemptive**: those rules only decide at election time - a router that joins later with a higher priority does not unseat an active DR, it wins only at the next election (for example after the current DR fails and the BDR takes over).

## 6. Configuring OSPF - the syntax explained

```
Router(config)# router ospf <process-id>
Router(config-router)# network <address> <wildcard-mask> area <area-id>
```

| Field | Meaning |
| --- | --- |
| `process-id` | Locally significant number identifying the OSPF process on this router. It does not have to match between routers. |
| `address` + `wildcard mask` | Selects which of the router's interfaces run OSPF. The wildcard mask is the inverse of a subnet mask: 255.255.255.0 becomes 0.0.0.255, and 255.255.255.255 becomes 0.0.0.0. |
| `area-id` | The area those interfaces belong to. Every router inside one area shares the same link-state database. |

**Wildcard examples:**

- `network 192.168.12.0 0.0.0.255 area 0` -> every interface in 192.168.12.0/24 runs OSPF in area 0
- `network 1.1.1.1 0.0.0.0 area 0` -> exactly the interface with address 1.1.1.1 (the /32 loopback)

## 7. Lab - two areas, three routers

R1 lives entirely in **area 0**, R3 entirely in **area 10**, and **R2 is the ABR** with one link in each area. Full configurations, as documented in the class material:

**R1 (area 0)**

```
interface loopback0
 ip address 1.1.1.1 255.255.255.255
interface g1/0
 ip address 192.168.12.1 255.255.255.0
 no shutdown
router ospf 110
 network 1.1.1.1 0.0.0.0 area 0
 network 192.168.12.0 0.0.0.255 area 0
```

**R2 (area 0 + ABR for area 10)**

```
interface loopback0
 ip address 2.2.2.2 255.255.255.255
interface g1/0
 ip address 192.168.12.2 255.255.255.0
 no shutdown
interface g2/0
 ip address 192.168.23.2 255.255.255.0
 no shutdown
router ospf 110
 network 2.2.2.2 0.0.0.0 area 0
 network 192.168.12.0 0.0.0.255 area 0
 network 192.168.23.0 0.0.0.255 area 10
```

**R3 (area 10)**

```
interface loopback0
 ip address 3.3.3.3 255.255.255.255
interface g2/0
 ip address 192.168.23.3 255.255.255.0
 no shutdown
router ospf 110
 network 3.3.3.3 0.0.0.0 area 10
 network 192.168.23.0 0.0.0.255 area 10
```

**Verification (expected results of this configuration)**

```
! Reachability across the area boundary, from R1:
ping 3.3.3.3
traceroute 3.3.3.3

! Who are my OSPF neighbors? (R1 sees R2; R2 sees R1 and R3; R3 sees R2)
show ip ospf neighbor

! The routing table: OSPF routes marked O (AD 110);
! routes coming from the other area marked O IA
show ip route
```

Once the neighbor adjacencies reach FULL, R1 can ping R3's loopback - routes learned dynamically across the area boundary, with no static routes anywhere.

**These are the expected outcomes of the documented configuration.** The class material demonstrates them with captured router output; this rewritten walkthrough was not re-executed here, so results are stated as intended behavior, not observed output. (One stray line in the source mentions pinging 4.4.4.4; the lab contains no such address - 3.3.3.3 is the target everywhere else, so that is treated as a typo.)

## 8. Command chart

| Command | Use |
| --- | --- |
| `router ospf <process-id>` | Start the OSPF process (process-id is locally significant) |
| `network <addr> <wildcard> area <id>` | Choose which interfaces run OSPF and in which area |
| `router-id <a.b.c.d>` | Fix the router's OSPF identity (usually a loopback) |
| `ip ospf priority <0-255>` | Interface DR election priority (0 = never DR) |
| `show ip ospf neighbor` | Discovered neighbors and their state (FULL = adjacent) |
| `show ip ospf interface brief` | Which interfaces run OSPF, and their areas |
| `show ip route` | Routing table - O and O IA mark OSPF-learned routes |
| `show ip ospf` | Process details: router-ID, areas, SPF runs |
| `show ip ospf database` | The link-state database the SPF map is built from |

## 9. Interview Q&A

**Q1. Why do we need dynamic routing protocols when static routes work?**
Static routes must be typed by hand on every router and updated manually after every change - unworkable on a large network. Dynamic protocols discover neighbors, exchange routes, pick best paths with an algorithm and react to link failures automatically, at the cost of some router CPU and RAM.

**Q2. What is the difference between an IGP and an EGP?**
An IGP routes inside one autonomous system - one organization's network - for example OSPF, EIGRP, RIP or IS-IS. An EGP routes between autonomous systems across the Internet; BGP is today's EGP. Each organization runs its own AS, identified by an AS number (public, private 64512-65534, or reserved ranges per the IANA registry).

**Q3. What kind of protocol is OSPF?**
OSPF is a link-state IGP. Every router in an area builds the same complete topology map (the link-state database), then runs Dijkstra's SPF algorithm on it to compute the shortest path to each destination. Updates are flooded when something changes rather than as full periodic re-broadcasts - though each LSA is still refreshed every 30 minutes - and OSPF routes carry AD 110.

**Q4. What are OSPF areas and why area 0?**
Areas divide a large OSPF network so each router only keeps the detailed map of its own area, keeping databases and SPF calculations small. Area 0 is the backbone that all other areas attach to; a router connecting area 0 to another area is an Area Border Router (ABR). Routes learned from another area appear as O IA in the routing table.

**Q5. Explain the OSPF network statement and the wildcard mask.**
Under `router ospf <process-id>`, the command `network <address> <wildcard> area <id>` selects which interfaces run OSPF and assigns them to an area. The wildcard mask is the inverse of the subnet mask: a /24 network uses 0.0.0.255, and a single host address uses 0.0.0.0. The process-id is locally significant - it need not match between routers.

**Q6. How do OSPF routers learn routes?**
Routers first discover neighbors on OSPF-enabled interfaces (Hello packets; Cisco defaults are 10 s hello / 40 s dead on Ethernet, 30/120 on NBMA) and form adjacencies - target state FULL in `show ip ospf neighbor`, with a DR/BDR elected on shared networks. They exchange link-state information until every router in the area holds the same database, and each one runs SPF to compute and install the best routes, marked O (or O IA for other areas) in the routing table.

---
*Sources verified while compiling: RFC 2328 (OSPFv2 - LSRefreshTime 30 min, AllSPFRouters/AllDRouters 224.0.0.5/6, timer sample values) https://www.rfc-editor.org/rfc/rfc2328.html · IANA AS Number registry https://www.iana.org/assignments/as-numbers/as-numbers.xhtml · RFC 6793 (AS_TRANS 23456) https://www.rfc-editor.org/rfc/rfc6793.html · Cisco IOS OSPF command reference - ip ospf hello-interval defaults https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/iproute_ospf/command/iro-cr-book/ospf-i1.html · Cisco "Understand Administrative Distance" https://www.cisco.com/c/en/us/support/docs/ip/border-gateway-protocol-bgp/15986-admin-distance.html · Cisco "An Introduction to IGRP" https://www.cisco.com/c/en/us/support/docs/ip/interior-gateway-routing-protocol-igrp/26825-5.html · Compiled and reorganized from Tungabadra Networks class material - 19 November 2026.*
