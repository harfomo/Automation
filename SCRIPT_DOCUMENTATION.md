# Network Automation Script - Comprehensive Documentation

## 🎯 Purpose
This script automates data collection from Nokia SROS and Cisco NX-OS/IOS-XR network devices. It gathers BGP neighbor information, interface configurations, LAG/Bundle-Ether settings, and EVPN route counts, organizing everything into an Excel workbook.

---

## 📋 Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Input/Output Files](#inputoutput-files)
3. [Device Types and Roles](#device-types-and-roles)
4. [Authentication Flow](#authentication-flow)
5. [Processing Phases](#processing-phases)
6. [Key Functions](#key-functions)
7. [Data Collection Details](#data-collection-details)
8. [Modification Guide](#modification-guide)

---

## 🏗️ Architecture Overview

### Script Flow
```
1. Load Excel device inventory (network_inputs.xlsx)
2. Parse device list and detect device types
3. Extract location codes (Primary/Sister CILLI)
4. Sort devices: Nokia first, then Cisco
5. PHASE 1: Process Nokia devices (B06, B07, BD0, etc.)
   - Collect BGP neighbors and route counts
   - Collect interface information (LAG, BD, BM, B4, B2)
   - Parse cpe-check neighbors
6. PHASE 2: Process Cisco devices (BD0, B01, B02, etc.)
   - Collect EVPN paths from BD0
   - Collect BGP AS numbers from B01/B02
   - Collect Bundle-Ether info from Tab devices
7. Sort and organize results
8. Save to Excel workbook
```

---

## 📁 Input/Output Files

### Input: `network_inputs.xlsx` - "Devices" Sheet
| Column | Name | Description | Example |
|--------|------|-------------|---------|
| A | Cilli_Hostname | Device hostname (used for type detection) | `NWCSDEBGB06` |
| B | IP/Hostname | IPv4/IPv6 address or hostname | `2001:4888:a1f:6332:194:26:0:6` |
| C | Device_Type (optional) | Override auto-detection | `nokia_sros_ssh`, `cisco_nxos`, `cisco_xr` |
| D | Proxy_IP | Jump server IP if needed | `198.226.102.37` |
| E | Primary/Secondary/Primary Tab#/Secondary Tab# | Role and tab info | `Primary`, `Secondary/2`, `Primary/1` |

### Output Sheets in `network_inputs.xlsx`

#### 1. **Results Sheet** - Raw Command Output
- Columns: `Device IP`, `Command`, `Output`
- Contains all raw command outputs for debugging/audit

#### 2. **Neighbors Sheet** - BGP Neighbor Information
- Columns: `Hostname`, `Device IP`, `Neighbor Description`, `Neighbor IP`, `No of advRoutes`, `No of received Routes`, `BGP EVPN IPv4/IPv6 Prefix (Adv)`, `BGP EVPN IPv4/IPv6 Prefix (Recv)`
- Contains BGP neighbors, route counts, and EVPN prefixes
- Special entries:
  - CPE-check neighbors (WSN_FW_nexthop entries)
  - RR-2-PEER neighbors (iBGP-TO-... entries)
  - BGP AS numbers from Cisco devices
  - EVPN path counts from BD0

#### 3. **Interfaces Sheet** - Interface/LAG Information
- Columns: `Hostname`, `Device IP`, `Interface Description`, `Interface Name`, `Threshold`
- Contains LAG interfaces, Bundle-Ether, and threshold values
- Handles duplicate descriptions by appending _1, _2, _3, etc.

---

## 🖥️ Device Types and Roles

### Device Type Detection (Auto or Explicit)
```python
# Automatic detection based on hostname pattern:
B06, B07         → nokia_sros_ssh
BD*, BM*, B4*    → cisco_nxos
B01, B02, B2C    → cisco_nxos

# Explicit override in Device_Type column:
cisco_xr         → Must be specified explicitly
```

### Device Roles

#### 1. **Primary Devices** (Primary with no Tab#)
- **B07/B06**: Full Nokia command set
  - BGP neighbors with route counts
  - CPE-check neighbors
  - Interface collection (BD, BM, B4, B2, B16, B17, B18)
  - LAG descriptions with thresholds
  - **B07/B06 only**: LAG 20 special parsing (description + local-ip-address)

#### 2. **Secondary Devices** (Secondary with no Tab#)
- **B07/B06**: Limited command set
  - LAG 20 port-threshold and full config
  - LAG descriptions (filtered to exclude certain patterns)

#### 3. **Primary Tab Devices** (Primary/1, Primary/2, etc.)
- **Nokia**: LAG descriptions only (filtered)

#### 4. **Secondary Tab Devices** (Secondary/1, Secondary/2, Secondary/3)
- **Tab 1 (Nokia)**: LAG descriptions only
- **Tab 2/3 (Nokia)**: Bundle-Ether search
  - Runs `sh int description` to find BE interfaces with sister_cilli
  - Runs `show bundle bundle-ether#` for each found bundle
  - Collects minimum active links threshold
- **Cisco Tabs**: Bundle-Ether search similar to Nokia Tab 2/3

#### 5. **Cisco Special Devices**
- **BD0**: EVPN path collection
  - Queries EVPN routes from B06/B07 RR-2-PEER addresses
  - Collects path counts for RAN/EDN/WSN contexts
- **B01/B02/B2C/B2D**: BGP AS number collection
  - Runs `sh run bgp | i "router bgp"` to extract AS number

---

## 🔐 Authentication Flow

### Credential Types
1. **Default TACACS Credentials** (embedded)
   - Username: `NCMSOLK`
   - Password: `mhb5N2Ap`

2. **Manual Credentials** (prompted with 2FA support)
   - Prompted if defaults fail
   - Cached globally for reuse on ALL devices (Nokia + Cisco)

3. **Jump Server Credentials** (for proxy connections)
   - Default: `harfomo` / `Aboelhamd0553!!`
   - Manual: Prompted separately if defaults fail
   - Cached for reuse across all proxy connections

### Authentication Strategy
```
For each device:
  1. If manual_creds cached → Try manual_creds first, then try defaults
  2. If no manual_creds → Try defaults first
  3. If both fail → Prompt for manual credentials (with 2FA)
  4. Cache manual credentials for ALL future devices
```

### Jump Server (Proxy) Flow
- Used when `Proxy_IP` column is populated
- Creates Paramiko SSH tunnel to jump server
- Netmiko connects through the tunnel using `sock=channel`
- Proxy credentials cached separately from device credentials

---

## ⚙️ Processing Phases

### Phase 1: Nokia Devices

#### Standard Primary B07/B06 Processing
```python
Commands executed:
1. /admin display-config                    # Full config for BGP neighbor parsing
2. /admin display-config | match cpe-check  # CPE-check neighbors (WSN FW nexthop)
3. /show port detail | match "BD"           # BD interfaces
4. /show port detail | match "BM"           # BM interfaces  
5. /show port detail | match "B4"           # B4 interfaces
6. /show port detail | match "B16/B17/B18"  # Generic B# interfaces
7. /show port detail | match "B2"           # B2 interfaces
8. show lag description | match ...         # LAG interfaces (filtered)
9. (B07/B06 only) /admin display-config | match "lag 20"  # LAG 20 special

For each BGP neighbor:
  - Determine router-id context (RAN=1, EDN=2, WSN=3, CELL_MGMT=4, etc.)
  - Query advertised routes: show router X bgp neighbor Y advertised-routes
  - Query received routes: show router X bgp neighbor Y received-routes
  - For iBGP EVPN: Query label-ipv4 and EVPN prefixes

For each LAG interface:
  - Run "show lag N" to extract threshold value
```

#### Secondary B07/B06 Processing
```python
Commands executed:
1. /admin display-config | match "lag 20"   # LAG 20 full config
   - Extract description
   - Extract port-threshold value
2. show lag description | match ...         # Filtered LAG descriptions
```

#### Tab Device Processing
```python
Primary/Secondary Tab 1:
  - show lag description (filtered)

Secondary Tab 2/3:
  1. sh int description                     # Find BE interfaces with sister_cilli
  2. show bundle bundle-ether# (for each)   # Get minimum active links
```

### Phase 2: Cisco Devices

#### BD0 EVPN Path Collection
```python
# Requires B06_RR-2-PEER and B07_RR-2-PEER from Nokia phase
Commands executed:
1. show bgp l2vpn evpn rd {B07_RR2}:1 | i prefixes  # RAN from B07
2. show bgp l2vpn evpn rd {B06_RR2}:1 | i prefixes  # RAN from B06
3. show bgp l2vpn evpn rd {B07_RR2}:2 | i prefixes  # EDN from B07
4. show bgp l2vpn evpn rd {B06_RR2}:2 | i prefixes  # EDN from B06
5. show bgp l2vpn evpn rd {B07_RR2}:3 | i prefixes  # WSN from B07
6. show bgp l2vpn evpn rd {B06_RR2}:3 | i prefixes  # WSN from B06

# Parses "Processed X prefixes, Y paths" and extracts Y
```

#### Cisco Tab Devices (B01/B02 Tabs)
```python
Commands executed:
1. sh int description                       # Find Bundle-Ether interfaces
2. show bundle bundle-ether# (for each)     # Get minimum active links
```

#### Other Cisco Devices (B01/B02/B2C/B2D)
```python
Command executed:
1. sh run bgp | i "router bgp"              # Extract AS number
# Parses "router bgp 65123" → extracts 65123
```

---

## 🔧 Key Functions

### Connection Functions

#### `get_full_output_nokia(connection, command)`
- Sends command to Nokia device
- Handles pagination ("Press any key", "--More--")
- Returns complete output without prompt/command text

#### `connect_cisco_device(ip, device_type, proxy_ip=None)`
- Unified Cisco connection function for NX-OS and IOS-XR
- Implements credential caching strategy
- Handles jump server connections via Paramiko
- Returns `(connection, proxy_ssh_client)` tuple

#### `open_proxy_channel(proxy_ip, proxy_username, proxy_password, target_ip, target_port=22)`
- Creates Paramiko SSH client to jump server
- Opens direct-tcpip channel to target device
- Returns `(ssh_client, channel)` for Netmiko sock parameter

### Parser Functions

#### BGP Neighbor Extraction
```python
extract_neighbors(display_config_output)
# Parses /admin display-config output
# Finds group "RAN_EBGP_MSE_V4" style contexts
# Extracts neighbor IPs and descriptions
# Returns list of (description, ip) tuples
```

#### CPE-Check Neighbor Extraction
```python
extract_cpe_check_neighbors(output)
# Parses cpe-check commands from VPRN contexts
# Identifies VPRN numbers (3, 500+)
# Generates descriptions like "WSN_FW_nexthop_501_IPv4"
# Returns list of (description, ip) tuples
```

#### Interface Extraction
```python
extract_bd_interfaces(output)  # BD interfaces
extract_bm_interfaces(output)  # BM interfaces
extract_b4_interfaces(output)  # B4 interfaces
extract_b2_interfaces(output)  # B2 interfaces
extract_b_interfaces(output)   # Generic B# (B16, B17, B18)

# All use _pair_desc_iface() helper
# Pattern: Find "Interface: X", then "Description: Y"
# Extract tag from description (e.g., BD0, BM1)
# Return list of (tag, interface) tuples
```

#### LAG Interface Extraction
```python
extract_lag_interfaces(output)
# Searches for "lag N" or "lag-N" patterns
# Looks for description in next few lines
# Matches patterns like "SITE_Bundle-Ether1" or "SITE_lag-1"
# Returns list of (description, lag_name) tuples

extract_threshold(output)
# Parses "show lag N" output
# Finds status row: "1   up   up   ..."
# Extracts threshold value from column 5
# Returns threshold string
```

### Utility Functions

#### Router-ID Context Mapping
```python
get_router_for_context(ctx_name, wsn_mobile_router_id="501")
# Maps BGP context names to router IDs:
# RAN_* → 1
# EDN_* → 2
# WSN_* → 3 (or 501/502 for WSN_VRF_PEER)
# CELL_MGMT_* → 4
# XRTT_* → 673 (or extracted from context name)
```

#### WSN Mobile Router ID Detection
```python
detect_wsn_mobile_router_id_from_neighbors(cpe_neighbors)
# Scans CPE neighbors for "WSN_MOBILE_FW_nexthop_501_"
# Extracts the router ID (501 or 502)
# Returns "501" as default
```

#### RR-2-PEER Discovery
```python
get_rr2_peers_from_neighbors()
# Scans Neighbors sheet for iBGP-TO-... entries
# If B07 device has "iBGP-TO-...B06" → B06_RR-2-PEER IP
# If B06 device has "iBGP-TO-...B07" → B07_RR-2-PEER IP
# Returns (b06_rr2, b07_rr2) tuple
```

### Sorting and Organization

#### Device Sort Key
```python
get_device_sort_key(hostname)
# Returns (role_priority, suffix_priority, tab_number)
# role_priority:
#   0 = Primary (no tab)
#   1 = Secondary (no tab)
#   2 = Primary Tab
#   3 = Secondary Tab
# suffix_priority:
#   0 = B07, 1 = B06, 2 = BD0, 3 = B01, 4 = B02, 5 = B2C, 6 = B2D
```

#### Duplicate Interface Handling
```python
add_interface_with_dedup(hostname, ip, desc, iface, threshold="")
# Tracks interface_desc_counter dictionary
# First occurrence: desc → desc_1
# Second occurrence: desc → desc_2
# Prevents duplicate rows in Interfaces sheet
```

---

## 📊 Data Collection Details

### BGP Context List
```python
BGP_CONTEXTS = [
    "RAN_EBGP_MSE_V4", "RAN_EBGP_MSE_V6",      # RAN MSE peering
    "EDN_EBGP_MSE_V4", "EDN_EBGP_MSE_V6",      # EDN MSE peering
    "WSN_EBGP_MSE_V4", "WSN_EBGP_MSE_V6",      # WSN MSE peering
    "RAN_EBGP_VXLAN_V4", "RAN_EBGP_VXLAN_V6",  # RAN VXLAN peering
    "EDN_EBGP_VXLAN_V4", "EDN_EBGP_VXLAN_V6",  # EDN VXLAN peering
    "WSN_EBGP_VXLAN_V4", "WSN_EBGP_VXLAN_V6",  # WSN VXLAN peering
    "RAN_EBGP_MLS_V4", "RAN_EBGP_MLS_V6",      # RAN MLS peering
    "EDN_EBGP_MLS_V4", "EDN_EBGP_MLS_V6",      # EDN MLS peering
    "WSN_EBGP_MLS_V4", "WSN_EBGP_MLS_V6",      # WSN MLS peering
    "CELL_MGMT_EBGP_MLS_V4", "CELL_MGMT_EBGP_MLS_V6",
    "XRTT_EBGP_MLS_V4",                        # Also XRTT_EBGP_MLS_V4_* variants
    "WSN_VRF_PEER_V4", "WSN_VRF_PEER_V6",      # WSN VRF peering
    "RR-31-PEER",                               # Route Reflector peering
    "RR-1-ENSESR",                              # Route Reflector peering
    "RR-2-PEER"                                 # Route Reflector peering
]
```

### LAG Description Filter
```python
# Filters out interfaces matching these patterns:
- Contains primary_cilli or sister_cilli
- Ends with lag-1, lag-2, lag-19, lag-33 (exact match)
- Must contain "lag-" or "Bundle"

# Example filter expression:
f'show lag description | match expression "({primary_cilli})|({sister_cilli})|(lag-1$)|(lag-2)|(lag-19$)|(lag-33$)" invert-match | match "(lag-)|(Bundle)" expression'
```

### Interface Collection Targets
```python
BD interfaces:  /show port detail | match "BD" post-lines 1
BM interfaces:  /show port detail | match "BM" post-lines 1
B4 interfaces:  /show port detail | match "B4" post-lines 1
B2 interfaces:  /show port detail | match "B2" post-lines 1
B16 interfaces: /show port detail | match "B16" post-lines 1
B17 interfaces: /show port detail | match "B17" post-lines 1
B18 interfaces: /show port detail | match "B18" post-lines 1
LAG interfaces: show lag description (with filters)
```

---

## 🛠️ Modification Guide

### Common Modifications

#### 1. Add New Device Type Detection
**Location**: Lines 100-135 (Device type detection logic)

```python
# Current pattern:
elif cilli and re.search(r"B(D\d+|M\d+|4\d+|01|02|2C|2D|D0)$", cilli):
    device_type = "cisco_nxos"

# To add new pattern (e.g., B3X devices):
elif cilli and re.search(r"B3[0-9A-Z]+$", cilli):
    device_type = "cisco_nxos"  # or cisco_xr
```

#### 2. Add New BGP Context
**Location**: Lines 483-503 (BGP_CONTEXTS list)

```python
BGP_CONTEXTS = [
    # ... existing contexts ...
    "YOUR_NEW_CONTEXT_V4",    # Add your new context
    "YOUR_NEW_CONTEXT_V6",
]

# Also update get_router_for_context() if needed (lines 461-471)
def get_router_for_context(ctx_name, wsn_mobile_router_id="501"):
    if ctx_name.startswith("YOUR_PREFIX_"):
        return 5  # Your router ID
    # ... rest of logic
```

#### 3. Add New Command to Nokia Primary Devices
**Location**: Lines 784-795 (Nokia commands list)

```python
commands = [
    "/admin display-config",
    # ... existing commands ...
    "your new command here",  # Add your command
]

# Then capture output:
your_new_output = ""
for cmd in commands:
    output = get_full_output_nokia(connection, cmd)
    results_ws.append([device["ip"], cmd, output])
    if "your keyword" in cmd:
        your_new_output = output
```

#### 4. Change Credential Defaults
**Location**: Lines 244-252 (Global credentials)

```python
default_username = "YOUR_USERNAME"
default_password = "YOUR_PASSWORD"

# For jump server:
default_proxy_username = "YOUR_PROXY_USERNAME"
default_proxy_password = "YOUR_PROXY_PASSWORD"
```

#### 5. Add New Interface Type (e.g., B5)
**Location**: Lines 380-404 (Interface extraction functions)

```python
# Add new function:
def extract_b5_interfaces(output):
    return _pair_desc_iface(output.splitlines(), r"B5([0-9A-Z]+)", "B5")

# Add to commands list:
commands = [
    # ... existing ...
    '/show port detail | match "B5" post-lines 1',
]

# Add to parsing section (around line 820):
b5_output = ""
# In loop:
if 'match "B5"' in cmd:
    b5_output = output

# Add to interface collection (around line 924):
if b5_output:
    for desc, iface in extract_b5_interfaces(b5_output):
        add_interface_with_dedup(device["hostname"], device["ip"], desc, iface)
```

#### 6. Modify Device Role Logic
**Location**: Lines 650-780 (Device role detection and processing)

```python
# Add new role type:
is_your_new_role = (
    (device.get("primary_secondary") or "").lower() == "your_role" and
    device.get("hostname", "").endswith("B99")
)

if is_your_new_role:
    print(f"  🔹 Your new role detected - running custom commands")
    # Your custom command logic here
    connection.disconnect()
    continue  # Skip standard processing
```

#### 7. Change Sorting Order
**Location**: Lines 1084-1125 (Device sort key function)

```python
def get_device_sort_key(hostname):
    # Modify role_priority values:
    if role == "your_new_role":
        role_priority = 1.5  # Insert between existing priorities
    
    # Modify suffix_priority:
    if hostname.endswith("B99"):
        suffix_priority = 2.5  # Insert between existing priorities
    
    return (role_priority, suffix_priority, tab_number)
```

#### 8. Add New Output Column
**Location**: Lines 191-210 (Sheet headers)

```python
# For Neighbors sheet:
neighbors_ws.append([
    "Hostname", "Device IP", "Neighbor Description", "Neighbor IP",
    "No of advRoutes", "No of received Routes",
    "BGP EVPN IPv4/IPv6 Prefix (Adv)", "BGP EVPN IPv4/IPv6 Prefix (Recv)",
    "Your New Column"  # Add here
])

# Then add data when appending rows:
neighbors_ws.append([
    device["hostname"], device["ip"], desc, ip_addr,
    no_of_adv_routes, no_of_recv_routes,
    evpn_prefix_adv, evpn_prefix_recv,
    your_new_value  # Add here
])
```

### Testing Tips

1. **Test with Single Device First**
   - Edit `network_inputs.xlsx` to contain only one device
   - Run script to verify changes work for that device type
   - Gradually add more devices

2. **Use Results Sheet for Debugging**
   - All raw command outputs are logged to Results sheet
   - Check if commands are running correctly
   - Verify output format matches your parser expectations

3. **Test Authentication Separately**
   - First test with default credentials
   - Then test manual credential prompt
   - Test jump server connections separately

4. **Add Debug Print Statements**
   ```python
   print(f"DEBUG: Your variable = {your_variable}")
   ```

5. **Check Log File**
   - Failed connections logged to `failed_connections.log`
   - Review this file if devices fail to connect

---

## 🔍 Troubleshooting

### Common Issues

#### "All authentication attempts failed"
- Check if default credentials are correct
- Verify 2FA push notification is approved during manual login
- Check if device is reachable (ping test)

#### "Proxy connection failed"
- Verify Proxy_IP is correct in Excel
- Check jump server credentials
- Ensure jump server can reach target device

#### "No data in Neighbors/Interfaces sheet"
- Check Results sheet for command outputs
- Verify parser regex patterns match your output format
- Check if device type detection is correct

#### "Script hangs on command"
- Netmiko timeout may be too short (increase global_connect_timeout)
- Device may be slow to respond (increase read_timeout in send_command)
- Pagination not handled (verify get_full_output_nokia logic)

#### "Wrong device type detected"
- Use Device_Type column override in Excel
- Update hostname pattern regex in device type detection logic

---

## 📝 Code Organization

### Section Breakdown
```
Lines 1-50:     Imports and file paths
Lines 51-72:    Template creation logic
Lines 73-140:   Device list parsing and type detection
Lines 141-186:  Location code extraction and device sorting
Lines 187-211:  Output sheet preparation
Lines 212-265:  Global credentials and timeout configuration
Lines 266-407:  Shared helper functions (parsers)
Lines 408-503:  Nokia-specific parsers (neighbors, cpe-check)
Lines 504-649:  Phase 1 start - Nokia device authentication
Lines 650-780:  Nokia special device processing (Secondary B07/B06, Tabs)
Lines 781-951:  Nokia standard device processing (Primary B07/B06)
Lines 952-972:  Neighbor sheet reordering
Lines 973-978:  Save after Nokia phase
Lines 979-1053: Phase 2 - Cisco device processing (BD0, B01, B02, Tabs)
Lines 1054-1083: Jump server connection functions
Lines 1084-1154: Sorting and deduplication
Lines 1155-1170: Interface sheet reordering
Lines 1171-1175: Final save
```

---

## 🎓 Learning Resources

### Understanding Netmiko
- `ConnectHandler`: Main connection class
- `send_command`: Execute command and wait for prompt
- `send_command_timing`: Execute command with timing delay
- `expect_string`: Custom prompt regex for pagination handling

### Understanding Paramiko (for jump servers)
- `SSHClient`: SSH connection manager
- `get_transport()`: Get underlying SSH transport
- `open_channel("direct-tcpip")`: Create port forwarding channel

### Understanding openpyxl
- `load_workbook`: Load existing Excel file
- `iter_rows(values_only=True)`: Iterate through rows as tuples
- `ws.append([...])`: Add new row to sheet
- `ws.cell(row=N, column=M).value`: Access/modify specific cell

---

## 🚀 Next Steps

Now that you understand the script, you can:

1. **Modify device detection** - Add new device types or hostname patterns
2. **Add new commands** - Collect additional configuration data
3. **Enhance parsers** - Extract new information from command outputs
4. **Customize authentication** - Integrate with credential vaults or SSO
5. **Add new device roles** - Define custom processing for specific device types
6. **Extend output format** - Add new columns or sheets for additional data

Good luck with your modifications! 🎉
