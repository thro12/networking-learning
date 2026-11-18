# CCNA Notes - Static and Default Routing

*CCNA 200-301 study notes · 19 November 2026*

## 1. Why routing exists

Switches move frames **inside** one network. The moment traffic must leave for a **different** network - another floor, another city, the Internet - a **router** has to decide where it goes. That decision is routing, and this note is about the simplest way to make it: telling the router exactly where things are, by hand.

## 2. How a router decides

A router keeps a **routing table**: a list of destination networks and the next hop for each. When a packet arrives, the router looks up the destination, picks the **longest matching prefix**, and forwards the packet out the matching interface. No match and no default route means the packet is dropped.

Route codes in `show ip route`: **C** connected, **S** static, **O** OSPF, **S\*** a static default route.

## 3. Static routes - the syntax explained

```
ip route <destination-network> <subnet-mask> <next-hop-ip | exit-interface> [AD]
```

| Field | Meaning |
| --- | --- |
| `destination-network` + `mask` | The remote network being described. |
| `next-hop-ip` | The neighboring router's address that can reach it. |
| `exit-interface` | Alternative: send it out one of the router's own interfaces (common on point-to-point links). |
| `[AD]` | Optional administrative distance - the lever behind floating static routes. |

Every router needs a route to every destination **and** the return path needs routes too - a very common lab mistake is configuring only one direction.

## 4. Default routes - the route of last resort

```
ip route 0.0.0.0 0.0.0.0 <next-hop>
```

`0.0.0.0/0` matches **everything**, so it is used only when no more specific route exists. Instead of dropping unknown traffic, the router forwards it to the default next hop. This is how branch routers reach the Internet without knowing every network on Earth: one default route pointing at the ISP.

## 5. Administrative distance - who wins

A router may learn the same destination from several sources. **Administrative distance (AD)** is the trust ranking - **lower wins**:

| Source | AD |
| --- | --- |
| Connected | 0 |
| Static | 1 |
| eBGP | 20 |
| EIGRP | 90 |
| IGRP | 100 |
| OSPF | 110 |
| IS-IS | 115 |
| RIP | 120 |
| Unknown | 255 (never used) |

Then **metric** breaks ties *within* one protocol (AD decides between protocols, metric decides inside one), and the **longest prefix match** has the final word at forwarding time.

## 6. Floating static routes - the backup that waits

Give a static route a **worse AD** than the primary route and it stays out of the table while the primary is healthy, then appears when the primary fails:

```
ip route 0.0.0.0 0.0.0.0 192.168.14.4 10    ! via Airtel, AD 10
ip route 0.0.0.0 0.0.0.0 192.168.15.5 20    ! via Tata,   AD 20 (floating backup)
```

## 7. Lab - branch office with two ISPs (static + default + floating backup)

R1 serves the branch LAN (192.168.1.0/24) and reaches the Internet through two ISPs: Airtel as primary, Tata as backup. The Google router (loopback 8.8.8.8/32) stands in for the Internet. R1 is also the LAN's DHCP server (its hostname in the lab is literally DHCP). Note this lab's pool lives on 192.168.1.0/24 - a different subnet from the standalone 192.168.3.0/24 lab in the DHCP notes; the configuration below is self-contained, not copied from there.

### Address plan (from the class lab)

| Link / device | Network or address |
| --- | --- |
| Branch LAN | 192.168.1.0/24 (gateway R1 g0/0 = 192.168.1.100) |
| R1 <-> R4 "Airtel" | 192.168.14.0/24 (R1 .1, R4 .4) |
| R1 <-> R5 "Tata" | 192.168.15.0/24 (R1 .1, R5 .5) |
| R4 <-> R3 "Google" | 192.168.34.0/24 (R4 .4, R3 .3) |
| R5 <-> R3 "Google" | 192.168.35.0/24 (R5 .5, R3 .3) |
| R3 loopback | 8.8.8.8/32 |

### Key configuration

```
! R1 - default routes toward both ISPs, Airtel preferred:
ip route 0.0.0.0 0.0.0.0 192.168.14.4 10   ! via Airtel,  AD 10
ip route 0.0.0.0 0.0.0.0 192.168.15.5 20   ! via Tata,    AD 20 (floating backup)

! R4 (Airtel) - reach Google, and the way back to the LAN:
ip route 8.8.8.8 255.255.255.255 192.168.34.3
ip route 192.168.1.0 255.255.255.0 192.168.14.1

! R5 (Tata) - same pattern on the backup side:
ip route 8.8.8.8 255.255.255.255 192.168.35.3
ip route 192.168.1.0 255.255.255.0 192.168.15.1

! R3 (Google) - return paths to the branch, floating statics,
! plus routes to the two R4-R3 / R5-R3 transit networks:
ip route 192.168.1.0 255.255.255.0 192.168.34.4 10
ip route 192.168.1.0 255.255.255.0 192.168.35.5 20
ip route 192.168.14.0 255.255.255.0 192.168.34.4
ip route 192.168.15.0 255.255.255.0 192.168.35.5
```

### R1 as the LAN's DHCP server (from the same lab)

```
hostname DHCP
ip dhcp excluded-address 192.168.1.101 192.168.1.102
ip dhcp pool DHCP
 network 192.168.1.0 255.255.255.0
 default-router 192.168.1.100
 dns-server 192.168.1.101 192.168.1.102
```

**Source correction:** the class handout omits the exclusion line; without it the pool could lease the two DNS server addresses (.101, .102) to clients. Added here, matching the standalone DHCP lab's exclusion practice. The gateway .100 needs no line - IOS auto-excludes the router's own interface address.

