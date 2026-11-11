"""Check hairstyle asset matches, distinct models, source fields and saved JoJo portraits."""
import argparse
import json
from pathlib import Path
import re

from nalya_formats import Archive, Scene, field

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', required=True)
    args = parser.parse_args()
    archive = Archive(args.game)
    objects = {field(obj, 'base.instanceId'): obj for obj in Scene(archive.read('Scene\\PlayerItemManager.scene')).objects(101)}
    entries = read('data/database.json')
    hair = [item for item in entries if item['section'] == 'Hairstyles']
    assert all(item['hairStyle'] != 23 for item in hair), 'Excluded braided ponytail returned'
    by_id = {item['id']: item for item in entries}
    old = {item['id']: item for item in read('backups/database-before-public-cleanup.json')}
    photos = read('data/hairstyle-assets.json')['photos']
    jojo = read('data/hairstyle-jojo-previews.json')
    for item in entries:
        for key in ('gameId', 'internalName', 'priceSC', 'priceJS', 'requiredLevel'):
            assert item[key] == old[item['id']][key], (item['id'], key)
    for item in hair:
        source = objects[item['gameId']]
        assert item['hairStyle'] == int(re.search(r'_(\d+)$', field(source, 'playerItem.iconMaterial'))[1]), item['id']
        assert item['hairMaterial'] == field(source, 'playerItem.clothingMaterial'), item['id']
        assert item['hairType'] and item['hairColour'] and item['hairLength'], item['id']
        if item['hairStyle'] == 33:
            assert item['image'] == jojo[item['id']]['image'], item['id']
        elif item['hairPhotoMatched']:
            assert any(photo['image'] == item['image'] and photo['model'] == item['hairStyle'] and photo['material'] == item['hairMaterial'] for photo in photos), item['id']
        else:
            assert item['image'] == item['fallbackImage'], item['id']
        assert (ROOT / item['image']).is_file(), item['id']
    for photo in photos:
        f = photo['frame']
        assert 0 <= f['x'] < f['sourceWidth'] and 0 <= f['y'] < f['sourceHeight']
        assert f['width'] > 0 and f['height'] > 0
        assert f['x'] + f['width'] <= f['sourceWidth'] and f['y'] + f['height'] <= f['sourceHeight']
    groups = read('data/catalogue-variants.json')
    for group, ids in groups.items():
        assert all(entry_id in by_id for entry_id in ids), group
        if group.startswith('hair-'):
            assert len({by_id[entry_id]['hairStyle'] for entry_id in ids}) == 1, group
    # These pairs share a material but have different game models.
    assert by_id['item-702']['variantGroup'] != by_id['item-1549']['variantGroup']
    assert by_id['item-52']['variantGroup'] != by_id['item-1995']['variantGroup']
    assert by_id['item-1995']['locations'] == ['Jarlaheim']
    assert by_id['item-8394']['locations'] == ['Dundull', 'Jorvik City Mall']
    print(f'Checked {len(hair)} hairstyles, {len(photos)} supplied portraits, {len({item["hairStyle"] for item in hair})} separate model groups and all 10 preserved JoJo pictures.')


if __name__ == '__main__':
    main()
