# Dataset Setup Complete - Summary & Next Steps

## ✅ What We've Done

### 1. **Updated .gitignore**
Added the following to prevent tracking large datasets:
```
data_set/              # Your 215K JSON files
data_set_images/       # Reserved for future use
gencad_images/         # HuggingFace extracted images
```

### 2. **Installed Dependencies**
```bash
✅ huggingface-hub>=0.20.0
✅ Pillow>=10.0.0
✅ pyarrow (for Parquet files)
✅ pandas (for data manipulation)
```

### 3. **Created Dataset Management Scripts**

#### `backend/scripts/extract_parquet_images.py`
- Extracts images from HuggingFace GenCAD Parquet files
- Organizes by deepcad_id (folder/filename structure)
- Handles all 4 parquet files (train, test, validation)

#### `backend/scripts/explore_hf_repo.py`
- Explores HuggingFace repository structure
- Lists available datasets

#### `backend/scripts/download_gencad_images.py`
- Shows dataset statistics
- Originally for direct image download (not needed for parquet format)

---

## 📊 Current Dataset Status

### Local JSON Files
- **Location:** `d:\Projects\CAD Compiler\SynthoCAD\data_set\`
- **Count:** 215,093 JSON files
- **Structure:** `0000/`, `0001/`, ... `0099/`

### HuggingFace GenCAD Images (Parquet)
- **Repository:** CADCODER/GenCAD-Code
- **Format:** 4 Parquet files containing images + metadata
- **Total rows:** ~162,848 entries
  - train-00000-of-00002.parquet: 73,645 rows
  - train-00001-of-00002.parquet: 73,644 rows
  - test-00000-of-00001.parquet: 7,355 rows
  - validation-00000-of-00001.parquet: 8,204 rows

### Extracted Images (Test)
- **Location:** `d:\Projects\CAD Compiler\SynthoCAD\gencad_images\`
- **Count:** 100 images (test extraction)
- **Format:** PNG images organized by deepcad_id

---

## 📋 Parquet Data Columns

Each row in the parquet files contains:
- **`image`**: PNG image bytes
- **`deepcad_id`**: Folder/filename (e.g., "0000/00006371")
- **`cadquery`**: CadQuery Python code
- **`token_count`**: Code token count
- **`prompt`**: Natural language description
- **`hundred_subset`**: Boolean flag

---

## 🚀 Next Steps

### Option 1: Extract ALL Images (Full Dataset)
```bash
cd backend/scripts
python extract_parquet_images.py --extract
```
**Warning:** This will extract ~162,848 images (~5-10 GB)
**Time estimate:** 30-60 minutes depending on disk speed

### Option 2: Extract Subset (Recommended for Testing)
```bash
# Extract 1000 images from each file
python extract_parquet_images.py --extract --limit 1000
```
**Result:** ~4,000 images (~200-300 MB)
**Time estimate:** 2-5 minutes

### Option 3: Use Parquet Directly (No Extraction)
You can read images directly from parquet files in your RAG pipeline without extracting:
```python
import pandas as pd
from PIL import Image
import io

df = pd.read_parquet("path/to/train.parquet")
img_bytes = df.iloc[0]['image']['bytes']
image = Image.open(io.BytesIO(img_bytes))
```

---

## 🔄 RAG Training Pipeline (Next Phase)

### Phase 1: Align JSON Files with Images

Your local JSONs (215K) vs HuggingFace images (162K):
- **Strategy 1:** Use only the 162K that have images
- **Strategy 2:** Use your 215K JSONs and generate missing images
- **Strategy 3:** Merge both datasets

### Phase 2: Generate Descriptions

Since GenCAD already has prompts, you have two options:

**Option A: Use GenCAD Prompts**
```python
# Read from parquet
df = pd.read_parquet("train.parquet")
for _, row in df.iterrows():
    deepcad_id = row['deepcad_id']
    prompt = row['prompt']
    cadquery_code = row['cadquery']
    # Use these directly for RAG
```

**Option B: Generate New Descriptions (Vision Model)**
```bash
cd backend/scripts
python description_generator.py
```

### Phase 3: Ingest into ChromaDB

Once you have aligned JSON + descriptions:
```bash
cd backend
python -m rag.ingest
```

### Phase 4: Integrate RAG into Pipeline

Modify `backend/core/main.py` to use RAG instead of keyword matching.

---

## 📁 Current Directory Structure

```
SynthoCAD/
├── data_set/                    # 215K local JSON files (gitignored)
│   ├── 0000/
│   ├── 0001/
│   └── ...
├── gencad_images/               # Extracted HuggingFace images (gitignored)
│   ├── 0000/
│   │   ├── 00006371.png
│   │   └── ...
│   └── ...
├── backend/
│   ├── scripts/
│   │   ├── extract_parquet_images.py    # ✅ Extract from parquet
│   │   ├── explore_hf_repo.py           # ✅ Explore repo
│   │   ├── download_gencad_images.py    # ✅ Stats
│   │   └── description_generator.py     # Existing (for vision LLM)
│   ├── rag/
│   │   ├── db.py                        # ChromaDB client
│   │   ├── ingest.py                    # Data ingestion
│   │   └── query.py                     # Query interface
│   └── ...
└── ...
```

---

## 💡 Recommendations

### For Testing/Development:
1. ✅ Extract subset of images (1000-5000)
2. ✅ Use GenCAD prompts directly (already good quality)
3. ✅ Ingest into ChromaDB
4. ✅ Test RAG queries
5. ✅ Integrate into main pipeline

### For Production:
1. Decide on dataset strategy (215K local vs 162K GenCAD)
2. Extract all images or use parquet directly
3. Generate or use existing descriptions
4. Full ChromaDB ingestion
5. Performance optimization

---

## 🎯 Quick Commands Reference

```bash
# Check dataset stats
cd backend/scripts
python download_gencad_images.py --stats

# Extract test batch (100 images)
python extract_parquet_images.py --extract --limit 100

# Extract larger batch (1000 images)
python extract_parquet_images.py --extract --limit 1000

# Extract ALL images (full dataset)
python extract_parquet_images.py --extract

# Inspect parquet structure
python extract_parquet_images.py --inspect

# Check HuggingFace repo
python explore_hf_repo.py
```

---

## ⚠️ Important Notes

1. **Disk Space:**
   - Full extraction: ~5-10 GB
   - Parquet files cache: ~750 MB
   - ChromaDB after ingestion: ~2-3 GB

2. **Data Alignment:**
   - Local JSONs: 215,093 files
   - GenCAD entries: 162,848 files
   - Need alignment strategy before RAG training

3. **Git:**
   - All dataset folders now in .gitignore ✅
   - Don't commit large files

---

## 🤔 Decision Point: Which Dataset to Use?

### Your Local Dataset (215K JSONs)
**Pros:**
- Larger dataset
- Already organized
- Your own data

**Cons:**
- No images yet (need to generate)
- No prompts (need to generate)

### GenCAD Dataset (162K)
**Pros:**
- Has images ✅
- Has prompts ✅
- Has CadQuery code ✅
- Ready to use

**Cons:**
- Slightly smaller
- Different format/structure

### Recommendation:
Use **GenCAD as primary**, supplement with your local dataset where unique.
