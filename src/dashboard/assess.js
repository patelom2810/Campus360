/**
 * Campus360 — Bring Your Own Data Assessment
 * assess.js — All 4 option flows + shared results renderer
 */

const API_BASE = (window.location.port === '8000')
  ? ''
  : 'http://localhost:8000';

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  activeOption: null,
  csvPreviewId: null,
  csvMappingData: [],
  stitchFiles: [],
  stitchSummaries: [],
  stitchKeyInfo: null,
  chatSessionId: null,
  chartInstances: {},
};

// ── Navigation & Persistence ──────────────────────────────────────────────────
function selectOption(option) {
  // Highlight selected card
  document.querySelectorAll('.option-card').forEach(c => c.classList.remove('selected'));
  const card = document.getElementById(`card-${option}`);
  if (card) card.classList.add('selected');

  // Hide all panels, show selected
  document.querySelectorAll('.flow-panel').forEach(p => p.classList.remove('active'));
  const panel = document.getElementById(`panel-${option}`);
  if (panel) panel.classList.add('active');

  // Hide hero + options grid slightly on mobile once a panel is active
  state.activeOption = option;
  try {
    window.location.hash = option;
    localStorage.setItem('campus360_assess_option', option);
  } catch (_) {}

  const singleContainer = document.getElementById('single-result-container');
  if (singleContainer) singleContainer.classList.add('hidden');

  // Scroll to panel
  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

  // Initialize chat if selected
  if (option === 'chat' && !state.chatSessionId) {
    initChatUI();
  }
}

function backToCards() {
  document.querySelectorAll('.option-card').forEach(c => c.classList.remove('selected'));
  document.querySelectorAll('.flow-panel').forEach(p => p.classList.remove('active'));
  state.activeOption = null;
  try {
    history.replaceState(null, null, window.location.pathname);
    localStorage.removeItem('campus360_assess_option');
  } catch (_) {}
  const grid = document.getElementById('option-grid');
  if (grid) grid.scrollIntoView({ behavior: 'smooth' });
}

// Restore active option when page is refreshed or hash changes
document.addEventListener('DOMContentLoaded', () => {
  const hash = window.location.hash.replace('#', '');
  let saved = null;
  try {
    saved = localStorage.getItem('campus360_assess_option');
  } catch (_) {}
  const validOptions = ['csv-match', 'csv-stitch', 'chat', 'new-student'];
  const initial = validOptions.includes(hash) ? hash : (validOptions.includes(saved) ? saved : null);
  if (initial) {
    setTimeout(() => selectOption(initial), 50);
  }
});

window.addEventListener('hashchange', () => {
  const hash = window.location.hash.replace('#', '');
  const validOptions = ['csv-match', 'csv-stitch', 'chat', 'new-student'];
  if (validOptions.includes(hash)) {
    selectOption(hash);
  } else if (!hash) {
    backToCards();
  }
});

// ── Shared Utilities ──────────────────────────────────────────────────────────
function showError(containerId, message) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = `
    <div class="p-4 rounded-xl bg-campus-coral border border-campus-danger/30 text-red-700 text-sm flex items-start gap-2">
      <svg class="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>
      <span>${message}</span>
    </div>`;
  el.classList.remove('hidden');
}

function showLoading(btn, text = 'Processing…') {
  if (!btn) return;
  btn._originalText = btn.innerHTML;
  btn.innerHTML = `<span class="spinner"></span> ${text}`;
  btn.disabled = true;
}

function restoreButton(btn) {
  if (!btn || !btn._originalText) return;
  btn.innerHTML = btn._originalText;
  btn.disabled = false;
}

// ── Real Progress Bar Component ──────────────────────────────────────────────
function renderRealProgressBar(containerId, options = {}) {
  const container = document.getElementById(containerId);
  if (!container) return null;

  const prefix = options.prefix || 'prog';
  const title = options.title || 'Processing Datasets';
  const initialDetail = options.initialDetail || 'Preparing request...';
  const stepLabels = options.steps || [
    '1. Transfer',
    '2. Parse & Map',
    '3. Reconcile',
    '4. ML Models'
  ];

  container.innerHTML = `
    <div class="real-progress-container" id="${prefix}-card">
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-xl bg-campus-lavender text-campus-primary flex items-center justify-center font-bold text-xs flex-shrink-0" id="${prefix}-icon">
            <svg class="w-4 h-4 animate-spin text-campus-primary" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
          <div>
            <div class="sora font-semibold text-sm text-campus-text" id="${prefix}-stage">${title}</div>
            <div class="text-xs text-campus-muted" id="${prefix}-detail">${initialDetail}</div>
          </div>
        </div>
        <div class="sora font-bold text-base text-campus-primary" id="${prefix}-pct">0%</div>
      </div>

      <div class="real-progress-track my-2.5">
        <div class="real-progress-bar" id="${prefix}-fill" style="width: 0%;"></div>
      </div>

      <div class="grid grid-cols-4 gap-2 mt-3.5 text-[11px] text-campus-muted font-medium">
        ${stepLabels.map((s, idx) => `
          <div id="${prefix}-step-${idx+1}" class="flex items-center gap-1.5 ${idx === 0 ? 'text-campus-primary font-semibold' : ''}">
            <span class="w-2 h-2 rounded-full ${idx === 0 ? 'bg-campus-primary' : 'bg-[#EDEBFB]'} flex-shrink-0"></span>
            <span class="truncate">${s}</span>
          </div>
        `).join('')}
      </div>
    </div>
  `;
  container.classList.remove('hidden');

  let currentPct = 0;

  function setProgress(pct, stage, detail, stepNum) {
    currentPct = Math.max(currentPct, Math.min(100, Math.round(pct)));
    const fill = document.getElementById(`${prefix}-fill`);
    const pctEl = document.getElementById(`${prefix}-pct`);
    const stageEl = document.getElementById(`${prefix}-stage`);
    const detailEl = document.getElementById(`${prefix}-detail`);

    if (fill) fill.style.width = `${currentPct}%`;
    if (pctEl) pctEl.textContent = `${currentPct}%`;
    if (stage && stageEl) stageEl.textContent = stage;
    if (detail && detailEl) detailEl.textContent = detail;

    if (stepNum) {
      for (let s = 1; s <= 4; s++) {
        const stepEl = document.getElementById(`${prefix}-step-${s}`);
        if (stepEl) {
          const dot = stepEl.querySelector('span');
          if (s <= stepNum) {
            stepEl.className = 'flex items-center gap-1.5 text-campus-primary font-semibold';
            if (dot) dot.className = 'w-2 h-2 rounded-full bg-campus-primary flex-shrink-0';
          } else {
            stepEl.className = 'flex items-center gap-1.5 text-campus-muted font-medium';
            if (dot) dot.className = 'w-2 h-2 rounded-full bg-[#EDEBFB] flex-shrink-0';
          }
        }
      }
    }
  }

  function setComplete(msg = 'Assessment complete!') {
    setProgress(100, msg, 'Finalizing and rendering results...', 4);
    const icon = document.getElementById(`${prefix}-icon`);
    if (icon) {
      icon.innerHTML = `<svg class="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>`;
      icon.className = 'w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold text-xs flex-shrink-0';
    }
  }

  return { setProgress, setComplete, getPct: () => currentPct };
}

