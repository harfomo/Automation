# Update: USWIN Credential Prompts

## Change Summary

Updated the credential prompt to ask for "USWIN username and password" instead of generic "TACACS username and password" when default credentials fail.

---

## What Changed

### Before:
```
⚠️ Default credentials failed — please enter manually.
Enter TACACS username: 
Enter TACACS password:
```

### After:
```
⚠️ Default credentials failed — please enter your USWIN credentials.
Enter USWIN username: 
Enter USWIN password:
```

---

## Files Updated

### Production Scripts (1):
✅ **`network_audit_enhanced.py`**
- Changed prompt from "Enter TACACS username" → "Enter USWIN username"
- Changed prompt from "Enter TACACS password" → "Enter USWIN password"
- Changed message from "please enter manually" → "please enter your USWIN credentials"

### Documentation (6):
✅ **`README.md`**
- Updated credentials section to mention USWIN

✅ **`QUICK_START.md`**
- Updated checklist: "TACACS credentials" → "TACACS/USWIN credentials"

✅ **`START_HERE.md`**
- Updated requirements: "TACACS credentials" → "TACACS/USWIN credentials"

✅ **`BD0_EVPN_QUERIES.md`**
- Updated network access section
- Updated testing checklist

✅ **`DELIVERABLES.txt`**
- Updated network access requirements

✅ **`SOLUTION_SUMMARY.md`**
- Updated network requirements section

---

## How It Works

1. **Script tries default credentials first**:
   - Username: `NCMSOLK`
   - Password: `mhb5N2Ap`

2. **If default credentials fail**:
   - Displays: "⚠️ Default credentials failed — please enter your USWIN credentials."
   - Prompts for: "Enter USWIN username:"
   - Prompts for: "Enter USWIN password:" (hidden input)

3. **Uses provided credentials for all devices**

---

## Example Output

```bash
$ python3 network_audit_enhanced.py

🔐 Using embedded TACACS credentials by default.
🔐 Testing default TACACS credentials on 2001:4888:a1f:6332::6 ...
⚠️ Default credentials failed — please enter your USWIN credentials.
Enter USWIN username: your_uswin_username
Enter USWIN password: ********

🔗 Connecting to 2001:4888:a1f:6332::6 (NWCSDEBGB06) — detected type: nokia_sros_ssh
✅ Connected successfully!
```

---

## Benefits

- **Clearer user communication**: Users immediately know they need USWIN credentials
- **Better UX**: No confusion about what credentials to provide
- **Consistent terminology**: Aligns with corporate authentication system

---

## Status

✅ Scripts updated  
✅ Documentation updated  
✅ Ready to use  

When default credentials fail, the script will now clearly ask for USWIN credentials!
