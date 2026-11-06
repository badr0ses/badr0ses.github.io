// BEAUTY DATABASE IMPORT: Converts saved the game Database rows into this site's database format.
import {readFile,writeFile} from 'node:fs/promises';

const root=new URL('../',import.meta.url);
const readJson=async path=>JSON.parse(await readFile(new URL(path,root),'utf8'));
const numberOrNull=value=>value&&value!=='-'?Number(value):null;
const cleanShop=value=>value.replaceAll('▪','').replace(/\s*\n\s*/g,'; ').replace(/\s{2,}/g,' ').trim();

const database=await readJson('data/database.json');
const makeupRows=await readJson('data/ssodb-makeup-raw.json');
const hairstyleRows=await readJson('data/ssodb-hairstyles-raw.json');

const makeup=makeupRows.map(row=>{
  const image=row.images[0];
  const id=image.match(/makeup_(\d+)\.webp$/)?.[1]||'Unknown';
  return{
    category:'Beauty',
    section:'Makeup',
    title:`Makeup ${id}`,
    description:row.cells[5].replace(/\s*\n\s*/g,', ').trim()||'Makeup look',
    image,
    images:row.images,
    shop:cleanShop(row.cells[6]),
    stats:{JS:numberOrNull(row.cells[3]),SC:numberOrNull(row.cells[4])},
    source:'https://ssodb.bplaced.net/db/en/makeup.html'
  };
});

const hairstyles=hairstyleRows.map((row,index)=>{
  const style=row.cells[1].trim();
  const colour=row.cells[2].replace(/^,\s*/,'').trim();
  return{
    category:'Beauty',
    section:'Hairstyles',
    title:`${style.charAt(0).toUpperCase()+style.slice(1)} — ${colour||`style ${index+1}`}`,
    description:`Style: ${style}. Colour: ${colour||'not listed'}.`,
    image:row.images[0],
    shop:cleanShop(row.cells[5]),
    stats:{JS:numberOrNull(row.cells[3]),SC:numberOrNull(row.cells[4])},
    source:'https://ssodb.bplaced.net/db/en/hairstyles.html'
  };
});

const merged=[...database.filter(item=>item.category!=='Beauty'),...makeup,...hairstyles];
await writeFile(new URL('data/database.json',root),`${JSON.stringify(merged,null,2)}\n`,'utf8');
console.log(`Database now contains ${merged.length} entries, including ${makeup.length} makeup looks and ${hairstyles.length} hairstyles.`);
