# Network Automation Script - Quick Reference Guide

## 🎯 Quick Start

### What This Script Does
Collects BGP, interface, and LAG configuration data from Nokia and Cisco devices into an Excel workbook.

### Files
- **Input**: `network_inputs.xlsx` (Devices sheet)
- **Output**: Same file with Results, Neighbors, Interfaces sheets
- **Log**: `failed_connections.log`

---

## 📝 Device Types Cheat Sheet

### Hostname Pattern → Device Type
```
B06, B07              → nokia_sros_ssh (Primary RR devices)
BD0, BD1, BD2...      → cisco_nxos (Distribution)
BM0, BM1, BM2...      → cisco_nxos (Metro)
B40, B41, B42...      → cisco_nxos (Access)
B01, B02              → cisco_nxos (Aggregation via proxy)
B2C, B2D              → cisco_nxos (Metro via proxy)
cisco_xr              → Must specify in Device_Type column!
```

### Device Roles
```
Primary               → Full data collection
Secondary             → Limited LAG data
Primary/1             → Tab device, LAG only
Secondary/2           → Tab device, Bundle-Ether search
Secondary/3           → Tab device, Bundle-Ether search
```

---

## 🔑 Authentication Cheat Sheet

### Flow
```
1. Try default TACACS credentials (embedded)
2. If fail → Try cached manual credentials
3. If fail → Prompt user (with 2FA support)
4. Cache manual creds for ALL devices
```

### Jump Server
```
Used when Proxy_IP column is filled
- Default jump creds tried first
- Manual prompt if fail
- Credentials cached separately
```

---

## 📊 Output Sheets

### Results Sheet
**Purpose**: Raw command output log  
**Columns**: Device IP | Command | Output

### Neighbors Sheet
**Purpose**: BGP neighbors and route counts  
**Columns**: Hostname | Device IP | Neighbor Description | Neighbor IP | Adv Routes | Recv Routes | EVPN Adv | EVPN Recv

**Special Entries**:
- CPE-check: `WSN_FW_nexthop_*` entries
- RR-2-PEER: `iBGP-TO-*` entries  
- BGP ID: From Cisco B01/B02 devices
- EVPN paths: From Cisco BD0 device

### Interfaces Sheet
**Purpose**: LAG/Bundle-Ether configurations  
**Columns**: Hostname | Device IP | Interface Description | Interface Name | Threshold

**Handles Duplicates**: Appends _1, _2, _3 to duplicate descriptions

---

## 🖥️ Commands by Device Type

### Nokia Primary B07/B06
```bash
/admin display-config                        # BGP neighbors
/admin display-config | match cpe-check      # CPE neighbors
/show port detail | match "BD"               # BD interfaces
/show port detail | match "BM"               # BM interfaces
/show port detail | match "B4"               # B4 interfaces
/show port detail | match "B2"               # B2 interfaces
/show port detail | match "B16/B17/B18"      # B# interfaces
show lag description | match ...             # LAG interfaces
/admin display-config | match "lag 20"       # LAG 20 special (B07/B06 only)

# For each BGP neighbor:
show router X bgp neighbor Y advertised-routes
show router X bgp neighbor Y received-routes

# For each LAG:
show lag N  # Extract threshold
```

### Nokia Secondary B07/B06
```bash
/admin display-config | match "lag 20"       # LAG 20 config + threshold
show lag description | match ...             # Filtered LAG interfaces
```

### Nokia Tab Devices
```bash
# Tab 1:
show lag description | match ...             # Filtered LAG interfaces

# Tab 2/3:
sh int description                           # Find Bundle-Ether
show bundle bundle-ether# (for each)         # Get min active links
```

### Cisco BD0
```bash
show bgp l2vpn evpn rd {B07_RR2}:1 | i prefixes  # RAN from B07
show bgp l2vpn evpn rd {B06_RR2}:1 | i prefixes  # RAN from B06
show bgp l2vpn evpn rd {B07_RR2}:2 | i prefixes  # EDN from B07
show bgp l2vpn evpn rd {B06_RR2}:2 | i prefixes  # EDN from B06
show bgp l2vpn evpn rd {B07_RR2}:3 | i prefixes  # WSN from B07
show bgp l2vpn evpn rd {B06_RR2}:3 | i prefixes  # WSN from B06
```

### Cisco B01/B02/B2C/B2D
```bash
sh run bgp | i "router bgp"                  # Extract BGP AS number
```

### Cisco Tab Devices
```bash
sh int description                           # Find Bundle-Ether
show bundle bundle-ether# (for each)         # Get min active links
```

---

## 🔧 Common Modifications

### 1. Add New Device Type Pattern
**File**: Main script, lines ~120  
**Search for**: `elif cilli and re.search(...)`
```python
elif cilli and re.search(r"BNEW\d+$", cilli):
    device_type = "cisco_nxos"
```

### 2. Add New BGP Context
**File**: Main script, lines ~483  
**Search for**: `BGP_CONTEXTS = [`
```python
BGP_CONTEXTS = [
    # ... existing ...
    "YOUR_NEW_CONTEXT_V4",
    "YOUR_NEW_CONTEXT_V6",
]
```

### 3. Add New Command
**File**: Main script, lines ~784  
**Search for**: `commands = [`
```python
commands = [
    # ... existing ...
    "your new command",
]
```

### 4. Change Default Credentials
**File**: Main script, lines ~244  
**Search for**: `default_username =`
```python
default_username = "NEW_USER"
default_password = "NEW_PASS"
```

### 5. Add New Interface Type
**File**: Main script, lines ~380  
**Search for**: `def extract_bd_interfaces`
```python
def extract_b99_interfaces(output):
    return _pair_desc_iface(output.splitlines(), r"B99([0-9A-Z]+)", "B99")
```

