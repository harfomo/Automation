# BD0 EVPN Query Enhancement - Implementation Summary

## What Was Requested

Query a Cisco NXOS device (ending with BD0) for EVPN route information using RR-2-PEER IP addresses collected from B06 and B07 Nokia devices.

## Solution Overview

I've created an **enhanced version** of your original script that:

1. ✅ Processes B06/B07 Nokia devices first
2. ✅ Captures their RR-2-PEER IP addresses
3. ✅ Connects to the BD0 Cisco NXOS device
4. ✅ Runs 6 EVPN commands using the captured IPs
5. ✅ Parses the path counts from the output
6. ✅ Adds results to the Neighbors sheet

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Query B06 and B07 (Nokia SROS)                      │
│                                                              │
│  B06 Device → Extract RR-2-PEER IP → Store: 10.1.1.10      │
│  B07 Device → Extract RR-2-PEER IP → Store: 10.1.1.20      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Query BD0 (Cisco NXOS)                              │
│                                                              │
│  Command: show bgp l2vpn evpn rd 10.1.1.20:1 | i prefixes  │
│  Output:  Processed 1541 prefixes, 3082 paths              │
│  Extract: 3082 (path count)                                 │
│                                                              │
│  Repeat for all 6 combinations (B06/B07 × RD 1/2/3)        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Add to Excel Neighbors Sheet                        │
│                                                              │
│  Row 1: [BD0_IP, "RAN routes from B07", "10.1.1.20:1",     │
│          "", "", "3082", ""]                                │
│  Row 2: [BD0_IP, "RAN routes from B06", "10.1.1.10:1",     │
│          "", "", "2954", ""]                                │
│  ... (4 more rows for EDN and WSN)                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Commands Executed on BD0

Using the collected RR-2-PEER IPs, the script runs:

| # | Command | Description | RD Meaning |
|---|---------|-------------|------------|
| 1 | `show bgp l2vpn evpn rd <B07_IP>:1 \| i prefixes` | RAN routes from B07 | VPRN 1 = RAN |
| 2 | `show bgp l2vpn evpn rd <B06_IP>:1 \| i prefixes` | RAN routes from B06 | VPRN 1 = RAN |
| 3 | `show bgp l2vpn evpn rd <B07_IP>:2 \| i prefixes` | EDN routes from B07 | VPRN 2 = EDN |
| 4 | `show bgp l2vpn evpn rd <B06_IP>:2 \| i prefixes` | EDN routes from B06 | VPRN 2 = EDN |
| 5 | `show bgp l2vpn evpn rd <B07_IP>:3 \| i prefixes` | WSN routes from B07 | VPRN 3 = WSN |
| 6 | `show bgp l2vpn evpn rd <B06_IP>:3 \| i prefixes` | WSN routes from B06 | VPRN 3 = WSN |

---

## Example Output Parsing

### Command Output:
```
Network          Next Hop        Metric     LocPrf     Weight Path
Route Distinguisher: 10.1.1.20:1
*>i[2]:[0]:[0]:[48]:[0050.7966.6808]:[0]:[0.0.0.0]/216
                 10.1.1.20              100          0 i
*>i[2]:[0]:[0]:[48]:[0050.7966.6809]:[0]:[0.0.0.0]/216
                 10.1.1.20              100          0 i

Processed 1541 prefixes, 3082 paths
```

### Parsed Data:
- **Prefixes**: 1541
- **Paths**: 3082 ← **This value goes into the Excel sheet**

---

## Excel Sheet Structure (Neighbors)

After running the enhanced script, your Neighbors sheet will have these additional rows:

| Device IP | Neighbor Description | Neighbor IP | advRoutes | recvRoutes | **BGP EVPN Prefix (Adv)** | BGP EVPN Prefix (Recv) |
|-----------|---------------------|-------------|-----------|------------|-------------------------|------------------------|
| 10.1.1.1  | RAN routes from B07 | 10.1.1.20:1 |           |            | **3082**                |                        |
| 10.1.1.1  | RAN routes from B06 | 10.1.1.10:1 |           |            | **2954**                |                        |
| 10.1.1.1  | EDN routes from B07 | 10.1.1.20:2 |           |            | **4123**                |                        |
| 10.1.1.1  | EDN routes from B06 | 10.1.1.10:2 |           |            | **3876**                |                        |
| 10.1.1.1  | WSN routes from B07 | 10.1.1.20:3 |           |            | **5234**                |                        |
| 10.1.1.1  | WSN routes from B06 | 10.1.1.10:3 |           |            | **4987**                |                        |

