# Three-Router RIP Network

**Status:** Practice lab (October 2026)
**Built with:** Cisco Packet Tracer

A three-router network running the RIP dynamic routing protocol: instead of typing routes by hand, each router advertises its connected networks and learns the rest from its neighbours.

## What it covers

- RIP configuration on three routers
- Advertising connected networks with network statements
- PCs on the LANs behind the routers for end-to-end testing

## Checks to run

- `show ip route` on each router - RIP-learned routes appear with an R
- Ping between PCs on different LANs, across the routers

## Known fix

- PC5 is on the 10.0.0.0 network but was addressed 20.0.0.3; the correct address is 10.0.0.3 (its subnet mask and gateway were already correct).

## Skills practiced

Dynamic routing with RIP, IP addressing, route verification, connectivity testing.

## File

- [RIP....pkt](../RIP....pkt) - the Packet Tracer project file (kept in the parent CCNA Labs folder with its original name)
