# HDFC Bank Network - Manual GNS3 Static Routing Lab

A five-router bank enterprise topology in GNS3, configured by hand through the router consoles (no automation). Verified outcome (18 November 2026, IST): primary-path connectivity from PC1 to the lab's simulated 8.8.8.8 target - 5/5 ICMP replies - after adding a missing return route on R1.

## Topology (addresses as marked on the diagram)

| Device | Role | Interfaces |
| --- | --- | --- |
| R1 "GOOGLE" | Simulated Internet target | Lo0 8.8.8.8/32, Fa0/0 192.168.21.2 (to R2), Gi1/0 192.168.31.1 (to R3) |
| R2 "AIRTEL" | ISP path 1 | Fa0/0 192.168.21.1, Gi1/0 192.168.42.1 (to R4) |
| R3 "TATA" | ISP path 2 | Gi1/0 192.168.31.2, Fa0/0 192.168.45.1 (to R4) |
| R4 | Bank edge router: LAN gateway | Gi1/0 192.168.42.2, Fa0/0 192.168.45.2, Gi2/0 192.168.1.100 (LAN) |
| R5 | Branch router on the LAN hub | Connected to Hub0; addressing not marked in the diagram |
| Hub0 | LAN hub | e1 to PC1, e2 to R5, uplink to R4 |
| PC1 | Bank client (VPCS) | 192.168.1.1, gateway 192.168.1.100 |

Subnet masks are not marked on the diagram; the session worked with /24 planning. 8.8.8.8 is a loopback on R1, labeled as a simulated Google/Internet target. Only ICMP reachability to that loopback was tested - no DNS lookup and no real Internet access was involved.

## Confirmed by captured evidence

- R1's route table before the fix: connected 8.8.8.8/32 (Loopback0), connected 192.168.21.0/24, a static to 192.168.42.0/24 via 192.168.21.1 - and no route to PC1's LAN 192.168.1.0/24, no default route.
- The fix on R1: `ip route 192.168.1.0 255.255.255.0 192.168.21.1`, with `show ip route 192.168.1.1` readback showing the static entry via 192.168.21.1.
- During diagnosis R2 was checked and already knew the return path to 192.168.1.0/24.
- PC1 `ping 8.8.8.8` after the fix: 5/5 replies, ttl=253. Working path: PC1 -> R4 -> R2 -> R1.
- During diagnosis, R1's Gi1/0 (the R3/TATA side) was administratively down; the successful test used the R2 (Airtel) path only.

## Advised during the session - final state unconfirmed

These steps were worked through in the console, but no captured output confirms their final state, so they are not claimed as measured configuration:

- DHCP pool `HDFC-LAN` on R4, with the gateway and R5's LAN address excluded.
- The full set of static routes on all four routers.
- Earlier in the session a DHCP pool was deleted at the user's request; the final DHCP state of the lab is unknown.
- PC1's final address assignment method (manual vs DHCP) was not established.

## Honest caveats

- TATA-side (R3) forwarding was not verified in this session.
- R5's addressing is not marked in the diagram and R5 was not part of the verified path.
- Configuration persistence is unverified: a `copy running-config startup-config` save was advised right after the successful ping, but the save was not confirmed.
- This lab is separate from the automated SBI bank lab in its own repository/folder. Nothing here was produced by that automation.

## Evidence

- `topology.jpg` - annotated GNS3 canvas (pending upload).
- `evidence-route-fix.jpg` - R1 route table before/after, the added return route and its readback (pending upload).
- `evidence-ping-success.jpg` - PC1's five successful replies from 8.8.8.8 (pending upload).

## Project file

Upload pending: the `.gns3` project file will be added to this folder by the owner.
