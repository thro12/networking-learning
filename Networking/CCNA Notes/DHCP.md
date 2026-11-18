# CCNA Notes - DHCP

*CCNA 200-301 study notes · 19 November 2026*

## 1. The problem DHCP solves

Every device on an IP network needs four things before it can talk: an **IP address**, a **subnet mask**, a **default gateway** and a **DNS server**. Typing these by hand on every PC is slow and error-prone - one typo in a mask breaks connectivity in ways that are painful to debug.

**DHCP (Dynamic Host Configuration Protocol)** hands out these settings automatically: a device plugs in, asks, and receives a ready-made configuration. Home Wi-Fi, office LANs, and the Tungabadra class labs all rely on it.

## 2. How DHCP works - DORA

A new client knows nothing, not even an IP of its own, so it shouts into the network and the server answers. Four messages, remembered as **DORA**:

| Step | Message | Who sends | What it says |
| --- | --- | --- | --- |
| **D** | Discover | Client -> broadcast | "Is any DHCP server out there?" |
| **O** | Offer | Server -> client | "Yes - take 192.168.3.101, mask, gateway, DNS." |
| **R** | Request | Client -> broadcast | "I accept that offer." (Broadcast so other servers stand down.) |
| **A** | Acknowledge | Server -> client | "Confirmed - it's yours until the lease expires." |

Broadcast rules, precisely: during the initial DORA selection, Discover and Request are **broadcast** (the client has no confirmed address or server identity yet); later renewal Requests go unicast - see "The lease" below. Offer and Ack are broadcast only when the client sets the **broadcast flag** - which real clients do, because they cannot receive unicast IP traffic before configuration finishes (RFC 2131).

### The lease

An address is **leased**, not owned. By default the client renews at half the lease time (the **T1 timer**, normally 0.5x the lease; a server may supply a different T1 in option 58), directly with the leasing server; if it leaves the network, the address returns to the pool. A Windows PC shows the whole story with `ipconfig /all` - address, gateway, DNS, which server answered, and lease times.

## 3. Ways to give out addresses

1. **Manual (static) allocation** - admin binds a fixed IP to a specific device. Used for servers and printers that must never move.
2. **Automatic allocation** - first free address is assigned permanently.
3. **Dynamic allocation** - addresses are leased from a pool and reclaimed. The everyday mode.

## 4. DHCP is UDP - ports 67 and 68

DHCP rides on **UDP**: server listens on port **67**, clients use port **68**. UDP because a brand-new client cannot do TCP - it has no IP address yet, and the early messages must travel as broadcasts.

## 5. Lab - a router as the DHCP server

One router (R1) serving one LAN: PC1 gets its address from the pool, Server1 keeps a static address, and the router protects the addresses already in use.

### Address plan

| Device | Interface | IP address | Notes |
| --- | --- | --- | --- |
| R1 | g0/0 | 192.168.3.100 /24 | Gateway for the LAN |
| PC1 | NIC | **from DHCP** (gets .101) | Dynamic |
| Server1 | NIC | 192.168.3.102 (static) | Also the DNS server |

### R1 configuration (from the class lab)

```
hostname DHCP
ip dhcp pool MYPOOL
 network 192.168.3.0 255.255.255.0
 default-router 192.168.3.100
 dns-server 192.168.3.102
ip dhcp excluded-address 192.168.3.100
```

**Expected result:** PC1 requests an address and receives 192.168.3.101 - the first free address in the pool, because .100 is excluded and .102 belongs to Server1. `show ip dhcp binding` on R1 lists the lease; PC1's `ipconfig /all` shows the gateway (.100), the DNS server (.102) and the DHCP server that answered.

### Why the excluded address matters

Without `ip dhcp excluded-address 192.168.3.100`, nothing stops the pool from handing the gateway's own address to a PC. IOS does auto-exclude the router's own interface address in current releases (see Cisco's IOS DHCP server guide), but in the lab we exclude it explicitly - safe on every IOS version and it documents intent.

### Relay - ip helper-address

DHCP Discover is a broadcast, and routers do not forward broadcasts. When the server lives on another network, the LAN router converts the broadcast into a unicast to the server with `ip helper-address <server-ip>` on the client-facing interface.

## 6. Command chart

| Command | Use |
| --- | --- |
| `ip dhcp pool <name>` | Create a DHCP pool |
| `network <net> <mask>` | Addresses the pool hands out |
| `default-router <ip>` | Gateway given to clients |
| `dns-server <ip>` | DNS server(s) given to clients |
| `ip dhcp excluded-address <a> [b]` | Keep addresses out of the pool |
| `ip helper-address <ip>` | Relay DHCP broadcasts to a remote server |
| `show ip dhcp binding` | Leases currently handed out |
| `ipconfig /all` | (Windows) show the received configuration |
| `ipconfig /release` + `/renew` | (Windows) drop and re-request the lease |

## 7. Security quick look

Because DHCP answers whoever asks, an attacker can run a **rogue DHCP server** and hand out a malicious gateway (man-in-the-middle), or flood Discover messages to **exhaust the pool**. Cisco's countermeasure is **DHCP snooping**: switch ports are untrusted by default, only trusted ports (toward the real server) may carry Offer/Ack messages, and the switch builds a binding database of legitimate leases. (Deep dive: CCNP / security track.)

## 8. Interview Q&A

**Q1. What is DHCP and why do we use it?**
A protocol that automatically assigns IP address, subnet mask, default gateway and DNS server to hosts. It removes manual configuration, prevents duplicate-address mistakes, and reclaims addresses from departed devices.

**Q2. Explain the DORA process.**
Discover (client broadcasts to find servers), Offer (server proposes an address and settings), Request (client broadcasts acceptance), Acknowledge (server confirms and starts the lease). The broadcasts belong to the initial selection; renewal Requests are unicast.

**Q3. Which transport protocol and ports does DHCP use?**
UDP - server port 67, client port 68. UDP because a client without an IP address cannot run TCP and must be able to broadcast.

**Q4. A DHCP client and its server are on different subnets. What breaks and how is it fixed?**
Broadcasts do not cross routers, so the Discover never reaches the server. Configure `ip helper-address <server>` on the client-side router interface; it relays DHCP as unicast.

**Q5. Why exclude addresses from a pool?**
So the server never hands out addresses already assigned statically - the gateway, servers, printers. Collisions would take both devices off the network.

**Q6. What is the difference between a reservation and an exclusion?**
An exclusion keeps an address out of the pool entirely (it is configured elsewhere). A reservation (manual allocation) keeps an address inside DHCP but binds it to one specific device.

---
*Sources verified while compiling: RFC 2131 (DHCP: DORA, ports 67/68, broadcast flag) https://www.rfc-editor.org/rfc/rfc2131.html · Cisco IOS DHCP server guide (auto-exclusion of the router's own interface address) https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/ip-addressing/b-ip-addressing/m_config-dhcp-server-xe.html · RFC 3927 (APIPA background) https://www.rfc-editor.org/rfc/rfc3927.html · Cisco "Operate and Troubleshoot DHCP Snooping" (trusted/untrusted ports, binding database) https://www.cisco.com/c/en/us/support/docs/ip/dynamic-host-configuration-protocol-dhcp-dhcpv6/217055-operate-and-troubleshoot-dhcp-snooping.html · Lab addressing and configurations per the Tungabadra Networks class lab. Compiled and reorganized from Tungabadra Networks class material - 19 November 2026.*
