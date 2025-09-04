import requests
import os
import time
import random
from pathlib import Path
from typing import List, Dict, Tuple

# API Configuration
api_key = "AIzaSyAEyK4Nll7SaXk-NRSRCf-af1LeL89UicM"
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
headers = {
    "x-goog-api-key": api_key,
    "Content-Type": "application/json"
}

# Prompt template
prompt_template = """
Please transliterate the following SRT subtitle content from Tinglish (Telugu written in English script) to proper Telugu script while maintaining the exact same timing and structure.

SRT content to transliterate:
{file_data}

CRITICAL REQUIREMENTS:
1. Keep the exact same timestamps (00:00:00,000 --> 00:00:00,000 format)
2. Keep the same SRT numbering starting from 1 (1, 2, 3, etc.) - DO NOT duplicate any numbers
3. Transliterate ONLY the subtitle text content from Tinglish to proper Telugu script
4. Maintain the exact same line breaks and structure
5. Do NOT add any headers, titles, or extra text
6. Do NOT change any formatting, punctuation, or timing information
7. Start with subtitle number 1 and continue sequentially
8. DO NOT add extra numbers or duplicate subtitle numbers
9. Each subtitle block should have exactly ONE number, ONE timestamp, and the text

Output format should be exactly:
1
00:00:00,000 --> 00:00:00,000
[Transliterated Telugu text]

2
00:00:00,000 --> 00:00:00,000
[Transliterated Telugu text]

3
00:00:00,000 --> 00:00:00,000
[Transliterated Telugu text]

IMPORTANT: Do NOT add extra "1" or duplicate numbers. Each subtitle should have only its own number (1, then 2, then 3, etc.) with no duplicates.

Provide ONLY the transliterated SRT content without any additional text, comments, or headers.
"""

def read_srt_file(file_path: str) -> str:
    """Read SRT file content with comprehensive error handling"""
    try:
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    if content.strip():  # Check if file has content
                        print(f"Successfully read {file_path} with {encoding} encoding")
                        return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"Error reading {file_path} with {encoding}: {e}")
                continue
        
        print(f"Warning: Could not read {file_path} with any encoding")
        return ""
        
    except Exception as e:
        print(f"Critical error reading {file_path}: {e}")
        return ""

