#!/usr/bin/env python3
"""
Script to query EVPN routes from BD0 device using RR-2-PEER IPs from B06/B07.
"""

from netmiko import ConnectHandler
from openpyxl import load_workbook
import getpass
import re
import os
import sys

# Configuration
script_dir = os.path.dirname(os.path.abspath(__file__))
input_file = os.path.join(script_dir, "network_inputs.xlsx")

# Credentials (TACACS/USWIN)
default_username = "NCMSOLK"
default_password = "mhb5N2Ap"
global_connect_timeout = 15

def main():
    # Check if Excel file exists
    if not os.path.exists(input_file):
        print(f"❌ Excel file not found: {input_file}")
        print("➡️ Please ensure the original script has been run first.")
        sys.exit(1)
    
    # Load workbook
    print(f"📂 Loading workbook: {input_file}")
    wb = load_workbook(input_file)
    
    if "Devices" not in wb.sheetnames:
        print("❌ 'Devices' sheet not found in workbook.")
        sys.exit(1)
    
    if "Neighbors" not in wb.sheetnames:
        print("❌ 'Neighbors' sheet not found in workbook.")
        sys.exit(1)
    
    devices_ws = wb["Devices"]
    neighbors_ws = wb["Neighbors"]
    
    # Find BD0 device
    bd0_device = None
    print("\n🔍 Searching for BD0 device...")
    for row in devices_ws.iter_rows(min_row=2, values_only=True):
        if row and row[0] and "BD0" in row[0]:
            bd0_device = {"hostname": row[0], "ip": row[1], "device_type": "cisco_nxos"}
            print(f"✅ Found BD0 device: {bd0_device['hostname']} ({bd0_device['ip']})")
            break
    
    if not bd0_device:
        print("❌ No device with 'BD0' in hostname found.")
        sys.exit(1)
    
    # Find B06 and B07 devices and their RR-2-PEER IPs
    print("\n🔍 Searching for RR-2-PEER IPs from iBGP-TO- neighbors...")
    b06_rr2_ip = None
    b07_rr2_ip = None
    
    for row in neighbors_ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0] or not row[1]:
            continue
        
        device_ip = row[0]
        neighbor_desc = str(row[1])
        neighbor_ip = row[2]
        
        # Check if this is an iBGP-TO- neighbor
        if neighbor_desc.startswith("iBGP-TO-"):
            # Extract peer hostname from description
            peer_hostname = neighbor_desc.replace("iBGP-TO-", "").strip()
            
            # Find which device this neighbor entry belongs to
            for dev_row in devices_ws.iter_rows(min_row=2, values_only=True):
                if dev_row and dev_row[1] == device_ip:
                    hostname = dev_row[0]
                    
                    # B06's RR-2-PEER = iBGP-TO-<B07> on B06 device
                    if peer_hostname.endswith("B07") and "B06" in hostname:
                        b07_rr2_ip = neighbor_ip
                        print(f"✅ Found B07 RR-2-PEER: {neighbor_ip} (from {neighbor_desc} on {hostname})")
                    
                    # B07's RR-2-PEER = iBGP-TO-<B06> on B07 device
                    elif peer_hostname.endswith("B06") and "B07" in hostname:
                        b06_rr2_ip = neighbor_ip
                        print(f"✅ Found B06 RR-2-PEER: {neighbor_ip} (from {neighbor_desc} on {hostname})")
                    
                    break
    
    if not b06_rr2_ip or not b07_rr2_ip:
        print(f"❌ Missing RR-2-PEER IPs:")
        print(f"   B06: {'✅' if b06_rr2_ip else '❌ Not found'}")
        print(f"   B07: {'✅' if b07_rr2_ip else '❌ Not found'}")
        sys.exit(1)
    
    # Build commands
    commands = [
        f"show bgp l2vpn evpn rd {b07_rr2_ip}:1 | i prefixes",
        f"show bgp l2vpn evpn rd {b06_rr2_ip}:1 | i prefixes",
        f"show bgp l2vpn evpn rd {b07_rr2_ip}:2 | i prefixes",
        f"show bgp l2vpn evpn rd {b06_rr2_ip}:2 | i prefixes",
        f"show bgp l2vpn evpn rd {b07_rr2_ip}:3 | i prefixes",
        f"show bgp l2vpn evpn rd {b06_rr2_ip}:3 | i prefixes",
    ]
    
    descriptions = [
        "RAN routes from B07",
        "RAN routes from B06",
        "EDN routes from B07",
        "EDN routes from B06",
        "WSN routes from B07",
        "WSN routes from B06",
    ]
    
    # Connect to BD0 device
    print(f"\n🔗 Connecting to {bd0_device['hostname']} ({bd0_device['ip']})...")
    
    bd0_username = default_username
    bd0_password = default_password
    
    try:
        connection = ConnectHandler(
            device_type=bd0_device["device_type"],
            ip=bd0_device["ip"],
            username=bd0_username,
            password=bd0_password,
            timeout=global_connect_timeout
        )
        print("✅ Connected successfully!")
    except Exception as conn_error:
        print(f"⚠️ Connection failed with default credentials: {conn_error}")
        print("⚠️ Please enter your USWIN credentials for BD0:")
        bd0_username = input("Enter USWIN username: ")
        bd0_password = getpass.getpass("Enter USWIN password: ")
        
        print(f"🔗 Retrying connection to BD0 with USWIN credentials...")
        try:
            connection = ConnectHandler(
                device_type=bd0_device["device_type"],
                ip=bd0_device["ip"],
                username=bd0_username,
                password=bd0_password,
                timeout=global_connect_timeout
            )
            print("✅ Connected successfully with USWIN credentials!")
        except Exception as e:
            print(f"❌ Failed to connect with USWIN credentials: {e}")
            sys.exit(1)
    
    # Execute commands and collect results
    print("\n📊 Executing EVPN commands...")
    results = []
    
    for cmd, desc in zip(commands, descriptions):
        print(f"  ▶ Running: {cmd}")
        try:
            output = connection.send_command(cmd, read_timeout=30)
            
            # Parse output for path count
            # Expected format: "Processed 1541 prefixes, 3082 paths"
            # Flexible regex handles singular/plural and variable spacing
            match = re.search(r'Processed\s+(\d+)\s+prefixe?s?\s*,\s*(\d+)\s+paths?', output, re.IGNORECASE)
            
            if match:
                prefix_count = match.group(1)
                path_count = match.group(2)
                print(f"    ✅ Found: {prefix_count} prefixes, {path_count} paths")
                results.append({
                    "description": desc,
                    "rd": cmd.split("rd ")[1].split(" |")[0],
                    "prefixes": prefix_count,
                    "paths": path_count,
                    "output": output
                })
            else:
                print(f"    ⚠️ Could not parse output: {output[:100]}")
                results.append({
                    "description": desc,
                    "rd": cmd.split("rd ")[1].split(" |")[0],
                    "prefixes": "ERROR",
                    "paths": "ERROR",
                    "output": output
                })
        except Exception as e:
            print(f"    ❌ Command failed: {e}")
            results.append({
                "description": desc,
                "rd": cmd.split("rd ")[1].split(" |")[0],
                "prefixes": "ERROR",
                "paths": "ERROR",
                "output": str(e)
            })
    
    connection.disconnect()
    print("\n✅ Disconnected from BD0")
    
    # Add results to Neighbors sheet
    print("\n📝 Adding results to Neighbors sheet...")
    
    # Add rows with the format:
    # [Device IP, Neighbor Description, Neighbor IP, No of advRoutes, No of received Routes, BGP EVPN IPv4/IPv6 Prefix (Adv), BGP EVPN IPv4/IPv6 Prefix (Recv)]
    for result in results:
        neighbors_ws.append([
            bd0_device["ip"],              # Device IP
            result["description"],          # Neighbor Description
            result["rd"],                   # RD (using as "Neighbor IP" proxy)
            "",                             # No of advRoutes (empty)
            "",                             # No of received Routes (empty)
            result["paths"],                # BGP EVPN IPv4/IPv6 Prefix (Adv) - the path count
            ""                              # BGP EVPN IPv4/IPv6 Prefix (Recv) (empty)
        ])
        print(f"  ✅ Added: {result['description']} - {result['paths']} paths")
    
    # Save workbook
    wb.save(input_file)
    print(f"\n💾 Workbook saved: {input_file}")
    print("✅ Script completed successfully!")
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY OF EVPN ROUTES")
    print("="*60)
    for result in results:
        print(f"{result['description']:25} | RD: {result['rd']:20} | Paths: {result['paths']}")
    print("="*60)

if __name__ == "__main__":
    main()
