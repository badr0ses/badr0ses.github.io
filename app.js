const routeNames=['home','database','waitlist','socials','map','quests','reputation','spirit','championship','privacy'];const weekdays=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];// EDIT TEXT: Spirit table times and locations, arranged by weekday.
const spiritTimes=['8:00 AM','9:00 AM','10:00 AM','11:00 AM','12:00 PM','1:00 PM','2:00 PM','3:00 PM','4:00 PM','5:00 PM','6:00 PM','7:00 PM','8:00 PM','9:00 PM'];const spiritLocations=[['South Hoof Peninsula','Sunfield Farm','Stormgarden','Everwind Fields','Hollow Woods','Cauldron, Epona','Forgotten Fields','Everwind Fields','Seahorse Point','Greendale','Valedale Lake','Seahorse Point','Everwind Fields','Nilmer’s Highland'],['Forgotten Fields','South Hoof Peninsula','Everwind Fields','Silverglade Acres, near Marley','Golden Hills Valley','Sunfield Farm','Forgotten Fields','Goldspur','South Hoof Peninsula','Seahorse Point','Fort Pinta','Nilmer’s Highland','Moorland','Everwind Fields'],['Hollow Woods','Everwind Fields','','Dew’s Farm, Epona','South Hoof Peninsula','Hollow Woods','Firgrove','Firgrove','Firgrove','South Hoof Peninsula','Seahorse Point','Fort Pinta','Nilmer’s Highland','New Hillcrest'],['Everwind Fields','Dew’s Farm, Epona','Everwind Fields','South Hoof Peninsula','Dew’s Farm, Epona','South Hoof Peninsula','Firgrove','Firgrove','Forgotten Fields','Moorland','Moorland','Fort Pinta','Dew’s Farm, Epona','Dew’s Farm, Epona'],['Forgotten Fields','Valedale Lake','South Hoof Peninsula','Golden Hills Valley','Greendale','Fort Pinta','Seahorse Point','Sunfield Farm','Moorland','South Hoof Peninsula','Golden Hills Valley','Dew’s Farm, Epona','Fort Pinta','Riding Hall'],['Golden Hills Valley','Seahorse Point','Golden Hills Valley','Everwind Fields','Firgrove','Golden Fields','Goldspur','South Hoof Peninsula','Firgrove','Moorland','Nilmer’s Highland','Stormgarden','Silverglade Acres, near Marley','Moorland'],['Everwind Fields','Everwind Fields','Forgotten Fields','Sunfield Farm','Valedale Lake','South Hoof Peninsula','Everwind Fields','Golden Hills Valley','Golden Fields','Fort Pinta','South Hoof Peninsula','Forgotten Fields','Dew’s Farm, Epona','Moorland']];// EDIT TEXT: Championship venue names and weekly rotation start times.
const championshipRoutes=['Firgrove','Valedale','Moorland','Fort Pinta','Goldenhills','Jorvik Stables','Pony','Silverglade','New Hillcrest'];const championshipStarts=[0,8,7,6,5,4,3];const config=window.BAD_ROSES_LINKS||{};document.getElementById('year').textContent=new Date().getFullYear();document.querySelectorAll('[data-link]').forEach(link=>{const target=config[link.dataset.link];if(target){link.href=target;link.target='_blank';link.rel='noreferrer'}else{link.href='#socials';link.title='Add this link in site-config.js';link.addEventListener('click',event=>{event.preventDefault();alert('Add the live link in site-config.js to activate this button.')})}});
const reputationCatalog = document.querySelector('.reputation-catalog');

