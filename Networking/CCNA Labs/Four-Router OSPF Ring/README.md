# Four-Router OSPF Ring

**Status:** Practice lab (October 2026)
**Built with:** Cisco Packet Tracer

Four routers connected in a ring, all running OSPF in a single area (area 0), so the routers share their networks automatically and always have two possible paths around the ring.

## What it covers

- OSPF configuration on four routers in area 0
- Network statements matching each router's interfaces
- Ring topology, so every router has a backup path if one link fails

## Checks to run

- `show ip ospf neighbor` - each router should list its two ring neighbours
- `show ip route` - OSPF-learned routes appear with an O
- Ping across the ring between devices on opposite sides

## Skills practiced

OSPF single-area configuration, link-state routing basics, neighbour and route verification.

## File

- [OSPF....pkt](../OSPF....pkt) - the Packet Tracer project file (kept in the parent CCNA Labs folder with its original name)
