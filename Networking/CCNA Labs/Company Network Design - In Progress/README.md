# Company Network Design - In Progress

Gurutech Networks case study (Project 6): a three-floor company network in Cisco Packet
Tracer. Five departments of about 120 users each plus a server room, two core switches,
two edge routers, and two ISPs (ISP1 main, ISP2 backup). Built 13 November 2026.

## Files

- `REPORT.md` - the full report in text form: design, IP plan, VLANs, DHCP, OSPF, NAT,
  security, honest test results, and interview Q&A. This is the complete content.
- `Project6-Company-Network-Report-and-Interview-Guide.pdf` - **to be uploaded** (the
  same report as a formatted PDF).
- `topology.jpg` - **to be uploaded** (the build in Packet Tracer).
- `evidence/` - **to be uploaded** (the actual test screenshots - passes and failures,
  nothing edited).
- `Project 6 - Company Network Design.pkt` - **to be uploaded** (the Packet Tracer file
  will be added here).

Text files are published now; the PDF, images and .pkt will be uploaded to this folder.

## Test status (14 November 2026)

Working and confirmed by screenshots: OSPF neighbours and full route table on CORE-1,
DHCP leases to PCs, the HR path through CORE-2, and pings to ISP2's test address 9.9.9.9.

Open issue: pings to ISP1's test address 8.8.8.8 fail - traces stop right after the edge
router. Under investigation; the route correction (ISP1 main, ISP2 backup) has been sent
to both edge routers and is awaiting on-router verification.

The full, honest list - confirmed, failed, and not-yet-tested - is in Section 11 of REPORT.md (and of the PDF once uploaded).

## Notes

- Lab passwords follow the case study and are deliberately not published in this repo.
- The DHCP pools do not hand out a DNS server yet (a known limitation; the DNS server
  at 172.16.3.131 exists in the server room).
