# Parser Reference Guide

## 📖 Overview

This document explains all parsing functions in the network automation script, including regex patterns, input formats, and expected outputs.

---

## 🔍 Table of Contents

1. [BGP Neighbor Parsers](#bgp-neighbor-parsers)
2. [Interface Parsers](#interface-parsers)
3. [LAG Parsers](#lag-parsers)
4. [Route Count Parsers](#route-count-parsers)
5. [Cisco Parsers](#cisco-parsers)
6. [Helper Functions](#helper-functions)
7. [Regex Pattern Reference](#regex-pattern-reference)

---

## 🌐 BGP Neighbor Parsers

### `extract_neighbors(display_config_output)`

**Purpose**: Extract BGP neighbors from Nokia `/admin display-config` output

**Input Format**:
```
configure
    router Base
        bgp
            group "RAN_EBGP_MSE_V4"
                neighbor 2001:4888:a1f:6332::1
                    description "Some description"
                exit
            exit
            group "RR-2-PEER"
                neighbor 10.1.1.1
                    description "iBGP-TO-NWCSDEBGB06"
                exit
            exit
        exit
    exit
```

**Regex Patterns**:
```python
group_re = re.compile(r'^\s*group\s+"([^"]+)"')
# Matches: group "RAN_EBGP_MSE_V4"
# Captures: RAN_EBGP_MSE_V4

neigh_re = re.compile(r'^\s*neighbor\s+([0-9a-fA-F:\.]+)\b')
# Matches: neighbor 2001:4888:a1f:6332::1
# Captures: 2001:4888:a1f:6332::1

desc_inline_re = re.compile(r'description\s+"([^"]+)"')
# Matches: description "Some description"
# Captures: Some description

desc_plain_re = re.compile(r'description\s+([^\n"]+)')
# Matches: description SomeDescription
# Captures: SomeDescription
```

**Logic Flow**:
1. Scan for `group "X"` lines → Set current_group
2. Check if group is "interesting" (in BGP_CONTEXTS list)
3. Find `neighbor Y` lines within interesting groups
4. For special groups (RR-1-ENSESR, RR-2-PEER, RR-31-PEER), look ahead for description
5. Return list of (description, ip) tuples

**Output**:
```python
[
    ("RAN_EBGP_MSE_V4", "2001:4888:a1f:6332::1"),
    ("iBGP-TO-NWCSDEBGB06", "10.1.1.1"),
    ...
]
```

**BGP Context Filter**:
```python
def is_interesting_group(gname: str) -> bool:
    return (gname in BGP_CONTEXTS) or gname.startswith("XRTT_EBGP_MLS_V4_")
```

---

### `extract_cpe_check_neighbors(output)`

**Purpose**: Extract CPE-check neighbors from Nokia VPRN configuration

**Input Format**:
```
vprn 3 customer 1 create
    sap lag-20.100 create
        anti-spoof nh-mac
            cpe-check 10.1.1.1
                interval 1
            exit
        exit
    exit
exit

vprn 501 customer 1 create
    sap lag-20.200 create
        anti-spoof nh-mac
            cpe-check 2001:db8::1
            exit
        exit
    exit
exit
```

**Regex Patterns**:
```python
vprn_match = re.search(r"\bvprn\s+(\d+)\b", line, re.IGNORECASE)
# Matches: vprn 3, vprn 501
# Captures: 3, 501

ip_match = re.search(r"cpe-check\s+([0-9a-fA-F:\.]+)", line)
# Matches: cpe-check 10.1.1.1
# Captures: 10.1.1.1
```

**Description Logic**:
```python
if current_vprn == 3:
    desc = "WSN_FW_nexthop_IPv6" if is_ipv6 else "WSN_FW_nexthop_IPv4"
elif current_vprn >= 500:
    desc = f"WSN_MOBILE_FW_nexthop_{current_vprn}_{'IPv6' if is_ipv6 else 'IPv4'}"
else:
    desc = f"WSN_FW_nexthop_{current_vprn}_{'IPv6' if is_ipv6 else 'IPv4'}"
```

**Output**:
```python
[
    ("WSN_FW_nexthop_IPv4", "10.1.1.1"),
    ("WSN_MOBILE_FW_nexthop_501_IPv6", "2001:db8::1"),
    ...
]
```

---

## 🔌 Interface Parsers

### Generic Interface Parser: `_pair_desc_iface(lines, tag_regex, tag_prefix)`

**Purpose**: Base parser for extracting interface-description pairs

**Logic**:
1. Find `Interface : X` lines
2. Find `Description : Y` lines
3. Extract tag from description using tag_regex
4. Pair description tag with interface name
5. Handle pending matches if order is reversed

**Usage Example**:
```python
def extract_bd_interfaces(output):
    return _pair_desc_iface(output.splitlines(), r"BD([0-9A-Z]+)", "BD")
```

---

### `extract_bd_interfaces(output)`

**Purpose**: Extract BD (Border) interfaces from Nokia `show port detail` output

**Input Format**:
```
Port Id        : 1/1/c1/1
Description    : NWCSDEBGBD0_interface
...
Interface      : 1/1/c1/1
Admin State    : Up
```

**Regex Pattern**:
```python
tag_regex = r"BD([0-9A-Z]+)"
# Matches: BD0, BDX, BD10
# Captures: 0, X, 10
# Produces: BD0, BDX, BD10
```

**Output**:
```python
[
    ("BD0", "1/1/c1/1"),
    ("BDX", "1/1/c2/1"),
    ...
]
```

---

### `extract_bm_interfaces(output)`

**Purpose**: Extract BM (Border Metro) interfaces

**Regex Pattern**:
```python
tag_regex = r"BM(\d+)"
# Matches: BM0, BM1, BM10
# Captures: 0, 1, 10
# Produces: BM0, BM1, BM10
```

---

### `extract_b4_interfaces(output)`

**Purpose**: Extract B4 interfaces (4G equipment)

**Regex Pattern**:
```python
tag_regex = r"B4(\d+)"
# Matches: B40, B41, B42
# Captures: 0, 1, 2
# Produces: B40, B41, B42
```

---

### `extract_b2_interfaces(output)`

**Purpose**: Extract B2 interfaces (2G/special equipment)

**Regex Pattern**:
```python
tag_regex = r"B2([0-9A-Z]+)"
# Matches: B2C, B2D, B20
# Captures: C, D, 0
# Produces: B2C, B2D, B20
```

---

### `extract_b_interfaces(output)`

**Purpose**: Extract generic B# interfaces (B16, B17, B18)

**Regex Pattern**:
```python
tag_regex = r"B(\d+)"
# Matches: B16, B17, B18, B99
# Captures: 16, 17, 18, 99
# Produces: B16, B17, B18, B99
```

---

## 🔗 LAG Parsers

### `extract_lag_interfaces(output)`

**Purpose**: Extract LAG interface descriptions from `show lag description` output

**Input Format**:
```
LAG ID  Description
-------------------------------------------------------------------------------
1       WMTPPAAAB06_lag-1
        Some additional info
2       NWCSDEBGB07_Bundle-Ether2
        More details here
```

**Regex Patterns**:
```python
lag_match = re.search(r'\blag[- ]?(\d+)\b', line, re.IGNORECASE)
# Matches: lag-1, lag 2, LAG3
# Captures: 1, 2, 3

desc_pattern = r'([A-Z0-9_-]+_(?:Bundle[-]?Ether|lag)[-A-Za-z0-9]+)'
# Matches: SITE_Bundle-Ether1, SITE_lag-2, SITE_BundleEther3
# Captures: Full description
```

**Logic Flow**:
1. Find line with `lag N` or `lag-N` pattern
2. Store LAG number
3. Scan next 1-4 lines for description
4. Look for pattern: `SITECODE_Bundle-Ether#` or `SITECODE_lag-#`
5. Skip lines with `>`, `environment`, `command` keywords
6. Return list of (description, lag_name) tuples

**Output**:
```python
[
    ("WMTPPAAAB06_lag-1", "lag 1"),
    ("NWCSDEBGB07_Bundle-Ether2", "lag 2"),
    ...
]
```

**Edge Cases Handled**:
- Multi-line descriptions (scans up to 4 lines ahead)
- Duplicate LAG mentions (stops scanning if another `lag N` found)
- Command prompts in output (skips lines with `>`, `command`, etc.)

---

### `extract_threshold(output)`

**Purpose**: Extract threshold value from `show lag N` command output

**Input Format**:
```
===============================================================================
LAG Details
===============================================================================
LAG ID                     : 1
Admin State                : Up
Oper State                 : Up
Mode                       : access
Port Id         Admin State Oper State
-------------------------------------------------------------------------------
1     up   up   active   None      1       1.00 Gbps
```

**Regex Pattern**:
```python
pattern = r'^\s*\d+\s+up\s+up'
# Matches: Lines starting with "number  up  up"
# Example: "1     up   up   active   None      1       1.00 Gbps"
```

**Logic**:
1. Find status row starting with `number up up`
2. Split line by whitespace
3. Extract column index 4 (5th element) as threshold
4. Return threshold string or empty string

**Output**:
```python
"1"  # Threshold value
""   # If not found
```

**Status Row Format**:
```
Index: 0    1   2    3       4         5     6
Value: 1    up  up   active  [THRESH]  1     1.00 Gbps
                              ^^^^^^^^
                              This is extracted
```

---

## 📊 Route Count Parsers

### Standard BGP Route Parser

**Purpose**: Parse route counts from Nokia BGP neighbor output

**Input Format**:
```
===============================================================================
BGP Router ID:10.1.1.1        AS:65000       Local AS:65000
===============================================================================
Routes : 1234
```

**Regex Pattern**:
```python
pattern = r"Routes\s*:\s*(\d+)"
# Matches: Routes : 1234, Routes: 5678, Routes :999
# Captures: 1234, 5678, 999
```

**Usage**:
```python
out_adv = get_full_output_nokia(connection, cmd_adv)
m = re.search(r"Routes\s*:\s*(\d+)", out_adv or "")
no_of_adv_routes = m.group(1) if m else "0"
```

---

### EVPN Prefix Route Parser (iBGP)

**Purpose**: Parse EVPN IP-Prefix and IPv6-Prefix route counts

**Input Format**:
```
===============================================================================
BGP EVPN IP-Prefix Routes
===============================================================================
Routes : 500
===============================================================================
BGP EVPN IPv6-Prefix Routes
===============================================================================
Routes : 300
```

**Logic**:
1. Find line with `BGP EVPN IP-Prefix Routes`
2. Read next line for `Routes : N`
3. Find line with `BGP EVPN IPv6-Prefix Routes`
4. Read next line for `Routes : N`
5. Format as: `IP-Prefix-500 routes, IPv6-Prefix-300 routes`

**Code Pattern**:
```python
ipv4_adv_pref = "0"
ipv6_adv_pref = "0"
lines = out_adv_evpn.splitlines()
for idx, line in enumerate(lines):
    if "BGP EVPN IP-Prefix Routes" in line and idx + 1 < len(lines):
        mm = re.search(r"Routes\s*:\s*(\d+)", lines[idx + 1])
        ipv4_adv_pref = mm.group(1) if mm else ipv4_adv_pref
    elif "BGP EVPN IPv6-Prefix Routes" in line and idx + 1 < len(lines):
        mm = re.search(r"Routes\s*:\s*(\d+)", lines[idx + 1])
        ipv6_adv_pref = mm.group(1) if mm else ipv6_adv_pref

evpn_prefix_adv = f"IP-Prefix-{ipv4_adv_pref} routes, IPv6-Prefix-{ipv6_adv_pref} routes"
```

---

## 🔴 Cisco Parsers

### Cisco EVPN Path Parser (BD0)

**Purpose**: Extract path counts from Cisco `show bgp l2vpn evpn` output

**Input Format**:
```
BGP routing table information for VRF default, address family L2VPN EVPN
Route Distinguisher: 10.1.1.1:1
BGP table version is 123, local router ID is 10.2.2.2
Status codes: s suppressed, d damped, h history, * valid, > best
Origin codes: i - IGP, e - EGP, ? - incomplete
AS Path Attributes: Or-ID - Originator ID, C-LST - Cluster List

   Network            Next Hop            Metric     LocPrf     Weight Path
...

Processed 1541 prefixes, 3082 paths
```

**Regex Pattern**:
```python
pattern = r'Processed\s+(\d+)\s+prefixe?s?\s*,\s*(\d+)\s+paths?'
# Matches: Processed 1541 prefixes, 3082 paths
#          Processed 1 prefix, 2 paths
# Captures: (1541, 3082) or (1, 2)
```

**Usage**:
```python
out = conn.send_command(cmd, read_timeout=30)
m = re.search(r'Processed\s+(\d+)\s+prefixe?s?\s*,\s*(\d+)\s+paths?', out, re.IGNORECASE)
paths = m.group(2) if m else "ERROR"  # Extract path count (group 2)
```

---

### Cisco BGP AS Number Parser

**Purpose**: Extract BGP AS number from Cisco `sh run bgp` output

**Input Format**:
```
!Command: show running-config bgp
!Running configuration last done at: Mon Jan 15 10:30:00 2024
!Time: Mon Jan 15 10:35:00 2024

version 9.3(3) Bios:version

router bgp 65123
  router-id 10.1.1.1
  address-family ipv4 unicast
  exit
```

**Regex Pattern**:
```python
pattern = r'router\s+bgp\s+(\d+)'
# Matches: router bgp 65123
# Captures: 65123
```

**Usage**:
```python
out = conn.send_command(cmd, read_timeout=30)
m = re.search(r'router\s+bgp\s+(\d+)', out, re.IGNORECASE)
bgp_number = m.group(1) if m else "UNKNOWN"
```

---

### Cisco Bundle-Ether Interface Parser (Tab Devices)

**Purpose**: Extract Bundle-Ether interface numbers from description output

**Input Format**:
```
Interface              Status   Protocol Description
---------------------- -------- -------- -----------
BE1                    up       up       Some description
BE2                    up       up       WMTPPAAAB06_lag-2
BE3                    up       up       NWCSDEBGB07_Bundle-Ether3
```

**Regex Patterns**:
```python
# Find BE interface with specific CILLI in description
if sister_cilli.upper() in line.upper():
    be_match = re.search(r'\bBE(\d+)\b', line, re.IGNORECASE)
    # Matches: BE1, BE2, BE10
    # Captures: 1, 2, 10
```

---

### Cisco Bundle Minimum Active Links Parser

**Purpose**: Extract minimum active links from `show bundle bundle-ether#` output

**Input Format**:
```
Bundle-Ether3
  Status:                    Up
  Local links <active/standby/configured>: 2 / 0 / 2
  Local bandwidth <effective/available>:   20000000 (20000000) kbps
  MAC address (source):      0011.2233.4455 (Chassis pool)
  Minimum active links / bandwidth:          1 / 1 kbps
  Maximum active links:      64
  Wait while timer:          2000 ms
```

**Regex Pattern**:
```python
pattern = r'minimum active links.*:\s*(\d+)\s*/'
# Matches: Minimum active links / bandwidth:          1 / 1 kbps
# Captures: 1
```

**Logic**:
```python
for line in bundle_output.splitlines():
    if "minimum active links" in line.lower():
        match = re.search(r':\s*(\d+)\s*/', line)
        if match:
            min_active_links = match.group(1)
            break
```

---

### Nokia LAG 20 Parser (Primary B07/B06)

**Purpose**: Extract LAG 20 description and local-ip-address

**Input Format**:
```
configure
    lag 20
        description "SITE_lag-20"
        mode access
        lacp
            active
            administrative-key 20
        exit
        local-ip-address 10.1.1.1
        port-threshold 1
    exit
```

**Regex Patterns**:
```python
# Description
desc_match = re.search(r'description\s+"([^"]+)"', line, re.IGNORECASE)
# or
desc_match = re.search(r'description\s+(\S+)', line, re.IGNORECASE)

# Local IP
ip_match = re.search(r'local-ip-address\s+([0-9a-fA-F:\.]+)', line, re.IGNORECASE)
```

**Output**: Added to Neighbors sheet
```python
[hostname, device_ip, lag20_desc, lag20_local_ip, "", "", "", ""]
```

---

### Nokia LAG 20 Threshold Parser (Secondary B07/B06)

**Purpose**: Extract port-threshold from LAG 20 configuration

**Input Format**:
```
configure
    lag 20
        description "SITE_lag-20"
        port-threshold 2
    exit
```

**Regex Pattern**:
```python
thresh_match = re.search(r'port-threshold\s+(\d+)', line, re.IGNORECASE)
# Matches: port-threshold 2
# Captures: 2
```

---

## 🛠️ Helper Functions

### `get_router_for_context(ctx_name, wsn_mobile_router_id="501")`

**Purpose**: Map BGP context name to Nokia router instance ID

**Mapping Table**:
```python
Context Prefix          → Router ID
---------------------------------
RAN_*                   → 1
EDN_*                   → 2
WSN_*                   → 3 (except VRF_PEER)
WSN_VRF_PEER_*          → 501/502 (dynamic)
CELL_MGMT_*             → 4
XRTT_EBGP_MLS_V4_N      → N (extracted from name)
XRTT_* (others)         → 673
Default                 → 1
```

**Code**:
```python
def get_router_for_context(ctx_name, wsn_mobile_router_id="501"):
    if ctx_name.startswith("RAN_"):  return 1
    if ctx_name.startswith("EDN_"):  return 2
    if ctx_name.startswith("WSN_"):
        if ctx_name in ("WSN_VRF_PEER_V4", "WSN_VRF_PEER_V6"):
            return int(wsn_mobile_router_id)
        return 3
    if ctx_name.startswith("CELL_MGMT_"): return 4
    if ctx_name.startswith("XRTT_"):
        m = re.search(r"_(\d+)$", ctx_name)
        return int(m.group(1)) if m else 673
    return 1
```

---

### `detect_wsn_mobile_router_id_from_neighbors(cpe_neighbors)`

**Purpose**: Detect WSN mobile router ID (501 or 502) from CPE neighbor descriptions

**Logic**:
```python
for desc, _ in cpe_neighbors:
    m = re.search(r"WSN_MOBILE_FW_nexthop_(\d+)_", desc)
    # Pattern: WSN_MOBILE_FW_nexthop_501_IPv4
    # Captures: 501
    if m:
        return m.group(1)
return "501"  # Default
```

---

### `get_rr2_peers_from_neighbors()`

**Purpose**: Find RR-2-PEER IPs from Neighbors sheet (iBGP-TO-* entries)

**Logic**:
```python
# Scan Neighbors sheet:
for row in neighbors_ws.iter_rows(min_row=2, values_only=True):
    hostname = row[0]      # Column 0: Hostname
    desc = str(row[2])     # Column 2: Neighbor Description
    nei_ip = row[3]        # Column 3: Neighbor IP
    
    if desc.startswith("iBGP-TO-"):
        peer_host = desc.replace("iBGP-TO-", "").strip()
        
        # If B06 device has iBGP-TO-...B07 neighbor → B07_RR-2-PEER
        if peer_host.endswith("B07") and hostname.endswith("B06"):
            b07_rr2 = nei_ip
        
        # If B07 device has iBGP-TO-...B06 neighbor → B06_RR-2-PEER
        if peer_host.endswith("B06") and hostname.endswith("B07"):
            b06_rr2 = nei_ip

return b06_rr2, b07_rr2
```

---

### `add_interface_with_dedup(hostname, ip, desc, iface, threshold="")`

**Purpose**: Add interface to sheet with duplicate description handling

**Logic**:
```python
interface_desc_counter = {}  # Per-device counter

def add_interface_with_dedup(hostname, ip, desc, iface, threshold=""):
    if desc in interface_desc_counter:
        interface_desc_counter[desc] += 1
        numbered_desc = f"{desc}_{interface_desc_counter[desc]}"
    else:
        interface_desc_counter[desc] = 1
        numbered_desc = f"{desc}_1"
    
    interfaces_ws.append([hostname, ip, numbered_desc, iface, threshold])
```

**Example**:
```python
# First B16: → B16_1
add_interface_with_dedup("HOST", "IP", "B16", "1/1/1")

# Second B16: → B16_2
add_interface_with_dedup("HOST", "IP", "B16", "1/1/2")

# Third B16: → B16_3
add_interface_with_dedup("HOST", "IP", "B16", "1/1/3")
```

---

## 📝 Regex Pattern Reference

### Common Patterns

#### IPv4 Address
```python
r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
# Matches: 10.1.1.1, 192.168.0.1
```

#### IPv6 Address
```python
r'([0-9a-fA-F:]+)'
# Matches: 2001:db8::1, fe80::1
```

#### IPv4 or IPv6 Combined
```python
r'([0-9a-fA-F:\.]+)'
# Matches both IPv4 and IPv6
```

#### Interface Name (Nokia)
```python
r'([\w\/]+)'
# Matches: 1/1/1, 1/1/c1/1, lag-1
```

#### LAG Number
```python
r'\blag[- ]?(\d+)\b'
# Matches: lag-1, lag 2, LAG3, lag10
# Captures: 1, 2, 3, 10
```

#### Bundle-Ether Number (Cisco)
```python
r'\bBE(\d+)\b'
# Matches: BE1, BE10, BE100
# Captures: 1, 10, 100
```

#### BGP AS Number
```python
r'router\s+bgp\s+(\d+)'
# Matches: router bgp 65000
# Captures: 65000
```

#### Route Count
```python
r"Routes\s*:\s*(\d+)"
# Matches: Routes : 1234, Routes: 5678
# Captures: 1234, 5678
```

#### EVPN Path Count (Cisco)
```python
r'Processed\s+(\d+)\s+prefixe?s?\s*,\s*(\d+)\s+paths?'
# Matches: Processed 1541 prefixes, 3082 paths
# Captures: (1541, 3082)
```

---

### Device Type Detection Patterns

```python
# Nokia B06/B07
r'B0[67]$'
# Matches: NWCSDEBGB06, WMTPPAAAB07

# Cisco BD/BM/B4/B01/B02/B2C/B2D
r'B(D\d+|M\d+|4\d+|01|02|2C|2D|D0)$'
# Matches: NWCSDEBGBD0, NWCSDEBGBM1, NWCSDEBGB40, NWCSDEBGB01

# Location code extraction
r'B\d+[A-Z]?$'
# Removes: B06, B07, BD0, B01, etc. from end of hostname
# NWCSDEBGB06 → NWCSDEBG
```

---

## 🧪 Testing Parsers

### Test Individual Parser

```python
# Copy parser function and test data
test_output = """
Interface      : 1/1/1
Description    : NWCSDEBGBD0_test
"""

result = extract_bd_interfaces(test_output)
print(result)  # Expected: [("BD0", "1/1/1")]
```

### Test Regex Online

Use [regex101.com](https://regex101.com/) with Python flavor:
1. Paste your regex pattern
2. Paste sample command output
3. Verify captures match expectations

### Debug Parser in Script

```python
# Add debug prints in parser:
def extract_neighbors(display_config_output):
    neighbors = []
    # ... existing code ...
    for line in lines:
        m_group = group_re.match(line)
        if m_group:
            print(f"DEBUG: Found group: {m_group.group(1)}")  # Debug
            current_group = m_group.group(1)
    # ... rest of code ...
    return neighbors
```

---

## 🎯 Common Parser Modifications

### 1. Add New Interface Type

```python
# Add new parser function
def extract_b99_interfaces(output):
    return _pair_desc_iface(output.splitlines(), r"B99([0-9A-Z]+)", "B99")

# Add to commands list
commands = [
    # ... existing ...
    '/show port detail | match "B99" post-lines 1',
]

# Add parsing logic
b99_output = ""
for cmd in commands:
    output = get_full_output_nokia(connection, cmd)
    if 'match "B99"' in cmd:
        b99_output = output

# Add to interface collection
if b99_output:
    for desc, iface in extract_b99_interfaces(b99_output):
        add_interface_with_dedup(device["hostname"], device["ip"], desc, iface)
```

### 2. Modify LAG Description Pattern

```python
# Current pattern:
desc_pattern = r'([A-Z0-9_-]+_(?:Bundle[-]?Ether|lag)[-A-Za-z0-9]+)'

# To also match "Port-Channel":
desc_pattern = r'([A-Z0-9_-]+_(?:Bundle[-]?Ether|lag|Port-Channel)[-A-Za-z0-9]+)'
```

### 3. Add New BGP Context Pattern

```python
# In is_interesting_group():
def is_interesting_group(gname: str) -> bool:
    return (gname in BGP_CONTEXTS) or \
           gname.startswith("XRTT_EBGP_MLS_V4_") or \
           gname.startswith("YOUR_NEW_PREFIX_")  # Add this
```

### 4. Parse Additional Field from Output

```python
# Example: Extract "Admin State" from port detail
def extract_admin_state(output):
    for line in output.splitlines():
        m = re.search(r'Admin State\s*:\s*(\w+)', line)
        if m:
            return m.group(1)
    return "Unknown"
```

---

## 📚 Parsing Best Practices

1. **Always Test with Real Data**
   - Use Results sheet to get actual command outputs
   - Test regex with exact format from devices

2. **Handle Missing Data Gracefully**
   ```python
   m = re.search(pattern, text)
   value = m.group(1) if m else "DEFAULT_VALUE"
   ```

3. **Use Raw Strings for Regex**
   ```python
   # Good:
   pattern = r'\d+'
   # Bad:
   pattern = '\\d+'
   ```

4. **Compile Regex for Repeated Use**
   ```python
   pattern = re.compile(r'your pattern')
   for line in lines:
       m = pattern.match(line)
   ```

5. **Document Expected Format**
   - Add comments showing expected input format
   - Include example matches and captures

6. **Test Edge Cases**
   - Empty output
   - Malformed lines
   - Multiple matches
   - No matches

---

**Parser reference complete! Use this guide to understand and modify parsing logic in the script.**
