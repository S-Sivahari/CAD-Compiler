"""Step Renderer - Converts a STEP file to images, with optional feature labels.

Three modes:
  render()          → Plain isometric SVG/PNG (wireframe render).
  render_labeled()  → Annotated diagram (single isometric view).
  render_multiview()→ 7 labeled PNGs: isometric + top/bottom/front/back/left/right.
                      Saves images in outputs/previews/<stem>/ folder.
"""
import os
import math
import cadquery as cq
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)


# ─── View definitions ─────────────────────────────────────────────────────────

# Each view has:
#   display_name: Human-readable label on the image
#   view_dir:     3D unit vector pointing TOWARD the camera (i.e., the ray direction).
#                 An edge whose points are all behind the model in this direction is culled.
#   axes:         (u_axis, v_axis) — two 3D unit vectors forming the projection plane.
#                 The projected u/v coordinates become the image x/y.

VIEWS = [
    {
        "name": "isometric",
        "label": "Isometric",
        "view_dir": (0.5, -0.5, 0.5),        # matches CadQuery default
        "project_fn": "isometric",
    },
    {
        "name": "top",
        "label": "Top (+Z → down)",
        "view_dir": (0.0, 0.0, 1.0),          # camera looks from +Z down
        "project_fn": "ortho",
        "u_axis": (1.0, 0.0, 0.0),
        "v_axis": (0.0, 1.0, 0.0),
    },
    {
        "name": "bottom",
        "label": "Bottom (-Z → up)",
        "view_dir": (0.0, 0.0, -1.0),
        "project_fn": "ortho",
        "u_axis": (1.0, 0.0, 0.0),
        "v_axis": (0.0, -1.0, 0.0),
    },
    {
        "name": "front",
        "label": "Front (-Y → front)",
        "view_dir": (0.0, -1.0, 0.0),
        "project_fn": "ortho",
        "u_axis": (1.0, 0.0, 0.0),
        "v_axis": (0.0, 0.0, -1.0),
    },
    {
        "name": "back",
        "label": "Back (+Y → back)",
        "view_dir": (0.0, 1.0, 0.0),
        "project_fn": "ortho",
        "u_axis": (-1.0, 0.0, 0.0),
        "v_axis": (0.0, 0.0, -1.0),
    },
    {
        "name": "left",
        "label": "Left (-X → left)",
        "view_dir": (-1.0, 0.0, 0.0),
        "project_fn": "ortho",
        "u_axis": (0.0, 1.0, 0.0),
        "v_axis": (0.0, 0.0, -1.0),
    },
    {
        "name": "right",
        "label": "Right (+X → right)",
        "view_dir": (1.0, 0.0, 0.0),
        "project_fn": "ortho",
        "u_axis": (0.0, -1.0, 0.0),
        "v_axis": (0.0, 0.0, -1.0),
    },
]


# ─── Projection helpers ────────────────────────────────────────────────────────

def _dot(a, b):
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def _iso_project(x: float, y: float, z: float) -> Tuple[float, float]:
    """Right isometric projection matching CadQuery's projectionDir=(0.5,-0.5,0.5)."""
    angle = math.pi / 6  # 30°
    sx =  (x - y) * math.cos(angle)
    sy = -((x + y) * math.sin(angle) + z)
    return sx, sy


def _ortho_project(x: float, y: float, z: float, u_axis, v_axis) -> Tuple[float, float]:
    """Orthographic projection along u_axis / v_axis."""
    p = (x, y, z)
    su = _dot(p, u_axis)
    sv = _dot(p, v_axis)
    return su, sv


def _map_to_canvas(sx, sy, proj_min, proj_max, canvas_w, canvas_h, margin=80):
    """Map projected 2D coordinates to pixel canvas coordinates."""
    px_min, py_min = proj_min
    px_max, py_max = proj_max
    span_x = max(px_max - px_min, 1e-6)
    span_y = max(py_max - py_min, 1e-6)
    cw = canvas_w - 2 * margin
    ch = canvas_h - 2 * margin
    cx = margin + (sx - px_min) / span_x * cw
    cy = margin + (sy - py_min) / span_y * ch
    return int(cx), int(cy)


