"""Add reference photos only to IDs already present in the installed client.

No source website entries are added to the catalogue. Horse references require
an explicit breed/model-generation mapping. Hair and makeup previews use local game icons.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from nalya_formats import Archive, Scene, field
from hairstyle_assets import hairstyle_updates
from horse_photo_corrections import horse_photo_updates

# Client breed IDs -> SSODB breed code and model generation, never newest-by-name.
HORSE_MODELS = {
    2:(618,15),3:(664,15),4:(644,15),5:(629,10),6:(620,15),7:(638,15),
    8:(602,15),9:(643,15),10:(650,15),11:(656,15),12:(602,15),13:(606,15),
    15:(601,15),17:(609,10),18:(631,10),19:(632,10),20:(602,15),
    21:(623,10),22:(660,10),23:(647,10),24:(649,10),25:(611,10),
    26:(603,20),27:(645,20),28:(657,20),29:(698,20),30:(628,20),
    31:(644,20),32:(602,20),33:(620,20),34:(663,20),35:(602,20),
    36:(602,20),37:(606,20),38:(631,20),39:(623,20),40:(698,20),
    41:(658,20),42:(626,20),43:(609,20),44:(627,20),45:(608,20),
    46:(636,30),47:(647,30),48:(640,30),50:(633,30),51:(662,30),
}
HORSE_COLORS = {'f11':'black','f12':'grey','f13':'white','f14':'cream','f15':'chestnut',
                'f16':'light brown','f17':'brown','f18':'dark brown',
                'p21':'pinto','p22':'spotted','p23':'roan'}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', required=True)
    args=parser.parse_args()
    archive=Archive(args.game)
    local_items={field(o,'base.instanceId'):o for o in Scene(archive.read('Scene\\PlayerItemManager.scene')).objects(101)}
    entries=json.loads((ROOT/'data/database.json').read_text(encoding='utf-8'))
    original_ids={e['id'] for e in entries}
    sources={}
    for name in ['horses','hairstyles']:
        path=ROOT/f'data/ssodb-{name}-photos-source.json'
        if not path.exists():
            request=urllib.request.Request(f'https://ssodb.bplaced.net/db/en/data/db-en.{name}.json', headers={
                'User-Agent':'Mozilla/5.0','Referer':f'https://ssodb.bplaced.net/db/en/{name}.html',
                'X-Requested-With':'XMLHttpRequest','Accept':'application/json'})
            with urllib.request.urlopen(request,timeout=30) as response: source=json.load(response)
            save(path,source)
        sources[name]=json.loads(path.read_text(encoding='utf-8'))

    assets=ROOT/'assets/catalogue/photos'
    assets.mkdir(parents=True,exist_ok=True)
    jobs={}
    def photo(url):
        extension='.jpg' if url.endswith('.jpg') else '.webp'
        path=assets/(hashlib.sha256(url.encode()).hexdigest()[:24]+extension)
        jobs[url]=path
        return path.relative_to(ROOT).as_posix()

    overlays={}
    hair_groups=defaultdict(list)
    horse_groups=defaultdict(list)
    source_types=sources['hairstyles']['aoSSO']['aTypes']
    # Prefer an explicit town in a local shop name over its faction's broad region.
    # The English town labels agree with SSODB's salon location list.
    shop_places=[('fortpinta','Fort Pinta'),('moorland','Moorland'),('silvergladehair','Silverglade'),
                 ('jarlaheim','Jarlaheim'),('firgrove','Firgrove'),('fiskebyn','Cape West Fishing Village'),
                 ('governorfall',"Governor's Fall"),('dundull','Dundull'),
                 ('megaclothesshop','Jorvik City Mall'),('megagearshop','Jorvik City Mall'),
                 ('megahorsedecorationshop','Jorvik City Mall')]
    # Cache the alternate coat photos needed to compare the local texture set.
    # These are candidates only; they never become additional database entries.
    models={HORSE_MODELS[e['breedId']] for e in entries if e['kind']=='horse' and e['breedId'] in HORSE_MODELS}
    models.update({(639,20),(644,10)})
    for row in sources['horses']['aaData']:
        if (row[1],row[11]) in models and (row[1]!=698 or row[2] in (13,14)):
            photo('https://ssodb.bplaced.net/db/items/'+row[0]+'.webp')
    for index in range(1,16):
        photo(f'https://ssodb.bplaced.net/db/media/images/starthorses/starthorse{index:02d}.jpg')
    for entry in entries:
        patch={}
        if entry['kind']=='horse':
            breed_id=entry['breedId']
            model=HORSE_MODELS.get(breed_id)
            candidates=[]
            if model:
                code,generation=model
                candidates=[r for r in sources['horses']['aaData'] if r[1]==code and r[11]==generation]
                if breed_id==29:candidates=[r for r in candidates if r[2]==13] # Nixie
                if breed_id==40:candidates=[r for r in candidates if r[2]==14] # Whinfell
                # Prefer the archive photos that predate the 2018 build.
                candidates.sort(key=lambda r:(int(r[0].split('-')[-1])>1537360667,r[0]))
            if breed_id==16:
                patch={'image':photo('https://ssodb.bplaced.net/db/media/images/starthorses/starthorse01.jpg'),
                       'imageKind':'Legacy model reference · coat may differ','photoGeneration':'Gen 1.5'}
            elif candidates:
                # Explicit colour words in a local record can refine a reference;
                # the result remains labelled as a reference, not an exact coat match.
                name=entry['internalName'].lower()
                color=next((code for word,code in [('black','f11'),('grey','f12'),('white','f13'),('darkbrown','f18'),('brown','f17')]
                            if word in name),None)
                row=next((r for r in candidates if color and color in r[3].split(',')),candidates[0])
                generation=model[1]
                patch={'image':photo('https://ssodb.bplaced.net/db/items/'+row[0]+'.webp'),
                       'imageKind':'Legacy model reference · coat may differ',
                       'photoGeneration':'Gen '+str(generation/10).removesuffix('.0'),
                       'photoSource':'https://ssodb.bplaced.net/db/en/horses.html',
                       'photoModel':{'breedCode':model[0],'generation':generation,'imageId':row[0]},
                       'photoColor':', '.join(HORSE_COLORS.get(c,c) for c in row[3].split(','))}
            elif breed_id==14 and entry['gameId']!=13:
                candidates=[r for r in sources['horses']['aaData'] if r[1]==639 and r[11]==20]
                if candidates:
                    row=candidates[0]
                    patch={'image':photo('https://ssodb.bplaced.net/db/items/'+row[0]+'.webp'),
                           'imageKind':'Legacy model reference · coat may differ','photoGeneration':'Gen 2',
                           'photoSource':'https://ssodb.bplaced.net/db/en/horses.html',
                           'photoModel':{'breedCode':639,'generation':20,'imageId':row[0]}}
            else:
                # The early faux-Lipizzaner has no matching model on the source.
                patch={'image':entry['fallbackImage'],'imageKind':'Game icon · matching model photo unavailable'}
            horse_groups[breed_id].append(entry['id'])
        elif entry['section']=='Hairstyles':
            obj=local_items[entry['gameId']]
            material=field(obj,'playerItem.clothingMaterial') or entry['internalName']
            match=re.fullmatch(r'Hair_(\d+)(?:_(\d+))?',str(material))
            style=int(match[1]) if match else None
            color=int(match[2]) if match and match[2] else 0
            style_name=source_types.get(str(500+style),f'Hairstyle {style}') if style is not None else 'Hairstyle'
            # A matching website ID does not establish a matching model version.
            # Keep the original client icon, even when colours share that icon.
            patch={'image':entry['fallbackImage'],
                   'imageKind':'Original game hairstyle icon','hairStyle':style,'colorVariant':color,
                   'variant':f'Colour {color+1:02d}',
                   'title':style_name[:1].upper()+style_name[1:],
                   'description':f'{style_name[:1].upper()+style_name[1:]} — colour variant {color+1:02d}.',
                   'photoSource':None,'imageViews':[]}
            if '_Hat' in entry['internalName'] and not entry['shops']:patch['unlisted']=True
            if style is not None:hair_groups[style].append((entry['id'],str(material)))
        elif entry['section']=='Makeup':
            # Keep the original makeup previews extracted from this client.
            patch={'image':entry['fallbackImage'],'imageKind':'Game icon',
                   'imageViews':[],'photoSource':None}
        elif entry['section'] in ('Faces','Bodies','Eyes') and not entry['shops']:
            patch={'unlisted':True}
        if entry.get('shops'):
            updated_shops=[]
            changed=False
            for shop in entry['shops']:
                updated=dict(shop)
                place=next((place for token,place in shop_places if token in shop['internalName'].lower()),None)
                if place:
                    updated.update({'region':place,'regionSource':'Location in local shop name'})
                    changed=True
                updated_shops.append(updated)
            if changed:
                patch.update({'shops':updated_shops,'locations':sorted({shop['region'] for shop in updated_shops if shop['region']}),
                              'locationSource':'Local shop location; broad regions where unspecified'})
        if patch:overlays[entry['id']]=patch

    def download(job):
        url,path=job
        if path.exists() and path.stat().st_size>100:return url,None
        for attempt in range(3):
            try:
                request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0',
                    'Referer':'https://ssodb.bplaced.net/db/en/index.html'})
                with urllib.request.urlopen(request,timeout=25) as response:data=response.read()
                if not (data.startswith(b'\xff\xd8') or data[:4]==b'RIFF'):
                    raise ValueError('Response is not an image')
                path.write_bytes(data)
                return url,None
            except Exception as error:
                if attempt==2:return url,str(error)
                time.sleep(.3*(attempt+1))
    print(f'Downloading {len(jobs)} photos for existing client IDs only.',flush=True)
    errors={}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures=[pool.submit(download,job) for job in jobs.items()]
        for index,future in enumerate(as_completed(futures),1):
            url,error=future.result()
            if error:errors[url]=error
            if index%60==0 or index==len(futures):print(f'Photos checked: {index}/{len(futures)}',flush=True)
    failed={jobs[url].relative_to(ROOT).as_posix() for url in errors}
    for entry_id,patch in overlays.items():
        if patch.get('image') in failed:
            patch.pop('image',None)
            patch['imageKind']='Game preview'
        if patch.get('imageViews'):
            patch['imageViews']=[v for v in patch['imageViews'] if v['image'] not in failed]
    by_id={entry['id']:entry for entry in entries}
    for entry_id,patch in overlays.items():by_id[entry_id].update(patch)
    galleries={}
    for style,group in hair_groups.items():
        unique={}
        for entry_id,material in group:
            entry=by_id[entry_id]
            if entry.get('unlisted') or '_Free' in entry['internalName']:continue
            unique.setdefault(material,entry_id)
        ids=sorted(unique.values(),key=lambda entry_id:by_id[entry_id].get('colorVariant',0))
        galleries[f'hair-{style}']=ids
        for entry_id,_ in group:overlays[entry_id]['variantGroup']=f'hair-{style}'
    for breed,ids in horse_groups.items():
        unique={}
        for entry_id in ids:unique.setdefault(by_id[entry_id]['bodyId'],entry_id)
        galleries[f'horse-{breed}']=list(unique.values())
        for entry_id in ids:overlays.setdefault(entry_id,{})['variantGroup']=f'horse-{breed}'
    hair_updates, hair_galleries = hairstyle_updates(entries, archive)
    for entry_id, patch in hair_updates.items():
        overlays.setdefault(entry_id, {}).update(patch)
        by_id[entry_id].update(patch)
    galleries = {key: ids for key, ids in galleries.items() if not key.startswith('hair-')}
    galleries.update(hair_galleries)
    assert original_ids==set(by_id), 'Source website must never add catalogue records'
    for entry_id, patch in horse_photo_updates(entries).items():
        overlays.setdefault(entry_id, {}).update(patch)
        by_id[entry_id].update(patch)
    save(ROOT/'data/catalogue-visuals.json',overlays)
    save(ROOT/'data/catalogue-variants.json',galleries)
    save(ROOT/'data/catalogue-photo-report.json',{'recordsAdded':0,'clientIds':len(original_ids),
        'horsePhotos':sum(e['kind']=='horse' and e.get('image','').startswith('assets/catalogue/photos/') for e in by_id.values()),
        'horseSuppliedScreenshots':sum(e['kind']=='horse' and e['imageKind']=='In-game screenshot' for e in by_id.values()),
        'hairPhotos':sum(e['section']=='Hairstyles' and e.get('image','').startswith('assets/catalogue/photos/') for e in by_id.values()),
        'hairGameImages':sum(e['section']=='Hairstyles' and e.get('image')==e.get('fallbackImage') for e in by_id.values()),
        'makeupGameImages':sum(e['section']=='Makeup' and e.get('image')==e.get('fallbackImage') for e in by_id.values()),
        'downloadErrors':errors})
    print(f'Added no records. Prepared {len(overlays)} photo updates; {len(errors)} downloads unavailable.',flush=True)


if __name__=='__main__':main()
