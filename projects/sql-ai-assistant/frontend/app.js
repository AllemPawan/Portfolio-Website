/* ─── Configuration ─── */
const API_BASE = '/api';

const $ = (sel, ctx = document) => (typeof sel === 'string' ? ctx.querySelector(sel) : sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

/* ─── State ─── */
let state = {
  dbLoaded: false,
  dbName: null,
  tables: [],
  sampleQuestions: [],
  history: [],
  chartInstance: null,
};

/* ─── DOM refs ─── */
const dom = {
  messages: $('#messages'),
  form: $('#query-form'),
  input: $('#query-input'),
  submit: $('#query-submit'),
  statusBadge: $('#status-badge'),
  dbInfo: $('#db-info'),
  sampleQuestions: $('#sample-questions'),
  historyList: $('#history-list'),
  uploadBtn: $('#upload-btn'),
  clearHistoryBtn: $('#clear-history-btn'),
  uploadModal: $('#upload-modal'),
  dropZone: $('#drop-zone'),
  fileInput: $('#file-input'),
  uploadStatus: $('#upload-status'),
  uploadCancel: $('#upload-cancel'),
  uploadSubmit: $('#upload-submit'),
};

/* ─── API helpers ─── */
async function api(method, path, body) {
  const opts = { method, headers: {} };
  if (body instanceof FormData) {
    opts.body = body;
  } else if (body) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${API_BASE}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/* ─── Utilities ─── */
function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function formatTime(ms) {
  return ms < 1000 ? `${ms.toFixed(1)}ms` : `${(ms / 1000).toFixed(2)}s`;
}

function formatTimestamp(iso) {
  return new Date(iso).toLocaleTimeString();
}

/* ─── Messages ─── */
function addMessage(content, role, extra) {
  const div = document.createElement('div');
  div.className = 'msg-enter';

  const isUser = role === 'user';
  const bg = isUser ? 'bg-primary-600/10 border border-primary-500/20' : 'bg-surface-900 border border-slate-800/60';
  const align = isUser ? 'ml-auto' : 'mr-auto';
  const maxW = isUser ? 'max-w-2xl' : 'max-w-3xl';

  div.innerHTML = `
    <div class="${bg} ${align} ${maxW} rounded-xl p-4">
      <div class="text-xs font-medium text-slate-500 mb-1">${isUser ? 'You' : 'Assistant'}</div>
      <div class="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">${content}</div>
      ${extra || ''}
    </div>
  `;
  dom.messages.appendChild(div);
  dom.messages.scrollTop = dom.messages.scrollHeight;
  return div;
}

function addThinking() {
  const div = document.createElement('div');
  div.className = 'msg-enter';
  div.id = 'thinking-msg';
  div.innerHTML = `
    <div class="bg-surface-900 border border-slate-800/60 rounded-xl p-4 max-w-3xl">
      <div class="text-xs font-medium text-slate-500 mb-2">Assistant</div>
      <div class="flex gap-1.5">
        <span class="thinking-dot w-2 h-2 rounded-full bg-primary-400"></span>
        <span class="thinking-dot w-2 h-2 rounded-full bg-primary-400"></span>
        <span class="thinking-dot w-2 h-2 rounded-full bg-primary-400"></span>
      </div>
    </div>
  `;
  dom.messages.appendChild(div);
  dom.messages.scrollTop = dom.messages.scrollHeight;
}

function removeThinking() {
  const el = $('#thinking-msg');
  if (el) el.remove();
}

/* ─── Results table ─── */
function buildResultsTable(columns, rows) {
  const wrapper = document.createElement('div');
  wrapper.className = 'overflow-x-auto mt-3 rounded-lg border border-slate-800/60';
  const table = document.createElement('table');
  table.className = 'w-full text-xs';

  const thead = document.createElement('thead');
  thead.className = 'bg-surface-800';
  const tr = document.createElement('tr');
  columns.forEach(col => {
    const th = document.createElement('th');
    th.className = 'px-3 py-2 text-left text-slate-400 font-medium whitespace-nowrap';
    th.textContent = col;
    tr.appendChild(th);
  });
  thead.appendChild(tr);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  rows.forEach((row, ri) => {
    const tr2 = document.createElement('tr');
    tr2.className = ri % 2 === 0 ? 'bg-surface-900/50' : 'bg-surface-950/30';
    row.forEach(val => {
      const td = document.createElement('td');
      td.className = 'px-3 py-2 text-slate-300 whitespace-nowrap max-w-xs truncate';
      td.textContent = val == null ? 'NULL' : String(val);
      tr2.appendChild(td);
    });
    tbody.appendChild(tr2);
  });
  table.appendChild(tbody);
  wrapper.appendChild(table);
  return wrapper;
}

/* ─── Charts ─── */
function renderChart(chartData) {
  if (!chartData) return '';
  const canvasId = 'chart-canvas';
  const container = document.createElement('div');
  container.className = 'mt-4 p-4 rounded-xl bg-surface-900 border border-slate-800/60';
  container.innerHTML = `
    <h4 class="text-sm font-semibold text-slate-400 mb-3">${escapeHtml(chartData.title || 'Chart')}</h4>
    <div class="relative" style="height: 260px;">
      <canvas id="${canvasId}"></canvas>
    </div>
  `;

  // Render chart after DOM insertion
  requestAnimationFrame(() => {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    if (state.chartInstance) state.chartInstance.destroy();

    const ctx = canvas.getContext('2d');
    const colors = ['#818cf8', '#34d399', '#f472b6', '#fbbf24', '#60a5fa', '#a78bfa', '#fb923c', '#2dd4bf'];

    const config = {
      type: chartData.chart_type || 'bar',
      data: {
        labels: chartData.labels || [],
        datasets: [{
          label: chartData.value_column || 'Value',
          data: chartData.values || [],
          backgroundColor: chartData.chart_type === 'pie'
            ? colors.slice(0, chartData.labels.length)
            : colors[0],
          borderColor: chartData.chart_type === 'pie' ? '#0f172a' : colors[0],
          borderWidth: chartData.chart_type === 'pie' ? 2 : 1,
          borderRadius: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        color: '#94a3b8',
        plugins: {
          legend: { display: chartData.chart_type === 'pie', labels: { color: '#94a3b8' } }
        },
        scales: chartData.chart_type !== 'pie' ? {
          x: { grid: { color: '#1e293b' }, ticks: { color: '#64748b' } },
          y: { grid: { color: '#1e293b' }, ticks: { color: '#64748b', beginAtZero: true } }
        } : {}
      }
    };

    state.chartInstance = new Chart(ctx, config);
  });

  return container;
}

/* ─── Export buttons ─── */
function buildExportBar(sql) {
  const bar = document.createElement('div');
  bar.className = 'flex flex-wrap gap-2 mt-3';
  ['csv', 'json', 'sql'].forEach(fmt => {
    const btn = document.createElement('button');
    btn.className = 'text-xs px-3 py-1.5 rounded-lg bg-surface-800 hover:bg-surface-700 text-slate-400 font-medium transition-colors';
    btn.textContent = `Export ${fmt.toUpperCase()}`;
    btn.onclick = () => exportResults(fmt, sql);
    bar.appendChild(btn);
  });
  return bar;
}

async function exportResults(fmt, sql) {
  const url = `${API_BASE}/export/${fmt}?sql=${encodeURIComponent(sql)}`;
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error('Export failed');
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `export.${fmt}`;
    a.click();
    URL.revokeObjectURL(a.href);
  } catch (e) {
    console.error(e);
  }
}

/* ─── SQL display ─── */
function buildSqlBlock(sql) {
  return `
    <div class="mt-3 p-3 rounded-lg bg-surface-950 border border-slate-800/60 overflow-x-auto">
      <div class="text-xs text-slate-500 mb-1">Generated SQL</div>
      <code class="text-xs text-emerald-400 font-mono whitespace-pre-wrap">${escapeHtml(sql)}</code>
    </div>
  `;
}

/* ─── History ─── */
function updateHistory() {
  const list = dom.historyList;
  if (!state.history.length) {
    list.innerHTML = '<p class="text-xs text-slate-600">No queries yet</p>';
    return;
  }
  list.innerHTML = state.history.map(h => `
    <button class="history-item w-full text-left px-2 py-1.5 rounded-lg hover:bg-surface-800 text-xs text-slate-400 hover:text-white transition-colors truncate" data-question="${escapeHtml(h.question)}">
      ${escapeHtml(h.question)}
    </button>
  `).join('');

  $$('.history-item', list).forEach(el => {
    el.addEventListener('click', () => {
      dom.input.value = el.dataset.question;
      dom.form.dispatchEvent(new Event('submit'));
    });
  });
}

/* ─── Refresh UI after DB change ─── */
async function refreshDbInfo() {
  if (!state.dbLoaded) {
    dom.dbInfo.innerHTML = '<div class="text-sm text-slate-500">No database loaded</div>';
    dom.statusBadge.textContent = 'no DB';
    dom.statusBadge.className = 'text-xs px-2 py-0.5 rounded-full bg-amber-900/50 text-amber-400';
    dom.sampleQuestions.innerHTML = '';
    dom.input.disabled = true;
    dom.submit.disabled = true;
    return;
  }

  dom.dbInfo.innerHTML = `
    <div class="font-medium text-white text-sm mb-1">${escapeHtml(state.dbName)}</div>
    <div class="text-xs text-slate-500">${state.tables.length} table${state.tables.length !== 1 ? 's' : ''}</div>
    <div class="mt-2 space-y-1">
      ${state.tables.map(t => `
        <div class="flex justify-between text-xs">
          <span class="text-slate-400">${escapeHtml(t.name)}</span>
          <span class="text-slate-500">${t.row_count} rows</span>
        </div>
      `).join('')}
    </div>
  `;

  dom.statusBadge.textContent = `DB: ${state.dbName}`;
  dom.statusBadge.className = 'text-xs px-2 py-0.5 rounded-full bg-emerald-900/50 text-emerald-400';
  dom.input.disabled = false;
  dom.submit.disabled = false;
  dom.input.focus();

  // Sample questions
  dom.sampleQuestions.innerHTML = state.sampleQuestions.length
    ? state.sampleQuestions.map(q => `
      <button class="sample-q w-full text-left px-2 py-1.5 rounded-lg hover:bg-surface-800 text-xs text-slate-400 hover:text-white transition-colors truncate">${escapeHtml(q)}</button>
    `).join('')
    : '<p class="text-xs text-slate-600">Loading samples...</p>';

  if (state.sampleQuestions.length === 0) {
    try {
      const data = await api('GET', '/sample-questions');
      state.sampleQuestions = data.questions || [];
      dom.sampleQuestions.innerHTML = state.sampleQuestions.map(q => `
        <button class="sample-q w-full text-left px-2 py-1.5 rounded-lg hover:bg-surface-800 text-xs text-slate-400 hover:text-white transition-colors truncate">${escapeHtml(q)}</button>
      `).join('');
      $$('.sample-q', dom.sampleQuestions).forEach(el => {
        el.addEventListener('click', () => {
          dom.input.value = el.textContent;
          dom.form.dispatchEvent(new Event('submit'));
        });
      });
    } catch { /* ignore */ }
  }

  $$('.sample-q', dom.sampleQuestions).forEach(el => {
    el.addEventListener('click', () => {
      dom.input.value = el.textContent;
      dom.form.dispatchEvent(new Event('submit'));
    });
  });
}

/* ─── Query flow ─── */
async function handleQuery(question) {
  addThinking();
  try {
    const data = await api('POST', '/query', { question });
    removeThinking();

    let extra = '';
    extra += buildSqlBlock(data.sql);

    const rowsLimited = data.rows.slice(0, 100);
    if (rowsLimited.length) {
      extra += buildResultsTable(data.columns, rowsLimited).outerHTML;
      if (data.row_count > 100) {
        extra += `<p class="text-xs text-slate-500 mt-2">Showing 100 of ${data.row_count} rows</p>`;
      }
    } else {
      extra += `<p class="text-xs text-slate-500 mt-2">0 rows returned</p>`;
    }

    if (data.chart_data) {
      const chartEl = renderChart(data.chart_data);
      if (chartEl) extra += chartEl.outerHTML;
    }

    const summary = `<div class="flex flex-wrap gap-3 mt-3 text-xs text-slate-500">
      <span>⏱ ${formatTime(data.execution_time_ms)}</span>
      <span>📊 ${data.row_count} rows</span>
    </div>`;

    extra += buildExportBar(data.sql);
    extra += summary;

    addMessage(question, 'user');
    addMessage(data.explanation || 'Query executed.', 'assistant', extra);

    state.history.unshift({ question: data.question, sql: data.sql, timestamp: new Date().toISOString() });
    updateHistory();

  } catch (e) {
    removeThinking();
    addMessage(question, 'user');
    addMessage(`❌ **Error:** ${e.message}`, 'assistant');
  }
}

/* ─── Event listeners ─── */
dom.form.addEventListener('submit', async e => {
  e.preventDefault();
  const q = dom.input.value.trim();
  if (!q) return;
  dom.input.value = '';
  await handleQuery(q);
});

dom.uploadBtn.addEventListener('click', () => {
  dom.uploadModal.classList.remove('hidden');
  dom.uploadModal.classList.add('flex');
});

dom.uploadCancel.addEventListener('click', () => {
  dom.uploadModal.classList.add('hidden');
  dom.uploadModal.classList.remove('flex');
  dom.fileInput.value = '';
  dom.uploadStatus.classList.add('hidden');
  dom.uploadSubmit.disabled = true;
});

dom.dropZone.addEventListener('click', () => dom.fileInput.click());
dom.dropZone.addEventListener('dragover', e => { e.preventDefault(); dom.dropZone.classList.add('border-primary-500'); });
dom.dropZone.addEventListener('dragleave', () => dom.dropZone.classList.remove('border-primary-500'));
dom.dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dom.dropZone.classList.remove('border-primary-500');
  if (e.dataTransfer.files.length) dom.fileInput.files = e.dataTransfer.files;
  dom.uploadSubmit.disabled = false;
});

dom.fileInput.addEventListener('change', () => {
  dom.uploadSubmit.disabled = !dom.fileInput.files.length;
});

dom.uploadSubmit.addEventListener('click', async () => {
  const file = dom.fileInput.files[0];
  if (!file) return;
  dom.uploadSubmit.disabled = true;
  dom.uploadSubmit.textContent = 'Uploading...';
  dom.uploadStatus.classList.remove('hidden');
  dom.uploadStatus.textContent = 'Uploading...';

  try {
    const fd = new FormData();
    fd.append('file', file);
    const data = await api('POST', '/upload-db', fd);
    state.dbLoaded = true;
    state.dbName = data.database;
    state.tables = data.tables.map(name => ({ name, row_count: 0, columns: [] }));

    // Load table details
    const tablesData = await api('GET', '/tables');
    state.tables = tablesData;
    state.sampleQuestions = [];

    dom.uploadModal.classList.add('hidden');
    dom.uploadModal.classList.remove('flex');
    dom.fileInput.value = '';
    dom.uploadSubmit.disabled = false;
    dom.uploadSubmit.textContent = 'Upload';
    dom.uploadStatus.classList.add('hidden');

    dom.messages.innerHTML = '';
    addMessage(`✅ Database **${data.database}** loaded successfully with ${data.tables.length} tables. Start asking questions!`, 'assistant');
    await refreshDbInfo();

  } catch (e) {
    dom.uploadStatus.textContent = `Error: ${e.message}`;
    dom.uploadSubmit.disabled = false;
    dom.uploadSubmit.textContent = 'Upload';
  }
});

dom.clearHistoryBtn.addEventListener('click', async () => {
  state.history = [];
  updateHistory();
  try { await api('GET', '/clear-history'); } catch { /* ignore */ }
});

/* ─── Init ─── */
(async function init() {
  try {
    const health = await api('GET', '/health');
    if (health.database && health.database !== 'none') {
      state.dbLoaded = true;
      state.dbName = health.database.replace('loaded: ', '');
      const tablesData = await api('GET', '/tables');
      state.tables = tablesData;
      dom.messages.innerHTML = '';
      await refreshDbInfo();
      dom.input.focus();
    }
  } catch {
    dom.statusBadge.textContent = 'API unavailable';
    dom.statusBadge.className = 'text-xs px-2 py-0.5 rounded-full bg-red-900/50 text-red-400';
  }
})();
