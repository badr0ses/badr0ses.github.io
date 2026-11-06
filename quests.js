const reduceQuestMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function openQuest(entry){
  entry.getAnimations().forEach(animation=>animation.cancel());
  entry.style.removeProperty('overflow');
  entry.removeAttribute('hidden');
}

function hideQuest(entry){
  entry.getAnimations().forEach(animation=>animation.cancel());
  entry.style.removeProperty('overflow');
  entry.setAttribute('hidden','');
}

function closeQuest(entry){
  if(entry.hasAttribute('hidden'))return;
  entry.getAnimations().forEach(animation=>animation.cancel());
  if(reduceQuestMotion){
    entry.setAttribute('hidden','');
    return;
  }
  entry.style.overflow='hidden';
  const animation=entry.animate([
    {height:entry.offsetHeight+'px',opacity:1,transform:'translateY(0)'},
    {height:'0px',opacity:0,transform:'translateY(-10px)'}
  ],{duration:320,easing:'cubic-bezier(.4,0,.2,1)'});
  animation.onfinish=()=>{
    entry.setAttribute('hidden','');
    entry.style.removeProperty('overflow');
    animation.cancel();
  };
}

document.addEventListener('click',event=>{
  const button=event.target.closest('[data-quest-target]');
  if(!button)return;
  const target=document.getElementById(button.dataset.questTarget);
  if(!target)return;
  const closing=!target.hasAttribute('hidden')&&button.getAttribute('aria-pressed')==='true';
  if(closing){
    closeQuest(target);
    button.setAttribute('aria-pressed','false');
    button.setAttribute('aria-expanded','false');
    return;
  }
  document.querySelectorAll('.quest-entry').forEach(entry=>{
    if(entry===target)openQuest(entry);
    else hideQuest(entry);
  });
  document.querySelectorAll('[data-quest-target]').forEach(item=>{
    const selected=item===button;
    item.setAttribute('aria-pressed',String(selected));
    item.setAttribute('aria-expanded',String(selected));
  });
  requestAnimationFrame(()=>target.scrollIntoView({behavior:reduceQuestMotion?'auto':'smooth',block:'start'}));
});
