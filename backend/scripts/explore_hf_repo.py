"""
Explore GenCAD HuggingFace repository structure
"""

from huggingface_hub import list_repo_files

REPO_ID = "CADCODER/GenCAD-Code"
REPO_TYPE = "dataset"

print(f"🔍 Exploring repository: {REPO_ID}")
print("=" * 60)

try:
    all_files = list(list_repo_files(repo_id=REPO_ID, repo_type=REPO_TYPE))
    
    # Show first 50 files
    print(f"\nTotal files in repo: {len(all_files)}")
    print("\nFirst 50 files:")
    for i, file in enumerate(all_files[:50], 1):
        print(f"{i:3d}. {file}")
    
    # Analyze structure
    print("\n" + "=" * 60)
    print("Directory structure:")
    dirs = set()
    for file in all_files:
        parts = file.split('/')
        if len(parts) > 1:
            dirs.add(parts[0])
    
    for dir_name in sorted(dirs):
        count = len([f for f in all_files if f.startswith(dir_name + '/')])
        print(f"  {dir_name}/  ({count} files)")
    
    # Check for image files
    print("\n" + "=" * 60)
    image_extensions = ['.png', '.jpg', '.jpeg', '.webp']
    images = [f for f in all_files if any(f.lower().endswith(ext) for ext in image_extensions)]
    print(f"Total image files: {len(images)}")
    
    if images:
        print("\nSample image paths:")
        for img in images[:10]:
            print(f"  {img}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nThe repository might not exist or be accessible.")
    print(f"Check: https://huggingface.co/datasets/{REPO_ID}")