function formatFloat(val, decimals = 2) {
  if (val === null || val === undefined) return '—';
  return Number(val).toFixed(decimals);
}

// ── SHARED RESULTS RENDERER ───────────────────────────────────────────────────
/**
 * Renders a full single-student assessment result into a container element.
 * Used by Option 3 (chat), Option 4 (form), and batch row expansion.
 */
function renderSingleResult(containerId, data, label = null) {
  const el = document.getElementById(containerId);
  if (!el) return;

  const cgpa = data.predicted_cgpa;
  const prob = data.at_risk_probability;
  const riskLabel = data.at_risk_label;
  const isAtRisk = riskLabel === 'At-Risk';
  const career = data.career_readiness;
  const defaulted = data.defaulted_fields || [];
  const disclaimers = data.disclaimers || {};

  const atRiskBannerClass = isAtRisk ? 'atrisk-banner-danger' : 'atrisk-banner-safe';
  const atRiskColor = isAtRisk ? '#E85D75' : '#4CAF7D';
  const atRiskIcon = isAtRisk
    ? `<svg class="w-5 h-5 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`
    : `<svg class="w-5 h-5 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`;

  // Career gauge HTML
  let careerSection = '';
  if (career) {
    const score = career.career_readiness_score;
    const peerAvg = career.peer_benchmark?.peer_avg_readiness;
    const peerGroup = career.peer_benchmark?.peer_group || 'Population';
    const topGap = career.skill_gap_breakdown?.[0];
    const suggestion = career.suggested_focus_area?.suggestion || '';
    const gaugeColor = score >= 65 ? '#4CAF7D' : score >= 40 ? '#F59E0B' : '#E85D75';

    // Skill gap bars
    const gapBars = (career.skill_gap_breakdown || []).slice(0, 6).map(g => {
      const pct = g.percentile_in_branch;
      const barColor = pct >= 60 ? '#4CAF7D' : pct >= 35 ? '#F59E0B' : '#E85D75';
      return `
        <div class="mb-2">
          <div class="flex justify-between text-xs mb-1">
            <span class="text-campus-text">${g.label}</span>
            <span class="text-campus-muted font-medium">${formatFloat(pct, 0)}th %ile</span>
          </div>
          <div class="progress-bar"><div class="progress-fill" style="width:${pct}%;background:${barColor}"></div></div>
        </div>`;
    }).join('');

    careerSection = `
      <div class="result-card mt-4">
        <div class="flex items-center justify-between mb-4">
          <h4 class="sora font-semibold text-campus-text">Career Readiness</h4>
          <span class="text-xs text-campus-muted">${peerGroup}</span>
        </div>
        <div class="flex items-center gap-6 mb-4">
          <div class="text-center">
            <div class="sora text-3xl font-bold" style="color:${gaugeColor}">${formatFloat(score, 1)}</div>
            <div class="text-xs text-campus-muted mt-0.5">/ 100</div>
            <div class="text-xs font-medium mt-1" style="color:${gaugeColor}">Your Score</div>
          </div>
          ${peerAvg !== null && peerAvg !== undefined ? `
          <div class="text-center">
            <div class="sora text-xl font-semibold text-campus-muted">${formatFloat(peerAvg, 1)}</div>
            <div class="text-xs text-campus-muted mt-0.5">/ 100</div>
            <div class="text-xs text-campus-muted mt-1">Peer Average</div>
          </div>` : ''}
        </div>
        <div class="mb-4">${gapBars}</div>
        ${suggestion ? `
        <div class="p-3 rounded-xl bg-campus-blue text-sm text-blue-800 leading-relaxed">
          <span class="font-semibold">Focus area:</span> ${suggestion}
        </div>` : ''}
        <p class="text-xs text-campus-muted mt-3">${disclaimers.career_note || ''}</p>
      </div>`;
  }

  // Defaulted fields disclosure
  let defaultedSection = '';
  if (defaulted.length > 0) {
    const fieldLabels = defaulted.map(f => f.replace('anchor_', '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()));
    defaultedSection = `
      <div class="p-3 rounded-xl bg-campus-lavender border border-[#EDEBFB] text-xs text-campus-muted mt-4">
        <span class="font-semibold text-campus-primary inline-flex items-center gap-1.5">
          <svg class="w-3.5 h-3.5 text-campus-primary flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
          Fields filled with population medians:
        </span>
        ${fieldLabels.slice(0, 8).join(', ')}${fieldLabels.length > 8 ? ` and ${fieldLabels.length - 8} more.` : ''}
      </div>`;
  }

  // GenAI brief cards
  const briefText = data.atrisk_brief?.brief_text || '';
  const summaryText = data.performance_summary?.summary_text || '';
  const narrativeText = data.career_narrative?.narrative_text || '';

  const genaiCards = [
    briefText ? { title: 'At-Risk Mentor Brief', text: briefText, color: isAtRisk ? '#FDEDEF' : '#E7F8EE', border: isAtRisk ? '#E85D75' : '#4CAF7D' } : null,
    summaryText ? { title: 'Academic Trajectory', text: summaryText, color: '#E6F0FE', border: '#6C5CE7' } : null,
    narrativeText ? { title: 'Career Guidance', text: narrativeText, color: '#E7F8EE', border: '#4CAF7D' } : null,
  ].filter(Boolean);

  const genaiHtml = genaiCards.map(card => `
    <div class="result-card" style="border-color:${card.border}40;background:${card.color}40;">
      <h4 class="sora font-semibold text-campus-text mb-2 text-sm">${card.title}</h4>
      <p class="text-sm text-campus-text leading-relaxed">${card.text}</p>
      ${data.atrisk_brief?.is_fallback ? `<p class="text-xs text-campus-muted mt-2 inline-flex items-center gap-1"><svg class="w-3 h-3 text-campus-muted flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> Generated from deterministic template (GenAI unavailable)</p>` : ''}
    </div>`).join('');

  el.innerHTML = `
    <div style="animation: fadeUp 0.4s ease forwards;">
      ${label ? `<div class="flex items-center justify-between mb-4">
        <h3 class="sora font-bold text-xl text-campus-text">${label}</h3>
        <span class="text-xs text-campus-muted bg-campus-lavender px-3 py-1 rounded-full">BYOD Assessment</span>
      </div>` : ''}

      <!-- Top KPI row -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
        <!-- CGPA card -->
        <div class="result-card text-center">
          <div class="text-xs text-campus-muted uppercase tracking-wider mb-2 font-semibold">Predicted CGPA</div>
          <div class="sora text-4xl font-bold text-campus-primary">${formatFloat(cgpa)}</div>
          <div class="text-xs text-campus-muted mt-1">/ 10.0</div>
          <div class="text-xs text-campus-muted mt-3 p-2 bg-campus-lavender rounded-lg leading-snug">
            ${disclaimers.model1_note || 'R²=0.21 — directional signal only'}
          </div>
        </div>

        <!-- At-Risk -->
        <div class="result-card text-center">
          <div class="text-xs text-campus-muted uppercase tracking-wider mb-2 font-semibold">At-Risk Signal</div>
          <div class="sora text-4xl font-bold" style="color:${atRiskColor}">${(prob * 100).toFixed(1)}%</div>
          <div class="text-xs font-semibold mt-1" style="color:${atRiskColor}">${riskLabel}</div>
          <div class="${atRiskBannerClass} mt-3 flex items-start gap-2 text-xs">
            ${atRiskIcon}
            <span>${disclaimers.model2_note || 'Recall=45%, Precision=32%'}</span>
          </div>
        </div>

        <!-- Career score or BYOD note -->
        <div class="result-card text-center">
          <div class="text-xs text-campus-muted uppercase tracking-wider mb-2 font-semibold">Career Readiness</div>
          ${career
            ? `<div class="sora text-4xl font-bold" style="color:${career.career_readiness_score >= 65 ? '#4CAF7D' : career.career_readiness_score >= 40 ? '#F59E0B' : '#E85D75'}">${formatFloat(career.career_readiness_score, 1)}</div>
               <div class="text-xs text-campus-muted mt-1">/ 100</div>`
            : `<div class="sora text-lg font-semibold text-campus-muted mt-4">Not computed</div>
               <div class="text-xs text-campus-muted mt-1">Branch/tier needed for peer normalization</div>`}
          <div class="text-xs text-campus-muted mt-3 p-2 bg-campus-mint rounded-lg leading-snug">
            ${disclaimers.byod_note || 'No DB write — assessment only'}
          </div>
        </div>
      </div>

      ${careerSection}

      <!-- GenAI Briefs -->
      ${genaiHtml ? `
      <div class="mt-4">
        <h4 class="sora font-semibold text-campus-text mb-3">GenAI Insights</h4>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">${genaiHtml}</div>
      </div>` : ''}

      ${defaultedSection}
    </div>`;

  el.classList.remove('hidden');
  el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── BATCH RESULTS RENDERER ────────────────────────────────────────────────────
function renderBatchResults(containerId, data, source = 'csv') {
  const el = document.getElementById(containerId);
  if (!el) return;

  const summary = data.summary || {};
  const results = data.results || [];
  const lineage = data.lineage || null;

  // Summary stats
  const summaryHtml = `
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
      ${summaryCard('Total Rows', summary.total_rows, '')}
      ${summaryCard('Assessed', summary.successfully_assessed, 'text-campus-success')}
      ${summaryCard('Avg CGPA', formatFloat(summary.avg_predicted_cgpa), 'text-campus-primary')}
      ${summaryCard('At-Risk %', summary.pct_flagged_at_risk !== null ? summary.pct_flagged_at_risk + '%' : '—', 'text-campus-danger')}
    </div>`;

  function summaryCard(label, value, colorClass) {
    return `
      <div class="result-card text-center">
        <div class="text-xs text-campus-muted mb-1 uppercase tracking-wider font-semibold">${label}</div>
        <div class="sora text-2xl font-bold ${colorClass} text-campus-text">${value ?? '—'}</div>
      </div>`;
  }

  // Lineage disclosure (Option 2)
  let lineageHtml = '';
  if (lineage) {
    const isApprox = lineage.is_approximate;
    lineageHtml = `
      <div class="mb-5 p-4 rounded-xl ${isApprox ? 'bg-yellow-50 border border-yellow-200' : 'bg-campus-mint border border-green-200'}">
        <div class="flex items-start gap-2">
          <span class="${isApprox ? 'badge-approx' : 'badge-ok'} mt-0.5">${isApprox ? 'Approximate' : 'Real Join'}</span>
          <div>
            <p class="text-sm font-semibold ${isApprox ? 'text-yellow-800' : 'text-green-800'}">${lineage.join_method_label}</p>
            ${isApprox && lineage.approximate_matching_disclosure
              ? `<p class="text-xs text-yellow-700 mt-1 leading-relaxed">${lineage.approximate_matching_disclosure}</p>`
              : ''}
            <p class="text-xs text-campus-muted mt-1">
              Files: ${lineage.files_uploaded?.join(', ')} · ${lineage.stitched_total_rows} stitched rows
            </p>
          </div>
        </div>
      </div>`;
  }

  // Results table
  const tableRows = results.map((r, i) => {
    if (r.error) {
      return `
        <tr class="batch-row">
          <td class="p-3 font-mono text-xs text-campus-muted">${r.row_index}</td>
          <td colspan="4" class="p-3 text-red-600 text-sm">Error: ${r.error}</td>
        </tr>`;
    }
    const a = r.assessment;
    const isRisk = a.at_risk_label === 'At-Risk';
    const riskBadge = isRisk
      ? `<span class="badge-review">At-Risk</span>`
      : `<span class="badge-ok">Safe</span>`;

    const detailRowId = `detail-${containerId}-${i}`;
    return `
      <tr class="batch-row cursor-pointer hover:bg-campus-lavender/40 transition-colors" onclick="toggleBatchDetail('${detailRowId}', '${containerId}', ${i})">
        <td class="p-3 font-mono text-xs text-campus-muted">${r.row_index}</td>
        <td class="p-3 font-semibold text-campus-primary sora">${formatFloat(a.predicted_cgpa)}</td>
        <td class="p-3">${riskBadge}</td>
        <td class="p-3 text-sm text-campus-muted">${(a.at_risk_probability * 100).toFixed(1)}%</td>
        <td class="p-3 text-campus-muted text-xs">
          <svg class="w-4 h-4 inline" id="chevron-${detailRowId}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
          </svg>
        </td>
      </tr>
      <tr class="batch-row-detail" id="${detailRowId}">
        <td colspan="5" class="p-4">
          <div id="detail-content-${detailRowId}">
            <!-- Loaded on expand -->
          </div>
        </td>
      </tr>`;
  }).join('');

  el.innerHTML = `
    <div style="animation: fadeUp 0.4s ease forwards;">
      <h3 class="sora font-bold text-xl text-campus-text mb-4">Batch Assessment Results</h3>
      ${summaryHtml}
      ${lineageHtml}
      <div class="result-card overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full mapping-table">
            <thead>
              <tr>
                <th class="p-3 text-left">#</th>
                <th class="p-3 text-left">Predicted CGPA</th>
                <th class="p-3 text-left">Risk Label</th>
                <th class="p-3 text-left">Risk Prob</th>
                <th class="p-3 text-left">Expand</th>
              </tr>
            </thead>
            <tbody>${tableRows}</tbody>
          </table>
        </div>
      </div>
    </div>`;

  el.classList.remove('hidden');
  el.scrollIntoView({ behavior: 'smooth', block: 'start' });

  // Store results for expand
  el._batchResults = results;
}

// Expand/collapse a batch row detail
function toggleBatchDetail(detailRowId, containerId, idx) {
  const detailRow = document.getElementById(detailRowId);
  const chevron = document.getElementById(`chevron-${detailRowId}`);
  const contentEl = document.getElementById(`detail-content-${detailRowId}`);
  const el = document.getElementById(containerId);
  if (!detailRow || !el) return;

  const isOpen = detailRow.classList.contains('open');
  // Close all others first
  document.querySelectorAll('.batch-row-detail.open').forEach(r => {
    r.classList.remove('open');
    const ch = document.getElementById(`chevron-${r.id}`);
    if (ch) ch.style.transform = '';
  });

  if (!isOpen) {
    detailRow.classList.add('open');
    if (chevron) chevron.style.transform = 'rotate(180deg)';

    // Render the single-student result into the detail content
    const result = el._batchResults?.[idx];
    if (result?.assessment) {
      // We need to render into the contentEl
      const tempId = `temp-${detailRowId}`;
      contentEl.innerHTML = `<div id="${tempId}"></div>`;
      renderSingleResult(tempId, result.assessment, `Row ${result.row_index}`);
    }
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// OPTION 1: CSV Upload with Fuzzy Matching
// ══════════════════════════════════════════════════════════════════════════════
async function handleCSVUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const statusEl = document.getElementById('csv-upload-status');
  statusEl.innerHTML = `<div class="flex items-center gap-2 text-campus-muted text-sm">
    <span class="spinner" style="border-color: rgba(108,92,231,0.3); border-top-color: #6C5CE7;"></span>
    Uploading and analysing columns…
  </div>`;
  statusEl.classList.remove('hidden');

  try {
    const formData = new FormData();
    formData.append('file', file);

    const resp = await fetch(`${API_BASE}/api/assess/csv-match`, { method: 'POST', body: formData });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${resp.status}`);
    }
    const data = await resp.json();

    state.csvPreviewId = data.preview_id;
    state.csvMappingData = data.mapping_preview;

    // Count needs-review
    const needsReview = data.mapping_preview.filter(m => m.needs_review).length;
    document.getElementById('csv-mapping-stats').textContent =
      `${data.total_rows} rows · ${data.columns_detected} columns · ${needsReview > 0 ? needsReview + ' needs review' : 'All matched'}`;

    if (needsReview > 0) {
      document.getElementById('csv-review-banner-text').textContent =
        `${needsReview} column(s) have low match confidence (< 70%) and are highlighted in red. Please review and select the correct feature from the dropdown before proceeding.`;
      document.getElementById('csv-review-banner').classList.remove('hidden');
    }

    renderMappingTable(data.mapping_preview, data.schema_features);
    document.getElementById('csv-step-mapping').classList.remove('hidden');
    statusEl.classList.add('hidden');

  } catch (err) {
    statusEl.innerHTML = '';
    showError('csv-upload-status', `Upload failed: ${err.message}`);
    statusEl.classList.remove('hidden');
  }
}