The **path count** is placed in the "BGP EVPN IPv4/IPv6 Prefix (Adv)" column as requested.

---

## Key Implementation Details

### 1. RR-2-PEER IP Collection
```python
# During B06/B07 processing - using iBGP-TO- cross-reference
if desc.startswith("iBGP-TO-"):
    peer_hostname = desc.replace("iBGP-TO-", "").strip()
    
    # B06's RR-2-PEER = iBGP-TO-<B07> found on B06 device
    if peer_hostname.endswith("B07") and "B06" in device['hostname']:
        b07_rr2_peer_ip = ip_addr
    
    # B07's RR-2-PEER = iBGP-TO-<B06> found on B07 device  
    elif peer_hostname.endswith("B06") and "B07" in device['hostname']:
        b06_rr2_peer_ip = ip_addr
```

### 2. BD0 Device Detection
```python
# During device processing
if "BD0" in device['hostname']:
    bd0_device = device
```

### 3. EVPN Query and Parse
```python
cmd = f"show bgp l2vpn evpn rd {b07_rr2_peer_ip}:1 | i prefixes"
output = connection.send_command(cmd)

# Parse: "Processed 1541 prefixes, 3082 paths"
match = re.search(r'Processed\s+(\d+)\s+prefixes?,\s+(\d+)\s+paths?', output)
if match:
    path_count = match.group(2)  # 3082
```

### 4. Add to Excel
```python
neighbors_ws.append([
    bd0_device["ip"],      # BD0 device IP
    "RAN routes from B07",  # Description
    f"{b07_rr2_peer_ip}:1", # RD value
    "",                     # advRoutes (empty)
    "",                     # recvRoutes (empty)
    path_count,            # BGP EVPN Prefix (Adv) ← THE PATH COUNT
    ""                      # BGP EVPN Prefix (Recv) (empty)
])
```

---

## How to Run

### If you haven't run the original script yet:
```bash
python3 network_audit_enhanced.py
```

### If you already have the Excel file with B06/B07 data:
```bash
python3 query_bd0_evpn.py
```

---

## Prerequisites

1. **Excel File** (`network_inputs.xlsx`) with devices:
   - At least one device with "B06" in hostname (Nokia)
   - At least one device with "B07" in hostname (Nokia)
   - At least one device with "BD0" in hostname (Cisco NXOS)

2. **Python Packages**:
   ```bash
   pip install netmiko openpyxl
   ```

3. **Network Access**:
   - SSH connectivity to all devices
   - TACACS credentials (embedded in script)

---

## Error Handling

The script includes robust error handling:

✅ **Missing B06/B07**: Skips BD0 queries with warning  
✅ **Missing BD0**: Skips EVPN queries with warning  
✅ **Connection failures**: Logged to `failed_connections.log`  
✅ **Parse errors**: Marked as "PARSE_ERROR" in Excel  
✅ **Command errors**: Marked as "ERROR" in Excel  

---

## Testing Checklist

Before running in production:

- [ ] Verify B06 device has RR-2-PEER configured
- [ ] Verify B07 device has RR-2-PEER configured
- [ ] Test BD0 connectivity
- [ ] Verify EVPN command syntax on your NXOS version
- [ ] Check TACACS credentials are valid
- [ ] Backup existing Excel file if it exists

---

## Files Created

| File | Purpose |
|------|---------|
| `network_audit_enhanced.py` | Complete solution (original + BD0 queries) |
| `query_bd0_evpn.py` | Standalone BD0 query script |
| `README.md` | User documentation |
| `BD0_EVPN_QUERIES.md` | This implementation summary |

---

## Summary

✅ **Enhanced script created**: Combines original functionality + BD0 queries  
✅ **Standalone script created**: For adding BD0 queries to existing data  
✅ **Documentation created**: README and implementation guide  
✅ **Path counts extracted**: From "Processed X prefixes, Y paths" output  
✅ **Excel integration**: Adds 6 rows to Neighbors sheet  
✅ **Error handling**: Comprehensive logging and error markers  

The enhancement is **ready to use** and follows the exact specification provided!
