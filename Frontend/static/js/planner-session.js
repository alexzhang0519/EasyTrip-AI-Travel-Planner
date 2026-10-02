// Every planner page entry starts fresh unless a saved trip was explicitly opened.
// Do not rely on unload events: browsers may never deliver them.
export async function openPlanner(api, url, history) {
  await api('/conversation/start', {});
  const trip = url.searchParams.get('trip');
  if (trip) {
    const data = await api(`/trips/${encodeURIComponent(trip)}/load`, {});
    // A later refresh starts fresh rather than silently loading this snapshot again.
    url.searchParams.delete('trip');
    history.replaceState(null, '', url.pathname + url.search + url.hash);
    return data;
  }
  return {messages: [], pois: []};
}
