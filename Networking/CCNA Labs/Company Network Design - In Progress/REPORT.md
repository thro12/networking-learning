# Project 6 - Company Network Design

Study notes and interview prep • Gurutech Networks case study • Built 13 November 2026 • test results updated 14 November 2026

## 1\. What this project is

A three-floor company network in Cisco Packet Tracer. Five departments of about 120 users each (600 staff in total) plus a server room, with two internet providers for backup (ISP1 main, ISP2 backup). The network is built and configured in Packet Tracer with scripts, and live testing is under way - Section 11 shows exactly what passed, what failed, and what is still untested.


**Confirmed so far (your screenshots, 13-14 Nov):** topology built and labelled. On CORE-1: hostname, banner, login passwords, all three routed uplinks and department gateways (Vlan10/30/50) up/up, all three OSPF neighbours FULL, and its route table shows the three remote department routes learned from CORE-2 via OSPF plus a default toward EDGE-R1. A Sales PC received a correct DHCP lease, and pings to ISP2's test address 9.9.9.9 get replies (2 of 4 packets per run).



**Open issue:** pings to ISP1's test address 8.8.8.8 fail even after the route correction - pings from two PCs time out and a trace stops right after the edge router. **Not yet tested:** spanning-tree state, SSH logins, pings between departments, DNS resolution, and failover. Section 11 has the full, honest list.


## 2\. Topology

**(Topology screenshot: to be uploaded as `topology.jpg` - described in text below and visible in the PDF once uploaded.)**

Your build in Packet Tracer - five departments plus the server room grouped by colour, two core switches in the middle, two edge routers and two ISPs below. (The screenshot viewport clips the outer department groups at the edges.) The build is scaled down to fit: one PC, one printer and one access point per department stand in for the 120 users, and three servers sit in the server room. The IP plan keeps the real /25 subnet sizes.

| Device                                | Model                        | Count | Job                                                                            |
| ------------------------------------- | ---------------------------- | ----- | ------------------------------------------------------------------------------ |
| ISP1, ISP2                            | Cisco 2911 router            | 2     | Internet providers (loopbacks 8.8.8.8 and 9.9.9.9 stand in for internet sites) |
| EDGE-R1, EDGE-R2                      | Cisco 2911 router            | 2     | Company edge: NAT, default routes, OSPF                                        |
| CORE-1, CORE-2                        | Cisco 3650 multilayer switch | 2     | Department gateways (SVIs), inter-VLAN routing, OSPF                           |
| One per department                    | Cisco 2960 switch            | 6     | Access switches for user ports, two uplinks each                               |
| PCs, printers, access points, servers | End devices                  | 18    | Users (DHCP) and servers (static)                                              |

## 3\. IP addressing plan

Base network `172.16.0.0/16`. Each user department gets a **/25** (126 usable addresses - smallest block that fits 120 users). The server room gets a **/28** (14 usable). Point-to-point links use /30s.

| Department                   | VLAN | Network         | Gateway (SVI)          | Addresses given out                   |
| ---------------------------- | ---- | --------------- | ---------------------- | ------------------------------------- |
| Sales & Marketing (floor 1)  | 10   | 172.16.1.0/25   | 172.16.1.1 on CORE-1   | DHCP .10 - .126 (117 leases)          |
| HR & Logistics (floor 1)     | 20   | 172.16.1.128/25 | 172.16.1.129 on CORE-2 | DHCP .138 - .254 (117 leases)         |
| Finance & Accounts (floor 2) | 30   | 172.16.2.0/25   | 172.16.2.1 on CORE-1   | DHCP .10 - .126 (117 leases)          |
| Admin & PR (floor 2)         | 40   | 172.16.2.128/25 | 172.16.2.129 on CORE-2 | DHCP .138 - .254 (117 leases)         |
| ICT (floor 3)                | 50   | 172.16.3.0/25   | 172.16.3.1 on CORE-1   | DHCP .10 - .126 (117 leases)          |
| Server Room (floor 3)        | 60   | 172.16.3.128/28 | 172.16.3.129 on CORE-2 | Static - servers keep fixed addresses |

