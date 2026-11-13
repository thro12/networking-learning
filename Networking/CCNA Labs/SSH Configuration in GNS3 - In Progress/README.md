# SSH Configuration in GNS3 - In Progress

**Status (13 Nov 2026):** SSH from Mac to R1 (HYD) is working and verified. SSH to R2 and R3 is configured but not yet verified on screen.

## Actual lab topology (13 Nov 2026)

Three emulated Cisco IOS routers (GNS3 + dynamips), one management network, and three small LANs. The router model is proven by `show inventory` on R2 (BLR) only:

- **Management:** Cloud1 (`feth1`, the Mac host side) - Switch4 - all three routers
- **R1 - HYD** (Cisco IOS router - model not captured yet)
  - Gi2/0: `172.16.100.11` up/up (management) - SSH target
  - Gi1/0: `10.20.12.1` up/up (transit toward R2; subnet mask not captured)
  - Fa0/0: `10.20.1.1` up/up (LAN via Switch1 - PC1, PC2 on VPCS)
  - All addresses show Method = NVRAM (loaded from startup-config at boot)
- **R2 - BLR** (Cisco 7206VXR, NPE-400)
  - Management: `172.16.100.12` (SSH command issued; login not yet captured)
  - Transit and LAN interfaces shown on the canvas (Gi1/0, Fa0/0, Gi2/0, Gi3/0); IPs not captured yet
- **R3** (SSH user: ramayana) - management IP not captured yet
- LANs: Switch1 - PC1/PC2, Switch2 - PC3/PC4, Switch3 - PC5/PC6 (VPCS)

Config register `0x2102` (normal boot from NVRAM). R2 reports 509K NVRAM and 8192K internal Flash SIMM.

## Working SSH command (Mac terminal)

```
ssh -o KexAlgorithms=+diffie-hellman-group14-sha1 -o HostKeyAlgorithms=+ssh-rsa -o Ciphers=+aes128-cbc varanasi@172.16.100.11
```

Why each option is needed - the old IOS image only offers legacy algorithms, and modern OpenSSH disables them by default:

| Option | Reason |
| --- | --- |
| `-o KexAlgorithms=+diffie-hellman-group14-sha1` | Router offers only legacy key exchange |
| `-o HostKeyAlgorithms=+ssh-rsa` | Router host key is RSA/SHA-1, deprecated since OpenSSH 8.8 |
| `-o Ciphers=+aes128-cbc` | Router offers only CBC ciphers; omitting this kills the session with `no matching cipher found. Their offer: aes128-cbc,3des-cbc,aes192-cbc,aes256-cbc` |

Verified: password prompt, successful login, `HYD#` prompt, `show ip interface brief` output over the session.

**Lab-only warning:** these are legacy, weak algorithms. Enabling them per-session is a temporary compatibility workaround for this isolated GNS3 lab, not a recommendation for production. For real devices, upgrade the device SSH stack instead.

## Errors hit during the session, and what they meant

- **VPCS PC2: `en` / `ssh` - "Bad command".** VPCS is a tiny PC simulator (ping, trace, ip, dhcp). It has no privilege mode and no SSH client. SSH must come from the Mac terminal or another router.
- **`sh ip` - "% Incomplete command".** IOS needs the full form: `show ip interface brief` (`sh ip int br`).
- **`dir flash` - "%Error opening disk0:/flash (No such device)".** Nothing broken; IOS looked for a folder named `flash` inside `disk0:`. Correct next step is read-only: `show file systems`, then `dir <name>` with a filesystem that actually exists (the output of `show file systems` is not captured yet).
- **`show environment all`.** PSU/temperature/voltage values come from the emulated image (GNS3 has no physical sensors). Fine for learning the command; they are not the Mac's real readings.
- **`show platform` - "% Invalid input".** Not supported on this IOS/router. Use `show version` and `show inventory` instead (verified working: Cisco 7206VXR 6-slot chassis, NPE-400, port adapters).

## Open items

- Capture successful SSH logins for R2 (`spirit@172.16.100.12`) and R3 (user `ramayana`) with the same three options
- Run `show file systems` on BLR, then the correct `dir` command
- Capture `show ip interface brief` on R2 and R3 to fill in the remaining addresses
- Verify startup-config persistence on R2/R3 (`show startup-config | include ip address`)

## Earlier plan (10 Nov 2026, superseded)

The first version of this lab was a two-router design: HYD `192.168.1.1/24` - BLR `192.168.1.2/24` over Gi1/0, with console-cable login notes and a show-command list. That design was replaced by the three-router build above; the two networks are not the same lab. Kept here for history only.
