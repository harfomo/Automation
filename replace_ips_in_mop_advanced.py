from openpyxl import load_workbook
import os
import re
import argparse

# =========================================================
# Configuration & Arguments
# =========================================================
script_dir = os.path.dirname(os.path.abspath(__file__))
mop_temp_file = os.path.join(script_dir, "MOPtemp.xlsx")

parser = argparse.ArgumentParser(
    description='Replace Neighbor IPs with Descriptions in MOPtemp.xlsx using its own Neighbors sheet'
)
parser.add_argument('--overwrite', action='store_true', 
                    help='Overwrite the original MOPtemp.xlsx instead of creating a new file')
parser.add_argument('--sheets', nargs='+', 
                    help='Specific sheet names to process (default: all except Neighbors)')
parser.add_argument('--include-neighbors', action='store_true',
                    help='Also process the Neighbors sheet itself (default: skip it)')
parser.add_argument('--preview', action='store_true',
                    help='Preview changes without saving (dry run)')
parser.add_argument('--verbose', action='store_true',
                    help='Show detailed output for each replacement')
args = parser.parse_args()

# =========================================================
# Validation
# =========================================================
if not os.path.exists(mop_temp_file):
    print(f"❌ Error: '{mop_temp_file}' not found!")
    print("   Please ensure MOPtemp.xlsx exists in the script directory.")
    raise SystemExit

# =========================================================
# Load MOPtemp.xlsx
# =========================================================
print(f"📖 Loading {mop_temp_file}...")
mop_wb = load_workbook(mop_temp_file)

if "Neighbors" not in mop_wb.sheetnames:
    print("❌ Error: 'Neighbors' sheet not found in MOPtemp.xlsx")
    print(f"   Available sheets: {', '.join(mop_wb.sheetnames)}")
    raise SystemExit

neighbors_sheet = mop_wb["Neighbors"]

# =========================================================
# Build IP -> Description mapping from Neighbors sheet
# =========================================================
ip_to_description = {}
replacement_count = 0
changes_log = []

print("🔍 Building IP to Description mapping from Neighbors sheet...")

# Try to find the header row to determine column positions
header_row = None
neighbor_desc_col = None
neighbor_ip_col = None
device_ip_col = None

for row_idx, row in enumerate(neighbors_sheet.iter_rows(min_row=1, max_row=10, values_only=True), start=1):
    if row:
        for col_idx, cell_value in enumerate(row):
            if cell_value:
                cell_str = str(cell_value).strip().lower()
                if 'device ip' in cell_str:
                    device_ip_col = col_idx
                    header_row = row_idx
                elif 'neighbor description' in cell_str or (cell_str == 'description' or cell_str.endswith('description')):
                    neighbor_desc_col = col_idx
                    header_row = row_idx
                elif 'neighbor ip' in cell_str or cell_str == 'neighbor ip':
                    neighbor_ip_col = col_idx
                    header_row = row_idx
        
        if neighbor_desc_col is not None and neighbor_ip_col is not None:
            break

# Default to standard layout if headers not found
if neighbor_desc_col is None or neighbor_ip_col is None:
    print("   ⚠️  Could not auto-detect columns, using default layout:")
    print("      Column A (index 0) = Device IP")
    print("      Column B (index 1) = Neighbor Description")
    print("      Column C (index 2) = Neighbor IP")
    device_ip_col = 0
    neighbor_desc_col = 1
    neighbor_ip_col = 2
    header_row = 1
else:
    print(f"   ✅ Auto-detected columns:")
    if device_ip_col is not None:
        print(f"      Column {chr(65 + device_ip_col)} = Device IP")
    print(f"      Column {chr(65 + neighbor_desc_col)} = Neighbor Description")
    print(f"      Column {chr(65 + neighbor_ip_col)} = Neighbor IP")

# Build the mapping
for row_num, row in enumerate(neighbors_sheet.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1):
    if not row or len(row) <= max(neighbor_desc_col, neighbor_ip_col):
        continue
    
    neighbor_desc = row[neighbor_desc_col] if neighbor_desc_col < len(row) else None
    neighbor_ip = row[neighbor_ip_col] if neighbor_ip_col < len(row) else None
    
    if neighbor_ip and neighbor_desc:
        neighbor_ip_str = str(neighbor_ip).strip()
        neighbor_desc_str = str(neighbor_desc).strip()
        
        # Skip empty or placeholder values
        if neighbor_ip_str and neighbor_desc_str and neighbor_ip_str.lower() not in ['none', 'n/a', '-', 'null']:
            # Handle duplicates - keep first occurrence or more specific one
            if neighbor_ip_str in ip_to_description:
                if args.verbose:
                    print(f"   ⚠️  Duplicate IP found: {neighbor_ip_str}")
                    print(f"      Existing: {ip_to_description[neighbor_ip_str]}")
                    print(f"      New: {neighbor_desc_str}")
                    print(f"      Keeping: {ip_to_description[neighbor_ip_str]}")
            else:
                ip_to_description[neighbor_ip_str] = neighbor_desc_str

