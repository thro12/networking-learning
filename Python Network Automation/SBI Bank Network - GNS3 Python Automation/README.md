# SBI Bank Network - GNS3 Python Automation (In Progress)

One Python script builds this entire GNS3 lab from an empty project: it places and cables four Cisco c7200 routers, a switch and a VPCS PC, uploads the full router startup configurations, then runs staged verification checks. No manual device placement or cabling.

**Status: in progress.** DHCP reservation, primary-path pings and PAT were verified live on 17 November 2026. The verification run then stopped at a traceroute check, so the controlled backup-path test and the final configuration save are not yet verified.

Intended environment: local GNS3 2.2 (developed against 2.2.61), a c7200 Dynamips template, the built-in Ethernet switch, VPCS, and Python standard library only. Cisco IOS image files are user-supplied and are not redistributed here.

## Topology

| Device | Role | Interfaces |
| --- | --- | --- |
| R1 | Bank edge router: LAN gateway, DHCP server, PAT | Gi1/0 192.168.1.100/24 (LAN), Gi2/0 192.168.14.1/24 (to R4), Gi3/0 192.168.15.1/24 (to R5) |
| R3 | Simulated Internet target | Lo0 8.8.8.8/32, Gi1/0 192.168.34.3/24 (to R4), Gi2/0 192.168.35.3/24 (to R5) |
| R4 | Airtel ISP, primary path | Gi1/0 192.168.34.4/24, Gi2/0 192.168.14.4/24 |
| R5 | TATA ISP, backup path | Gi1/0 192.168.35.5/24, Gi2/0 192.168.15.5/24 |
| Switch1 | Built-in Ethernet switch | e1 to R1, e0 to PC1 |
| PC1 | Bank client (VPCS) | DHCP reservation 192.168.1.1/24, gateway 192.168.1.100 |

8.8.8.8/32 is a loopback on R3. It simulates an Internet target; it is not the real Internet.

## Network design

- Static default routing on R1: primary via Airtel (192.168.14.4, AD 10), floating backup via TATA (192.168.15.5, AD 20).
- PAT on R1: access-list 10 permits the LAN (192.168.1.0/24); inside global is the Airtel-side address 192.168.14.1.
- DHCP pool `SBI-Bank` on R1: network 192.168.1.0/24, default-router 192.168.1.100, excluded addresses 192.168.1.100-192.168.1.102, DNS options 192.168.1.101/.102 as placeholders (no DNS servers in the lab).
- DHCP reservation pool `PC1-RESERVATION`: host 192.168.1.1/24 bound to PC1's client identifier, so PC1 always receives the exact diagram address.
- Return routing: R3 carries routes back to the LAN via both ISPs (AD 10/20) plus the transit networks; R4 and R5 carry a host route to 8.8.8.8 via R3 and a LAN return route via R1.
- Canvas annotations mark the simulation boundaries: "8.8.8.8/32 is R3 Loopback0 - NOT real Internet" and "Static default: Airtel AD10 primary / TATA AD20 backup".

## What the automation does

- Python standard library only. Runs against the local GNS3 server (127.0.0.1:3080).
- Creates a separate new project and refuses any change outside it; existing projects and shared templates are untouched.
- Reads the local GNS3 login from the user's own saved GNS3 settings without displaying or transmitting it.
- Places nodes, cables links, uploads per-router startup configs, adds canvas annotations, then stages checks: exact DHCP lease, default-route/CEF forwarding check, measured pings, PAT translation readback, a controlled backup-path failover test (one interface shutdown), and `write memory` on all four routers. Configurations are backed up before later stages; a failure restores and stops instead of assuming success.

## Verified live results (17 November 2026)

- R1 and R3 booted and took their configurations (console logs captured during the run).
- PC1 received exactly 192.168.1.1/24 with gateway 192.168.1.100 through the DHCP reservation.
- PC1 pinged the gateway and the simulated 8.8.8.8: 5/5 replies (ttl=253).
- PAT confirmed: R1's NAT translation table showed PC1's 192.168.1.1 translated to inside global 192.168.14.1 (the Airtel-side address), matching the primary path.
- These results are from that evening's run. They have not been rechecked since; PC1's console later became unavailable during the session.

## Where the run stopped

- The traceroute measured check failed: the trace reached R4 then R3, but the final hop returned ICMP port-unreachable, and the script treats any unexpected reply as a failure ("STOPPED ... No success assumed"). This was a verification stop, not proof of a lab fault.
- A corrected finish script (fixed forwarding-path parsing) was delivered afterwards, but its final full-run results were never received, so the controlled backup-path test and final save stay unverified.
- Code QA status (18 November 2026): the builder passes 20 standalone offline tests, one of which exercises the full 30-check mocked workflow (run: `python3 test_static_builder.py gns3_static_default_builder.py`). A project-specific finish script passed 4 mock tests during internal QA. All of these are mocked/socket-level tests with simulated device replies, not live GNS3 proof. This exact builder revision has not been rerun from scratch on the live lab, and no final run record proves the full check workflow completed. During review only reporting text changed: the script no longer prints a success-sounding final state when save/readback checks fail. No device commands, addressing or workflow behavior changed.

## Evidence

- `topology.png` - labeled project canvas (pending upload).
- `evidence-primary-path-pat.jpg` - PC1 pings, NAT translation table and the traceroute stop (pending upload).
- Full per-device console logs and check records were saved on the lab machine during the run.

## Project file

Upload pending: the `.gns3` project file will be added to this folder by the owner.

## Boundaries

- The backup test shuts the local primary interface and probes new flows. It is not upstream failure detection, IP SLA tracking or session-preserving failover.
- The builder creates a fresh project on each run. Do not rerun blindly after a failure; preserve the project's report folder and inspect the error.
- Router numbering R1/R3/R4/R5 follows the reference design; there is no R2.
- The finish script is project-specific, not a general-purpose recovery tool.
- The private WAN uses 192.168.x.x addressing despite the provider labels.

## Source code

- `gns3_static_default_builder.py` - fresh-lab builder (SHA-256 d7d05c1dd0e2e8d88081f27831bba2f955cc320ad1eaf751e47e09de5314e08e).
- `test_static_builder.py` - standalone offline test suite; run with `python3 test_static_builder.py gns3_static_default_builder.py`.
- A project-specific finish/check script also exists; it depends on the original lab's saved state and is not published as a portable tool.
