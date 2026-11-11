"""Match distinct legacy-model coat photos to existing local body records.

The candidate pool is restricted by the explicit model-generation crosswalk.
An assignment uses local coat textures, image colour/pattern features and
available source metadata. The UI keeps the images labelled as references.
"""
from pathlib import Path
from collections import defaultdict, Counter
from functools import lru_cache
import colorsys
import hashlib
import importlib.util
import json
import math
import sys
import shutil
import argparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tmp/nalya-tools'))
from PIL import Image,ImageDraw
from nalya_formats import Archive, Scene, field
from nalya_images import texture_png
from horse_photo_corrections import horse_photo_updates

spec=importlib.util.spec_from_file_location('catalogue_photos',ROOT/'scripts/import-catalogue-photos.py')
photos=importlib.util.module_from_spec(spec)
spec.loader.exec_module(photos)


def asset(url):
    ext='.jpg' if url.endswith('.jpg') else '.webp'
    return 'assets/catalogue/photos/'+hashlib.sha256(url.encode()).hexdigest()[:24]+ext


def features(path,texture=False,magic=False):
    image=Image.open(path).convert('RGB')
    w,h=image.size
    if texture:
        image=image.crop((int(w*.04),int(h*.13),int(w*.96),int(h*.96)))
    else:
        image=image.crop((int(w*.22),int(h*.32),int(w*.73),int(h*.68)))
    image=image.resize((48,48),Image.Resampling.BILINEAR)
    pixels=list(image.get_flattened_data())
    common=Counter(pixels).most_common(1)[0]
    hist=[0.0]*28
    values=[];saturations=[];reds=[];greens=[];blues=[]
    for r,g,b in pixels:
        if texture and common[1]>len(pixels)*.04 and (r,g,b)==common[0]:continue
        hue,sat,val=colorsys.rgb_to_hsv(r/255,g/255,b/255)
        if not texture and not magic and sat>.28 and (g>r*1.13 and g>b*1.06 or b>r*1.35 and b>g*1.12):continue
        light=0 if val<.18 else 1 if val<.4 else 2 if val<.67 else 3
        if sat<.19:
            index=light
        else:
            huebin=0 if hue<.065 or hue>=.96 else 1 if hue<.17 else 2 if hue<.42 else 3 if hue<.58 else 4 if hue<.75 else 5
            index=4+huebin*4+light
        hist[index]+=1
        values.append(val);saturations.append(sat)
        total=r+g+b+1
        reds.append(r/total);greens.append(g/total);blues.append(b/total)
    count=sum(hist) or 1
    hist=[v/count for v in hist]
    average=lambda values:sum(values)/len(values) if values else 0
    return hist+[average(values),average(saturations),average(reds),average(greens),average(blues)]


def distance(a,b):
    histogram=sum((x-y)**2/(x+y+.04) for x,y in zip(a[:28],b[:28]))
    return histogram+sum(abs(a[i]-b[i])*weight for i,weight in [(28,.5),(29,.35),(30,1),(31,1),(32,1)])


