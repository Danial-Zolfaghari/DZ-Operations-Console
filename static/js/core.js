const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

window.apiFetch = async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  const method = (options.method || 'GET').toUpperCase();
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  if (!['GET', 'HEAD'].includes(method)) headers.set('X-CSRF-Token', csrfToken);

  const response = await fetch(url, { ...options, headers, credentials: 'same-origin' });
  if (response.status === 401) {
    location.href = '/login';
    throw new Error('Your session has expired. Please sign in again.');
  }

  const contentType = response.headers.get('content-type') || '';
  const body = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) throw new Error(body?.error || body || `Request failed with status ${response.status}`);
  return body;
};

window.toast = function toast(message, type = '') {
  const root = document.getElementById('toastStack');
  if (!root) return;
  const item = document.createElement('div');
  item.className = `toast ${type}`;
  item.textContent = message;
  root.appendChild(item);
  setTimeout(() => item.remove(), 4200);
};

function tickClock() {
  const el = document.getElementById('clock');
  if (el) el.textContent = new Date().toLocaleTimeString('en-GB', { hour12: false });
}
tickClock();
setInterval(tickClock, 1000);

const sidebar = document.getElementById('sidebar');
const backdrop = document.getElementById('mobileBackdrop');
const sidebarToggle = document.getElementById('sidebarToggle');
const SIDEBAR_KEY = 'dz.sidebar.collapsed';
const DESKTOP_NAV_QUERY = '(min-width: 1081px)';

function readSidebarPreference() {
  try { return localStorage.getItem(SIDEBAR_KEY); } catch (_) { return null; }
}

function writeSidebarPreference(collapsed) {
  try { localStorage.setItem(SIDEBAR_KEY, collapsed ? '1' : '0'); } catch (_) { /* Storage may be unavailable in hardened/private contexts. */ }
}

function isDesktopNavigation() {
  return window.matchMedia(DESKTOP_NAV_QUERY).matches;
}

function syncSidebarToggle() {
  if (!sidebarToggle) return;
  const desktopCollapsed = document.body.classList.contains('sidebar-collapsed');
  const mobileOpen = sidebar?.classList.contains('open');
  const expanded = isDesktopNavigation() ? !desktopCollapsed : Boolean(mobileOpen);
  sidebarToggle.setAttribute('aria-expanded', String(expanded));
  sidebarToggle.setAttribute('aria-label', isDesktopNavigation()
    ? (desktopCollapsed ? 'Expand navigation' : 'Collapse navigation')
    : (mobileOpen ? 'Close navigation' : 'Open navigation'));
  sidebarToggle.title = sidebarToggle.getAttribute('aria-label');
}

function closeSidebarDrawer() {
  sidebar?.classList.remove('open');
  backdrop?.classList.remove('show');
  syncSidebarToggle();
}

function applyStoredSidebarState() {
  if (isDesktopNavigation()) {
    closeSidebarDrawer();
    document.body.classList.toggle('sidebar-collapsed', readSidebarPreference() === '1');
  } else {
    document.body.classList.remove('sidebar-collapsed');
  }
  syncSidebarToggle();
}

sidebarToggle?.addEventListener('click', () => {
  if (isDesktopNavigation()) {
    const collapsed = !document.body.classList.contains('sidebar-collapsed');
    document.body.classList.toggle('sidebar-collapsed', collapsed);
    writeSidebarPreference(collapsed);
    closeSidebarDrawer();
    syncSidebarToggle();
    return;
  }

  const open = !sidebar?.classList.contains('open');
  sidebar?.classList.toggle('open', open);
  backdrop?.classList.toggle('show', open);
  syncSidebarToggle();
});

backdrop?.addEventListener('click', closeSidebarDrawer);
window.addEventListener('resize', applyStoredSidebarState);
applyStoredSidebarState();
