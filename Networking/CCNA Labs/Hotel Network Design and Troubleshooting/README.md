# Hotel Network Design and Troubleshooting

Three-floor hotel network designed, built and debugged in Cisco Packet Tracer, connecting eight departments with inter-VLAN routing, DHCP and OSPF. Based on Gurutech Networks' Hotel System Network Design (Project #3): https://gurutechnetworks.com/assetsProject/project3

**Status:** Completed (November 2026)

## Design
- Eight departments across three floors, each on its own dedicated VLAN
- Router-on-a-stick inter-VLAN routing
- Per-department DHCP pools
- OSPF routing between floors over serial links
- Wireless access points for Wi-Fi client access
- SSH configured on network devices for secure remote management
- Switch port security enabled on user-facing ports

## Troubleshooting work
Diagnosed and corrected real faults during the build:
- A switch uplink (Fa0/1) that was not trunking, which blocked DHCP requests from reaching the router
- OSPF network statements that did not match the actual serial link addresses, so no OSPF neighbours formed
- An incorrect printer access-VLAN assignment that left a floor printer without DHCP
- Verified client addressing and end-to-end connectivity after each fix

## Tools
Cisco Packet Tracer

## Files
The Packet Tracer project file (.pkt) and topology image will be added here.