function renderMappingTable(mappings, schemaFeatures) {
  const tbody = document.getElementById('csv-mapping-tbody');

  const optionsHtml = ['__skip__ (ignore this column)', ...schemaFeatures]
    .map(f => `<option value="${f === '__skip__ (ignore this column)' ? '__skip__' : f}">${f}</option>`)
    .join('');

  tbody.innerHTML = mappings.map((m, idx) => {
    const confidence = m.confidence;
    const badge = m.needs_review
      ? `<span class="badge-review inline-flex items-center gap-1"><svg class="w-3 h-3 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg> Review (${confidence.toFixed(0)}%)</span>`
      : `<span class="badge-ok inline-flex items-center gap-1"><svg class="w-3 h-3 text-emerald-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg> ${confidence.toFixed(0)}%</span>`;

    const selectedOption = m.matched_to_feature || '__skip__';
    const selectHtml = `
      <select id="mapping-select-${idx}" class="form-input text-xs py-1.5" style="min-width:200px;"
        onchange="updateMapping(${idx}, this.value)">
        ${['__skip__ (ignore this column)', ...schemaFeatures].map(f => {
          const val = f === '__skip__ (ignore this column)' ? '__skip__' : f;
          return `<option value="${val}" ${val === selectedOption ? 'selected' : ''}>${f}</option>`;
        }).join('')}
      </select>`;

    const sampleVals = (m.sample_values || []).slice(0, 3).join(', ') || '—';
    const rowBg = m.needs_review ? 'style="background:#FFF5F5;"' : '';

    return `<tr ${rowBg}>
      <td class="p-3 font-mono font-semibold text-campus-text">${m.uploaded_column}</td>
      <td class="p-3">${selectHtml}</td>
      <td class="p-3">${badge}</td>
      <td class="p-3 text-campus-muted font-mono text-xs">${sampleVals}</td>
      <td class="p-3">&nbsp;</td>
    </tr>`;
  }).join('');
}

