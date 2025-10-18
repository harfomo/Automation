# Update: B01 BGP AS Number Extraction

## Change Summary

Added functionality to query the B01 (Cisco NXOS) device for the BGP AS number and insert it at the top of the Neighbors sheet with description "BGP ID".

---

## What Changed

### New Feature:
- **Query B01 device** for BGP AS number using command: `sh run bgp | i "router bgp"`
- **Extract BGP AS number** from output (e.g., from "router bgp 65000" extract "65000")
- **Insert at top of Neighbors sheet** (row 2, right after header) with description "BGP ID"
- **All other rows pushed down** to maintain data integrity
- **BGP ID row stays at top** even after sorting

---

## Files Updated

### Production Scripts (1):
✅ **`network_audit_enhanced.py`**
- Added `b01_device` and `bgp_as_number` tracking variables
- Added B01 device detection during device loop
- Added Step 7: Query B01 for BGP AS Number (new section)
- Added USWIN credential fallback for B01 connection
- Added Step 9: Insert BGP AS Number at top of Neighbors sheet
- Updated Step 10: Reorder Neighbors (keeps BGP ID at top)
- Updated step numbering (Step 11: Save workbook)

---

## How It Works

### Step-by-Step Process:

1. **Device Detection**: Script identifies device with "B01" in hostname during main loop

2. **After all Nokia/Cisco devices processed**: Script queries B01

3. **B01 Connection**:
   - Try with default/startup credentials
   - If fails, prompt for USWIN credentials (same as BD0)

4. **Execute Command**: `sh run bgp | i "router bgp"`

5. **Parse Output**: Extract BGP AS number using regex `router\s+bgp\s+(\d+)`

6. **Insert into Excel**:
   - Insert new row at position 2 (pushes all data down)
   - Set values:
     - Column 1: B01 Device IP
     - Column 2: "BGP ID"
     - Column 3: BGP AS Number (e.g., "65000")
     - Columns 4-7: Empty

7. **Reorder Sheet**: Sort other neighbors by BGP_CONTEXTS, but keep BGP ID at top

---

## Example Output

### Console Output:
```bash
═══════════════════════════════════════════════════════════════════════════
🔍 QUERYING B01 DEVICE FOR BGP AS NUMBER
═══════════════════════════════════════════════════════════════════════════
B01 Device: NWCSDEBGB01 (10.1.1.5)

🔗 Connecting to B01...
✅ Connected to B01!

  ▶ Running: sh run bgp | i "router bgp"
    ✅ Found BGP AS Number: 65000

✅ B01 BGP AS query completed!

📝 Inserting BGP AS Number (65000) at top of Neighbors sheet...
✅ BGP ID inserted at top of Neighbors sheet
✅ Neighbor sheet reordered (BGP ID kept at top).
```

### Excel Neighbors Sheet (After Update):
```
| Device IP | Neighbor Description | Neighbor IP | Adv | Recv | EVPN(Adv) | EVPN(Recv) |
|-----------|---------------------|-------------|-----|------|-----------|------------|
| 10.1.1.5  | BGP ID              | 65000       |     |      |           |            | ← NEW!
| B06_IP    | RAN_EBGP_MSE_V4     | 10.1.2.1    | 100 | 50   |           |            |
| B06_IP    | EDN_EBGP_MSE_V6     | 2001::1     | 120 | 60   |           |            |
| BD0_IP    | RAN routes from B07 | 10.1.1.20:1 |     |      | 3082      |            |
| ...       | ...                 | ...         | ... | ...  | ...       | ...        |
```

---

## Command Details

### Command Executed:
```bash
sh run bgp | i "router bgp"
```

### Expected Output:
```
router bgp 65000
```

### Parsed Value:
- **BGP AS Number**: `65000`

### Regex Pattern:
```python
r'router\s+bgp\s+(\d+)'
```

---

## Error Handling

### If B01 device not found:
```
⚠️ No B01 device found - skipping BGP AS number query
```
- Neighbors sheet continues without BGP ID row

### If connection fails with default credentials:
```
⚠️ Connection to B01 failed with default credentials
⚠️ Please enter your USWIN credentials for B01:
Enter USWIN username: 
Enter USWIN password:
```

### If command fails:
```
❌ Command failed: <error message>
```
- BGP AS number set to "ERROR"
- Still inserted into sheet for visibility

### If parsing fails:
```
⚠️ Could not parse BGP AS number from output: <output>
```
- BGP AS number set to "ERROR"

---

## Device Requirements

### Excel File Must Include:
- Device with "B01" in hostname (e.g., "NWCSDEBGB01")
- Device type should be `cisco_nxos`

### Example Devices Sheet:
```
| Cilli_Hostname | IP/Hostname | Device_Type |
|----------------|-------------|-------------|
| NWCSDEBGB06    | <B06_IP>    | nokia_sros_ssh |
| NWCSDEBGB07    | <B07_IP>    | nokia_sros_ssh |
| NWCSDEBGB01    | <B01_IP>    | cisco_nxos     | ← Required
| NWCSDEBGBD0    | <BD0_IP>    | cisco_nxos     |
```

---

## Processing Order

1. **Nokia devices** (B06, B07) - Collect RR-2-PEER IPs
2. **Other devices** in the list
3. **B01 device** - Get BGP AS number ← NEW STEP
4. **BD0 device** - Query EVPN routes
5. **Insert BGP ID** at top of Neighbors sheet
6. **Reorder neighbors** (BGP ID stays at top)
7. **Save workbook**

---

## Benefits

✅ **Automatic BGP AS extraction**: No manual lookup needed  
✅ **Top of sheet placement**: Easy to find and reference  
✅ **Always visible**: Stays at top even after sorting  
✅ **USWIN credential support**: Same fallback as BD0  
✅ **Error visibility**: Shows "ERROR" if extraction fails  
✅ **Non-breaking**: Script continues if B01 not found  

---

## Code Structure

### Key Variables:
```python
b01_device = None      # Tracks B01 device
bgp_as_number = None   # Stores extracted BGP AS number
```

### Key Functions:
- **Device detection**: Checks for "B01" in hostname
- **BGP extraction**: Uses regex on "sh run bgp | i \"router bgp\""
- **Row insertion**: `neighbors_ws.insert_rows(2)` pushes data down
- **Sorting logic**: Separates BGP ID row, sorts others, reassembles

---

## Testing Checklist

To test this feature:

- [ ] Add B01 device to Excel file
- [ ] Run script and verify B01 is detected
- [ ] Check console shows "QUERYING B01 DEVICE FOR BGP AS NUMBER"
- [ ] Verify BGP AS number is extracted
- [ ] Open Excel and confirm BGP ID is at row 2 (after header)
- [ ] Verify all other rows are pushed down
- [ ] Confirm BGP ID stays at top after sorting

---

## Status

✅ Feature implemented in `network_audit_enhanced.py`  
✅ USWIN credential fallback for B01  
✅ BGP ID insertion at top of sheet  
✅ Sorting logic updated to preserve BGP ID position  
✅ Error handling for missing B01 or parsing failures  
✅ Ready for testing and deployment  

---

**The script now automatically extracts the BGP AS number from B01 and places it at the top of the Neighbors sheet!** 🎉
