#!/usr/bin/env python3
"""
Universal Audio Optimizer
Handles WAV and OGG files, reduces size by lowering sample rate and converting to mono
"""

import os
import sys
from pathlib import Path
import subprocess

def check_ffmpeg():
    """Check if ffmpeg is available"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def optimize_audio_ffmpeg(input_file, output_file, sample_rate=22050, mono=True, ogg_quality=5):
    """
    Optimize audio using ffmpeg, preserving original format
    
    Args:
        input_file: Input audio file (WAV or OGG)
        output_file: Output audio file (same format as input)
        sample_rate: Target sample rate in Hz (default: 22050)
        mono: Convert to mono if True (default: True)
        ogg_quality: Quality for OGG encoding 0-10 (default: 5)
    """
    
    input_ext = input_file.suffix.lower()
    
    # Build ffmpeg command - note the order matters!
    cmd = ['ffmpeg', '-y', '-i', str(input_file)]
    
    # Sample rate
    cmd.extend(['-ar', str(sample_rate)])
    
    # Format-specific settings
    if input_ext == '.wav':
        # WAV: 16-bit PCM - can do mono
        if mono:
            cmd.extend(['-ac', '1'])
        cmd.extend(['-acodec', 'pcm_s16le'])
    elif input_ext == '.ogg':
        # OGG: The native vorbis encoder only supports stereo (2 channels)
        # So we keep it as stereo even if mono was requested
        cmd.extend(['-ac', '2'])
        
        # Try libvorbis first (better quality), fall back to native vorbis
        # Check if libvorbis is available
        check_libvorbis = subprocess.run(
            ['ffmpeg', '-encoders'],
            capture_output=True,
            text=True
        )
        
        if 'libvorbis' in check_libvorbis.stdout:
            # libvorbis supports mono/stereo
            if mono:
                cmd[-1] = '1'  # Change -ac 2 to -ac 1
            cmd.extend(['-acodec', 'libvorbis', '-q:a', str(ogg_quality)])
        else:
            # Native vorbis encoder - must be stereo
            cmd.extend(['-acodec', 'vorbis', '-strict', '-2', '-q:a', str(ogg_quality)])
    else:
        # Unknown format
        return None
    
    cmd.append(str(output_file))
    
    # Run ffmpeg
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")
    
    return output_file

def optimize_audio_batch(input_dir, output_dir, sample_rate=22050, mono=True, ogg_quality=5):
    """Optimize all audio files in directory"""
    
    if not check_ffmpeg():
        print("ERROR: ffmpeg not found!")
        print("Please install ffmpeg:")
        print("  Ubuntu/Debian: sudo apt install ffmpeg")
        print("  macOS: brew install ffmpeg")
        sys.exit(1)
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        print(f"Error: Input directory '{input_dir}' not found")
        return
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*80}")
    print(f"AUDIO OPTIMIZATION")
    print(f"{'='*80}")
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"Sample rate: {sample_rate} Hz")
    print(f"Channels: {'Mono' if mono else 'Stereo'}")
    print(f"  Note: OGG files will remain stereo (native vorbis encoder limitation)")
    print(f"OGG quality: {ogg_quality}/10")
    print(f"{'='*80}\n")
    
    # Find all audio files
    wav_files = list(input_path.glob('*.wav'))
    ogg_files = list(input_path.glob('*.ogg'))
    audio_files = wav_files + ogg_files
    
    if not audio_files:
        print("No audio files found!")
        return
    
    print(f"Found {len(wav_files)} WAV files")
    print(f"Found {len(ogg_files)} OGG files")
    print(f"Total: {len(audio_files)} files\n")
    
    # Process each file
    total_before = 0
    total_after = 0
    processed = 0
    skipped = 0
    errors = 0
    
    for i, audio_file in enumerate(audio_files, 1):
        try:
            # Keep original format
            rel_path = audio_file.relative_to(input_path)
            out_file = output_path / rel_path
            out_file.parent.mkdir(parents=True, exist_ok=True)
            
            orig_size = audio_file.stat().st_size
            
            # Optimize with ffmpeg
            result = optimize_audio_ffmpeg(audio_file, out_file, sample_rate, mono, ogg_quality)
            
            if result is None:
                errors += 1
                print(f"✗ Unknown format: {audio_file.name}")
                continue
            
            new_size = result.stat().st_size
            
            total_before += orig_size
            total_after += new_size
            processed += 1
            
            reduction = (1 - new_size/orig_size) * 100 if orig_size > 0 else 0
            
            if processed <= 10 or processed % 50 == 0:
                print(f"✓ {audio_file.name}: {orig_size:,} → {new_size:,} bytes (-{reduction:.0f}%)")
            
        except Exception as e:
            errors += 1
            print(f"✗ Error processing {audio_file.name}: {e}")
    
    # Final report
    print(f"\n{'='*80}")
    print(f"OPTIMIZATION COMPLETE")
    print(f"{'='*80}")
    
    print(f"\nProcessed: {processed} files")
    if skipped > 0:
        print(f"Skipped: {skipped} files")
    print(f"Errors: {errors} files")
    
    if total_before > 0:
        print(f"\nOriginal size: {total_before/1024/1024:.2f} MB")
        print(f"Optimized size: {total_after/1024/1024:.2f} MB")
        saved_mb = (total_before - total_after) / 1024 / 1024
        saved_pct = (1 - total_after/total_before) * 100
        print(f"Space saved: {saved_mb:.2f} MB ({saved_pct:.1f}%)")
    
    print(f"\nOptimized audio saved to: {output_path}")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Optimize audio files (WAV and OGG) for low memory usage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Optimize to 22kHz mono
  python optimize_audio.py extracted_assets/sounds/ optimized_sounds/
  
  # Optimize to 16kHz mono with lower OGG quality
  python optimize_audio.py extracted_assets/sounds/ optimized_sounds/ --sample-rate 16000 --ogg-quality 3
  
  # Keep stereo
  python optimize_audio.py extracted_assets/sounds/ optimized_sounds/ --stereo
        """
    )
    
    parser.add_argument('input_dir', help='Input directory with audio files')
    parser.add_argument('output_dir', help='Output directory for optimized audio')
    parser.add_argument('--sample-rate', type=int, default=22050,
                       help='Target sample rate in Hz (default: 22050)')
    parser.add_argument('--stereo', action='store_true',
                       help='Keep stereo (default is mono). Note: OGG files will remain stereo regardless due to encoder limitations')
    parser.add_argument('--ogg-quality', type=int, default=5, choices=range(0, 11),
                       help='OGG quality 0-10, lower=smaller (default: 5)')
    
    args = parser.parse_args()
    
    optimize_audio_batch(
        args.input_dir,
        args.output_dir,
        sample_rate=args.sample_rate,
        mono=not args.stereo,
        ogg_quality=args.ogg_quality
    )