# Quick Command Reference

## 🚀 Running Scripts

### Main Production Script
```bash
# Run full audit including BD0 EVPN queries
python3 network_audit_enhanced.py
```

### Standalone BD0 Query
```bash
# Add BD0 queries to existing Excel file
python3 query_bd0_evpn.py
```

### Test Parsing Logic
```bash
# Verify regex pattern works correctly
python3 test_evpn_parsing.py
```

---

## 📦 Installation

```bash
# Install required packages
pip install netmiko openpyxl

# Or with specific versions
pip install netmiko==4.3.0 openpyxl==3.1.2
```

---

## 📂 File Operations

```bash
# View Excel file (if xlrd installed)
python3 -c "from openpyxl import load_workbook; wb = load_workbook('network_inputs.xlsx'); print(wb.sheetnames)"

# Check for failed connections
cat failed_connections.log

# View script output
tail -f output.log  # if you redirect: python3 script.py > output.log 2>&1
```

---

## 🔍 Verification

```bash
# Check devices in Excel
python3 << EOF
from openpyxl import load_workbook
wb = load_workbook('network_inputs.xlsx')
ws = wb['Devices']
for row in ws.iter_rows(min_row=2, values_only=True):
    if row and row[0]:
        print(f"{row[0]} | {row[1]} | {row[2] if len(row) > 2 else 'auto'}")
EOF

# Count neighbors in Excel
python3 << EOF
from openpyxl import load_workbook
wb = load_workbook('network_inputs.xlsx')
ws = wb['Neighbors']
print(f"Total neighbors: {ws.max_row - 1}")
EOF
```

---

## 🧪 Testing

```bash
# Run full test suite
python3 test_evpn_parsing.py

# Test single pattern
python3 << EOF
import re
output = "Processed 1541 prefixes, 3082 paths"
match = re.search(r'Processed\s+(\d+)\s+prefixe?s?\s*,\s*(\d+)\s+paths?', output, re.IGNORECASE)
if match:
    print(f"Prefixes: {match.group(1)}, Paths: {match.group(2)}")
else:
    print("No match")
EOF
```

---

## 🔧 Troubleshooting Commands

### Check Connectivity
```bash
# Test SSH to device
ssh NCMSOLK@<device_ip>

# Test from Python
python3 << EOF
from netmiko import ConnectHandler
try:
    conn = ConnectHandler(
        device_type='cisco_nxos',
        ip='<device_ip>',
        username='NCMSOLK',
        password='mhb5N2Ap',
        timeout=10
    )
    print("✅ Connected successfully!")
    conn.disconnect()
except Exception as e:
    print(f"❌ Connection failed: {e}")
EOF
```

### Manual Command Test
```bash
# Test EVPN command manually on BD0
ssh NCMSOLK@<BD0_IP>
show bgp l2vpn evpn rd <RR2_PEER_IP>:1 | i prefixes
# Expected output: "Processed 1541 prefixes, 3082 paths"
```

### Check Excel File Structure
```bash
# Validate Excel has required sheets
python3 << EOF
from openpyxl import load_workbook
wb = load_workbook('network_inputs.xlsx')
required = ['Devices', 'Neighbors', 'Results', 'Interfaces']
for sheet in required:
    status = "✅" if sheet in wb.sheetnames else "❌"
    print(f"{status} {sheet}")
EOF
```

---

## 📊 Data Extraction

### Extract BD0 Results
```bash
# Extract BD0 EVPN results from Excel
python3 << EOF
from openpyxl import load_workbook
wb = load_workbook('network_inputs.xlsx')
ws = wb['Neighbors']
print("BD0 EVPN Results:")
print("-" * 70)
for row in ws.iter_rows(min_row=2, values_only=True):
    if row and 'routes from B0' in str(row[1]):
        desc = row[1]
        paths = row[5]
        print(f"{desc:30} | Paths: {paths}")
EOF
```

### Export to CSV
```bash
# Export Neighbors sheet to CSV
python3 << EOF
from openpyxl import load_workbook
import csv
wb = load_workbook('network_inputs.xlsx')
ws = wb['Neighbors']
with open('neighbors_export.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    for row in ws.iter_rows(values_only=True):
        writer.writerow(row)
print("✅ Exported to neighbors_export.csv")
EOF
```

---

## 🔄 Script Modifications

### Change Timeout
```bash
# Edit script and modify:
global_connect_timeout = 30  # Change from 15 to 30 seconds
```

### Change Credentials
```bash
# Edit script and modify:
default_username = "YOUR_USERNAME"
default_password = "YOUR_PASSWORD"
```

### Add More Devices
```bash
# Edit network_inputs.xlsx or:
python3 << EOF
from openpyxl import load_workbook
wb = load_workbook('network_inputs.xlsx')
ws = wb['Devices']
ws.append(["NEWDEVICEB06", "10.1.1.100", "nokia_sros_ssh"])
wb.save('network_inputs.xlsx')
print("✅ Device added")
EOF
```

