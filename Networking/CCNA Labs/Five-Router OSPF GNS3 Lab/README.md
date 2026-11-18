# Five-Router OSPF GNS3 Lab

**Status:** In progress (18 November 2026)

**Built with:** GNS3 with Cisco IOS routers, configured by hand at the console

Five routers (R1-R5) running OSPF across two areas, built in one evening lab session on 18 November 2026. A four-router area 0 backbone connects to an area 1 stub link through R4, the area border router. The goal of the session was to practise multi-area OSPF: router-IDs, network statements, neighbour adjacencies, and inter-area routing.

## Topology

```
                        area 0 (backbone)
     R1 -------------------------------- R2
     |    192.168.12.0/24                |
     |                                   |
     | 192.168.13.0/24                   | 192.168.24.0/24
     |                                   |
     R3 -------------------------------- R4 -------------- R5
            192.168.34.0/24                     area 1
                                                192.168.45.0/24
```

## Addressing

| Router | Router-ID / Loopback0 | Links |
|--------|----------------------|-------|
| R1 | 1.1.1.1 | Fa0/0 192.168.12.1 (to R2), Gi1/0 192.168.13.1 (to R3) |
| R2 | 2.2.2.2 | Fa0/0 192.168.12.2 (to R1), Gi1/0 192.168.24.1 (to R4) |
| R3 | 3.3.3.3 | Gi0/0 192.168.13.2 (to R1), Fa0/0 192.168.34.1 (to R4) |
| R4 | 4.4.4.4 | Fa0/0 192.168.24.2 (to R2), Gi1/0 192.168.34.2 (to R3), Gi2/0 192.168.45.1 (to R5) |
| R5 | 5.5.5.5 | Fa0/0 192.168.45.2 (to R4) |

Area 0 (the backbone) covers the R1-R2, R1-R3, R2-R4 and R3-R4 links, so R1 and R4 each have two paths through it. Area 1 is the R4-R5 link (192.168.45.0/24). R4 is the area border router.

## Suggested R1 configuration (documented during the session)

```
enable
configure terminal
router ospf 1
 router-id 1.1.1.1
 network 192.168.12.0 0.0.0.255 area 0
 network 192.168.13.0 0.0.0.255 area 0
 network 1.1.1.1 0.0.0.0 area 0
end
write memory
```

How it works: `router ospf 1` starts the OSPF process, and `router-id 1.1.1.1` fixes R1's identity (matching its loopback) so it stays stable across reloads. Each `network` statement selects which interfaces run OSPF and which area they belong to: the two /24 statements cover the backbone links to R2 and R3, and the /32 statement advertises the loopback. Neighbours form only when the other side runs matching OSPF settings (same area, compatible timers), so every router needs the same pattern with its own router-ID, interfaces and networks.

Session screenshots confirm the OSPF process and the 192.168.12.0 network statement were entered and saved on R1; they do not show every suggested line being run. The exact final configurations of R2-R5 were not captured.

## What the session verified, and what is unresolved

**Verified (from session screenshots, 18 November 2026):**

- R1 interfaces up/up: Fa0/0 192.168.12.1 (link to R2), Gi1/0 192.168.13.1 (link to R3), Loopback0 1.1.1.1
- R1's neighbour table shows R3 (3.3.3.3) in FULL state
- The captured portion of R1's routing table carries OSPF-learned routes for the R3, R4 and R5 networks and loopbacks, including the inter-area route (O IA) to 192.168.45.0/24
- R1 pinged R5's 192.168.45.2: 5/5 replies (the first attempt had a typo, a comma instead of a dot; the corrected command succeeded)

**Unresolved:**

- R2 (2.2.2.2) is absent from R1's captured neighbour table; R2-side configuration not yet checked
- Full neighbour and end-to-end verification across all five routers not yet done

**Next steps to finish the lab:** check R2's OSPF configuration (process, router-ID, network statements, area) and interface state, confirm the R1-R2 adjacency reaches FULL, then verify the full neighbour set and end-to-end pings between all five routers.

## Verification commands

Captured in session screenshots: `show ip ospf neighbor`, `show ip ospf interface brief`, `show ip route ospf`, `show ip interface brief`

Suggested during the session but not captured: `show ip ospf`, `show ip ospf database`

## Files

- `Five-Router-OSPF-GNS3-Lab-Session-Notes.pdf` - combined session notes: this topology and addressing, the suggested R1 configuration, the verification results, and the five original session screenshots with captions. Small privacy treatment, disclosed in the PDF: the two GNS3 canvas screenshots had the status/warning bar (local machine path and hostname) cropped off the bottom; topology pixels untouched, console screenshots unmodified. (To be uploaded by the owner, pending.)
- `.gns3` project file - to be uploaded by the owner (pending)
