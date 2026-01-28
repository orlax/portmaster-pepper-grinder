# Pepper Grinder Reverse Engineering Scripts

This document provides usage instructions for all the tools created during the reverse engineering process.

---

## Table of Contents
- [Extract Assets](#extract-assets)
- [Decode Images](#decode-images)
- [Encode Images](#encode-images)
- [Repack Assets](#repack-assets)
- [Optimization Tools](#optimization-tools)

---

## Extract Assets

**Script:** `extract.py`

**Description:** Extracts all assets from Pepper Grinder's `Assets.dat` file. Supports the 2024 Chowdren format with offset+size pairs.

**Extracts:**
- 10,260 images (saved as `.bin` files)
- 267 sounds (saved as `.wav` or `.ogg`)
- 19 fonts (saved as `.ttf` or `.bin`)
- 3 shaders (saved as `.glsl`)

**Usage:**
```bash
python3 extract.py <path_to_Assets.dat> [output_dir]
```

**Examples:**
```bash
# Extract to default directory (./extracted_assets)
python3 extract.py assets_linux/Assets.dat

# Extract to custom directory
python3 extract.py assets_linux/Assets.dat my_extracted_assets/
```

**Output structure:**
```
extracted_assets/
├── images/
│   ├── image_00000.bin
│   ├── image_00001.bin
│   └── ...
├── sounds/
│   ├── sound_000.wav
│   ├── sound_001.ogg
│   └── ...
├── fonts/
│   ├── font_00.ttf
│   └── ...
└── shaders/
    ├── shader_00.glsl
    └── ...
```

**Features:**
- Displays asset distribution statistics
- Auto-detects file formats (WAV, OGG, TTF, etc.)
- Shows progress and file information

---

## Decode Images

**Script:** `decode_images.py`

**Description:** Converts Chowdren `.bin` image files to standard PNG format. Handles zlib-compressed RGBA pixel data with custom 50-byte headers.

**Usage:**
```bash
# Decode single image
python3 decode_images.py <image.bin> [output.png]

# Decode entire directory
python3 decode_images.py <directory> [output_directory]
```

**Examples:**
```bash
# Single image
python3 decode_images.py extracted_assets/images/image_00123.bin player_sprite.png

# Batch decode all images
python3 decode_images.py extracted_assets/images/ decoded_images/
```

**Output:**
- PNG files with original dimensions and transparency
- Displays dimensions, compression info, and format details

**Notes:**
- Handles RGBA and RGB formats
- Preserves transparency (alpha channel)
- About ~110 images may fail (corrupted/invalid files <50 bytes)

---

## Encode Images

**Script:** `encode_images_fixed.py`

**Description:** Converts PNG files back to Chowdren `.bin` format. Includes critical fixes for dimension changes and mystery byte handling.

**Usage:**
```bash
python3 encode_images_fixed.py <input.png> <output.bin> [original.bin] [width] [height]
```

**Arguments:**
- `input.png` - Input PNG file
- `output.bin` - Output `.bin` file
- `original.bin` - (Optional) Original `.bin` for metadata preservation
- `width height` - (Optional) Target dimensions for resizing

**Examples:**
```bash
# Preserve original dimensions and metadata
python3 encode_images_fixed.py modified.png output.bin original.bin

# Resize to 64x64 pixels
python3 encode_images_fixed.py sprite.png resized.bin original.bin 64 64

# Create new image without original metadata
python3 encode_images_fixed.py new_sprite.png output.bin
```

**Important features:**
- **Mystery byte fix:** Automatically zeros bytes 20-45 when dimensions change
- **Size validation:** Checks uint16 limit (max 65,535 bytes decompressed)
- **Maximum safe dimensions:** ~127×127 pixels for RGBA
- **Metadata preservation:** Keeps hotspots, flags, and texture coordinates from original

**Size limits:**
```
RGBA format: 4 bytes per pixel
Max decompressed: 65,535 bytes (uint16 limit)
Max pixels: 16,383 (65,535 ÷ 4)
Safe dimensions: 127×127 or smaller
```

---

## Repack Assets

**Script:** `repack_assets.py`

**Description:** Rebuilds `Assets.dat` with modified assets. Automatically copies unmodified assets from the original file.

**Usage:**
```bash
python3 repack_assets.py <original_Assets.dat> <modified_dir> <output_Assets.dat>
```

**Example:**
```bash
python3 repack_assets.py assets_linux/Assets.dat repacked_assets/ Assets_modded.dat
```

**Required directory structure:**
```
repacked_assets/
├── images/
│   ├── image_00123.bin  # Modified images
│   └── image_00456.bin
├── sounds/
│   ├── sound_042.wav    # Modified sounds
│   └── sound_100.ogg
├── fonts/               # (not yet supported)
└── shaders/             # (not yet supported)
```

**Features:**
- Only include files you want to modify
- Automatically copies unmodified assets from original
- Updates all offset tables
- Displays progress and statistics
- Shows which assets were modified

**Notes:**
- Fonts and shaders are always copied from original (modification not supported yet)
- File naming must match pattern: `image_XXXXX.bin` or `sound_XXX.wav`
- Output file size may differ from original (different compression)

---

## Optimization Tools

### Audio Optimizer

**Script:** `optimize_audio.py`

**Description:** Downsamples audio files to reduce memory usage. Converts to 22kHz mono format.

**Usage:**
```bash
python3 optimize_audio.py <input_sounds_dir> <output_dir>
```

**Example:**
```bash
python3 optimize_audio.py extracted_assets/sounds/ optimized_sounds/
```

**Requirements:**
- `ffmpeg` installed on system
- Script must include `-strict -2` flag (for experimental vorbis encoder)

**Expected savings:** ~16MB RAM reduction (tested: 737MB → 721MB)

---

### Silent Audio Creator

**Script:** `create_silent_audio.py`

**Description:** Creates minimal silent audio files (100ms duration) to test maximum audio RAM impact.

**Usage:**
```bash
python3 create_silent_audio.py <extracted_sounds_dir> <output_dir>
```

**Example:**
```bash
python3 create_silent_audio.py extracted_assets/sounds/ silent_sounds/
```

**Features:**
- Generates tiny WAV files (~2KB each)
- Attempts OGG creation with ffmpeg fallback to WAV
- Used for testing: confirms audio uses only ~19MB RAM

---

### Smart Image Optimizer

**Script:** `optimize_smart.py`

**Description:** Batch resize images with smart filtering and automatic mystery byte fix.

**Usage:**
```bash
python3 optimize_smart.py <decoded_images_dir> <output_dir> --scale 0.5 --min-size 16
```

**Arguments:**
- `--scale` - Resize scale (e.g., 0.5 = 50% dimensions)
- `--min-size` - Skip images smaller than this (default: 16 pixels)

**Example:**
```bash
# Resize all images to 50%, skip images ≤16×16
python3 optimize_smart.py decoded_images/ optimized_images/ --scale 0.5

# Resize to 75%, skip images ≤32×32
python3 optimize_smart.py decoded_images/ optimized_images/ --scale 0.75 --min-size 32
```

**Warning:** Image resizing breaks the Chowdren engine and increases RAM usage. Not recommended for actual optimization.

---

## Complete Workflow Example

Here's a complete workflow to modify sprites:

```bash
# 1. Extract assets
python3 extract.py assets_linux/Assets.dat extracted_assets/

# 2. Decode images to PNG
python3 decode_images.py extracted_assets/images/ decoded_images/

# 3. Edit images (use GIMP, Photoshop, etc.)
#    For example, edit decoded_images/image_01800.png

# 4. Encode modified images back to .bin
python3 encode_images_fixed.py decoded_images/image_01800.png modified_01800.bin extracted_assets/images/image_01800.bin

# 5. Prepare repacking directory
mkdir -p repacked_assets/images
cp modified_01800.bin repacked_assets/images/image_01800.bin

# 6. Repack Assets.dat
python3 repack_assets.py assets_linux/Assets.dat repacked_assets/ Assets_modded.dat

# 7. Backup and test
cp assets_linux/Assets.dat assets_linux/Assets.dat.backup
cp Assets_modded.dat assets_linux/Assets.dat

# 8. Run the game
./Chowdren_pepper
```

---

## Audio-Only Optimization Workflow

To optimize only audio (recommended approach):

```bash
# 1. Extract assets
python3 extract.py assets_linux/Assets.dat extracted_assets/

# 2. Optimize audio
python3 optimize_audio.py extracted_assets/sounds/ optimized_sounds/

# 3. Prepare repacking directory (audio only)
mkdir -p repacked_assets/sounds
cp -r optimized_sounds/* repacked_assets/sounds/

# 4. Clear other directories (so originals are used)
rm -rf repacked_assets/images/*
rm -rf repacked_assets/fonts/*
rm -rf repacked_assets/shaders/*

# 5. Repack with optimized audio only
python3 repack_assets.py assets_linux/Assets.dat repacked_assets/ Assets_audio_opt.dat

# 6. Test
cp assets_linux/Assets.dat assets_linux/Assets.dat.backup
cp Assets_audio_opt.dat assets_linux/Assets.dat
```

---

## Diagnostic Tools

### Test Encoder Fix

**Script:** `test_encoder_fix.py`

**Description:** Verifies that mystery bytes (20-45) are properly zeroed in encoded images.

**Usage:**
```bash
python3 test_encoder_fix.py <encoded_image.bin>
```

---

### Diagnose Images

**Script:** `diagnose_images.py`

**Description:** Scans for corrupted or invalid `.bin` files in a directory.

**Usage:**
```bash
python3 diagnose_images.py <images_directory>
```

**Checks for:**
- Files smaller than 50 bytes (invalid header)
- Missing zlib compressed data
- Dimension mismatches

---

## Technical Notes

### Image Format Structure
```
Bytes 0-1:   Width (uint16)
Bytes 2-3:   Height (uint16)
Bytes 4-5:   Width copy
Bytes 6-7:   Height copy
Bytes 8-11:  Unknown
Bytes 12-13: Width copy
Bytes 14-15: Height copy
Bytes 16-19: Hotspot X (float)
Bytes 20-23: Hotspot Y (float)
Bytes 24-25: Flags (uint16)
Bytes 26-45: Mystery bytes (MUST be zeroed if dimensions change)
Bytes 46-47: Decompressed size (uint16)
Byte 50+:    zlib compressed RGBA pixel data
```

### Asset Table Format (2024 Chowdren)
```
Each entry: 8 bytes
  Bytes 0-3: Offset (uint32)
  Bytes 4-7: Size (uint32)

Table locations:
  Images:  Offset 0,     10,260 entries
  Sounds:  Offset 82048, 267 entries
  Fonts:   Offset 84184, 19 entries
  Shaders: Offset 84336, 3 entries
```

---

## Common Issues

### "Image too large" error
**Problem:** Decompressed size exceeds 65,535 bytes  
**Solution:** Resize image to ≤127×127 pixels before encoding

### Textures appear corrupted in-game
**Problem:** Mystery bytes (20-45) not properly zeroed  
**Solution:** Use `encode_images_fixed.py` which includes the fix

### Game uses more RAM after optimization
**Problem:** Resizing breaks engine assumptions  
**Solution:** Don't resize images; focus on audio optimization instead

### "zlib not found" during decode
**Problem:** Image file is corrupted or <50 bytes  
**Solution:** Skip the file or extract from original Assets.dat again

---

## Requirements

- Python 3.6+
- PIL/Pillow (`pip install pillow`)
- ffmpeg (for audio optimization)

---

**Last Updated:** January 28, 2026