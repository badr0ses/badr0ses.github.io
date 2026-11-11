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
