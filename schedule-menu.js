// NAVIGATION DROPDOWNS: Change the shared Quests/Rep and Schedules dropdown behavior here.
(()=>{
  const dropdowns=[...document.querySelectorAll('.schedule-dropdown')];
  if(!dropdowns.length)return;

  function closeDropdown(dropdown,restoreFocus=false){
    const button=dropdown.querySelector('.schedule-menu-button');
    const menu=dropdown.querySelector('.schedule-menu');
    button.setAttribute('aria-expanded','false');
    menu.hidden=true;
    if(restoreFocus)button.focus();
  }

  function closeAll(except=null){
    dropdowns.forEach(dropdown=>{
      if(dropdown!==except)closeDropdown(dropdown);
    });
  }

  function positionMenu(dropdown){
    const button=dropdown.querySelector('.schedule-menu-button');
    const menu=dropdown.querySelector('.schedule-menu');
    const rect=button.getBoundingClientRect();
    const width=menu.offsetWidth||205;
    menu.style.top=`${Math.round(rect.bottom+6)}px`;
    menu.style.left=`${Math.round(Math.max(12,Math.min(rect.left,window.innerWidth-width-12)))}px`;
  }

  function openDropdown(dropdown){
    closeAll(dropdown);
    const button=dropdown.querySelector('.schedule-menu-button');
    const menu=dropdown.querySelector('.schedule-menu');
    menu.hidden=false;
    button.setAttribute('aria-expanded','true');
    positionMenu(dropdown);
  }

  function updateActiveStates(){
    dropdowns.forEach(dropdown=>{
      const button=dropdown.querySelector('.schedule-menu-button');
      const active=dropdown.querySelector('[data-route][aria-current="page"]');
      if(active)button.setAttribute('aria-current','page');
      else button.removeAttribute('aria-current');
    });
  }

  dropdowns.forEach(dropdown=>{
    const button=dropdown.querySelector('.schedule-menu-button');
    const menu=dropdown.querySelector('.schedule-menu');
    button.addEventListener('click',()=>{
      if(menu.hidden)openDropdown(dropdown);
      else closeDropdown(dropdown);
    });
    menu.addEventListener('click',event=>{
      if(event.target.closest('a'))closeDropdown(dropdown);
    });
  });

  document.addEventListener('click',event=>{
    if(!event.target.closest('.schedule-dropdown'))closeAll();
  });
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'){
      const openDropdownElement=dropdowns.find(dropdown=>!dropdown.querySelector('.schedule-menu').hidden);
      if(openDropdownElement)closeDropdown(openDropdownElement,true);
    }
  });
  window.addEventListener('resize',()=>closeAll());
  window.addEventListener('scroll',()=>closeAll(),{passive:true});
  window.addEventListener('hashchange',updateActiveStates);
  updateActiveStates();
})();
