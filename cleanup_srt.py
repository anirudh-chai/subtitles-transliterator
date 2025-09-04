#!/usr/bin/env python3
"""
SRT Cleanup Script
Removes duplicate subtitle numbers and fixes formatting issues in processed SRT files.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple

def clean_srt_content(content: str) -> str:
    """
    Clean SRT content by removing duplicate numbers and fixing formatting
    """
    lines = content.strip().split('\n')
    cleaned_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines at the beginning
        if not line and not cleaned_lines:
            i += 1
            continue
            
        # If this line is a number
        if line.isdigit():
            # Check if the next line is also a number (duplicate)
            if i + 1 < len(lines) and lines[i + 1].strip().isdigit():
                # Skip the duplicate number
                i += 1
                continue
            
            # Check if this is a subtitle number (followed by timestamp)
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # If next line is a timestamp, this is a valid subtitle number
                if re.match(r'\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}', next_line):
                    cleaned_lines.append(line)
                    i += 1
                    continue
            
            # If we reach here, it might be a standalone number, skip it
            i += 1
            continue
        
        # Add non-number lines as they are
        cleaned_lines.append(line)
        i += 1
    
    return '\n'.join(cleaned_lines)

def fix_srt_numbering(content: str) -> str:
    """
    Fix SRT numbering to ensure sequential numbering starting from 1
    No spacing between subtitle entries - line by line format
    """
    lines = content.strip().split('\n')
    fixed_lines = []
    subtitle_number = 1
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines at the beginning
        if not line and not fixed_lines:
            i += 1
            continue
        
        # If this line is a number
        if line.isdigit():
            # Check if the next line is a timestamp
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if re.match(r'\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}', next_line):
                    # This is a subtitle number, replace with correct sequential number
                    fixed_lines.append(str(subtitle_number))
                    subtitle_number += 1
                    i += 1
                    continue
            
            # If not followed by timestamp, skip this line
            i += 1
            continue
        
        # Add non-number lines as they are
        fixed_lines.append(line)
        i += 1
    
    # Join all lines without any empty lines between subtitle blocks
    # This creates a line-by-line format with no spacing
    return '\n'.join(fixed_lines)

def extract_timestamps_from_content(content: str) -> List[str]:
    """
    Extract all timestamps from SRT content
    """
    timestamp_pattern = r'\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}'
    timestamps = re.findall(timestamp_pattern, content)
    return timestamps

def find_source_file(processed_file_path: str) -> str:
    """
    Find the corresponding source file for a processed file
    """
    # Get the relative path from processed folder
    processed_path = Path(processed_file_path)
    series_name = processed_path.parent.name
    
    # Remove "_telugu" from filename to get original name
    original_filename = processed_path.stem.replace("_telugu", "")
    original_filename_with_ext = f"{original_filename}.srt"
    
    # Look for the source file in the series folder
    base_folder = processed_path.parents[2]  # Go up to the main folder
    source_file_path = base_folder / series_name / original_filename_with_ext
    
    return str(source_file_path)

def replace_timestamps_with_originals(processed_content: str, source_file_path: str) -> str:
    """
    Replace timestamps in processed content with original timestamps from source file
    """
    try:
        # Read source file
        with open(source_file_path, 'r', encoding='utf-8') as f:
            source_content = f.read()
        
        # Extract timestamps from source
        source_timestamps = extract_timestamps_from_content(source_content)
        
        if not source_timestamps:
            print(f"⚠️  No timestamps found in source file: {os.path.basename(source_file_path)}")
            return processed_content
        
        # Extract timestamps from processed content
        processed_timestamps = extract_timestamps_from_content(processed_content)
        
        if len(source_timestamps) != len(processed_timestamps):
            print(f"⚠️  Timestamp count mismatch: source={len(source_timestamps)}, processed={len(processed_timestamps)}")
            return processed_content
        
        # Replace timestamps in processed content
        result_content = processed_content
        for i, (source_ts, processed_ts) in enumerate(zip(source_timestamps, processed_timestamps)):
            result_content = result_content.replace(processed_ts, source_ts, 1)
        
        print(f"✓ Replaced {len(source_timestamps)} timestamps from source")
        return result_content
        
    except Exception as e:
        print(f"⚠️  Could not replace timestamps: {e}")
        return processed_content

def process_srt_file(file_path: str) -> bool:
    """
    Process a single SRT file to clean up formatting and replace timestamps
    """
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"Processing: {os.path.basename(file_path)}")
        
        # Clean the content
        cleaned_content = clean_srt_content(content)
        fixed_content = fix_srt_numbering(cleaned_content)
        
        # Try to replace timestamps with originals
        source_file_path = find_source_file(file_path)
        if os.path.exists(source_file_path):
            print(f"  Found source file: {os.path.basename(source_file_path)}")
            final_content = replace_timestamps_with_originals(fixed_content, source_file_path)
        else:
            print(f"  Source file not found: {os.path.basename(source_file_path)}")
            final_content = fixed_content
        
        # Write back to the same file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        print(f"✓ Fixed: {os.path.basename(file_path)}")
        return True
        
    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}")
        return False

def find_srt_files(base_folder: str) -> List[str]:
    """
    Find all SRT files in the processed folder
    """
    srt_files = []
    processed_folder = os.path.join(base_folder, "processed")
    
    if not os.path.exists(processed_folder):
        print(f"✗ Processed folder not found: {processed_folder}")
        return srt_files
    
    # Walk through all subdirectories in processed folder
    for root, dirs, files in os.walk(processed_folder):
        for file in files:
            if file.endswith('.srt'):
                srt_files.append(os.path.join(root, file))
    
    return srt_files

def main():
    """
    Main function to clean up all processed SRT files
    """
    print("SRT Cleanup Script")
    print("=" * 50)
    
    # Get current directory as base folder
    base_folder = os.getcwd()
    print(f"Base folder: {base_folder}")
    
    # Find all SRT files in processed folder
    srt_files = find_srt_files(base_folder)
    
    if not srt_files:
        print("✗ No SRT files found in processed folder")
        return
    
    print(f"\nFound {len(srt_files)} SRT files to process:")
    for file_path in srt_files:
        print(f"  {os.path.relpath(file_path, base_folder)}")
    
    # Process each file
    successful = 0
    failed = 0
    
    for file_path in srt_files:
        if process_srt_file(file_path):
            successful += 1
        else:
            failed += 1
    
    print(f"\n{'='*50}")
    print("CLEANUP COMPLETE")
    print(f"{'='*50}")
    print(f"Successfully processed: {successful} files")
    if failed > 0:
        print(f"Failed: {failed} files")
    else:
        print("All files processed successfully! ✓")

if __name__ == "__main__":
    main()
