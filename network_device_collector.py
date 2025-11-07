from netmiko import ConnectHandler
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment
import getpass
import os
import re
import time
from datetime import datetime
import paramiko

# =========================================================
# Paths / Files
# =========================================================
script_dir = os.path.dirname(os.path.abspath(__file__))
input_file = os.path.join(script_dir, "network_inputs.xlsx")
log_file = os.path.join(script_dir, "failed_connections.log")

def log_failure(ip, reason):
    """Append failed connection details with timestamp to a local log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"{timestamp} - {ip} - {reason}\n")

# =========================================================
# Create workbook template if missing
# =========================================================
if not os.path.exists(input_file):
    print("📘 No Excel file found — creating template 'network_inputs.xlsx'...")
    wb = Workbook()
    ws_devices = wb.active
    ws_devices.title = "Devices"
    # Cilli_Hostname first (used to detect device type), then IP, optional device type, optional Proxy_IP, and role/tab column
    ws_devices.append(["Cilli_Hostname", "IP/Hostname", "Device_Type (optional)", "Proxy_IP", "Primary/Secondary/Primary Tab#/Secondary Tab#"])
    ws_devices.append(["NWCSDEBGB06", "2001:4888:a1f:6332:194:26:0:6", "nokia_sros_ssh", "", ""])
    ws_devices.append(["NWCSDEBGB07", "2001:4888:a1f:6332:194:26:0:7", "nokia_sros_ssh", "", ""])
    # Example Cisco NX-OS and IOS-XR rows (optional)
    ws_devices.append(["NWCSDEBGBD0", "2001:4888:a1f:6032:196:28:0:d0", "cisco_nxos", "", ""])   # BD0 (no proxy)
    ws_devices.append(["NWCSDEBGB01", "1NWCSDEBGB01", "cisco_nxos", "198.226.102.37", ""])  # B01 via proxy (NX-OS)
    ws_devices.append(["NWCSDEBGB02", "1NWCSDEBGB02", "cisco_nxos", "198.226.102.37", ""])  # B02 via proxy (NX-OS)
    # For IOS-XR devices, use: cisco_ios_xr
    wb.save(input_file)
    print(f"✅ Template created: {input_file}")
    print("➡️ Fill in your devices, then re-run the script.")
    raise SystemExit

wb = load_workbook(input_file)
if "Devices" not in wb.sheetnames:
    print("❌ The workbook must have a 'Devices' sheet.")
    raise SystemExit
devices_ws = wb["Devices"]

# =========================================================
# Build device list from Devices sheet
# =========================================================
devices = []
for row in devices_ws.iter_rows(min_row=2, values_only=True):
    if not row or not row[1]:
        continue
    cilli = row[0]
    ip = row[1]
    dtype = row[2] if len(row) > 2 and row[2] else None
    proxy_ip = row[3] if len(row) > 3 and row[3] else None
    role_tab_info = row[4] if len(row) > 4 and row[4] else None
    
    # Parse the "Primary/Secondary/Primary Tab#/Secondary Tab#" column
    # Format examples: "Primary/1", "Secondary/2", "Primary", "Secondary"
    primary_secondary = None
    primary_tab = None
    secondary_tab = None
    
    if role_tab_info:
        role_tab_str = str(role_tab_info).strip()
        parts = role_tab_str.split("/")
        if len(parts) >= 1:
            role = parts[0].strip().lower()
            if role in ["primary", "secondary"]:
                primary_secondary = parts[0].strip()
                if len(parts) >= 2 and parts[1].strip():
                    tab_num = parts[1].strip()
                    if role == "primary":
                        primary_tab = tab_num
                    else:
                        secondary_tab = tab_num

    # Determine device type:
    # 1. If Device_Type column is filled, use that (explicit override)
    # 2. Otherwise, use heuristic based on hostname pattern
    # 3. For cisco_ios_xr devices, MUST specify in Device_Type column
    
    if dtype:
        # Explicit device type provided in Excel - use it
        device_type = dtype
    elif cilli and (cilli.endswith("B06") or cilli.endswith("B07")):
        # Hostname pattern: B06/B07 → Nokia SROS
        device_type = "nokia_sros_ssh"
    elif cilli and re.search(r"B(D\d+|M\d+|4\d+|01|02|2C|2D|D0)$", cilli):
        # Hostname pattern: BD#/BM#/B4#/B01/B02/etc → Cisco NX-OS
        device_type = "cisco_nxos"
    else:
        # Default to Nokia if no pattern matches
        # NOTE: For cisco_ios_xr, you MUST specify it in Device_Type column!
        device_type = "nokia_sros_ssh"
        if cilli:
            print(f"⚠️ Warning: Could not auto-detect device type for {cilli}, defaulting to nokia_sros_ssh")
            print(f"   If this is a Cisco device, please specify 'cisco_nxos' or 'cisco_ios_xr' in Device_Type column")

    devices.append({
        "hostname": cilli, 
        "ip": ip, 
        "device_type": device_type, 
        "proxy_ip": proxy_ip,
        "primary_secondary": primary_secondary,
        "primary_tab": primary_tab,
        "secondary_tab": secondary_tab
    })

# =========================================================
# Extract primary and sister location codes from Cilli_Hostname
# =========================================================
primary_cilli = None
sister_cilli = None

for device in devices:
    cilli_hostname = device.get("hostname", "")
    role = device.get("primary_secondary", "")
    
    if cilli_hostname and role:
        # Extract location code by removing the last 3-4 characters (B06, B07, BD0, etc.)
        # Example: NWCSDEBGB06 → NWCSDEBG, WMTPPAAAB07 → WMTPPAAA
        location_code = re.sub(r'B\d+[A-Z]?$', '', cilli_hostname)
        
        if role and role.lower() == "primary":
            primary_cilli = location_code
        elif role and role.lower() == "secondary":
            sister_cilli = location_code

# Fallback to defaults if not found
if not primary_cilli:
    primary_cilli = "NWCSDEBG"
if not sister_cilli:
    sister_cilli = "WMTPPAAA"

print(f"🏢 Location codes: Primary={primary_cilli}, Sister={sister_cilli}")

# =========================================================
# Sort devices: Nokia first, then Cisco
# =========================================================
def device_sort_key(device):
    """Sort devices by type: Nokia first, then Cisco"""
    dtype = device.get("device_type", "")
    if "nokia" in dtype.lower():
        return 0
    elif "cisco" in dtype.lower():
        return 1
    else:
        return 2

devices.sort(key=device_sort_key)
print(f"📋 Processing order: Nokia devices first, then Cisco devices")

# =========================================================
# Prepare output sheets
# =========================================================
for name in ["Results", "Neighbors", "Interfaces"]:
    if name in wb.sheetnames:
        del wb[name]

results_ws = wb.create_sheet("Results")
neighbors_ws = wb.create_sheet("Neighbors")
interfaces_ws = wb.create_sheet("Interfaces")

# Results: raw command output logs
results_ws.append(["Device IP", "Command", "Output"])

# Neighbors sheet header — keep existing layout
neighbors_ws.append([
    "Device IP", "Neighbor Description", "Neighbor IP",
    "No of advRoutes", "No of received Routes",
    "BGP EVPN IPv4/IPv6 Prefix (Adv)", "BGP EVPN IPv4/IPv6 Prefix (Recv)"
])

# Interfaces: for BD/BM/B4/B2 and LAG thresholds
interfaces_ws.append(["Device IP", "Interface Description", "Interface Name", "Threshold"])

# =========================================================
# Global Credentials & Timeouts
# =========================================================
default_username = "NCMSOLK"
default_password = "mhb5N2Ap"
global_connect_timeout = 10  # moderate default

# Jump-server default (for B01 and any NX-OS row with Proxy_IP)
default_proxy_username = "harfomo"
default_proxy_password = "Aboelhamd0553!!"

if not devices:
    print("❌ No devices found — please verify your Excel file.")
    raise SystemExit

print("🔐 Nokia devices will use embedded TACACS credentials by default.")
print("   If authentication fails, you'll be prompted for credentials per device.")

# Cisco auth strategy — per-device:
# Try defaults first; if fail, prompt once and reuse that Cisco manual set for later devices.
nxos_manual_creds = None  # tuple of (username, password), set after first prompt
proxy_manual_creds = None # tuple of (username, password) for jump server, set after first prompt

# =========================================================
# Shared helpers
# =========================================================
def get_full_output_nokia(connection, command):
    """Send Nokia command and handle paging cleanly."""
    output = connection.send_command(
        command,
        expect_string=r"[\r\n].*>",
        delay_factor=2,
        read_timeout=45,
        strip_prompt=False,
        strip_command=False,
    )
    while any(x in output for x in ["Press any key", "--More--", "---- More ----"]):
        output += connection.send_command_timing(" ", strip_prompt=False, strip_command=False)
    return output

# LAG description parser
def extract_lag_interfaces(output):
    interfaces = []
    lines = output.splitlines()
    for i, line in enumerate(lines):
        lag_match = re.search(r'\blag[- ]?(\d+)\b', line, re.IGNORECASE)
        if lag_match:
            lag_num = f"lag {lag_match.group(1)}"
            desc = ""
            # Scan next few lines for a clean description token like XYZ_Bundle-EtherN or XYZ_lag-N
            for j in range(i + 1, min(i + 4, len(lines))):
                candidate = lines[j].strip()
                if not candidate or re.search(r'\blag[- ]?\d+\b', candidate, re.IGNORECASE):
                    break
                if re.search(r'>|environment|command', candidate, re.IGNORECASE):
                    continue
                m = re.search(r'([A-Z0-9_-]+_(?:Bundle[-]?Ether|lag)[-A-Za-z0-9]+)', candidate)
                if m:
                    desc = m.group(1)
                    break
            if desc:
                interfaces.append((desc, lag_num))
    return interfaces

def extract_threshold(output):
    """From 'show lag <n>' output, read 'Threshold' column value on the status row."""
    for line in output.splitlines():
        if re.match(r'^\s*\d+\s+up\s+up', line):
            parts = re.split(r'\s+', line.strip())
            if len(parts) >= 6:
                return parts[4]
    return ""

# Interface matchers (BD/BM/B4/B2 and generic B#)
def _pair_desc_iface(lines, tag_regex, tag_prefix):
    neighbors = []
    pending_interface = None
    pending_desc = None
    for line in lines:
        m_if = re.search(r"Interface\s*:\s*([\w\/]+)", line)
        if m_if:
            pending_interface = m_if.group(1).strip()
            if pending_desc:
                neighbors.append((pending_desc, pending_interface))
                pending_desc = None
                pending_interface = None
            continue
        m_desc = re.search(r"Description\s*:\s*(\S+)", line)
        if m_desc:
            token = m_desc.group(1).strip()
            m_tag = re.search(tag_regex, token, re.IGNORECASE)
            if m_tag:
                pending_desc = f"{tag_prefix}{m_tag.group(1)}"
                if pending_interface:
                    neighbors.append((pending_desc, pending_interface))
                    pending_desc = None
                    pending_interface = None
            continue
    if pending_desc and pending_interface:
        neighbors.append((pending_desc, pending_interface))
    return neighbors

def extract_bd_interfaces(output): return _pair_desc_iface(output.splitlines(), r"BD([0-9A-Z]+)", "BD")
def extract_bm_interfaces(output): return _pair_desc_iface(output.splitlines(), r"BM(\d+)", "BM")
def extract_b4_interfaces(output): return _pair_desc_iface(output.splitlines(), r"B4(\d+)", "B4")
def extract_b2_interfaces(output): return _pair_desc_iface(output.splitlines(), r"B2([0-9A-Z]+)", "B2")
def extract_b_interfaces(output):  return _pair_desc_iface(output.splitlines(), r"B(\d+)",  "B")

# Nokia router-id mappers and contexts
def get_router_for_context(ctx_name, wsn_mobile_router_id="501"):
    if ctx_name.startswith("RAN_"):  return 1
    if ctx_name.startswith("EDN_"):  return 2
    if ctx_name.startswith("WSN_"):
        if ctx_name in ("WSN_VRF_PEER_V4", "WSN_VRF_PEER_V6"):
            return int(wsn_mobile_router_id)  # 501/502 dynamic
        return 3
    if ctx_name.startswith("CELL_MGMT_"): return 4
    if ctx_name.startswith("XRTT_"):
        m = re.search(r"_(\d+)$", ctx_name)
        return int(m.group(1)) if m else 673
    return 1

def detect_wsn_mobile_router_id_from_neighbors(cpe_neighbors):
    for desc, _ in cpe_neighbors:
        m = re.search(r"WSN_MOBILE_FW_nexthop_(\d+)_", desc)
        if m:
            return m.group(1)
    return "501"

BGP_CONTEXTS = [
    "RAN_EBGP_MSE_V4", "RAN_EBGP_MSE_V6",
    "EDN_EBGP_MSE_V4", "EDN_EBGP_MSE_V6",
    "WSN_EBGP_MSE_V4", "WSN_EBGP_MSE_V6",
    "RAN_EBGP_VXLAN_V4", "RAN_EBGP_VXLAN_V6",
    "EDN_EBGP_VXLAN_V4", "EDN_EBGP_VXLAN_V6",
    "WSN_EBGP_VXLAN_V4", "WSN_EBGP_VXLAN_V6",
    "RAN_EBGP_MLS_V4", "RAN_EBGP_MLS_V6",
    "EDN_EBGP_MLS_V4", "EDN_EBGP_MLS_V6",
    "WSN_EBGP_MLS_V4", "WSN_EBGP_MLS_V6",
    "CELL_MGMT_EBGP_MLS_V4", "CELL_MGMT_EBGP_MLS_V6",
    "XRTT_EBGP_MLS_V4",
    "WSN_VRF_PEER_V4", "WSN_VRF_PEER_V6",
    "RR-31-PEER",
    "RR-1-ENSESR",
    "RR-2-PEER"
]

def extract_neighbors(display_config_output):
    neighbors = []

    def is_interesting_group(gname: str) -> bool:
        return (gname in BGP_CONTEXTS) or gname.startswith("XRTT_EBGP_MLS_V4_")

    text = display_config_output.replace("\r", "")
    lines = text.splitlines()
    group_re = re.compile(r'^\s*group\s+"([^"]+)"')
    neigh_re = re.compile(r'^\s*neighbor\s+([0-9a-fA-F:\.]+)\b')
    desc_inline_re = re.compile(r'description\s+"([^"]+)"')
    desc_plain_re  = re.compile(r'description\s+([^\n"]+)')

    current_group = None
    in_interesting = False
    i = 0
    while i < len(lines):
        line = lines[i]
        m_group = group_re.match(line)
        if m_group:
            current_group = m_group.group(1)
            in_interesting = is_interesting_group(current_group)
            i += 1
            continue

        if in_interesting:
            m_nei = neigh_re.match(line)
            if m_nei:
                ip = m_nei.group(1)
                desc = current_group
                if current_group in ["RR-1-ENSESR", "RR-2-PEER", "RR-31-PEER"]:
                    j = i + 1
                    while j < len(lines):
                        if group_re.match(lines[j]) or neigh_re.match(lines[j]):
                            break
                        d1 = desc_inline_re.search(lines[j])
                        d2 = desc_plain_re.search(lines[j]) if not d1 else None
                        if d1:
                            desc = d1.group(1).strip()
                            break
                        if d2:
                            desc = d2.group(1).strip()
                            break
                        j += 1
                neighbors.append((desc, ip))
            elif group_re.match(line):
                m2 = group_re.match(line)
                current_group = m2.group(1)
                in_interesting = is_interesting_group(current_group)
        i += 1
    return neighbors

def extract_cpe_check_neighbors(output):
    neighbors = []
    lines = output.splitlines()
    current_vprn = None
    for line in lines:
        vprn_match = re.search(r"\bvprn\s+(\d+)\b", line, re.IGNORECASE)
        if vprn_match:
            current_vprn = int(vprn_match.group(1))
            continue
        if current_vprn and "cpe-check" in line:
            ip_match = re.search(r"cpe-check\s+([0-9a-fA-F:\.]+)", line)
            if ip_match:
                ip = ip_match.group(1)
                is_ipv6 = ":" in ip
                if current_vprn == 3:
                    desc = "WSN_FW_nexthop_IPv6" if is_ipv6 else "WSN_FW_nexthop_IPv4"
                elif current_vprn >= 500:
                    desc = f"WSN_MOBILE_FW_nexthop_{current_vprn}_{'IPv6' if is_ipv6 else 'IPv4'}"
                else:
                    desc = f"WSN_FW_nexthop_{current_vprn}_{'IPv6' if is_ipv6 else 'IPv4'}"
                neighbors.append((desc, ip))
    return neighbors

# =========================================================
# Phase 1 — NOKIA: run embedded commands & parse
# =========================================================
for device in devices:
    if device["device_type"] != "nokia_sros_ssh":
        continue

    print(f"\n🔗 Connecting to {device['ip']} ({device['hostname']}) — detected type: {device['device_type']}")
    
    # Try default credentials first
    connection = None
    try:
        print(f"   🔐 Trying default TACACS credentials...")
        connection = ConnectHandler(
            device_type=device["device_type"],
            ip=device["ip"],
            username=default_username,
            password=default_password,
            timeout=global_connect_timeout
        )
        print(f"✅ Connected to {device['ip']} with default credentials")
    except Exception as e:
        print(f"   ⚠️ Default credentials failed: {e}")
        # Prompt for manual credentials for this device
        print(f"   Please enter credentials for {device['hostname']} ({device['ip']}):")
        manual_username = input("   Enter TACACS username: ")
        manual_password = getpass.getpass("   Enter TACACS password: ")
        
        try:
            connection = ConnectHandler(
                device_type=device["device_type"],
                ip=device["ip"],
                username=manual_username,
                password=manual_password,
                timeout=global_connect_timeout
            )
            print(f"✅ Connected to {device['ip']} with manual credentials")
        except Exception as e2:
            print(f"❌ Manual credentials also failed for {device['ip']}: {e2}")
            log_failure(device["ip"], f"Default and manual auth failed: {e2}")
            continue
    
    if not connection:
        print(f"❌ Could not establish connection to {device['ip']}")
        log_failure(device["ip"], "Connection failed")
        continue

    # Prep session
    try:
        connection.send_command_timing("environment no more", strip_prompt=False)
        connection.send_command_timing("admin", strip_prompt=False)
    except Exception:
        pass

    # Embedded Nokia commands
    commands = [
        "/admin display-config",
        "/admin display-config | match cpe-check context all",
        '/show port detail | match "BD" post-lines 1',
        '/show port detail | match "BM" post-lines 1',
        '/show port detail | match "B4" post-lines 1',
        '/show port detail | match "B16" post-lines 1',
        '/show port detail | match "B17" post-lines 1',
        '/show port detail | match "B18" post-lines 1',
        '/show port detail | match "B2" post-lines 1',
        f'show lag description | match expression "({primary_cilli})|({sister_cilli})|(lag-1$)|(lag-2)|(lag-19$)|(lag-33$)" invert-match | match "(lag-)|(Bundle)" expression'
    ]

    # Stash outputs for parsers
    display_output = ""
    cpe_output = ""
    bd_output = bm_output = b4_output = b16_output = b17_output = b18_output = b2_output = ""
    lag_output = ""

    for cmd in commands:
        print(f"  ▶ Running: {cmd}")
        output = get_full_output_nokia(connection, cmd)
        results_ws.append([device["ip"], cmd, output])
        if cmd == "/admin display-config":
            display_output = output
        elif "cpe-check" in cmd:
            cpe_output = output
        elif 'match "BD"' in cmd:
            bd_output = output
        elif 'match "BM"' in cmd:
            bm_output = output
        elif 'match "B4"' in cmd:
            b4_output = output
        elif 'match "B16"' in cmd:
            b16_output = output
        elif 'match "B17"' in cmd:
            b17_output = output
        elif 'match "B18"' in cmd:
            b18_output = output
        elif 'match "B2"' in cmd:
            b2_output = output
        elif 'show lag description' in cmd:
            lag_output = output
        time.sleep(0.2)

    # cpe-check to detect 501/502
    wsn_mobile_router_id = "501"
    if cpe_output:
        cpe_neighbors = extract_cpe_check_neighbors(cpe_output)
        wsn_mobile_router_id = detect_wsn_mobile_router_id_from_neighbors(cpe_neighbors)
        for desc, ip_addr in cpe_neighbors:
            neighbors_ws.append([device["ip"], desc, ip_addr, "", "", "", ""])

    # Parse neighbors and collect BGP/EVPN route counts
    if display_output:
        neighbors = extract_neighbors(display_output)
        for desc, ip_addr in neighbors:
            is_ipv6 = ":" in ip_addr
            router_id = get_router_for_context(desc, wsn_mobile_router_id)
            no_of_adv_routes = "0"
            no_of_recv_routes = "0"
            evpn_prefix_adv = ""
            evpn_prefix_recv = ""
            try:
                if desc.startswith("iBGP-TO-"):
                    # iBGP EVPN + label-ipv4 (Adv/Recv)
                    cmd_adv_label  = f"/show router bgp neighbor {ip_addr} advertised-routes label-ipv4 brief | match \"Routes :\""
                    cmd_adv_evpn   = f"/show router bgp neighbor {ip_addr} advertised-routes evpn | match expression \"(Routes :)|(BGP EVPN)\""
                    cmd_recv_label = f"/show router bgp neighbor {ip_addr} received-routes label-ipv4 brief | match \"Routes :\""
                    cmd_recv_evpn  = f"/show router bgp neighbor {ip_addr} received-routes evpn | match expression \"(Routes :)|(BGP EVPN)\""
                    out_adv_label  = get_full_output_nokia(connection, cmd_adv_label)
                    out_adv_evpn   = get_full_output_nokia(connection, cmd_adv_evpn)
                    out_recv_label = get_full_output_nokia(connection, cmd_recv_label)
                    out_recv_evpn  = get_full_output_nokia(connection, cmd_recv_evpn)

                    m_adv  = re.search(r"Routes\s*:\s*(\d+)", out_adv_label or "")
                    m_recv = re.search(r"Routes\s*:\s*(\d+)", out_recv_label or "")
                    no_of_adv_routes  = m_adv.group(1) if m_adv else "0"
                    no_of_recv_routes = m_recv.group(1) if m_recv else "0"

                    # EVPN advertised — titles on one line, "Routes :" is next line
                    ipv4_adv_pref = "0"; ipv6_adv_pref = "0"
                    lines = out_adv_evpn.splitlines()
                    for idx, line in enumerate(lines):
                        if "BGP EVPN IP-Prefix Routes" in line and idx + 1 < len(lines):
                            mm = re.search(r"Routes\s*:\s*(\d+)", lines[idx + 1]);  ipv4_adv_pref = mm.group(1) if mm else ipv4_adv_pref
                        elif "BGP EVPN IPv6-Prefix Routes" in line and idx + 1 < len(lines):
                            mm = re.search(r"Routes\s*:\s*(\d+)", lines[idx + 1]);  ipv6_adv_pref = mm.group(1) if mm else ipv6_adv_pref

                    # EVPN received
                    ipv4_recv_pref = "0"; ipv6_recv_pref = "0"
                    lines = out_recv_evpn.splitlines()
                    for idx, line in enumerate(lines):
                        if "BGP EVPN IP-Prefix Routes" in line and idx + 1 < len(lines):
                            mm = re.search(r"Routes\s*:\s*(\d+)", lines[idx + 1]);  ipv4_recv_pref = mm.group(1) if mm else ipv4_recv_pref
                        elif "BGP EVPN IPv6-Prefix Routes" in line and idx + 1 < len(lines):
                            mm = re.search(r"Routes\s*:\s*(\d+)", lines[idx + 1]);  ipv6_recv_pref = mm.group(1) if mm else ipv6_recv_pref

                    evpn_prefix_adv  = f"IP-Prefix-{ipv4_adv_pref} routes, IPv6-Prefix-{ipv6_adv_pref} routes"
                    evpn_prefix_recv = f"IP-Prefix-{ipv4_recv_pref} routes, IPv6-Prefix-{ipv6_recv_pref} routes"

                else:
                    cmd_adv  = f"/show router {router_id} bgp neighbor {ip_addr} advertised-routes {'ipv6 ' if is_ipv6 else ''}brief | match \"Routes :\""
                    cmd_recv = f"/show router {router_id} bgp neighbor {ip_addr} received-routes {'ipv6 ' if is_ipv6 else ''}brief | match \"Routes :\""
                    out_adv  = get_full_output_nokia(connection, cmd_adv)
                    out_recv = get_full_output_nokia(connection, cmd_recv)
                    m1 = re.search(r"Routes\s*:\s*(\d+)", out_adv or "");  no_of_adv_routes  = m1.group(1) if m1 else "0"
                    m2 = re.search(r"Routes\s*:\s*(\d+)", out_recv or ""); no_of_recv_routes = m2.group(1) if m2 else "0"

                neighbors_ws.append([
                    device["ip"], desc, ip_addr,
                    no_of_adv_routes, no_of_recv_routes,
                    evpn_prefix_adv, evpn_prefix_recv
                ])
                time.sleep(0.2)
            except Exception as e:
                print(f"⚠️ Failed to collect routes for {desc} ({ip_addr}): {e}")
                neighbors_ws.append([device["ip"], desc, ip_addr, "ERROR", "ERROR", "ERROR", "ERROR"])

    # Interfaces (BD/BM/B4/B2/B#) to Interfaces sheet
    if bd_output:
        for desc, iface in extract_bd_interfaces(bd_output):
            interfaces_ws.append([device["ip"], desc, iface, ""])
    if bm_output:
        for desc, iface in extract_bm_interfaces(bm_output):
            interfaces_ws.append([device["ip"], desc, iface, ""])
    if b4_output:
        for desc, iface in extract_b4_interfaces(b4_output):
            interfaces_ws.append([device["ip"], desc, iface, ""])
    if b2_output:
        for desc, iface in extract_b2_interfaces(b2_output):
            interfaces_ws.append([device["ip"], desc, iface, ""])
    # Generic B# for B16/B17/B18
    if b16_output:
        for desc, iface in extract_b_interfaces(b16_output):
            interfaces_ws.append([device["ip"], desc, iface, ""])
    if b17_output:
        for desc, iface in extract_b_interfaces(b17_output):
            interfaces_ws.append([device["ip"], desc, iface, ""])
    if b18_output:
        for desc, iface in extract_b_interfaces(b18_output):
            interfaces_ws.append([device["ip"], desc, iface, ""])

    # LAG description + Threshold
    if lag_output:
        lag_interfaces = extract_lag_interfaces(lag_output)
        for desc, lag_name in lag_interfaces:
            num_match = re.search(r'\d+', lag_name)
            if not num_match:
                interfaces_ws.append([device["ip"], desc, lag_name, ""])
                continue
            lag_num = num_match.group(0)
            lag_show_cmd = f"show lag {lag_num}"
            print(f"  ▶ Checking threshold for {lag_name}")
            lag_detail_output = get_full_output_nokia(connection, lag_show_cmd)
            results_ws.append([device["ip"], lag_show_cmd, lag_detail_output])
            threshold = extract_threshold(lag_detail_output)
            interfaces_ws.append([device["ip"], desc, lag_name, threshold])

    connection.disconnect()
    print(f"✅ Completed {device['ip']}")

# After Nokia phase: reorder Neighbors by BGP_CONTEXTS
try:
    context_order = {name: idx for idx, name in enumerate(BGP_CONTEXTS)}
    rows = list(neighbors_ws.iter_rows(min_row=2, values_only=True))
    rows.sort(key=lambda r: context_order.get(r[1], 9999))
    for r in range(2, neighbors_ws.max_row + 1):
        for c in range(1, neighbors_ws.max_column + 1):
            neighbors_ws.cell(row=r, column=c).value = None
    for i, row in enumerate(rows, start=2):
        for j, val in enumerate(row, start=1):
            neighbors_ws.cell(row=i, column=j, value=val)
    print("✅ Neighbor sheet reordered to match BGP_CONTEXTS list.")
except Exception as e:
    print(f"⚠️ Sorting skipped due to error: {e}")

# Save after Nokia phase (as requested)
wb.save(input_file)
print(f"\n💾 Nokia phase saved: {input_file}")

# =========================================================
# Phase 2 — Cisco (NX-OS/IOS-XR): BD0 EVPN paths & B01 BGP-ID, with reusable jump-server
# =========================================================

def open_proxy_channel(proxy_ip, proxy_username, proxy_password, target_ip, target_port=22):
    """
    Open a Paramiko SSHClient to the proxy and return a direct-tcpip channel
    to the target along with the ssh_client (caller must keep it open).
    """
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(proxy_ip, username=proxy_username, password=proxy_password, timeout=20)
    transport = ssh_client.get_transport()
    if transport is None:
        ssh_client.close()
        raise RuntimeError("Proxy transport is not available.")
    chan = transport.open_channel("direct-tcpip", (target_ip, target_port), ("127.0.0.1", 0))
    return ssh_client, chan

def connect_cisco_device(ip, device_type, proxy_ip=None):
    """
    Connect to Cisco device (NX-OS or IOS-XR). Try default creds first; on failure prompt once and reuse.
    If proxy_ip is provided, build a jump-channel first (and reuse jump creds on demand).
    Returns (connection, proxy_ssh_client) — proxy_ssh_client must be closed if not None.
    """
    global nxos_manual_creds, proxy_manual_creds

    # Decide which creds to try first for Cisco devices (NX-OS/IOS-XR)
    attempts = []
    attempts.append(("default", default_username, default_password))
    if nxos_manual_creds:
        attempts.append(("manual_cached", nxos_manual_creds[0], nxos_manual_creds[1]))

    proxy_client = None
    last_error = None

    for label, u, p in attempts:
        try:
            if proxy_ip:
                # Try default proxy creds then cached
                proxy_attempts = []
                proxy_attempts.append(("proxy_default", default_proxy_username, default_proxy_password))
                if proxy_manual_creds:
                    proxy_attempts.append(("proxy_manual_cached", proxy_manual_creds[0], proxy_manual_creds[1]))

                proxy_connected = False
                last_proxy_error = None
                for plabel, pu, pp in proxy_attempts:
                    try:
                        print(f"   🔐 Trying {plabel} for jump-server {proxy_ip} ...")
                        proxy_client, chan = open_proxy_channel(proxy_ip, pu, pp, ip, 22)
                        print(f"   ✅ Jump-server channel established via {proxy_ip}.")
                        proxy_connected = True
                        break
                    except Exception as pe:
                        last_proxy_error = pe
                        print(f"   ⚠️ Jump-server {plabel} failed: {pe}")

                if not proxy_connected:
                    # Prompt once for jump creds and cache
                    print(f"   ⚠️ Default jump credentials failed for {proxy_ip}. Please enter jump-server credentials.")
                    ju = input("   Enter Jump username: ")
                    jp = getpass.getpass("   Enter Jump password: ")
                    try:
                        proxy_client, chan = open_proxy_channel(proxy_ip, ju, jp, ip, 22)
                        print(f"   ✅ Jump-server channel established via {proxy_ip}.")
                        proxy_manual_creds = (ju, jp)
                    except Exception as pe2:
                        print(f"   ❌ Jump-server authentication failed: {pe2}")
                        # no proxy => cannot proceed to device
                        raise pe2

                # With channel ready, connect Netmiko via sock
                print(f"   🔗 Connecting to Cisco {device_type} {ip} through proxy {proxy_ip} using {label} creds ...")
                conn = ConnectHandler(
                    device_type=device_type,
                    ip=ip,
                    username=u,
                    password=p,
                    sock=chan,
                    timeout=global_connect_timeout
                )
            else:
                print(f"   🔗 Connecting directly to Cisco {device_type} {ip} using {label} creds ...")
                conn = ConnectHandler(
                    device_type=device_type,
                    ip=ip,
                    username=u,
                    password=p,
                    timeout=global_connect_timeout
                )
            print(f"   ✅ Connected to Cisco {device_type} {ip} ({label}).")
            # If we connected using manual cached (or newly prompted below), keep nxos_manual_creds as-is
            return conn, proxy_client
        except Exception as e:
            last_error = e
            print(f"   ⚠️ Cisco {device_type} {label} auth failed on {ip}: {e}")
            if proxy_client:
                try:
                    proxy_client.close()
                except Exception:
                    pass
            proxy_client = None

    # If default and cached manual failed or not present: prompt once and retry
    print(f"   ⚠️ Please enter Cisco ({device_type}) credentials for {ip}.")
    u = input(f"   Enter Cisco {device_type} username: ")
    p = getpass.getpass(f"   Enter Cisco {device_type} password: ")
    nxos_manual_creds = (u, p)

    try:
        if proxy_ip:
            # ensure proxy is up with (possibly) cached or manual
            if not proxy_manual_creds:
                print(f"   🔐 Enter jump-server credentials for {proxy_ip}.")
                ju = input("   Enter Jump username: ")
                jp = getpass.getpass("   Enter Jump password: ")
                proxy_manual_creds = (ju, jp)
            else:
                ju, jp = proxy_manual_creds

            proxy_client, chan = open_proxy_channel(proxy_ip, ju, jp, ip, 22)
            print(f"   ✅ Jump-server channel established via {proxy_ip}.")
            conn = ConnectHandler(
                device_type=device_type,
                ip=ip,
                username=u,
                password=p,
                sock=chan,
                timeout=global_connect_timeout
            )
        else:
            conn = ConnectHandler(
                device_type=device_type,
                ip=ip,
                username=u,
                password=p,
                timeout=global_connect_timeout
            )
        print(f"   ✅ Connected to Cisco {device_type} {ip} (manual).")
        return conn, proxy_client
    except Exception as e2:
        print(f"   ❌ Cisco {device_type} manual auth failed on {ip}: {e2}")
        if proxy_client:
            try:
                proxy_client.close()
            except Exception:
                pass
        return None, None

# ---- Helpers to find BD0 / B01 and pull RR-2-PEERs from Nokia results
def find_device_by_suffix(suffix):
    for d in devices:
        device_type = d.get("device_type", "")
        # Support both cisco_nxos and cisco_ios_xr
        if device_type in ["cisco_nxos", "cisco_ios_xr"] and d["hostname"] and d["hostname"].endswith(suffix):
            return d
    return None

def get_rr2_peers_from_neighbors():
    """
    Scan Neighbors sheet to find:
      - B06_RR-2-PEER → neighbor IP where row belongs to B07 device with desc iBGP-TO-...B06
      - B07_RR-2-PEER → neighbor IP where row belongs to B06 device with desc iBGP-TO-...B07
    """
    # Map device IP -> Cilli_Hostname for quick lookup
    ip_to_cilli = {}
    for row in devices_ws.iter_rows(min_row=2, values_only=True):
        if row and row[1]:
            ip_to_cilli[row[1]] = row[0]

    b06_rr2 = None
    b07_rr2 = None

    for row in neighbors_ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0] or not row[1]:
            continue
        device_ip = row[0]
        desc = str(row[1])
        nei_ip = row[2]
        host = ip_to_cilli.get(device_ip, "")
        if desc.startswith("iBGP-TO-"):
            peer_host = desc.replace("iBGP-TO-", "").strip()
            # If neighbor desc ends with B07 and the local device is B06 => B07 RR-2-PEER
            if peer_host.endswith("B07") and host.endswith("B06"):
                b07_rr2 = nei_ip
            # If neighbor desc ends with B06 and the local device is B07 => B06 RR-2-PEER
            if peer_host.endswith("B06") and host.endswith("B07"):
                b06_rr2 = nei_ip

    return b06_rr2, b07_rr2

# ---- NX-OS Phase: BD0 EVPN paths
bd0 = find_device_by_suffix("BD0")
b01 = find_device_by_suffix("B01")

# Use RR-2-PEER values from Nokia phase
b06_rr2, b07_rr2 = get_rr2_peers_from_neighbors()
print(f"\n🔎 RR-2-PEER discovery: B06={b06_rr2 or 'N/A'}  |  B07={b07_rr2 or 'N/A'}")

# 1) BD0 EVPN path counts (if BD0 and both RRs present)
if bd0 and b06_rr2 and b07_rr2:
    print(f"\n🔗 Connecting to BD0 ({bd0['hostname']} @ {bd0['ip']}) — {bd0['device_type']} EVPN path checks")
    conn, proxy_client = connect_cisco_device(bd0["ip"], bd0["device_type"], proxy_ip=bd0.get("proxy_ip"))
    if conn:
        try:
            commands = [
                f"show bgp l2vpn evpn rd {b07_rr2}:1 | i prefixes",
                f"show bgp l2vpn evpn rd {b06_rr2}:1 | i prefixes",
                f"show bgp l2vpn evpn rd {b07_rr2}:2 | i prefixes",
                f"show bgp l2vpn evpn rd {b06_rr2}:2 | i prefixes",
                f"show bgp l2vpn evpn rd {b07_rr2}:3 | i prefixes",
                f"show bgp l2vpn evpn rd {b06_rr2}:3 | i prefixes",
            ]
            descriptions = [
                "RAN routes from B07",
                "RAN routes from B06",
                "EDN routes from B07",
                "EDN routes from B06",
                "WSN routes from B07",
                "WSN routes from B06",
            ]
            for cmd, desc in zip(commands, descriptions):
                print(f"  ▶ {cmd}")
                out = conn.send_command(cmd, read_timeout=30)
                results_ws.append([bd0["ip"], cmd, out])
                # Parse: "Processed 1541 prefixes, 3082 paths"
                m = re.search(r'Processed\s+(\d+)\s+prefixe?s?\s*,\s*(\d+)\s+paths?', out, re.IGNORECASE)
                paths = m.group(2) if m else "ERROR"
                neighbors_ws.append([
                    bd0["ip"], desc, cmd.split("rd ")[1].split(" |")[0], "", "", paths, ""
                ])
                print(f"    → {desc}: paths={paths}")
        finally:
            try:
                conn.disconnect()
            except Exception:
                pass
            if proxy_client:
                try:
                    proxy_client.close()
                except Exception:
                    pass
    else:
        print("❌ Skipping BD0 EVPN checks (unable to connect).")
else:
    print("ℹ️ BD0 EVPN checks skipped (BD0 or RR-2-PEER values missing).")

# 2) B01 BGP-ID (prepend a row under header)
if b01:
    print(f"\n🔗 Connecting to B01 ({b01['hostname']} @ {b01['ip']}) — {b01['device_type']} BGP ID read")
    conn, proxy_client = connect_cisco_device(b01["ip"], b01["device_type"], proxy_ip=b01.get("proxy_ip"))
    if conn:
        try:
            cmd = 'sh run bgp | i "router bgp"'
            print(f"  ▶ {cmd}")
            out = conn.send_command(cmd, read_timeout=30)
            results_ws.append([b01["ip"], cmd, out])
            # e.g. "router bgp 65123"
            m = re.search(r'router\s+bgp\s+(\d+)', out, re.IGNORECASE)
            bgp_number = m.group(1) if m else "UNKNOWN"
            # Insert at row 2 (push existing rows down)
            neighbors_ws.insert_rows(2, amount=1)
            neighbors_ws.cell(row=2, column=1).value = b01["ip"]
            neighbors_ws.cell(row=2, column=2).value = "BGP ID"
            neighbors_ws.cell(row=2, column=3).value = bgp_number
            neighbors_ws.cell(row=2, column=4).value = ""
            neighbors_ws.cell(row=2, column=5).value = ""
            neighbors_ws.cell(row=2, column=6).value = ""
            neighbors_ws.cell(row=2, column=7).value = ""
            print(f"    → BGP ID = {bgp_number} (inserted at top of Neighbors)")
        finally:
            try:
                conn.disconnect()
            except Exception:
                pass
            if proxy_client:
                try:
                    proxy_client.close()
                except Exception:
                    pass
else:
    print("ℹ️ B01 BGP-ID check skipped (B01 not present).")

# =========================================================
# Final save
# =========================================================
wb.save(input_file)
print(f"\n📊 Results, Neighbors, and Interfaces saved in '{input_file}'")
print("✅ Script completed successfully.")
