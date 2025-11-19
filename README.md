# Network Automation Script - Documentation Suite

## 📚 Welcome

This documentation suite provides comprehensive understanding of the network automation script that collects configuration data from Nokia SROS and Cisco NX-OS/IOS-XR devices.

---

## 🎯 What This Script Does

The script:
- Connects to Nokia and Cisco network devices
- Collects BGP neighbor information and route counts
- Gathers interface and LAG configuration data
- Organizes all data into an Excel workbook
- Supports jump-server (proxy) connections
- Implements smart credential caching to minimize 2FA prompts

---

## 📖 Documentation Files

### 1. **SCRIPT_DOCUMENTATION.md** - The Complete Guide
**Best for**: Understanding the entire script architecture, detailed explanations, and comprehensive modification guide

**Contents**:
- Architecture overview and script flow
- Input/Output file formats
- Device types and roles (Primary, Secondary, Tab devices)
- Authentication flow with credential caching
- Processing phases (Nokia → Cisco)
- Key function explanations
- Data collection details
- Modification guide with examples
- Troubleshooting section

**Start here if**: You're new to the script or need in-depth understanding

---

### 2. **QUICK_REFERENCE.md** - The Cheat Sheet
**Best for**: Quick lookups, command reference, and common modifications

**Contents**:
- Device type cheat sheet
- Authentication flow summary
- Output sheet descriptions
- Commands by device type
- Common modification patterns
- Function location reference
- Debugging tips
- Troubleshooting table

**Start here if**: You need quick answers or want to make a specific change

---

### 3. **FLOW_DIAGRAM.md** - The Visual Guide
**Best for**: Understanding execution flow, decision paths, and data movement

**Contents**:
- High-level script flow diagram
- Phase 1 (Nokia) processing flow
- Phase 2 (Cisco) processing flow
- Authentication flow detail
- Data extraction flow charts
- Device role decision tree
- Credential cache flow
- Data flow summary

**Start here if**: You're a visual learner or need to understand the overall flow

---

### 4. **PARSER_REFERENCE.md** - The Parser Bible
**Best for**: Understanding/modifying data extraction logic and regex patterns

**Contents**:
- All parser functions explained
- Input/output formats for each parser
- Regex pattern breakdowns
- Nokia BGP neighbor parsers
- Interface parsers (BD, BM, B4, B2, LAG)
- Route count parsers
- Cisco parsers (EVPN, BGP AS, Bundle-Ether)
- Helper function details
- Testing guidelines
- Modification examples

**Start here if**: You need to modify parsing logic or add new data extraction

---

## 🚀 Getting Started

### For First-Time Users

1. **Read SCRIPT_DOCUMENTATION.md** (Section: Architecture Overview)
   - Understand what the script does
   - Learn about device types and roles
   - Review input/output formats

2. **Check QUICK_REFERENCE.md** (Section: Pre-Flight Checklist)
   - Verify prerequisites
   - Ensure Excel file is properly formatted
   - Confirm network connectivity

3. **Review FLOW_DIAGRAM.md** (Section: High-Level Flow)
   - Visualize the script execution
   - Understand the two processing phases

4. **Run the Script**
   - Start with a single test device
   - Check Results sheet for raw outputs
   - Verify Neighbors and Interfaces sheets

### For Developers Making Modifications

1. **Identify What You Need to Change**
   - New device type? → SCRIPT_DOCUMENTATION.md (Modification Guide)
   - New command? → QUICK_REFERENCE.md (Common Modifications)
   - New parser? → PARSER_REFERENCE.md (Parser Modifications)
   - New BGP context? → SCRIPT_DOCUMENTATION.md (Add New BGP Context)

2. **Understand the Current Implementation**
   - Find the relevant function in PARSER_REFERENCE.md
   - Check the flow diagram in FLOW_DIAGRAM.md
   - Review examples in QUICK_REFERENCE.md

3. **Make Your Changes**
   - Follow the modification patterns provided
   - Test with a single device first
   - Check Results sheet to verify commands ran correctly

4. **Verify the Output**
   - Confirm data appears in correct sheet
   - Check for parsing errors
   - Test with multiple devices

---

## 📋 Common Use Cases

### Use Case 1: "I need to add a new site"
**Documents needed**: QUICK_REFERENCE.md

1. Check "Device Types Cheat Sheet" for hostname patterns
2. Add devices to Excel Devices sheet
3. Run script
4. Review output sheets

---

### Use Case 2: "I need to understand how BGP neighbors are collected"
**Documents needed**: SCRIPT_DOCUMENTATION.md, PARSER_REFERENCE.md, FLOW_DIAGRAM.md

1. Read SCRIPT_DOCUMENTATION.md → "Data Collection Details" → BGP Context List
2. Read PARSER_REFERENCE.md → "BGP Neighbor Parsers" → `extract_neighbors()`
3. Review FLOW_DIAGRAM.md → "Data Extraction Flow" → Nokia BGP Neighbor Route Collection
4. Check QUICK_REFERENCE.md → "Commands by Device Type" → Nokia Primary

