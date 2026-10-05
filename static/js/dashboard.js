let scheduleMode = 'countdown';
const $ = id => document.getElementById(id);

function setMeter(id, value) {
  const el = $(id);
  if (el) el.style.width = `${Math.max(0, Math.min(100, value))}%`;
}

function formatAction(action) {
  return ({ shutdown: 'Shutdown', restart: 'Restart', sleep: 'Sleep', lock: 'Lock' })[action] || action;
}

function renderCores(values) {
  const root = $('coreGrid');
  if (!root) return;
  root.innerHTML = '';
  values.forEach((rawValue, index) => {
    const numericValue = Number(rawValue);
    const value = Number.isFinite(numericValue) ? Math.max(0, Math.min(100, numericValue)) : 0;
    // Treat tiny rounded samples as idle so a reported 0.0% never renders a filled bar.
    const visualValue = value < 0.05 ? 0 : value;
    const item = document.createElement('div');
    item.className = 'core-item';
    item.innerHTML = `<div><span>CPU ${String(index).padStart(2, '0')}</span><strong>${value.toFixed(1)}%</strong></div><div class="core-meter${visualValue === 0 ? ' is-idle' : ''}"><i></i></div>`;
    item.querySelector('.core-meter > i').style.width = `${visualValue}%`;
    root.appendChild(item);
  });
}

async function updateSystem() {
  try {
    const d = await apiFetch('/api/system');
    $('cpuValue').textContent = `${d.cpu.percent.toFixed(1)}%`;
    $('cpuPhysical').textContent = `Physical: ${d.cpu.physical_cores}`;
    $('cpuLogical').textContent = `Logical: ${d.cpu.logical_cores}`;
    $('cpuCoreCount').textContent = `${d.cpu.logical_cores} logical processors`;
    $('cpuFreq').textContent = d.cpu.frequency_mhz ? `${Math.round(d.cpu.frequency_mhz)} MHz` : '—';
    setMeter('cpuBar', d.cpu.percent);
    renderCores(d.cpu.per_core || []);

    $('memoryValue').textContent = `${d.memory.percent.toFixed(1)}%`;
    $('memoryMeta').textContent = `${d.memory.used_gb} / ${d.memory.total_gb} GB`;
    setMeter('memoryBar', d.memory.percent);

    $('diskValue').textContent = `${d.disk.percent.toFixed(1)}%`;
    $('diskMeta').textContent = `${d.disk.used_gb} / ${d.disk.total_gb} GB`;
    setMeter('diskBar', d.disk.percent);

    $('downValue').textContent = d.network.download_mbps.toFixed(2);
    $('upValue').textContent = d.network.upload_mbps.toFixed(2);
    $('hostname').textContent = d.host.hostname;
    $('hostOs').textContent = d.host.os;
  } catch (error) {
    console.error('System telemetry update failed:', error);
  }
}

async function loadTasks() {
  try {
    const { tasks } = await apiFetch('/api/power/tasks');
    const root = $('taskList');
    root.innerHTML = '';
    const visible = tasks.filter(task => !task.completed && !task.cancelled);
    if (!visible.length) {
      root.innerHTML = '<div class="empty-state">No active operations.</div>';
      return;
    }

    visible.forEach(task => {
      const row = document.createElement('div');
      row.className = 'task';
      const when = new Date(task.execute_at * 1000).toLocaleString('en-GB');
      row.innerHTML = `<div><b>${formatAction(task.action)}</b><small>${when}</small></div><button class="cancel-task">Cancel</button>`;
      row.querySelector('button').addEventListener('click', async () => {
        try {
          await apiFetch(`/api/power/tasks/${task.id}`, { method: 'DELETE' });
          toast('Operation cancelled.', 'success');
          loadTasks();
        } catch (error) {
          toast(error.message, 'error');
        }
      });
      root.appendChild(row);
    });
  } catch (error) {
    console.error('Task refresh failed:', error);
  }
}

document.querySelectorAll('#scheduleTabs button').forEach(button => button.addEventListener('click', () => {
  scheduleMode = button.dataset.mode;
  document.querySelectorAll('#scheduleTabs button').forEach(item => item.classList.toggle('active', item === button));
  $('countdownFields').classList.toggle('hidden', scheduleMode !== 'countdown');
  $('scheduledFields').classList.toggle('hidden', scheduleMode !== 'scheduled');
}));

document.querySelectorAll('.power-action').forEach(button => button.addEventListener('click', async () => {
  const action = button.dataset.action;
  if (!confirm(`Schedule ${formatAction(action)}?`)) return;

  const payload = { action, mode: scheduleMode };
  if (scheduleMode === 'scheduled') {
    payload.time = $('scheduledTime').value;
    if (!payload.time) {
      toast('Enter an execution time.', 'error');
      return;
    }
  } else {
    payload.seconds = (Number($('hours').value) || 0) * 3600 + (Number($('minutes').value) || 0) * 60 + (Number($('seconds').value) || 0);
    if (payload.seconds < 1) {
      toast('The countdown must be greater than zero.', 'error');
      return;
    }
  }

  try {
    await apiFetch('/api/power/schedule', { method: 'POST', body: JSON.stringify(payload) });
    toast('Operation scheduled.', 'success');
    loadTasks();
  } catch (error) {
    toast(error.message, 'error');
  }
}));

$('refreshTasks')?.addEventListener('click', loadTasks);
updateSystem();
loadTasks();
setInterval(updateSystem, 1600);
setInterval(loadTasks, 15000);