def _get_proj_bounds(projected_pts: List[Tuple[float, float]], extra_margin=0.12):
    """Compute projected bounding box."""
    if not projected_pts:
        return (-10, -10), (10, 10)
    xs = [p[0] for p in projected_pts]
    ys = [p[1] for p in projected_pts]
    pad_x = (max(xs) - min(xs)) * extra_margin
    pad_y = (max(ys) - min(ys)) * extra_margin
    return (min(xs) - pad_x, min(ys) - pad_y), (max(xs) + pad_x, max(ys) + pad_y)


def _sample_edge(edge, n_line=2, n_curve=24) -> List[Tuple[float, float, float]]:
    """
    Sample 3D points along a CadQuery edge.
    Uses BRepAdaptor_Curve for accurate curve sampling.
    """
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_Line

    try:
        adaptor = BRepAdaptor_Curve(edge.wrapped)
        curve_type = adaptor.GetType()
        n = n_line if curve_type == GeomAbs_Line else n_curve
        t0 = adaptor.FirstParameter()
        t1 = adaptor.LastParameter()
        pts = []
        for j in range(n + 1):
            t = t0 + (t1 - t0) * j / n
            p = adaptor.Value(t)
            pts.append((p.X(), p.Y(), p.Z()))
        return pts
    except Exception:
        return []


# ─── Visibility (depth-based culling) ─────────────────────────────────────────

def _is_edge_visible(pts: List[Tuple[float, float, float]], view_dir: tuple,
                     model_depth_min: float, threshold_frac=0.12) -> bool:
    """
    Returns True if the edge is visible from the given view direction.

    An edge is considered hidden (not visible) if all its sampled 3D points
    have a depth value (dot product with view_dir) that is below the model's
    minimum depth plus a small threshold.  This culls back-facing edges.

    Args:
        pts:             Sampled 3D points on the edge.
        view_dir:        Camera direction unit vector (pointing toward viewer).
        model_depth_min: Minimum depth of any model point in this view direction.
        threshold_frac:  A fraction of model depth extent used as tolerance.
    """
    if not pts:
        return False
    depths = [_dot(p, view_dir) for p in pts]
    return max(depths) > model_depth_min + threshold_frac
    # If all points are near the back, hide the edge


def _compute_model_depth_range(all_edge_pts, view_dir):
    """Compute min/max depth of all model points along view_dir."""
    depths = []
    for pts in all_edge_pts:
        for p in pts:
            depths.append(_dot(p, view_dir))
    if not depths:
        return 0.0, 1.0
    return min(depths), max(depths)


# ─── Plain render ─────────────────────────────────────────────────────────────

def render(step_path: str, output_path: Optional[str] = None) -> str:
    """Render a STEP file to an SVG/PNG image (isometric view)."""
    step_path = Path(step_path).resolve()
    if not step_path.exists():
        raise FileNotFoundError(f"STEP file not found: {step_path}")

    if output_path is None:
        output_path = step_path.with_suffix(".png")
    else:
        output_path = Path(output_path).resolve()

    model = cq.importers.importStep(str(step_path))
    svg_path = output_path.with_suffix(".svg")
    cq.exporters.export(model, str(svg_path), opt={
        "width": 800, "height": 600,
        "marginLeft": 10, "marginTop": 10,
        "showAxes": False,
        "projectionDir": (0.5, -0.5, 0.5),
        "strokeColor": (0, 0, 0),
        "hiddenColor": (0, 100, 0),
        "showHidden": False,
    })

    try:
        import cairosvg
        cairosvg.svg2png(url=str(svg_path), write_to=str(output_path), scale=2.0)
        os.remove(svg_path)
        return str(output_path)
    except ImportError:
        logger.warning("cairosvg not installed. Returning SVG path.")
        return str(svg_path)


# ─── Single labeled render (backward compat) ────────────────────────────────

