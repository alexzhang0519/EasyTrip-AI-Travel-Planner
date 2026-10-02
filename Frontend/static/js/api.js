// In-memory page identity: never copied from cookies, localStorage or sessionStorage.
const draftId = crypto.randomUUID();
const headers = {'Content-Type': 'application/json', 'X-EasyTrip': '1', 'X-EasyTrip-Draft': draftId};
export function closeDraft() {
  return fetch('/api/conversation/close', {
    method: 'POST', headers, body: '{}', keepalive: true
  }).catch(() => {});
}
export async function api(path, data) {
  const response = await fetch(`/api${path}`, {
    headers, ...(data === undefined ? {} : {method: 'POST', body: JSON.stringify(data)})
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