---

## 📍 Key Function Locations

| Function | Line Range | Purpose |
|----------|------------|---------|
| `extract_neighbors()` | ~505-545 | Parse BGP neighbors from display-config |
| `extract_cpe_check_neighbors()` | ~547-570 | Parse CPE-check from VPRN config |
| `extract_lag_interfaces()` | ~380-404 | Parse LAG interfaces from description output |
| `extract_threshold()` | ~406-413 | Extract threshold from show lag output |
| `get_router_for_context()` | ~461-471 | Map BGP context to router ID |
| `connect_cisco_device()` | ~1000-1083 | Connect to Cisco with credential caching |
| `open_proxy_channel()` | ~979-990 | Create jump server SSH tunnel |
| `get_device_sort_key()` | ~1084-1125 | Generate device sorting priority |
| `get_rr2_peers_from_neighbors()` | ~1156-1180 | Find RR-2-PEER IPs from Neighbors sheet |

---

## 🐛 Debugging Tips

### Enable Extra Logging
```python
# Add after line 1:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Print Variable Values
```python
print(f"DEBUG: variable_name = {variable_name}")
```

### Test Single Device
1. Edit `network_inputs.xlsx` → Keep only 1 device row
2. Run script
3. Check Results sheet for command outputs
4. Verify parser output in Neighbors/Interfaces sheets

### Check Command Output
1. Open `network_inputs.xlsx`
2. Go to Results sheet
3. Find your device IP
4. Check raw command output
5. Test your parser regex with that output

### Test Regex Patterns
```python
import re
test_string = "your output line"
match = re.search(r"your pattern", test_string)
print(match.group(1) if match else "No match")
```

---

## ⚡ Performance Tips

### Reduce Timeout for Faster Failure
```python
global_connect_timeout = 5  # Default is 10
```

### Skip Devices
```python
# Comment out device types in processing:
# if device["device_type"] != "nokia_sros_ssh":
#     continue
```

### Parallel Processing (Advanced)
Currently sequential. To parallelize:
1. Use `concurrent.futures.ThreadPoolExecutor`
2. Create worker function for each device
3. Submit all devices to thread pool
4. Merge results after completion

---

## 🔍 Troubleshooting Guide

| Symptom | Possible Cause | Solution |
|---------|----------------|----------|
| "All auth failed" | Wrong credentials or 2FA not approved | Check creds, approve 2FA push |
| "Proxy failed" | Jump server unreachable | Check Proxy_IP, verify network path |
| No data in sheets | Parser regex mismatch | Check Results sheet, update regex |
| Wrong device type | Hostname pattern mismatch | Use Device_Type column override |
| Script hangs | Pagination not handled | Check get_full_output_nokia() logic |
| Timeout errors | Device slow to respond | Increase read_timeout in send_command |
| Duplicate interfaces | Normal behavior | Script adds _1, _2, _3 suffix |
| Missing neighbors | BGP context not in list | Add context to BGP_CONTEXTS |

---

## 📋 Pre-Flight Checklist

Before running script:

- [ ] `network_inputs.xlsx` exists with valid Devices sheet
- [ ] Device IPs/hostnames are correct and reachable
- [ ] Device_Type column filled for cisco_xr devices
- [ ] Proxy_IP filled for devices behind jump server
- [ ] Primary/Secondary roles assigned correctly
- [ ] Default credentials are current
- [ ] 2FA device available for manual auth
- [ ] Network connectivity to all devices verified

---

## 🎯 Common Use Cases

### Case 1: Add New Site
1. Add devices to Devices sheet in Excel
2. Fill columns: Cilli_Hostname, IP/Hostname, Device_Type (if needed), Proxy_IP (if needed), Role
3. Run script
4. Review Neighbors and Interfaces sheets

### Case 2: Collect from Single Device
1. Edit Excel → Keep only 1 device row
2. Run script
3. Check Results sheet for troubleshooting

### Case 3: Update Credentials
1. Edit lines 244-252 in script
2. Or let script prompt and cache new manual creds

### Case 4: Add New Command
1. Add command to `commands` list (line ~784)
2. Capture output in loop
3. Add parser function if needed
4. Append results to appropriate sheet

### Case 5: Change Output Format
1. Modify sheet headers (lines 191-210)
2. Update append statements to include new columns
3. Test with single device first

---

## 🔗 Related Files

- `code11` - Unknown purpose (in workspace)
- `code12` - Unknown purpose (in workspace)
- `failed_connections.log` - Connection failure log
- `network_inputs.xlsx` - Main I/O file

---

## 💡 Pro Tips

1. **Always test with 1 device first** before running on entire inventory
2. **Check Results sheet** when parsers don't work - raw output shows format
3. **Use Device_Type override** for ambiguous hostname patterns
4. **Cache credentials** - Script remembers your manual login across all devices
5. **Sort order matters** - Nokia processed first to discover RR-2-PEER IPs for Cisco
6. **Duplicate handling** - Script automatically numbers duplicate interface descriptions
7. **Jump server reuse** - Proxy credentials cached and reused across devices
8. **Tab devices differ** - Tab2/3 run Bundle-Ether search, Tab1 runs LAG only

---

## 📞 Support

For questions or issues:
1. Check SCRIPT_DOCUMENTATION.md for detailed explanations
2. Review Results sheet for command output debugging
3. Check failed_connections.log for connection errors
4. Use print() statements to debug variable values
5. Test parsers with regex testers (regex101.com)

---

**Last Updated**: 2025-11-19  
**Script Version**: Based on provided code
