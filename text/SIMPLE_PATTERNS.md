Purpose: tiny, canonical JSON snippets the LLM can copy/adapt when generating SCL JSON. Keep this file short for fast local lookup.

1) Cylinder (extrude)
```json
{
  "sketch": {"face_1": {"loop_1": {"circle_1": {"Center": [0,0], "Radius": 25}}}},
  "extrusion": {"extrude_depth_towards_normal": 100.0, "operation": "NewBodyFeatureOperation"}
}
```

2) Revolved Cylinder (revolve)
```json
{
  "revolve_profile": {"face_1": {"loop_1": {"line_1": {"Start Point": [0,0], "End Point": [25,0]}, "line_2": {"Start Point": [25,0], "End Point": [25,100]}, "line_3": {"Start Point": [25,100], "End Point": [0,100]}, "line_4": {"Start Point": [0,100], "End Point": [0,0]}}}},
  "revolve": {"axis": [0,0,1], "angle": 360, "operation": "NewBodyFeatureOperation"}
}
```

3) Rectangular Block (extrude)
```json
{
  "sketch": {"face_1": {"loop_1": {"line_1": {"Start Point": [0,0], "End Point": [80,0]}, "line_2": {"Start Point": [80,0], "End Point": [80,60]}, "line_3": {"Start Point": [80,60], "End Point": [0,60]}, "line_4": {"Start Point": [0,60], "End Point": [0,0]}}}},
  "extrusion": {"extrude_depth_towards_normal": 40.0, "operation": "NewBodyFeatureOperation"}
}
```

4) Bolt Circle (polar pattern)
```json
{
  "hole_feature": {"hole_type": "Simple", "diameter": 5.5, "depth": 10.0, "position": [45.0, 0.0], "operation": "CutFeatureOperation"},
  "pattern": {"type": "polar", "count": 6, "center": [0,0,0], "total_angle": 360, "axis": [0,0,1]}
}
```

5) Linear Pattern (slots/holes)
```json
{
  "sketch": {"face_1": {"loop_1": {/* slot loop */}}},
  "extrusion": {"extrude_depth_opposite_normal": 2.0, "operation": "CutFeatureOperation"},
  "pattern": {"type": "linear", "count": 8, "spacing": 20.0, "direction": [1,0,0]}
}
```

6) Fillet (post-processing)
```json
{"post_processing": [{"radius": 3.0, "edge_selector": "|Z"}]}
```

7) Chamfer (post-processing)
```json
{"post_processing": [{"distance": 1.5, "edge_selector": ">Z"}]}
```