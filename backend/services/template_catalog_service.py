import json
import hashlib
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core import config


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_rel_path(path: str) -> Optional[str]:
    normalized = path.replace('\\', '/').strip('/')
    if normalized.startswith('templates/'):
        normalized = normalized[len('templates/'):]
    if not normalized or '..' in normalized.split('/'):
        return None
    return normalized


def _entry_checksum(entry: zipfile.ZipInfo) -> str:
    return f"{entry.CRC}:{entry.file_size}:{entry.date_time}"


def _file_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with file_path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def _catalog_path() -> Path:
    return config.JSON_OUTPUT_DIR / 'template_catalog.json'


def _manifest_path() -> Path:
    return config.JSON_OUTPUT_DIR / 'template_sync_manifest.json'


def load_catalog() -> Dict[str, Any]:
    path = _catalog_path()
    if not path.exists():
        return {
            'version': 1,
            'source': 'templates.zip',
            'last_sync_at': None,
            'summary': {'total': 0, 'ready': 0, 'failed': 0, 'pending': 0},
            'templates': [],
        }
    return json.loads(path.read_text(encoding='utf-8'))


def save_catalog(catalog: Dict[str, Any]) -> None:
    path = _catalog_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog, indent=2), encoding='utf-8')


def load_manifest() -> Dict[str, Any]:
    path = _manifest_path()
    if not path.exists():
        return {'version': 1, 'last_sync_at': None, 'files': {}}
    return json.loads(path.read_text(encoding='utf-8'))


def save_manifest(manifest: Dict[str, Any]) -> None:
    path = _manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')


def sync_templates_from_zip(force: bool = False) -> Dict[str, Any]:
    zip_path = config.BASE_DIR / 'templates.zip'
    templates_dir = config.TEMPLATES_DIR
    templates_dir.mkdir(parents=True, exist_ok=True)

    if not zip_path.exists():
        raise FileNotFoundError(f'templates.zip not found: {zip_path}')

    manifest = load_manifest()
    old_files: Dict[str, Any] = manifest.get('files', {})
    new_files: Dict[str, Any] = {}

    extracted = 0
    skipped = 0
    removed = 0

    seen = set()

    with zipfile.ZipFile(zip_path, 'r') as zf:
        for entry in zf.infolist():
            if entry.is_dir() or not entry.filename.lower().endswith('.json'):
                continue

            rel = _safe_rel_path(entry.filename)
            if not rel:
                continue

            seen.add(rel)
            checksum = _entry_checksum(entry)
            out_path = templates_dir / rel
            prev = old_files.get(rel, {})

            should_extract = force or not out_path.exists() or prev.get('checksum') != checksum
            if should_extract:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(entry, 'r') as src, out_path.open('wb') as dst:
                    dst.write(src.read())
                extracted += 1
            else:
                skipped += 1

            new_files[rel] = {
                'checksum': checksum,
                'updated_at': _utc_now(),
            }

    for old_rel in old_files.keys():
        if old_rel not in seen:
            stale = templates_dir / old_rel
            if stale.exists():
                stale.unlink(missing_ok=True)
                removed += 1

    new_manifest = {
        'version': 1,
        'last_sync_at': _utc_now(),
        'source_zip': str(zip_path),
        'source_zip_mtime': zip_path.stat().st_mtime,
        'files': new_files,
    }
    save_manifest(new_manifest)

    return {
        'zip_path': str(zip_path),
        'templates_dir': str(templates_dir),
        'extracted': extracted,
        'skipped': skipped,
        'removed': removed,
        'total': len(new_files),
    }


def _step_path_for_template_id(template_id: str) -> Path:
    return config.STEP_OUTPUT_DIR / 'templates' / f"{template_id}.step"


def _thumb_path_for_template_id(template_id: str) -> Path:
    return config.PREVIEWS_DIR / 'templates' / f"{template_id}.png"


def _thumb_svg_path_for_template_id(template_id: str) -> Path:
    return config.PREVIEWS_DIR / 'templates' / f"{template_id}.svg"


