# RR-2-PEER IP Detection Logic

## Overview

The script needs to find the RR-2-PEER IP addresses from B06 and B07 devices to use in BD0 EVPN queries.

## Cross-Reference Method

The RR-2-PEER IPs are found using **iBGP-TO-** neighbor descriptions with **cross-referencing**:

### B07's RR-2-PEER IP
- **Where to find**: In the Neighbors sheet from B07 device
- **Look for**: Description that starts with `iBGP-TO-` and ends with a hostname containing `B06`
- **Example**: 
  ```
  Device: NWCSDEBGB07
  Description: iBGP-TO-NWCSDEBGB06
  Neighbor IP: 10.1.1.10  ← This is B06's RR-2-PEER
  ```

### B06's RR-2-PEER IP
- **Where to find**: In the Neighbors sheet from B06 device
- **Look for**: Description that starts with `iBGP-TO-` and ends with a hostname containing `B07`
- **Example**:
  ```
  Device: NWCSDEBGB06
  Description: iBGP-TO-NWCSDEBGB07
  Neighbor IP: 10.1.1.20  ← This is B07's RR-2-PEER
  ```

## Visual Explanation

```
┌─────────────────────────────────────────────────────────────┐
│ B07 Device (NWCSDEBGB07)                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Neighbor: iBGP-TO-NWCSDEBGB06                             │
│  IP: 10.1.1.10  ──────────┐                                │
│                           │                                 │
└───────────────────────────┼─────────────────────────────────┘
                            │
                            │ This IP is used as:
                            │ B06_RR2_PEER_IP
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ BD0 Commands Using This IP:                                 │
│                                                             │
│  show bgp l2vpn evpn rd 10.1.1.10:1 | i prefixes           │
│  show bgp l2vpn evpn rd 10.1.1.10:2 | i prefixes           │
│  show bgp l2vpn evpn rd 10.1.1.10:3 | i prefixes           │
│                                                             │
│  Descriptions: RAN/EDN/WSN routes from B06                  │
└─────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│ B06 Device (NWCSDEBGB06)                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Neighbor: iBGP-TO-NWCSDEBGB07                             │
│  IP: 10.1.1.20  ──────────┐                                │
│                           │                                 │
└───────────────────────────┼─────────────────────────────────┘
                            │
                            │ This IP is used as:
                            │ B07_RR2_PEER_IP
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ BD0 Commands Using This IP:                                 │
│                                                             │
│  show bgp l2vpn evpn rd 10.1.1.20:1 | i prefixes           │
│  show bgp l2vpn evpn rd 10.1.1.20:2 | i prefixes           │
│  show bgp l2vpn evpn rd 10.1.1.20:3 | i prefixes           │
│                                                             │
│  Descriptions: RAN/EDN/WSN routes from B07                  │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Logic

### Step-by-Step Process

1. **Query B06 device**:
   - Execute Nokia commands
   - Parse neighbors from config
   - Find neighbor with description starting with `iBGP-TO-`
   - Extract hostname from description (e.g., `iBGP-TO-NWCSDEBGB07` → `NWCSDEBGB07`)
   - If hostname ends with `B07`, store the neighbor IP as **B07_RR2_PEER_IP**

2. **Query B07 device**:
   - Execute Nokia commands
   - Parse neighbors from config
   - Find neighbor with description starting with `iBGP-TO-`
   - Extract hostname from description (e.g., `iBGP-TO-NWCSDEBGB06` → `NWCSDEBGB06`)
   - If hostname ends with `B06`, store the neighbor IP as **B06_RR2_PEER_IP**

3. **Query BD0 device**:
   - Use stored B06_RR2_PEER_IP and B07_RR2_PEER_IP
   - Build 6 EVPN commands (RD :1, :2, :3 for each peer)
   - Execute commands and parse path counts

## Code Example

```python
# Extract neighbors from display-config
neighbors = extract_neighbors(display_output)