**What actually sits in the routing tables:** on both R1 and R3, only the AD 10 route is installed; the AD 20 floating static waits in the configuration until the primary route's interface goes down. "Two routes configured" is not "two routes in the table".

### Case study 1 - normal operation

A PC pings 8.8.8.8. R1's installed default route points to Airtel (AD 10), so traffic flows R1 -> Airtel -> Google, and Google's replies follow its installed route back through Airtel.

### Case study 2 - failover, and its limits

Shut R1's Airtel-facing interface. R1's AD 10 default route leaves the table, the AD 20 route via Tata is installed, and **outbound** traffic now leaves through Tata. That is the failover this lab demonstrates.

**Read this before claiming end-to-end failover:** whether replies come back depends on *where the break is*. Shutting R1's Airtel-facing interface withdraws only R1's primary route. R3 keeps its AD 10 route via Airtel as long as its own link to R4 is up - nothing on R3 notices the change - so replies reach R4, which has no working path to the LAN, and are dropped: a blackhole. The mirror image also holds: a break of only the R3-R4 link withdraws R3's primary route but leaves R1's installed, and outbound traffic blackholes at R4 instead. Full bidirectional failover needs **both ends to withdraw their primary routes** - in this topology that is a combined failure such as a complete R4 outage, which brings down the R1-R4 and R3-R4 links together. Production designs solve the single-edge case with IP SLA object tracking (or a dynamic protocol) so the dead path is detected at both ends. Treat the lab's ping success as the intended demonstration of the combined-failure case, not proof that every failure scenario converges.

**Real-world note:** actual ISPs run BGP toward the Internet; static/default routes are the branch-office side of the design. Default and static routes both carry AD 1 by default - here the administrator overrode it (10/20) to build the failover.

## 8. Command chart

| Command | Use |
| --- | --- |
| `ip route <net> <mask> <next-hop>` | Add a static route |
| `ip route 0.0.0.0 0.0.0.0 <next-hop>` | Add a default route (gateway of last resort) |
| `ip route <net> <mask> <next-hop> <AD>` | Static route with custom AD (floating backup) |
| `interface loopback<N>` | Create a logical interface with no physical dependency |
| `show ip route` | View the routing table (S = static, C = connected, O = OSPF...) |
| `show ip interface brief` | Interface IPs and up/down state at a glance |
| `show version` | Platform, IOS version, uptime, config register |
| `ping` / `traceroute <ip>` | Verify reachability and the path taken |
| `write memory` (or `copy run start`) | Save the configuration |

## 9. Interview Q&A

**Q1. What is the purpose of routing protocols?**
Routing protocols let routers learn remote networks automatically and pick the best paths, instead of an administrator typing every route by hand. Without them, a router knows only its connected networks plus any static routes configured manually. Real-world example: a call between an Airtel user and a Jio user works because BGP connects the two providers' networks.

**Q2. What is administrative distance (AD)?**
AD is the trustworthiness of a route source: when two different sources offer the same prefix, the lower AD is installed in the routing table. Key values: connected 0, static 1, eBGP 20, EIGRP 90, IGRP 100, OSPF 110, IS-IS 115, RIP 120, BGP 200.

**Q3. How does the route selection process work?**
Two stages. First the table is built: between different sources of the same prefix the lowest AD wins, and inside one protocol the lowest metric wins. Then forwarding: for each packet the router picks the longest prefix match among installed routes. So a /32 learned from OSPF forwards traffic even against a static /24, while the same /24 from static (AD 1) beats OSPF (AD 110) for a place in the table.

**Q4. What is a default route?**
The default route (0.0.0.0/0) is used when no specific route matches the destination - instead of dropping the packet, the router forwards it to the default next hop. It keeps routing tables small and is the standard way to point a branch router at its ISP: `ip route 0.0.0.0 0.0.0.0 10.0.0.1`.

**Q5. Static routing - advantages and disadvantages?**
Static routes are configured by hand: `ip route <net> <mask> <next-hop>`, AD 1. Advantages: simple, no protocol overhead on CPU/RAM or bandwidth, and fully predictable paths - good for small organizations. Disadvantages: manual and time-consuming, and the router cannot detect a failed remote path on its own, and a backup link is used only if a floating static (or tracking) was pre-configured.

**Q6. How do you configure a static route?**
Use `ip route` followed by destination network, mask and next-hop IP (or exit interface), e.g. `ip route 8.8.8.8 255.255.255.255 10.0.0.2`. In the routing table it appears as `S 8.8.8.8/32 [1/0] via 10.0.0.2`: S for static, AD 1, metric 0, next hop 10.0.0.2. An optional AD at the end turns it into a floating backup route.

---
*Sources verified while compiling: Cisco "Understand Administrative Distance" (AD values incl. IS-IS 115) https://www.cisco.com/c/en/us/support/docs/ip/border-gateway-protocol-bgp/15986-admin-distance.html · Cisco "BGP Best Path Selection Algorithm" https://www.cisco.com/c/en/us/support/docs/ip/border-gateway-protocol-bgp/13753-25.html · Cisco "An Introduction to IGRP" (composite metric) https://www.cisco.com/c/en/us/support/docs/ip/interior-gateway-routing-protocol-igrp/26825-5.html · Lab addressing and configurations per the Tungabadra Networks class lab. Compiled and reorganized from Tungabadra Networks class material - 19 November 2026.*
