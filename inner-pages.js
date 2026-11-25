// Choose a readable day view without changing the underlying schedule or its clock.
(() => {
  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const compactSchedules = window.matchMedia('(max-width: 900px)');
  for (const tableId of ['spirit-table', 'champ-table']) {
    const table = document.getElementById(tableId);
    if (!table) continue;
    const controls = document.createElement('div');
    controls.className = 'schedule-days';
    controls.setAttribute('role', 'group');
    controls.setAttribute('aria-label', tableId === 'spirit-table' ? 'Spirit schedule day' : 'Championship schedule day');
    const summary = document.createElement('p');
    summary.className = 'schedule-selection';
    summary.setAttribute('aria-live', 'polite');
    summary.textContent = 'All week · UTC+1';

    const labels = ['All week', ...days];
    let selectedManually = false;
    function selectDay(index) {
      controls.querySelectorAll('button').forEach((item, buttonIndex) => item.setAttribute('aria-pressed', String(buttonIndex === index)));
      if (index === 0) table.removeAttribute('data-selected-day');
      else table.dataset.selectedDay = String(index - 1);
      summary.textContent = labels[index] + ' · UTC+1';
      table.closest('.table-scroll').scrollLeft = 0;
    }
    function selectDefaultDay() {
      const utcPlusOne = new Date(Date.now() + 60 * 60 * 1000);
      const todayIndex = (utcPlusOne.getUTCDay() + 6) % 7;
      selectDay(compactSchedules.matches ? todayIndex + 1 : 0);
    }
    labels.forEach((label, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = label;
      button.setAttribute('aria-controls', tableId);
      button.setAttribute('aria-pressed', String(index === 0));
      button.addEventListener('click', () => {
        selectedManually = true;
        selectDay(index);
      });
      controls.append(button);
    });
    const scroller = table.closest('.table-scroll');
    scroller.tabIndex = 0;
    scroller.setAttribute('role', 'region');
    scroller.setAttribute('aria-label', tableId === 'spirit-table' ? 'Spirit timetable' : 'Championship timetable');
    scroller.before(controls, summary);
    selectDefaultDay();
    compactSchedules.addEventListener('change', () => {
      if (!selectedManually) selectDefaultDay();
    });
  }
})();