---

### Use Case 3: "Script fails to connect to a device"
**Documents needed**: QUICK_REFERENCE.md, SCRIPT_DOCUMENTATION.md

1. Check QUICK_REFERENCE.md → "Troubleshooting Guide" table
2. Review failed_connections.log file
3. Check SCRIPT_DOCUMENTATION.md → "Authentication Flow"
4. Verify device IP, credentials, and network connectivity

---

### Use Case 4: "I need to add support for a new interface type (e.g., B5)"
**Documents needed**: PARSER_REFERENCE.md, QUICK_REFERENCE.md, SCRIPT_DOCUMENTATION.md

1. Read PARSER_REFERENCE.md → "Interface Parsers" → "Generic Interface Parser"
2. Copy pattern from PARSER_REFERENCE.md → "Common Parser Modifications" → "Add New Interface Type"
3. Check QUICK_REFERENCE.md → "Key Function Locations" for line numbers
4. Read SCRIPT_DOCUMENTATION.md → "Modification Guide" → "Add New Interface Type" for complete example
5. Test with device that has B5 interfaces

---

### Use Case 5: "I need to add a new BGP context"
**Documents needed**: SCRIPT_DOCUMENTATION.md, QUICK_REFERENCE.md

1. Read SCRIPT_DOCUMENTATION.md → "Data Collection Details" → "BGP Context List"
2. Follow QUICK_REFERENCE.md → "Common Modifications" → "Add New BGP Context"
3. Update BGP_CONTEXTS list (line ~483)
4. Update `get_router_for_context()` if new router ID needed (line ~461)

---

### Use Case 6: "I need to change the default credentials"
**Documents needed**: QUICK_REFERENCE.md

1. Check QUICK_REFERENCE.md → "Common Modifications" → "Change Default Credentials"
2. Edit lines 244-252 in script
3. Test connection with new credentials

---

### Use Case 7: "I don't understand what a specific function does"
**Documents needed**: PARSER_REFERENCE.md, QUICK_REFERENCE.md

1. Check QUICK_REFERENCE.md → "Key Function Locations" for line number
2. Read PARSER_REFERENCE.md → find function name
3. Review input format, regex patterns, and output examples

---

### Use Case 8: "Parser isn't working correctly"
**Documents needed**: PARSER_REFERENCE.md, QUICK_REFERENCE.md

1. Check Results sheet for raw command output
2. Read PARSER_REFERENCE.md → find parser function
3. Test regex pattern online at regex101.com
4. Follow PARSER_REFERENCE.md → "Testing Parsers" section
5. Use QUICK_REFERENCE.md → "Debugging Tips"

---

## 🔍 Document Quick Lookup

| I want to... | Check this document | Section |
|-------------|---------------------|---------|
| Understand overall architecture | SCRIPT_DOCUMENTATION.md | Architecture Overview |
| See visual flow diagram | FLOW_DIAGRAM.md | High-Level Flow |
| Find device type patterns | QUICK_REFERENCE.md | Device Types Cheat Sheet |
| Understand authentication | SCRIPT_DOCUMENTATION.md | Authentication Flow |
| See authentication flow chart | FLOW_DIAGRAM.md | Authentication Flow Detail |
| Learn about device roles | SCRIPT_DOCUMENTATION.md | Device Types and Roles |
| Find commands for specific device | QUICK_REFERENCE.md | Commands by Device Type |
| Understand a parser function | PARSER_REFERENCE.md | Specific parser section |
| See parser input/output examples | PARSER_REFERENCE.md | Each parser explanation |
| Learn regex patterns | PARSER_REFERENCE.md | Regex Pattern Reference |
| Make common modifications | QUICK_REFERENCE.md | Common Modifications |
| See detailed modification examples | SCRIPT_DOCUMENTATION.md | Modification Guide |
| Find function line numbers | QUICK_REFERENCE.md | Key Function Locations |
| Debug script issues | QUICK_REFERENCE.md | Debugging Tips |
| Troubleshoot connection issues | QUICK_REFERENCE.md | Troubleshooting Guide |
| Understand data extraction | FLOW_DIAGRAM.md | Data Extraction Flow |
| Test parsers | PARSER_REFERENCE.md | Testing Parsers |

---

## 📂 File Structure

```
/workspace/
├── README.md                    # This file - Documentation overview
├── SCRIPT_DOCUMENTATION.md      # Complete guide with all details
├── QUICK_REFERENCE.md           # Cheat sheet for quick lookups
├── FLOW_DIAGRAM.md              # Visual flow diagrams
├── PARSER_REFERENCE.md          # Parser function reference
├── network_inputs.xlsx          # Input/Output Excel file (created by script)
├── failed_connections.log       # Connection failure log (created by script)
├── code11                       # (Unknown - in workspace)
└── code12                       # (Unknown - in workspace)
```

---

## 🎓 Learning Path

