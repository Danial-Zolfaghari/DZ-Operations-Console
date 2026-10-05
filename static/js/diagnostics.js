const output = document.getElementById('terminalOutput');
const title = document.getElementById('terminalTitle');
const shellForm = document.getElementById('shellForm');
const customInput = document.getElementById('customCommand');
const count = document.getElementById('commandCount');

function visibleCount() {
  const total = [...document.querySelectorAll('.helper-command')].filter(item => !item.classList.contains('hidden')).length;
  if (count) count.textContent = `${total} COMMANDS`;
}

function showRunning(command) {
  title.textContent = 'PowerShell';
  output.textContent = `PS> ${command}\n\nRunning…`;
}

function showResult(command, result) {
  output.textContent = `PS> ${command}\n\n${result.output || '(no output)'}\n\n[exit ${result.returncode}]`;
  output.scrollTop = output.scrollHeight;
}

document.querySelectorAll('.category-btn').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('.category-btn').forEach(item => item.classList.toggle('active', item === button));
  document.querySelectorAll('.helper-command').forEach(item => item.classList.toggle('hidden', item.dataset.category !== button.dataset.category));
  visibleCount();
}));

document.querySelectorAll('.helper-command').forEach(button => button.addEventListener('click', async () => {
  const id = button.dataset.commandId;
  const command = button.dataset.commandText;
  showRunning(command);
  try {
    const result = await apiFetch('/api/diagnostics/helper', { method: 'POST', body: JSON.stringify({ id }) });
    showResult(command, result);
  } catch (error) {
    output.textContent = `PS> ${command}\n\nERROR: ${error.message}`;
    toast(error.message, 'error');
  }
}));

shellForm?.addEventListener('submit', async event => {
  event.preventDefault();
  const command = customInput.value.trim();
  if (!command) return;
  showRunning(command);
  try {
    const result = await apiFetch('/api/diagnostics/custom', { method: 'POST', body: JSON.stringify({ command }) });
    showResult(command, result);
    customInput.focus();
  } catch (error) {
    output.textContent = `PS> ${command}\n\nERROR: ${error.message}`;
    toast(error.message, 'error');
  }
});

document.getElementById('clearTerminal')?.addEventListener('click', () => {
  output.textContent = 'DZ CONTROL / COMMAND CENTER\n\nTerminal output cleared.';
});

visibleCount();
