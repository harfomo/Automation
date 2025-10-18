# Solution Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     NETWORK AUDIT SYSTEM                            │
│                   (Enhanced with BD0 Queries)                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ INPUT: network_inputs.xlsx                                          │
├─────────────────────────────────────────────────────────────────────┤
│ Devices Sheet:                                                      │
│  - NWCSDEBGB06  | 2001:4888:a1f:6332::6  | nokia_sros_ssh         │
│  - NWCSDEBGB07  | 2001:4888:a1f:6332::7  | nokia_sros_ssh         │
│  - NWCSDEBGBD0  | 10.1.1.1               | cisco_nxos             │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 1: NOKIA DEVICE QUERIES (B06, B07)                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐         ┌──────────────┐                        │
│  │   B06 Device │         │   B07 Device │                        │
│  │  (Nokia SROS)│         │  (Nokia SROS)│                        │
│  └──────┬───────┘         └──────┬───────┘                        │
│         │                        │                                 │
│         │ /admin display-config  │ /admin display-config           │
│         │ show port detail       │ show port detail                │
│         │ show lag description   │ show lag description            │
│         │ show router bgp...     │ show router bgp...              │
│         │                        │                                 │
│         ▼                        ▼                                 │
│  ┌─────────────────────────────────────────┐                      │
│  │   EXTRACT RR-2-PEER IPs:                │                      │
│  │   • B06: 10.1.1.10                      │                      │
│  │   • B07: 10.1.1.20                      │                      │
│  └─────────────────────────────────────────┘                      │
│         │                                                           │
│         └──────────────┬────────────────────────────────┐          │
│                        │                                │          │
└────────────────────────┼────────────────────────────────┼──────────┘
                         │                                │
                         ▼                                │
┌─────────────────────────────────────────────────────────┼──────────┐
│ PHASE 2: CISCO BD0 EVPN QUERIES                         │          │
├─────────────────────────────────────────────────────────┼──────────┤
│                                                          │          │
│  ┌────────────────────────────────────────────────────┐ │          │
│  │  BD0 Device (Cisco NXOS)                           │ │          │
│  └────────────────┬───────────────────────────────────┘ │          │
│                   │                                      │          │
│                   │ Commands using captured IPs:        │          │
│                   │                                      │          │
│  ┌────────────────▼─────────────────────────────────────▼────────┐ │
│  │                                                                │ │
│  │  show bgp l2vpn evpn rd 10.1.1.20:1 | i prefixes  [B07 RAN]  │ │
│  │  show bgp l2vpn evpn rd 10.1.1.10:1 | i prefixes  [B06 RAN]  │ │
│  │  show bgp l2vpn evpn rd 10.1.1.20:2 | i prefixes  [B07 EDN]  │ │
│  │  show bgp l2vpn evpn rd 10.1.1.10:2 | i prefixes  [B06 EDN]  │ │
│  │  show bgp l2vpn evpn rd 10.1.1.20:3 | i prefixes  [B07 WSN]  │ │
│  │  show bgp l2vpn evpn rd 10.1.1.10:3 | i prefixes  [B06 WSN]  │ │
│  │                                                                │ │
│  └────────────────┬───────────────────────────────────────────────┘ │
│                   │                                                  │
│                   ▼ Parse Output:                                   │
│  ┌────────────────────────────────────────────────────────┐         │
│  │  "Processed 1541 prefixes, 3082 paths"                │         │
│  │   ├─ Extract prefix count: 1541                       │         │
│  │   └─ Extract path count: 3082  ◄───── SAVE THIS       │         │
│  └────────────────────────────────────────────────────────┘         │
│                                                                      │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ OUTPUT: network_inputs.xlsx (Updated)                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Results Sheet (Raw Command Outputs)                         │   │
│ │ - All commands and their complete outputs                   │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Neighbors Sheet (BGP Data)                                  │   │
│ │ ┌──────┬────────────────┬──────────┬─────┬──────┬────────┐ │   │
│ │ │Device│ Description    │ Neighbor │ Adv │ Recv │ EVPN   │ │   │
│ │ │ IP   │                │ IP       │     │      │ (Adv)  │ │   │
│ │ ├──────┼────────────────┼──────────┼─────┼──────┼────────┤ │   │
│ │ │B06_IP│ RR-2-PEER      │10.1.1.10 │ 100 │  50  │        │ │   │
│ │ │B07_IP│ RR-2-PEER      │10.1.1.20 │ 120 │  60  │        │ │   │
│ │ │BD0_IP│RAN routes B07  │10.1.1.20:│     │      │ 3082   │ │   │
│ │ │BD0_IP│RAN routes B06  │10.1.1.10:│     │      │ 2954   │ │   │
│ │ │BD0_IP│EDN routes B07  │10.1.1.20:│     │      │ 4123   │ │   │
│ │ │BD0_IP│EDN routes B06  │10.1.1.10:│     │      │ 3876   │ │   │
│ │ │BD0_IP│WSN routes B07  │10.1.1.20:│     │      │ 5234   │ │   │
│ │ │BD0_IP│WSN routes B06  │10.1.1.10:│     │      │ 4987   │ │   │
│ │ └──────┴────────────────┴──────────┴─────┴──────┴────────┘ │   │
│ │          ▲                                        ▲         │   │
│ │          │                                        │         │   │
│ │   From original script              From BD0 queries       │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Interfaces Sheet (Port & LAG Data)                          │   │
│ │ - Interface descriptions and names                          │   │
│ │ - LAG thresholds                                            │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌─────────┐
│ User    │
│ Runs    │
│ Script  │
└────┬────┘
     │
     ▼
