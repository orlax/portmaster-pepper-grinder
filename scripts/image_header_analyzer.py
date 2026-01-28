#!/usr/bin/env python3
"""
Analyze Chowdren image header to understand the format
"""

import struct
import sys

def analyze_image_header(filepath):
    """Analyze the first 64 bytes of an image file"""
    
    with open(filepath, 'rb') as f:
        data = f.read(64)
    
    print(f"Analyzing: {filepath}")
    print("="*80)
    print("\nHex dump of first 64 bytes:")
    for i in range(0, 64, 16):
        hex_str = ' '.join(f'{b:02x}' for b in data[i:i+16])
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
        print(f"{i:04x}: {hex_str:<48} {ascii_str}")
    
    print("\n" + "="*80)
    print("Trying different interpretations:")
    print("="*80)
    
    # Try as uint32 values
    print("\nAs uint32 (little-endian) values:")
    for i in range(0, min(48, len(data)), 4):
        if i + 4 <= len(data):
            val = struct.unpack('<I', data[i:i+4])[0]
            print(f"  Bytes {i:2d}-{i+3:2d}: {val:10d} (0x{val:08x})")
    
    # Try as uint16 values
    print("\nAs uint16 (little-endian) values:")
    for i in range(0, min(48, len(data)), 2):
        if i + 2 <= len(data):
            val = struct.unpack('<H', data[i:i+2])[0]
            print(f"  Bytes {i:2d}-{i+1:2d}: {val:5d} (0x{val:04x})")
    
    # Try as floats
    print("\nAs float (little-endian) values:")
    for i in range(0, min(48, len(data)), 4):
        if i + 4 <= len(data):
            try:
                val = struct.unpack('<f', data[i:i+4])[0]
                print(f"  Bytes {i:2d}-{i+3:2d}: {val:10.2f}")
            except:
                pass
    
    # Find zlib header
    print("\n" + "="*80)
    print("Looking for zlib header (78 9c):")
    print("="*80)
    for i in range(len(data) - 1):
        if data[i:i+2] == b'\x78\x9c':
            print(f"\nFound zlib header at byte {i} (0x{i:02x})")
            print(f"Header size: {i} bytes")
            break
    
    # Look for common small dimensions
    print("\n" + "="*80)
    print("Looking for likely width/height values (< 4096):")
    print("="*80)
    for i in range(0, min(48, len(data)), 2):
        if i + 2 <= len(data):
            val = struct.unpack('<H', data[i:i+2])[0]
            if 1 < val < 4096:
                print(f"  Byte {i:2d}: {val} (could be dimension)")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python analyze_image_header.py <image.bin>")
        sys.exit(1)
    
    analyze_image_header(sys.argv[1])