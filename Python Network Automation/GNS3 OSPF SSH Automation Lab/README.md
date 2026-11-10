# GNS3 OSPF Network Automation and Device Data Collection

Python automation for a three-router, six-PC OSPF lab in GNS3. The scripts configure and verify the whole lab over SSH (routers) and console connections (PCs), replacing repetitive manual device setup and checks.

**Status:** Completed (November 2026) - verified working: all 30 directional PC-to-PC ping tests passed 5/5, OSPF neighbours FULL with all routes learned, and traceroutes confirmed full routed reachability (test run 10 Nov 2026, IST).

**Caveat:** router startup-config persistence after a reboot is not yet confirmed (a save-check run is pending). The scripts save with `write memory` / VPCS `save` only when every test passes, but reopening the lab to confirm the saved state has not been done.

## Files
- `lab3-all.py` - the complete one-file lab: read-only preflight checks, prints the plan and asks for confirmation, configures router IPs + OSPF area 0 over SSH (Netmiko), configures the six PC IPs over their console ports, then tests everything: interface status, OSPF neighbours and routes, router pings, PC-to-gateway pings, all 30 PC-to-PC ping directions, and traceroutes. Saves the configuration (write memory / VPCS save) ONLY if every test passes. Router passwords are entered through macOS Keychain prompts (or a hidden terminal prompt where Keychain is unavailable) - this script stores no password in itself and writes none to any file.
- `pcs-lab3.py` - standalone PC configuration and ping verification. No router changes, no passwords.

## Setup requirements
- GNS3 on macOS with 3 Cisco IOS routers, 6 VPCS PCs, and a Cloud node connecting the Mac to the routers' management ports
- A Python virtualenv with `netmiko` and `paramiko` (these routers need legacy SSH key-exchange options)
- SSH users on the routers need privilege 15
- Edit the `PLAN` block at the top of `lab3-all.py` (usernames, management IPs, interfaces) to match your lab. This published copy uses example usernames `r1admin` / `r2admin` / `r3admin`.
