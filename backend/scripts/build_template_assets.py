import argparse
import json
import sys
from pathlib import Path

# Ensure local backend modules take precedence over similarly named third-party packages.
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.template_asset_builder import build_template_assets


def main() -> int:
    parser = argparse.ArgumentParser(description='Build STEP + thumbnails for template JSON files')
    parser.add_argument('--force', action='store_true', help='Rebuild all selected templates')
    parser.add_argument('--category-prefix', type=str, default=None, help='Build only category prefix (e.g. automotive/body_aero)')
    parser.add_argument('--template-id', action='append', default=None, help='Specific template_id to build (repeatable)')
    parser.add_argument('--max-templates', type=int, default=None, help='Limit number of templates for quick runs')

    args = parser.parse_args()

    result = build_template_assets(  
        force=args.force,
        category_prefix=args.category_prefix,
        template_ids=args.template_id,
        max_templates=args.max_templates,
    )

    print(json.dumps(result, indent=2))
    return 0 if result.get('success') else 1


if __name__ == '__main__':
    raise SystemExit(main())
