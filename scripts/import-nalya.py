r"""Rebuild the website catalogue from an installed Nalya Legacy client.

Usage: python scripts/import-nalya.py --game "C:\path\to\game"
All client access is read-only. Outputs and the original database backup stay
inside this website checkout. No client executables or scripts are executed.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import sys

from nalya_formats import Archive, Scene, field, hash_name, translations
from nalya_images import texture_png
from catalogue_visibility import exclusion_reason
from hairstyle_assets import hairstyle_updates
from horse_photo_corrections import horse_photo_updates

ROOT = Path(__file__).resolve().parents[1]
TYPE_NAMES = {
    0: ('Horse Appearance', 'Coats'), 1: ('Quest Items', 'Quest items'),
    2: ('Clothes', 'Tops'), 3: ('Clothes', 'Pants'), 4: ('Clothes', 'Hats'),
    5: ('Clothes', 'Gloves'), 6: ('Clothes', 'Shoes'),
    7: ('Equipment', 'Saddles'), 8: ('Equipment', 'Bridles'),
    9: ('Equipment', 'Saddle pads'), 10: ('Equipment', 'Horseshoes'),
    11: ('Services', 'Services'), 12: ('Beauty', 'Makeup'),
    13: ('Beauty', 'Hairstyles'), 14: ('Horse Appearance', 'Manes & tails'),
    15: ('Horse Decorations', 'Tail decorations'), 16: ('Horse Decorations', 'Head decorations'),
    17: ('Horse Decorations', 'Leg wraps'), 19: ('Equipment', 'Saddle bags'),
    20: ('Horses & Pets', 'Pets'), 21: ('Game Records', 'Test objects'),
    22: ('Game Records', 'Test objects'), 24: ('Player Accessories', 'Accessories'),
    25: ('Beauty', 'Bodies'), 26: ('Beauty', 'Faces'), 27: ('Beauty', 'Eyes'),
}
SEASONS = ['', 'Spring', 'Summer', 'Autumn', 'Winter', 'Christmas', 'Easter',
           'Midsummer', 'Halloween', 'New Year', "Valentine’s Day", 'Birthday']
EVENT_WORDS = {'christmas': 'Christmas', 'easter': 'Easter', 'midsummer': 'Midsummer',
               'halloween': 'Halloween', 'newyear': 'New Year', 'valentine': "Valentine’s Day",
               'birthday': 'Birthday', 'cloudkingdom': 'Cloud Kingdom', 'jojo': 'Jojo Event',
               'aprilfool': 'April Fools', 'aprilsfool': 'April Fools'}
SKILLS = {'Riding': 'itemRidingValue', 'Jumping': 'itemJumpingValue', 'Command': 'itemCommandValue',
          'Caring': 'itemCaringValue', 'Strength': 'itemStrengthValue', 'Speed': 'itemSwiftnessValue',
          'Endurance': 'itemEnduranceValue', 'Discipline': 'itemDisciplineValue', 'Agility': 'itemAgilityValue'}


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    temporary.replace(path)


def humanize(value):
    return re.sub(r'\s+', ' ', re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', str(value)).replace('_', ' ')).strip()


def events_from_names(*names):
    """Recognize event names in local display names and internal asset names."""
    normalized = [re.sub(r'[\W_]+', '', str(name or '').lower()) for name in names]
    events = {event for word, event in EVENT_WORDS.items() if any(word in name for name in normalized)}
    # Flower crowns belong to Midsummer; the candle-lit Lucia crown is Christmas.
    if any('crown' in name for name in normalized) and not any('lucia' in name for name in normalized):
        events.add('Midsummer')
    return events


def number(value):
    if value is None:
        return None
    return int(value) if value == int(value) else round(value, 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', required=True)
    parser.add_argument('--decoder-path', help='Optional directory containing texture2ddecoder for Crunch icons')
    args = parser.parse_args()
    if args.decoder_path:
        sys.path.insert(0, str(Path(args.decoder_path).resolve()))
    archive = Archive(args.game)
    print(f'Indexed {len(archive.files):,} game resources.', flush=True)
    language = translations(archive.read('Text\\TranslationEN.text'))
    language_lower = {key.lower(): value for key, value in language.items()}

    def translate(key, suffix='_Name'):
        if not isinstance(key, str) or not key:
            return ''
        return language_lower.get((key + suffix).lower(), '').strip()

    def display(key):
        return translate(key) or humanize(key)

    database_path = ROOT / 'data/database.json'
    references_path = ROOT / 'data/catalogue-image-references.json'
    if not references_path.exists():
        previous = json.loads(database_path.read_text(encoding='utf-8'))
        backup = ROOT / 'backups/database-before-nalya.json'
        backup.parent.mkdir(exist_ok=True)
        if not backup.exists():
            shutil.copyfile(database_path, backup)
        references = {'items': {}, 'horses': {}}
        for item in previous:
            image = item.get('image', '')
            match = re.search(r'/100x100sem/(\d+)\.jpg$', image)
            if match:
                references['items'][match[1]] = {'image': image, 'title': item['title']}
            elif item.get('category') == 'Horses & Pets' and item.get('breed') and image:
                references['horses'].setdefault(item['breed'].lower(), image)
        save_json(references_path, references)
    references = json.loads(references_path.read_text(encoding='utf-8'))

    objects = list(Scene(archive.read('Scene\\PlayerItemManager.scene')).objects(101))
    horses_scene = Scene(archive.read('Scene\\HorseManager.scene'))
    horses = list(horses_scene.objects(166))
    breeds = {field(obj, 'base.instanceId'): obj for obj in horses_scene.objects(192)}
    factions = {field(obj, 'base.instanceId'): obj for obj in Scene(archive.read('Scene\\FactionManager.scene')).objects(156)}
    locations = {field(obj, 'base.instanceId'): obj for obj in Scene(archive.read('Scene\\LocationManager.scene')).objects(158)}
    shop_objects = list(Scene(archive.read('Scene\\ShopManager.scene')).objects(161))
    shops_by_item = defaultdict(list)
    shops = []
    for obj in shop_objects:
        faction = factions.get(field(obj, 'shop.factionId'))
        location = locations.get(field(faction, 'faction.locationId')) if faction else None
        internal_name = field(obj, 'base.name', '')
        info = {'id': field(obj, 'base.instanceId'), 'name': display(internal_name),
                'internalName': internal_name,
                'region': display(field(location, 'base.name')) if location else None,
                'regionSource': 'Shop faction region' if location else None}
        shops.append(info)
        for key, value, kind in obj['records']:
            if key == hash_name('shopItem.playerItemId'):
                shops_by_item[value].append(info)
    shop_ids = {shop['id']: shop for shop in shops}
    for obj in objects:
        item_id = field(obj, 'base.instanceId')
        for prop in ('item.shopId', 'playerItem.shoppingMallShopId'):
            shop = shop_ids.get(field(obj, prop))
            if shop and shop not in shops_by_item[item_id]:
                shops_by_item[item_id].append(shop)

    # Resolve horse locations from actual sale placements and their scene parents.
    sale_locations = defaultdict(list)
    sale_marker = struct.pack('<III', hash_name('classId'), 167, 0xA02)
    for name, _, _, _ in archive.files.values():
        if not name.lower().endswith('.scene'):
            continue
        data = archive.read(name)
        if sale_marker not in data:
            continue
        scene_objects = list(Scene(data).objects())
        parents = {obj['objectIndex']: obj for obj in scene_objects}
        for sale in (obj for obj in scene_objects if obj['class'] == 167):
            horse_id = field(sale, 'horseForSale.id')
            ancestor = parents.get(sale['parentIndex'])
            chain, seen = [], set()
            while ancestor and ancestor['objectIndex'] not in seen:
                seen.add(ancestor['objectIndex'])
                label = field(ancestor, 'base.name', '')
                if label and label not in ['Horses', 'HorsesForSale', 'Open', 'HorseForSale', 'Root', 'HorsesToBuy', 'HorsesToBuyNew']:
                    chain.append(label)
                ancestor = parents.get(ancestor['parentIndex'])
            location_name = next((display(label) for label in chain if translate(label)), None)
            if not location_name and chain:
                location_name = humanize(chain[-1])
            scene_name = name.split('\\')[-1].replace('.scene', '').removeprefix('FO_').removeprefix('Gameplay_')
            if not location_name:
                location_name = humanize(scene_name.replace('HorsesToBuy', '').replace('Horses', ''))
            if location_name.startswith(('Resale Horse Bundles', 'Spirit Horse')):
                location_name = None
            location_name = {'Winery':'Silverglade Manor', 'At Hermit':"Hermit's Cottage",
                             'Jorvik Stable':'Jorvik Stables', 'Crecent Village':'Crescent Moon Village',
                             'Jorvi City Harbor':'Jorvik City Harbor', 'Golden Hills':'Goldenhills Valley',
                             'Vally Of The Hidden Dinosaur':'The Valley of the Hidden Dinosaur'}.get(location_name,location_name)
            info = {'name': location_name, 'source': 'Horse sale placement', 'scene': scene_name}
            if info not in sale_locations[horse_id]:
                sale_locations[horse_id].append(info)
    print(f'Read {len(objects):,} items, {len(horses)} horses and {len(shops)} shops.', flush=True)

    icon_folder = ROOT / 'assets/catalogue/icons'
    icon_folder.mkdir(parents=True, exist_ok=True)
    icons, image_errors = {}, {}

    def icon_image(material):
        if not isinstance(material, str) or not material:
            return None
        key = material.lower()
        if key in icons:
            return icons[key]
        path = icon_folder / (hashlib.sha256(key.encode()).hexdigest()[:20] + '.png')
        try:
            if not path.exists():
                path.write_bytes(texture_png(archive.read(material + '.pte')))
            icons[key] = path.relative_to(ROOT).as_posix()
        except (ValueError, KeyError, struct.error) as error:
            image_errors[material] = str(error)
            icons[key] = None
        return icons[key]

    def reputation(obj, prefix):
        faction = factions.get(field(obj, prefix + 'factionId'))
        if not faction:
            return None
        name = field(faction, 'base.name')
        return {'faction': translate(name, '_FactionName') or display(name),
                'level': field(obj, prefix + 'factionLevelRequirement', 0)}

    entries = []
    for obj in objects:
        item_id = field(obj, 'base.instanceId')
        internal = field(obj, 'base.name', '')
        item_type = field(obj, 'playerItem.type')
        category, section = TYPE_NAMES.get(item_type, ('Game Records', 'Other'))
        local_shops = shops_by_item[item_id]
        title_tag = field(obj, 'playerItem.nameTranslationTag') or internal
        description_tag = field(obj, 'playerItem.descTranslationTag') or internal
        localized = translate(title_tag)
        if localized.startswith('_'):
            localized = ''
        reference = references['items'].get(str(item_id), {})
        reference_title = reference.get('title', '')
        if reference_title.startswith('_'):
            reference_title = ''
        title = localized or reference_title or humanize(internal)
        local_icon = icon_image(field(obj, 'playerItem.iconMaterial'))
        events = set()
        season = field(obj, 'playerItem.season', 0)
        if 5 <= season < len(SEASONS):
            events.add(SEASONS[season])
        for shop in local_shops:
            for word, event in EVENT_WORDS.items():
                if word in shop['internalName'].lower():
                    events.add(event)
        stats = {label: number(field(obj, 'playerItem.' + prop)) for label, prop in SKILLS.items()
                 if field(obj, 'playerItem.' + prop)}
        currencies = []
        for slot in (1, 2):
            currency_id = field(obj, f'playerItem.itemCurrencyId{slot}', 0)
            if currency_id:
                currencies.append({'itemId': currency_id, 'count': field(obj, f'playerItem.itemCurrencyCount{slot}', 0)})
        regions = sorted({shop['region'] for shop in local_shops if shop['region']})
        entry = {'id': f'item-{item_id}', 'gameId': item_id, 'kind': 'item', 'category': category, 'section': section,
                 'title': title, 'internalName': internal, 'description': translate(description_tag, '_Desc'),
                 'image': reference.get('image') or local_icon, 'fallbackImage': local_icon,
                 'imageKind': 'Item reference' if reference.get('image') else 'Game icon' if local_icon else 'Unavailable',
                 'shops': local_shops, 'locations': regions,
                 'locationSource': 'Shop faction region' if regions else None,
                 'shop': '; '.join(shop['name'] for shop in local_shops),
                 'priceSC': number(field(obj, 'playerItem.sCPrice')), 'priceJS': number(field(obj, 'playerItem.jSPrice')),
                 'currencies': currencies, 'requiredLevel': field(obj, 'playerItem.levelRequirement'),
                 'reputation': reputation(obj, 'playerItem.'), 'events': sorted(events),
                 'season': SEASONS[season] if 0 <= season < len(SEASONS) else None,
                 'stats': stats, 'reward': bool(field(obj, 'playerItem.reward')),
                 'lockedForPurchase': bool(field(obj, 'playerItem.lockedForBuyout')),
                 'unlisted': bool((not localized and not reference_title and not local_shops) or item_type in (0, 14, 21, 22)
                                  or internal in ('NoTop', 'NoPants', 'NoHat', 'NoHands', 'NoShoes')),
                 'source': 'Nalya Legacy client'}
        entries.append(entry)

    horse_icon = icon_image('HorseIcon2')
    welsh_icon = icon_image('HorseIcon_WelshPony')
    by_game_id = {entry['gameId']: entry for entry in entries}
    for horse in horses:
        horse_id = field(horse, 'base.instanceId')
        internal = field(horse, 'base.name')
        breed = breeds.get(field(horse, 'horseForSaleData.breedId'))
        breed_key = field(breed, 'horseBreed.breed') if breed else internal
        breed_name = translate(breed_key, '_Breed') or display(breed_key)
        body_id = field(horse, 'horseForSaleData.body')
        body = by_game_id.get(body_id, {})
        image = references['horses'].get(breed_name.lower())
        places = sale_locations[horse_id]
        events = sorted({event for place in places for word, event in EVENT_WORDS.items() if word in place['scene'].lower()})
        stats = {label: number(field(horse, 'horseForSaleData.' + prop)) for label, prop in {
            'Strength': 'strengthBaseValue', 'Discipline': 'disciplineBaseValue', 'Speed': 'swiftnessBaseValue',
            'Endurance': 'enduranceBaseValue', 'Agility': 'agilityBaseValue'}.items()}
        icon = welsh_icon if 'welsh' in breed_name.lower() else horse_icon
        entry = {'id': f'horse-{horse_id}', 'gameId': horse_id, 'kind': 'horse', 'category': 'Horses & Pets',
                 'section': 'Horses', 'title': translate(internal) or breed_name, 'breed': breed_name,
                 'internalName': internal, 'variant': f'Coat {body_id}', 'bodyId': body_id,
                 'breedId': field(horse, 'horseForSaleData.breedId'),
                 'coatAsset': body.get('internalName'),
                 'description': translate(breed_key, '_Desc'), 'image': image or icon, 'fallbackImage': icon,
                 'imageKind': 'Breed reference · coat may differ' if image else 'Horse icon · coat preview unavailable',
                 'shops': [], 'shop': '; '.join(place['name'] for place in places if place['name']),
                 'locations': sorted({place['name'] for place in places if place['name']}),
                 'locationSource': 'Horse sale placement' if any(place['name'] for place in places) else None,
                 'placements': places, 'priceSC': field(horse, 'horseForSaleData.starPrice'), 'priceJS': None,
                 'currencies': [], 'requiredLevel': field(horse, 'horseForSaleData.levelRequirement'),
                 'reputation': reputation(horse, 'horseForSaleData.'), 'events': events, 'season': None,
                 'stats': stats, 'unlisted': not bool(places), 'source': 'Nalya Legacy client'}
        entries.append(entry)

    # Give token costs their real item names, never assume a zero cash price means free.
    for entry in entries:
        for cost in entry['currencies']:
            cost['name'] = by_game_id.get(cost['itemId'], {}).get('title', f"Currency item {cost['itemId']}")
    visuals_path = ROOT / 'data/catalogue-visuals.json'
    if visuals_path.exists():
        visuals = json.loads(visuals_path.read_text(encoding='utf-8'))
        for entry in entries:
            entry.update(visuals.get(entry['id'], {}))
    for entry in entries:
        entry['events'] = sorted(set(entry['events']) | events_from_names(entry['title'], entry['internalName']))
    excluded = Counter(reason for entry in entries if (reason := exclusion_reason(entry)))
    entries = [entry for entry in entries if exclusion_reason(entry) is None]
    horse_updates = horse_photo_updates(entries)
    for entry in entries:
        entry.update(horse_updates.get(entry['id'], {}))
    hair_updates, hair_groups = hairstyle_updates(entries, archive)
    for entry in entries:
        entry.update(hair_updates.get(entry['id'], {}))
    entries.sort(key=lambda entry: (entry['title'].casefold(), entry['id']))
    assert len({entry['id'] for entry in entries}) == len(entries), 'Duplicate catalogue ID'
    assert len(objects) > 5000 and len(horses) > 100, 'Incomplete source catalogue'
    metadata = {'source': 'Nalya Legacy client', 'importedAt': datetime.now(timezone.utc).isoformat(),
                'total': len(entries), 'items': sum(entry['kind'] == 'item' for entry in entries),
                'horses': sum(entry['kind'] == 'horse' for entry in entries), 'shops': len(shops),
                'sourceItems': len(objects), 'sourceHorses': len(horses), 'excluded': dict(excluded),
                'browsable': sum(not item['unlisted'] for item in entries),
                'categories': dict(Counter(entry['category'] for entry in entries)),
                'withImage': sum(bool(entry['image']) for entry in entries),
                'localIcons': sum(bool(value) for value in icons.values()),
                'withLocation': sum(bool(entry['locations']) for entry in entries),
                'eventEntries': sum(bool(entry['events']) for entry in entries),
                'imageErrors': image_errors,
                'notes': ['Client records describe this legacy build; they do not establish current live availability.',
                          'Item reference thumbnails are matched by exact game item ID.',
                          'Horse reference images show the breed and may show a different coat.',
                          'Item regions come from shop faction records; horse locations come from sale placements.',
                          'Internal assets, unlisted entries and ambassador items are excluded from the public catalogue.']}
    save_json(database_path, entries)
    save_json(ROOT / 'data/catalogue-meta.json', metadata)
    save_json(ROOT / 'data/catalogue-shops.json', shops)
    variants_path = ROOT / 'data/catalogue-variants.json'
    if variants_path.exists():
        public_ids = {entry['id'] for entry in entries}
        variants = json.loads(variants_path.read_text(encoding='utf-8'))
        variants = {group: ids for group, ids in variants.items() if not group.startswith('hair-')}
        variants.update(hair_groups)
        variants = {group: kept for group, ids in variants.items() if (kept := [entry_id for entry_id in ids if entry_id in public_ids])}
        save_json(variants_path, variants)
    print(json.dumps({key: value for key, value in metadata.items() if key not in ('imageErrors', 'notes', 'categories')}, indent=2), flush=True)
    print(f'{len(image_errors)} icons could not be converted; see data/catalogue-meta.json.', flush=True)


if __name__ == '__main__':
    main()