### Beginner (Never seen the script before)
```
Day 1: Read SCRIPT_DOCUMENTATION.md (Sections 1-3)
       Understand purpose, I/O files, device types
       
Day 2: Read QUICK_REFERENCE.md
       Review device types, commands, troubleshooting
       
Day 3: Read FLOW_DIAGRAM.md
       Visualize script execution flow
       
Day 4: Run script with 1 test device
       Review Results, Neighbors, Interfaces sheets
       
Day 5: Read PARSER_REFERENCE.md (Sections 1-2)
       Understand how data is extracted
```

### Intermediate (Familiar with script, want to modify)
```
1. Identify modification needed
2. Check QUICK_REFERENCE.md for quick pattern
3. Read detailed example in SCRIPT_DOCUMENTATION.md
4. Review PARSER_REFERENCE.md if parser changes needed
5. Make changes and test
```

### Advanced (Deep customization)
```
1. Read all documentation thoroughly
2. Understand complete flow from FLOW_DIAGRAM.md
3. Study all parsers in PARSER_REFERENCE.md
4. Review SCRIPT_DOCUMENTATION.md modification patterns
5. Make architectural changes as needed
```

---

## 💡 Pro Tips

1. **Always Check Results Sheet First**
   - When parsers fail, raw output shows exact format
   - Use Results sheet to test regex patterns

2. **Test with Single Device**
   - Faster iteration during development
   - Easier to spot issues

3. **Use Device_Type Override**
   - For ambiguous hostnames
   - For cisco_xr devices (must be explicit)

4. **Credential Caching Saves Time**
   - Script remembers manual credentials
   - Only one 2FA prompt for all devices

5. **Duplicate Descriptions Are Normal**
   - Script automatically adds _1, _2, _3 suffixes
   - Prevents data loss from duplicate interface tags

6. **Sort Order Matters**
   - Nokia processed first to discover RR-2-PEER IPs
   - Those IPs used for Cisco BD0 EVPN queries

7. **Check Line Numbers in QUICK_REFERENCE.md**
   - Fast way to locate functions for modification
   - Line numbers based on provided script

---

## 🆘 Getting Help

### Debugging Steps

1. **Connection Issues**
   → Check QUICK_REFERENCE.md → Troubleshooting Guide
   → Review failed_connections.log

2. **Parser Issues**
   → Check Results sheet for raw output
   → Review PARSER_REFERENCE.md for expected format
   → Test regex at regex101.com

3. **Missing Data**
   → Verify command ran (check Results sheet)
   → Check parser function in PARSER_REFERENCE.md
   → Add debug print statements

4. **Wrong Device Type Detected**
   → Check QUICK_REFERENCE.md → Device Types Cheat Sheet
   → Use Device_Type column override in Excel

5. **Unexpected Behavior**
   → Review FLOW_DIAGRAM.md for execution path
   → Check device role detection logic
   → Verify Primary/Secondary/Tab settings in Excel

---

## 🔗 External Resources

- **Netmiko Documentation**: https://github.com/ktbyers/netmiko
- **Paramiko Documentation**: http://www.paramiko.org/
- **Regex Tester**: https://regex101.com/ (use Python flavor)
- **openpyxl Documentation**: https://openpyxl.readthedocs.io/

---

## 📊 Quick Stats

- **Total Functions**: 20+ parsing and helper functions
- **Device Types Supported**: Nokia SROS, Cisco NX-OS, Cisco IOS-XR
- **BGP Contexts Monitored**: 25+ contexts
- **Interface Types Collected**: BD, BM, B4, B2, B16, B17, B18, LAG, Bundle-Ether
- **Output Sheets**: 3 (Results, Neighbors, Interfaces)
- **Authentication Methods**: Default TACACS + Manual with 2FA
- **Credential Caching**: Global (shared across all devices)

---

## ✅ Document Status

All documentation is complete and ready for use:

- ✅ SCRIPT_DOCUMENTATION.md - Comprehensive guide (100+ sections)
- ✅ QUICK_REFERENCE.md - Quick lookup reference
- ✅ FLOW_DIAGRAM.md - Visual flow diagrams
- ✅ PARSER_REFERENCE.md - Parser function reference
- ✅ README.md - Documentation overview (this file)

---

## 🎯 Next Steps

1. **Choose your starting document** based on your needs:
   - New user? → Start with SCRIPT_DOCUMENTATION.md
   - Need quick info? → Check QUICK_REFERENCE.md
   - Visual learner? → Review FLOW_DIAGRAM.md
   - Modifying parsers? → Read PARSER_REFERENCE.md

2. **Test the script** with a single device to see it in action

3. **Refer back to documentation** as needed during development

4. **Use the Quick Lookup table** above to find specific information

---

## 📞 Support

For issues or questions:
1. Check relevant documentation file
2. Review Results sheet for raw command outputs
3. Check failed_connections.log for connection errors
4. Test regex patterns at regex101.com
5. Add debug print statements to trace execution

---

**Happy automating! 🚀**

**Last Updated**: 2025-11-19  
**Documentation Version**: 1.0  
**Script Version**: Based on provided code
