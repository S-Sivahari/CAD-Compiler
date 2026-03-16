import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core import config
from core.cadquery_generator import CadQueryGenerator
from services.template_catalog_service import (
    load_catalog,
    save_catalog,
    refresh_catalog,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status_entry(status: str, stage: Optional[str] = None, message: Optional[str] = None) -> Dict[str, Any]:
    return {
        'status': status,
        'error': ({'stage': stage, 'message': message, 'last_attempt_at': _utc_now()} if stage else None),
    }


def _rectangle_to_lines(rect: Dict[str, Any]) -> Dict[str, Any]:
    width = float(rect.get('X', rect.get('width', 0.0)))
    height = float(rect.get('Y', rect.get('height', 0.0)))
    if width <= 0 or height <= 0:
        return {}

    half_w = width / 2.0
    half_h = height / 2.0
    p1 = [-half_w, -half_h]
    p2 = [half_w, -half_h]
    p3 = [half_w, half_h]
    p4 = [-half_w, half_h]

    return {
        'line_1': {'Start Point': p1, 'End Point': p2},
        'line_2': {'Start Point': p2, 'End Point': p3},
        'line_3': {'Start Point': p3, 'End Point': p4},
        'line_4': {'Start Point': p4, 'End Point': p1},
    }


def _circle_to_schema(circle: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(circle, dict):
        return {}

    if 'Radius' in circle:
        radius = float(circle.get('Radius', 0.0))
    elif 'Diameter' in circle:
        radius = float(circle.get('Diameter', 0.0)) / 2.0
    elif 'D' in circle:
        radius = float(circle.get('D', 0.0)) / 2.0
    else:
        radius = 0.0

    if radius <= 0:
        return {}

    center = circle.get('Center', [0.0, 0.0])
    if not isinstance(center, list) or len(center) < 2:
        center = [0.0, 0.0]

    return {
        'circle_1': {
            'Center': [float(center[0]), float(center[1])],
            'Radius': radius,
        }
    }


def _normalize_template_primitives(data: Dict[str, Any]) -> Dict[str, Any]:
    parts = data.get('parts', {})
    if not isinstance(parts, dict):
        return data

    for part in parts.values():
        sketch = part.get('sketch', {})
        if not isinstance(sketch, dict):
            continue

        for face in sketch.values():
            if not isinstance(face, dict):
                continue

            for loop_name, loop in list(face.items()):
                if not isinstance(loop, dict):
                    continue

                if 'Rectangle' in loop and all(not k.startswith(('line_', 'arc_', 'circle_')) for k in loop.keys()):
                    converted = _rectangle_to_lines(loop.get('Rectangle', {}))
                    if converted:
                        face[loop_name] = converted
                        continue

                if 'Circle' in loop and all(not k.startswith(('line_', 'arc_', 'circle_')) for k in loop.keys()):
                    converted = _circle_to_schema(loop.get('Circle', {}))
                    if converted:
                        face[loop_name] = converted

    return data


def _build_one_template(template: Dict[str, Any]) -> Dict[str, Any]:
    try:
        try:
            from validators.json_validator import repair_json, validate_json_detailed
        except Exception as e:
            return _status_entry('failed', 'dependency', f"json validator import failed: {e}")

        try:
            from step_editor import step_renderer
        except Exception as e:
            return _status_entry('failed', 'dependency', f"step_renderer import failed: {e}")

        json_path = config.BASE_DIR / template['relative_json_path']
        template_id = template['template_id']
        step_path = config.BASE_DIR / template['relative_step_path']
        thumb_path = config.BASE_DIR / template['thumbnail_url'].lstrip('/')

        step_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.parent.mkdir(parents=True, exist_ok=True)

        data = json.loads(json_path.read_text(encoding='utf-8'))
        data = _normalize_template_primitives(data)
        data = repair_json(data)[0]
        validation = validate_json_detailed(data)
        if not validation.get('valid', False):
            msg = '; '.join(validation.get('errors', [])[:5])
            return _status_entry('failed', 'validation', msg)

        out_stem = Path(template_id).name
        py_dir = config.PY_OUTPUT_DIR / 'templates' / Path(template_id).parent
        py_dir.mkdir(parents=True, exist_ok=True)
        py_file = py_dir / f"{out_stem}_generated.py"

        code = CadQueryGenerator(data, output_name=out_stem).generate()
        py_file.write_text(code, encoding='utf-8')

        result = subprocess.run(
            [sys.executable, str(py_file)],
            cwd=str(step_path.parent),
            capture_output=True,
            text=True,
            timeout=config.EXECUTION_TIMEOUT,
        )
        if result.returncode != 0:
            stderr = (result.stderr or '').strip()
            return _status_entry('failed', 'execution', stderr[:1000] or 'CadQuery execution failed')

        produced = step_path.parent / f"{out_stem}.step"
        if not produced.exists():
            return _status_entry('failed', 'execution', 'STEP file was not produced')

        if produced.resolve() != step_path.resolve():
            step_path.parent.mkdir(parents=True, exist_ok=True)
            produced.replace(step_path)

        step_renderer.render(str(step_path), str(thumb_path))

        return {
            'status': 'ready',
            'error': None,
            'last_built_at': _utc_now(),
        }
    except subprocess.TimeoutExpired:
        return _status_entry('failed', 'execution', f'Execution timeout ({config.EXECUTION_TIMEOUT}s)')
    except Exception as e:
        return _status_entry('failed', 'unknown', str(e))


def build_template_assets(
    force: bool = False,
    category_prefix: Optional[str] = None,
    template_ids: Optional[List[str]] = None,
    max_templates: Optional[int] = None,
) -> Dict[str, Any]:
    catalog = refresh_catalog(sync_zip=True)
    items = catalog.get('templates', [])

    if category_prefix:
        normalized_prefix = category_prefix.strip('/')
        items = [t for t in items if '/'.join(t.get('category_path', [])).startswith(normalized_prefix)]

    if template_ids:
        id_set = set(template_ids)
        items = [t for t in items if t.get('template_id') in id_set]

    if max_templates is not None:
        items = items[:max_templates]

    processed = 0
    built = 0
    failed = 0
    skipped = 0

    catalog_state = load_catalog()
    state_map = {t['template_id']: t for t in catalog_state.get('templates', [])}

    for item in items:
        template_id = item['template_id']
        current = state_map.get(template_id, item)

        if not force and current.get('build_status') == 'ready':
            skipped += 1
            continue

        result = _build_one_template(item)
        processed += 1

        current['build_status'] = result['status']
        current['error'] = result.get('error')
        if result.get('last_built_at'):
            current['last_built_at'] = result['last_built_at']

        if result['status'] == 'ready':
            built += 1
        else:
            failed += 1

    updated_templates = list(state_map.values())
    summary = {'total': len(updated_templates), 'ready': 0, 'failed': 0, 'pending': 0}
    for t in updated_templates:
        s = t.get('build_status', 'pending')
        if s == 'ready':
            summary['ready'] += 1
        elif s == 'failed':
            summary['failed'] += 1
        else:
            summary['pending'] += 1

    catalog_state['summary'] = summary
    catalog_state['last_sync_at'] = _utc_now()
    catalog_state['templates'] = sorted(updated_templates, key=lambda t: t.get('template_id', ''))
    save_catalog(catalog_state)

    return {
        'success': True,
        'processed': processed,
        'built': built,
        'failed': failed,
        'skipped': skipped,
        'summary': summary,
    }
