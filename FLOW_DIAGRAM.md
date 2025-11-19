# Network Automation Script - Flow Diagram

## 🔄 High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      SCRIPT START                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │  Check if network_inputs.xlsx │
         │         exists                │
         └───────────┬───────────────────┘
                     │
          ┌──────────┴──────────┐
          │ No                  │ Yes
          ▼                     ▼
  ┌───────────────┐    ┌────────────────────┐
  │ Create Excel  │    │ Load Excel file    │
  │  template     │    │ Parse Devices sheet│
  └───────┬───────┘    └─────────┬──────────┘
          │                      │
          └──────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │ Extract Primary/Sister CILLI  │
         │ Location codes from devices   │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │ Sort devices: Nokia first,    │
         │ then Cisco (by device_type)   │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │ Create output sheets:         │
         │ - Results                     │
         │ - Neighbors                   │
         │ - Interfaces                  │
         └───────────┬───────────────────┘
                     │
         ┌───────────┴──────────────────┐
         │                              │
         ▼                              ▼
┌──────────────────┐         ┌──────────────────┐
│   PHASE 1:       │         │   PHASE 2:       │
│   NOKIA DEVICES  │         │   CISCO DEVICES  │
│   (B06, B07)     │────────▶│   (BD0, B01,     │
│                  │         │    B02, etc.)    │
└──────────────────┘         └──────────────────┘
         │                              │
         │                              │
         ▼                              ▼
┌──────────────────┐         ┌──────────────────┐
│ Sort Neighbors   │         │ Sort Interfaces  │
│ by hostname &    │         │ by hostname      │
│ BGP context      │         │                  │
└──────────────────┘         └──────────────────┘
         │                              │
         └──────────┬───────────────────┘
                    │
                    ▼
         ┌───────────────────────────────┐
         │ Save Excel file with all data │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │        SCRIPT END              │
         │   (Success or Error logged)   │
         └───────────────────────────────┘
```

---

## 🔵 PHASE 1: Nokia Device Processing Flow

```
┌─────────────────────────────────────────────────────────────┐
│          FOR EACH NOKIA DEVICE IN SORTED LIST               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │   Attempt Connection          │
         │   1. Try default creds        │
         │   2. Try cached manual creds  │
         │   3. Prompt for manual creds  │
         └───────────┬───────────────────┘
                     │
          ┌──────────┴──────────┐
          │ Failed              │ Success
          ▼                     ▼
  ┌───────────────┐    ┌────────────────────┐
  │ Log failure   │    │ Detect device role │
  │ Skip device   │    │ and tab number     │
  └───────────────┘    └─────────┬──────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
          ┌─────────────┐  ┌──────────┐  ┌──────────┐
          │  Primary    │  │Secondary │  │Tab Device│
          │  B07/B06    │  │ B07/B06  │  │ (1/2/3)  │
          └─────┬───────┘  └────┬─────┘  └────┬─────┘
                │               │             │
                │               │             │
                ▼               ▼             ▼
    ┌──────────────────┐  ┌─────────┐  ┌─────────────┐
    │  FULL COMMAND    │  │ LIMITED │  │TAB-SPECIFIC │
    │     SET          │  │COMMAND  │  │  COMMANDS   │
    │                  │  │  SET    │  │             │
    │ • display-config │  │ • LAG20 │  │Tab1: LAG    │
    │ • cpe-check      │  │ • LAG   │  │Tab2/3: BE   │
    │ • port detail    │  │  desc   │  │             │
    │ • lag desc       │  │         │  │             │
    │ • LAG 20 (B07/B06)│ │         │  │             │
    └────────┬─────────┘  └────┬────┘  └──────┬──────┘
             │                 │              │
             │                 │              │
             ▼                 ▼              ▼
    ┌─────────────────────────────────────────────┐
    │         Parse Command Outputs:              │
    │  • BGP neighbors → Neighbors sheet          │
    │  • CPE neighbors → Neighbors sheet          │
    │  • Interfaces → Interfaces sheet            │
    │  • LAG thresholds → Interfaces sheet        │
    │  • Bundle-Ether → Interfaces sheet          │
    └─────────────────┬───────────────────────────┘
                      │
                      ▼
    ┌─────────────────────────────────────────────┐
    │    FOR EACH BGP NEIGHBOR (Primary only):    │
    │  • Query advertised routes                  │
    │  • Query received routes                    │
    │  • Query EVPN prefixes (if iBGP)            │
    │  • Add to Neighbors sheet                   │
    └─────────────────┬───────────────────────────┘
                      │
                      ▼
             ┌────────────────┐
             │  Disconnect    │
             └────────────────┘
