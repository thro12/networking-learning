# Multi-Area OSPF Lab in GNS3

Seven-router practice lab using OSPF process 10 across Areas 0, 10 and 20. The combined image documents the topology and captured verification output.

## Router IDs and area roles

| Router | Router ID | Area membership | Role |
|---|---|---|---|
| R5 | 1.1.1.1 | 10 | Internal router |
| R4 | 2.2.2.2 | 10 | Internal router |
| R3 | 3.3.3.3 | 0 and 10 | Area Border Router (ABR) |
| R2 | 4.4.4.4 | 0 | Backbone internal router |
| R6 | 5.5.5.5 | 0 and 20 | Area Border Router (ABR) |
| R7 | 6.6.6.6 | 20 | Internal router |
| R8 | 7.7.7.7 | 20 | Internal router |

## Captured results

- PC1 receives ping replies from loopbacks 4.4.4.4, 5.5.5.5, 6.6.6.6 and 7.7.7.7.
- R7's Area 20 database contains router, network and summary LSAs.
- R3's Area 0 database shows Type 1, Type 2 and Type 3 LSAs.
- R3's database summary shows 3 router LSAs, 2 network LSAs and 9 summary LSAs in Area 0, totalling 14.
- R8's captured configuration shows FastEthernet0/0 at 192.168.78.2, loopback 7.7.7.7 and an adjacency with R7 reaching FULL.
- The captured external and ASBR-summary outputs are empty. External-route redistribution is not demonstrated in this evidence.

## What this lab covers

Multi-area topology, router IDs, ABR roles, Type 1/2/3 LSAs, loopback advertisement, adjacency verification and ICMP reachability checks.

These are GNS3 lab results, not a production deployment. The image preserves the original terminal output, including intermediate commands. No complete configuration archive or GNS3 project file is included in this upload.