function updateMapping(idx, value) {
  if (state.csvMappingData[idx]) {
    state.csvMappingData[idx].matched_to_feature = value;
  }
}

async function confirmCSVMapping() {
  if (!state.csvPreviewId) {
    showError('csv-upload-status', 'No preview session found. Please re-upload the CSV.');
    return;
  }

  // Build finalized mapping from dropdowns
  const finalMapping = state.csvMappingData.map((m, idx) => {
    const select = document.getElementById(`mapping-select-${idx}`);
    return {
      uploaded_column: m.uploaded_column,
      matched_to_feature: select ? select.value : (m.matched_to_feature || '__skip__'),
    };
  });

  const btn = document.getElementById('csv-confirm-btn');
  showLoading(btn, 'Running assessment…');

  document.getElementById('csv-step-mapping').classList.add('hidden');
  document.getElementById('csv-step-processing').classList.remove('hidden');

  const procContainer = document.getElementById('csv-step-processing');
  procContainer.classList.remove('hidden');
  document.getElementById('csv-step-mapping').classList.add('hidden');

  const tracker = renderRealProgressBar('csv-step-processing', {
    prefix: 'csv-prog',
    title: 'Processing Batch CSV Assessment',
    initialDetail: 'Applying finalized column mapping...',
  });

  let p = 15;
  tracker.setProgress(15, 'Applying Column Mapping', 'Mapping uploaded headers to warehouse schema...', 2);
  const timer = setInterval(() => {
    p += 3;
    if (p >= 35 && p < 65) {
      tracker.setProgress(p, 'Processing Student Records', 'Engineering interaction features...', 3);
    } else if (p >= 65 && p < 92) {
      tracker.setProgress(p, 'Running ML Models', 'Evaluating CGPA regression and at-risk classification...', 4);
    }
    if (p >= 92) clearInterval(timer);
  }, 120);

  try {
    const resp = await fetch(`${API_BASE}/api/assess/csv-match/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preview_id: state.csvPreviewId, mapping: finalMapping }),
    });
    clearInterval(timer);
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${resp.status}`);
    }
    const data = await resp.json();
    const count = data.summary?.total_rows || data.results?.length || 0;
    tracker.setComplete(`Batch Complete! Assessed ${count.toLocaleString()} students`);

    setTimeout(() => {
      procContainer.classList.add('hidden');
      restoreButton(btn);
      renderBatchResults('csv-batch-results', data, 'csv');
    }, 500);

  } catch (err) {
    clearInterval(timer);
    procContainer.classList.add('hidden');
    document.getElementById('csv-step-mapping').classList.remove('hidden');
    restoreButton(btn);
    showError('csv-upload-status', `Assessment failed: ${err.message}`);
    document.getElementById('csv-upload-status').classList.remove('hidden');
  }
}

