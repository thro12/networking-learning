# SSH Configuration in GNS3 - In Progress

**Status:** In progress (13 November 2026) - SSH is being configured on a two-router GNS3
topology. This note records the work as it happens; the SSH session is not tested yet and no
results are claimed here.

## Topology (as supplied)
Two Cisco IOS routers connected directly:

| Router | Interface | IP address |
| --- | --- | --- |
| HYD | g1/0 | 192.168.1.1/24 |
| BLR | g1/0 | 192.168.1.2/24 |

The hand-edited topology diagram is ready but pending upload - GitHub's web upload of image
files is currently failing, so the diagram will be attached once that route works again.

## Environment
- Mac (Apple M3) running GNS3
- Cisco IOS routers (HYD, BLR)

## Procedure being followed (SSH enablement)
1. `hostname` and `ip domain-name` - both are required before RSA keys can be generated
2. Local user: `username <name> privilege 15 secret <password>`
3. `crypto key generate rsa`
4. vty lines: `line vty 0 4` with `login local` and `transport input ssh`
5. Host test: `ssh <user>@192.168.1.1` (HYD) and `ssh <user>@192.168.1.2` (BLR), with legacy
   algorithm options if the IOS version requires them

No passwords or keys are stored in this repository.

## Reference notes from the lab sheet
Show commands practiced: `show version`, `show inventory`, `show platform`,
`show ip interface brief`, `show environment all`, `dir flash:`, `show processes cpu`.

CLI modes (labels corrected from the lab sheet):
- `R1>` is **user EXEC mode** - where you land on login
- `enable` from user EXEC enters **privileged EXEC mode** (`R1#`)
- `configure terminal` from privileged EXEC enters **global configuration mode** (`R1(config)#`)

Console access from a Windows PC: power on the device, connect the console cable, check the
COM port in Device Manager under Ports (COM & LPT), then open PuTTY and start a serial session
on that COM port.

## Current state
Topology and IP plan are as above. SSH enablement is being applied on the routers; the
host-to-router SSH session has not been tested yet. This file will be updated with the actual
outcome (success, or the exact error) once the test runs.