┌──────────────────┐
│ Excel File       │
│ Loaded           │
└────┬─────────────┘
     │
     ▼
┌──────────────────────────────────────┐
│ Device Loop Starts                    │
├──────────────────────────────────────┤
│                                      │
│  FOR EACH DEVICE:                    │
│                                      │
│  ┌─────────────────────────────┐   │
│  │ If B06 or B07 (Nokia):      │   │
│  │  • Run Nokia commands       │   │
│  │  • Extract RR-2-PEER IP     │   │
│  │  • Store for later          │   │
│  └─────────────────────────────┘   │
│                                      │
│  ┌─────────────────────────────┐   │
│  │ If BD0 (Cisco):             │   │
│  │  • Mark for EVPN queries    │   │
│  │  • (Queries run at end)     │   │
│  └─────────────────────────────┘   │
│                                      │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ All Devices Processed                 │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ IF (BD0 exists AND                    │
│     B06 RR-2-PEER exists AND         │
│     B07 RR-2-PEER exists):           │
│                                      │
│   ┌─────────────────────────────┐   │
│   │ Connect to BD0              │   │
│   │ Run 6 EVPN commands         │   │
│   │ Parse path counts           │   │
│   │ Add to Neighbors sheet      │   │
│   └─────────────────────────────┘   │
│                                      │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ Sort Neighbors Sheet                  │
│ (by BGP_CONTEXTS order)              │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ Save Excel File                       │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ Done! ✅                              │
└──────────────────────────────────────┘
```

---

## Component Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    SCRIPT COMPONENTS                           │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ 1. INITIALIZATION                                     │    │
│  │    • Load Excel file                                  │    │
│  │    • Build device list                                │    │
│  │    • Test TACACS credentials                          │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ 2. HELPER FUNCTIONS                                   │    │
│  │    • get_full_output() - Handle pagination            │    │
│  │    • extract_neighbors() - Parse BGP config           │    │
│  │    • extract_lag_interfaces() - Parse LAG data        │    │
│  │    • extract_threshold() - Parse LAG thresholds       │    │
│  │    • get_router_for_context() - Router ID mapping     │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ 3. NOKIA DEVICE PROCESSING                            │    │
│  │    • Execute commands                                 │    │
│  │    • Parse outputs                                    │    │
│  │    • Query BGP routes                                 │    │
│  │    • Extract interfaces                               │    │
│  │    • Capture RR-2-PEER IPs ◄─────────────┐           │    │
│  └──────────────────────────────────────────┼───────────┘    │
│                                              │                │
│  ┌──────────────────────────────────────────┼───────────┐    │
│  │ 4. BD0 EVPN QUERIES (NEW!)                │           │    │
│  │    • Use captured RR-2-PEER IPs ──────────┘           │    │
│  │    • Build 6 EVPN commands                            │    │
│  │    • Execute on BD0                                   │    │
│  │    • Parse path counts                                │    │
│  │    • Add to Neighbors sheet                           │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ 5. FINALIZATION                                       │    │
│  │    • Sort Neighbors sheet                             │    │
│  │    • Save Excel file                                  │    │
│  │    • Display summary                                  │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Error Handling Flow

```
┌──────────────────┐
│ Operation        │
└────┬─────────────┘
     │
     ▼