function resetCSVFlow() {
  state.csvPreviewId = null;
  state.csvMappingData = [];
  document.getElementById('csv-step-mapping').classList.add('hidden');
  document.getElementById('csv-batch-results').classList.add('hidden');
  document.getElementById('csv-upload-status').classList.add('hidden');
  document.getElementById('csv-review-banner').classList.add('hidden');
  document.getElementById('csv-file-input').value = '';
}

// ══════════════════════════════════════════════════════════════════════════════
// OPTION 2: Multi-CSV Stitching
// ══════════════════════════════════════════════════════════════════════════════

const ID_CANDIDATES = [
  'student_id', 'roll_no', 'roll_number', 'student_no', 'studentid',
  'enrollment_id', 'reg_no', 'registration_no', 'id', 'student', 'email'
];

function parseCsvLine(text) {
  if (!text) return [];
  const result = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') {
      if (inQuotes && text[i + 1] === '"') {
        cur += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (c === ',' && !inQuotes) {
      result.push(cur.trim());
      cur = '';
    } else {
      cur += c;
    }
  }
  result.push(cur.trim());
  return result.map(h => h.replace(/^["']|["']$/g, '').trim()).filter(Boolean);
}

async function parseCsvSummary(file) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = function(e) {
      try {
        const text = e.target.result || '';
        const lines = text.split(/\r?\n/).filter(line => line.trim().length > 0);
        if (lines.length === 0) {
          resolve({ file, name: file.name, size: file.size, rows: 0, cols: 0, headers: [] });
          return;
        }
        const headers = parseCsvLine(lines[0]);
        const rowCount = Math.max(0, lines.length - 1);
        resolve({
          file,
          name: file.name,
          size: file.size,
          rows: rowCount,
          cols: headers.length,
          headers
        });
      } catch (_) {
        resolve({ file, name: file.name, size: file.size, rows: 0, cols: 0, headers: [] });
      }
    };
    reader.onerror = function() {
      resolve({ file, name: file.name, size: file.size, rows: 0, cols: 0, headers: [] });
    };
    reader.readAsText(file);
  });
}

function analyzeStitchKeys(summaries) {
  if (!summaries || summaries.length === 0) {
    return { primaryKey: null, keyType: 'none', title: '', description: '', fileKeyMap: {} };
  }

  const fileKeyMap = {};
  const fileLowerHeaders = summaries.map(s => s.headers.map(h => h.toLowerCase()));

  // 1a: Check if an ID candidate is present across ALL files (case-insensitive)
  for (const candidate of ID_CANDIDATES) {
    const allHaveCandidate = summaries.every(s => {
      const match = s.headers.find(h => h.toLowerCase() === candidate);
      if (match) fileKeyMap[s.name] = match;
      return !!match;
    });
    if (allHaveCandidate) {
      return {
        primaryKey: candidate,
        keyType: 'exact_id',
        title: `Primary Stitch Key: "${candidate}"`,
        description: `Direct key join identified across all ${summaries.length} files. Records will be matched and merged directly on "${candidate}".`,
        badgeText: `Stitch Key: ${candidate}`,
        fileKeyMap
      };
    }
  }

  // 1b: Check common columns across all files
  let commonHeaders = fileLowerHeaders[0] || [];
  for (let i = 1; i < fileLowerHeaders.length; i++) {
    commonHeaders = commonHeaders.filter(h => fileLowerHeaders[i].includes(h));
  }
  if (commonHeaders.length > 0) {
    const idLike = commonHeaders.find(h => ID_CANDIDATES.includes(h) || h.includes('id') || h.includes('roll'));
    const chosen = idLike || commonHeaders[0];
    summaries.forEach(s => {
      const orig = s.headers.find(h => h.toLowerCase() === chosen);
      fileKeyMap[s.name] = orig || chosen;
    });
    return {
      primaryKey: chosen,
      keyType: 'shared_column',
      title: `Shared Column Detected: "${chosen}"`,
      description: `All ${summaries.length} files share the "${chosen}" column. Records will be stitched across datasets using this shared field.`,
      badgeText: `Stitch Column: ${chosen}`,
      fileKeyMap
    };
  }

  // 1c: Check if every file has SOME identifier candidate
  const individualMatches = {};
  let allHaveAnId = true;
  summaries.forEach(s => {
    const match = s.headers.find(h => {
      const low = h.toLowerCase();
      return ID_CANDIDATES.includes(low) || low.includes('student') || low.includes('id') || low.includes('roll');
    });
    if (match) {
      individualMatches[s.name] = match;
    } else {
      allHaveAnId = false;
    }
  });

  if (allHaveAnId) {
    const keysFound = [...new Set(Object.values(individualMatches))];
    return {
      primaryKey: keysFound.join(' ↔ '),
      keyType: 'mapped_ids',
      title: `Mapped Student Identifiers: ${keysFound.join(' ↔ ')}`,
      description: `Campus360 detected student identifier columns in each dataset (${keysFound.join(', ')}). The engine will automatically align and join student profiles on these keys.`,
      badgeText: `Mapped Key`,
      fileKeyMap: individualMatches
    };
  }

  // 1d: Fallback profile matching
  summaries.forEach(s => {
    const match = s.headers.find(h => ID_CANDIDATES.includes(h.toLowerCase()) || h.toLowerCase().includes('id'));
    if (match) fileKeyMap[s.name] = match;
  });

  return {
    primaryKey: 'Profile Attributes',
    keyType: 'profile_match',
    title: 'Profile-Based Cross Attribute Stitching',
    description: 'No universal ID column was detected across all files. Campus360 will stitch records using multi-attribute profile matching, academic tiers, and cohort performance bands.',
    badgeText: 'Profile Match',
    fileKeyMap
  };
}

