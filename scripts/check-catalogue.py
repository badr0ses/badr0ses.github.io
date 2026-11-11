"""Validate catalogue integrity and optionally compare every entry to the client."""
import argparse
import binascii
import json
import math
from pathlib import Path
import struct
import zlib

from nalya_formats import Archive, Scene, field
from catalogue_visibility import exclusion_reason

ROOT = Path(__file__).resolve().parents[1]


def check_png(path):
    data = path.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', path
    pos, compressed, width, height = 8, bytearray(), None, None
    while pos < len(data):
        length = struct.unpack_from('>I', data, pos)[0]
        name, payload = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + length]
        crc = struct.unpack_from('>I', data, pos + 8 + length)[0]
        assert binascii.crc32(name + payload) & 0xFFFFFFFF == crc, path
        if name == b'IHDR':
            width, height, depth, color, _, _, interlace = struct.unpack_from('>IIBBBBB', payload)
            assert depth in (1, 2, 4, 8, 16) and color in (0, 2, 3, 4, 6), path
            assert interlace == 0, path
        elif name == b'IDAT':
            compressed.extend(payload)
        pos += length + 12
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
    assert len(zlib.decompress(compressed)) == height * ((width * channels * depth + 7) // 8 + 1), path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', help='Read-only comparison against an installed client')
    args = parser.parse_args()
    entries = json.loads((ROOT / 'data/database.json').read_text(encoding='utf-8'))
    meta = json.loads((ROOT / 'data/catalogue-meta.json').read_text(encoding='utf-8'))
    assert len(entries) == meta['total']
    assert len({item['id'] for item in entries}) == len(entries)
    assert sum(item['kind'] == 'item' for item in entries) == meta['items']
    assert sum(item['kind'] == 'horse' for item in entries) == meta['horses']
    assert sum(not item['unlisted'] for item in entries) == meta['browsable']
    assert sum(bool(item['locations']) for item in entries) == meta['withLocation']
    local_images = set()
    for item in entries:
        assert exclusion_reason(item) is None, item['id']
        assert item['title'].strip() and item['category'] and item['section'], item['id']
        assert item['id'] == f"{item['kind']}-{item['gameId']}", item['id']
        assert isinstance(item['events'], list) and isinstance(item['locations'], list)
        for key in ('priceSC', 'priceJS', 'requiredLevel'):
            value = item[key]
            assert value is None or isinstance(value, (int, float)) and math.isfinite(value) and value >= 0, (item['id'], key)
        for value in item['stats'].values():
            assert value is None or math.isfinite(value), item['id']
        for image in (item['image'], item.get('fallbackImage')):
            if not image:
                continue
            if image.startswith('https://'):
                continue
            assert image.startswith(('assets/catalogue/icons/', 'assets/catalogue/photos/', 'assets/HAIRSTYLES/')) and '..' not in image
            path = (ROOT / image).resolve()
            assert path.is_relative_to(ROOT) and path.is_file(), (item['id'], image)
            local_images.add(path)
    for path in local_images:
        if path.suffix == '.png':
            check_png(path)
        else:
            data = path.read_bytes()
            assert (data[:4] == b'RIFF' and data[8:12] == b'WEBP') or (data[:2] == b'\xff\xd8' and data[-2:] == b'\xff\xd9'), path
    if args.game:
        archive = Archive(args.game)
        source_items = {field(obj, 'base.instanceId'): obj for obj in Scene(archive.read('Scene\\PlayerItemManager.scene')).objects(101)}
        source_horses = {field(obj, 'base.instanceId'): obj for obj in Scene(archive.read('Scene\\HorseManager.scene')).objects(166)}
        assert len(source_items) == meta['sourceItems'] and len(source_horses) == meta['sourceHorses']
        assert len(entries) + sum(meta['excluded'].values()) == len(source_items) + len(source_horses)
        for item in entries:
            obj = (source_items if item['kind'] == 'item' else source_horses)[item['gameId']]
            prefix = 'playerItem.' if item['kind'] == 'item' else 'horseForSaleData.'
            assert item['internalName'] == field(obj, 'base.name'), item['id']
            assert item['requiredLevel'] == field(obj, prefix + 'levelRequirement'), item['id']
            assert item['priceSC'] == field(obj, prefix + ('sCPrice' if item['kind'] == 'item' else 'starPrice')), item['id']
            if item['kind'] == 'item':
                assert item['priceJS'] == field(obj, 'playerItem.jSPrice'), item['id']
            else:
                assert item['bodyId'] == field(obj, 'horseForSaleData.body'), item['id']
        print(f'Compared all {len(entries):,} names, IDs, prices and level requirements with the client.')
    print(f'Validated {len(entries):,} records and {len(local_images):,} local images.')


if __name__ == '__main__':
    main()
