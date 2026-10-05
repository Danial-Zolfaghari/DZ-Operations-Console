const currentPassword = document.getElementById('currentPassword');
const newPassword = document.getElementById('newPassword');
const confirmPassword = document.getElementById('confirmPassword');
const shellEnabled = document.getElementById('shellEnabled');
const pendingState = document.getElementById('pendingShellState');

function updatePending() {
  if (!pendingState) return;
  pendingState.textContent = shellEnabled.checked ? 'Enabled' : 'Disabled';
  pendingState.classList.toggle('on', shellEnabled.checked);
  pendingState.classList.toggle('off', !shellEnabled.checked);
}

shellEnabled?.addEventListener('change', updatePending);

document.getElementById('saveSettings')?.addEventListener('click', async () => {
  if (!currentPassword.value) {
    toast('Enter the current administrator password.', 'error');
    return;
  }
  if (newPassword.value && newPassword.value !== confirmPassword.value) {
    toast('Password confirmation does not match.', 'error');
    return;
  }
  if (newPassword.value && newPassword.value.length < 8) {
    toast('The new password must be at least 8 characters long.', 'error');
    return;
  }

  try {
    const result = await apiFetch('/api/settings', {
      method: 'POST',
      body: JSON.stringify({
        current_password: currentPassword.value,
        new_password: newPassword.value,
        shell_enabled: shellEnabled.checked
      })
    });
    toast(result.message, 'success');
    currentPassword.value = '';
    newPassword.value = '';
    confirmPassword.value = '';
    setTimeout(() => location.reload(), 750);
  } catch (error) {
    toast(error.message, 'error');
  }
});

updatePending();
