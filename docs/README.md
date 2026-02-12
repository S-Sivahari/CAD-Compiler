# SCL Schema v3.0 - Feature-Based Parametric CAD JSON Format

## Overview

This repository contains the **Schema for CAD Language (SCL) v3.0**, a comprehensive JSON schema designed to transform Natural Language descriptions into professional-grade CAD models. The schema supports feature-based parametric modeling with manufacturing-ready specifications, enabling the Text2CAD pipeline:

```
Natural Language → Minimal JSON → CadQuery Python → Universal STEP Files
```

**Key Capabilities:**
- Feature-based parametric modeling (revolve, patterns, holes, mirrors)
- Manufacturing constraints (draft angles, threads, tolerances)
- Boolean operations (NewBody, Join, Cut, Intersect)
- Post-processing (fillets, chamfers with edge selectors)
- Material metadata and units system (mm/inch/cm/m)
- Engineering documentation with constraint tagging
- Validated against 178k+ Fusion 360 Gallery dataset files

---

## File Structure

```
text/
├── README.md                                # This file (moved here)
├── LLM_INSTRUCTIONS.md                      # Concise LLM directive to produce SCL JSON intermediate
└── SIMPLE_PATTERNS.md                       # Minimal canonical templates for fast LLM lookup
```

---

## Dataset Attribution

This project uses the **Fusion 360 Gallery Dataset** for training and validation. Please cite the following research papers if you use this work:

**Primary Source:**
```
Willis, K. D., Pu, Y., Luo, J., Chu, H., Du, T., Lambourne, J. G., ... & Shayani, H. (2021).
Fusion 360 Gallery: A Dataset and Environment for Programmatic CAD Construction from Human Design Sequences.
ACM Transactions on Graphics (TOG), 40(4), 1-24.
DOI: 10.1145/3450626.3459818
```

**Related Work:**
```
Wu, R., Xiao, C., & Zheng, C. (2021).
DeepCAD: A Deep Generative Network for Computer-Aided Design Models.
IEEE International Conference on Computer Vision (ICCV), 2021.
DOI: 10.1109/ICCV48922.2021.00071
```

**Dataset Information:**
- Total Examples: 178,680+ parametric CAD models
- Format: SCL JSON v3.0
- Source: Autodesk Fusion 360 Gallery (https://github.com/AutodeskAILab/Fusion360GalleryDataset)
- HuggingFace: https://huggingface.co/datasets/fusion360gallery

For detailed dataset documentation, see [data_set/data_Set.md](../data_set/data_Set.md).

---

(README content trimmed in text folder for brevity; original detailed README exists in repo history.)
