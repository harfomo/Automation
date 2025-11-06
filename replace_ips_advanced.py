from openpyxl import load_workbook
import os
import re
import argparse

# =========================================================
# Configuration
# =========================================================
script_dir = os.path.dirname(os.path.abspath(__file__))
network_inputs_file = os.path.join(script_dir, "network_inputs.xlsx")
mop_temp_file = os.path.join(script_dir, "MOPtemp.xlsx")

# =========================================================
# Command-line arguments
# =========================================================
parser = argparse.ArgumentParser(description='Replace Neighbor IPs with Descriptions in MOPtemp.xlsx')
parser.add_argument('--overwrite', action='store_true', 
                    help='Overwrite the original MOPtemp.xlsx instead of creating a new file')
parser.add_argument('--sheets', nargs='+', 
                    help='Specific sheet names to process (default: all sheets)')
parser.add_argument('--case-sensitive', action='store_true',
                    help='Use case-sensitive matching for IPs')
parser.add_argument('--preview', action='store_true',
                    help='Preview changes without saving (dry run)')
args = parser.parse_args()

# =========================================================
# Validation
# =========================================================
if not os.path.exists(network_inputs_file):
    print(f"❌ Error: '{network_inputs_file}' not found!")
    print("   Please run the network_device_collector.py script first.")
    raise SystemExit

if not os.path.exists(mop_temp_file):
    print(f"❌ Error: '{mop_temp_file}' not found!")
    print("   Please ensure MOPtemp.xlsx exists in the script directory.")
    raise SystemExit

# =========================================================
# Load network_inputs.xlsx and build IP -> Description mapping
# =========================================================
print("📖 Loading network_inputs.xlsx...")
network_wb = load_workbook(network_inputs_file, data_only=True)

if "Neighbors" not in network_wb.sheetnames:
    print("❌ Error: 'Neighbors' sheet not found in network_inputs.xlsx")
    raise SystemExit

neighbors_sheet = network_wb["Neighbors"]

# Build mapping: Neighbor IP -> Neighbor Description
ip_to_description = {}
replacement_count = 0
changes_log = []

print("🔍 Building IP to Description mapping from Neighbors sheet...")
for row in neighbors_sheet.iter_rows(min_row=2, values_only=True):
    if not row or len(row) < 3:
        continue
    
    # Column structure: [Device IP, Neighbor Description, Neighbor IP, ...]
    neighbor_desc = row[1]  # Column B: Neighbor Description
    neighbor_ip = row[2]    # Column C: Neighbor IP
    
    if neighbor_ip and neighbor_desc:
        neighbor_ip_str = str(neighbor_ip).strip()
        neighbor_desc_str = str(neighbor_desc).strip()
        
        if neighbor_ip_str and neighbor_desc_str:
            ip_to_description[neighbor_ip_str] = neighbor_desc_str

print(f"✅ Found {len(ip_to_description)} unique Neighbor IP -> Description mappings")

if not ip_to_description:
    print("⚠️  No valid mappings found. Exiting.")
    raise SystemExit

# Show first 10 mappings as preview
print("\n📋 Sample mappings (first 10):")
for i, (ip, desc) in enumerate(list(ip_to_description.items())[:10]):
    print(f"   {ip} → {desc}")
if len(ip_to_description) > 10:
    print(f"   ... and {len(ip_to_description) - 10} more")

# =========================================================
# Helper function for smart IP matching
# =========================================================
def replace_ip_in_text(text, ip, description, case_sensitive=False):
    """
    Replace IP with description in text, handling both IPv4 and IPv6.
    Returns (new_text, was_replaced)
    """
    if not case_sensitive:
        # For case-insensitive, we need to find and replace while preserving original case
        pattern = re.compile(re.escape(ip), re.IGNORECASE)
    else:
        pattern = re.compile(re.escape(ip))
    
    # Check if pattern exists
    if not pattern.search(text):
        return text, False
    
    # For IPv6 (contains colons) and IPv4, use different strategies
    if ':' in ip:
        # IPv6 - use exact match with optional surrounding whitespace or punctuation
        new_text = pattern.sub(description, text)
    else:
        # IPv4 - try to use word boundaries, but fallback to simple replace if needed
        try:
            # Attempt word boundary match
            pattern_wb = re.compile(r'\b' + re.escape(ip) + r'\b', 
                                   re.IGNORECASE if not case_sensitive else 0)
            if pattern_wb.search(text):
                new_text = pattern_wb.sub(description, text)
            else:
                # Fallback to simple replacement
                new_text = pattern.sub(description, text)
        except:
            # If regex fails, use simple string replacement
            new_text = pattern.sub(description, text)
    
    return new_text, (new_text != text)

