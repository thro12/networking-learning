# CCNA Labs

Hands-on networking labs in Cisco Packet Tracer and GNS3. Each project folder has its own README with the goal, design, configuration notes and checks.

## Projects

| Project | Built with | Status |
| --- | --- | --- |
| [Hotel Network Design and Troubleshooting](./Hotel%20Network%20Design%20and%20Troubleshooting) | Cisco Packet Tracer | Completed (Nov 2026) |
| [Bank Network Architecture - In Progress](./Bank%20Network%20Architecture%20-%20In%20Progress) | Cisco Packet Tracer + PTBuilder (JavaScript) | In progress |
| [Company Network Design - In Progress](./Company%20Network%20Design%20-%20In%20Progress) | Cisco Packet Tracer + PTBuilder (JavaScript) | In progress |
| [Campus Network Design](./Campus%20Network%20Design) | Cisco Packet Tracer | Topology and .pkt uploaded; detailed write-up pending |
| [Lab 1 - Routing Between Two LANs in GNS3](./Lab%201%20-%20Routing%20Between%20Two%20LANs%20in%20GNS3) | GNS3 + VPCS | Completed (Nov 2026) |
| [SSH Configuration in GNS3 - In Progress](./SSH%20Configuration%20in%20GNS3%20-%20In%20Progress) | GNS3 + Cisco IOS | In progress (Nov 2026): router SSH setup being applied, host connectivity test pending |
| [Getting Started - Two-Network Setup](./Getting%20Started%20-%20Two-Network%20Setup) | Cisco Packet Tracer | Practice lab (Oct 2026) |
| [Three-Router RIP Network](./Three-Router%20RIP%20Network) | Cisco Packet Tracer | Practice lab (Oct 2026) |
| [Four-Router Static Routing Network](./Four-Router%20Static%20Routing%20Network) | Cisco Packet Tracer | Practice lab (Oct 2026) |
| [Four-Router OSPF Ring](./Four-Router%20OSPF%20Ring) | Cisco Packet Tracer | Practice lab (Oct 2026) |
| [EIGRP Four-Router Ring](./EIGRP%20Four-Router%20Ring) | Cisco Packet Tracer | Practice lab (Oct 2026) |

Technologies practiced across these labs: VLANs, inter-VLAN routing, DHCP, OSPF, RIP, EIGRP, static routing, SSH device management, port security, wireless, and scripted topology builds with PTBuilder.

## DHCP lab journal - 16 November 2026

Two separate practice environments use the same subnet. They are not one connected network, and 192.168.1.1 has a different role in each.

### GNS3: router-based DHCP

Topology: R1 connects through a hub to five VPCS clients (PC1-PC5). The client screenshots show these leases:

| Client | DHCP address | Subnet mask | Gateway / DHCP server | DNS option |
| --- | --- | --- | --- | --- |
| PC1 | 192.168.1.3 | 255.255.255.0 | 192.168.1.1 | 8.8.8.8 |
| PC2 | 192.168.1.4 | 255.255.255.0 | 192.168.1.1 | 8.8.8.8 |
| PC3 | 192.168.1.5 | 255.255.255.0 | 192.168.1.1 | 8.8.8.8 |
| PC5 | 192.168.1.6 | 255.255.255.0 | 192.168.1.1 | 8.8.8.8 |

PC4 is present in the topology, but its address line was not visible in the captured output. These outputs confirm the displayed DHCP leases and delivered options, not ping success, DNS resolution or internet access. R1's interface configuration has not yet been captured, so the server/gateway address above is recorded from the clients, not asserted from a router configuration dump.

### Cisco Packet Tracer: one server, multiple services

The earlier "Multi-Service Server Network" has one Server-PT, one Cisco 2950T-24 switch and four PCs on 192.168.1.0/24. Server0 is 192.168.1.1/24. It is a server, not a router or a routed exit.

- Saved project evidence: DHCP leases for PC1 (.2), PC2 (.3), PC3 (.4) and PC0 (.5), plus a simulated email exchange and reply. These are stored project records, not a new execution on 16 November.
- Configured services: DHCP, DNS, FTP, SMTP/POP3 email, HTTP/HTTPS, NTP and Syslog. Client-use evidence was recovered for DHCP and email only. Simulation domain names do not imply real Gmail or external DNS integration.
- Open configuration issues: overlapping DHCP pools and a configured range extending outside the /24, including reserved/server addresses. Corrections and retesting are not yet evidenced.

Multiple services on one server, or multiple pools on that server, do not mean multiple DHCP servers. This lab is not evidence of a rogue-server or DHCP-snooping test.

### Next evidence to collect

- Capture R1's DHCP configuration and interface summary before adapting automation to the existing lab. Preserve the current pool and exclusions rather than inventing replacements.
- Record connectivity and DNS tests separately if performed. A DNS address in a lease is not a successful lookup.
- Keep automation marked as an internal, untested-on-real-devices draft until a real run establishes its behavior. Mock results are not lab validation.

The original Packet Tracer file contains saved lab account information and is not attached or copied here. Any shared screenshots must omit passwords and account settings.
