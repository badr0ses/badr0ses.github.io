"""Preserve reviewed in-game horse photos after automatic reference matching."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def horse_photo_updates(entries):
    corrections = json.loads((ROOT / 'data/horse-photo-corrections.json').read_text(encoding='utf-8'))
    by_id = {entry['id']: entry for entry in entries}
    updates = {}
    for entry_id, correction in corrections.items():
        entry = by_id[entry_id]
        assert entry['kind'] == 'horse' and entry['bodyId'] == correction['bodyId'], entry_id
        image = correction['image']
        path = (ROOT / image).resolve()
        assert image.startswith('assets/') and path.is_relative_to(ROOT) and path.is_file(), image
        updates[entry_id] = {
            'image': image, 'imageKind': 'In-game screenshot',
            'variant': correction['variant'], 'photoColor': correction['variant'].lower(),
            'photoSource': None, 'photoModel': None,
            'photoMatch': 'User-supplied in-game screenshot', 'photoBodyId': entry['bodyId'],
        }
    return updates