for desc, ip_addr in neighbors:
    # Check for iBGP-TO- descriptions
    if desc.startswith("iBGP-TO-"):
        # Extract peer hostname
        peer_hostname = desc.replace("iBGP-TO-", "").strip()
        
        # On B06 device, find iBGP-TO-<B07> for B07's RR-2-PEER
        if peer_hostname.endswith("B07") and "B06" in device['hostname']:
            b07_rr2_peer_ip = ip_addr
            print(f"Found B07 RR-2-PEER: {ip_addr}")
        
        # On B07 device, find iBGP-TO-<B06> for B06's RR-2-PEER
        elif peer_hostname.endswith("B06") and "B07" in device['hostname']:
            b06_rr2_peer_ip = ip_addr
            print(f"Found B06 RR-2-PEER: {ip_addr}")
```

## Example Neighbors Sheet Entries

### B06 Device Neighbors
| Device IP | Neighbor Description | Neighbor IP |
|-----------|---------------------|-------------|
| 2001:4888:a1f:6332::6 | RAN_EBGP_MSE_V4 | 10.1.2.1 |
| 2001:4888:a1f:6332::6 | EDN_EBGP_MSE_V6 | 2001::1 |
| 2001:4888:a1f:6332::6 | **iBGP-TO-NWCSDEBGB07** | **10.1.1.20** ← B07's RR-2-PEER |

### B07 Device Neighbors
| Device IP | Neighbor Description | Neighbor IP |
|-----------|---------------------|-------------|
| 2001:4888:a1f:6332::7 | RAN_EBGP_MSE_V4 | 10.1.2.2 |
| 2001:4888:a1f:6332::7 | EDN_EBGP_MSE_V6 | 2001::2 |
| 2001:4888:a1f:6332::7 | **iBGP-TO-NWCSDEBGB06** | **10.1.1.10** ← B06's RR-2-PEER |

## Why Cross-Reference?

The iBGP peering is **bidirectional**:
- B06 peers with B07 (B06 has iBGP-TO-B07 neighbor)
- B07 peers with B06 (B07 has iBGP-TO-B06 neighbor)

When we want to query **routes from B06**, we use **B06's router ID** (which is its RR-2-PEER IP).
This IP is found in **B07's neighbor list** as the iBGP peer pointing to B06.

Similarly, when we want to query **routes from B07**, we use **B07's router ID** (its RR-2-PEER IP).
This IP is found in **B06's neighbor list** as the iBGP peer pointing to B07.

## Troubleshooting

### If B06_RR2_PEER_IP is not found:
- ✅ Check that B06 device has been processed
- ✅ Check that B06 has an iBGP-TO- neighbor with hostname ending in B07
- ✅ Verify the description format is exactly: `iBGP-TO-<hostname>`

### If B07_RR2_PEER_IP is not found:
- ✅ Check that B07 device has been processed
- ✅ Check that B07 has an iBGP-TO- neighbor with hostname ending in B06
- ✅ Verify the description format is exactly: `iBGP-TO-<hostname>`

### Debug Commands:
```python
# Check Neighbors sheet for iBGP-TO- entries
python3 << EOF
from openpyxl import load_workbook
wb = load_workbook('network_inputs.xlsx')
ws = wb['Neighbors']
print("iBGP-TO- Neighbors:")
for row in ws.iter_rows(min_row=2, values_only=True):
    if row and row[1] and str(row[1]).startswith("iBGP-TO-"):
        print(f"  Device: {row[0]}")
        print(f"  Description: {row[1]}")
        print(f"  Neighbor IP: {row[2]}")
        print()
EOF
```

## Summary

✅ **B07's RR-2-PEER** = IP of `iBGP-TO-<B06_hostname>` neighbor on B07 device  
✅ **B06's RR-2-PEER** = IP of `iBGP-TO-<B07_hostname>` neighbor on B06 device  
✅ These IPs are then used as Route Distinguisher prefixes in BD0 EVPN queries  
✅ Cross-referencing ensures we get the correct router IDs for each device  
