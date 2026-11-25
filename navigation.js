// The compact navigation shares the same links and dropdowns as the desktop header.
(() => {
  const toggle = document.querySelector('.nav-toggle');
  const navigation = document.querySelector('.main-nav');
  const compact = window.matchMedia('(max-width: 1100px)');

  function closeNavigation(restoreFocus = false) {
    toggle.setAttribute('aria-expanded', 'false');
    toggle.querySelector('.nav-toggle-label').textContent = 'Menu';
    navigation.classList.remove('is-open');
    document.querySelectorAll('.schedule-menu-button').forEach(button => {
      button.setAttribute('aria-expanded', 'false');
      document.getElementById(button.getAttribute('aria-controls')).hidden = true;
    });
    if (restoreFocus) toggle.focus();
  }

  toggle.addEventListener('click', () => {
    const opening = toggle.getAttribute('aria-expanded') !== 'true';
    if (!opening) return closeNavigation();
    toggle.setAttribute('aria-expanded', 'true');
    toggle.querySelector('.nav-toggle-label').textContent = 'Close';
    navigation.classList.add('is-open');
  });
  navigation.addEventListener('click', event => {
    if (compact.matches && event.target.closest('a')) closeNavigation();
  });
  document.addEventListener('click', event => {
    if (compact.matches && !event.target.closest('.site-header')) closeNavigation();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
      // The first Escape closes a dropdown; the next closes the mobile navigation.
      if (!navigation.querySelector('.schedule-menu-button[aria-expanded="true"]')) {
        closeNavigation(true);
      }
    }
  }, true);
  navigation.addEventListener('focusout', () => {
    requestAnimationFrame(() => {
      if (compact.matches && !document.activeElement.closest('.site-header')) closeNavigation();
    });
  });
  compact.addEventListener('change', () => closeNavigation());
  window.addEventListener('hashchange', () => closeNavigation());
})();
