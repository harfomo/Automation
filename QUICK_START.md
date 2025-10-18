# Quick Start Guide: BD0 EVPN Queries

## 🚀 Get Started in 3 Steps

### Step 1: Prepare Your Excel File

Create or edit `network_inputs.xlsx` with at least these devices:

```
| Cilli_Hostname | IP/Hostname | Device_Type     |
|----------------|-------------|-----------------|
| NWCSDEBGB06    | <your_IP>   | nokia_sros_ssh  |
| NWCSDEBGB07    | <your_IP>   | nokia_sros_ssh  |
| NWCSDEBGBD0    | <your_IP>   | cisco_nxos      |
```

**Important**: Hostnames must contain "B06", "B07", and "BD0"

---

### Step 2: Install Dependencies

```bash
pip install netmiko openpyxl
```

---

### Step 3: Run the Script

```bash
python3 network_audit_enhanced.py
```

**That's it!** The script will:
- ✅ Query B06 and B07 for iBGP-TO- neighbor IPs (RR-2-PEER IPs)
- ✅ Query BD0 for EVPN routes using those IPs
- ✅ Save everything to Excel

---

## 📊 What You'll Get

### In the "Neighbors" sheet, you'll see 6 new rows:

| Description | What It Shows |
|-------------|---------------|
| RAN routes from B07 | Path count for RAN network from B07 |
| RAN routes from B06 | Path count for RAN network from B06 |
| EDN routes from B07 | Path count for EDN network from B07 |
| EDN routes from B06 | Path count for EDN network from B06 |
| WSN routes from B07 | Path count for WSN network from B07 |
| WSN routes from B06 | Path count for WSN network from B06 |

The **path count** appears in the "BGP EVPN IPv4/IPv6 Prefix (Adv)" column.

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| "No BD0 device found" | Add device with "BD0" in hostname to Excel |
| "Missing RR-2-PEER IPs" | Ensure B06 has iBGP-TO-<B07> and B07 has iBGP-TO-<B06> neighbors |
| Connection timeout | Check network connectivity and credentials |
| Parse error | Verify NXOS output format with test script |

---

## 📋 Advanced Options

### Already have data? Just add BD0 queries:
```bash
python3 query_bd0_evpn.py
```

### Test if parsing works:
```bash
python3 test_evpn_parsing.py
```

### Check failed connections:
```bash
cat failed_connections.log
```

---

## 📖 Need More Details?

- **README.md** - Complete user guide
- **BD0_EVPN_QUERIES.md** - Technical details
- **SOLUTION_SUMMARY.md** - Full solution overview

---

## ✅ Checklist Before Running

- [ ] Excel file has B06, B07, and BD0 devices
- [ ] Can SSH to all devices
- [ ] TACACS credentials work (embedded: NCMSOLK / mhb5N2Ap)
- [ ] Python packages installed (netmiko, openpyxl)

---

**Ready?** Run `python3 network_audit_enhanced.py` and you're all set! 🎉
