# Network Audit Scripts

This workspace contains scripts for auditing network devices (Nokia SROS and Cisco NXOS) and collecting BGP/EVPN data.

## Files

1. **`code11`** - Original network audit script
2. **`network_audit_enhanced.py`** - Enhanced script with BD0 EVPN queries
3. **`query_bd0_evpn.py`** - Standalone script to add BD0 queries to existing Excel file

## Features

### Enhanced Script (`network_audit_enhanced.py`)

This is a complete solution that:
- Connects to Nokia SROS devices (B06, B07) and collects BGP neighbor data
- Extracts RR-2-PEER IP addresses from B06 and B07
- Automatically connects to Cisco NXOS BD0 device
- Queries EVPN routes using the collected RR-2-PEER IPs
- Saves path counts to the Neighbors sheet

### What Gets Added to Neighbors Sheet

From the BD0 device, the script adds 6 new rows:

| Description | RD Value | Path Count Column |
|-------------|----------|-------------------|
| RAN routes from B07 | `<B07_RR2_IP>:1` | BGP EVPN IPv4/IPv6 Prefix (Adv) |
| RAN routes from B06 | `<B06_RR2_IP>:1` | BGP EVPN IPv4/IPv6 Prefix (Adv) |
| EDN routes from B07 | `<B07_RR2_IP>:2` | BGP EVPN IPv4/IPv6 Prefix (Adv) |
| EDN routes from B06 | `<B06_RR2_IP>:2` | BGP EVPN IPv4/IPv6 Prefix (Adv) |
| WSN routes from B07 | `<B07_RR2_IP>:3` | BGP EVPN IPv4/IPv6 Prefix (Adv) |
| WSN routes from B06 | `<B06_RR2_IP>:3` | BGP EVPN IPv4/IPv6 Prefix (Adv) |

The path count is extracted from output like:
```
Processed 1541 prefixes, 3082 paths
```
The value `3082` is saved in the "BGP EVPN IPv4/IPv6 Prefix (Adv)" column.

## Usage

### Option 1: Run Enhanced Script (Recommended)

This does everything in one go:

```bash
python3 network_audit_enhanced.py
```

**Prerequisites:**
1. Create or update `network_inputs.xlsx` with your devices:
   - At least one device with hostname ending in **B06**
   - At least one device with hostname ending in **B07**
   - At least one device with hostname containing **BD0**

Example Excel format:
```
| Cilli_Hostname    | IP/Hostname              | Device_Type       |
|-------------------|--------------------------|-------------------|
| NWCSDEBGB06       | 2001:4888:a1f:6332::6    | nokia_sros_ssh    |
| NWCSDEBGB07       | 2001:4888:a1f:6332::7    | nokia_sros_ssh    |
| NWCSDEBGBD0       | 10.1.1.1                 | cisco_nxos        |
```

### Option 2: Add BD0 Queries to Existing File

If you already ran the original script and have the Excel file with data:

```bash
python3 query_bd0_evpn.py
```

This script:
- Loads existing `network_inputs.xlsx`
- Finds B06/B07 RR-2-PEER IPs from the Neighbors sheet
- Connects to BD0
- Adds the 6 EVPN query results

## Commands Executed on BD0

The script runs these Cisco NXOS commands:

```bash
show bgp l2vpn evpn rd <B07_RR2_IP>:1 | i prefixes
show bgp l2vpn evpn rd <B06_RR2_IP>:1 | i prefixes
show bgp l2vpn evpn rd <B07_RR2_IP>:2 | i prefixes
show bgp l2vpn evpn rd <B06_RR2_IP>:2 | i prefixes
show bgp l2vpn evpn rd <B07_RR2_IP>:3 | i prefixes
show bgp l2vpn evpn rd <B06_RR2_IP>:3 | i prefixes
```

Where:
- **RD :1** = RAN routes
- **RD :2** = EDN routes
- **RD :3** = WSN routes

## Credentials

Default TACACS credentials are embedded:
- **Username**: `NCMSOLK`
- **Password**: `mhb5N2Ap`

If these fail, you'll be prompted to enter your USWIN username and password.

## Output

All scripts create/update `network_inputs.xlsx` with three sheets:

1. **Devices** - Input device list
2. **Results** - Raw command outputs
3. **Neighbors** - BGP neighbor information with route counts (includes BD0 EVPN data)
4. **Interfaces** - Interface descriptions and LAG thresholds

## Troubleshooting

### "No BD0 device found"
- Ensure your Excel file has a device with "BD0" in the hostname

### "Missing RR-2-PEER IPs"
- The B06 and B07 devices must be queried first
- They must have iBGP-TO- neighbors configured
- B07 should have "iBGP-TO-<hostname_ending_with_B06>" neighbor
- B06 should have "iBGP-TO-<hostname_ending_with_B07>" neighbor
- Check the Neighbors sheet for iBGP-TO- entries

### Connection timeouts
- Increase `global_connect_timeout` in the script (default: 15 seconds)
- Check network connectivity to devices

### Parse errors
- The script expects output format: `Processed X prefixes, Y paths`
- If your NXOS version has different output, adjust the regex pattern

## Requirements

```bash
pip install netmiko openpyxl
```

## Notes

- The enhanced script processes Nokia devices first to collect RR-2-PEER IPs
- BD0 queries run at the end after all other devices
- Failed connections are logged to `failed_connections.log`
- The script handles paginated output (`--More--` prompts) automatically
