# EIGRP Four-Router Ring

**Status:** Practice lab (October 2026)
**Built with:** Cisco Packet Tracer

Four routers in a ring with two end LANs, running EIGRP in autonomous system 100 so routes are shared dynamically between all routers.

## What it covers

- EIGRP configuration with AS number 100 on four routers
- Advertising connected networks with network statements
- Two LANs for end-to-end connectivity testing

## Checks to run

- `show ip eigrp neighbors` - each router lists its ring neighbours
- `show ip route` - EIGRP-learned routes appear with a D
- Ping between PCs on the two LANs

## Skills practiced

EIGRP configuration, autonomous systems, dynamic route verification.

## File

- [EIGRP.pkt](../EIGRP.pkt) - the Packet Tracer project file (kept in the parent CCNA Labs folder with its original name)