```

---

## 🔴 PHASE 2: Cisco Device Processing Flow

```
┌─────────────────────────────────────────────────────────────┐
│          FOR EACH CISCO DEVICE IN SORTED LIST               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │   Check if Proxy_IP exists    │
         └───────────┬───────────────────┘
                     │
          ┌──────────┴──────────┐
          │ No Proxy            │ Proxy Needed
          ▼                     ▼
  ┌───────────────┐    ┌────────────────────┐
  │ Direct        │    │ Connect to Jump    │
  │ Connection    │    │ Server (Paramiko)  │
  └───────┬───────┘    │ Create SSH tunnel  │
          │            └─────────┬──────────┘
          │                      │
          └──────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │   Attempt Device Connection   │
         │   1. Try default creds        │
         │   2. Try cached manual creds  │
         │   3. Prompt for manual creds  │
         └───────────┬───────────────────┘
                     │
          ┌──────────┴──────────┐
          │ Failed              │ Success
          ▼                     ▼
  ┌───────────────┐    ┌────────────────────┐
  │ Log failure   │    │ Detect device type │
  │ Close proxy   │    │ BD0/B01/B02/Tab    │
  │ Skip device   │    └─────────┬──────────┘
  └───────────────┘              │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
          ┌─────────────┐  ┌──────────┐  ┌──────────┐
          │    BD0      │  │ B01/B02  │  │Tab Device│
          │   (EVPN)    │  │ B2C/B2D  │  │          │
          └─────┬───────┘  └────┬─────┘  └────┬─────┘
                │               │             │
                │               │             │
                ▼               ▼             ▼
    ┌──────────────────┐  ┌─────────┐  ┌─────────────┐
    │  EVPN PATH       │  │ BGP AS  │  │BUNDLE-ETHER │
    │  COMMANDS        │  │ NUMBER  │  │  COMMANDS   │
    │                  │  │         │  │             │
    │ • show bgp       │  │• sh run │  │• sh int desc│
    │   l2vpn evpn     │  │  bgp    │  │• show bundle│
    │   rd X:1/2/3     │  │         │  │             │
    │ • Query B06/B07  │  │         │  │             │
    │   RR-2-PEER      │  │         │  │             │
    └────────┬─────────┘  └────┬────┘  └──────┬──────┘
             │                 │              │
             │                 │              │
             ▼                 ▼              ▼
    ┌─────────────────────────────────────────────┐
    │         Parse Command Outputs:              │
    │  • EVPN paths → Neighbors sheet             │
    │  • BGP AS → Neighbors sheet                 │
    │  • Bundle-Ether → Interfaces sheet          │
    └─────────────────┬───────────────────────────┘
                      │
                      ▼
             ┌────────────────┐
             │  Disconnect    │
             │  Close proxy   │
             └────────────────┘
```

---

## 🔐 Authentication Flow Detail

```
┌─────────────────────────────────────────────────────────────┐
│              DEVICE CONNECTION ATTEMPT                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │ Check: manual_creds cached?   │
         └───────────┬───────────────────┘
                     │
          ┌──────────┴──────────┐
          │ Yes                 │ No
          ▼                     ▼
  ┌───────────────┐    ┌────────────────────┐
  │ Try cached    │    │ Try default creds  │
  │ manual creds  │    │ (TACACS embedded)  │
  └───────┬───────┘    └─────────┬──────────┘
          │                      │
          ├──Success─────────────┤
          │                      │
          ├──Failed──────────────┤
          │                      │
          ▼                      ▼
  ┌───────────────┐    ┌────────────────────┐
  │ Try default   │    │ Try cached manual  │
  │ as fallback   │    │ (if exists)        │
  └───────┬───────┘    └─────────┬──────────┘
          │                      │
          ├──Success─────────────┤
          │                      │
          └──Failed──────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │ Prompt for manual credentials │
         │ (with 2FA support)            │
         └───────────┬───────────────────┘
                     │
          ┌──────────┴──────────┐
          │ Success             │ Failed
          ▼                     ▼
  ┌───────────────┐    ┌────────────────────┐
  │ Cache creds   │    │ Log failure        │
  │ globally for  │    │ Skip device        │
  │ ALL devices   │    │                    │
  └───────┬───────┘    └────────────────────┘
          │
          ▼
  ┌───────────────┐
  │   Connected   │
  │   Continue    │
  └───────────────┘