function setRoute() {
  const route = location.hash.slice(1);
  const guide = document.getElementById(route);
  const isReputationGuide = guide?.matches('.reputation-guide');
  const page = isReputationGuide ? 'reputation' : route;
  const active = routeNames.includes(page) ? page : 'home';
  const closingLink = route === 'reputation'
    ? reputationCatalog.querySelector('[aria-current="location"]')
    : null;

  document.querySelectorAll('[data-view]').forEach(view => {
    view.classList.toggle('active', view.dataset.view === active);
  });
  document.querySelectorAll('[data-route]').forEach(link => {
    if (link.dataset.route === active) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
  reputationCatalog.querySelectorAll('a').forEach(link => {
    const selected = Boolean(isReputationGuide && link.hash === location.hash);
    link.setAttribute('aria-expanded', String(selected));
    if (selected) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  });

  if (isReputationGuide) {
    guide.focus({ preventScroll: true });
    guide.scrollIntoView();
  } else if (closingLink) {
    closingLink.focus({ preventScroll: true });
    reputationCatalog.closest('.reputation-library').scrollIntoView();
  } else {
    window.scrollTo(0, 0);
  }
  if (active === 'database') renderDatabase();
}

reputationCatalog.addEventListener('click', event => {
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const link = event.target.closest('a[aria-current="location"]');
  if (!link) return;
  event.preventDefault();
  location.hash = 'reputation';
});

window.addEventListener('hashchange', setRoute);
setRoute();
function getUtcPlusOneScheduleTime() {
  const date = new Date(Date.now() + 60 * 60 * 1000);
  return {
    dayIndex: (date.getUTCDay() + 6) % 7,
    hour: date.getUTCHours(),
    secondsIntoHour: date.getUTCMinutes() * 60 + date.getUTCSeconds()
  };
}

function buildSpiritTable(){const table=document.getElementById('spirit-table');const utc=getUtcPlusOneScheduleTime();const spiritIsAvailable=utc.hour>=8&&utc.hour<21;const head=document.createElement('thead');head.innerHTML='<tr><th scope="col">Clock</th>'+weekdays.map(day=>'<th scope="col">'+day+'</th>').join('')+'</tr>';const body=document.createElement('tbody');spiritTimes.forEach((time,row)=>{const tr=document.createElement('tr');tr.innerHTML='<th scope="row">'+time+'</th>'+spiritLocations.map((day,dayIndex)=>{const isCurrent=spiritIsAvailable&&dayIndex===utc.dayIndex&&row===utc.hour-8&&Boolean(day[row]);return'<td'+(isCurrent?' class="current-location" aria-current="true"':'')+'>'+day[row]+'</td>'}).join('');body.appendChild(tr)});table.replaceChildren(head,body)}

const firstChampionshipHour = 6;
const lastChampionshipHour = 23;

function buildChampTable() {
  const table = document.getElementById('champ-table');
  const head = document.createElement('thead');
  head.innerHTML = '<tr><th scope="col">Time</th>' + weekdays.map(day => '<th scope="col">' + day + '</th>').join('') + '</tr>';
  const body = document.createElement('tbody');

  for (let hour = firstChampionshipHour; hour <= lastChampionshipHour; hour++) {
    const tr = document.createElement('tr');
    const time = String(hour).padStart(2, '0') + ':00';
    const slot = hour - firstChampionshipHour;
    const locations = championshipStarts.map(start => championshipRoutes[(start + slot) % championshipRoutes.length]);
    tr.innerHTML = '<th scope="row">' + time + '</th>' + locations.map(location => '<td>' + location + '</td>').join('');
    body.appendChild(tr);
  }

  table.append(head, body);
}

function refreshChampionshipSchedule() {
  const utc = getUtcPlusOneScheduleTime();
  const table = document.getElementById('champ-table');
  let dayIndex = utc.dayIndex;
  let hour = Math.max(firstChampionshipHour, utc.hour + 1);

  if (hour > lastChampionshipHour) {
    dayIndex = (dayIndex + 1) % weekdays.length;
    hour = firstChampionshipHour;
  }

  const hoursUntil = hour - utc.hour + (dayIndex === utc.dayIndex ? 0 : 24);
  const secondsUntil = hoursUntil * 3600 - utc.secondsIntoHour;
  const countdown = {
    hours: Math.floor(secondsUntil / 3600),
    minutes: Math.floor(secondsUntil / 60) % 60,
    seconds: secondsUntil % 60
  };
  for (const [unit, value] of Object.entries(countdown)) {
    document.getElementById('champ-countdown-' + unit).textContent = String(value).padStart(2, '0');
  }

  const row = table.tBodies[0].rows[hour - firstChampionshipHour];
  const next = row.cells[dayIndex + 1];
  if (next.hasAttribute('aria-current')) return;

  const previous = table.querySelector('.current-location');
  if (previous) {
    previous.classList.remove('current-location');
    previous.removeAttribute('aria-current');
  }

  next.classList.add('current-location');
  next.setAttribute('aria-current', 'true');
  document.getElementById('champ-next-venue').textContent = next.textContent;
  document.getElementById('champ-next-time').textContent =
    weekdays[dayIndex] + ' at ' + row.cells[0].textContent + ' UTC+1';
}

buildSpiritTable();
buildChampTable();
refreshChampionshipSchedule();
setInterval(buildSpiritTable, 15000);
setInterval(refreshChampionshipSchedule, 1000);

let database=[];let activeCategory='All collections';let visibleCount=36;const categoryList=document.getElementById('category-list');const sectionSelect=document.getElementById('section-filter');const grid=document.getElementById('item-grid');const searchInput=document.getElementById('db-search');const resultCount=document.getElementById('result-count');const sortSelect=document.getElementById('sort-filter');const loadMore=document.getElementById('load-more');const clearFilters=document.getElementById('clear-filters');const sectionNames={'Hats':'Hats','Hat':'Hats','Top':'Tops','Bridle':'Bridles','Saddle':'Saddles','Blanket':'Blankets','Horseshoe':'Horseshoes','Mask':'Masks','More':'Beards, earrings & more','Saddle Bag':'Saddle bags'};function sectionLabel(item){return sectionNames[item.section]||item.section}const categories=['All collections','Clothes','Player Accessories','Equipment','Horse Decorations','Horses & Pets'];function makeCategoryButtons(){categoryList.replaceChildren();categories.forEach(category=>{const button=document.createElement('button');button.className='category-button'+(category===activeCategory?' selected':'');button.type='button';button.setAttribute('aria-pressed',String(category===activeCategory));const count=category==='All collections'?database.length:database.filter(item=>item.category===category).length;button.innerHTML='<span>'+category+'</span><span>'+count.toLocaleString()+'</span>';button.addEventListener('click',()=>{activeCategory=category;visibleCount=36;makeCategoryButtons();updateSections();renderDatabase()});categoryList.append(button)})}function updateSections(){const current=sectionSelect.value;const sections=[...new Set(database.filter(item=>activeCategory==='All collections'||item.category===activeCategory).map(item=>item.section))].sort((a,b)=>a.localeCompare(b));sectionSelect.replaceChildren(new Option('All sections',''));sections.forEach(section=>{const item=database.find(entry=>entry.section===section&&(activeCategory==='All collections'||entry.category===activeCategory));sectionSelect.add(new Option(item?sectionLabel(item):section,section))});if(sections.includes(current))sectionSelect.value=current}function searchable(item){return [item.title,item.description,item.shop,item.category,item.section,item.breed,item.speciality,...Object.entries(item.stats||{}).flat()].filter(Boolean).join(' ').toLocaleLowerCase()}function renderDatabase(){if(!database.length)return;const query=searchInput.value.trim().toLocaleLowerCase();let matches=database.filter(item=>(activeCategory==='All collections'||item.category===activeCategory)&&(!sectionSelect.value||item.section===sectionSelect.value)&&(!query||searchable(item).includes(query)));if(sortSelect.value==='za')matches.sort((a,b)=>b.title.localeCompare(a.title));else if(sortSelect.value==='category')matches.sort((a,b)=>(a.category+' '+a.section+' '+a.title).localeCompare(b.category+' '+b.section+' '+b.title));else matches.sort((a,b)=>a.title.localeCompare(b.title));resultCount.textContent=matches.length.toLocaleString()+' entr'+(matches.length===1?'y':'ies')+(query||sectionSelect.value||activeCategory!=='All collections'?' found':' in the archive');const page=matches.slice(0,visibleCount);grid.replaceChildren();page.forEach(item=>{const card=document.createElement('article');card.className='item-card';const image=document.createElement('img');image.className='item-image';image.loading='lazy';image.alt=item.title;image.src=item.image||'assets/rose.svg';image.referrerPolicy='no-referrer';image.onerror=()=>{image.onerror=null;image.src='assets/rose.svg'};const details=document.createElement('div');const type=document.createElement('p');type.className='item-type';type.textContent=sectionLabel(item)+' · '+item.category;const title=document.createElement('h3');title.textContent=item.title;const shop=document.createElement('p');shop.className='item-shop';shop.textContent=item.shop||item.description||item.speciality||'Historical entry';details.append(type,title,shop);card.append(image,details);const stats=[];if(item.breed)stats.push('Breed: '+item.breed);if(item.speciality)stats.push(item.speciality);if(item.stats)for(const [key,value]of Object.entries(item.stats)){if(value!==null&&value!==''&&key!=='Type')stats.push(key+': '+value)}if(stats.length){const strip=document.createElement('div');strip.className='item-stats';stats.slice(0,7).forEach(stat=>{const badge=document.createElement('span');badge.textContent=stat;strip.append(badge)});card.append(strip)}if(item.description){const description=document.createElement('p');description.className='item-shop';description.textContent=item.description;card.append(description)}grid.append(card)});loadMore.hidden=page.length>=matches.length;document.getElementById('empty-state').hidden=matches.length!==0}fetch('data/database.json').then(response=>{if(!response.ok)throw Error('Database file could not be loaded');return response.json()}).then(items=>{database=items;makeCategoryButtons();updateSections();const picks=[];for(const category of ['Horses & Pets','Equipment','Clothes']){const candidate=items.find(item=>item.category===category&&item.image);if(candidate)picks.push(candidate)}const preview=document.getElementById('home-items');picks.forEach(item=>{const box=document.createElement('div');box.className='preview-item';const img=document.createElement('img');img.loading='lazy';img.src=item.image;img.alt='';img.onerror=()=>{img.onerror=null;img.src='assets/rose.svg'};const caption=document.createElement('span');caption.textContent=item.title;box.append(img,caption);preview.append(box)});resultCount.textContent=database.length.toLocaleString()+' entries in the archive';if(location.hash==='#database')renderDatabase()}).catch(()=>{resultCount.textContent='The archive could not be loaded. Open this page through GitHub Pages or a local web server.'});searchInput.addEventListener('input',()=>{visibleCount=36;renderDatabase()});sectionSelect.addEventListener('change',()=>{visibleCount=36;renderDatabase()});sortSelect.addEventListener('change',renderDatabase);loadMore.addEventListener('click',()=>{visibleCount+=36;renderDatabase()});clearFilters.addEventListener('click',()=>{activeCategory='All collections';searchInput.value='';sectionSelect.value='';sortSelect.value='az';visibleCount=36;makeCategoryButtons();updateSections();renderDatabase()});document.addEventListener('keydown',event=>{if(event.key==='/'&&document.querySelector('[data-view="database"]').classList.contains('active')&&document.activeElement!==searchInput){event.preventDefault();searchInput.focus()}});
