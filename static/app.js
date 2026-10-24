const $ = id => document.getElementById(id);
let selected;
function choose(file) { selected = file; $('filename').textContent = file ? file.name : 'No file selected'; }
$('file').addEventListener('change', e => choose(e.target.files[0]));
$('drop').addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); $('file').click(); } });
for (const name of ['dragover', 'drop']) $('drop').addEventListener(name, e => { e.preventDefault(); if (name === 'drop') { choose(e.dataTransfer.files[0]); $('file').required = !selected; } });
fetch('/api/formats').then(r => { if (!r.ok) throw Error('Could not load FFmpeg formats.'); return r.json(); }).then(config => {
  for (const kind of ['video', 'image']) {
    const group = document.createElement('optgroup'); group.label = kind === 'video' ? 'Video & animation' : 'Pictures (first frame)';
    for (const f of config.formats.filter(f => f.kind === kind)) group.append(new Option(f.label, f.id));
    $('format').append(group);
  }
  for (const q of config.qualities) $('quality').append(new Option(q, q, false, q === 'balanced'));
  for (const w of config.widths) $('width').append(new Option(w ? `${w}px` : 'Original', w));
  $('submit').disabled = !config.formats.length;
}).catch(e => $('status').textContent = e.message);
$('converter').addEventListener('submit', async e => {
  e.preventDefault();
  if (!selected) { $('status').textContent = 'Choose a file first.'; return; }
  if (selected.size > 512 * 1024 * 1024) { $('status').textContent = 'Maximum upload size is 512 MiB.'; return; }
  const body = new FormData(); body.append('file', selected);
  for (const key of ['format', 'quality', 'width']) body.append(key, $(key).value);
  body.append('mute', $('mute').checked);
  $('submit').disabled = true; $('status').textContent = 'Converting… larger videos may take a few minutes.';
  try {
    const response = await fetch('/api/convert', { method: 'POST', body });
    if (!response.ok) { const error = await response.json(); throw Error(typeof error.detail === 'string' ? error.detail : 'Invalid request.'); }
    const url = URL.createObjectURL(await response.blob());
    const a = document.createElement('a'); a.href = url;
    a.download = response.headers.get('content-disposition')?.match(/filename="([^"]+)"/)?.[1] || 'converted';
    a.click(); setTimeout(() => URL.revokeObjectURL(url), 60000); $('status').textContent = 'Done. Your download is ready.';
  } catch (e) { $('status').textContent = e.message; }
  finally { $('submit').disabled = false; }
});