---

## 📋 Common Workflows

### Workflow 1: First Time Setup
```bash
# 1. Install dependencies
pip install netmiko openpyxl

# 2. Create Excel file with devices
# (Manually or import from existing source)

# 3. Run script
python3 network_audit_enhanced.py
```

### Workflow 2: Re-run BD0 Queries Only
```bash
# If you already have B06/B07 data
python3 query_bd0_evpn.py
```

### Workflow 3: Update and Re-run
```bash
# 1. Backup existing file
cp network_inputs.xlsx network_inputs_backup_$(date +%Y%m%d).xlsx

# 2. Update devices in Excel
# (Add/remove/modify devices)

# 3. Re-run
python3 network_audit_enhanced.py
```

### Workflow 4: Troubleshooting
```bash
# 1. Test parsing
python3 test_evpn_parsing.py

# 2. Check connection logs
cat failed_connections.log

# 3. Verify Excel structure
python3 -c "from openpyxl import load_workbook; print(load_workbook('network_inputs.xlsx').sheetnames)"

# 4. Test connectivity to one device
# (Use troubleshooting commands above)
```

---

## 🎯 One-Liners

```bash
# Count devices
python3 -c "from openpyxl import load_workbook; print(load_workbook('network_inputs.xlsx')['Devices'].max_row - 1)"

# List BD0 results
python3 -c "from openpyxl import load_workbook; [print(f'{r[1]}: {r[5]}') for r in load_workbook('network_inputs.xlsx')['Neighbors'].iter_rows(min_row=2, values_only=True) if r and 'B0' in str(r[1])]"

# Check if RR-2-PEER exists
python3 -c "from openpyxl import load_workbook; print('Found' if any('RR-2-PEER' in str(r[1]) for r in load_workbook('network_inputs.xlsx')['Neighbors'].iter_rows(min_row=2, values_only=True) if r) else 'Not found')"
```

---

## 🛠️ Advanced Usage

### Run with Logging
```bash
# Capture all output to log file
python3 network_audit_enhanced.py 2>&1 | tee audit_$(date +%Y%m%d_%H%M%S).log
```

### Run in Background
```bash
# Run script in background (Linux/Mac)
nohup python3 network_audit_enhanced.py > audit.log 2>&1 &

# Check progress
tail -f audit.log

# Check if still running
ps aux | grep network_audit_enhanced.py
```

### Parallel Testing
```bash
# Test multiple devices in parallel (advanced)
python3 << EOF
from concurrent.futures import ThreadPoolExecutor
from netmiko import ConnectHandler

def test_device(ip):
    try:
        conn = ConnectHandler(device_type='cisco_nxos', ip=ip, 
                             username='NCMSOLK', password='mhb5N2Ap', timeout=10)
        conn.disconnect()
        return f"✅ {ip}"
    except Exception as e:
        return f"❌ {ip}: {e}"

devices = ['10.1.1.1', '10.1.1.2', '10.1.1.3']
with ThreadPoolExecutor(max_workers=5) as executor:
    results = executor.map(test_device, devices)
    for result in results:
        print(result)
EOF
```

---

## 📚 Documentation Commands

```bash
# View documentation
cat README.md                  # User guide
cat QUICK_START.md            # Quick start
cat BD0_EVPN_QUERIES.md       # Technical details
cat SOLUTION_SUMMARY.md       # Complete overview
cat ARCHITECTURE.md           # Architecture diagrams
cat DELIVERABLES.txt          # Project summary

# Search documentation
grep -i "error" README.md     # Find error handling info
grep -i "excel" *.md          # Find Excel-related docs
```

---

## 🔐 Security Notes

```bash
# IMPORTANT: The script contains embedded credentials
# For production use, consider:

# 1. Use environment variables
export TACACS_USER="your_username"
export TACACS_PASS="your_password"

# 2. Modify script to read from environment:
# username = os.getenv('TACACS_USER')
# password = os.getenv('TACACS_PASS')

# 3. Or use encrypted credentials file
```

---

## 📞 Quick Help

| Task | Command |
|------|---------|
| Run full audit | `python3 network_audit_enhanced.py` |
| Add BD0 queries only | `python3 query_bd0_evpn.py` |
| Test parsing | `python3 test_evpn_parsing.py` |
| Check failures | `cat failed_connections.log` |
| View Excel sheets | `python3 -c "from openpyxl import load_workbook; print(load_workbook('network_inputs.xlsx').sheetnames)"` |
| Count neighbors | `python3 -c "from openpyxl import load_workbook; print(load_workbook('network_inputs.xlsx')['Neighbors'].max_row - 1)"` |

---

**For detailed explanations, see README.md or other documentation files.**