| Point-to-point link      | Network          | Side A        | Side B        |
| ------------------------ | ---------------- | ------------- | ------------- |
| EDGE-R1 - ISP1           | 195.136.17.0/30  | 195.136.17.2  | 195.136.17.1  |
| EDGE-R1 - ISP2           | 195.136.17.4/30  | 195.136.17.6  | 195.136.17.5  |
| EDGE-R2 - ISP1           | 195.136.17.8/30  | 195.136.17.10 | 195.136.17.9  |
| EDGE-R2 - ISP2           | 195.136.17.12/30 | 195.136.17.14 | 195.136.17.13 |
| EDGE-R1 - CORE-1         | 10.10.10.0/30    | 10.10.10.2    | 10.10.10.1    |
| EDGE-R2 - CORE-1         | 10.10.10.4/30    | 10.10.10.6    | 10.10.10.5    |
| EDGE-R1 - CORE-2         | 10.10.10.8/30    | 10.10.10.10   | 10.10.10.9    |
| EDGE-R2 - CORE-2         | 10.10.10.12/30   | 10.10.10.14   | 10.10.10.13   |
| CORE-1 - CORE-2 (routed) | 10.10.10.16/30   | 10.10.10.17   | 10.10.10.18   |


**Capacity note:** a /25 holds 126 usable addresses, but after the gateway the pools hand out 117 leases and infrastructure devices share the subnet - so a full 120-user department needs the pool widened first. Room to grow exists at network level: most of 172.16.0.0/16 is still free.


## 4\. VLANs and trunking (access layer)


**Analogy:** a VLAN is a room in the building. People in the Sales room can shout (broadcast) without disturbing Finance. A **trunk** is the corridor between floors - it carries every room's traffic with a tag saying which room it belongs to (the 802.1Q tag).


Each department switch puts its user ports in that department's VLAN and its two uplinks in trunk mode:

    vlan 30
     name FINANCE-ACCOUNTS
    interface FastEthernet0/3
     switchport mode access
     switchport access vlan 30
    interface range FastEthernet0/4 - 5
     switchport mode access
     switchport access vlan 30
    interface range FastEthernet0/1 - 2
     switchport mode trunk

## 5\. Inter-VLAN routing (the core switches)


**Analogy:** the multilayer switch is the reception desk that knows every room's phone number. A device leaving its room addresses the message to "reception" (its default gateway), and reception forwards it.


VLANs cannot talk to each other directly - a Layer-3 device must route between them. Each core holds the gateway for its departments as an SVI (one virtual interface per VLAN), with routing on:

    ip routing
    interface vlan 10
     ip address 172.16.1.1 255.255.255.128
     ip helper-address 172.16.3.130
     no shutdown

The uplinks to the edge routers and the CORE-1 to CORE-2 link are routed ports (`no switchport`) with /30 addresses. The downlinks to the access switches are trunks.

## 6\. DHCP from the server room

One DHCP server (172.16.3.130, static) holds one pool per user department: network, mask, gateway, and a lease range of .10 to .126 - 117 leases. Keeping .2 to .9 free leaves room for static devices like printers.


**Analogy:** DHCP is the front desk handing out visitor badges. A new laptop shouts "any badges free?" - but shouts (broadcasts) cannot leave the room. The receptionist (`ip helper-address` on the SVI) carries the request to the badge office and posts the badge back.


## 7\. Routing with OSPF

Both edge routers and both core switches run OSPF in area 0, so every internal device learns every subnet automatically. Each edge router is configured with a static default route toward ISP1 as the main path, plus a floating static default toward ISP2 at administrative distance 10 as the backup - a correction sent to both edge routers on 14 November, not yet verified on the routers, after testing showed the original equal-cost pair sent ISP1-bound traffic to ISP2, which has no path to it. The edge routers share their default route with `default-information originate`, so the whole company gets a way to the internet. Router IDs are set by hand (edges 1.1.1.1 / 2.2.2.2, cores 10.0.0.1 / 10.0.0.2) to keep the topology predictable.

    router ospf 1
     router-id 10.0.0.1
     network 172.16.1.0 0.0.0.127 area 0
     network 10.10.10.0 0.0.0.3 area 0

## 8\. NAT overload (PAT) on the edge routers

Private 172.16.x.x addresses cannot cross the internet. Both edge routers run NAT overload: ACL 1 matches the whole 172.16.0.0/16 range, and each private source is rewritten to the public address of the outgoing serial link.

    access-list 1 permit 172.16.0.0 0.0.255.255
    interface GigabitEthernet0/0
     ip nat inside
    interface Serial0/2/0
     ip nat outside
    ip nat inside source list 1 interface Serial0/2/0 overload


