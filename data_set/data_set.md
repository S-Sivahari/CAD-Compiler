# SynthoCAD Dataset

## Overview

This dataset contains parametric CAD model examples used for training and validation of the SynthoCAD Text2CAD pipeline. The dataset consists of structured JSON files representing 3D mechanical designs in the SCL (Schema for CAD Language) v3.0 format.

## Dataset Source

The examples in this repository are derived from the **Fusion 360 Gallery Dataset** and **DeepCAD** research work, which provides a large-scale collection of parametric CAD designs with construction sequences.

### Research Paper Citations

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

### Dataset Statistics

- **Total Examples**: 178,680+ parametric CAD models
- **Format**: SCL JSON v3.0 (Schema for CAD Language)
- **Organization**: Hierarchical directory structure (0000-0099)
- **Source Platform**: Autodesk Fusion 360 Gallery
- **License**: See original dataset licenses from Autodesk Research

## Data Structure

The dataset is organized into 100 top-level directories (0000-0099), each containing multiple CAD model examples:

```
data_set/
├── 0000/
│   ├── 00000007/
│   ├── 00000061/
│   └── ...
├── 0001/
├── 0002/
...
└── 0099/
```

Each subdirectory contains JSON files representing individual CAD models with:
- Part geometry definitions
- Parametric constraints
- Feature operations (extrude, revolve, holes, patterns)
- Manufacturing metadata

## Usage in SynthoCAD

These examples serve multiple purposes in the SynthoCAD pipeline:

1. **Training Data**: Used to train LLM models for natural language to SCL JSON conversion
2. **Validation**: Testing the robustness of the CadQuery code generator
3. **Templates**: Reference patterns for common mechanical designs
4. **Schema Evolution**: Validating SCL schema updates against real-world designs

## Attribution

If you use this dataset or the SynthoCAD pipeline in your research, please cite both the original Fusion 360 Gallery dataset and the relevant research papers above.

## Additional Resources

- Original Fusion 360 Gallery: https://github.com/AutodeskAILab/Fusion360GalleryDataset
- DeepCAD Project: https://github.com/ChrisWu1997/DeepCAD
- HuggingFace Dataset: https://huggingface.co/datasets/fusion360gallery

## Notes

This is a derived dataset adapted for the SCL JSON format. The original designs and construction sequences remain property of their respective creators and Autodesk Research. This work is for research and educational purposes.