```

---

## 🔍 Data Extraction Flow

### Nokia BGP Neighbor Route Collection

```
┌─────────────────────────────────────────────────────────────┐
│         FOR EACH BGP NEIGHBOR FOUND IN display-config       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │ Determine neighbor type:      │
         │ • iBGP-TO-* (EVPN)            │
         │ • RAN_EBGP_* (MSE/VXLAN/MLS)  │
         │ • EDN_EBGP_*                  │
         │ • WSN_EBGP_*                  │
         │ • RR-*-PEER                   │
         └───────────┬───────────────────┘
                     │
          ┌──────────┴──────────┐
          │ iBGP EVPN           │ Standard BGP
          ▼                     ▼
  ┌───────────────┐    ┌────────────────────┐
  │ Query EVPN    │    │ Map context to     │
  │ routes:       │    │ router ID:         │
  │               │    │ RAN_*    → 1       │
  │• label-ipv4   │    │ EDN_*    → 2       │
  │  advertised   │    │ WSN_*    → 3       │
  │• label-ipv4   │    │ CELL_*   → 4       │
  │  received     │    │ XRTT_*   → 673     │
  │• evpn         │    └─────────┬──────────┘
  │  advertised   │              │
  │• evpn         │              ▼
  │  received     │    ┌────────────────────┐
  │               │    │ Query routes:      │
  │Parse counts:  │    │                    │
  │• label routes │    │• advertised        │
  │• IPv4 prefix  │    │  (ipv4/ipv6)       │
  │• IPv6 prefix  │    │• received          │
  └───────┬───────┘    │  (ipv4/ipv6)       │
          │            │                    │
          │            │Parse "Routes: N"   │
          │            └─────────┬──────────┘
          │                      │
          └──────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │ Add row to Neighbors sheet:   │
         │ [Hostname, IP, Desc,          │
         │  Neighbor_IP, Adv, Recv,      │
         │  EVPN_Adv, EVPN_Recv]         │
         └───────────────────────────────┘
```

### Nokia Interface/LAG Extraction

```
┌─────────────────────────────────────────────────────────────┐
│           FOR EACH INTERFACE TYPE (BD, BM, B4, B2)          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │ Parse "show port detail"      │
         │ output line by line           │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │ Find "Interface: X"           │
         │ Store as pending_interface    │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │ Find "Description: Y"         │
         │ Extract tag (BD0, BM1, etc.)  │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │ Pair description with         │
         │ interface → (tag, interface)  │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │ Add to Interfaces sheet       │
         │ with deduplication (_1, _2)   │
         └───────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│                  FOR EACH LAG INTERFACE                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │ Parse "show lag description"  │
         │ Find "lag N" pattern          │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │ Extract description from      │
         │ next few lines                │
         │ (pattern: SITE_Bundle-Ether)  │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │ Run "show lag N" to get       │
         │ threshold value               │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │ Parse status row:             │
         │ "1  up  up  ...  [threshold]" │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │ Add to Interfaces sheet       │
         │ [Hostname, IP, Desc,          │
         │  LAG_name, Threshold]         │
         └───────────────────────────────┘
```

---

## 🎯 Device Role Decision Tree

```
                     ┌───────────────┐
                     │  Read Device  │
                     │   from Excel  │
                     └───────┬───────┘
                             │
                             ▼
                ┌────────────────────────┐
                │ Check primary_tab or   │
                │ secondary_tab columns  │
                └────────┬───────────────┘
                         │
              ┌──────────┴──────────┐
              │ Has Tab             │ No Tab
              ▼                     ▼
     ┌────────────────┐    ┌────────────────┐
     │ Check tab      │    │ Check primary_ │
     │ number         │    │ secondary      │
     └────┬───────────┘    └────┬───────────┘
          │                     │
    ┌─────┼─────┐         ┌─────┴─────┐
    │     │     │         │           │
    ▼     ▼     ▼         ▼           ▼
┌─────┐┌─────┐┌─────┐┌─────────┐┌─────────┐
│Tab 1││Tab 2││Tab 3││ Primary ││Secondary│
└──┬──┘└──┬──┘└──┬──┘└────┬────┘└────┬────┘
   │      │      │        │          │
   │      │      │        │          │
   ▼      ▼      ▼        ▼          ▼
