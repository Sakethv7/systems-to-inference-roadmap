(() => {
  'use strict';
  const panel = document.getElementById('live-notes');
  if (!panel) return;
  const status = document.getElementById('live-status');
  const detail = document.getElementById('live-detail');
  const list = document.getElementById('live-list');
  const warnings = document.getElementById('live-warnings');
  const filter = document.getElementById('live-filter');
  const refresh = document.getElementById('live-refresh');
  const layers = {1: 'Machine & OS', 2: 'Network', 3: 'Redis', 4: 'Cache case', 5: 'Postgres', 6: 'Distributed', 7: 'Transformer', 8: 'Inference', 9: 'Harness'};
  let notes = new Map(), timer, controller, inFlight = false, lastSuccess = null;
  let retained = false;

  function render() {
    list.replaceChildren();
    const all = [...notes.values()].sort((a, b) => (b.entry_date || '').localeCompare(a.entry_date || '') || b.id.localeCompare(a.id));
    const shown = all.filter(n => filter.value === 'all' || n.layer_id !== null).slice(0, 12);
    if (!shown.length) {
      const li = document.createElement('li');
      li.textContent = filter.value === 'all' ? 'No learning notes in this snapshot.' : 'No mapped notes yet. Choose “All notes” to see unmapped evidence.';
      list.append(li);
    }
    for (const note of shown) {
      const li = document.createElement('li');
      const title = document.createElement('a');
      title.textContent = note.title;
      title.href = 'obsidian://open?vault=SakethVault&file=' + encodeURIComponent(note.id);
      const meta = document.createElement('span');
      meta.className = 'note-meta';
      meta.textContent = `${note.entry_date || 'Entry date unknown'} · ${note.layer_id === null ? 'Unmapped — needs review' : `Layer ${note.layer_id}: ${layers[note.layer_id]}`} · Saved evidence${note.retained ? ' · Previously seen; not confirmed in partial scan' : ''}`;
      li.append(title, meta);
      list.append(li);
    }
    document.getElementById('live-count').textContent = `Showing ${shown.length} of ${all.filter(n => filter.value === 'all' || n.layer_id !== null).length} ${filter.value === 'all' ? 'notes' : 'mapped notes'}${retained ? ' (includes retained evidence)' : ''}`;
  }

  function validate(data) {
    if (!data || data.schema_version !== 1 || !['ok', 'partial', 'unavailable'].includes(data.status) || !Array.isArray(data.notes) || !Array.isArray(data.warnings)) throw new Error('Invalid snapshot');
    for (const n of data.notes) {
      if (!n || typeof n.id !== 'string' || !/^_wiki\/cs\/[\w-]+\.md$/.test(n.id) || typeof n.title !== 'string' || !(n.entry_date === null || /^\d{4}-\d{2}-\d{2}$/.test(n.entry_date)) || !(n.layer_id === null || Object.hasOwn(layers, n.layer_id)) || n.evidence_state !== 'stored') throw new Error('Invalid note');
    }
    return data;
  }

  async function poll() {
    if (inFlight || document.hidden || location.protocol === 'file:') return;
    clearTimeout(timer);
    inFlight = true;
    refresh.disabled = true;
    controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);
    try {
      const response = await fetch('/api/learning-state', {cache: 'no-store', signal: controller.signal});
      if (!response.ok) throw new Error('Service unavailable');
      const data = validate(await response.json());
      if (data.status === 'unavailable') throw new Error('Vault unavailable');
      if (data.status === 'ok') {
        notes = new Map(data.notes.map(n => [n.id, n]));
        lastSuccess = data.last_success_at;
        retained = false;
      } else {
        notes = new Map([...notes].map(([id, n]) => [id, {...n, retained: true}]));
        for (const note of data.notes) notes.set(note.id, note);
        retained = [...notes.values()].some(n => n.retained);
      }
      status.textContent = data.status === 'ok' ? 'Live' : 'Partial — some evidence may be stale';
      status.dataset.state = data.status;
      detail.textContent = `Last scan: ${new Date(data.scanned_at).toLocaleString()}. ${lastSuccess ? `Last complete scan: ${new Date(lastSuccess).toLocaleString()}.` : 'No complete scan yet.'} Refreshes every 10 seconds while open.`;
      warnings.textContent = data.warnings.join(' ');
      render();
    } catch (_) {
      status.textContent = 'Disconnected — evidence may be stale';
      status.dataset.state = 'unavailable';
      detail.textContent = lastSuccess ? `Showing the last successful data from ${new Date(lastSuccess).toLocaleString()}. Retrying every 10 seconds.` : 'No successful connection yet. Start the roadmap service on this Mac; this page will reconnect automatically.';
      warnings.textContent = 'The source could not be refreshed. Your reviewed roadmap and completion progress are still available.';
    } finally {
      clearTimeout(timeout);
      controller = null;
      inFlight = false;
      refresh.disabled = false;
      if (!document.hidden) timer = setTimeout(poll, 10000);
    }
  }
  filter.addEventListener('change', render);
  refresh.addEventListener('click', poll);
  document.addEventListener('visibilitychange', () => {
    clearTimeout(timer);
    if (document.hidden) controller?.abort();
    else poll();
  });
  window.addEventListener('focus', poll);
  window.addEventListener('pagehide', () => {clearTimeout(timer); controller?.abort();});
  if (location.protocol === 'file:') {
    status.textContent = 'Open the live site to connect';
    detail.textContent = 'This file is the portable roadmap. Live notes are available at http://127.0.0.1:8768/ while the roadmap service runs.';
    refresh.disabled = true;
  } else poll();
})();
