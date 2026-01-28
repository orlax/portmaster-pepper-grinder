#!/usr/bin/env python3
"""
Create silent audio files to replace all Pepper Grinder audio.
This tests the maximum possible RAM savings from audio optimization.
"""

import struct
from pathlib import Path
import sys

def create_silent_wav(output_path, duration_ms=100, sample_rate=22050, channels=1):
    """
    Create a minimal silent WAV file.
    
    Args:
        output_path: Where to save the file
        duration_ms: Duration in milliseconds (default 100ms = tiny file)
        sample_rate: Sample rate in Hz
        channels: Number of channels (1=mono, 2=stereo)
    """
    num_samples = int((duration_ms / 1000.0) * sample_rate)
    data_size = num_samples * channels * 2  # 2 bytes per sample (16-bit)
    
    with open(output_path, 'wb') as f:
        # RIFF header
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + data_size))  # File size - 8
        f.write(b'WAVE')
        
        # fmt chunk
        f.write(b'fmt ')
        f.write(struct.pack('<I', 16))  # fmt chunk size
        f.write(struct.pack('<H', 1))   # PCM format
        f.write(struct.pack('<H', channels))
        f.write(struct.pack('<I', sample_rate))
        f.write(struct.pack('<I', sample_rate * channels * 2))  # byte rate
        f.write(struct.pack('<H', channels * 2))  # block align
        f.write(struct.pack('<H', 16))  # bits per sample
        
        # data chunk
        f.write(b'data')
        f.write(struct.pack('<I', data_size))
        f.write(b'\x00' * data_size)  # Silent audio data

def create_silent_ogg(output_path, duration_ms=100):
    """
    Create a minimal silent OGG file using ffmpeg.
    Falls back to WAV if ffmpeg fails.
    """
    import subprocess
    
    # Try to create silent OGG with ffmpeg
    try:
        duration_sec = duration_ms / 1000.0
        cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', f'anullsrc=r=22050:cl=mono',
            '-t', str(duration_sec), '-strict', '-2',
            '-y', str(output_path)
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=5)
        
        if result.returncode == 0:
            return True
    except:
        pass
    
    # Fallback: create WAV instead
    print(f"  (Creating WAV instead of OGG for {output_path.name})")
    create_silent_wav(output_path.with_suffix('.wav'), duration_ms)
    return False

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 create_silent_audio.py <extracted_sounds_dir> <output_dir>")
        print("\nExample:")
        print("  python3 create_silent_audio.py extracted_assets/sounds/ silent_sounds/")
        sys.exit(1)
    
    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    
    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}")
        sys.exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all audio files
    wav_files = list(input_dir.glob('*.wav'))
    ogg_files = list(input_dir.glob('*.ogg'))
    
    total_files = len(wav_files) + len(ogg_files)
    print(f"Creating {total_files} silent audio files...")
    print(f"  WAV files: {len(wav_files)}")
    print(f"  OGG files: {len(ogg_files)}")
    print()
    
    # Create silent WAV files
    for i, wav_file in enumerate(wav_files, 1):
        output_path = output_dir / wav_file.name
        create_silent_wav(output_path, duration_ms=100)
        if i % 50 == 0:
            print(f"  Created {i}/{len(wav_files)} WAV files...")
    
    print(f"  ✓ Created {len(wav_files)} silent WAV files")
    
    # Create silent OGG files
    ogg_success = 0
    for i, ogg_file in enumerate(ogg_files, 1):
        output_path = output_dir / ogg_file.name
        if create_silent_ogg(output_path, duration_ms=100):
            ogg_success += 1
        if i % 50 == 0:
            print(f"  Created {i}/{len(ogg_files)} OGG files...")
    
    print(f"  ✓ Created {len(ogg_files)} silent OGG files ({ogg_success} actual OGG, {len(ogg_files)-ogg_success} WAV fallback)")
    
    print(f"\n✓ Done! Silent audio files created in: {output_dir}")
    print(f"\nNext steps:")
    print(f"  1. Clear repacked_assets:")
    print(f"     rm -rf repacked_assets/images/* repacked_assets/fonts/* repacked_assets/shaders/*")
    print(f"  2. Copy silent sounds:")
    print(f"     cp -r {output_dir}/* repacked_assets/sounds/")
    print(f"  3. Repack:")
    print(f"     python3 repack_assets.py assets_linux/Assets.dat repacked_assets/ Assets_silent_audio.dat")
    print(f"  4. Test and measure RAM!")

if __name__ == '__main__':
    main()