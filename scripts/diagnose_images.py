#!/usr/bin/env python3
"""
Diagnose corrupted or invalid .bin image files
"""

from pathlib import Path
import sys

def diagnose_bin_file(bin_path):
    """Check if a .bin file is valid"""
    try:
        file_size = bin_path.stat().st_size
        
        with open(bin_path, 'rb') as f:
            data = f.read()
        
        print(f"\n{bin_path.name}:")
        print(f"  File size: {file_size} bytes")
        
        if file_size < 50:
            print(f"  ⚠ ERROR: File too small for valid header (need 50 bytes minimum)")
            print(f"  First bytes: {data[:min(20, len(data))].hex()}")
            return False
        
        # Try to read header
        import struct
        try:
            width = struct.unpack('<H', data[0:2])[0]
            height = struct.unpack('<H', data[2:4])[0]
            decompressed_size = struct.unpack('<H', data[46:48])[0] if len(data) >= 48 else 0
            
            print(f"  Dimensions: {width}x{height}")
            print(f"  Decompressed size: {decompressed_size}")
            
            # Check for zlib header
            has_zlib = False
            zlib_offset = None
            for i in range(min(100, len(data) - 1)):
                if data[i:i+2] == b'\x78\x9c':
                    has_zlib = True
                    zlib_offset = i
                    break
            
            if has_zlib:
                print(f"  ✓ zlib header found at byte {zlib_offset}")
            else:
                print(f"  ⚠ No zlib header found in first 100 bytes")
            
            # Sanity checks
            if width == 0 or height == 0:
                print(f"  ⚠ Invalid dimensions (zero)")
                return False
            
            if width > 4096 or height > 4096:
                print(f"  ⚠ Suspiciously large dimensions")
                return False
            
            expected_pixels = width * height * 4
            if decompressed_size != expected_pixels:
                print(f"  ⚠ Size mismatch: expected {expected_pixels} bytes, header says {decompressed_size}")
            
            return True
            
        except Exception as e:
            print(f"  ✗ Error reading header: {e}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error opening file: {e}")
        return False

def scan_directory(directory, show_valid=False):
    """Scan directory and find all corrupted files"""
    
    bin_files = sorted(Path(directory).glob('image_*.bin'))
    
    print(f"Scanning {len(bin_files)} files in {directory}")
    print("="*60)
    
    valid = []
    invalid = []
    
    for bin_file in bin_files:
        is_valid = diagnose_bin_file(bin_file)
        
        if is_valid:
            valid.append(bin_file)
        else:
            invalid.append(bin_file)
    
    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"  Valid:   {len(valid)} files")
    print(f"  Invalid: {len(invalid)} files")
    
    if invalid:
        print(f"\nInvalid files:")
        for f in invalid:
            index = int(f.stem.split('_')[1])
            print(f"  - image_{index:05d}.bin")
    
    return valid, invalid

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Diagnose single file:")
        print("    python diagnose_images.py <image.bin>")
        print()
        print("  Scan entire directory:")
        print("    python diagnose_images.py <directory>")
        sys.exit(1)
    
    path = Path(sys.argv[1])
    
    if path.is_dir():
        scan_directory(path)
    elif path.is_file():
        diagnose_bin_file(path)
    else:
        print(f"Error: Path not found: {path}")
        sys.exit(1)

if __name__ == '__main__':
    main()