**Analogy:** an apartment building has one street address. The receptionist keeps a notebook of which flat sent which parcel, so replies come back to the right flat. For web traffic the notebook tracks port numbers; for ping (ICMP, no ports) it tracks the ICMP identifier instead. The notebook is the translation table - `show ip nat translations` is the proof PAT is working, not a ping alone.


## 9\. Security

  - **Passwords:** a console password and an enable secret are set on every device (the exact values come from the case study and are kept out of this public document) - they must be replaced before any real network.
  - **SSH version 2 only** on both edge routers and both core switches: domain name, 1024-bit RSA keys, a local admin user, and vty lines set to `login local` + `transport input ssh` - Telnet is refused, so management passwords never cross the network in clear text. The case study asks for it on all routers and Layer-3 switches, so adding the ISP routers is a noted extension.
  - **Finance port-security:** maximum one MAC address per port, learned with the sticky method, violation mode shutdown - an unknown device disables the port until an admin re-enables it.
  - **Banner and housekeeping:** MOTD warning banner, `no ip domain-lookup`, passwords scrambled in the config with `service password-encryption`.


## 10\. Redundancy - and the loop it creates

The brief demands redundancy at every layer: two ISPs (ISP1 main, ISP2 backup through floating static routes), two edge routers, two core switches, and two uplinks from every access switch. If one ISP, router, core or uplink fails, a physical path still remains. That is not complete service redundancy though - each department's gateway SVI lives on one core and there is a single DHCP server, so gateway and service failover (HSRP, a second DHCP scope) remain open improvements. Failover has not been tested in this build.



**The loop question.** Dual uplinks plus default settings DO create a real layer-2 ring, hiding in the default VLAN: every switch has VLAN 1, every trunk carries VLAN 1 (the script does not restrict allowed VLANs), and every access switch connects to both cores - so a ring like CORE-1 - access switch A - CORE-2 - access switch B - CORE-1 exists with no inter-core link involved. The routed inter-core link does not remove this loop. What protects the network is Spanning Tree, on by default: it elects a root bridge and blocks redundant ports until no ring remains for that VLAN.


A department VLAN like VLAN 10 is defined only on its own access switch and the two cores (other access switches never create it, and a trunk will not forward a VLAN missing from the local database), so its layer-2 shape is a V, not a ring, and Spanning Tree should leave both of its uplinks forwarding - a design expectation, not a tested result. Checks: `show spanning-tree vlan 10`, `show spanning-tree vlan 1` (blocked ports there are the loop being broken - normal), and `show interfaces trunk`.

## 11\. Test results so far (14 November 2026)

Every "confirmed" below was seen in your own screenshots or CLI output - nothing is assumed or simulated. Testing is paused while the 8.8.8.8 issue is open.


**Expected when testing resumes (not yet observed):** a ping to 8.8.8.8 from any department PC gets replies through ISP1. The backup route is a separate test: with ISP1's link disconnected, traffic should shift to ISP2 on both edge routers - checked by pinging ISP2's own test address 9.9.9.9, because each ISP's test address exists only on that ISP (8.8.8.8 cannot work while ISP1 is down, by design). For the same reason, 9.9.9.9 staying unreachable while ISP1 is up is the lab design, not a fault.


