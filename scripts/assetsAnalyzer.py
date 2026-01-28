#!/usr/bin/env python3
"""
Analyze Pepper Grinder Assets.dat to find metadata structure
"""

import struct
import sys
from pathlib import Path

def analyze_assets_file(filepath):
    """Analyze an Assets.dat file to find the metadata block"""
    
    file_size = Path(filepath).stat().st_size
    print(f"File size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
    print(f"File size in hex: 0x{file_size:08x}")
    print()
    
    with open(filepath, 'rb') as f:
        # Read the last 1MB of the file (metadata is usually near the end)
        search_size = min(1024 * 1024, file_size)
        f.seek(-search_size, 2)  # Seek to 1MB before end
        tail_data = f.read()
        
        print("Searching for potential metadata offsets...")
        print("Looking for large numbers that could be the metadata offset...")
        print()
        
        # Search for potential metadata offset values
        # These would be large numbers close to the file size
        candidates = []
        
        # Search through the last 1MB for uint32 values
        for i in range(0, len(tail_data) - 4, 4):
            value = struct.unpack('<I', tail_data[i:i+4])[0]
            
            # Metadata offset should be:
            # 1. Large (> 100MB for a 160MB file)
            # 2. Less than file size
            # 3. Reasonably close to end (within last 10MB of file)
            if 100_000_000 < value < file_size and value > file_size - 10_000_000:
                offset_in_file = file_size - search_size + i
                candidates.append((offset_in_file, value))
        
        if candidates:
            print(f"Found {len(candidates)} potential metadata offset locations:")
            print()
            for file_offset, metadata_offset in candidates[:20]:  # Show first 20
                print(f"  At file offset 0x{file_offset:08x}: metadata_offset = 0x{metadata_offset:08x} ({metadata_offset:,})")
                
                # Try to read what comes after this potential metadata offset
                f.seek(file_offset + 4)
                following_values = struct.unpack('<10I', f.read(40))
                print(f"    Following 10 uint32 values: {following_values}")
                
                # Check if these look like reasonable asset counts
                if all(0 < v < 10000 for v in following_values[:6]):
                    print(f"    ^^^ LOOKS PROMISING! These could be asset counts!")
                print()
        
        # Also try looking for the pattern at specific likely locations
        print("\n" + "="*80)
        print("Checking specific offset near end of file...")
        print("="*80 + "\n")
        
        # Try the last 4KB (common location for metadata)
        f.seek(-4096, 2)
        last_4kb = f.read()
        
        print("Last 4KB as uint32 values:")
        for i in range(0, len(last_4kb), 16):
            chunk = last_4kb[i:i+16]
            if len(chunk) == 16:
                values = struct.unpack('<4I', chunk)
                offset = file_size - 4096 + i
                print(f"0x{offset:08x}: {values[0]:12,} {values[1]:12,} {values[2]:12,} {values[3]:12,}")
        
        print("\n" + "="*80)
        print("Searching for 'OggS' headers (sound files)...")
        print("="*80 + "\n")
        
        # Search for OggS headers to understand sound format
        f.seek(0)
        ogg_positions = []
        chunk_size = 1024 * 1024
        position = 0
        
        while position < file_size and len(ogg_positions) < 10:
            f.seek(position)
            chunk = f.read(chunk_size)
            
            # Search for OggS signature
            ogg_idx = chunk.find(b'OggS')
            if ogg_idx != -1:
                ogg_pos = position + ogg_idx
                ogg_positions.append(ogg_pos)
                print(f"Found OggS at offset: 0x{ogg_pos:08x} ({ogg_pos:,})")
                
                # Read the bytes before OggS to see if there's a size header
                f.seek(ogg_pos - 8)
                before_ogg = f.read(8)
                potential_sizes = struct.unpack('<2I', before_ogg)
                print(f"  8 bytes before: {potential_sizes} (0x{potential_sizes[0]:08x}, 0x{potential_sizes[1]:08x})")
                
                position = ogg_pos + 4  # Move past this OggS
            else:
                position += chunk_size - 4  # Overlap to catch boundary cases
        
        if not ogg_positions:
            print("No OggS headers found in first pass")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python analyze_assets.py <path_to_Assets.dat>")
        sys.exit(1)
    
    analyze_assets_file(sys.argv[1])