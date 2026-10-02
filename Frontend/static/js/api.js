export async function api(path, data) {
  const response = await fetch(`/api${path}`, data === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json', 'X-EasyTrip': '1'}, body: JSON.stringify(data)
  });
  let result;
  try { result = await response.json(); } catch { throw new Error('The server did not respond correctly. Check that EasyTrip is running.'); }
  if (!response.ok) throw new Error(result.error || 'Request failed. Please try again.');
  return result;
}
export function notice(message, error = false) {
  const box = document.querySelector('#notice');
  box.textContent = message; box.hidden = !message; box.classList.toggle('error', error);
}
export function element(tag, text, className) {
  const node = document.createElement(tag); node.textContent = text;
  if (className) node.className = className;
  return node;
}
export function setBusy(form, busy) {
  form.querySelectorAll('button, input, select, textarea').forEach(node => { node.disabled = busy; });
}