function renderStitchBasket() {
  const listEl = document.getElementById('stitch-file-list');
  const runBtn = document.getElementById('stitch-run-btn');
  const statusEl = document.getElementById('stitch-status');
  if (!listEl) return;

  const summaries = state.stitchSummaries || [];
  if (summaries.length === 0) {
    listEl.classList.add('hidden');
    listEl.innerHTML = '';
    if (runBtn) runBtn.classList.add('hidden');
    if (statusEl) statusEl.classList.add('hidden');
    return;
  }

  listEl.classList.remove('hidden');

  const totalFiles = summaries.length;
  const totalRows = summaries.reduce((acc, s) => acc + (s.rows || 0), 0);
  const totalBytes = summaries.reduce((acc, s) => acc + (s.size || 0), 0);
  const totalMB = (totalBytes / (1024 * 1024)).toFixed(1);

  const keyInfo = analyzeStitchKeys(summaries);
  state.stitchKeyInfo = keyInfo;

  let keyBannerHtml = '';
  if (keyInfo.keyType === 'exact_id' || keyInfo.keyType === 'shared_column') {
    keyBannerHtml = `
      <div class="stitch-key-banner my-3.5">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-xl bg-campus-lavender text-campus-primary flex items-center justify-center flex-shrink-0 shadow-sm">
            <svg class="w-4 h-4 text-campus-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          </div>
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-xs font-semibold uppercase tracking-wider text-campus-primary">Stitching Column:</span>
              <span class="font-mono font-bold text-xs bg-white px-2.5 py-0.5 rounded-md text-campus-primary border border-campus-primary/30 shadow-sm">${keyInfo.primaryKey}</span>
              <span class="text-[11px] bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full font-semibold border border-emerald-200 flex items-center gap-1">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
                Common key across all ${totalFiles} CSVs
              </span>
            </div>
            <p class="text-xs text-campus-muted mt-1 leading-normal">${keyInfo.description}</p>
          </div>
        </div>
      </div>
    `;
  } else if (keyInfo.keyType === 'mapped_ids') {
    keyBannerHtml = `
      <div class="stitch-key-banner my-3.5">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-xl bg-campus-lavender text-campus-primary flex items-center justify-center flex-shrink-0 shadow-sm">
            <svg class="w-4 h-4 text-campus-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
          </div>
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-xs font-semibold uppercase tracking-wider text-campus-primary">Stitching Keys:</span>
              <span class="font-mono font-bold text-xs bg-white px-2 py-0.5 rounded-md text-campus-primary border border-campus-primary/30">${keyInfo.primaryKey}</span>
              <span class="text-[11px] bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full font-semibold border border-blue-200">Auto-Harmonized</span>
            </div>
            <p class="text-xs text-campus-muted mt-1 leading-normal">${keyInfo.description}</p>
          </div>
        </div>
      </div>
    `;
  } else {
    keyBannerHtml = `
      <div class="stitch-key-banner my-3.5" style="border-color: rgba(245, 158, 11, 0.4); background: rgba(254, 243, 199, 0.45);">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center flex-shrink-0 shadow-sm">
            <svg class="w-4 h-4 text-amber-800" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-xs font-semibold uppercase tracking-wider text-amber-900">Stitching Mode:</span>
              <span class="font-bold text-xs bg-white px-2 py-0.5 rounded-md text-amber-950 border border-amber-300">Multi-Attribute Profile Alignment</span>
            </div>
            <p class="text-xs text-amber-900 mt-1 leading-normal">${keyInfo.description}</p>
          </div>
        </div>
      </div>
    `;
  }

  const cardsHtml = summaries.map((s, idx) => {
    const sizeKB = (s.size / 1024).toFixed(1);
    const sizeStr = s.size > 1024 * 1024 ? `${(s.size / (1024 * 1024)).toFixed(2)} MB` : `${sizeKB} KB`;
    const matchedKey = keyInfo.fileKeyMap[s.name];

    const maxChips = 5;
    const chips = s.headers.slice(0, maxChips).map(col => {
      const isKey = matchedKey && (col.toLowerCase() === matchedKey.toLowerCase());
      if (isKey) {
        return `<span class="stitch-chip stitch-chip-key inline-flex items-center gap-1" title="Stitch Key Column"><svg class="w-2.5 h-2.5 text-white flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" /></svg>${col}</span>`;
      }
      return `<span class="stitch-chip" title="${col}">${col}</span>`;
    }).join(' ');

    const remainingCols = s.headers.length > maxChips
      ? `<span class="text-[11px] text-campus-muted font-medium ml-1">+${s.headers.length - maxChips} more</span>`
      : '';

    return `
      <div class="stitch-file-card flex flex-col justify-between">
        <div>
          <div class="flex items-start justify-between gap-2 mb-2">
            <div class="flex items-center gap-2 min-w-0">
              <div class="w-7 h-7 rounded-lg bg-campus-lavender text-campus-primary flex items-center justify-center flex-shrink-0">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
              </div>
              <div class="min-w-0">
                <div class="font-mono font-semibold text-xs text-campus-text truncate" title="${s.name}">${s.name}</div>
                <div class="text-[11px] text-campus-muted">${sizeStr}</div>
              </div>
            </div>
            <button onclick="removeStitchFile(${idx})" title="Remove this CSV from basket" class="text-campus-muted hover:text-red-500 hover:bg-red-50 w-6 h-6 rounded-md flex items-center justify-center transition-colors">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>

          <div class="flex items-center gap-2 mb-2.5 flex-wrap">
            <span class="stitch-badge-row" title="${s.rows.toLocaleString()} Rows in CSV">
              <svg class="w-3.5 h-3.5 text-campus-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"/></svg>
              ${s.rows.toLocaleString()} rows
            </span>
            <span class="stitch-badge-col" title="${s.cols} Columns in CSV">
              <svg class="w-3.5 h-3.5 text-campus-mint" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 4v16m6-16v16"/></svg>
              ${s.cols} columns
            </span>
            ${matchedKey ? `
              <span class="stitch-key-badge text-[11px] inline-flex items-center gap-1" title="Stitching on key: ${matchedKey}">
                <svg class="w-3 h-3 text-white flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                </svg>
                Key: ${matchedKey}
              </span>
            ` : ''}
          </div>
        </div>

        <div class="mt-1 pt-2.5 border-t border-slate-100">
          <div class="text-[10px] uppercase font-bold tracking-wider text-campus-muted mb-1.5 flex items-center justify-between">
            <span>Columns Preview</span>
            ${matchedKey ? `<span class="text-campus-primary lowercase text-[10px] font-semibold">join key: <strong>${matchedKey}</strong></span>` : ''}
          </div>
          <div class="flex items-center flex-wrap gap-1.5">
            ${chips}
            ${remainingCols}
          </div>
        </div>
      </div>
    `;
  }).join('');

  listEl.innerHTML = `
    <div class="stitch-basket">
      <div class="stitch-basket-top">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-campus-lavender text-campus-primary flex items-center justify-center font-bold flex-shrink-0 shadow-sm">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
            </svg>
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h3 class="sora font-bold text-base text-campus-text">Dataset Basket</h3>
              <span class="px-2.5 py-0.5 rounded-full bg-campus-primary text-white font-bold text-xs">${totalFiles} CSV${totalFiles > 1 ? 's' : ''}</span>
            </div>
            <p class="text-xs text-campus-muted mt-0.5">${totalRows.toLocaleString()} total student records &bull; ${totalMB} MB staged in basket</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button onclick="document.getElementById('stitch-file-input').click()" class="text-xs font-semibold px-3 py-1.5 rounded-lg border border-campus-primary/30 text-campus-primary hover:bg-campus-lavender transition-colors flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
            Add More CSVs
          </button>
          <button onclick="clearStitchBasket()" class="text-xs font-semibold px-3 py-1.5 rounded-lg text-campus-muted hover:text-red-500 hover:bg-red-50 transition-colors">
            Clear Basket
          </button>
        </div>
      </div>

      ${keyBannerHtml}

      <div class="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        ${cardsHtml}
      </div>
    </div>
  `;

  if (runBtn) {
    if (totalFiles >= 2) {
      runBtn.classList.remove('hidden');
      runBtn.innerHTML = `Stitch &amp; Assess Datasets (${totalFiles} CSVs &bull; ${totalRows.toLocaleString()} Rows) →`;
    } else {
      runBtn.classList.add('hidden');
      if (statusEl) {
        statusEl.innerHTML = `<div class="p-3 rounded-xl bg-amber-50 text-amber-900 border border-amber-200 text-xs">Please add at least 1 more CSV file to the basket to enable stitching.</div>`;
        statusEl.classList.remove('hidden');
      }
    }
  }
}

