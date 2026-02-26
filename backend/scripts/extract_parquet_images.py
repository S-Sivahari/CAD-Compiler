"""
Extract Images from GenCAD Parquet Files

The GenCAD-Code dataset stores images in Parquet format.
This script extracts images and organizes them to match the JSON structure.
"""

import os
import sys
import io
from pathlib import Path
from tqdm import tqdm
import pandas as pd
from PIL import Image
from huggingface_hub import hf_hub_download

# Configuration
REPO_ID = "CADCODER/GenCAD-Code"
REPO_TYPE = "dataset"
LOCAL_IMAGES_DIR = Path(__file__).parent.parent.parent / "gencad_images"
DATA_SET_DIR = Path(__file__).parent.parent.parent / "data_set"

# Parquet files in the dataset
PARQUET_FILES = [
    "data/train-00000-of-00002.parquet",
    "data/train-00001-of-00002.parquet",
    "data/test-00000-of-00001.parquet",
    "data/validation-00000-of-00001.parquet",
]


def download_and_extract_images(parquet_file, limit=None):
    """
    Download a parquet file and extract images from it.
    
    Args:
        parquet_file: Path to parquet file in the repo
        limit: Maximum number of images to extract (None for all)
    """
    print(f"\n📦 Processing: {parquet_file}")
    
    try:
        # Download parquet file
        print(f"  ⬇️  Downloading parquet file...")
        local_parquet = hf_hub_download(
            repo_id=REPO_ID,
            repo_type=REPO_TYPE,
            filename=parquet_file
        )
        
        # Read parquet file
        print(f"  📖 Reading parquet file...")
        df = pd.read_parquet(local_parquet)
        
        print(f"  📊 Found {len(df)} rows")
        print(f"  📋 Columns: {list(df.columns)}")
        
        # Check for image column
        image_col = None
        if 'image' in df.columns:
            image_col = 'image'
        elif 'img' in df.columns:
            image_col = 'img'
        elif 'images' in df.columns:
            image_col = 'images'
        
        if image_col is None:
            print(f"  ⚠️  No image column found!")
            print(f"  Available columns: {list(df.columns)}")
            return 0
        
        # Check for ID/filename column
        id_col = None
        if 'id' in df.columns:
            id_col = 'id'
        elif 'name' in df.columns:
            id_col = 'name'
        elif 'filename' in df.columns:
            id_col = 'filename'
        
        # Extract images
        extracted = 0
        skipped = 0
        failed = 0
        
        rows_to_process = df.head(limit) if limit else df
        
        print(f"  💾 Extracting images...")
        for idx, row in tqdm(rows_to_process.iterrows(), total=len(rows_to_process), desc="  Extracting"):
            try:
                # Get image data
                img_data = row[image_col]
                
                # Determine filename
                if id_col and id_col in row:
                    filename = str(row[id_col])
                    if not filename.endswith(('.png', '.jpg', '.jpeg')):
                        filename += '.png'
                else:
                    # Use index
                    filename = f"{idx:08d}.png"
                
                # Parse folder structure from filename or index
                # Assuming format: 0000/00000001.png or similar
                if '/' in filename:
                    local_path = LOCAL_IMAGES_DIR / filename
                else:
                    # Create folder structure based on index
                    folder = f"{idx // 1000:04d}"
                    local_path = LOCAL_IMAGES_DIR / folder / filename
                
                #Skip if exists
                if local_path.exists():
                    skipped += 1
                    continue
                
                # Create directory
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Handle different image storage formats
                if isinstance(img_data, bytes):
                    # Direct bytes
                    image = Image.open(io.BytesIO(img_data))
                elif isinstance(img_data, dict) and 'bytes' in img_data:
                    # Dictionary with bytes key
                    image = Image.open(io.BytesIO(img_data['bytes']))
                elif hasattr(img_data, 'read'):
                    # File-like object
                    image = Image.open(img_data)
                else:
                    # Try PIL directly
                    image = img_data
                
                # Save image
                image.save(local_path)
                extracted += 1
                
            except Exception as e:
                failed += 1
                if failed <= 5:  # Only show first 5 errors
                    print(f"\n  ❌ Failed row {idx}: {e}")
        
        print(f"  ✅ Extracted: {extracted}, Skipped: {skipped}, Failed: {failed}")
        return extracted
        
    except Exception as e:
        print(f"  ❌ Error processing {parquet_file}: {e}")
        return 0


def extract_all_images(limit_per_file=None):
    """
    Extract images from all parquet files.
    
    Args:
        limit_per_file: Maximum images to extract per file (None for all)
    """
    print(f"🖼️  GenCAD Image Extractor")
    print(f"=" * 60)
    print(f"Repository: {REPO_ID}")
    print(f"Output directory: {LOCAL_IMAGES_DIR}")
    print(f"=" * 60)
    
    # Create output directory
    LOCAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    total_extracted = 0
    
    for parquet_file in PARQUET_FILES:
        extracted = download_and_extract_images(parquet_file, limit=limit_per_file)
        total_extracted += extracted
    
    print(f"\n" + "=" * 60)
    print(f"✅ Total images extracted: {total_extracted}")
    print(f"=" * 60)
    
    return total_extracted


def inspect_parquet_structure():
    """Inspect the structure of parquet files to understand data format."""
    print(f"🔍 Inspecting Parquet Structure")
    print(f"=" * 60)
    
    parquet_file = PARQUET_FILES[0]  # Check first file
    
    try:
        print(f"Downloading: {parquet_file}")
        local_parquet = hf_hub_download(
            repo_id=REPO_ID,
            repo_type=REPO_TYPE,
            filename=parquet_file
        )
        
        df = pd.read_parquet(local_parquet)
        
        print(f"\n📊 DataFrame Info:")
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {list(df.columns)}")
        print(f"\n📋 Column Types:")
        for col in df.columns:
            print(f"  {col}: {df[col].dtype}")
        
        print(f"\n📝 First Row Sample:")
        if len(df) > 0:
            first_row = df.iloc[0]
            for col in df.columns:
                val = first_row[col]
                if isinstance(val, (bytes, bytearray)):
                    print(f"  {col}: <{len(val)} bytes>")
                elif isinstance(val, dict):
                    print(f"  {col}: {list(val.keys())}")
                else:
                    val_str = str(val)[:100]
                    print(f"  {col}: {val_str}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract images from GenCAD Parquet files")
    parser.add_argument("--extract", action="store_true", help="Extract all images")
    parser.add_argument("--limit", type=int, help="Limit images per file (for testing)")
    parser.add_argument("--inspect", action="store_true", help="Inspect parquet structure")
    
    args = parser.parse_args()
    
    if args.inspect:
        inspect_parquet_structure()
    elif args.extract:
        extract_all_images(limit_per_file=args.limit)
    else:
        print("Usage:")
        print("  --inspect     : Check parquet file structure")
        print("  --extract     : Extract all images")
        print("  --limit N     : Extract only N images per file (for testing)")
        print("\nExample:")
        print("  python extract_parquet_images.py --inspect")
        print("  python extract_parquet_images.py --extract --limit 10")