# =========================================================
# Load MOPtemp.xlsx and search/replace
# =========================================================
print(f"\n📖 Loading {mop_temp_file}...")
mop_wb = load_workbook(mop_temp_file)

# Determine which sheets to process
sheets_to_process = args.sheets if args.sheets else mop_wb.sheetnames

# Validate sheet names if specific sheets requested
if args.sheets:
    invalid_sheets = [s for s in args.sheets if s not in mop_wb.sheetnames]
    if invalid_sheets:
        print(f"⚠️  Warning: The following sheets were not found: {', '.join(invalid_sheets)}")
        sheets_to_process = [s for s in args.sheets if s in mop_wb.sheetnames]

if not sheets_to_process:
    print("❌ No valid sheets to process. Exiting.")
    raise SystemExit

print(f"📝 Searching and replacing IPs in {len(sheets_to_process)} sheet(s)...")
if args.preview:
    print("🔍 PREVIEW MODE - No changes will be saved\n")

for sheet_name in sheets_to_process:
    sheet = mop_wb[sheet_name]
    print(f"\n  🔎 Processing sheet: '{sheet_name}'")
    sheet_replacements = 0
    
    for row in sheet.iter_rows():
        for cell in row:
            if cell.value is None:
                continue
            
            cell_value = str(cell.value)
            original_value = cell_value
            replaced_ips = []
            
            # Check if any of our IPs exist in this cell
            for ip, description in ip_to_description.items():
                new_value, was_replaced = replace_ip_in_text(
                    cell_value, ip, description, args.case_sensitive
                )
                if was_replaced:
                    cell_value = new_value
                    replaced_ips.append(f"{ip} → {description}")
            
            # If the value changed, update the cell
            if cell_value != original_value:
                if not args.preview:
                    cell.value = cell_value
                
                sheet_replacements += 1
                replacement_count += 1
                
                change_info = {
                    'sheet': sheet_name,
                    'cell': cell.coordinate,
                    'original': original_value,
                    'new': cell_value,
                    'replacements': replaced_ips
                }
                changes_log.append(change_info)
                
                print(f"    ✓ Cell {cell.coordinate}:")
                print(f"      Before: {original_value}")
                print(f"      After:  {cell_value}")
                for replacement in replaced_ips:
                    print(f"      • {replacement}")
    
    if sheet_replacements > 0:
        print(f"  ✅ {'Would make' if args.preview else 'Made'} {sheet_replacements} replacement(s) in '{sheet_name}'")
    else:
        print(f"  ℹ️  No replacements needed in '{sheet_name}'")

# =========================================================
# Save the updated workbook
# =========================================================
if not args.preview:
    if args.overwrite:
        output_file = mop_temp_file
        print(f"\n💾 Saving changes to original file '{output_file}'...")
    else:
        output_file = os.path.join(script_dir, "MOPtemp_updated.xlsx")
        print(f"\n💾 Saving updated workbook to '{output_file}'...")
    
    mop_wb.save(output_file)
    print(f"✅ File saved successfully!")
else:
    print(f"\n🔍 Preview complete - no changes were saved")

# =========================================================
# Summary
# =========================================================
print(f"\n" + "="*60)
print(f"📊 SUMMARY")
print(f"="*60)
print(f"Total replacements {'(preview)' if args.preview else ''}: {replacement_count}")
print(f"Sheets processed: {len(sheets_to_process)}")
print(f"IPs in mapping: {len(ip_to_description)}")

if replacement_count > 0:
    print(f"\n📝 Detailed change log:")
    for i, change in enumerate(changes_log, 1):
        print(f"\n{i}. Sheet: {change['sheet']}, Cell: {change['cell']}")
        print(f"   Replacements: {', '.join(change['replacements'])}")

if not args.preview and not args.overwrite:
    print(f"\n💡 Tip: Review '{os.path.basename(output_file)}' and if satisfied,")
    print(f"         you can rename it to 'MOPtemp.xlsx'")
elif args.preview:
    print(f"\n💡 Tip: Run without --preview to apply these changes")
    print(f"         Add --overwrite to modify the original file directly")

print(f"\n✅ Script completed successfully!")
