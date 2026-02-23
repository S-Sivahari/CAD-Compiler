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
            )
            result[view_cfg["name"]] = str(out_png)
            logger.info(f"Rendered view '{view_cfg['name']}' → {out_png}")
        except Exception as exc:
            logger.error(f"Failed to render view '{view_cfg['name']}': {exc}")

    return result


# ─── Core per-view render ─────────────────────────────────────────────────────

# Canvas layout
_W        = 1200   # total image width
_H        = 900    # total image height
_LEGEND_W = 270    # right-side legend panel width
_GEO_W    = _W - _LEGEND_W   # width available for geometry

def _render_view(view_cfg: dict, all_edge_pts: List[List[Tuple]],
                 features: Dict[str, Any], step_stem: str,
                 output_path, include_legend: bool = False) -> str:
    """Render a single view and save it to output_path. Returns path string."""
    from PIL import Image, ImageDraw, ImageFont

    img  = Image.new("RGB", (_W, _H), (248, 249, 250))
    draw = ImageDraw.Draw(img)

    try:
        font_label = ImageFont.truetype("arial.ttf", 13)
        font_title = ImageFont.truetype("arial.ttf", 15)
        font_sm    = ImageFont.truetype("arial.ttf", 11)
        font_bold  = ImageFont.truetype("arialbd.ttf", 12)
    except Exception:
        font_label = ImageFont.load_default()
        font_title = font_label
        font_sm    = font_label
        font_bold  = font_label

    # ── Legend panel background ────────────────────────────────────────────────
    draw.rectangle([_GEO_W, 0, _W, _H], fill=(240, 242, 248))
    draw.line([(_GEO_W, 0), (_GEO_W, _H)], fill=(200, 205, 215), width=1)

    # ── Determine projection function ─────────────────────────────────────────
    proj_fn     = view_cfg.get("project_fn", "isometric")
    u_axis      = view_cfg.get("u_axis")
    v_axis      = view_cfg.get("v_axis")
    view_direction = view_cfg.get("view_dir", (0.5, -0.5, 0.5))

    def project3d(x, y, z):
        if proj_fn == "isometric":
            return _iso_project(x, y, z)
        return _ortho_project(x, y, z, u_axis, v_axis)

    # ── Visibility culling ─────────────────────────────────────────────────────
    depth_min, depth_max = _compute_model_depth_range(all_edge_pts, view_direction)
    depth_range = max(depth_max - depth_min, 1e-6)
    visibility_threshold = depth_min + depth_range * 0.12

    if proj_fn == "isometric":
        visible_edge_pts = all_edge_pts
    else:
        visible_edge_pts = [
            pts for pts in all_edge_pts
            if max(_dot(p, view_direction) for p in pts) > visibility_threshold
        ]

    # ── Projection bounds (geometry area only) ────────────────────────────────
    all_proj = [project3d(*p) for pts in visible_edge_pts for p in pts]
    proj_min, proj_max = _get_proj_bounds(all_proj)

    MARGIN = 80
    def to_px(x, y, z):
        sx, sy = project3d(x, y, z)
        px_min, py_min = proj_min
        px_max, py_max = proj_max
        span_x = max(px_max - px_min, 1e-6)
        span_y = max(py_max - py_min, 1e-6)
        cw = _GEO_W - 2 * MARGIN
        ch = _H     - 2 * MARGIN
        cx = MARGIN + (sx - px_min) / span_x * cw
        cy = MARGIN + (sy - py_min) / span_y * ch
        return int(cx), int(cy)

    # ── Draw edges ────────────────────────────────────────────────────────────
    EDGE_COLOR = (80, 100, 130)
    for pts in visible_edge_pts:
        px_pts = [to_px(*p) for p in pts]
        for k in range(len(px_pts) - 1):
            draw.line([px_pts[k], px_pts[k + 1]], fill=EDGE_COLOR, width=1)

    # ── Axis indicators (isometric only) ─────────────────────────────────────
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

    # ── Feature markers (geometry area) ───────────────────────────────────────
    _draw_feature_markers(draw, features, to_px, view_direction,
                          visibility_threshold, font_bold, font_sm, view_cfg)

    # ── Legend panel ──────────────────────────────────────────────────────────
    _draw_legend(draw, font_sm, font_bold, font_label, features)

    # ── Title ─────────────────────────────────────────────────────────────────
    bb  = features.get("bounding_box", {"x_mm": "?", "y_mm": "?", "z_mm": "?"})
    bbs = f"{bb.get('x_mm','?')}mm × {bb.get('y_mm','?')}mm × {bb.get('z_mm','?')}mm"
    view_label = view_cfg.get("label", view_cfg["name"])
    draw.text((10, 8),  f"{step_stem}  —  {view_label}  —  {bbs}",
              font=font_title, fill=(30, 30, 30))
    draw.text((10, 28),
              "Markers: \u25cf cylinder  \u25a0 horiz-face  \u25c6 vert-face  \u25b2 cone  |  see panel → for IDs",
              font=font_sm, fill=(100, 100, 100))

    output_path = Path(output_path)
    img.save(str(output_path), "PNG")
    return str(output_path)


