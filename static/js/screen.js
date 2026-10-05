const img = document.getElementById('screenImage');
const stage = document.getElementById('screenStage');
const mouseBtn = document.getElementById('toggleMouse');
const keyboardBtn = document.getElementById('toggleKeyboard');
const fullscreenBtn = document.getElementById('toggleFullscreen');
const mouseLabel = document.getElementById('mouseLabel');
const keyboardLabel = document.getElementById('keyboardLabel');
const fullscreenLabel = document.getElementById('fullscreenLabel');
const statusEl = document.getElementById('screenStatus');
const hint = document.getElementById('screenHint');

let mouseEnabled = false;
let keyboardEnabled = false;
let fullscreenFallback = false;
let capabilities = { mouse: null, keyboard: null, message: 'Checking desktop input availability…' };
let probePromise = null;
let moveBusy = false;
let lastMove = 0;
let lastMoveErrorToast = 0;
let lastKeyErrorToast = 0;

function isFullscreen() {
  return document.fullscreenElement === stage || fullscreenFallback;
}

function statusText() {
  if (capabilities.mouse === null || capabilities.keyboard === null) return 'Checking desktop input availability…';
  if (!capabilities.mouse && !capabilities.keyboard) return 'Live stream · input unavailable';
  if (mouseEnabled || keyboardEnabled) return 'Live stream · remote input enabled';
  return 'Live stream · input ready';
}

function refreshControls() {
  mouseLabel.textContent = `Mouse: ${mouseEnabled ? 'On' : 'Off'}`;
  keyboardLabel.textContent = `Keyboard: ${keyboardEnabled ? 'On' : 'Off'}`;
  fullscreenLabel.textContent = isFullscreen() ? 'Exit fullscreen' : 'Fullscreen';
  mouseBtn.classList.toggle('active', mouseEnabled);
  keyboardBtn.classList.toggle('active', keyboardEnabled);
  stage.classList.toggle('mouse-control-active', mouseEnabled);
  stage.classList.toggle('fullscreen', fullscreenFallback);
  hint.style.display = (mouseEnabled || keyboardEnabled) ? 'none' : 'block';
  statusEl.textContent = statusText();
}

function normalized(event) {
  const rect = img.getBoundingClientRect();
  if (!rect.width || !rect.height) return null;
  return {
    x: (event.clientX - rect.left) / rect.width,
    y: (event.clientY - rect.top) / rect.height,
  };
}

async function probeControls({ notify = false } = {}) {
  if (probePromise) return probePromise;
  probePromise = (async () => {
    try {
      const data = await apiFetch('/api/control/probe');
      capabilities = {
        mouse: Boolean(data?.mouse),
        keyboard: Boolean(data?.keyboard),
        message: data?.message || 'Desktop input capability check completed.',
      };
      refreshControls();
      if (notify) toast(capabilities.message, capabilities.mouse || capabilities.keyboard ? 'success' : 'error');
      return capabilities;
    } catch (error) {
      capabilities = {
        mouse: false,
        keyboard: false,
        message: error.message || 'Unable to check desktop input availability.',
      };
      refreshControls();
      if (notify) toast(capabilities.message, 'error');
      return capabilities;
    } finally {
      probePromise = null;
    }
  })();
  return probePromise;
}

async function toggleInput(kind) {
  const isMouse = kind === 'mouse';
  const current = isMouse ? mouseEnabled : keyboardEnabled;

  if (current) {
    if (isMouse) mouseEnabled = false;
    else keyboardEnabled = false;
    refreshControls();
    toast(`${isMouse ? 'Mouse' : 'Keyboard'} control disabled.`);
    return;
  }

  if (capabilities[kind] === null) {
    toast(`Checking ${kind} control availability…`);
    await probeControls();
  }

  if (!capabilities[kind]) {
    toast(capabilities.message || `${isMouse ? 'Mouse' : 'Keyboard'} control is unavailable in this desktop session.`, 'error');
    return;
  }

  if (isMouse) mouseEnabled = true;
  else keyboardEnabled = true;
  refreshControls();
  toast(`${isMouse ? 'Mouse' : 'Keyboard'} control enabled.`, 'success');
}

mouseBtn?.addEventListener('click', () => void toggleInput('mouse'));
keyboardBtn?.addEventListener('click', () => void toggleInput('keyboard'));

fullscreenBtn?.addEventListener('click', async () => {
  try {
    if (document.fullscreenElement === stage) {
      await document.exitFullscreen();
      fullscreenFallback = false;
      refreshControls();
      toast('Fullscreen mode disabled.');
      return;
    }

    if (stage.requestFullscreen) {
      await stage.requestFullscreen();
      fullscreenFallback = false;
    } else {
      fullscreenFallback = !fullscreenFallback;
    }
    refreshControls();
    toast(isFullscreen() ? 'Fullscreen mode enabled.' : 'Fullscreen mode disabled.', 'success');
  } catch (error) {
    // Browser fullscreen can be blocked by policy. Keep a CSS fallback so the button still works.
    fullscreenFallback = !fullscreenFallback;
    refreshControls();
    toast(fullscreenFallback ? 'Browser fullscreen was blocked; expanded view enabled instead.' : 'Expanded view disabled.', '');
  }
});

document.addEventListener('fullscreenchange', () => {
  if (document.fullscreenElement === stage) fullscreenFallback = false;
  refreshControls();
});

img?.addEventListener('mousemove', event => {
  if (!mouseEnabled || moveBusy) return;
  const now = performance.now();
  if (now - lastMove < 55) return;
  lastMove = now;
  const point = normalized(event);
  if (!point || point.x < 0 || point.x > 1 || point.y < 0 || point.y > 1) return;

  moveBusy = true;
  apiFetch('/api/control/mouse/move', {
    method: 'POST',
    body: JSON.stringify(point),
  }).catch(error => {
    const stamp = Date.now();
    if (stamp - lastMoveErrorToast > 5000) {
      lastMoveErrorToast = stamp;
      toast(error.message || 'Mouse movement could not be applied.', 'error');
    }
  }).finally(() => { moveBusy = false; });
});

img?.addEventListener('mousedown', event => {
  if (!mouseEnabled) return;
  event.preventDefault();
  const point = normalized(event);
  if (!point || point.x < 0 || point.x > 1 || point.y < 0 || point.y > 1) return;
  apiFetch('/api/control/mouse/click', {
    method: 'POST',
    body: JSON.stringify({ ...point, button: event.button }),
  }).catch(error => toast(error.message || 'Mouse click could not be applied.', 'error'));
});

img?.addEventListener('contextmenu', event => {
  if (mouseEnabled) event.preventDefault();
});

img?.addEventListener('error', () => {
  statusEl.textContent = 'Desktop stream unavailable';
  toast('The live desktop stream could not be loaded.', 'error');
}, { once: true });

window.addEventListener('keydown', event => {
  if (!keyboardEnabled) return;
  if (event.key === 'F11') return;

  event.preventDefault();
  apiFetch('/api/control/key', {
    method: 'POST',
    body: JSON.stringify({
      key: event.key,
      ctrl: event.ctrlKey,
      shift: event.shiftKey,
      alt: event.altKey,
    }),
  }).catch(error => {
    const stamp = Date.now();
    if (stamp - lastKeyErrorToast > 2500) {
      lastKeyErrorToast = stamp;
      toast(error.message || 'Keyboard input could not be applied.', 'error');
    }
  });
});

refreshControls();
void probeControls();
