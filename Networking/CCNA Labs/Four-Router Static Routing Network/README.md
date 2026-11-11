# Four-Router Static Routing Network

**Status:** Practice lab (October 2026)
**Built with:** Cisco Packet Tracer

A four-router network with eight PCs where every route is typed by hand: static routes tell each router how to reach the networks it is not directly connected to.

## What it covers

- Point-to-point serial links between the four routers
- Static route configuration on each router for every remote network
- Eight PCs across the LANs for end-to-end testing

## Checks to run

- `show ip route` on each router - static routes appear with an S
- Ping from a PC on one edge LAN to a PC on the far edge, across all four routers

## Skills practiced

Static routing, serial point-to-point addressing, next-hop logic, connectivity testing.

## File

- [Static Routing .pkt](../Static%20Routing%20.pkt) - the Packet Tracer project file (kept in the parent CCNA Labs folder with its original name)