| Check                                                                                        | Result                                                                                                                                                                                                                                                                                          | Evidence / next check                                                                                  |
| -------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Topology, cabling, labels                                                                    | Confirmed                                                                                                                                                                                                                                                                                       | Your screenshots                                                                                       |
| CORE-1 base config, routed uplinks, department gateways (Vlan10/30/50 up/up)                 | Confirmed                                                                                                                                                                                                                                                                                       | CLI screenshot                                                                                         |
| OSPF neighbours on CORE-1 (EDGE-R1, EDGE-R2, CORE-2)                                         | Confirmed - all three FULL                                                                                                                                                                                                                                                                      | CLI screenshot                                                                                         |
| OSPF route table on CORE-1                                                                   | Confirmed - the three remote department routes learned from CORE-2 via OSPF, plus CORE-1's own connected routes and a default toward EDGE-R1                                                                                                                                                    | `show ip route` screenshot                                                                             |
| DHCP lease to a Sales PC (172.16.1.11/25, gateway 172.16.1.1)                                | Confirmed, with one limitation: the pools hand out no DNS server (PC shows 0.0.0.0). The DNS server at 172.16.3.131 exists but is unused so far                                                                                                                                                 | PC screenshot                                                                                          |
| CORE-2 path for HR (gateway 172.16.1.129 answering and forwarding to EDGE-R2)                | Confirmed                                                                                                                                                                                                                                                                                       | tracert screenshot                                                                                     |
| ISP2 test address 9.9.9.9 from a PC                                                          | Partial - two of four packets got replies on each run (50% loss). The replies prove the path works; the lost packets are unexplained                                                                                                                                                            | ping + tracert screenshots                                                                             |
| NAT on EDGE-R1                                                                               | Partly observed - counters show hits and misses, but the translation table was empty when checked and no single flow is proven end to end                                                                                                                                                       | `show ip nat statistics`; next: `show ip nat translations` right after traffic                         |
| Route correction: ISP1 main, ISP2 backup (floating static, distance 10) on both edge routers | Commands sent by script on 14 Nov - not yet verified on the routers                                                                                                                                                                                                                             | Next: `show ip route 0.0.0.0` on EDGE-R1/R2 should list only the ISP1 next-hop                         |
| ISP1 test address 8.8.8.8 from a PC                                                          | **Failing - open issue.** Before the route fix, ISP2 routers answered "destination unreachable" (ISP2 has no path to ISP1's address). After the fix, pings from two PCs (Sales and HR) time out, and a trace from the HR PC stops right after EDGE-R2. The fault location is not yet identified | Next checks: default route and a router-side ping on EDGE-R2, then ISP1's interface and loopback state |
| Spanning Tree state                                                                          | Not yet tested                                                                                                                                                                                                                                                                                  | `show spanning-tree vlan 10`, `show spanning-tree vlan 1`                                              |
| SSH remote login                                                                             | Not yet tested                                                                                                                                                                                                                                                                                  | `ssh -l admin 10.10.10.1` from a PC                                                                    |
| Pings between departments                                                                    | Not yet tested                                                                                                                                                                                                                                                                                  | PC command prompt                                                                                      |
| DNS name resolution from PCs                                                                 | Not yet tested - the pools advertise no DNS server, so a PC needs a manual DNS entry (172.16.3.131) or a pool fix first                                                                                                                                                                         | PC \> Command Prompt \> `nslookup`                                                                     |
| Failover (unplug ISP1, expect backup via ISP2)                                               | Not yet tested                                                                                                                                                                                                                                                                                  | after unplugging ISP1, ping 9.9.9.9 (ISP2's own address - 8.8.8.8 cannot work while ISP1 is down)      |
| CORE-2's other department gateways, trunk detail                                             | Not yet tested                                                                                                                                                                                                                                                                                  | `show ip interface brief`, `show interfaces trunk`                                                     |

## 12\. Traffic flows (what should happen)

**A new PC gets an address:** the PC broadcasts a DHCP request; the SVI's helper address converts it to a unicast to 172.16.3.130; the server answers from the right pool because the relay names the network it came from.

**A PC pings another department:** the PC sees the destination is outside its /25 and sends the packet to its gateway SVI; the core routes it to the destination VLAN's SVI (across the routed inter-core link if the other department lives on the other core); the receiving core delivers it.

**A PC reaches 8.8.8.8:** packet goes to the gateway SVI, follows the OSPF default route to an edge router, whose main default points to ISP1 (the ISP2 default, distance 10, only appears if the ISP1 link fails); PAT rewrites the source to the public serial address, and ISP1 answers from its loopback. The return packet matches the translation-table entry and finds its way back. (What actually happens today is in Section 11.)

## 13\. Interview questions, with answers

### Subnetting and addressing


Q: Walk me through your IP addressing plan.

Base network 172.16.0.0/16. Five user departments get a /25 each (126 usable, smallest fit for 120 users), the server room a /28 (14 usable). Point-to-point links are /30s. Public side is four /30 ranges from the two ISPs: 195.136.17.0/30 through 195.136.17.12/30.



Q: Why /25 and not /24?

A /24 gives 254 usable - more than half would sit unused. /25 is the tightest fit for 120 users. Honest limit: after the gateway, the pools give 117 leases, so a full 120-user department needs the pool widened. Growth room is at network level - most of 172.16.0.0/16 is free.



Q: How do you get 126 usable hosts from a /25?

A /25 leaves 7 host bits. 2^7 = 128 addresses, minus network and broadcast = 126 usable. The formula everywhere: usable = 2^(host bits) - 2.



Q: What is a /30 for?

Exactly two usable addresses - perfect for a point-to-point link with one device at each end. Anything bigger on a router-to-router link wastes addresses.



Q: Why do the servers have static addresses?

Services must stay findable at a known address - the helper-address config points at 172.16.3.130 for DHCP, for example. And a DHCP server cannot lease an address to itself.


### VLANs and switching


Q: What is a VLAN and why bother?

One physical switch divided into separate logical networks - each VLAN is its own broadcast domain. Here it keeps each department's traffic inside its own boundary and lets security rules (like Finance's port-security) apply per department. Analogy: separate rooms instead of one open hall.



Q: Access port vs trunk port?

An access port carries exactly one VLAN and faces an end device. A trunk carries many VLANs between switches, tagging each frame with its VLAN ID (802.1Q). In this build Fa0/3-5 are access ports; Fa0/1-2 are trunks up to the two cores.



Q: How do two VLANs communicate?

They cannot talk directly - a router or Layer-3 switch routes between them. Here the two 3650s do it with SVIs: a virtual 'interface vlan X' holding the department's gateway address, with 'ip routing' enabled. That is inter-VLAN routing.



Q: Each access switch has two uplinks - does that not create a loop?

Yes - in the default VLAN it does: VLAN 1 exists on every switch and every trunk carries it, so rings like CORE-1 - access switch A - CORE-2 - access switch B - CORE-1 exist. Spanning Tree (on by default) blocks redundant ports to break the ring. A department VLAN is a V shape, not a ring, so both its uplinks should forward - but that is an expectation to verify with 'show spanning-tree', not a tested result.


### DHCP


Q: How does a PC reach a DHCP server in a different VLAN?

DHCP discovery is a broadcast, and broadcasts stop at the router. The SVI's 'ip helper-address 172.16.3.130' converts it to a unicast to the server. Because the relay names the network it came from, the server answers from the correct pool.



Q: What does a DHCP pool contain here?

Per department: the network address, the /25 mask, the default router (that department's SVI), the usable range .10 to .126, and a max-users limit of 117.


### Routing and OSPF


Q: Which routing protocol, and why OSPF?

OSPF - a link-state protocol. Every router builds the same complete map and converges quickly when a link fails, which suits a redundant design. It is also what the case study asks for. Single area, area 0, on both edge routers and both cores.



Q: How does the company learn the way to the internet?

Each edge router holds a static default route toward ISP1 (main) and a floating static default toward ISP2 at distance 10 (backup), and injects its default into OSPF with 'default-information originate'. Every internal router then has an OSPF-learned default pointing at an edge router.



Q: What is a router ID?

OSPF's name tag for a router - a 32-bit number written like an IP address. Set manually here: 1.1.1.1 / 2.2.2.2 on the edges, 10.0.0.1 / 10.0.0.2 on the cores. Manual IDs keep the topology predictable.


### NAT and PAT


Q: How do private 172.16.x.x addresses reach the internet?

They do not, directly. The edge routers run NAT overload (PAT): ACL 1 matches 172.16.0.0/16 and each private source is rewritten to the public address of the outgoing serial. Many staff share one public address; the internet never sees the private scheme.



Q: Inside vs outside NAT interfaces?

Inside faces the company (the gigabit links to the cores), outside faces the ISPs (the serial links). Translations happen for traffic crossing from inside to outside.



Q: How do you prove PAT is working?

Generate traffic to an internet address, then 'show ip nat translations' on the edge router - inside-local 172.16.x.x entries mapped to the public address. A ping alone only proves connectivity; the translation table is the proof of PAT.


### Security


Q: How is remote management secured?

SSH version 2 only, on both edge routers and both core switches: a domain name, 1024-bit RSA keys, a local admin user, and vty lines set to 'login local' + 'transport input ssh' - Telnet is refused, so management passwords never cross in clear text. The case study asks for it on all routers and Layer-3 switches, so adding the ISP routers is a noted extension.



Q: Explain the Finance port-security setup.

Maximum one MAC address per port, learned dynamically and saved with the sticky method, violation mode shutdown. If anyone unplugs the Finance PC and connects their own device, the port disables itself until an admin re-enables it.



Q: How do you bring back a port that port-security shut down?

Remove the offending device, then 'shutdown' followed by 'no shutdown' on the interface - and check 'show port-security' to confirm the violation counter and state.


### Redundancy and design thinking


Q: Why two of everything?

The brief demands redundancy at every layer. Two ISPs, two edge routers, two cores, and dual uplinks remove single points of failure from the physical path. That is not complete service redundancy - each department's gateway SVI lives on one core and there is one DHCP server, so HSRP and a second DHCP scope remain open improvements. Failover has not been tested here.



Q: What is the biggest weakness left?

The department gateways are single SVIs on one core each. If CORE-1 fails, Sales, Finance and ICT lose their gateway even though physical paths remain. HSRP between the cores is the fix, and the first thing to add.



Q: What would you add with more time?

HSRP between the cores, EtherChannel on the core interconnect, inter-department ACLs, SSH on the access switches too, centralised logging, and automated config backups.


### Troubleshooting scenarios


Q: A PC in HR cannot get an IP address. Walk me through it.

Bottom-up: PC set to DHCP and link up; Fa0/3-5 in VLAN 20 on the HR switch ('show vlan brief'); trunks up and passing VLAN 20 ('show interfaces trunk'); the HR SVI up with the helper address on CORE-2; the HRL pool configured and DHCP service on; finally, can the core reach 172.16.3.130 at all.



Q: Users ping inside the company but cannot reach 8.8.8.8. Where do you look?

Does the core have a default route ('show ip route' - the OSPF default from the edges); are the edge serials up/up; does ACL 1 cover the user's subnet; are there entries in 'show ip nat translations' after traffic; and can the edge router ping the ISP side of the serial link.



Q: Two departments cannot reach each other. First three checks?

'ip routing' on the core (or cores) that own the two SVIs, those SVIs up/up, and hosts pointing at the correct gateway. Then confirm each department's VLAN is active on its own access switch's trunks - each trunk only needs that one VLAN. If the departments sit on different cores, also check the routed inter-core link and the OSPF neighbourship.


## 14\. How to explain this project in an interview

1.  **Start with the brief:** "A three-floor company, five departments of about 120 users each plus a server room, two ISPs for backup. I designed it in Packet Tracer."
2.  **Walk the topology top-down** on your screenshot: ISPs, edge routers, core switches, access switches, end devices. Point out that everything above the end devices is connected upward twice.
3.  **Addressing:** one /25 per department from 172.16.0.0/16, /28 for the server room, /30s for point-to-point links. Say why /25 (tightest fit for 120).
4.  **Switching:** one VLAN per department, access ports to users, trunks upward; inter-VLAN routing on the two cores with SVIs.
5.  **DHCP:** one server, one pool per department, helper-address on the SVIs carrying the broadcast to it.
6.  **Routing:** OSPF area 0 on both edge routers and both core switches; static defaults on the edges injected with default-information originate.
7.  **Internet:** NAT overload on the edge serials - private to public, many users sharing one public address.
8.  **Security:** SSH v2 on the managed devices, Finance port-security, banners and encrypted passwords.
9.  **Be honest about state and limits:** "The topology is built and the base config is verified on one core; I am validating the rest check by check. The known improvements are HSRP for gateway redundancy and widening the DHCP pools for a full 120-user department."

## 15\. Command chart

| Purpose                      | Command                                | Where                        |
| ---------------------------- | -------------------------------------- | ---------------------------- |
| See all interfaces and IPs   | show ip interface brief                | Routers, core switches       |
| See just the gateways (SVIs) | show ip interface brief | include Vlan | Core switches                |
| See VLANs and member ports   | show vlan brief                        | Access switches              |
| See trunking ports           | show interfaces trunk                  | Access and core switches     |
| See Spanning Tree state      | show spanning-tree vlan 10             | Access and core switches     |
| See OSPF neighbors           | show ip ospf neighbor                  | Routers, core switches       |
| See the routing table        | show ip route                          | Routers, core switches       |
| Prove PAT                    | show ip nat translations               | Edge routers (after traffic) |
| Check port-security          | show port-security                     | Finance access switch        |
| Test remote login            | ssh -l admin \<device-ip\>             | Edge routers, core switches  |
| Test a path                  | ping / tracert                         | Any PC                       |
| Check an address lease       | ipconfig /all                          | Any PC (Command Prompt)      |
