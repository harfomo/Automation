# Update: Credential Testing in Standalone Script

## Change Summary

Added credential testing at the start of the standalone script (`query_bd0_evpn.py`) to verify credentials work on B01 before attempting full connection.

---

## Problem

The standalone script was failing to connect to B01 even when default credentials were correct, because:

1. **No credential validation** - Script used hardcoded credentials without testing
2. **Poor error visibility** - Generic connection errors didn't help diagnose issues
3. **No early failure** - Failed connection only discovered deep in script execution

---

## Solution

Added credential testing function that:

1. **Tests credentials early** - Validates on B01 before starting main work
2. **Provides clear feedback** - Shows exactly what's working or failing
3. **Allows manual override** - Prompts for credentials if defaults fail
4. **Uses tested credentials** - Same credentials for both B01 and BD0

---

## What Changed

### New Function Added:

```python
def test_credentials(device_ip, device_type, username, password):
    """Test if credentials work on a device."""
    try:
        print(f"  🔐 Testing credentials on {device_ip}...")
        conn = ConnectHandler(
            device_type=device_type,
            ip=device_ip,
            username=username,
            password=password,
            timeout=global_connect_timeout
        )
        conn.disconnect()
        print(f"  ✅ Credentials work on {device_ip}")
        return True
    except Exception as e:
        print(f"  ⚠️ Credentials failed on {device_ip}: {e}")
        return False
```

### Credential Testing Flow:

```python
# Test credentials on B01 first if it exists
credentials_username = default_username
credentials_password = default_password

if b01_device:
    print("\n🔐 Testing default credentials on B01...")
    if not test_credentials(b01_device["ip"], b01_device["device_type"], 
                           credentials_username, credentials_password):
        print("⚠️ Default credentials don't work on B01.")
        print("⚠️ Please enter your credentials:")
        credentials_username = input("Enter username: ")
        credentials_password = getpass.getpass("Enter password: ")
        
        print(f"\n🔐 Testing provided credentials on B01...")
        if not test_credentials(b01_device["ip"], b01_device["device_type"],
                               credentials_username, credentials_password):
            print("❌ Provided credentials also failed on B01.")
            print("⚠️ Continuing with BD0 queries only (B01 will be skipped)")
            b01_device = None  # Skip B01 if credentials don't work
```

### Connection Updated:

```python
# OLD: Used separate credential handling with fallback
b01_username = default_username
b01_password = default_password
try:
    conn_b01 = ConnectHandler(username=b01_username, ...)
except:
    # Prompt for USWIN and retry

# NEW: Uses already tested credentials
conn_b01 = ConnectHandler(
    username=credentials_username,  # Already tested and working
    password=credentials_password,
    ...
)
```

---

## Example Output

### Scenario 1: Default Credentials Work

```bash
$ python3 query_bd0_evpn.py

📂 Loading workbook: network_inputs.xlsx

🔍 Searching for BD0 and B01 devices...
✅ Found BD0 device: NWCSDEBGBD0 (10.1.1.1)
✅ Found B01 device: NWCSDEBGB01 (10.1.1.5)

🔐 Testing default credentials on B01...
  🔐 Testing credentials on 10.1.1.5...
  ✅ Credentials work on 10.1.1.5

🔍 Searching for RR-2-PEER IPs from iBGP-TO- neighbors...
✅ Found B07 RR-2-PEER: 10.1.1.20
✅ Found B06 RR-2-PEER: 10.1.1.10

═══════════════════════════════════════════════════════════════════════════
🔍 QUERYING B01 DEVICE FOR BGP AS NUMBER
═══════════════════════════════════════════════════════════════════════════
B01 Device: NWCSDEBGB01 (10.1.1.5)

🔗 Connecting to B01...
✅ Connected to B01!

  ▶ Running: sh run bgp | i "router bgp"
    ✅ Found BGP AS Number: 65000
```

### Scenario 2: Default Credentials Fail, Manual Entry

