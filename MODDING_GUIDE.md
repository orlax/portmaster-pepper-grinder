# Pepper Grinder Asset Modding Guide

## Complete Workflow: Extract → Modify → Repack → Test

### Step 1: Extract Assets

Extract assets from the original game:

```bash
python3 extract_pepper_grinder.py assets_linux/Assets.dat extracted_assets
```

This creates:
- `extracted_assets/images/image_XXXXX.bin` (10,260 images)
- `extracted_assets/sounds/sound_XXX.wav` (267 sounds)
- `extracted_assets/fonts/font_XX.bin` (19 fonts)

### Step 2: Decode Images to PNG

Decode the binary images to editable PNGs:

```bash
# Decode specific images
python3 decode_images.py extracted_assets/images/image_00000.bin

# Or decode all images (this will take a while for 10,260 images!)
python3 decode_images.py extracted_assets/images/ decoded_images/
```

### Step 3: Modify Assets

#### Option A: Make Sprites Magenta
```bash
# Use ImageMagick or similar
convert decoded_images/image_00100.png -modulate 100,100,300 modified_images/image_00100.png
```

#### Option B: Edit in GIMP/Photoshop
1. Open `decoded_images/image_XXXXX.png`
2. Make your changes (change colors, add text, etc.)
3. Save to `modified_images/image_XXXXX.png`

#### Option C: Python Script to Make Images Magenta
```python
from PIL import Image
import sys

img = Image.open(sys.argv[1])
pixels = img.load()
for y in range(img.height):
    for x in range(img.width):
        r, g, b, a = pixels[x, y]
        # Make it magenta (keep alpha)
        pixels[x, y] = (255, 0, 255, a)
img.save(sys.argv[2])
```

### Step 4: Encode Modified PNG Back to .bin

Encode your modified PNGs back to Chowdren format:

```bash
# Encode single image (preserves original metadata)
python3 encode_images.py modified_images/image_00100.png \
    repacked_assets/images/image_00100.bin \
    extracted_assets/images/image_00100.bin

# Or batch encode
python3 encode_images.py modified_images/ \
    repacked_assets/images/ \
    extracted_assets/images/
```

**Important**: Always provide the original .bin path (3rd argument) to preserve hotspot and texture metadata!

### Step 5: Repack Assets.dat

Create a new Assets.dat with your modifications:

```bash
python3 repack_assets.py \
    assets_linux/Assets.dat \
    repacked_assets/ \
    Assets_modded.dat
```

The script will:
- Copy all original assets
- Replace modified images/sounds
- Update the metadata tables
- Create `Assets_modded.dat`

### Step 6: Test in Game

1. **Backup the original**:
   ```bash
   cp assets_linux/Assets.dat assets_linux/Assets.dat.backup
   ```

2. **Replace with modded version**:
   ```bash
   cp Assets_modded.dat assets_linux/Assets.dat
   ```

3. **Run the game** and check if your modifications appear!

4. **Restore original if needed**:
   ```bash
   cp assets_linux/Assets.dat.backup assets_linux/Assets.dat
   ```

---

## Quick Test Example: Make Logo Magenta

Here's a complete example to modify what might be a logo:

```bash
# 1. Extract just a few images for testing
python3 extract_pepper_grinder.py assets_linux/Assets.dat extracted_assets

# 2. Decode first 100 images
mkdir decoded_images
for i in {0..99}; do
    python3 decode_images.py extracted_assets/images/image_$(printf "%05d" $i).bin \
        decoded_images/image_$(printf "%05d" $i).png
done

# 3. Look through decoded_images/ and find a logo or character sprite
# Let's say image_00050.png looks like a logo

# 4. Make it magenta (using ImageMagick)
convert decoded_images/image_00050.png -colorspace RGB -fill magenta -colorize 50% modified_images/image_00050.png

# 5. Encode it back
mkdir -p repacked_assets/images
python3 encode_images.py modified_images/image_00050.png \
    repacked_assets/images/image_00050.bin \
    extracted_assets/images/image_00050.bin

# 6. Repack
python3 repack_assets.py assets_linux/Assets.dat repacked_assets/ Assets_modded.dat

# 7. Test
cp assets_linux/Assets.dat assets_linux/Assets.dat.backup
cp Assets_modded.dat assets_linux/Assets.dat
# Run the game!
```

---

## Finding Specific Sprites

To find specific game elements:

1. **Look at file sizes**: Larger images are likely more important
   ```bash
   ls -lS decoded_images/ | head -20
   ```

2. **Search by dimensions**: Logo/title screens are often larger
   ```bash
   python3 -c "
   from PIL import Image
   from pathlib import Path
   for p in Path('decoded_images').glob('*.png'):
       img = Image.open(p)
       if img.size[0] > 200 or img.size[1] > 200:
           print(f'{p.name}: {img.size}')
   "
   ```

3. **Trial and error**: Modify a bunch and see what changes!

---

## Troubleshooting

**Game crashes on startup:**
- Your repacked Assets.dat might be corrupt
- Make sure you used the original .bin when encoding (3rd parameter)
- Restore the backup and try again

**Modifications don't appear:**
- The sprite you modified might not be used in the area you're testing
- Try modifying multiple sprites
- Check file sizes match (original vs. modified .bin)

**Images look wrong:**
- RGBA format required - make sure your PNG has an alpha channel
- Dimensions must match the original
- Use the original .bin as metadata source when encoding

---

## Advanced: Batch Processing

To make ALL sprites magenta:

```bash
# Extract all images
python3 extract_pepper_grinder.py assets_linux/Assets.dat extracted_assets

# Decode all
python3 decode_images.py extracted_assets/images/ decoded_images/

# Make them all magenta
for img in decoded_images/*.png; do
    convert "$img" -colorspace RGB -fill magenta -colorize 70% "modified_images/$(basename $img)"
done

# Re-encode all
python3 encode_images.py modified_images/ repacked_assets/images/ extracted_assets/images/

# Repack
python3 repack_assets.py assets_linux/Assets.dat repacked_assets/ Assets_modded.dat

# Test
cp assets_linux/Assets.dat assets_linux/Assets.dat.backup
cp Assets_modded.dat assets_linux/Assets.dat
```

Good luck modding! 🎮✨
