# LLM Instructions — SCL Schema Adoption

Purpose: a concise directive any LLM should follow when converting Natural Language prompts into SCL JSON (intermediate) before CadQuery codegen.

1. Mandatory workflow (enforce strictly)
- Step 1: Parse NL intent and identify top-level features (base body, holes, patterns, mates).
- Step 2: Produce a complete, validated SCL JSON (schema v3.0) as the single canonical intermediate artifact.
- Step 3: Attach `_comment`, `_engineering_note`, and any `_constraint` or `_formula` fields to document intent.
- Step 4: Stop — return only the SCL JSON. Do not generate CadQuery code or STEP files unless explicitly requested.

2. Schema discipline
- Always use `NewBodyFeatureOperation` for the first primary feature.
- Use `JoinFeatureOperation` / `CutFeatureOperation` / `IntersectFeatureOperation` for additional features as appropriate.
- Prefer `revolve` for rotational geometry and `extrusion` for prismatic bodies.
- Use `hole_feature` for any fastener hole; do not sketch a hole as generic extrusion when a standardized hole exists.

3. Face anchoring and coordinate inference
- Infer face selectors from the feature `coordinate_system` Translation Vector relative to the base bounding box; default to `>Z` for top attachments when translation_z equals base height.
- Populate `coordinate_system` with Euler Angles when orientation differs from global axes.

4. Patterns and mirrors
- For repetitive features, emit one canonical feature entry + a `pattern` (linear or polar) or `mirror` directive. Avoid emitting repeated identical parts.

5. Units, materials and manufacturing metadata
- Always set `units` (default `mm` when unspecified).
- Populate `material_metadata` when user mentions material or when choosing a reasonable default for the application context.
- Add `_manufacturing_notes` for tolerances, draft angle, surface finish when user mentions manufacturing requirements.

6. Validation checks (LLM must self-validate before returning JSON)
- All sketch loops must be closed.
- Pattern spacing must exceed feature size (no overlaps).
- First operation must be `NewBodyFeatureOperation`.
- Hole diameters should follow ISO clearance defaults unless user specifies otherwise.

7. RAG & examples
- Consult the local `SIMPLE_PATTERNS.md` for canonical, short templates (fast lookup).
- Query the RAG database for large, contextual examples and L3 descriptions when user asks for style, industry conventions, or unusual features.

8. Output policy
- Return only valid SCL JSON in machine-readable form (no explanatory text). If the prompt asks for rationale, include a separate `explain` object alongside the JSON.

9. Error handling
- If any validation fails, return an `"error"` object describing the failure and a corrected suggestion patch.

---

Minimal Example (LLM should output only the JSON object):

{ "final_name": "Example", "units": "mm", "parts": { /* ... */ } }