function removeStitchFile(index) {
  if (!state.stitchSummaries || !state.stitchFiles) return;
  state.stitchSummaries.splice(index, 1);
  state.stitchFiles.splice(index, 1);
  renderStitchBasket();
}

function clearStitchBasket() {
  state.stitchFiles = [];
  state.stitchSummaries = [];
  state.stitchKeyInfo = null;
  const fileInput = document.getElementById('stitch-file-input');
  if (fileInput) fileInput.value = '';
  renderStitchBasket();
}

async function handleStitchUpload(event) {
  const incomingFiles = Array.from(event.target.files || []);
  if (incomingFiles.length === 0) return;

  const listEl = document.getElementById('stitch-file-list');
  listEl.classList.remove('hidden');
  listEl.innerHTML = `
    <div class="stitch-basket flex items-center justify-center py-6 gap-3 text-campus-primary">
      <svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <span class="sora text-sm font-semibold">Inspecting CSV structures, counting rows &amp; detecting stitch keys…</span>
    </div>
  `;

  const existingFiles = state.stitchFiles || [];
  const existingSummaries = state.stitchSummaries || [];

  const existingKeys = new Set(existingFiles.map(f => `${f.name}-${f.size}`));
  const newFiles = incomingFiles.filter(f => !existingKeys.has(`${f.name}-${f.size}`));

  const newSummaries = await Promise.all(newFiles.map(f => parseCsvSummary(f)));

  state.stitchFiles = [...existingFiles, ...newFiles];
  state.stitchSummaries = [...existingSummaries, ...newSummaries];

  renderStitchBasket();
}