# ─── Pattern-based marker helpers ────────────────────────────────────────────

def _overlaps(rect, placed: list, pad: int = 4) -> bool:
    """Return True if rect (x0,y0,x1,y1) overlaps any rect in placed (with pad)."""
    x0, y0, x1, y1 = rect
    for (bx0, by0, bx1, by1) in placed:
        if x0 - pad < bx1 and x1 + pad > bx0 and y0 - pad < by1 and y1 + pad > by0:
            return True
    return False


def _marker_radius(feature: dict, feature_type: str, base: int = 8) -> int:
    """Scale marker radius slightly with feature significance."""
    if feature_type == "cylinder":
        r = feature.get("radius_mm", 1)
        return min(14, max(base, int(base + r * 0.3)))
    if feature_type in ("plane", "cone"):
        a = feature.get("area_mm2", 1)
        return min(13, max(base, int(base + a ** 0.25)))
    return base


def _draw_feature_markers(draw, features, to_px, view_direction, visibility_threshold,
                          font_badge, font_sm, view_cfg):
    """
    Draw pattern markers for all visible features.

    Strategy:
    - Always draw the shape (circle / square / diamond / triangle).
    - Draw a short ID badge (e.g. 'C2', 'P14') next to the shape ONLY if it
      doesn’t overlap any previously-placed badges.  This prevents the label
      blizzard on complex parts while preserving the marker itself.
    """
    from PIL import ImageDraw as _ID

    proj_fn = view_cfg.get("project_fn", "isometric")

    def visible(loc):
        if proj_fn == "isometric":
            return True
        return _dot(tuple(loc), view_direction) >= visibility_threshold

    placed: List[Tuple] = []   # list of (x0,y0,x1,y1) bounding-boxes already drawn

    def try_badge(draw, px, py, text, color, font):
        """Draw a badge label if there is clear space for it."""
        try:
            bbox = draw.textbbox((px, py), text, font=font)
        except Exception:
            bbox = (px, py, px + len(text) * 7, py + 14)
        pad   = 3
        rb    = (bbox[0]-pad, bbox[1]-pad, bbox[2]+pad, bbox[3]+pad)
        if _overlaps(rb, placed):
            return  # skip — too crowded
        placed.append(rb)
        draw.rectangle(rb, fill=(255, 255, 255, 220), outline=color, width=1)
        draw.text((px, py), text, font=font, fill=color)

    # ── Cylinders — filled red circles ────────────────────────────────────────
    CYL = (210, 40, 40)
    for cyl in features.get("cylinders", []):
        loc = cyl["location"]
        if not visible(loc): continue
        px, py = to_px(*loc)
        r = _marker_radius(cyl, "cylinder")
        draw.ellipse([px-r, py-r, px+r, py+r], fill=CYL, outline=(255,255,255), width=2)
        badge = cyl["id"].replace("f","C")  # e.g. "f3" -> "C3"
        try_badge(draw, px + r + 3, py - 7, badge, CYL, font_badge)

    # ── Planes — filled squares (horiz) or diamonds (vert) ────────────────────
    PLN_H = (25, 90, 200)    # horizontal faces — strong blue square
    PLN_V = (80, 140, 220)   # vertical/side faces — lighter blue diamond
    for pln in features.get("planes", []):
        if pln.get("area_mm2", 0) < 0.5:   # skip sub-mm² noise
            continue
        loc = pln["location"]
        if not visible(loc): continue
        px, py = to_px(*loc)
        r = _marker_radius(pln, "plane")
        ft = pln.get("face_type", "vertical")
        color = PLN_H if ft == "horizontal" else PLN_V
        if ft == "horizontal":
            # Square
            draw.rectangle([px-r, py-r, px+r, py+r], fill=color, outline=(255,255,255), width=2)
        else:
            # Diamond
            draw.polygon([
                (px, py - r), (px + r, py), (px, py + r), (px - r, py)
            ], fill=color, outline=(255,255,255))
        badge = pln["id"].replace("f","P")
        try_badge(draw, px + r + 3, py - 7, badge, color, font_badge)

    # ── Cones — filled purple triangles ──────────────────────────────────────
    CONE = (180, 80, 200)
    for cone in features.get("cones", []):
        loc = cone["location"]
        if not visible(loc): continue
        px, py = to_px(*loc)
        r = _marker_radius(cone, "cone")
        draw.polygon([
            (px, py - r), (px + r, py + r), (px - r, py + r)
        ], fill=CONE, outline=(255,255,255), width=1)
        badge = cone["id"].replace("f","K")  # K = countersink
        try_badge(draw, px + r + 3, py - 7, badge, CONE, font_badge)


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


