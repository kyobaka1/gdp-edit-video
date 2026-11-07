(() => {
  if (window.GDPTheme) return;

  const STORAGE_KEY = 'gdp-theme';
  const root = document.documentElement;

  function getPreferred() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'dark' || stored === 'light') return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function apply(theme) {
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
    root.dataset.theme = theme;
    updateIcons(theme);
  }

  function updateIcons(theme) {
    const sunEls = document.querySelectorAll('.gdp-icon-sun');
    const moonEls = document.querySelectorAll('.gdp-icon-moon');
    sunEls.forEach(el => el.classList.toggle('hidden', theme === 'light'));
    moonEls.forEach(el => el.classList.toggle('hidden', theme === 'dark'));
  }

  function toggle() {
    const current = root.classList.contains('dark') ? 'dark' : 'light';
    const next = current === 'dark' ? 'light' : 'dark';
    localStorage.setItem(STORAGE_KEY, next);
    apply(next);
  }

  function init() {
    const theme = getPreferred();
    apply(theme);

    document.querySelectorAll('#gdpThemeToggle').forEach(btn => {
      if (btn.dataset.gdpBound === '1') return;
      btn.dataset.gdpBound = '1';
      btn.addEventListener('click', toggle);
    });

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
      if (!localStorage.getItem(STORAGE_KEY)) {
        apply(e.matches ? 'dark' : 'light');
      }
    });
  }

  window.GDPTheme = { init, toggle, apply, getPreferred };
  document.addEventListener('DOMContentLoaded', init);
  document.addEventListener('nav:done', () => {
    const theme = root.classList.contains('dark') ? 'dark' : 'light';
    updateIcons(theme);
    document.querySelectorAll('#gdpThemeToggle').forEach(btn => {
      if (btn.dataset.gdpBound === '1') return;
      btn.dataset.gdpBound = '1';
      btn.addEventListener('click', toggle);
    });
  });
})();