┌──────────────────┐      ┌──────────────────┐
│ Try Operation    │─────▶│ Success          │
└────┬─────────────┘      └────┬─────────────┘
     │                         │
     │ Exception               │
     ▼                         ▼
┌──────────────────┐      ┌──────────────────┐
│ Catch Error      │      │ Continue         │
└────┬─────────────┘      └──────────────────┘
     │
     ├─────────────────────────────────┐
     │                                 │
     ▼                                 ▼
┌──────────────────┐      ┌──────────────────┐
│ Log to File      │      │ Mark in Excel    │
│ (failed_         │      │ (ERROR /         │
│  connections.log)│      │  PARSE_ERROR)    │
└──────────────────┘      └──────────────────┘
     │                                 │
     └────────────┬────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────┐
│ Continue with Next Operation         │
└──────────────────────────────────────┘
```

---

## File Dependencies

```
network_audit_enhanced.py
├── Requires:
│   ├── netmiko (SSH connectivity)
│   ├── openpyxl (Excel manipulation)
│   ├── getpass (Password input)
│   ├── re (Regex parsing)
│   └── datetime (Logging timestamps)
│
├── Reads:
│   └── network_inputs.xlsx (Devices sheet)
│
├── Writes:
│   ├── network_inputs.xlsx (Results, Neighbors, Interfaces sheets)
│   └── failed_connections.log (Connection failures)
│
└── Connects To:
    ├── Nokia SROS devices (B06, B07, etc.)
    └── Cisco NXOS devices (BD0, etc.)
```

---

## Execution Timeline

```
Time  │ Activity
──────┼──────────────────────────────────────────────────
 0s   │ Script starts
      │ Load Excel file
      │ Build device list
──────┼──────────────────────────────────────────────────
 5s   │ Test TACACS credentials
      │ Connect to first device
──────┼──────────────────────────────────────────────────
 10s  │ Query B06 (Nokia)
      │ Execute ~10 commands
      │ Capture RR-2-PEER IP: 10.1.1.10
──────┼──────────────────────────────────────────────────
 60s  │ Query B07 (Nokia)
      │ Execute ~10 commands
      │ Capture RR-2-PEER IP: 10.1.1.20
──────┼──────────────────────────────────────────────────
110s  │ Query other devices (if any)
──────┼──────────────────────────────────────────────────
120s  │ BD0 EVPN Queries Phase
      │ Connect to BD0
      │ Execute 6 EVPN commands
      │ Parse path counts
      │ Add to Excel
──────┼──────────────────────────────────────────────────
135s  │ Finalization
      │ Sort Neighbors sheet
      │ Save Excel file
──────┼──────────────────────────────────────────────────
140s  │ Complete! ✅
──────┴──────────────────────────────────────────────────

Note: Times are approximate and depend on network latency
```

---

## Integration Points

```
┌────────────────────────────────────────────────────────┐
│ ORIGINAL SCRIPT FUNCTIONALITY                          │
│ (Preserved unchanged)                                  │
│ ────────────────────────────────────────────────────   │
│ • Nokia device queries                                 │
│ • Interface parsing                                    │
│ • BGP neighbor extraction                              │
│ • LAG threshold collection                             │
│ • CPE-check neighbors                                  │
└──────────────────────┬─────────────────────────────────┘
                       │
                       │ Integration Point:
                       │ Capture RR-2-PEER IPs
                       │
                       ▼
┌────────────────────────────────────────────────────────┐
│ NEW BD0 FUNCTIONALITY                                  │
│ (Added seamlessly)                                     │
│ ────────────────────────────────────────────────────   │
│ • Use captured RR-2-PEER IPs                           │
│ • Query BD0 for EVPN routes                            │
│ • Parse path counts                                    │
│ • Add to same Neighbors sheet                          │
└────────────────────────────────────────────────────────┘
```

---

**Architecture Summary**:
- ✅ Non-invasive integration with original script
- ✅ Modular design with clear separation of concerns
- ✅ Robust error handling at all levels
- ✅ Efficient execution (parallel where possible)
- ✅ Comprehensive logging and reporting