def assign(cost):
    n,m=len(cost),len(cost[0])
    if n>m:raise ValueError(f'{n} local coats but only {m} source photos')
    @lru_cache(None)
    def solve(row,used):
        if row==n:return 0.0,()
        best=(float('inf'),())
        for column in range(m):
            if used&(1<<column):continue
            tail,assignment=solve(row+1,used|(1<<column))
            candidate=(cost[row][column]+tail,(column,)+assignment)
            if candidate[0]<best[0]:best=candidate
        return best
    return solve(0,0)[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',help='Read-only client directory; needed to create a fresh coat-texture cache')
    args=parser.parse_args()
    entries=json.loads((ROOT/'data/database.json').read_text(encoding='utf-8'))
    texture_folder=ROOT/'tmp/coat-matching/textures'
    texture_folder.mkdir(parents=True,exist_ok=True)
    missing={entry['bodyId'] for entry in entries if entry['kind']=='horse' and not (texture_folder/f'{entry["bodyId"]}.png').exists()}
    if missing:
        if not args.game:raise ValueError('Supply --game to decode the local coat textures')
        archive=Archive(args.game)
        items={field(obj,'base.instanceId'):obj for obj in Scene(archive.read('Scene\\PlayerItemManager.scene')).objects(101)}
        for body_id in missing:
            material=field(items[body_id],'playerItem.clothingMaterial')
            (texture_folder/f'{body_id}.png').write_bytes(texture_png(archive.read(material+'.pte')))
    source=json.loads((ROOT/'data/ssodb-horses-photos-source.json').read_text(encoding='utf-8'))
    overlays=json.loads((ROOT/'data/catalogue-visuals.json').read_text(encoding='utf-8'))
    groups=defaultdict(dict)
    for entry in entries:
        if entry['kind']!='horse':continue
        breed=entry['breedId']
        if breed==16:key=('starter',15,0)
        elif breed==14 and entry['gameId']!=13:key=(639,20,0)
        elif breed in photos.HORSE_MODELS:
            code,generation=photos.HORSE_MODELS[breed]
            key=(code,generation,13 if breed==29 else 14 if breed==40 else 0)
        else:continue
        groups[key].setdefault(entry['bodyId'],entry)
    matches=[];problems=[]
    # Some early records share a body asset across breeds. Reuse a photograph
    # already matched to that exact body instead of assigning it a different coat.
    viable_bodies=set()
    for (code,generation,subtype),local in groups.items():
        count=15 if code=='starter' else sum(r[1]==code and r[11]==generation and (not subtype or r[2]==subtype) for r in source['aaData'])
        if len(local)<=count:viable_bodies.update(local)
    for (code,generation,subtype),local in groups.items():
        if code=='starter':
            candidates=[{'image':asset(f'https://ssodb.bplaced.net/db/media/images/starthorses/starthorse{i:02d}.jpg'),
                         'imageId':f'starter-{i:02d}','color':'','price':None} for i in range(1,16)]
        else:
            candidates=[{'image':asset('https://ssodb.bplaced.net/db/items/'+row[0]+'.webp'),
                         'imageId':row[0],'color':row[3],'price':row[4]}
                        for row in source['aaData'] if row[1]==code and (row[11]==generation or code==644 and generation==15 and row[11]==10) and (not subtype or row[2]==subtype)]
        candidates=[c for c in candidates if (ROOT/c['image']).is_file()]
        records=list(local.values())
        if len(candidates)<len(records):
            records=[record for record in records if record['bodyId'] not in viable_bodies]
            if not records:continue
        texture_features=[features(ROOT/f'tmp/coat-matching/textures/{e["bodyId"]}.png',True,code==698) for e in records]
        photo_features=[features(ROOT/c['image'],False,code==698) for c in candidates]
        costs=[]
        for e,feature in zip(records,texture_features):
            row=[]
            for candidate,target in zip(candidates,photo_features):
                score=distance(feature,target)
                name=e['internalName'].lower()
                explicit=next((color for word,color in [('darkbrown','f18'),('black','f11'),('white','f13'),('grey','f12'),('brown','f17')]
                               if word in name),None)
                if explicit and explicit not in candidate['color'].split(','):score+=.65
                # A rare unique cash-price match provides secondary evidence;
                # historical sale prices are otherwise allowed to differ.
                if candidate['price']==e['priceSC'] and sum(c['price']==e['priceSC'] for c in candidates)==1:score-=.15
                row.append(score)
            costs.append(row)
        if len(records)>len(candidates):
            shortage=len(records)-len(candidates)
            for entry,row in zip(records,costs):
                # A non-sale prototype should retain its actual game texture
                # instead of taking a real sale coat's reference photograph.
                penalty=.45 if entry['unlisted'] else 1.9
                row.extend([penalty]*shortage)
        selected=assign(costs)
        for row,column in enumerate(selected):
            entry=records[row]
            if column>=len(candidates):
                target=ROOT/f'assets/catalogue/photos/game-coat-{entry["bodyId"]}.png'
                shutil.copyfile(ROOT/f'tmp/coat-matching/textures/{entry["bodyId"]}.png',target)
                candidate={'image':target.relative_to(ROOT).as_posix(),'imageId':f'game-texture-{entry["bodyId"]}','color':''}
                problems.append({'bodyId':entry['bodyId'],'reason':'No matching source coat photo; kept the real game texture'})
            else:candidate=candidates[column]
            matches.append({'bodyId':entry['bodyId'],'gameId':entry['gameId'],'breedId':entry['breedId'],
                            'model':[code,generation,subtype],'image':candidate['image'],
                            'imageId':candidate['imageId'],'colorCodes':candidate['color'],
                            'score':round(costs[row][column],4)})
    # Manual visual QA corrections are explicit and preserved between runs.
    corrections_path=ROOT/'data/catalogue-coat-corrections.json'
    corrections=json.loads(corrections_path.read_text(encoding='utf-8')) if corrections_path.exists() else {}
    by_body={match['bodyId']:match for match in matches}
    for body, image_id in corrections.items():
        match=by_body[int(body)]
        match['imageId']=image_id
        match['image']=asset('https://ssodb.bplaced.net/db/items/'+image_id+'.webp') if not image_id.startswith('starter-') else asset(f'https://ssodb.bplaced.net/db/media/images/starthorses/starthorse{image_id[-2:]}.jpg')
    for entry in entries:
        if entry['kind']!='horse' or entry['bodyId'] not in by_body:continue
        match=by_body[entry['bodyId']]
        color=', '.join(photos.HORSE_COLORS.get(code,code) for code in match['colorCodes'].split(',') if code)
        overlays.setdefault(entry['id'],{}).update({'image':match['image'],
            'imageKind':'Game coat texture · photo unavailable' if match['imageId'].startswith('game-texture-') else 'Legacy coat photo reference','photoColor':color,
            'variant':color[:1].upper()+color[1:] if color else entry['variant'],
            'photoMatch':'Local coat texture and legacy model','photoBodyId':entry['bodyId'],
            'photoModel':{'breedCode':match['model'][0],'generation':match['model'][1],'imageId':match['imageId']}})
    for entry_id, patch in horse_photo_updates(entries).items():
        overlays.setdefault(entry_id, {}).update(patch)
    photos.save(ROOT/'data/catalogue-visuals.json',overlays)
    photos.save(ROOT/'data/catalogue-coat-matches.json',{'matches':matches,'unmatchedModels':problems})
    effective=[dict(entry,**overlays.get(entry['id'],{})) for entry in entries]
    photos.save(ROOT/'data/catalogue-photo-report.json',{
        'recordsAdded':0,'records':len(entries),
        'horsesWithPhotos':sum(entry['kind']=='horse' and '/photos/' in (entry['image'] or '') and entry['image'].endswith(('.jpg','.webp')) for entry in effective),
        'horseSuppliedScreenshots':sum(entry['kind']=='horse' and entry['imageKind']=='In-game screenshot' for entry in effective),
        'hairColourPortraits':sum(entry['section']=='Hairstyles' and '/photos/' in (entry['image'] or '') for entry in effective),
        'makeupRecordsWithViews':sum(bool(entry.get('imageViews')) for entry in effective),
        'gameCoatTextureFallbacks':[entry['id'] for entry in effective if entry['kind']=='horse' and 'Game coat texture' in entry['imageKind']]})
    # Contact sheets pair every local texture with its proposed photo for QA.
    out=ROOT/'tmp/coat-matching';out.mkdir(exist_ok=True)
    for page in range((len(matches)+29)//30):
        selected=matches[page*30:(page+1)*30]
        sheet=Image.new('RGB',(1000,((len(selected)+3)//4)*132),'#ede7e1')
        draw=ImageDraw.Draw(sheet)
        for i,match in enumerate(selected):
            x=(i%4)*250;y=(i//4)*132
            for offset,path in [(0,ROOT/f'tmp/coat-matching/textures/{match["bodyId"]}.png'),(120,ROOT/match['image'])]:
                image=Image.open(path).convert('RGB');image.thumbnail((118,109));sheet.paste(image,(x+offset,y))
            draw.text((x+3,y+111),f'{match["gameId"]} body {match["bodyId"]} / {match["score"]}',fill='black')
        sheet.save(out/f'pairs-{page+1}.jpg')
    print(f'Matched {len(matches)} distinct local coat textures. Insufficient source pools: {problems}',flush=True)


if __name__=='__main__':main()
