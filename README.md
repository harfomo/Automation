# Network Automation Scripts

Collection of Python scripts for network device data collection and MOP (Method of Procedure) template processing.

---

## 📁 Files in this Repository

### 1. **network_device_collector.py** (36 KB)
Network device data collection script that connects to Nokia SROS and Cisco NX-OS devices.

**Features:**
- Connects to Nokia SROS routers via SSH
- Connects to Cisco NX-OS switches via SSH (with optional jump-server support)
- Collects BGP neighbor information and route counts
- Collects EVPN routes and path information
- Extracts interface configurations (BD/BM/B4/B2/B16/B17/B18)
- Extracts LAG interface details and thresholds
- Exports all data to Excel (`network_inputs.xlsx`)

**Requirements:**
```bash
pip install netmiko openpyxl paramiko
```

**Usage:**
```bash
python network_device_collector.py
```

**Output:**
- Creates `network_inputs.xlsx` with three sheets:
  - **Devices**: Input device list
  - **Neighbors**: BGP neighbor data with route counts
  - **Interfaces**: Physical and LAG interface information
  - **Results**: Raw command outputs

---

### 2. **replace_ips_in_mop.py** (11 KB)
Simple script to replace neighbor IPs with descriptions in MOP templates.

**Features:**
- Reads IP → Description mappings from `network_inputs.xlsx` (Neighbors sheet)
- Searches and replaces IPs in all sheets of `MOPtemp.xlsx`
- Replaces route counts in regular BGP advertised-routes and received-routes commands
- Replaces EVPN route information with simplified description-based labels
- Creates `MOPtemp_updated.xlsx` (preserves original)

**Requirements:**
```bash
pip install openpyxl
```

**Usage:**
```bash
python replace_ips_in_mop.py
```

**Input Files:**
- `network_inputs.xlsx` (source of mappings)
- `MOPtemp.xlsx` (target for replacements)

**Output:**
- `MOPtemp_updated.xlsx` (updated MOP template)

---

### 3. **replace_ips_in_mop_advanced.py** (15 KB)
Advanced version with more control and options.

**Additional Features:**
- Preview mode (dry run without saving)
- Process only specific sheets
- Overwrite original file option
- Verbose logging
- Detailed change tracking
- Custom file path support

**Usage:**
```bash
# Preview changes without saving
python replace_ips_in_mop_advanced.py --preview

# Save to new file (default)
python replace_ips_in_mop_advanced.py

# Overwrite the original MOPtemp.xlsx
python replace_ips_in_mop_advanced.py --overwrite

# Process only specific sheets
python replace_ips_in_mop_advanced.py --sheets "Sheet1" "Sheet2"

# Verbose mode - see every replacement
python replace_ips_in_mop_advanced.py --verbose

# Combine options
python replace_ips_in_mop_advanced.py --preview --verbose --sheets "Config"

# Custom file paths
python replace_ips_in_mop_advanced.py --network-file "/path/to/network_inputs.xlsx" --mop-file "/path/to/MOP.xlsx"
```

**Command-line Options:**
- `--preview` - Preview changes without saving (dry run)
- `--overwrite` - Overwrite the original MOPtemp.xlsx
- `--sheets SHEET1 SHEET2` - Process only specific sheets
- `--verbose` - Show detailed output for every replacement
- `--network-file PATH` - Custom path to network inputs file
- `--mop-file PATH` - Custom path to MOP template file

---

## 🔄 Workflow

### Step 1: Collect Network Data
```bash
python network_device_collector.py
```

This creates `network_inputs.xlsx` with:
- Device inventory
- BGP neighbor data with IP → Description mappings
- Interface configurations

### Step 2: Replace IPs in MOP Template
```bash
# Simple version
python replace_ips_in_mop.py

# OR advanced version with preview
python replace_ips_in_mop_advanced.py --preview
```

This processes `MOPtemp.xlsx` and:
- Replaces all neighbor IPs with their descriptions
- Replaces route counts with description-based labels

---

## 📊 Example Transformations

### IP Replacement
**Before:**
```
/show router 1 bgp neighbor 10.118.49.117 advertised-routes brief
```

**After:**
```
/show router 1 bgp neighbor RAN_EBGP_VXLAN_V4 advertised-routes brief
```

### Route Count Replacement (in Next Column)

#### Regular BGP Routes
**Before:**
```
Column A: /show router 1 bgp neighbor 10.118.49.117 advertised-routes brief
Column B: 311 routes
```

**After:**
```
Column A: /show router 1 bgp neighbor RAN_EBGP_VXLAN_V4 advertised-routes brief
Column B: RAN_EBGP_VXLAN_V4_adv_routes routes
```

#### EVPN Routes
**Before:**
```
Column A: /show router bgp neighbor 172.31.6.0 advertised-routes evpn
Column B: Auto-Disc-0 routes, IP-Prefix-2471 routes, IPv6-Prefix-8884 routes
```

**After:**
```
Column A: /show router bgp neighbor iBGP-TO-NWCSDEBGB06 advertised-routes evpn
Column B: iBGP-TO-NWCSDEBGB06_BGP_EVPN_Prefix_Adv
```

