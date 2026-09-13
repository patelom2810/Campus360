/**
 * Campus360 — Bring Your Own Data Assessment
 * assess.js — All 4 option flows + shared results renderer
 */

const API_BASE = (window.location.port === '8501' || window.location.port === '5500' || window.location.port === '3000')
  ? 'http://localhost:8000'
  : '';

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  activeOption: null,
  csvPreviewId: null,
  csvMappingData: [],
  stitchFiles: [],
  chatSessionId: null,
  chartInstances: {},
};

// ── Navigation ────────────────────────────────────────────────────────────────
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
  document.getElementById('single-result-container').classList.add('hidden');

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
  document.getElementById('option-grid').scrollIntoView({ behavior: 'smooth' });
}

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
        <span class="font-semibold text-campus-primary">⚠ Fields filled with population medians:</span>
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
      ${data.atrisk_brief?.is_fallback ? `<p class="text-xs text-campus-muted mt-2">✦ Generated from deterministic template (GenAI unavailable)</p>` : ''}
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
      `${data.total_rows} rows · ${data.columns_detected} columns · ${needsReview > 0 ? needsReview + ' needs review' : 'All matched ✓'}`;

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
      ? `<span class="badge-review">⚠ Review (${confidence.toFixed(0)}%)</span>`
      : `<span class="badge-ok">✓ ${confidence.toFixed(0)}%</span>`;

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

  try {
    const resp = await fetch(`${API_BASE}/api/assess/csv-match/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preview_id: state.csvPreviewId, mapping: finalMapping }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${resp.status}`);
    }
    const data = await resp.json();

    document.getElementById('csv-step-processing').classList.add('hidden');
    restoreButton(btn);
    renderBatchResults('csv-batch-results', data, 'csv');

  } catch (err) {
    document.getElementById('csv-step-processing').classList.add('hidden');
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
function handleStitchUpload(event) {
  const files = Array.from(event.target.files);
  state.stitchFiles = files;

  const listEl = document.getElementById('stitch-file-list');
  listEl.innerHTML = `
    <div class="p-3 rounded-xl bg-campus-lavender">
      <p class="text-sm font-semibold text-campus-text mb-2">${files.length} file(s) selected:</p>
      <ul class="space-y-1">
        ${files.map((f, i) => `
          <li class="flex items-center gap-2 text-sm text-campus-muted">
            <svg class="w-4 h-4 text-campus-primary flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
            <span class="font-mono">${f.name}</span>
            <span class="text-xs">(${(f.size / 1024).toFixed(1)} KB)</span>
          </li>`).join('')}
      </ul>
    </div>`;
  listEl.classList.remove('hidden');

  const runBtn = document.getElementById('stitch-run-btn');
  if (files.length >= 2) {
    runBtn.classList.remove('hidden');
  } else {
    runBtn.classList.add('hidden');
    const statusEl = document.getElementById('stitch-status');
    statusEl.innerHTML = `<div class="text-sm text-campus-muted">Please select at least 2 CSV files.</div>`;
    statusEl.classList.remove('hidden');
  }
}

async function runStitchAssessment() {
  if (state.stitchFiles.length < 2) return;

  const btn = document.getElementById('stitch-run-btn');
  const statusEl = document.getElementById('stitch-status');

  showLoading(btn, 'Stitching and assessing…');
  statusEl.innerHTML = `<div class="flex items-center gap-2 text-campus-muted text-sm">
    <span class="spinner" style="border-color:rgba(108,92,231,0.3);border-top-color:#6C5CE7;"></span>
    Joining datasets and running assessment…
  </div>`;
  statusEl.classList.remove('hidden');

  try {
    const formData = new FormData();
    state.stitchFiles.forEach(f => formData.append('files', f));

    const resp = await fetch(`${API_BASE}/api/assess/csv-stitch`, { method: 'POST', body: formData });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${resp.status}`);
    }
    const data = await resp.json();

    statusEl.classList.add('hidden');
    restoreButton(btn);
    renderBatchResults('stitch-batch-results', data, 'stitch');

  } catch (err) {
    statusEl.innerHTML = '';
    showError('stitch-status', `Stitch assessment failed: ${err.message}`);
    statusEl.classList.remove('hidden');
    restoreButton(btn);
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// OPTION 3: Chat-Guided Input
// ══════════════════════════════════════════════════════════════════════════════
function initChatUI() {
  // Show start button, hide input area
  document.getElementById('chat-start-area').classList.remove('hidden');
  document.getElementById('chat-input-area').classList.add('hidden');
  document.getElementById('chat-input-area').style.display = 'none';

  addBotMessage(`👋 Welcome! I'm going to walk you through a guided assessment — asking about your academics, lifestyle, and skills one step at a time.\n\nYou can type **"skip"** at any time if you don't know an answer, and I'll use population averages for that field.\n\nWhenever you're ready, click **Start** below.`);
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
    addBotMessage(`❌ Failed to start session: ${err.message}. Please refresh and try again.`);
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
    addBotMessage(`❌ Error: ${err.message}. Try again.`);
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
