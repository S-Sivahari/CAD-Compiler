# SCL Schema v3.0 - Feature-Based Parametric CAD JSON Format

## Overview

This repository contains the **Schema for CAD Language (SCL) v3.0**, a comprehensive JSON schema designed to transform Natural Language descriptions into professional-grade CAD models. The schema supports feature-based parametric modeling with manufacturing-ready specifications, enabling the Text2CAD pipeline:

```
Natural Language → Minimal JSON → CadQuery Python → Universal STEP Files
```

**Key Capabilities:**
- ✅ Feature-based parametric modeling (revolve, patterns, holes, mirrors)
- ✅ Manufacturing constraints (draft angles, threads, tolerances)
- ✅ Boolean operations (NewBody, Join, Cut, Intersect)
- ✅ Post-processing (fillets, chamfers with edge selectors)
- ✅ Material metadata and units system (mm/inch/cm/m)
- ✅ Engineering documentation with constraint tagging
- ✅ Validated against 170k+ HuggingFace Text2CAD dataset files

---

## File Structure

```
text/
├── README.md                                # This file (moved here)
├── LLM_INSTRUCTIONS.md                      # Concise LLM directive to produce SCL JSON intermediate
└── SIMPLE_PATTERNS.md                       # Minimal canonical templates for fast LLM lookup
```

---

(README content trimmed in text folder for brevity; original detailed README exists in repo history.)