```bash
$ python3 query_bd0_evpn.py

📂 Loading workbook: network_inputs.xlsx

🔍 Searching for BD0 and B01 devices...
✅ Found BD0 device: NWCSDEBGBD0 (10.1.1.1)
✅ Found B01 device: NWCSDEBGB01 (10.1.1.5)

🔐 Testing default credentials on B01...
  🔐 Testing credentials on 10.1.1.5...
  ⚠️ Credentials failed on 10.1.1.5: Authentication failed

⚠️ Default credentials don't work on B01.
⚠️ Please enter your credentials:
Enter username: john.doe
Enter password: ********

🔐 Testing provided credentials on B01...
  🔐 Testing credentials on 10.1.1.5...
  ✅ Credentials work on 10.1.1.5

🔍 Searching for RR-2-PEER IPs from iBGP-TO- neighbors...
✅ Found B07 RR-2-PEER: 10.1.1.20
✅ Found B06 RR-2-PEER: 10.1.1.10

═══════════════════════════════════════════════════════════════════════════
🔍 QUERYING B01 DEVICE FOR BGP AS NUMBER
═══════════════════════════════════════════════════════════════════════════
B01 Device: NWCSDEBGB01 (10.1.1.5)

🔗 Connecting to B01...
✅ Connected to B01!

  ▶ Running: sh run bgp | i "router bgp"
    ✅ Found BGP AS Number: 65000
```

### Scenario 3: No Working Credentials, Skip B01

```bash
$ python3 query_bd0_evpn.py

📂 Loading workbook: network_inputs.xlsx

🔍 Searching for BD0 and B01 devices...
✅ Found BD0 device: NWCSDEBGBD0 (10.1.1.1)
✅ Found B01 device: NWCSDEBGB01 (10.1.1.5)

🔐 Testing default credentials on B01...
  🔐 Testing credentials on 10.1.1.5...
  ⚠️ Credentials failed on 10.1.1.5: Authentication failed

⚠️ Default credentials don't work on B01.
⚠️ Please enter your credentials:
Enter username: wrong_user
Enter password: ********

🔐 Testing provided credentials on B01...
  🔐 Testing credentials on 10.1.1.5...
  ⚠️ Credentials failed on 10.1.1.5: Authentication failed

❌ Provided credentials also failed on B01.
⚠️ Continuing with BD0 queries only (B01 will be skipped)

🔍 Searching for RR-2-PEER IPs from iBGP-TO- neighbors...
✅ Found B07 RR-2-PEER: 10.1.1.20
✅ Found B06 RR-2-PEER: 10.1.1.10

⚠️ No B01 device found - skipping BGP AS number query

🔗 Connecting to NWCSDEBGBD0 (10.1.1.1)...
✅ Connected successfully!
```

---

## Benefits

✅ **Early validation** - Tests credentials before doing main work  
✅ **Better error messages** - Shows exactly what failed and when  
✅ **User-friendly** - Prompts for credentials if needed  
✅ **Graceful degradation** - Skips B01 if credentials don't work  
✅ **Consistent credentials** - Uses same tested credentials for B01 and BD0  
✅ **Shows actual error** - Displays connection error details  

---

## Why This Fixes the Issue

### Before:
- Script used hardcoded credentials blindly
- Connection attempt happened deep in execution
- Error message was generic
- No way to test credentials early

### After:
- Script tests credentials immediately after loading Excel
- Shows exact error from connection attempt
- Allows user to provide correct credentials
- Can skip B01 if credentials don't work

### If Default Credentials Are Correct:
- Test succeeds immediately
- Shows "✅ Credentials work on 10.1.1.5"
- No prompts, proceeds with queries

### If They're Actually Wrong:
- Test shows exact error
- User prompted for correct credentials
- Retests before proceeding

---

## Technical Details

### test_credentials() Function:
- **Purpose**: Validate credentials on a device
- **Returns**: True if connection succeeds, False otherwise
- **Side effect**: Prints status messages with emojis for clarity
- **Error handling**: Catches all exceptions and shows error details

### Credential Flow:
1. Load devices from Excel
2. Initialize credentials with defaults
3. If B01 exists, test credentials on it
4. If test fails, prompt for new credentials
5. Retest with new credentials
6. If still fails, set b01_device = None (skip it)
7. Use tested credentials for all subsequent connections

---

## Files Updated

✅ **query_bd0_evpn.py**
- Added test_credentials() function (18 lines)
- Added credential testing flow after device discovery (16 lines)
- Updated B01 connection to use tested credentials (simplified)
- Updated BD0 connection to use tested credentials

✅ **UPDATE_CREDENTIAL_TEST.md**
- Complete documentation of the change

---

## Status

✅ Credential testing implemented  
✅ Early validation before main work  
✅ Clear error messages with details  
✅ Manual credential entry option  
✅ Graceful handling of auth failures  
✅ Ready to commit  

---

**The standalone script now tests credentials on B01 FIRST and shows exactly why connection fails if it does!** 🎉