def discover_templates() -> List[Dict[str, Any]]:
    templates_dir = config.TEMPLATES_DIR
    templates_dir.mkdir(parents=True, exist_ok=True)

    discovered: List[Dict[str, Any]] = []

    for json_file in sorted(templates_dir.rglob('*.json')):
        rel_json = json_file.relative_to(config.BASE_DIR).as_posix()
        rel_under_templates = json_file.relative_to(templates_dir).as_posix()
        template_id = rel_under_templates[:-5]  # drop .json

        category_path = rel_under_templates.split('/')[:-1]
        step_path = _step_path_for_template_id(template_id)
        thumb_png_path = _thumb_path_for_template_id(template_id)
        thumb_svg_path = _thumb_svg_path_for_template_id(template_id)

        if thumb_png_path.exists():
            thumbnail_rel_path = thumb_png_path.relative_to(config.BASE_DIR).as_posix()
            thumbnail_url = f"/{thumbnail_rel_path}"
            has_thumbnail = True
        elif thumb_svg_path.exists():
            thumbnail_rel_path = thumb_svg_path.relative_to(config.BASE_DIR).as_posix()
            thumbnail_url = f"/{thumbnail_rel_path}"
            has_thumbnail = True
        else:
            thumbnail_url = f"/outputs/previews/templates/{template_id}.png"
            has_thumbnail = False

        name = json_file.stem.replace('_', ' ').title()
        description = ''
        editable_parameters: List[Any] = []

        parse_error = None
        try:
            data = json.loads(json_file.read_text(encoding='utf-8'))
            name = data.get('final_name') or data.get('name') or name
            description = data.get('_description', data.get('description', ''))
            editable_parameters = data.get('_editable_parameters', [])
        except Exception as e:
            parse_error = str(e)

        discovered.append({
            'template_id': template_id,
            'name': name,
            'category_path': category_path,
            'relative_json_path': rel_json,
            'relative_step_path': step_path.relative_to(config.BASE_DIR).as_posix(),
            'step_url': f"/outputs/step/templates/{template_id}.step",
            'thumbnail_url': thumbnail_url,
            'build_status': 'ready' if step_path.exists() and has_thumbnail else 'pending',
            'last_built_at': None,
            'checksum': _file_sha256(json_file),
            'description': description,
            'editable_parameters': editable_parameters,
            'error': {'stage': 'json_parse', 'message': parse_error} if parse_error else None,
        })

    return discovered


def _summarize(templates: List[Dict[str, Any]]) -> Dict[str, int]:
    summary = {'total': len(templates), 'ready': 0, 'failed': 0, 'pending': 0}
    for t in templates:
        status = t.get('build_status', 'pending')
        if status == 'ready':
            summary['ready'] += 1
        elif status == 'failed':
            summary['failed'] += 1
        else:
            summary['pending'] += 1
    return summary


def refresh_catalog(sync_zip: bool = True, force_sync: bool = False) -> Dict[str, Any]:
    if sync_zip:
        sync_templates_from_zip(force=force_sync)

    existing = load_catalog()
    existing_map = {t['template_id']: t for t in existing.get('templates', [])}

    templates = discover_templates()

    for item in templates:
        prev = existing_map.get(item['template_id'])
        if prev:
            if prev.get('build_status') == 'failed' and item['build_status'] != 'ready':
                item['build_status'] = 'failed'
            item['last_built_at'] = prev.get('last_built_at')
            if prev.get('error') and item.get('build_status') == 'failed':
                item['error'] = prev.get('error')

    catalog = {
        'version': 1,
        'source': 'templates.zip',
        'last_sync_at': _utc_now(),
        'summary': _summarize(templates),
        'templates': templates,
    }
    save_catalog(catalog)
    return catalog


def build_category_tree(templates: List[Dict[str, Any]]) -> Dict[str, Any]:
    root: Dict[str, Any] = {'name': 'root', 'path': [], 'children': {}, 'template_count': 0}

    for t in templates:
        node = root
        for part in t.get('category_path', []):
            if part not in node['children']:
                node['children'][part] = {
                    'name': part,
                    'path': node['path'] + [part],
                    'children': {},
                    'template_count': 0,
                }
            node = node['children'][part]
            node['template_count'] += 1

    def to_list(node: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'name': node['name'],
            'path': node['path'],
            'template_count': node['template_count'],
            'children': [to_list(node['children'][k]) for k in sorted(node['children'].keys())],
        }

    return to_list(root)


def templates_by_category_path(templates: List[Dict[str, Any]], category_path: str) -> List[Dict[str, Any]]:
    normalized = category_path.strip('/').split('/') if category_path.strip('/') else []
    return [t for t in templates if t.get('category_path', []) == normalized]