**Note:** 
- The route count/information is in a **separate column** (next cell in the same row)
- For **regular BGP routes**: Replaces number pattern (e.g., "311 routes" → "{description}_adv_routes routes")
- For **EVPN routes**: Replaces entire cell content with simplified label

---

## 🔧 Configuration

### Device Type Detection (network_device_collector.py)
The script auto-detects device types based on hostname patterns:

- **Nokia SROS**: Hostnames ending with `B06` or `B07`
- **Cisco NX-OS**: Hostnames ending with `BD#`, `BM#`, `B4#`, `B01`, `B02`, `B2C`, `B2D`, `BD0`

### Default Credentials
Hardcoded in `network_device_collector.py`:
- **TACACS**: `NCMSOLK` / `mhb5N2Ap`
- **Jump-server**: `harfomo` / `Aboelhamd0553!!`

⚠️ **Security Note**: Consider using environment variables or a secrets manager instead of hardcoded credentials.

---

## 📋 Excel File Structures

### network_inputs.xlsx

**Devices Sheet:**
| Cilli_Hostname | IP/Hostname | Device_Type (optional) | Proxy_IP | Primary/Secondary | Primary Tab# | Secondary Tab# |
|----------------|-------------|------------------------|----------|-------------------|--------------|----------------|
| NWCSDEBGB06 | 2001:4888:a1f:6332:194:26:0:6 | nokia_sros_ssh | | Primary | 1 | |
| NWCSDEBGB07 | 2001:4888:a1f:6332:194:26:0:7 | nokia_sros_ssh | | Secondary | | 1 |
| NWCSDEBGBD0 | 10.10.10.10 | cisco_nxos | | Primary | 2 | |
| NWCSDEBGB01 | 172.22.22.22 | cisco_nxos | 198.226.102.37 | Secondary | | 2 |

**Neighbors Sheet:**
| Device IP | Neighbor Description | Neighbor IP | No of advRoutes | No of received Routes | BGP EVPN IPv4/IPv6 Prefix (Adv) | BGP EVPN IPv4/IPv6 Prefix (Recv) |
|-----------|---------------------|-------------|-----------------|----------------------|--------------------------------|----------------------------------|
| 10.1.1.1 | RAN_EBGP_MSE_V4 | 192.168.1.100 | 500 | 450 | | |

**Interfaces Sheet:**
| Device IP | Interface Description | Interface Name | Threshold |
|-----------|---------------------|----------------|-----------|
| 10.1.1.1 | BD1 | 1/1/1 | |
| 10.1.1.1 | NWCSDEBGB01_Bundle-Ether1 | lag 1 | 3 |

---

## 🚀 Quick Start

1. **Install Dependencies:**
```bash
pip install netmiko openpyxl paramiko
```

2. **Prepare Device List:**
   - Edit `network_inputs.xlsx` (auto-created on first run)
   - Add your devices to the "Devices" sheet

3. **Collect Network Data:**
```bash
python network_device_collector.py
```

4. **Process MOP Template:**
```bash
# Preview first
python replace_ips_in_mop_advanced.py --preview

# If satisfied, run without preview
python replace_ips_in_mop.py
```

5. **Review Output:**
   - Check `MOPtemp_updated.xlsx`
   - If satisfied, rename to `MOPtemp.xlsx`

---

## 🐛 Troubleshooting

### Connection Issues
- Check network connectivity to devices
- Verify credentials in the script
- Check if jump-server is needed (add Proxy_IP to Devices sheet)
- Review `failed_connections.log` for error details

### Missing Dependencies
```bash
pip install --upgrade netmiko openpyxl paramiko
```

### Excel File Issues
- Ensure Excel files are not open in another application
- Check file permissions
- Verify sheet names match expected format

### No Replacements Made
- Verify `network_inputs.xlsx` Neighbors sheet has data
- Check that Neighbor IP column contains the IPs you want to replace
- Try `--verbose` flag to see detailed processing

---

## 📝 Notes

- The collector script supports both IPv4 and IPv6 addresses
- Jump-server (bastion host) support included for NX-OS devices
- Route count replacement works for both `advertised-routes` and `received-routes`
- All scripts handle paging for long command outputs
- Failed connections are logged to `failed_connections.log`

---

## 🔐 Security Recommendations

1. **Remove hardcoded credentials** - Use environment variables:
```python
import os
username = os.environ.get('NETWORK_USERNAME')
password = os.environ.get('NETWORK_PASSWORD')
```

2. **Use SSH keys** where possible instead of passwords

3. **Restrict file permissions:**
```bash
chmod 600 network_inputs.xlsx
chmod 700 *.py
```

4. **Don't commit credentials** to version control

---

## 📦 Repository

**GitHub:** https://github.com/harfomo/Automation  
**Branch:** cursor/collect-and-parse-network-device-data-0f5b

---

## 📜 License

Internal use only.

---

## 👤 Author

Network Automation Team

---

## 📅 Last Updated

November 6, 2025
