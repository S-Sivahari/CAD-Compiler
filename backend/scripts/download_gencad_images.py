"""
Download GenCAD Images from HuggingFace

Downloads images from CADCODER/GenCAD-Code dataset and organizes them
to match the local data_set JSON structure.

Dataset: https://huggingface.co/datasets/CADCODER/GenCAD-Code
"""

import os
import sys
from pathlib import Path
from tqdm import tqdm
from huggingface_hub import hf_hub_download, list_repo_files
import shutil

# Configuration
REPO_ID = "CADCODER/GenCAD-Code"
REPO_TYPE = "dataset"
LOCAL_IMAGES_DIR = Path(__file__).parent.parent.parent / "gencad_images"
DATA_SET_DIR = Path(__file__).parent.parent.parent / "data_set"

def download_dataset_images():
    """Download all images from the GenCAD dataset."""
    
    print(f"📦 GenCAD Image Downloader")
    print(f"=" * 60)
    print(f"Repository: {REPO_ID}")
    print(f"Local images directory: {LOCAL_IMAGES_DIR}")
    print(f"=" * 60)
    
    # Create output directory
    LOCAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # List all files in the repository
        print("\n🔍 Scanning repository for image files...")
        all_files = list_repo_files(repo_id=REPO_ID, repo_type=REPO_TYPE)
        
        # Filter for image files in data/ directory
        image_files = [
            f for f in all_files 
            if f.startswith('data/') and (f.endswith('.png') or f.endswith('.jpg') or f.endswith('.jpeg'))
        ]
        
        print(f"✅ Found {len(image_files)} image files")
        
        if not image_files:
            print("⚠️  No image files found in data/ directory")
            return
        
        # Download images with progress bar
        print(f"\n📥 Downloading images...")
        downloaded = 0
        skipped = 0
        failed = 0
        
        for file_path in tqdm(image_files, desc="Downloading", unit="file"):
            try:
                # Extract the relative path (e.g., data/0000/00000001.png -> 0000/00000001.png)
                relative_path = file_path.replace('data/', '')
                local_path = LOCAL_IMAGES_DIR / relative_path
                
                # Skip if already exists
                if local_path.exists():
                    skipped += 1
                    continue
                
                # Create parent directory
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Download file
                downloaded_path = hf_hub_download(
                    repo_id=REPO_ID,
                    repo_type=REPO_TYPE,
                    filename=file_path,
                    cache_dir=None,
                    local_dir=None
                )
                
                # Copy to our directory structure
                shutil.copy2(downloaded_path, local_path)
                downloaded += 1
                
            except Exception as e:
                failed += 1
                print(f"\n❌ Failed to download {file_path}: {e}")
        
        # Summary
        print(f"\n" + "=" * 60)
        print(f"✅ Download complete!")
        print(f"   Downloaded: {downloaded}")
        print(f"   Skipped (already exist): {skipped}")
        print(f"   Failed: {failed}")
        print(f"=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error accessing repository: {e}")
        print(f"\nTroubleshooting:")
        print(f"1. Check if the repository exists: https://huggingface.co/datasets/{REPO_ID}")
        print(f"2. Ensure you have internet connection")
        print(f"3. Try: huggingface-cli login (if dataset is private)")
        sys.exit(1)


def verify_alignment():
    """Check if JSON files and images are aligned."""
    print("\n🔍 Verifying JSON-Image alignment...")
    
    if not DATA_SET_DIR.exists():
        print(f"⚠️  data_set directory not found: {DATA_SET_DIR}")
        return
    
    if not LOCAL_IMAGES_DIR.exists():
        print(f"⚠️  images directory not found: {LOCAL_IMAGES_DIR}")
        return
    
    # Sample check: first 10 JSON files
    json_files = list(DATA_SET_DIR.glob("**/*.json"))[:10]
    matched = 0
    
    for json_file in json_files:
        # Get relative path
        rel_path = json_file.relative_to(DATA_SET_DIR)
        # Change extension to .png
        img_path = LOCAL_IMAGES_DIR / rel_path.with_suffix('.png')
        
        if img_path.exists():
            matched += 1
        else:
            # Try .jpg
            img_path = LOCAL_IMAGES_DIR / rel_path.with_suffix('.jpg')
            if img_path.exists():
                matched += 1
    
    print(f"✅ Sample check: {matched}/{len(json_files)} files have matching images")
    
    if matched < len(json_files):
        print(f"⚠️  Some JSON files may not have corresponding images")


def show_stats():
    """Show dataset statistics."""
    print("\n📊 Dataset Statistics")
    print("=" * 60)
    
    # Count JSONs
    if DATA_SET_DIR.exists():
        json_files = list(DATA_SET_DIR.glob("**/*.json"))
        print(f"JSON files: {len(json_files):,}")
    else:
        print(f"JSON directory not found: {DATA_SET_DIR}")
    
    # Count images
    if LOCAL_IMAGES_DIR.exists():
        image_files = list(LOCAL_IMAGES_DIR.glob("**/*.png")) + list(LOCAL_IMAGES_DIR.glob("**/*.jpg"))
        print(f"Image files: {len(image_files):,}")
        
        # Check size
        total_size = sum(f.stat().st_size for f in image_files if f.is_file())
        size_gb = total_size / (1024**3)
        print(f"Total size: {size_gb:.2f} GB")
    else:
        print(f"Images directory not found: {LOCAL_IMAGES_DIR}")
    
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download GenCAD images from HuggingFace")
    parser.add_argument("--download", action="store_true", help="Download images")
    parser.add_argument("--verify", action="store_true", help="Verify JSON-image alignment")
    parser.add_argument("--stats", action="store_true", help="Show dataset statistics")
    
    args = parser.parse_args()
    
    if args.download:
        download_dataset_images()
    
    if args.verify:
        verify_alignment()
    
    if args.stats or not any([args.download, args.verify]):
        show_stats()
