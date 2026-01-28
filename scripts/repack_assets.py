#!/usr/bin/env python3
"""
Repack Pepper Grinder's Assets.dat with modified assets
"""

import struct
import sys
from pathlib import Path

# Pepper Grinder format
METADATA_OFFSET = 0
IMAGE_COUNT = 10260
SOUND_COUNT = 267
FONT_COUNT = 19
SHADER_COUNT = 3

TABLE_OFFSETS = {
    'images': 0,
    'sounds': 82048,   # 0x14080
    'fonts': 84184,    # 0x14080 + 0x858
    'shaders': 84336   # 0x14080 + 0x858 + 0x98
}

def read_asset_table(f, table_offset, count):
    """Read an asset table (offset+size pairs)"""
    f.seek(table_offset)
    entries = []
    
    for i in range(count):
        data = f.read(8)
        if len(data) < 8:
            break
        offset, size = struct.unpack('<II', data)
        entries.append([offset, size])  # Use list so we can modify
    
    return entries

def write_asset_table(f, table_offset, entries):
    """Write an asset table (offset+size pairs)"""
    f.seek(table_offset)
    
    for offset, size in entries:
        f.write(struct.pack('<II', offset, size))

def repack_assets(original_assets, modified_dir, output_assets):
    """
    Repack Assets.dat with modified assets
    
    Args:
        original_assets: Path to original Assets.dat
        modified_dir: Directory containing modified .bin files
        output_assets: Path to output Assets.dat
    """
    
    print(f"\n{'='*80}")
    print(f"REPACKING ASSETS.DAT")
    print(f"{'='*80}")
    print(f"Original:  {original_assets}")
    print(f"Modified:  {modified_dir}")
    print(f"Output:    {output_assets}")
    print(f"{'='*80}\n")
    
    modified_path = Path(modified_dir)
    
    # Read original asset tables
    print("Reading original asset tables...")
    with open(original_assets, 'rb') as f:
        image_table = read_asset_table(f, TABLE_OFFSETS['images'], IMAGE_COUNT)
        sound_table = read_asset_table(f, TABLE_OFFSETS['sounds'], SOUND_COUNT)
        font_table = read_asset_table(f, TABLE_OFFSETS['fonts'], FONT_COUNT)
        shader_table = read_asset_table(f, TABLE_OFFSETS['shaders'], SHADER_COUNT)
    
    print(f"  Images:  {len(image_table)} entries")
    print(f"  Sounds:  {len(sound_table)} entries")
    print(f"  Fonts:   {len(font_table)} entries")
    print(f"  Shaders: {len(shader_table)} entries")
    
    # Find modified images
    modified_images = {}
    images_dir = modified_path / 'images'
    if images_dir.exists():
        for bin_file in images_dir.glob('*.bin'):
            # Extract index from filename (e.g., image_00123.bin -> 123)
            name = bin_file.stem
            if name.startswith('image_'):
                try:
                    index = int(name.split('_')[1])
                    if 0 <= index < IMAGE_COUNT:
                        modified_images[index] = bin_file
                except (ValueError, IndexError):
                    pass
    
    print(f"\nFound {len(modified_images)} modified images")
    
    # Find modified sounds
    modified_sounds = {}
    sounds_dir = modified_path / 'sounds'
    if sounds_dir.exists():
        for sound_file in sounds_dir.glob('sound_*.wav'):
            name = sound_file.stem
            if name.startswith('sound_'):
                try:
                    index = int(name.split('_')[1])
                    if 0 <= index < SOUND_COUNT:
                        modified_sounds[index] = sound_file
                except (ValueError, IndexError):
                    pass
    
    print(f"Found {len(modified_sounds)} modified sounds")
    
    # Calculate metadata size
    metadata_size = (IMAGE_COUNT * 8 + SOUND_COUNT * 8 + 
                     FONT_COUNT * 8 + SHADER_COUNT * 8)
    
    # Start writing new Assets.dat
    print(f"\nBuilding new Assets.dat...")
    
    with open(original_assets, 'rb') as orig_f:
        with open(output_assets, 'wb') as new_f:
            
            # Reserve space for metadata (we'll write it at the end)
            new_f.write(b'\x00' * metadata_size)
            
            current_offset = metadata_size
            
            # Write images
            print(f"\nProcessing images...")
            for i in range(IMAGE_COUNT):
                if i in modified_images:
                    # Write modified image
                    with open(modified_images[i], 'rb') as img_f:
                        data = img_f.read()
                    
                    new_f.seek(current_offset)
                    new_f.write(data)
                    
                    image_table[i][0] = current_offset
                    image_table[i][1] = len(data)
                    
                    if i < 10 or i in list(modified_images.keys())[:5]:
                        print(f"  Image {i:5d}: MODIFIED - offset=0x{current_offset:08x}, size={len(data):8,} bytes")
                    
                    current_offset += len(data)
                else:
                    # Copy original image
                    orig_offset, orig_size = image_table[i]
                    orig_f.seek(orig_offset)
                    data = orig_f.read(orig_size)
                    
                    new_f.seek(current_offset)
                    new_f.write(data)
                    
                    image_table[i][0] = current_offset
                    # Size stays the same
                    
                    current_offset += orig_size
                
                if (i + 1) % 1000 == 0:
                    print(f"  Processed {i+1}/{IMAGE_COUNT} images...")
            
            print(f"  ✓ All {IMAGE_COUNT} images processed")
            
            # Write sounds
            print(f"\nProcessing sounds...")
            for i in range(SOUND_COUNT):
                if i in modified_sounds:
                    # Write modified sound
                    with open(modified_sounds[i], 'rb') as snd_f:
                        data = snd_f.read()
                    
                    new_f.seek(current_offset)
                    new_f.write(data)
                    
                    sound_table[i][0] = current_offset
                    sound_table[i][1] = len(data)
                    
                    print(f"  Sound {i:3d}: MODIFIED - offset=0x{current_offset:08x}, size={len(data):8,} bytes")
                    
                    current_offset += len(data)
                else:
                    # Copy original sound
                    orig_offset, orig_size = sound_table[i]
                    orig_f.seek(orig_offset)
                    data = orig_f.read(orig_size)
                    
                    new_f.seek(current_offset)
                    new_f.write(data)
                    
                    sound_table[i][0] = current_offset
                    
                    current_offset += orig_size
            
            print(f"  ✓ All {SOUND_COUNT} sounds processed")
            
            # Write fonts (always copy original)
            print(f"\nProcessing fonts...")
            for i in range(FONT_COUNT):
                orig_offset, orig_size = font_table[i]
                orig_f.seek(orig_offset)
                data = orig_f.read(orig_size)
                
                new_f.seek(current_offset)
                new_f.write(data)
                
                font_table[i][0] = current_offset
                current_offset += orig_size
            
            print(f"  ✓ All {FONT_COUNT} fonts processed")
            
            # Write shaders (always copy original)
            print(f"\nProcessing shaders...")
            for i in range(SHADER_COUNT):
                orig_offset, orig_size = shader_table[i]
                if orig_size > 0 and orig_offset > 0:
                    orig_f.seek(orig_offset)
                    data = orig_f.read(orig_size)
                    
                    new_f.seek(current_offset)
                    new_f.write(data)
                    
                    shader_table[i][0] = current_offset
                    current_offset += orig_size
            
            print(f"  ✓ All {SHADER_COUNT} shaders processed")
            
            # Write updated metadata tables at the beginning
            print(f"\nWriting metadata tables...")
            write_asset_table(new_f, TABLE_OFFSETS['images'], image_table)
            write_asset_table(new_f, TABLE_OFFSETS['sounds'], sound_table)
            write_asset_table(new_f, TABLE_OFFSETS['fonts'], font_table)
            write_asset_table(new_f, TABLE_OFFSETS['shaders'], shader_table)
            
            print(f"  ✓ Metadata written")
            
            final_size = current_offset
    
    print(f"\n{'='*80}")
    print(f"REPACKING COMPLETE!")
    print(f"{'='*80}")
    print(f"Output file: {output_assets}")
    print(f"Final size:  {final_size:,} bytes ({final_size/1024/1024:.2f} MB)")
    print(f"\nModified assets:")
    print(f"  Images: {len(modified_images)}")
    print(f"  Sounds: {len(modified_sounds)}")
    print(f"{'='*80}\n")

def main():
    if len(sys.argv) != 4:
        print("Usage: python repack_assets.py <original_Assets.dat> <modified_dir> <output_Assets.dat>")
        print()
        print("The modified_dir should contain:")
        print("  images/image_XXXXX.bin  - Modified image files")
        print("  sounds/sound_XXX.wav    - Modified sound files")
        print()
        print("Example:")
        print("  python repack_assets.py assets_linux/Assets.dat modified_assets/ Assets_modded.dat")
        sys.exit(1)
    
    original = sys.argv[1]
    modified_dir = sys.argv[2]
    output = sys.argv[3]
    
    if not Path(original).exists():
        print(f"Error: Original Assets.dat not found: {original}")
        sys.exit(1)
    
    if not Path(modified_dir).exists():
        print(f"Error: Modified directory not found: {modified_dir}")
        sys.exit(1)
    
    repack_assets(original, modified_dir, output)

if __name__ == '__main__':
    main()
