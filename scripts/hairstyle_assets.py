"""Match supplied hairstyle portraits to existing game models and colour materials."""
from collections import defaultdict
from pathlib import Path
import argparse
import json
import re

from nalya_formats import Archive, Scene, field

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')


def hairstyle_updates(entries, archive):
    definitions = read('data/hairstyle-colours.json')
    photos = read('data/hairstyle-assets.json')['photos']
    by_appearance = defaultdict(list)
    for photo in photos:
        by_appearance[(photo['model'], photo['material'])].append(photo)
    objects = {field(obj, 'base.instanceId'): obj for obj in Scene(archive.read('Scene\\PlayerItemManager.scene')).objects(101)}
    jojo = read('data/hairstyle-jojo-previews.json')
    places = {
        'FortPintaHairSaloon': ('Fort Pinta', 'Fort Pinta salon'),
        'FortPintaHairSaloon2': ('Fort Pinta', 'Fort Pinta salon'),
        'SilvergladeHairStyle': ('Silverglade', 'Silverglade salon'),
        'SilvergladeHairStyle2': ('Silverglade', 'Silverglade salon'),
        'WineryBarber': ('Silverglade Manor', 'Silverglade Manor salon'),
        'WineryBarber2': ('Silverglade Manor', 'Silverglade Manor salon'),
        'WineryBarber3': ('Silverglade Manor', 'Silverglade Manor salon'),
        'FishingVillageHairSaloon1': ('Cape West Fishing Village', 'Cape West Fishing Village salon'),
        'FishingVillageHairSaloon2': ('Cape West Fishing Village', 'Cape West Fishing Village salon'),
        # The supplied Salon Belle and Heavy Metal Scissors captures locate these shops.
        'VineyardSaloon': ('Jarlaheim', 'Salon Belle'),
        'RockHairSaloon': ('Jarlaheim', 'Heavy Metal Scissors'),
        'FirgroveSaloon': ('Firgrove', 'Firgrove salon'),
        'ShoppingMallHairSaloon': ('Jorvik City Mall', 'The Shieldmaiden'),
        'Dundull_BeautySalon': ('Dundull', 'The Shieldmaiden'),
        'JorvikCitysHairSaloon': ("Governor's Fall", 'Primadonna Lounge'),
    }
    updates, groups = {}, defaultdict(dict)
    for item in entries:
        if item['section'] != 'Hairstyles' or item.get('unlisted'):
            continue
        obj = objects[item['gameId']]
        icon = str(field(obj, 'playerItem.iconMaterial'))
        model = int(re.search(r'_(\d+)$', icon)[1])
        material = field(obj, 'playerItem.clothingMaterial')
        match = re.fullmatch(r'Hair_(\d+)(?:_(\d+))?', material)
        assert match, (item['id'], material)
        palette, variant = match[1], int(match[2] or 0)
        colours = definitions['palettes'][palette]
        colour = colours[str(variant)] if isinstance(colours, dict) else colours[variant]
        assert colour, (item['id'], material)
        style = definitions['styles'][str(model)]
        patch = {'title': style['name'], 'hairType': style['name'], 'hairLength': style['length'],
                 'hairStyle': model, 'hairMaterial': material, 'hairColour': colour,
                 'colorVariant': variant, 'variant': colour,
                 'description': style['name'] + ' in ' + colour.lower() + '.',
                 'variantGroup': f'hair-model-{model}', 'image': item['fallbackImage'],
                 'imageKind': 'Game hairstyle icon · colour preview unavailable',
                 'imageViews': [], 'imageFrame': None, 'hairPhotoMatched': False, 'photoSource': None}
        matches = by_appearance.get((model, material), [])
        if matches:
            patch.update(image=matches[0]['image'], imageFrame=matches[0]['frame'],
                         imageKind='Hairstyle preview', hairPhotoMatched=True,
                         photoSource='Supplied hairstyle assets')
            if len(matches) > 1:
                patch['imageViews'] = [{'label': photo['location'] + (' · view ' + str(i + 1) if sum(p['location'] == photo['location'] for p in matches) > 1 else ''), 'image': photo['image'],
                                        'location': photo['location'],
                                        'imageFrame': photo['frame'], 'imageKind': 'Hairstyle preview'}
                                       for i, photo in enumerate(matches)]
        if model == 33 and item['id'] in jojo:
            patch.update(jojo[item['id']])
        shops = []
        for original in item['shops']:
            shop = dict(original)
            if shop['internalName'] in places:
                location, name = places[shop['internalName']]
                shop.update(region=location, name=name, regionSource='Named salon or supplied salon screenshot')
            shops.append(shop)
        locations = sorted({shop['region'] for shop in shops if shop.get('region')})
        if not locations and matches:
            locations = sorted({photo['location'] for photo in matches})
        patch.update(shops=shops, locations=locations, shop='; '.join(shop['name'] for shop in shops),
                     locationSource='Salon listings and supplied salon screenshots' if locations else None)
        updates[item['id']] = patch
        # Models that share a colour texture are still distinct hairstyles.
        groups[patch['variantGroup']].setdefault(material, item['id'])
    return updates, {key: list(group.values()) for key, group in groups.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', required=True)
    args = parser.parse_args()
    entries = read('data/database.json')
    before = {item['id']: (item['priceSC'], item['priceJS'], item['requiredLevel'], item['internalName']) for item in entries}
    updates, groups = hairstyle_updates(entries, Archive(args.game))
    overlays = read('data/catalogue-visuals.json')
    for item in entries:
        if item['id'] in updates:
            item.update(updates[item['id']])
            overlays.setdefault(item['id'], {}).update(updates[item['id']])
        assert before[item['id']] == (item['priceSC'], item['priceJS'], item['requiredLevel'], item['internalName'])
    variants = {key: value for key, value in read('data/catalogue-variants.json').items() if not key.startswith('hair-')}
    variants.update(groups)
    save('data/database.json', entries)
    save('data/catalogue-visuals.json', overlays)
    save('data/catalogue-variants.json', variants)
    meta = read('data/catalogue-meta.json')
    meta.update(withImage=sum(bool(x['image']) for x in entries), withLocation=sum(bool(x['locations']) for x in entries))
    save('data/catalogue-meta.json', meta)
    report = {'hairstyles': len(updates), 'models': len(groups),
              'suppliedPortraitRecords': sum(x['photoSource'] == 'Supplied hairstyle assets' for x in updates.values()),
              'jojoPortraitRecords': sum(x['hairStyle'] == 33 and x['hairPhotoMatched'] for x in updates.values()),
              'originalIconRecords': sum(not x['hairPhotoMatched'] for x in updates.values()),
              'withLocation': sum(bool(x['locations']) for x in updates.values()),
              'unknownLocations': [key for key, x in updates.items() if not x['locations']], 'recordsAdded': 0}
    save('data/hairstyle-assets-report.json', report)
    photo_report = read('data/catalogue-photo-report.json')
    photo_report.update(hairColourPortraits=report['suppliedPortraitRecords'] + report['jojoPortraitRecords'],
                        hairSuppliedPortraits=report['suppliedPortraitRecords'], hairGameImages=report['originalIconRecords'])
    save('data/catalogue-photo-report.json', photo_report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