async function runStitchAssessment() {
  if (!state.stitchFiles || state.stitchFiles.length < 2) return;

  const btn = document.getElementById('stitch-run-btn');
  showLoading(btn, 'Stitching & assessing…');

  const totalBytes = state.stitchFiles.reduce((acc, f) => acc + f.size, 0);
  const totalMB = (totalBytes / (1024 * 1024)).toFixed(1);
  const detectedKey = state.stitchKeyInfo?.primaryKey || 'student_id';

  const tracker = renderRealProgressBar('stitch-status', {
    prefix: 'stitch-prog',
    title: `Stitching ${state.stitchFiles.length} Datasets (${totalMB} MB)`,
    initialDetail: `Transferring files and locking stitch key "${detectedKey}"...`,
    steps: [
      '1. Transfer Datasets',
      '2. Parse & Extract Keys',
      '3. Stitch Student Records',
      '4. Dual ML Pipelines'
    ]
  });

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/api/assess/csv-stitch`);

    let processingTimer = null;

    // Real byte-level upload progress (0% - 35%)
    xhr.upload.onprogress = function(e) {
      if (e.lengthComputable) {
        const fraction = e.loaded / e.total;
        const uploadPct = Math.min(35, Math.round(fraction * 35));
        const transferredMB = (e.loaded / (1024 * 1024)).toFixed(1);
        tracker.setProgress(
          uploadPct,
          `Uploading ${state.stitchFiles.length} Files (${transferredMB}/${totalMB} MB)`,
          `${Math.round(fraction * 100)}% transferred to server...`,
          1
        );
      }
    };

    xhr.upload.onload = function() {
      // Upload finished! Smoothly advance through server processing stages
      tracker.setProgress(38, 'Files Received by Engine', `Extracting headers and validating stitch key "${detectedKey}"...`, 2);

      let p = 38;
      processingTimer = setInterval(() => {
        p += 2;
        if (p >= 46 && p < 66) {
          tracker.setProgress(p, 'Stitching Student Records', `Joining datasets on "${detectedKey}" across performance bands...`, 3);
        } else if (p >= 66 && p < 86) {
          tracker.setProgress(p, 'Running ML Pipeline', 'Evaluating Model 1 (CGPA) & Model 2 (Risk Classifier)...', 4);
        } else if (p >= 86 && p < 96) {
          tracker.setProgress(p, 'Aggregating Cohort Metrics', 'Synthesizing distribution statistics and risk alerts...', 4);
        }
        if (p >= 95) {
          clearInterval(processingTimer);
        }
      }, 180);
    };

    xhr.onload = function() {
      if (processingTimer) clearInterval(processingTimer);

      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          const rowCount = data.summary?.total_rows || data.results?.length || 0;
          tracker.setComplete(`Completed! Successfully stitched and assessed ${rowCount.toLocaleString()} records`);

          setTimeout(() => {
            const statusEl = document.getElementById('stitch-status');
            if (statusEl) statusEl.classList.add('hidden');
            restoreButton(btn);
            renderBatchResults('stitch-batch-results', data, 'stitch');
            resolve(data);
          }, 600);
        } catch (e) {
          restoreButton(btn);
          showError('stitch-status', 'Failed to parse assessment response: ' + e.message);
          reject(e);
        }
      } else {
        restoreButton(btn);
        let errDetail = `Server error (${xhr.status})`;
        try {
          const errObj = JSON.parse(xhr.responseText);
          if (errObj.detail) errDetail = errObj.detail;
        } catch (_) {}
        showError('stitch-status', `Stitch assessment failed: ${errDetail}`);
        reject(new Error(errDetail));
      }
    };

    xhr.onerror = function() {
      if (processingTimer) clearInterval(processingTimer);
      restoreButton(btn);
      showError('stitch-status', 'Network error during stitch assessment. Please check your connection.');
      reject(new Error('Network error'));
    };

    const formData = new FormData();
    state.stitchFiles.forEach(f => formData.append('files', f));
    xhr.send(formData);
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// OPTION 3: Chat-Guided Input
// ══════════════════════════════════════════════════════════════════════════════
function initChatUI() {
  // Show start button, hide input area
  document.getElementById('chat-start-area').classList.remove('hidden');
  document.getElementById('chat-input-area').classList.add('hidden');
  document.getElementById('chat-input-area').style.display = 'none';

  addBotMessage(`Welcome! I'm going to walk you through a guided assessment — asking about your academics, lifestyle, and skills one step at a time.\n\nYou can type **"skip"** at any time if you don't know an answer, and I'll use population averages for that field.\n\nWhenever you're ready, click **Start** below.`);
}

async function startChatSession() {
  const startArea = document.getElementById('chat-start-area');
  const inputArea = document.getElementById('chat-input-area');

  startArea.classList.add('hidden');
  inputArea.classList.remove('hidden');
  inputArea.style.display = 'flex';

  // Kick off session (empty message to trigger first question)
  const btn = document.getElementById('chat-send-btn');
  showLoading(btn, '');

  try {
    const resp = await fetch(`${API_BASE}/api/assess/chat-guided`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: null, message: '__init__', student_label: 'You' }),
    });
    if (!resp.ok) throw new Error(`Server error ${resp.status}`);
    const data = await resp.json();

    state.chatSessionId = data.session_id;
    addBotMessage(data.bot_message);
    updateChatProgress(data.question_index, data.total_questions);
    restoreButton(btn);
    document.getElementById('chat-input').focus();

  } catch (err) {
    addBotMessage(`Failed to start session: ${err.message}. Please refresh and try again.`);
    restoreButton(btn);
  }
}

async function sendChatMessage() {
  const inputEl = document.getElementById('chat-input');
  const message = inputEl.value.trim();
  if (!message || !state.chatSessionId) return;

  // Add user bubble
  addUserMessage(message);
  inputEl.value = '';

  const btn = document.getElementById('chat-send-btn');
  showLoading(btn, '');
  inputEl.disabled = true;

  try {
    const resp = await fetch(`${API_BASE}/api/assess/chat-guided`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: state.chatSessionId, message }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${resp.status}`);
    }
    const data = await resp.json();

    addBotMessage(data.bot_message);
    updateChatProgress(data.question_index, data.total_questions);

    if (data.session_complete) {
      // Session done — hide input, show results
      document.getElementById('chat-input-area').style.display = 'none';
      state.chatSessionId = null;
      if (data.assessment_result) {
        const resultEl = document.getElementById('chat-result');
        resultEl.innerHTML = `<div id="chat-result-inner"></div>`;
        resultEl.classList.remove('hidden');
        renderSingleResult('chat-result-inner', data.assessment_result, 'Your Assessment Results');
      }
    } else {
      state.chatSessionId = data.session_id;
    }

  } catch (err) {
    addBotMessage(`Error: ${err.message}. Try again.`);
  }

  restoreButton(btn);
  inputEl.disabled = false;
  inputEl.focus();

  // Auto-scroll chat
  const chatEl = document.getElementById('chat-messages');
  chatEl.scrollTop = chatEl.scrollHeight;
}

function addBotMessage(text) {
  const chatEl = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'flex items-start gap-2.5';

  // Format **bold** markdown
  const formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');

  div.innerHTML = `
    <div class="w-8 h-8 rounded-full bg-campus-lavender flex items-center justify-center flex-shrink-0 mt-0.5">
      <svg class="w-4 h-4 text-campus-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
      </svg>
    </div>
    <div class="chat-bubble-bot text-sm">${formatted}</div>`;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

function addUserMessage(text) {
  const chatEl = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'flex justify-end';
  div.innerHTML = `<div class="chat-bubble-user text-sm">${text}</div>`;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

function updateChatProgress(qIdx, total) {
  const pct = total ? Math.round((qIdx / total) * 100) : 0;
  document.getElementById('chat-progress-bar').style.width = `${pct}%`;
  document.getElementById('chat-progress-label').textContent =
    qIdx >= total ? 'Assessment complete!' : `Question ${qIdx} of ${total} (${pct}%)`;
}

// ══════════════════════════════════════════════════════════════════════════════
// OPTION 4: Direct Form Entry
// ══════════════════════════════════════════════════════════════════════════════
async function submitDirectForm(event) {
  event.preventDefault();
  const form = document.getElementById('direct-form');
  const btn = document.getElementById('form-submit-btn');
  const resultEl = document.getElementById('form-result');
  resultEl.classList.add('hidden');

  showLoading(btn, 'Running assessment…');

  // Collect non-empty fields
  const formData = new FormData(form);
  const body = {};
  formData.forEach((value, key) => {
    if (value !== '' && value !== null) {
      if (key === 'student_label' || key === 'branch') {
        body[key] = value;
      } else {
        const num = parseFloat(value);
        if (!isNaN(num)) body[key] = num;
      }
    }
  });

  try {
    const resp = await fetch(`${API_BASE}/api/assess/new-student`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${resp.status}`);
    }
    const data = await resp.json();

    restoreButton(btn);
    resultEl.innerHTML = `<div id="form-result-inner"></div>`;
    resultEl.classList.remove('hidden');
    renderSingleResult('form-result-inner', data, body.student_label || 'Assessment Results');

  } catch (err) {
    restoreButton(btn);
    resultEl.innerHTML = `
      <div class="p-4 rounded-xl bg-campus-coral border border-campus-danger/30 text-red-700 text-sm">
        Assessment failed: ${err.message}
      </div>`;
    resultEl.classList.remove('hidden');
  }
}

// ── Drag and Drop ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setupDropZone('csv-dropzone', 'csv-file-input', false, handleCSVUpload);
  setupDropZone('stitch-dropzone', 'stitch-file-input', true, handleStitchUpload);
});

function setupDropZone(zoneId, inputId, multiple, handler) {
  const zone = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  if (!zone || !input) return;

  zone.addEventListener('dragover', e => {
    e.preventDefault();
    zone.classList.add('dragover');
  });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('dragover');
    const files = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.csv'));
    if (!files.length) return;

    // Simulate file input
    const dt = new DataTransfer();
    if (multiple) {
      files.forEach(f => dt.items.add(f));
    } else {
      dt.items.add(files[0]);
    }
    input.files = dt.files;
    handler({ target: { files: multiple ? files : [files[0]] } });
  });
}