print(f"✅ Found {len(ip_to_description)} unique Neighbor IP -> Description mappings")

if not ip_to_description:
    print("⚠️  No valid mappings found. Exiting.")
    raise SystemExit

# Show mappings preview
print("\n📋 IP to Description mappings:")
if len(ip_to_description) <= 20 or args.verbose:
    for ip, desc in ip_to_description.items():
        print(f"   {ip} → {desc}")
else:
    for i, (ip, desc) in enumerate(list(ip_to_description.items())[:10]):
        print(f"   {ip} → {desc}")
    print(f"   ... and {len(ip_to_description) - 10} more")

# =========================================================
# Helper function for smart IP replacement
# =========================================================
def replace_ip_in_text(text, ip, description):
    """
    Replace IP with description in text, handling both IPv4 and IPv6.
    Returns (new_text, was_replaced)
    """
    original_text = text
    
    # Create case-insensitive pattern
    pattern = re.compile(re.escape(ip), re.IGNORECASE)
    
    # Check if pattern exists
    if not pattern.search(text):
        return text, False
    
    # For IPv6 (contains colons) and IPv4, use different strategies
    if ':' in ip:
        # IPv6 - direct replacement
        text = pattern.sub(description, text)
    else:
        # IPv4 - try word boundary first
        try:
            pattern_wb = re.compile(r'\b' + re.escape(ip) + r'\b', re.IGNORECASE)
            if pattern_wb.search(text):
                text = pattern_wb.sub(description, text)
            else:
                text = pattern.sub(description, text)
        except:
            text = pattern.sub(description, text)
    
    return text, (text != original_text)

# =========================================================
# Determine sheets to process
# =========================================================
if args.sheets:
    sheets_to_process = args.sheets
    # Validate sheet names
    invalid_sheets = [s for s in sheets_to_process if s not in mop_wb.sheetnames]
    if invalid_sheets:
        print(f"⚠️  Warning: The following sheets were not found: {', '.join(invalid_sheets)}")
        sheets_to_process = [s for s in sheets_to_process if s in mop_wb.sheetnames]
else:
    # Process all sheets except Neighbors (unless explicitly included)
    sheets_to_process = [s for s in mop_wb.sheetnames if s != "Neighbors" or args.include_neighbors]

if not sheets_to_process:
    print("❌ No valid sheets to process. Exiting.")
    raise SystemExit

# =========================================================
# Search and replace in sheets
# =========================================================
print(f"\n📝 Searching and replacing IPs in {len(sheets_to_process)} sheet(s)...")
if args.preview:
    print("🔍 PREVIEW MODE - No changes will be saved\n")

for sheet_name in sheets_to_process:
    sheet = mop_wb[sheet_name]
    
    if sheet_name == "Neighbors" and not args.include_neighbors:
        print(f"\n  ⏭️  Skipping sheet: '{sheet_name}' (source data)")
        continue
    
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
                new_value, was_replaced = replace_ip_in_text(cell_value, ip, description)
                if was_replaced:
                    cell_value = new_value
                    replaced_ips.append((ip, description))
            
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
                
                if args.verbose:
                    print(f"    ✓ Cell {cell.coordinate}:")
                    print(f"      Before: {original_value[:80]}{'...' if len(original_value) > 80 else ''}")
                    print(f"      After:  {cell_value[:80]}{'...' if len(cell_value) > 80 else ''}")
                    for ip, desc in replaced_ips:
                        print(f"      • {ip} → {desc}")
                elif sheet_replacements <= 5:  # Show first 5 in non-verbose mode
                    print(f"    ✓ Cell {cell.coordinate}: Replaced {len(replaced_ips)} IP(s)")
    
    if sheet_replacements > 0:
        status = "Would make" if args.preview else "Made"
        print(f"  ✅ {status} {sheet_replacements} replacement(s) in '{sheet_name}'")
        if not args.verbose and sheet_replacements > 5:
            print(f"     (showing first 5, use --verbose to see all)")
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
print(f"IP mappings used: {len(ip_to_description)}")

if replacement_count > 0 and args.verbose:
    print(f"\n📝 Detailed change log:")
    for i, change in enumerate(changes_log, 1):
        print(f"\n{i}. Sheet: '{change['sheet']}', Cell: {change['cell']}")
        print(f"   Original: {change['original'][:70]}{'...' if len(change['original']) > 70 else ''}")
        print(f"   Updated:  {change['new'][:70]}{'...' if len(change['new']) > 70 else ''}")
        print(f"   Replaced: {', '.join([f'{ip} → {desc}' for ip, desc in change['replacements']])}")

if not args.preview and not args.overwrite:
    print(f"\n💡 Tip: Review '{os.path.basename(output_file)}' and if satisfied,")
    print(f"         you can rename it to 'MOPtemp.xlsx' to replace the original.")
elif args.preview:
    print(f"\n💡 Run without --preview to apply these changes")
    print(f"   Add --overwrite to modify the original file directly")

print(f"\n✅ Script completed successfully!")
