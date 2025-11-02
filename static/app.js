const API_BASE = "http://127.0.0.1:8000";

const form = document.getElementById('searchForm');
const results = document.getElementById('results');
const btnJson = document.getElementById('btnJson');
const btnCsv  = document.getElementById('btnCsv');

async function doSearch(query) {
  const res = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ query })
  });
  if (!res.ok) throw new Error('Search failed');
  return await res.json();
}

function renderResults(list) {
  results.innerHTML = '';
  if (!list || list.length === 0) {
    results.textContent = 'Nic nenalezeno.';
    btnJson.disabled = true;
    btnCsv.disabled = true;
    return;
  }

  list.forEach(it => {
    const el = document.createElement('div');
    el.className = 'item';
    el.innerHTML = `
      <small class="meta">#${it.rank}</small>
      <h3><a href="${it.url}" target="_blank" rel="noopener noreferrer">${it.title || '(bez názvu)'}</a></h3>
      <p>${it.snippet || ''}</p>
    `;
    results.appendChild(el);
  });

  btnJson.disabled = false;
  btnCsv.disabled = false;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = document.getElementById('q').value.trim();
  if (!q) return;
  results.textContent = 'Hledám…';
  try {
    const data = await doSearch(q);
    renderResults(data.results || []);
  } catch (err) {
    console.error(err);
    results.textContent = 'Chyba vyhledávání.';
    btnJson.disabled = true;
    btnCsv.disabled = true;
  }
});

async function download(fmt) {
  const q = document.getElementById('q').value.trim();
  if (!q) { alert('Nejprve zadejte dotaz.'); return; }
  const res = await fetch(`${API_BASE}/download/${fmt}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ query: q })
  });
  if (!res.ok) { alert('Download failed'); return; }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fmt === 'json' ? 'results.json' : 'results.csv';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

btnJson.addEventListener('click', () => download('json'));
btnCsv.addEventListener('click', () => download('csv'));