┌─────────────────────────────────────────┐
│         Check Device Type                │
│      (Nokia vs Cisco, B06/B07 etc.)     │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌────────┐  ┌────────┐  ┌────────┐
│ Nokia  │  │ Cisco  │  │ Cisco  │
│ B06/B07│  │  BD0   │  │B01/B02 │
└────┬───┘  └───┬────┘  └───┬────┘
     │          │           │
     ▼          ▼           ▼
┌─────────────────────────────┐
│  Execute Role-Specific      │
│  Command Set                │
└─────────────────────────────┘
```

### Decision Matrix

| Role | Tab | Device Type | Hostname Pattern | Commands Executed |
|------|-----|-------------|------------------|-------------------|
| Primary | - | Nokia | B07 | Full set + LAG20 |
| Primary | - | Nokia | B06 | Full set + LAG20 |
| Secondary | - | Nokia | B07 | LAG20 + LAG desc |
| Secondary | - | Nokia | B06 | LAG20 + LAG desc |
| Primary | 1 | Nokia | * | LAG desc only |
| Secondary | 1 | Nokia | * | LAG desc only |
| Secondary | 2 | Nokia | * | Bundle-Ether search |
| Secondary | 3 | Nokia | * | Bundle-Ether search |
| - | - | Cisco | BD0 | EVPN paths |
| - | - | Cisco | B01/B02 | BGP AS number |
| Primary/Secondary | Any | Cisco | * | Bundle-Ether search |

---

## 📦 Data Flow Summary

```
Excel Input (Devices)
         │
         ▼
┌─────────────────┐
│ Device Parser   │
│ • IP/Hostname   │
│ • Device Type   │
│ • Role/Tab      │
│ • Proxy         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Sort Devices   │
│  Nokia → Cisco  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐┌────────┐
│ Nokia  ││ Cisco  │
│Process ││Process │
└───┬────┘└───┬────┘
    │         │
    └────┬────┘
         │
         ▼
┌─────────────────┐
│ Raw Outputs →   │
│ Results Sheet   │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Parsed Data:    │
│                 │
│ BGP Neighbors → │
│ Neighbors Sheet │
│                 │
│ Interfaces →    │
│ Interfaces Sheet│
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Sort & Organize │
│ by Device Order │
└────────┬────────┘
         │
         ▼
    Excel Output
    (Same file)
```

---

## 🔄 Credential Cache Flow

```
┌─────────────────────────────────────┐
│      First Device Connection        │
└────────────────┬────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │ Try default    │
        │ credentials    │
        └────────┬───────┘
                 │
          ┌──────┴──────┐
          │Success      │Fail
          ▼             ▼
     ┌─────────┐   ┌────────────────┐
     │Continue │   │Prompt for      │
     │using    │   │manual creds    │
     │defaults │   │(with 2FA)      │
     └─────────┘   └────────┬───────┘
                            │
                            ▼
                   ┌────────────────┐
                   │Cache creds in  │
                   │manual_creds    │
                   │global variable │
                   └────────┬───────┘
                            │
                            ▼
┌─────────────────────────────────────────────┐
│      Subsequent Device Connections          │
└────────────────┬────────────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │ Check if       │
        │ manual_creds   │
        │ cached?        │
        └────────┬───────┘
                 │
          ┌──────┴──────┐
          │Yes          │No
          ▼             ▼
     ┌─────────┐   ┌─────────┐
     │Try cache│   │Try      │
     │first    │   │defaults │
     └────┬────┘   └────┬────┘
          │             │
          │Success      │Success
          ├─────────────┤
          │             │
          │Fail         │Fail
          └──────┬──────┘
                 │
                 ▼
        ┌────────────────┐
        │Try alternative │
        │(cache/default) │
        └────────┬───────┘
                 │
          ┌──────┴──────┐
          │Success      │Fail
          ▼             ▼
     ┌─────────┐   ┌─────────┐
     │Continue │   │Re-prompt│
     └─────────┘   └─────────┘

Result: Only ONE manual credential prompt for ALL devices!
```

---

## 🎨 Color Legend

- 🔵 = Nokia Processing
- 🔴 = Cisco Processing
- 🟢 = Success Path
- 🔶 = Decision Point
- 🟡 = Data Output
- ⚠️  = Error/Failure Path

---

**Visual flow diagrams created for easy understanding of script execution paths.**