def render_labeled(step_path: str, features: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Render the ACTUAL part wireframe (all edges from the STEP model)
    and overlay feature ID labels at each face center (isometric view).
    """
    step_path = Path(step_path).resolve()
    if output_path is None:
        output_path = step_path.with_suffix(".labeled.png")
    else:
        output_path = Path(output_path).resolve()

    model = cq.importers.importStep(str(step_path))
    all_edge_pts = [_sample_edge(e) for e in model.edges().vals()]
    all_edge_pts = [pts for pts in all_edge_pts if len(pts) >= 2]

    img_path = _render_view(
        view_cfg=VIEWS[0],  # isometric
        all_edge_pts=all_edge_pts,
        features=features,
        step_stem=step_path.stem,
        output_path=output_path,
        include_legend=True,
    )
    logger.info(f"Labeled feature map saved: {img_path}")
    return img_path


# ─── Multi-view render (7 angles) ────────────────────────────────────────────

def render_multiview(step_path: str, features: Dict[str, Any],
                     output_dir: Optional[str] = None) -> Dict[str, str]:
    """
    Render 7 labeled PNG images of the STEP model, one per view angle.

    Views: isometric, top, bottom, front, back, left, right.
    Only edges visible from each view direction are drawn.

    Args:
        step_path:  Path to the STEP file.
        features:   Output dict from step_analyzer.analyze().
        output_dir: Directory in which to create the images folder.
                    Defaults to the same directory as step_path.

    Returns:
        Dict mapping view name → absolute path to the PNG, e.g.:
        { "isometric": "/.../.../isometric.png", "top": "...", ... }
    """
    step_path = Path(step_path).resolve()
    if not step_path.exists():
        raise FileNotFoundError(f"STEP file not found: {step_path}")

    # Create per-stem subfolder under output_dir
    if output_dir is None:
        folder = step_path.parent / step_path.stem
    else:
        folder = Path(output_dir) / step_path.stem
    folder.mkdir(parents=True, exist_ok=True)

    # Load model once
    model = cq.importers.importStep(str(step_path))
    all_edge_pts = [_sample_edge(e) for e in model.edges().vals()]
    all_edge_pts = [pts for pts in all_edge_pts if len(pts) >= 2]

    result = {}
    for view_cfg in VIEWS:
        out_png = folder / f"{view_cfg['name']}.png"
        try:
            _render_view(
                view_cfg=view_cfg,
                all_edge_pts=all_edge_pts,
                features=features,
                step_stem=step_path.stem,
                output_path=out_png,
                include_legend=(view_cfg["name"] == "isometric"),
            )
            result[view_cfg["name"]] = str(out_png)
            logger.info(f"Rendered view '{view_cfg['name']}' → {out_png}")
        except Exception as exc:
            logger.error(f"Failed to render view '{view_cfg['name']}': {exc}")

    return result


# ─── Core per-view render ─────────────────────────────────────────────────────

def _render_view(view_cfg: dict, all_edge_pts: List[List[Tuple]],
                 features: Dict[str, Any], step_stem: str,
                 output_path, include_legend: bool = False) -> str:
    """Render a single view and save it to output_path. Returns path string."""
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1000, 750
    img  = Image.new("RGB", (W, H), (248, 249, 250))
    draw = ImageDraw.Draw(img)

    try:
        font_label = ImageFont.truetype("arial.ttf", 13)
        font_title = ImageFont.truetype("arial.ttf", 15)
        font_sm    = ImageFont.truetype("arial.ttf", 11)
    except Exception:
        font_label = ImageFont.load_default()
        font_title = font_label
        font_sm    = font_label

    # ── Determine projection function for this view ────────────────────────────
    proj_fn = view_cfg.get("project_fn", "isometric")
    u_axis = view_cfg.get("u_axis")
    v_axis = view_cfg.get("v_axis")
    view_direction = view_cfg.get("view_dir", (0.5, -0.5, 0.5))

    def project3d(x, y, z):
        if proj_fn == "isometric":
            return _iso_project(x, y, z)
        else:
            return _ortho_project(x, y, z, u_axis, v_axis)

    # ── Compute depth range for visibility culling ─────────────────────────────
    depth_min, depth_max = _compute_model_depth_range(all_edge_pts, view_direction)
    depth_range = max(depth_max - depth_min, 1e-6)
    # threshold is 12% from front face (depths closer to depth_min are "back")
    visibility_threshold = depth_min + depth_range * 0.12

    # ── Filter visible edges ───────────────────────────────────────────────────
    if proj_fn == "isometric":
        # Isometric: show all edges (same behaviour as before)
        visible_edge_pts = all_edge_pts
    else:
        visible_edge_pts = [
            pts for pts in all_edge_pts
            if max(_dot(p, view_direction) for p in pts) > visibility_threshold
        ]

    # ── Compute projection bounds from visible edges ───────────────────────────
    all_proj = []
    for pts in visible_edge_pts:
        for p in pts:
            all_proj.append(project3d(*p))
    proj_min, proj_max = _get_proj_bounds(all_proj)

    def to_px(x, y, z):
        sx, sy = project3d(x, y, z)
        return _map_to_canvas(sx, sy, proj_min, proj_max, W, H, margin=100)

    # ── Draw visible edges ─────────────────────────────────────────────────────
    EDGE_COLOR = (80, 100, 130)
    for pts in visible_edge_pts:
        px_pts = [to_px(*p) for p in pts]
        for k in range(len(px_pts) - 1):
            draw.line([px_pts[k], px_pts[k + 1]], fill=EDGE_COLOR, width=1)

    # ── Draw axis indicators (isometric only) ─────────────────────────────────
    if proj_fn == "isometric":
        bb = features.get("bounding_box", {"x_mm": 10, "y_mm": 10, "z_mm": 10})
        xM, yM, zM = bb["x_mm"], bb["y_mm"], bb["z_mm"]
        ox, oy = to_px(0, 0, 0)
        ax_x = to_px(xM * 0.3, 0, 0)
        ax_y = to_px(0, yM * 0.3, 0)
        ax_z = to_px(0, 0, zM * 0.3)
        draw.line([(ox, oy), ax_x], fill=(200, 60, 60), width=2)
        draw.line([(ox, oy), ax_y], fill=(60, 160, 60), width=2)
        draw.line([(ox, oy), ax_z], fill=(60, 60, 200), width=2)
        draw.text(ax_x, " X", font=font_sm, fill=(200, 60, 60))
        draw.text(ax_y, " Y", font=font_sm, fill=(60, 160, 60))
        draw.text(ax_z, " Z", font=font_sm, fill=(60, 60, 200))

    # ── Overlay feature markers (only features visible from this view) ─────────
    _draw_feature_markers(draw, features, to_px, view_direction,
                          visibility_threshold, font_label, font_sm, view_cfg)

    # ── Legend (isometric view only) ─────────────────────────────────────────
    if include_legend:
        _draw_legend(draw, font_sm, font_label, features)

    # ── Title ─────────────────────────────────────────────────────────────────
    bb = features.get("bounding_box", {"x_mm": "?", "y_mm": "?", "z_mm": "?"})
    bbs = f"{bb.get('x_mm', '?')}mm × {bb.get('y_mm', '?')}mm × {bb.get('z_mm', '?')}mm"
    view_label = view_cfg.get("label", view_cfg["name"])
    draw.text((10, 8),  f"{step_stem}  —  {view_label}  —  {bbs}", font=font_title, fill=(30, 30, 30))
    draw.text((10, 28), "Use feature IDs in your edit prompt (e.g. 'change f6 radius to 5mm')",
              font=font_sm, fill=(100, 100, 100))

    output_path = Path(output_path)
    img.save(str(output_path), "PNG")
    return str(output_path)


def _draw_feature_markers(draw, features, to_px, view_direction, visibility_threshold,
                          font_label, font_sm, view_cfg):
    """Draw cylinder, plane, and cone markers - only for features visible in this view."""
    proj_fn = view_cfg.get("project_fn", "isometric")

    def _is_loc_visible(loc):
        """Check if a 3D location is visible (not fully behind the model) in this view."""
        if proj_fn == "isometric":
            return True  # Show all in isometric
        depth = _dot(loc, view_direction)
        return depth >= visibility_threshold

    # ── Cylinder markers (red dots) ──────────────────────────────────────────
    CYL_COLOR = (210, 40, 40)
    for cyl in features.get("cylinders", []):
        loc = tuple(cyl["location"])
        if not _is_loc_visible(loc):
            continue
        px, py = to_px(*loc)
        r = 9
        draw.ellipse([px-r, py-r, px+r, py+r], fill=CYL_COLOR, outline="white", width=2)
        tag = f"{cyl['id']}  R={cyl['radius_mm']}mm  ax={cyl['axis']}"
        _draw_label(draw, px + 13, py - 7, tag, font_label, CYL_COLOR)

    # ── Plane markers (blue diamonds at face center) ───────────────────────
    PLN_STRONG = (25, 90, 200)
    PLN_SIDE   = (80, 140, 220)

    for pln in features.get("planes", []):
        if pln.get("area_mm2", 0) < 0.001:
            continue
        loc = tuple(pln["location"])
        if not _is_loc_visible(loc):
            continue
        px, py = to_px(*loc)
        r = 7
        color = PLN_STRONG if pln.get("face_type") == "horizontal" else PLN_SIDE
        draw.polygon([
            (px, py - r), (px + r, py), (px, py + r), (px - r, py)
        ], fill=color, outline="white")
        dims = pln.get("dims", [0, 0])
        ft   = pln.get("face_type", "plane")
        tag  = f"{pln['id']}  {ft}  {dims[0]:.1f}×{dims[1]:.1f}mm"
        _draw_label(draw, px + 11, py - 6, tag, font_sm, color)

    # ── Cone markers ──────────────────────────────────────────────────────
    CONE_COLOR = (180, 80, 200)
    for cone in features.get("cones", []):
        loc = tuple(cone["location"])
        if not _is_loc_visible(loc):
            continue
        px, py = to_px(*loc)
        r = 8
        draw.polygon([
            (px, py - r), (px + r, py + r), (px - r, py + r)
        ], fill=CONE_COLOR, outline="white")
        tag = f"{cone['id']}  cone  α={cone['half_angle_deg']}°"
        _draw_label(draw, px + 11, py - 6, tag, font_sm, CONE_COLOR)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _draw_label(draw, x, y, text, font, color):
    """Draw text with a semi-transparent white background box."""
    try:
        bbox = draw.textbbox((x, y), text, font=font)
    except Exception:
        bbox = (x, y, x + len(text) * 7, y + 14)
    pad = 2
    draw.rectangle([bbox[0]-pad, bbox[1]-pad, bbox[2]+pad, bbox[3]+pad],
                   fill=(255, 255, 255), outline=color, width=1)
    draw.text((x, y), text, font=font, fill=color)


def _draw_legend(draw, font_sm, font_label, features):
    """Draw feature reference table in bottom-left."""
    x0, y0 = 10, 530
    line_h  = 17

    n_meaningful_planes = sum(1 for p in features.get("planes", []) if p.get("area_mm2", 0) >= 0.001)
    total_rows = len(features.get("cylinders", [])) + n_meaningful_planes + len(features.get("cones", [])) + 1
    box_h = total_rows * line_h + 24
    draw.rectangle([x0-4, y0-22, 420, y0 + box_h],
                   fill=(255, 255, 255), outline=(190, 190, 200), width=1)
    draw.text((x0, y0 - 18), "FEATURE REFERENCE", font=font_label, fill=(40, 40, 40))

    row = y0
    for c in features.get("cylinders", []):
        draw.ellipse([x0, row+3, x0+11, row+14], fill=(210, 40, 40))
        draw.text((x0+16, row),
                  f"{c['id']}  Cylinder   R={c['radius_mm']}mm   axis={c['axis']}   loc={c['location']}",
                  font=font_sm, fill=(170, 30, 30))
        row += line_h

    for p in features.get("planes", []):
        if p.get("area_mm2", 0) < 0.001:
            continue
        ft   = p.get("face_type", "plane")
        dims = p.get("dims", [0, 0])
        n    = p["normal"]
        color = (25, 90, 200) if ft == "horizontal" else (80, 140, 220)
        draw.polygon([(x0+5, row), (x0+11, row+11), (x0-1, row+11)], fill=color)
        draw.text((x0+16, row),
                  f"{p['id']}  {ft}   {dims[0]:.1f}×{dims[1]:.1f}mm   n=[{n[0]:.0f},{n[1]:.0f},{n[2]:.0f}]   area={p['area_mm2']:.1f}mm²",
                  font=font_sm, fill=color)
        row += line_h

    for cone in features.get("cones", []):
        draw.polygon([(x0+5, row), (x0+11, row+11), (x0-1, row+11)], fill=(180, 80, 200))
        draw.text((x0+16, row),
                  f"{cone['id']}  Cone   half_angle={cone['half_angle_deg']}°",
                  font=font_sm, fill=(140, 50, 170))
        row += line_h


if __name__ == "__main__":
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from step_editor import step_analyzer

    if len(sys.argv) < 2:
        print("Usage: python -m step_editor.step_renderer <path.step> [output_dir]")
        sys.exit(1)

    step = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Analyzing: {step}")
    feats = step_analyzer.analyze(step)
    print(f"  Found: {len(feats['cylinders'])} cylinders, {len(feats['planes'])} planes, "
          f"{len(feats['cones'])} cones")

    print("Rendering 7-view multiview images...")
    paths = render_multiview(step, feats, out_dir)
    for view_name, path in paths.items():
        print(f"  {view_name:12s} → {path}")
