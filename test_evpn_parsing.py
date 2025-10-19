#!/usr/bin/env python3
"""
Test script to verify EVPN output parsing logic.
Run this to ensure the regex pattern works correctly.
"""

import re

# Sample outputs from Cisco NXOS "show bgp l2vpn evpn rd X:Y | i prefixes"
test_outputs = [
    # Test case 1: Standard output
    """
Network          Next Hop        Metric     LocPrf     Weight Path
Route Distinguisher: 10.1.1.20:1

Processed 1541 prefixes, 3082 paths
    """,
    
    # Test case 2: Large numbers
    """
Route Distinguisher: 192.168.1.1:3

Processed 125678 prefixes, 251356 paths
    """,
    
    # Test case 3: Single digit
    """
Processed 5 prefixes, 10 paths
    """,
    
    # Test case 4: Different spacing
    """
Processed 100 prefixes,200 paths
    """,
    
    # Test case 5: Singular form
    """
Processed 1 prefix, 1 path
    """,
]

def parse_evpn_output(output):
    """
    Parse EVPN output to extract prefix and path counts.
    Returns: (prefix_count, path_count) or (None, None) if parsing fails
    """
    # More flexible regex that handles:
    # - Variable spacing around comma
    # - Singular and plural forms (prefix/prefixes, path/paths)
    match = re.search(r'Processed\s+(\d+)\s+prefixe?s?\s*,\s*(\d+)\s+paths?', output, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2)
    return None, None

def main():
    print("="*70)
    print("EVPN OUTPUT PARSING TEST")
    print("="*70)
    
    all_passed = True
    
    for i, output in enumerate(test_outputs, 1):
        print(f"\n📋 Test Case {i}:")
        print("-" * 70)
        print(output.strip())
        print("-" * 70)
        
        prefix_count, path_count = parse_evpn_output(output)
        
        if prefix_count and path_count:
            print(f"✅ PARSED SUCCESSFULLY")
            print(f"   Prefixes: {prefix_count}")
            print(f"   Paths:    {path_count}")
        else:
            print(f"❌ PARSING FAILED")
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Parsing logic is working correctly!")
    else:
        print("❌ SOME TESTS FAILED - Check regex pattern")
    print("="*70)

if __name__ == "__main__":
    main()
