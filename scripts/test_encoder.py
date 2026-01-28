#!/usr/bin/env python3
"""
Test the fixed encoder on a single image
"""

import sys
from pathlib import Path

# Test: Resize image 01800 and verify bytes 20-45 are zeroed

print("Testing fixed encoder...")
print("="*60)

# 1. Extract original
print("\n1. Extracting image 01800...")
import subprocess
subprocess.run([
    sys.executable, 'extract.py',
    'assets_linux/Assets.dat', 'test_fix/'
], capture_output=True)

# 2. Decode
print("2. Decoding...")
subprocess.run([
    sys.executable, 'decode_images.py',
    'test_fix/images/image_01800.bin',
    'test_fix_decoded.png'
], capture_output=True)

# 3. Encode with resize using FIXED encoder
print("3. Encoding with resize (20x20)...")
result = subprocess.run([
    sys.executable, 'encode_images_fixed.py',
    'test_fix_decoded.png',
    'test_fix_resized.bin',
    'test_fix/images/image_01800.bin',
    '20', '20'
], capture_output=True, text=True)

print(result.stdout)
if result.stderr:
    print("Errors:", result.stderr)

# 4. Check the bytes
print("\n4. Verifying bytes 20-45 are zeroed...")
with open('test_fix_resized.bin', 'rb') as f:
    data = f.read(50)

mystery_bytes = data[20:46]
print(f"Bytes 20-45: {mystery_bytes.hex()}")

if mystery_bytes == b'\x00' * 26:
    print("✓ SUCCESS! Mystery bytes are properly zeroed!")
    print("\nThe fix is working. Now test in-game:")
    print("1. Run: python3 optimize_smart.py extracted_assets/images/ repacked_assets/images/ 0.5 1.0")
    print("2. Run: python3 repack_assets.py assets_linux/Assets.dat repacked_assets/ Assets_fixed.dat")
    print("3. Test Assets_fixed.dat in the game!")
else:
    print("✗ FAILED! Mystery bytes still contain data:")
    print(f"  Expected: {'00' * 26}")
    print(f"  Got:      {mystery_bytes.hex()}")

print("="*60)