def _draw_legend(draw, font_sm, font_bold, font_label, features):
    """
    Draw a compact grouped legend in the right-side panel.

    Groups:
      CYLINDERS (N)             — list all (usually few)
      HORIZ FACES (N)           — top-5 by area + "... N more"
      VERT / SIDE FACES (N)     — top-5 by area + "... N more"
      CONES (N)                 — list all
    """
    # Panel starts at x = _GEO_W + 10
    x0     = _GEO_W + 12
    x_end  = _W - 6
    y      = 14
    lh     = 16    # line height
    MAX_ROWS = 5   # max rows per group before truncating

    CYL  = (210, 40, 40)
    PLN_H = (25, 90, 200)
    PLN_V = (80, 140, 220)
    CONE = (180, 80, 200)
    HDR  = (40,  40,  40)
    SEP  = (190, 195, 210)

    def section_header(title, count, color):
        nonlocal y
        draw.line([(x0, y+2), (x_end, y+2)], fill=SEP, width=1)
        y += 6
        draw.text((x0, y), f"{title}  ({count})", font=font_bold, fill=color)
        y += lh + 2

    def icon_row(shape, color, text):
        nonlocal y
        if shape == "circle":
            draw.ellipse([x0, y+2, x0+10, y+12], fill=color)
        elif shape == "square":
            draw.rectangle([x0, y+2, x0+10, y+12], fill=color)
        elif shape == "diamond":
            mx = x0 + 5
            draw.polygon([(mx, y+1),(x0+10, y+7),(mx, y+13),(x0, y+7)], fill=color)
        elif shape == "triangle":
            draw.polygon([(x0+5, y+1),(x0+11, y+13),(x0-1, y+13)], fill=color)
        # Clip text to panel width
        max_chars = int((x_end - x0 - 14) / 6.5)
        clipped = text if len(text) <= max_chars else text[:max_chars-1] + "…"
        draw.text((x0 + 14, y), clipped, font=font_sm, fill=(50, 50, 50))
        y += lh

    def note_row(text):
        nonlocal y
        draw.text((x0 + 14, y), text, font=font_sm, fill=(120, 120, 130))
        y += lh

    # Title
    draw.text((x0, y), "FEATURE REFERENCE", font=font_label, fill=HDR)
    y += lh + 4

    # ── Cylinders ───────────────────────────────────
    cyls = features.get("cylinders", [])
    section_header("● CYLINDERS", len(cyls), CYL)
    if not cyls:
        note_row("  none detected")
    for c in cyls:
        fid  = c["id"]
        r    = c["radius_mm"]
        axis = c.get("axis", "?")
        icon_row("circle", CYL, f"{fid}  R={r}mm  axis={axis}")

    y += 4
    # ── Horizontal flat faces ────────────────────────
    h_planes = sorted(
        [p for p in features.get("planes", []) if p.get("face_type") == "horizontal" and p.get("area_mm2",0) >= 0.5],
        key=lambda p: -p.get("area_mm2", 0)
    )
    section_header("■ HORIZ FACES", len(h_planes), PLN_H)
    if not h_planes:
        note_row("  none detected")
    for p in h_planes[:MAX_ROWS]:
        dims = p.get("dims", [0, 0])
        z    = round(p["location"][2], 1)
        icon_row("square", PLN_H, f"{p['id']}  {dims[0]:.1f}×{dims[1]:.1f}mm  z={z}mm")
    if len(h_planes) > MAX_ROWS:
        note_row(f"  … {len(h_planes)-MAX_ROWS} more (use zoom)")

    y += 4
    # ── Vertical / side flat faces ───────────────────
    v_planes = sorted(
        [p for p in features.get("planes", []) if p.get("face_type") != "horizontal" and p.get("area_mm2",0) >= 0.5],
        key=lambda p: -p.get("area_mm2", 0)
    )
    section_header("◆ VERT FACES", len(v_planes), PLN_V)
    if not v_planes:
        note_row("  none detected")
    for p in v_planes[:MAX_ROWS]:
        dims = p.get("dims", [0, 0])
        n    = p.get("normal", [0, 0, 0])
        icon_row("diamond", PLN_V,
                 f"{p['id']}  {dims[0]:.1f}×{dims[1]:.1f}mm  n=[{n[0]:.0f},{n[1]:.0f},{n[2]:.0f}]")
    if len(v_planes) > MAX_ROWS:
        note_row(f"  … {len(v_planes)-MAX_ROWS} more (zoom in)")

    y += 4
    # ── Cones / countersinks ─────────────────────────
    cones = features.get("cones", [])
    section_header("▲ CONES", len(cones), CONE)
    if not cones:
        note_row("  none detected")
    for cone in cones:
        ang = cone.get("half_angle_deg", "?")
        icon_row("triangle", CONE, f"{cone['id']}  half-angle={ang}°")

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