def save_transliterated_srt(content: str, output_path: str) -> bool:
    """Save transliterated SRT content to file with error handling"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write with UTF-8 encoding
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ Saved: {output_path}")
        return True
        
    except PermissionError:
        print(f"✗ Permission denied: {output_path}")
        return False
    except Exception as e:
        print(f"✗ Error saving {output_path}: {e}")
        return False

def get_all_srt_files(base_folder: str) -> Dict[str, List[Tuple[str, str]]]:
    """
    Get all SRT files organized by series
    Returns: Dict with series_name as key and list of (file_name, file_path) as value
    """
    srt_files_by_series = {}
    base_path = Path(base_folder)
    
    try:
        if not base_path.exists():
            print(f"✗ Base folder {base_folder} does not exist!")
            return srt_files_by_series
        
        if not base_path.is_dir():
            print(f"✗ {base_folder} is not a directory!")
            return srt_files_by_series
        
        # Iterate through series folders
        for series_folder in base_path.iterdir():
            if series_folder.is_dir() and series_folder.name != "processed":  # Skip processed folder
                series_name = series_folder.name
                srt_files_by_series[series_name] = []
                
                print(f"Scanning series: {series_name}")
                
                # Find all SRT files in the series folder
                srt_files = list(series_folder.glob("*.srt"))
                for srt_file in srt_files:
                    # Use filename without extension as the identifier
                    file_name = srt_file.stem
                    srt_files_by_series[series_name].append((file_name, str(srt_file)))
                    print(f"  Found: {srt_file.name}")
        
        return srt_files_by_series
        
    except Exception as e:
        print(f"✗ Error scanning folder structure: {e}")
        return {}

def process_series(series_name: str, srt_files: List[Tuple[str, str]], base_output_folder: str) -> bool:
    """Process all SRT files for a single series - one file at a time"""
    print(f"\n{'='*60}")
    print(f"Processing Series: {series_name}")
    print(f"Files to process: {len(srt_files)}")
    print(f"{'='*60}")
    
    if not srt_files:
        print(f"No SRT files found for series: {series_name}")
        return False
    
    success_count = 0
    total_files = len(srt_files)
    
    # Process each file individually
    for i, (file_name, file_path) in enumerate(srt_files, 1):
        print(f"\n[{i}/{total_files}] Processing: {os.path.basename(file_path)}")
        
        content = read_srt_file(file_path)
        if not content.strip():
            print(f"⚠️  Skipping empty file: {file_path}")
            continue
        
        # Process this single file
        if process_single_file(series_name, file_name, file_path, content, base_output_folder):
            success_count += 1
            print(f"✓ Successfully processed: {os.path.basename(file_path)}")
        else:
            print(f"✗ Failed to process: {os.path.basename(file_path)}")
        
        # Small delay between files
        if i < total_files:
            time.sleep(1)
    
    print(f"\nSuccessfully processed {success_count}/{total_files} files for series: {series_name}")
    return success_count > 0

def process_single_file(series_name: str, file_name: str, file_path: str, content: str, base_output_folder: str) -> bool:
    """Process a single SRT file"""
    try:
        # Prepare API request for single file
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt_template.format(file_data=content)}
                    ]
                }
            ]
        }
        
        # Make API call with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"Making API request (attempt {attempt + 1}/{max_retries})...")
                start_time = time.time()
                
                response = requests.post(url, headers=headers, json=payload, timeout=400)
                
                end_time = time.time()
                print(f"API request took {end_time - start_time:.2f} seconds")
                
                if response.ok:
                    result = response.json()
                    
                    # Validate response structure
                    if 'candidates' in result and len(result['candidates']) > 0:
                        if 'content' in result['candidates'][0] and 'parts' in result['candidates'][0]['content']:
                            transliterated_content = result['candidates'][0]['content']['parts'][0]['text']
                            
                            # Save the single file
                            success = save_single_transliterated_file(
                                transliterated_content, file_name, file_path, series_name, base_output_folder
                            )
                            
                            if success:
                                return True
                            else:
                                print(f"✗ Failed to save file: {file_name}")
                                return False
                        else:
                            print(f"✗ Invalid response structure - missing content/parts")
                    else:
                        print(f"✗ Invalid response structure - missing candidates")
                    
                else:
                    print(f"✗ API Error {response.status_code}: {response.text}")
                    if response.status_code == 429:  # Rate limit
                        wait_time = random.uniform(10, 20)
                        print(f"Rate limited. Waiting {wait_time:.2f} seconds...")
                        time.sleep(wait_time)
                        continue
                    elif response.status_code >= 500:  # Server error
                        wait_time = random.uniform(5, 10)
                        print(f"Server error. Waiting {wait_time:.2f} seconds before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        break  # Don't retry for client errors
                        
            except requests.exceptions.Timeout:
                print(f"✗ Request timeout (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    wait_time = random.uniform(5, 10)
                    print(f"Waiting {wait_time:.2f} seconds before retry...")
                    time.sleep(wait_time)
            except requests.exceptions.RequestException as e:
                print(f"✗ Request error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    wait_time = random.uniform(5, 10)
                    print(f"Waiting {wait_time:.2f} seconds before retry...")
                    time.sleep(wait_time)
            except Exception as e:
                print(f"✗ Unexpected error (attempt {attempt + 1}): {e}")
                break
        
        print(f"✗ Failed to process file: {file_name} after {max_retries} attempts")
        return False
        
    except Exception as e:
        print(f"✗ Critical error processing file {file_name}: {e}")
        return False

def save_single_transliterated_file(transliterated_content: str, file_name: str, original_file_path: str, series_name: str, base_output_folder: str) -> bool:
    """Save a single transliterated file with proper formatting"""
    try:
        # Clean the content - remove any extra text that might be added by AI
        content_lines = transliterated_content.strip().split('\n')
        cleaned_content = []
        
        # Find the first subtitle number to ensure proper formatting
        subtitle_found = False
        for line in content_lines:
            line = line.strip()
            if line and line.isdigit():
                # This is a subtitle number
                if not subtitle_found and line != "1":
                    # Add missing subtitle number 1 if needed
                    cleaned_content.append("1")
                    subtitle_found = True
                cleaned_content.append(line)
            elif line and ":" in line and "-->" in line:
                # This is a timestamp
                cleaned_content.append(line)
            elif line and not line.startswith("===") and not line.startswith(series_name):
                # This is subtitle text (not a header)
                cleaned_content.append(line)
        
        # Join the cleaned content
        final_content = '\n'.join(cleaned_content)
        
        # Create output path - append "telugu" to the filename
        original_filename = os.path.basename(original_file_path)
        name_without_ext = os.path.splitext(original_filename)[0]
        telugu_filename = f"{name_without_ext}_telugu.srt"
        output_path = os.path.join(base_output_folder, "processed", series_name, telugu_filename)
        
        # Save the file
        return save_transliterated_srt(final_content, output_path)
        
    except Exception as e:
        print(f"✗ Error saving single file {file_name}: {e}")
        return False

def split_and_save_transliterated_content(transliterated_content: str, file_info: List[Tuple[str, str]], series_name: str, base_output_folder: str) -> bool:
    """Split the combined transliterated content back into individual files"""
    
    try:
        # Split by the file separators
        sections = transliterated_content.split("===")
        
        success_count = 0
        total_files = len(file_info)
        
        for i, (_, original_file_path) in enumerate(file_info):
            try:
                if i + 1 < len(sections):
                    # Extract content for this file (skip the header line)
                    content_lines = sections[i + 1].strip().split('\n')
                    if len(content_lines) > 1:
                        # Remove the first line (which should be the header)
                        file_content = '\n'.join(content_lines[1:]).strip()
                    else:
                        file_content = sections[i + 1].strip()
                    
                    # Create output path in processed/series_name/ folder
                    # Append "telugu" to the filename
                    original_filename = os.path.basename(original_file_path)
                    name_without_ext = os.path.splitext(original_filename)[0]
                    telugu_filename = f"{name_without_ext}_telugu.srt"
                    output_path = os.path.join(base_output_folder, "processed", series_name, telugu_filename)
                    
                    # Save the file
                    if save_transliterated_srt(file_content, output_path):
                        success_count += 1
                else:
                    print(f"⚠️  No content found for {original_file_path}")
                    
            except Exception as e:
                print(f"✗ Error processing file {original_file_path}: {e}")
        
        print(f"Successfully saved {success_count}/{total_files} files for series: {series_name}")
        return success_count > 0
        
    except Exception as e:
        print(f"✗ Error splitting content for series {series_name}: {e}")
        return False

def main():
    """Main function with comprehensive error handling"""
    try:
        print("SRT Transliteration Batch Processor")
        print("=" * 50)
        
        # Get user input with validation
        while True:
            base_folder = input("Enter the path to your series folder (or press Enter for current directory): ").strip()
            if not base_folder:
                base_folder = os.getcwd()
            if base_folder and os.path.exists(base_folder):
                break
            print("✗ Invalid path. Please enter a valid folder path.")
        
        # Set output folder to be a 'processed' subfolder in the base folder
        base_output_folder = base_folder
        processed_folder = os.path.join(base_folder, "processed")
        try:
            os.makedirs(processed_folder, exist_ok=True)
            print(f"✓ Output folder set to: {processed_folder}")
        except Exception as e:
            print(f"✗ Cannot create processed folder: {e}")
            return
        
        # Get all SRT files organized by series
        print(f"\nScanning folder: {base_folder}")
        srt_files_by_series = get_all_srt_files(base_folder)
        
        if not srt_files_by_series:
            print("✗ No SRT files found!")
            return
        
        total_series = len(srt_files_by_series)
        total_files = sum(len(files) for files in srt_files_by_series.values())
        
        print(f"\nFound {total_files} SRT files across {total_series} series:")
        for series_name, files in srt_files_by_series.items():
            print(f"  {series_name}: {len(files)} files")
        
        # Process each series
        successful_series = 0
        failed_series = []
        
        for i, (series_name, srt_files) in enumerate(srt_files_by_series.items(), 1):
            print(f"\n[{i}/{total_series}] Processing series: {series_name}")
            
            success = process_series(series_name, srt_files, base_output_folder)
            
            if success:
                successful_series += 1
            else:
                failed_series.append(series_name)
            
            # Cooldown period (except for the last series)
            if i < total_series:
                cooldown_time = random.uniform(2, 7)
                print(f"⏳ Cooldown: {cooldown_time:.2f} seconds...")
                time.sleep(cooldown_time)
        
        # Final summary
        print(f"\n{'='*60}")
        print("PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Successfully processed: {successful_series}/{total_series} series")
        
        if failed_series:
            print(f"Failed series: {', '.join(failed_series)}")
        else:
            print("All series processed successfully! ��")
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Process interrupted by user")
    except Exception as e:
        print(f"\n✗ Critical error in main: {e}")

# Run the main function
if __name__ == "__main__":
    main()