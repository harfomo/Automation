#!/usr/bin/env python3
"""
Enhanced network audit script with BD0 EVPN route queries.
Extends the original script to query EVPN routes from Cisco BD0 device.
"""

from netmiko import ConnectHandler
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment
import getpass
import os
import re
import time
from datetime import datetime


# ==============================
# Step 1: Excel setup
# ==============================
script_dir = os.path.dirname(os.path.abspath(__file__))
input_file = os.path.join(script_dir, "network_inputs.xlsx")
log_file = os.path.join(script_dir, "failed_connections.log")

def log_failure(ip, reason):
    """Write connection failure to log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"{timestamp} - {ip} - {reason}\n")


# Create workbook template if missing
if not os.path.exists(input_file):
    print("📘 No Excel file found — creating template 'network_inputs.xlsx'...")
    wb = Workbook()
    ws_devices = wb.active
    ws_devices.title = "Devices"
    ws_devices.append(["Cilli_Hostname", "IP/Hostname", "Device_Type (optional)"])
    ws_devices.append(["NWCSDEBGB06", "2001:4888:a1f:6332:194:26:0:6", "nokia_sros_ssh"])
    wb.save(input_file)
    print(f"✅ Template created: {input_file}")
    print("➡️ Fill in your devices, then re-run the script.")
    raise SystemExit

wb = load_workbook(input_file)
if "Devices" not in wb.sheetnames:
    print("❌ The workbook must have a 'Devices' sheet.")
    raise SystemExit

devices_ws = wb["Devices"]


# ==============================
# Step 2: Build device list
# ==============================
devices = []
for row in devices_ws.iter_rows(min_row=2, values_only=True):
    if not row or not row[1]:
        continue
    cilli = row[0]
    ip = row[1]
    dtype = row[2] if len(row) > 2 and row[2] else None

    # Heuristic: B06/B07 → Nokia; BD#/BM#/B4#/B2C/B2D etc → Cisco
    if cilli and (cilli.endswith("B06") or cilli.endswith("B07")):
        device_type = "nokia_sros_ssh"
    elif cilli and re.search(r"B(D\d+|M\d+|4\d+|01|02|2C|2D)$", cilli):
        device_type = "cisco_nxos"
    elif dtype:
        device_type = dtype
    else:
        device_type = "nokia_sros_ssh"

    devices.append({"hostname": cilli, "ip": ip, "device_type": device_type})


# ==============================
# Step 3: Prepare output sheets
# ==============================
for name in ["Results", "Neighbors", "Interfaces"]:
    if name in wb.sheetnames:
        del wb[name]

results_ws = wb.create_sheet("Results")
neighbors_ws = wb.create_sheet("Neighbors")
interfaces_ws = wb.create_sheet("Interfaces")

results_ws.append(["Device IP", "Command", "Output"])
neighbors_ws.append([
    "Device IP", "Neighbor Description", "Neighbor IP",
    "No of advRoutes", "No of received Routes",
    "BGP EVPN IPv4/IPv6 Prefix (Adv)", "BGP EVPN IPv4/IPv6 Prefix (Recv)"
])
interfaces_ws.append(["Device IP", "Interface Description", "Interface Name", "Threshold"])


# ==============================
# Step 4: TACACS credentials
# ==============================
default_username = "NCMSOLK"
default_password = "mhb5N2Ap"
global_connect_timeout = 15

def try_login(ip, username, password):
    """Test login to confirm credentials are valid."""
    try:
        conn = ConnectHandler(
            device_type="nokia_sros_ssh",
            ip=ip, username=username, password=password,
            timeout=global_connect_timeout
        )
        conn.disconnect()
        return True
    except Exception as e:
        print(f"   ⚠️ Test login failed on {ip}: {e}")
        return False

if not devices:
    print("❌ No devices found — please verify your Excel file.")
    raise SystemExit

first_ip = devices[0]["ip"]
print("🔐 Using embedded TACACS credentials by default.")
print(f"🔐 Testing default TACACS credentials on {first_ip} ...")
if try_login(first_ip, default_username, default_password):
    username = default_username
    password = default_password
    print("✅ Default credentials work — proceeding.")
else:
    print("⚠️ Default credentials failed — please enter your USWIN credentials.")
    username = input("Enter USWIN username: ")
    password = getpass.getpass("Enter USWIN password: ")


# ==============================
# Step 5: Helper functions
# ==============================
def get_full_output(connection, command):
    """Send command and handle paging."""
    output = connection.send_command(
        command,
        expect_string=r"[\r\n].*[>#]",
        delay_factor=2,
        read_timeout=30,
        strip_prompt=False,
        strip_command=False
    )
    while any(x in output for x in ["Press any key", "--More--", "---- More ----"]):
        output += connection.send_command_timing(" ", strip_prompt=False, strip_command=False)
    return output


def extract_lag_interfaces(output):
    """Extract lag number and description from 'show lag description' output."""
    interfaces = []
    lines = output.splitlines()
    for i, line in enumerate(lines):
        lag_match = re.search(r'\blag[- ]?(\d+)\b', line, re.IGNORECASE)
        if lag_match:
            lag_num = f"lag {lag_match.group(1)}"
            desc = ""
            for j in range(i + 1, min(i + 4, len(lines))):
                candidate = lines[j].strip()
                if not candidate or re.search(r'\blag[- ]?\d+\b', candidate, re.IGNORECASE):
                    break
                if re.search(r'>|environment|command', candidate, re.IGNORECASE):
                    continue
                match = re.search(r'([A-Z0-9_-]+_(?:Bundle[-]Ether|lag)[-A-Za-z0-9]+)', candidate)
                if match:
                    desc = match.group(1)
                    break
            if desc:
                interfaces.append((desc, lag_num))
    return interfaces

def extract_threshold(output):
    """Extract Threshold value from 'show lag <num>' output."""
    for line in output.splitlines():
        if re.match(r'^\s*\d+\s+up\s+up', line):
            parts = re.split(r'\s+', line.strip())
            if len(parts) >= 6:
                return parts[4]
    return ""


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

def extract_bd_interfaces(output):
    return _pair_desc_iface(output.splitlines(), r"BD(\d+)", "BD")

def extract_bm_interfaces(output):
    return _pair_desc_iface(output.splitlines(), r"BM(\d+)", "BM")

def extract_b4_interfaces(output):
    return _pair_desc_iface(output.splitlines(), r"B4(\d+)", "B4")

def extract_b2_interfaces(output):
    return _pair_desc_iface(output.splitlines(), r"B2(\d+)", "B2")

def extract_b_interfaces(output):
    return _pair_desc_iface(output.splitlines(), r"B(\d+)", "B")


def get_router_for_context(ctx_name, wsn_mobile_router_id="501"):
    """Map neighbor 'group' names to SR OS router IDs."""
    if ctx_name.startswith("RAN_"):
        return 1
    if ctx_name.startswith("EDN_"):
        return 2
    if ctx_name.startswith("WSN_"):
        if ctx_name in ("WSN_VRF_PEER_V4", "WSN_VRF_PEER_V6"):
            return int(wsn_mobile_router_id)
        return 3
    if ctx_name.startswith("CELL_MGMT_"):
        return 4
    if ctx_name.startswith("XRTT_"):
        m = re.search(r"_(\d+)$", ctx_name)
        return int(m.group(1)) if m else 673
    return 1

def detect_wsn_mobile_router_id_from_neighbors(cpe_neighbors):
    """Pull 501/502 from cpe-check-derived descriptions."""
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
    """From '/admin display-config', extract tuples of (desc, ip) for our groups."""
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
    """Parse '/admin display-config | match cpe-check context all'."""
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


# ==============================
# Step 6: Run per device
# ==============================
# Store RR-2-PEER IPs for later BD0 queries
b06_rr2_peer_ip = None
b07_rr2_peer_ip = None
bd0_device = None

for device in devices:
    print(f"\n🔗 Connecting to {device['ip']} ({device['hostname']}) — detected type: {device['device_type']}")

    # Track BD0 device for later
    if "BD0" in device['hostname']:
        bd0_device = device
        print("  📌 Marked as BD0 device for EVPN queries")

    try:
        connection = ConnectHandler(
            device_type=device["device_type"],
            ip=device["ip"],
            username=username,
            password=password,
            timeout=global_connect_timeout
        )
    except Exception as e:
        print(f"❌ Failed to connect to {device['ip']}: {e}\n")
        log_failure(device["ip"], str(e))
        continue

    # Prep session
    try:
        connection.send_command_timing("environment no more", strip_prompt=False)
        connection.send_command_timing("admin", strip_prompt=False)
    except Exception:
        pass

    if device["device_type"] == "nokia_sros_ssh":
        # Nokia commands
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
            'show lag description | match expression "(NWCSDEBG)|(WMTPPAAA)|(lag-1$)|(lag-2)|(lag-19$)|(lag-33$)" invert-match | match "(lag-)|(Bundle)" expression'
        ]

        display_output = ""
        cpe_output = ""
        bd_output = bm_output = b4_output = b16_output = b17_output = b18_output = b2_output = ""
        lag_output = ""

        for cmd in commands:
            print(f"  ▶ Running: {cmd}")
            output = get_full_output(connection, cmd)
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

        # Parse cpe-check
        wsn_mobile_router_id = "501"
        cpe_neighbors = []
        if cpe_output:
            cpe_neighbors = extract_cpe_check_neighbors(cpe_output)
            wsn_mobile_router_id = detect_wsn_mobile_router_id_from_neighbors(cpe_neighbors)
            for desc, ip_addr in cpe_neighbors:
                neighbors_ws.append([device["ip"], desc, ip_addr, "", "", "", ""])

        # Parse neighbors and collect RR-2-PEER IPs
        if display_output:
            neighbors = extract_neighbors(display_output)
            for desc, ip_addr in neighbors:
                # Store RR-2-PEER IPs based on iBGP-TO- descriptions
                # B07's RR-2-PEER = iBGP-TO-<hostname_ending_with_B06> on B07 device
                # B06's RR-2-PEER = iBGP-TO-<hostname_ending_with_B07> on B06 device
                if desc.startswith("iBGP-TO-"):
                    # Extract hostname from description (e.g., "iBGP-TO-NWCSDEBGB06" -> "NWCSDEBGB06")
                    peer_hostname = desc.replace("iBGP-TO-", "").strip()
                    
                    if peer_hostname.endswith("B06") and "B07" in device['hostname']:
                        # This is B06's RR-2-PEER (found on B07 device)
                        b06_rr2_peer_ip = ip_addr
                        print(f"  📝 Stored B06 RR-2-PEER: {ip_addr} (from {desc} on B07)")
                    elif peer_hostname.endswith("B07") and "B06" in device['hostname']:
                        # This is B07's RR-2-PEER (found on B06 device)
                        b07_rr2_peer_ip = ip_addr
                        print(f"  📝 Stored B07 RR-2-PEER: {ip_addr} (from {desc} on B06)")

                is_ipv6 = ":" in ip_addr
                router_id = get_router_for_context(desc, wsn_mobile_router_id)

                no_of_adv_routes = "0"
                no_of_recv_routes = "0"
                evpn_prefix_adv = ""
                evpn_prefix_recv = ""

                try:
                    if desc.startswith("iBGP-TO-"):
                        cmd_adv_label  = f"/show router bgp neighbor {ip_addr} advertised-routes label-ipv4 brief | match \"Routes :\""
                        cmd_adv_evpn   = f"/show router bgp neighbor {ip_addr} advertised-routes evpn | match expression \"(Routes :)|(BGP EVPN)\""
                        cmd_recv_label = f"/show router bgp neighbor {ip_addr} received-routes label-ipv4 brief | match \"Routes :\""
                        cmd_recv_evpn  = f"/show router bgp neighbor {ip_addr} received-routes evpn | match expression \"(Routes :)|(BGP EVPN)\""

                        out_adv_label  = get_full_output(connection, cmd_adv_label)
                        out_adv_evpn   = get_full_output(connection, cmd_adv_evpn)
                        out_recv_label = get_full_output(connection, cmd_recv_label)
                        out_recv_evpn  = get_full_output(connection, cmd_recv_evpn)

                        m_adv  = re.search(r"Routes\s*:\s*(\d+)", out_adv_label or "")
                        m_recv = re.search(r"Routes\s*:\s*(\d+)", out_recv_label or "")
                        no_of_adv_routes  = m_adv.group(1) if m_adv else "0"
                        no_of_recv_routes = m_recv.group(1) if m_recv else "0"

                        ipv4_adv_pref = "0"; ipv6_adv_pref = "0"
                        lines = out_adv_evpn.splitlines()
                        for idx, line in enumerate(lines):
                            if "BGP EVPN IP-Prefix Routes" in line and idx + 1 < len(lines):
                                mm = re.search(r"Routes\s*:\s*(\d+)", lines[idx + 1])
                                if mm: ipv4_adv_pref = mm.group(1)
                            elif "BGP EVPN IPv6-Prefix Routes" in line and idx + 1 < len(lines):
                                mm = re.search(r"Routes\s*:\s*(\d+)", lines[idx + 1])
                                if mm: ipv6_adv_pref = mm.group(1)

                        ipv4_recv_pref = "0"; ipv6_recv_pref = "0"
                        lines = out_recv_evpn.splitlines()
                        for idx, line in enumerate(lines):
                            if "BGP EVPN IP-Prefix Routes" in line and idx + 1 < len(lines):
                                mm = re.search(r"Routes\s*:\s*(\d+)", lines[idx + 1])
                                if mm: ipv4_recv_pref = mm.group(1)
                            elif "BGP EVPN IPv6-Prefix Routes" in line and idx + 1 < len(lines):
                                mm = re.search(r"Routes\s*:\s*(\d+)", lines[idx + 1])
                                if mm: ipv6_recv_pref = mm.group(1)

                        evpn_prefix_adv  = f"IP-Prefix-{ipv4_adv_pref} routes, IPv6-Prefix-{ipv6_adv_pref} routes"
                        evpn_prefix_recv = f"IP-Prefix-{ipv4_recv_pref} routes, IPv6-Prefix-{ipv6_recv_pref} routes"

                    else:
                        cmd_adv  = f"/show router {router_id} bgp neighbor {ip_addr} advertised-routes {'ipv6 ' if is_ipv6 else ''}brief | match \"Routes :\""
                        cmd_recv = f"/show router {router_id} bgp neighbor {ip_addr} received-routes {'ipv6 ' if is_ipv6 else ''}brief | match \"Routes :\""
                        out_adv  = get_full_output(connection, cmd_adv)
                        out_recv = get_full_output(connection, cmd_recv)
                        m1 = re.search(r"Routes\s*:\s*(\d+)", out_adv or "")
                        m2 = re.search(r"Routes\s*:\s*(\d+)", out_recv or "")
                        no_of_adv_routes  = m1.group(1) if m1 else "0"
                        no_of_recv_routes = m2.group(1) if m2 else "0"

                    neighbors_ws.append([
                        device["ip"], desc, ip_addr,
                        no_of_adv_routes, no_of_recv_routes,
                        evpn_prefix_adv, evpn_prefix_recv
                    ])
                    time.sleep(0.2)

                except Exception as e:
                    print(f"⚠️ Failed to collect routes for {desc} ({ip_addr}): {e}")
                    neighbors_ws.append([device["ip"], desc, ip_addr, "ERROR", "ERROR", "ERROR", "ERROR"])

        # Interfaces
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
        if b16_output:
            for desc, iface in extract_b_interfaces(b16_output):
                interfaces_ws.append([device["ip"], desc, iface, ""])
        if b17_output:
            for desc, iface in extract_b_interfaces(b17_output):
                interfaces_ws.append([device["ip"], desc, iface, ""])
        if b18_output:
            for desc, iface in extract_b_interfaces(b18_output):
                interfaces_ws.append([device["ip"], desc, iface, ""])

        # LAG interfaces
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
                lag_detail_output = get_full_output(connection, lag_show_cmd)
                results_ws.append([device["ip"], lag_show_cmd, lag_detail_output])
                threshold = extract_threshold(lag_detail_output)
                interfaces_ws.append([device["ip"], desc, lag_name, threshold])

    elif device["device_type"] == "cisco_nxos":
        print(f"  ⚙️ Cisco device detected ({device['hostname']})")
        interfaces_ws.append([device["ip"], "CISCO_DEVICE", "N/A", "N/A"])

    connection.disconnect()
    print(f"✅ Completed {device['ip']}")


# ==============================
# Step 7: Query BD0 for EVPN routes
# ==============================
if bd0_device and b06_rr2_peer_ip and b07_rr2_peer_ip:
    print("\n" + "="*70)
    print("🔍 QUERYING BD0 DEVICE FOR EVPN ROUTES")
    print("="*70)
    print(f"BD0 Device: {bd0_device['hostname']} ({bd0_device['ip']})")
    print(f"B06 RR-2-PEER IP: {b06_rr2_peer_ip}")
    print(f"B07 RR-2-PEER IP: {b07_rr2_peer_ip}")
    
    try:
        print(f"\n🔗 Connecting to BD0...")
        bd0_username = username
        bd0_password = password
        
        try:
            connection = ConnectHandler(
                device_type=bd0_device["device_type"],
                ip=bd0_device["ip"],
                username=bd0_username,
                password=bd0_password,
                timeout=global_connect_timeout
            )
            print("✅ Connected to BD0!")
        except Exception as conn_error:
            print(f"⚠️ Connection to BD0 failed with default credentials: {conn_error}")
            print("⚠️ Please enter your USWIN credentials for BD0:")
            bd0_username = input("Enter USWIN username: ")
            bd0_password = getpass.getpass("Enter USWIN password: ")
            
            print(f"🔗 Retrying connection to BD0 with USWIN credentials...")
            connection = ConnectHandler(
                device_type=bd0_device["device_type"],
                ip=bd0_device["ip"],
                username=bd0_username,
                password=bd0_password,
                timeout=global_connect_timeout
            )
            print("✅ Connected to BD0 with USWIN credentials!")
        
        # Define EVPN commands
        evpn_queries = [
            (f"show bgp l2vpn evpn rd {b07_rr2_peer_ip}:1 | i prefixes", "RAN routes from B07", 1),
            (f"show bgp l2vpn evpn rd {b06_rr2_peer_ip}:1 | i prefixes", "RAN routes from B06", 1),
            (f"show bgp l2vpn evpn rd {b07_rr2_peer_ip}:2 | i prefixes", "EDN routes from B07", 2),
            (f"show bgp l2vpn evpn rd {b06_rr2_peer_ip}:2 | i prefixes", "EDN routes from B06", 2),
            (f"show bgp l2vpn evpn rd {b07_rr2_peer_ip}:3 | i prefixes", "WSN routes from B07", 3),
            (f"show bgp l2vpn evpn rd {b06_rr2_peer_ip}:3 | i prefixes", "WSN routes from B06", 3),
        ]
        
        for cmd, desc, vprn_id in evpn_queries:
            print(f"\n  ▶ Running: {cmd}")
            try:
                output = connection.send_command(cmd, read_timeout=30)
                results_ws.append([bd0_device["ip"], cmd, output])
                
                # Parse for path count
                # Expected: "Processed 1541 prefixes, 3082 paths"
                # Flexible regex handles singular/plural and variable spacing
                match = re.search(r'Processed\s+(\d+)\s+prefixe?s?\s*,\s*(\d+)\s+paths?', output, re.IGNORECASE)
                
                if match:
                    prefix_count = match.group(1)
                    path_count = match.group(2)
                    print(f"    ✅ {desc}: {prefix_count} prefixes, {path_count} paths")
                    
                    # Add to Neighbors sheet
                    # Using RD as "Neighbor IP" and path count in "BGP EVPN IPv4/IPv6 Prefix (Adv)" column
                    rd_value = f"{b07_rr2_peer_ip if 'B07' in desc else b06_rr2_peer_ip}:{vprn_id}"
                    neighbors_ws.append([
                        bd0_device["ip"],      # Device IP
                        desc,                   # Neighbor Description
                        rd_value,              # Neighbor IP (RD value)
                        "",                     # No of advRoutes (empty)
                        "",                     # No of received Routes (empty)
                        path_count,            # BGP EVPN IPv4/IPv6 Prefix (Adv) - THE PATH COUNT
                        ""                      # BGP EVPN IPv4/IPv6 Prefix (Recv) (empty)
                    ])
                else:
                    print(f"    ⚠️ Could not parse output")
                    neighbors_ws.append([bd0_device["ip"], desc, "", "", "", "PARSE_ERROR", ""])
                
                time.sleep(0.3)
                
            except Exception as e:
                print(f"    ❌ Command failed: {e}")
                neighbors_ws.append([bd0_device["ip"], desc, "", "", "", "ERROR", ""])
        
        connection.disconnect()
        print("\n✅ BD0 EVPN queries completed!")
        
    except Exception as e:
        print(f"❌ Failed to connect to BD0: {e}")
        log_failure(bd0_device["ip"], str(e))
else:
    if not bd0_device:
        print("\n⚠️ No BD0 device found - skipping EVPN queries")
    elif not b06_rr2_peer_ip or not b07_rr2_peer_ip:
        print(f"\n⚠️ Missing RR-2-PEER IPs (B06: {b06_rr2_peer_ip}, B07: {b07_rr2_peer_ip}) - skipping EVPN queries")


# ==============================
# Step 8: Reorder Neighbors by BGP_CONTEXTS
# ==============================
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
    print("✅ Neighbor sheet reordered.")
except Exception as e:
    print(f"⚠️ Sorting skipped: {e}")


# ==============================
# Step 9: Save workbook
# ==============================
wb.save(input_file)
print(f"\n📊 Results, Neighbors, and Interfaces saved in '{input_file}'")
print("✅ Script completed successfully!")
