# Update: USWIN Credentials for BD0 Connection

## Change Summary

Updated the scripts to ask for **USWIN credentials specifically for BD0 device** if the default credentials fail when connecting to BD0.

---

## What Changed

### Before:
- If BD0 connection failed with default credentials → Script would fail and log error
- No retry mechanism
- No USWIN credential prompt for BD0

### After:
- If BD0 connection fails with default credentials → **Prompts for USWIN credentials**
- Automatically retries connection with USWIN credentials
- Continues with EVPN queries if USWIN credentials work

---

## Files Updated

### Production Scripts (2):
✅ **`network_audit_enhanced.py`**
- Added try-except for BD0 connection
- Prompts for USWIN credentials if default fails
- Retries connection with USWIN credentials

✅ **`query_bd0_evpn.py`**
- Added try-except for BD0 connection
- Prompts for USWIN credentials if default fails
- Retries connection with USWIN credentials
- Added `getpass` import

---

## How It Works

### For Nokia Devices (B06, B07):
- Uses the credentials tested at script startup (default or manually entered)
- No change in behavior

### For BD0 Device (Cisco NXOS):
1. **First attempt**: Try with default/startup credentials
2. **If that fails**: 
   - Display: "⚠️ Connection to BD0 failed with default credentials"
   - Display: "⚠️ Please enter your USWIN credentials for BD0:"
   - Prompt: "Enter USWIN username:"
   - Prompt: "Enter USWIN password:"
3. **Retry connection** with USWIN credentials
4. **If successful**: Continue with EVPN queries
5. **If still fails**: Log error and skip BD0 queries

---

## Example Output

### Scenario 1: Default Credentials Work
```bash
🔍 QUERYING BD0 DEVICE FOR EVPN ROUTES
BD0 Device: NWCSDEBGBD0 (10.1.1.1)
B06 RR-2-PEER IP: 10.1.1.10
B07 RR-2-PEER IP: 10.1.1.20

🔗 Connecting to BD0...
✅ Connected to BD0!

  ▶ Running: show bgp l2vpn evpn rd 10.1.1.20:1 | i prefixes
    ✅ RAN routes from B07: 1541 prefixes, 3082 paths
```

### Scenario 2: Default Credentials Fail, USWIN Works
```bash
🔍 QUERYING BD0 DEVICE FOR EVPN ROUTES
BD0 Device: NWCSDEBGBD0 (10.1.1.1)
B06 RR-2-PEER IP: 10.1.1.10
B07 RR-2-PEER IP: 10.1.1.20

🔗 Connecting to BD0...
⚠️ Connection to BD0 failed with default credentials: Authentication failed
⚠️ Please enter your USWIN credentials for BD0:
Enter USWIN username: john.doe
Enter USWIN password: ********

🔗 Retrying connection to BD0 with USWIN credentials...
✅ Connected to BD0 with USWIN credentials!

  ▶ Running: show bgp l2vpn evpn rd 10.1.1.20:1 | i prefixes
    ✅ RAN routes from B07: 1541 prefixes, 3082 paths
```

---

## Why This Approach?

BD0 is a **Cisco NXOS device** that may have different authentication requirements than the Nokia devices (B06/B07). This change allows:

1. **Flexibility**: Different credentials for different device types
2. **Continuity**: Script doesn't fail if BD0 needs different credentials
3. **User-friendly**: Clear prompts explain what's needed
4. **Automatic retry**: No need to re-run the entire script

---

## Code Changes

### network_audit_enhanced.py (lines ~601-628)
```python
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
```

---

## Benefits

✅ **Automatic fallback**: If default credentials don't work for BD0, prompts for USWIN  
✅ **Device-specific**: Only affects BD0 connection, not Nokia devices  
✅ **No script re-run needed**: Retries immediately with new credentials  
✅ **Clear messaging**: User knows exactly what's happening and what to do  
✅ **Production-ready**: Handles authentication differences gracefully  

---

## Testing Checklist

To test this feature:

- [ ] Run script with BD0 that accepts default credentials
  - Should connect normally without prompting
  
- [ ] Run script with BD0 that requires USWIN credentials
  - Should prompt for USWIN credentials
  - Should retry and connect successfully
  
- [ ] Provide wrong USWIN credentials
  - Should fail gracefully and log error

---

## Status

✅ Both scripts updated (`network_audit_enhanced.py` & `query_bd0_evpn.py`)  
✅ USWIN prompts added specifically for BD0 connection  
✅ Automatic retry mechanism implemented  
✅ Ready for testing and deployment  

---

**The script now handles BD0 authentication failures gracefully by prompting for USWIN credentials!** 🎉
