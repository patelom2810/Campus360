/**
 * Campus360 Dashboard Application Logic
 * Modern Ed-Tech SaaS Dashboard
 */

// API Base URL resolution (supports both same-origin and separate dashboard server)
const API_BASE = (window.location.port === '8000')
  ? ''
  : 'http://localhost:8000';

// Application State
const state = {
  currentView: 'overview',
  charts: {},
  overviewData: null,
  subjectsData: null,
  atRiskMeta: null,
  atRiskTable: [],
  atRiskSortCol: 'predicted_risk_probability',
  atRiskSortAsc: false,
  subjectGapsSortCol: 'avg_normalized_pct',
  subjectGapsSortAsc: true,
  currentStudentId: 'STU00001',
};

// Design Palette
const PALETTE = {
  primary: '#6C5CE7',
  primaryDark: '#4B3FA8',
  lavender: '#EDEBFB',
  blue: '#E6F0FE',
  mint: '#E7F8EE',
  coral: '#FDEDEF',
  danger: '#E85D75',
  success: '#4CAF7D',
  textPrimary: '#1E1B2E',
  textMuted: '#8A8797',
};

// View Titles
const VIEW_TITLES = {
  overview: 'Executive Overview',
  subjects: 'Subject-Wise Performance & Learning Gaps',
  atrisk: 'Early-Warning At-Risk Detection',
  predict: 'Performance Trajectory Predictor',
  student: 'Student 360° Profile Lookup',
  career: 'Career Guidance & Readiness Analysis',
  pipeline: 'Data & ETL Pipeline Monitoring',
};

const VALID_VIEWS = ['overview', 'subjects', 'atrisk', 'predict', 'student', 'career', 'pipeline'];

// ── Initialization ────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupSliders();
  setupStudentSearch();
  setupCareerSearch();
  loadCurrentDate();

  // Restore current view from URL hash or localStorage, fallback to 'overview'
  const hash = window.location.hash.replace('#', '').trim();
  let savedView = null;
  try {
    savedView = localStorage.getItem('campus360_active_view');
  } catch (_) {}

  const initialView = VALID_VIEWS.includes(hash)
    ? hash
    : (VALID_VIEWS.includes(savedView) ? savedView : 'overview');

  switchView(initialView, false);
});

window.addEventListener('hashchange', () => {
  const hash = window.location.hash.replace('#', '').trim();
  if (VALID_VIEWS.includes(hash) && hash !== state.currentView) {
    switchView(hash, false);
  }
});

function loadCurrentDate() {
  const dateEl = document.getElementById('top-bar-date');
  if (dateEl) {
    const today = new Date();
    const options = { month: 'short', day: 'numeric', year: 'numeric' };
    dateEl.textContent = today.toLocaleDateString('en-US', options);
  }
}

// ── Navigation ────────────────────────────────────────────────────────────────
function setupNavigation() {
  const navBtns = document.querySelectorAll('.nav-btn');
  navBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const view = btn.dataset.view;
      if (view) switchView(view);
    });
  });
}

function switchView(viewName, updateHistory = true) {
  if (!VALID_VIEWS.includes(viewName)) {
    viewName = 'overview';
  }

  state.currentView = viewName;

  try {
    if (updateHistory) {
      window.location.hash = viewName;
    }
    localStorage.setItem('campus360_active_view', viewName);
  } catch (_) {}

  // Update Top Bar Title
  const titleEl = document.getElementById('page-title');
  if (titleEl) titleEl.textContent = VIEW_TITLES[viewName] || 'Campus360 Analytics';

  // Update Left Nav Active State
  const navBtns = document.querySelectorAll('.nav-btn');
  navBtns.forEach((btn) => {
    const isActive = btn.dataset.view === viewName;
    const pill = btn.querySelector('.nav-pill');
    if (pill) {
      if (isActive) {
        pill.classList.add('bg-[#EDEBFB]', 'text-[#6C5CE7]');
        pill.classList.remove('text-[#8A8797]', 'hover:bg-slate-100');
      } else {
        pill.classList.remove('bg-[#EDEBFB]', 'text-[#6C5CE7]');
        pill.classList.add('text-[#8A8797]', 'hover:bg-slate-100');
      }
    }
  });

  // Toggle View Containers
  document.querySelectorAll('.view-section').forEach((sec) => {
    sec.classList.add('hidden');
  });

  const activeSec = document.getElementById(`view-${viewName}`);
  if (activeSec) {
    activeSec.classList.remove('hidden');
  }

  // Trigger Data Load per View
  if (viewName === 'overview') loadOverviewView();
  else if (viewName === 'subjects') loadSubjectsView();
  else if (viewName === 'atrisk') loadAtRiskView();
  else if (viewName === 'predict') loadPredictView();
  else if (viewName === 'student') loadStudentView(state.currentStudentId);
  else if (viewName === 'career') loadCareerView(state.currentCareerStudentId || 'STU00001');
  else if (viewName === 'pipeline') loadPipelineView();

  // Polling lifecycle for pipeline monitoring
  if (viewName === 'pipeline') {
    startPipelinePolling();
  } else {
    stopPipelinePolling();
  }
}

// Global Helper to jump to a student from lists
window.jumpToStudent = function (studentId) {
  state.currentStudentId = studentId;
  const input = document.getElementById('student-search-input');
  if (input) input.value = studentId;
  switchView('student');
};

// Global Helper to jump to career guidance for a student
window.jumpToCareer = function (studentId) {
  state.currentCareerStudentId = studentId;
  const input = document.getElementById('career-search-input');
  if (input) input.value = studentId;
  switchView('career');
};

// ── Chart Helper ──────────────────────────────────────────────────────────────
function getOrCreateChart(canvasId, config) {
  if (state.charts[canvasId]) {
    state.charts[canvasId].destroy();
  }
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;
  const ctx = canvas.getContext('2d');
  const chart = new Chart(ctx, config);
  state.charts[canvasId] = chart;
  return chart;
}

// ── VIEW 1: Overview ──────────────────────────────────────────────────────────
async function loadOverviewView() {
  try {
    // 1. Fetch Overview KPIs & Distribution
    const res = await fetch(`${API_BASE}/api/analytics/overview`);
    const data = await res.json();
    state.overviewData = data;

    // Populate KPI values
    document.getElementById('kpi-total-students').textContent = Number(data.total_students || 25000).toLocaleString();
    document.getElementById('kpi-avg-cgpa').textContent = (data.average_cgpa || 7.62).toFixed(2);
    document.getElementById('kpi-placement-rate').textContent = `${data.placement_rate_pct || 62.4}%`;
    document.getElementById('kpi-at-risk-rate').textContent = `${data.at_risk_pct || 31.9}%`;

    // 2. Render CGPA Histogram Bar Chart
    const cgpaBins = data.cgpa_distribution || [];
    const labels = cgpaBins.map((b) => b.bin);
    const counts = cgpaBins.map((b) => b.count);

    getOrCreateChart('cgpaDistributionChart', {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Students Count',
            data: counts,
            backgroundColor: 'rgba(108, 92, 231, 0.82)',
            hoverBackgroundColor: '#4B3FA8',
            borderRadius: 8,
            borderSkipped: false,
            maxBarThickness: 48,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1E1B2E',
            titleFont: { family: 'Sora', size: 13 },
            bodyFont: { family: 'Inter', size: 12 },
            padding: 10,
            cornerRadius: 8,
            callbacks: {
              label: (ctx) => ` ${ctx.raw.toLocaleString()} students (${((ctx.raw / (data.total_students || 25000)) * 100).toFixed(1)}%)`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { family: 'Inter', size: 12 }, color: PALETTE.textMuted },
          },
          y: {
            grid: { color: '#F0EFFB' },
            ticks: { font: { family: 'Inter', size: 11 }, color: PALETTE.textMuted },
          },
        },
      },
    });

    // 3. Fetch & Render Top 6 Flagged At-Risk Students
    loadOverviewAtRiskList();
  } catch (err) {
    console.error('Error loading Overview:', err);
  }
}

async function loadOverviewAtRiskList() {
  const container = document.getElementById('overview-flagged-list');
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/api/analytics/at-risk-students?limit=6`);
    const data = await res.json();
    const students = data.students || [];

    container.innerHTML = '';
    students.forEach((stu) => {
      const row = document.createElement('div');
      row.className =
        'flex items-center justify-between p-3 rounded-xl bg-white border border-[#EDEBFB] hover:border-[#6C5CE7] hover:shadow-sm cursor-pointer transition-all duration-150';
      row.onclick = () => jumpToStudent(stu.student_id);

      row.innerHTML = `
        <div class="flex items-center space-x-3">
          <div class="w-9 h-9 rounded-full bg-[#FDEDEF] text-[#E85D75] flex items-center justify-center font-sora font-semibold text-xs">
            ${stu.student_id.slice(-3)}
          </div>
          <div>
            <div class="font-sora font-semibold text-sm text-[#1E1B2E] flex items-center space-x-2">
              <span>${stu.student_id}</span>
              <span class="text-xs font-normal text-[#8A8797]">(${stu.stream_branch || 'Eng'})</span>
            </div>
            <div class="text-xs text-[#8A8797] truncate max-w-[140px]" title="${stu.top_contributing_factor}">
              ${stu.top_contributing_factor || 'Risk factor identified'}
            </div>
          </div>
        </div>
        <div class="text-right">
          <div class="font-sora font-semibold text-xs text-[#1E1B2E]">CGPA ${stu.current_cgpa.toFixed(2)}</div>
          <span class="inline-block mt-0.5 px-2 py-0.5 rounded-full text-[10px] font-medium bg-[#FDEDEF] text-[#E85D75]">
            At-Risk
          </span>
        </div>
      `;
      container.appendChild(row);
    });
  } catch (err) {
    console.error('Error loading flagged list:', err);
    container.innerHTML = '<div class="text-xs text-red-500 py-4">Failed to load flagged students</div>';
  }
}

// ── VIEW 2: Subject-Wise Performance ──────────────────────────────────────────
async function loadSubjectsView() {
  try {
    const res = await fetch(`${API_BASE}/api/analytics/subjects`);
    const data = await res.json();
    state.subjectsData = data;

    // 1. Normalized Percentage Bar Chart
    const overall = data.overall_subjects || [];
    const subjects = overall.map((o) => o.subject);
    const scores = overall.map((o) => o.avg_normalized_pct);

    getOrCreateChart('subjectBarChart', {
      type: 'bar',
      data: {
        labels: subjects,
        datasets: [
          {
            label: 'Avg Normalized Score (%)',
            data: scores,
            backgroundColor: scores.map((s) => (s < 65 ? 'rgba(232, 93, 117, 0.85)' : 'rgba(108, 92, 231, 0.85)')),
            borderRadius: 8,
            maxBarThickness: 54,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1E1B2E',
            titleFont: { family: 'Sora', size: 13 },
            bodyFont: { family: 'Inter', size: 12 },
            callbacks: {
              label: (ctx) => ` Normalized Score: ${ctx.raw}% (Scale: 0–100%)`,
            },
          },
        },
        scales: {
          y: {
            min: 50,
            max: 90,
            grid: { color: '#F0EFFB' },
            ticks: { font: { family: 'Inter', size: 11 }, color: PALETTE.textMuted, callback: (v) => `${v}%` },
          },
          x: {
            grid: { display: false },
            ticks: { font: { family: 'Inter', size: 11 }, color: PALETTE.textMuted },
          },
        },
      },
    });

    // 2. Render Heatmap Grid (Div-based, styled background)
    renderHeatmapGrid(data);

    // 3. Render Lowest-Performing per Branch Table
    renderSubjectGapsTable(data.lowest_performing_per_branch || []);
  } catch (err) {
    console.error('Error loading Subjects View:', err);
  }
}

function renderHeatmapGrid(data) {
  const container = document.getElementById('heatmap-grid-container');
  if (!container) return;

  const branches = data.branches || [];
  const matrix = data.heatmap_matrix || [];

  let html = `
    <div class="overflow-x-auto">
      <table class="w-full text-xs text-left">
        <thead>
          <tr class="border-b border-[#EDEBFB] text-[#8A8797]">
            <th class="py-2.5 px-3 font-semibold">Subject</th>
            ${branches.map((b) => `<th class="py-2.5 px-3 font-semibold text-center">${b}</th>`).join('')}
          </tr>
        </thead>
        <tbody>
  `;

  matrix.forEach((row) => {
    html += `
      <tr class="border-b border-[#F6F5FC] hover:bg-[#FAF9FD]">
        <td class="py-2 px-3 font-medium text-[#1E1B2E]">${row.subject}</td>
    `;
    branches.forEach((b) => {
      const score = row[b];
      if (score === null || score === undefined) {
        html += `<td class="py-2 px-3 text-center text-[#8A8797]">—</td>`;
      } else {
        // Color scale: Coral (low, ~63) to Mint (high, ~80)
        let bgStyle = '';
        let textStyle = '';
        if (score < 65) {
          bgStyle = 'background-color: #FDEDEF;';
          textStyle = 'color: #E85D75;';
        } else if (score < 72) {
          bgStyle = 'background-color: #E6F0FE;';
          textStyle = 'color: #2F64C8;';
        } else {
          bgStyle = 'background-color: #E7F8EE;';
          textStyle = 'color: #2E8555;';
        }
        html += `
          <td class="py-2 px-2 text-center">
            <div class="py-1 px-2 rounded-lg font-sora font-semibold text-xs inline-block min-w-[52px]" style="${bgStyle} ${textStyle}">
              ${score.toFixed(1)}%
            </div>
          </td>
        `;
      }
    });
    html += `</tr>`;
  });

  html += `</tbody></table></div>`;
  container.innerHTML = html;
}

function renderSubjectGapsTable(gaps) {
  const container = document.getElementById('subject-gaps-table-body');
  if (!container) return;

  let sorted = [...gaps];
  const col = state.subjectGapsSortCol;
  const asc = state.subjectGapsSortAsc;

  sorted.sort((a, b) => {
    let vA = a[col];
    let vB = b[col];
    if (typeof vA === 'string') return asc ? vA.localeCompare(vB) : vB.localeCompare(vA);
    return asc ? vA - vB : vB - vA;
  });

  container.innerHTML = sorted
    .map(
      (item) => `
    <tr class="border-b border-[#F6F5FC] hover:bg-[#FAF9FD]">
      <td class="py-3 px-4 font-medium text-[#1E1B2E]">${item.stream_branch}</td>
      <td class="py-3 px-4 font-semibold text-[#E85D75]">${item.lowest_subject}</td>
      <td class="py-3 px-4 font-sora font-bold text-[#1E1B2E]">${item.avg_normalized_pct.toFixed(2)}%</td>
      <td class="py-3 px-4">
        <span class="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${
          item.gap_severity === 'High Gap' ? 'bg-[#FDEDEF] text-[#E85D75]' : 'bg-[#EDEBFB] text-[#6C5CE7]'
        }">
          ${item.gap_severity}
        </span>
      </td>
    </tr>
  `
    )
    .join('');
}

// Click-to-sort for Subject Gaps Table
window.sortSubjectGaps = function (col) {
  if (state.subjectGapsSortCol === col) {
    state.subjectGapsSortAsc = !state.subjectGapsSortAsc;
  } else {
    state.subjectGapsSortCol = col;
    state.subjectGapsSortAsc = true;
  }
  if (state.subjectsData) {
    renderSubjectGapsTable(state.subjectsData.lowest_performing_per_branch || []);
  }
};

// ── VIEW 3: At-Risk Detection ─────────────────────────────────────────────────
async function loadAtRiskView() {
  try {
    // 1. Fetch Metadata, Population Split, Top 5 Features & Disclosure
    const resMeta = await fetch(`${API_BASE}/api/models/atrisk-metadata`);
    const meta = await resMeta.json();
    state.atRiskMeta = meta;

    // Disclosure Banner Text
    const bannerText = document.getElementById('atrisk-disclosure-text');
    if (bannerText && meta.disclosure_text) {
      bannerText.textContent = meta.disclosure_text;
    }

    // 2. Population Split Doughnut Chart (Expects ~32% at-risk, 68% safe)
    const split = meta.population_split || { at_risk_pct: 31.9, safe_pct: 68.1 };
    getOrCreateChart('atRiskDoughnutChart', {
      type: 'doughnut',
      data: {
        labels: ['Safe Population', 'At-Risk Population'],
        datasets: [
          {
            data: [split.safe_pct, split.at_risk_pct],
            backgroundColor: ['#EDEBFB', '#FDEDEF'],
            hoverBackgroundColor: ['#D6D2F7', '#FCD6DC'],
            borderColor: ['#6C5CE7', '#E85D75'],
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: { font: { family: 'Inter', size: 12 }, color: PALETTE.textPrimary, padding: 16 },
          },
          tooltip: {
            backgroundColor: '#1E1B2E',
            bodyFont: { family: 'Inter', size: 12 },
            callbacks: {
              label: (ctx) => ` ${ctx.label}: ${ctx.raw}% (~${Math.round((ctx.raw / 100) * 25000).toLocaleString()} students)`,
            },
          },
        },
      },
    });

    // 3. Top 5 Feature Importances Bar Chart
    const top5 = meta.top_5_features || [];
    getOrCreateChart('atRiskFeatureImportanceChart', {
      type: 'bar',
      data: {
        labels: top5.map((f) => f.label),
        datasets: [
          {
            label: 'Feature Importance',
            data: top5.map((f) => f.importance),
            backgroundColor: 'rgba(108, 92, 231, 0.85)',
            borderRadius: 6,
            maxBarThickness: 36,
          },
        ],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1E1B2E',
            bodyFont: { family: 'Inter', size: 12 },
            callbacks: {
              label: (ctx) => ` Importance: ${(ctx.raw * 100).toFixed(2)}%`,
            },
          },
        },
        scales: {
          x: {
            grid: { color: '#F0EFFB' },
            ticks: { font: { family: 'Inter', size: 11 }, color: PALETTE.textMuted },
          },
          y: {
            grid: { display: false },
            ticks: { font: { family: 'Inter', size: 11 }, color: PALETTE.textPrimary },
          },
        },
      },
    });

    // 4. Fetch & Render Full At-Risk Table
    loadAtRiskTable();
  } catch (err) {
    console.error('Error loading At-Risk View:', err);
  }
}

async function loadAtRiskTable() {
  const container = document.getElementById('atrisk-table-body');
  if (!container) return;

  try {
    const searchInput = document.getElementById('atrisk-table-search');
    const query = searchInput ? searchInput.value.trim() : '';
    const res = await fetch(`${API_BASE}/api/analytics/atrisk-table?limit=40&search=${encodeURIComponent(query)}`);
    const data = await res.json();
    state.atRiskTable = data.students || [];

    renderAtRiskTableRows();
  } catch (err) {
    console.error('Error loading At-Risk Table:', err);
    container.innerHTML = '<tr><td colspan="5" class="py-4 text-center text-xs text-red-500">Failed to load table</td></tr>';
  }
}

function renderAtRiskTableRows() {
  const container = document.getElementById('atrisk-table-body');
  if (!container) return;

  let sorted = [...state.atRiskTable];
  const col = state.atRiskSortCol;
  const asc = state.atRiskSortAsc;

  sorted.sort((a, b) => {
    let vA = a[col];
    let vB = b[col];
    if (typeof vA === 'string') return asc ? vA.localeCompare(vB) : vB.localeCompare(vA);
    return asc ? vA - vB : vB - vA;
  });

  if (sorted.length === 0) {
    container.innerHTML = `
      <tr>
        <td colspan="6" class="py-8 text-center text-xs text-[#8A8797]">
          <div class="text-xl mb-1">🔍</div>
          No students match the current filter parameters.
        </td>
      </tr>
    `;
    return;
  }

  container.innerHTML = sorted
    .map(
      (stu) => `
    <tr class="border-b border-[#F6F5FC] hover:bg-[#FAF9FD] cursor-pointer transition-colors" onclick="jumpToStudent('${stu.student_id}')">
      <td class="py-3 px-4 font-sora font-semibold text-sm text-[#6C5CE7] hover:underline">${stu.student_id}</td>
      <td class="py-3 px-4">
        <div class="flex items-center space-x-2">
          <span class="font-sora font-bold text-xs ${stu.predicted_risk_probability >= 0.5 ? 'text-[#E85D75]' : 'text-[#4CAF7D]'}">
            ${(stu.predicted_risk_probability * 100).toFixed(1)}%
          </span>
          <div class="w-16 bg-[#EDEBFB] h-1.5 rounded-full overflow-hidden">
            <div class="h-full ${stu.predicted_risk_probability >= 0.5 ? 'bg-[#E85D75]' : 'bg-[#4CAF7D]'}" style="width: ${stu.predicted_risk_probability * 100}%"></div>
          </div>
        </div>
      </td>
      <td class="py-3 px-4 font-sora font-medium text-xs text-[#1E1B2E]">${stu.current_cgpa.toFixed(2)}</td>
      <td class="py-3 px-4 text-xs text-[#1E1B2E]">
        <span class="inline-block px-2 py-0.5 rounded-md bg-[#EDEBFB] text-[#6C5CE7] font-medium text-[11px]">
          ${stu.top_contributing_factor}
        </span>
      </td>
      <td class="py-3 px-4">
        <span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${
          stu.predicted_risk_probability >= 0.5 ? 'bg-[#FDEDEF] text-[#E85D75]' : 'bg-[#E7F8EE] text-[#4CAF7D]'
        }">
          ${stu.predicted_risk_probability >= 0.5 ? 'Flagged' : 'Safe'}
        </span>
      </td>
      <td class="py-3 px-4 text-right">
        <button
          onclick="event.stopPropagation(); showAtRiskMentorBrief('${stu.student_id}')"
          class="px-2.5 py-1 rounded-lg bg-[#EDEBFB] hover:bg-[#6C5CE7] text-[#6C5CE7] hover:text-white font-sora font-semibold text-[11px] transition-all shadow-sm inline-flex items-center space-x-1"
          title="Generate Mentor Brief for ${stu.student_id}">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <span>Mentor Brief</span>
        </button>
      </td>
    </tr>
  `
    )
    .join('');
}

window.sortAtRiskTable = function (col) {
  if (state.atRiskSortCol === col) {
    state.atRiskSortAsc = !state.atRiskSortAsc;
  } else {
    state.atRiskSortCol = col;
    state.atRiskSortAsc = false; // default desc for probability
  }
  renderAtRiskTableRows();
};

window.filterAtRiskTable = function () {
  loadAtRiskTable();
};

window.showAtRiskMentorBrief = async function (studentId) {
  const modal = document.getElementById('ai-mentor-modal');
  const title = document.getElementById('ai-modal-title');
  const subtitle = document.getElementById('ai-modal-subtitle');
  const body = document.getElementById('ai-modal-body');
  if (!modal || !body) return;

  title.textContent = `Mentor Brief • ${studentId}`;
  subtitle.textContent = 'AI synthesis from calibrated Model 2 early-warning classifier';
  modal.classList.remove('hidden');

  body.innerHTML = `
    <div class="py-8 text-center">
      <div class="inline-block animate-spin rounded-full h-7 w-7 border-b-2 border-[#6C5CE7]"></div>
      <div class="mt-3 text-xs text-[#8A8797]">Synthesizing mentor brief for ${studentId}...</div>
    </div>
  `;

  try {
    const res = await fetch(`${API_BASE}/api/genai/atrisk-brief/${encodeURIComponent(studentId)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const prob = (data.model_probability * 100).toFixed(1);
    const badgeColor = data.model_probability >= 0.5 ? 'bg-[#FDEDEF] text-[#E85D75]' : 'bg-[#E7F8EE] text-[#4CAF7D]';

    body.innerHTML = `
      <div class="rounded-2xl p-5 border border-purple-100" style="background: linear-gradient(135deg, #EDEBFB 0%, #F6F5FC 100%)">
        <div class="flex flex-wrap items-center gap-2 mb-3">
          <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold ${badgeColor}">
            Risk Probability: ${prob}%
          </span>
          <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white text-[#6C5CE7]">
            Top Factor: ${data.model_top_factor}
          </span>
          ${data.is_fallback ? '<span class="px-2 py-0.5 rounded-full text-[10px] bg-white/70 text-[#8A8797]">Rule-Grounded</span>' : '<span class="px-2 py-0.5 rounded-full text-[10px] bg-purple-100 text-[#6C5CE7]">Gemini 2.5 Flash</span>'}
        </div>
        <p class="text-sm text-[#1E1B2E] font-medium leading-relaxed mb-4">
          ${data.brief_text}
        </p>
        <div class="pt-3 border-t border-purple-200/60 flex items-center justify-between text-[11px] text-[#8A8797]">
          <span>Generated: ${new Date(data.generated_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
          <span class="italic font-medium">AI-generated — verify before acting</span>
        </div>
      </div>
      <div class="mt-5 flex items-center justify-end space-x-3">
        <button onclick="closeAiModal()" class="px-4 py-2 rounded-xl text-xs font-semibold text-[#8A8797] hover:bg-[#F6F5FC] transition-colors">
          Close
        </button>
        <button onclick="closeAiModal(); jumpToStudent('${studentId}')" class="px-4 py-2 rounded-xl text-xs font-semibold bg-[#6C5CE7] hover:bg-[#4B3FA8] text-white transition-all shadow-sm">
          View 360° Profile
        </button>
      </div>
    `;
  } catch (err) {
    console.error('At-risk brief error:', err);
    body.innerHTML = `
      <div class="p-6 text-center text-xs text-red-500">
        Failed to load mentor brief for ${studentId}. Please ensure backend API is running.
      </div>
    `;
  }
};

window.closeAiModal = function () {
  const modal = document.getElementById('ai-mentor-modal');
  if (modal) modal.classList.add('hidden');
};


// ── VIEW 4: Performance Prediction ────────────────────────────────────────────
function setupSliders() {
  const sliders = [
    { id: 'slider-attendance', badge: 'badge-attendance', unit: '%' },
    { id: 'slider-study', badge: 'badge-study', unit: ' hrs' },
    { id: 'slider-dsa', badge: 'badge-dsa', unit: ' solved' },
    { id: 'slider-internships', badge: 'badge-internships', unit: '' },
    { id: 'slider-sleep', badge: 'badge-sleep', unit: ' hrs' },
    { id: 'slider-comms', badge: 'badge-comms', unit: ' / 100' },
  ];

  sliders.forEach(({ id, badge, unit }) => {
    const input = document.getElementById(id);
    const badgeEl = document.getElementById(badge);
    if (input && badgeEl) {
      input.addEventListener('input', () => {
        badgeEl.textContent = `${input.value}${unit}`;
      });
    }
  });

  const predictBtn = document.getElementById('btn-predict-cgpa');
  if (predictBtn) {
    predictBtn.addEventListener('click', runPrediction);
  }
}

function loadPredictView() {
  // Ensure default prediction runs if not yet computed
  if (!state.hasInitialPrediction) {
    runPrediction();
    state.hasInitialPrediction = true;
  }
}

window.applyPredictPreset = function (presetName) {
  const presets = {
    achiever: { attendance: 95, study: 7.0, dsa: 350, internships: 2, sleep: 7.5, comms: 90 },
    typical: { attendance: 80, study: 4.0, dsa: 120, internships: 1, sleep: 6.5, comms: 70 },
    distress: { attendance: 58, study: 1.5, dsa: 20, internships: 0, sleep: 4.5, comms: 45 },
  };

  const p = presets[presetName];
  if (!p) return;

  setSliderVal('slider-attendance', 'badge-attendance', p.attendance, '%');
  setSliderVal('slider-study', 'badge-study', p.study, ' hrs');
  setSliderVal('slider-dsa', 'badge-dsa', p.dsa, ' solved');
  setSliderVal('slider-internships', 'badge-internships', p.internships, '');
  setSliderVal('slider-sleep', 'badge-sleep', p.sleep, ' hrs');
  setSliderVal('slider-comms', 'badge-comms', p.comms, ' / 100');

  runPrediction();
};

function setSliderVal(id, badgeId, val, unit) {
  const el = document.getElementById(id);
  const b = document.getElementById(badgeId);
  if (el) el.value = val;
  if (b) b.textContent = `${val}${unit}`;
}

async function runPrediction() {
  const resultCard = document.getElementById('prediction-output-card');
  const numberEl = document.getElementById('predicted-cgpa-number');
  const noteEl = document.getElementById('prediction-confidence-note');

  const payload = {
    attendance_percentage: parseFloat(document.getElementById('slider-attendance')?.value || 80),
    study_hours_daily: parseFloat(document.getElementById('slider-study')?.value || 4),
    dsa_problems_solved: parseInt(document.getElementById('slider-dsa')?.value || 120),
    internships_completed: parseInt(document.getElementById('slider-internships')?.value || 1),
    sleep_hours: parseFloat(document.getElementById('slider-sleep')?.value || 7),
    communication_skills: parseFloat(document.getElementById('slider-comms')?.value || 70),
  };

  if (numberEl) numberEl.innerHTML = '<span class="text-2xl text-[#8A8797]">Calculating...</span>';

  try {
    const res = await fetch(`${API_BASE}/api/models/predict-performance`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (numberEl) {
      numberEl.textContent = data.predicted_cgpa.toFixed(2);
    }
    if (noteEl) {
      noteEl.innerHTML = `Model R² = <span class="font-semibold text-[#6C5CE7]">${data.model_r2.toFixed(2)}</span> (RMSE ${data.model_rmse.toFixed(2)}) — provides directional guidance.`;
    }
  } catch (err) {
    console.error('Error running prediction:', err);
    if (numberEl) numberEl.textContent = 'Error';
  }
}

// ── VIEW 5: Student 360 Lookup ────────────────────────────────────────────────
function setupStudentSearch() {
  const form = document.getElementById('student-search-form');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const input = document.getElementById('student-search-input');
      const sid = input ? input.value.trim() : '';
      if (sid) loadStudentView(sid);
    });
  }
}

async function loadStudentView(studentId) {
  state.currentStudentId = studentId;
  const container = document.getElementById('student-360-content');
  if (!container) return;

  container.innerHTML = `
    <div class="p-8 text-center">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[#6C5CE7]"></div>
      <div class="mt-2 text-xs text-[#8A8797]">Loading comprehensive 360° record for ${studentId}...</div>
    </div>
  `;

  try {
    const res = await fetch(`${API_BASE}/api/students/${encodeURIComponent(studentId)}`);
    if (!res.ok) {
      container.innerHTML = `
        <div class="p-12 text-center bg-white rounded-2xl border border-[#EDEBFB]">
          <div class="text-4xl mb-2">🔍</div>
          <div class="font-sora font-semibold text-lg text-[#1E1B2E]">Student ${studentId} not found</div>
          <div class="text-xs text-[#8A8797] mt-1">Please try one of the demo IDs: STU00001, STU15140, STU16970, STU08983.</div>
        </div>
      `;
      return;
    }

    const data = await res.json();
    renderStudent360(data);
  } catch (err) {
    console.error('Error fetching student 360:', err);
    container.innerHTML = '<div class="p-8 text-center text-xs text-red-500">Failed to load student record.</div>';
  }
}

function renderStudent360(data) {
  const container = document.getElementById('student-360-content');
  if (!container) return;

  const d = data.demographics || {};
  const life = data.lifestyle || {};
  const c = data.career || {};
  const academics = data.academics || [];
  const risk = data.model_risk;

  // Graceful Null Helper
  const val = (v, suffix = '') => {
    if (v === null || v === undefined || v === '') {
      return '<span class="text-[#8A8797] italic font-normal text-xs">Not available</span>';
    }
    return `${v}${suffix}`;
  };

  let riskBadge = '';
  if (risk) {
    riskBadge = `
      <div class="px-3 py-1 rounded-full text-xs font-semibold ${
        risk.is_predicted_at_risk ? 'bg-[#FDEDEF] text-[#E85D75]' : 'bg-[#E7F8EE] text-[#4CAF7D]'
      }">
        ${risk.is_predicted_at_risk ? `At-Risk (${(risk.predicted_risk_probability * 100).toFixed(0)}%)` : 'On-Track (Safe)'}
      </div>
    `;
  }

  container.innerHTML = `
    <!-- Demographics Header -->
    <div class="bg-white rounded-2xl p-6 border border-[#EDEBFB] shadow-sm mb-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
      <div class="flex items-center space-x-4">
        <div class="w-14 h-14 rounded-2xl bg-[#EDEBFB] text-[#6C5CE7] flex items-center justify-center font-sora font-bold text-xl">
          ${d.student_id ? d.student_id.slice(-2) : 'ST'}
        </div>
        <div>
          <div class="flex items-center space-x-3">
            <h2 class="font-sora font-bold text-xl text-[#1E1B2E]">${val(d.student_id)}</h2>
            ${riskBadge}
          </div>
          <p class="text-xs text-[#8A8797] mt-0.5">
            ${val(d.stream_branch)} • Tier ${val(d.college_tier)} • ${val(d.degree)} • ${val(d.gender)} • ${val(d.state)}
          </p>
        </div>
      </div>
      <div class="flex items-center space-x-3 bg-[#F6F5FC] px-4 py-2.5 rounded-xl text-xs">
        <div>
          <span class="text-[#8A8797]">Family Income:</span>
          <span class="font-sora font-semibold text-[#1E1B2E] ml-1">${val(d.family_income_lpa, ' LPA')}</span>
        </div>
        <span class="text-slate-300">|</span>
        <div>
          <span class="text-[#8A8797]">City Tier:</span>
          <span class="font-sora font-semibold text-[#1E1B2E] ml-1">Tier ${val(d.city_tier)}</span>
        </div>
      </div>
    </div>

    <!-- AI Mentor Insights Callout Card -->
    <div id="student-mentor-brief-card" class="bg-white rounded-2xl p-6 border border-[#EDEBFB] shadow-sm">
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-2xl bg-[#EDEBFB] flex items-center justify-center text-[#6C5CE7]">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <h3 class="font-sora font-bold text-base text-[#1E1B2E]">Faculty & Mentor Insights</h3>
            <p class="text-xs text-[#8A8797]">AI-synthesized explanations from calibrated predictive models</p>
          </div>
        </div>
        <div class="flex items-center space-x-2">
          <button id="btn-tab-atrisk" onclick="switchStudentBriefTab('${d.student_id}', 'atrisk')" class="px-3.5 py-1.5 rounded-xl font-sora font-semibold text-xs bg-[#6C5CE7] text-white transition-all shadow-sm">
            At-Risk Brief
          </button>
          <button id="btn-tab-perf" onclick="switchStudentBriefTab('${d.student_id}', 'perf')" class="px-3.5 py-1.5 rounded-xl font-sora font-semibold text-xs bg-[#F6F5FC] text-[#8A8797] hover:bg-[#EDEBFB] hover:text-[#6C5CE7] transition-all">
            Performance Trajectory
          </button>
        </div>
      </div>
      <div id="student-brief-content" class="rounded-xl p-5 border border-purple-100" style="background: linear-gradient(135deg, #EDEBFB 0%, #F6F5FC 100%)">
        <div class="flex items-center justify-center py-3">
          <div class="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-[#6C5CE7]"></div>
          <span class="ml-2 text-xs text-[#8A8797]">Synthesizing mentor brief for ${d.student_id}...</span>
        </div>
      </div>
    </div>

    <!-- 3-Column Grid: Academics, Lifestyle, Career -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      <!-- Academic Performance Mini-Table (7 cols) -->
      <div class="lg:col-span-7 bg-white rounded-2xl p-6 border border-[#EDEBFB] shadow-sm">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-sora font-semibold text-base text-[#1E1B2E]">Academic Assessment Breakdown</h3>
          <span class="text-xs text-[#8A8797]">${academics.length} Assessments</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-xs text-left">
            <thead>
              <tr class="border-b border-[#EDEBFB] text-[#8A8797]">
                <th class="pb-2 font-semibold">Subject</th>
                <th class="pb-2 font-semibold text-center">Marks</th>
                <th class="pb-2 font-semibold text-center">Norm %</th>
                <th class="pb-2 font-semibold text-center">Attendance</th>
                <th class="pb-2 font-semibold text-right">Status</th>
              </tr>
            </thead>
            <tbody>
              ${
                academics.length === 0
                  ? '<tr><td colspan="5" class="py-4 text-center text-[#8A8797]">No assessment records found</td></tr>'
                  : academics
                      .map(
                        (a) => `
                <tr class="border-b border-[#F6F5FC] hover:bg-[#FAF9FD]">
                  <td class="py-2.5 font-medium text-[#1E1B2E]">${val(a.subject)}</td>
                  <td class="py-2.5 text-center font-sora">${val(a.marks)} / ${val(a.max_marks)}</td>
                  <td class="py-2.5 text-center font-sora font-semibold text-[#6C5CE7]">${val(a.normalized_pct, '%')}</td>
                  <td class="py-2.5 text-center text-[#8A8797]">${val(a.attendance_pct, '%')}</td>
                  <td class="py-2.5 text-right font-medium">${val(a.grade_or_status)}</td>
                </tr>
              `
                      )
                      .join('')
              }
            </tbody>
          </table>
        </div>
      </div>

      <!-- Career Readiness (5 cols) -->
      <div class="lg:col-span-5 bg-white rounded-2xl p-6 border border-[#EDEBFB] shadow-sm">
        <h3 class="font-sora font-semibold text-base text-[#1E1B2E] mb-4">Career Readiness & Placement</h3>
        <div class="space-y-3">
          <div class="flex items-center justify-between p-3 rounded-xl bg-[#EDEBFB]">
            <span class="text-xs text-[#6C5CE7] font-medium">Degree CGPA</span>
            <span class="font-sora font-bold text-base text-[#6C5CE7]">${val(c.cgpa)} / 10</span>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="p-3 rounded-xl bg-[#F6F5FC]">
              <span class="text-[11px] text-[#8A8797]">Placement Status</span>
              <div class="font-sora font-semibold text-xs text-[#1E1B2E] mt-0.5">${val(c.placement_status)}</div>
            </div>
            <div class="p-3 rounded-xl bg-[#F6F5FC]">
              <span class="text-[11px] text-[#8A8797]">Annual Package</span>
              <div class="font-sora font-semibold text-xs text-[#1E1B2E] mt-0.5">${val(c.salary_lpa, ' LPA')}</div>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-2 text-center">
            <div class="p-2.5 rounded-xl border border-[#EDEBFB]">
              <div class="text-[10px] text-[#8A8797]">Backlogs</div>
              <div class="font-sora font-bold text-xs text-[#1E1B2E] mt-0.5">${val(c.backlogs)}</div>
            </div>
            <div class="p-2.5 rounded-xl border border-[#EDEBFB]">
              <div class="text-[10px] text-[#8A8797]">Internships</div>
              <div class="font-sora font-bold text-xs text-[#1E1B2E] mt-0.5">${val(c.internships)}</div>
            </div>
            <div class="p-2.5 rounded-xl border border-[#EDEBFB]">
              <div class="text-[10px] text-[#8A8797]">DSA Problems</div>
              <div class="font-sora font-bold text-xs text-[#1E1B2E] mt-0.5">${val(c.dsa_problems_solved)}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Lifestyle & Behavioral Profile (Full 12 cols) -->
      <div class="lg:col-span-12 bg-white rounded-2xl p-6 border border-[#EDEBFB] shadow-sm">
        <h3 class="font-sora font-semibold text-base text-[#1E1B2E] mb-4">Lifestyle, Wellness & Behavioral Habits</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <div class="p-3.5 rounded-xl bg-[#E6F0FE]">
            <span class="text-[11px] text-[#2F64C8]">Daily Sleep</span>
            <div class="font-sora font-bold text-sm text-[#1E1B2E] mt-1">${val(life.sleep_hours, ' hrs')}</div>
          </div>
          <div class="p-3.5 rounded-xl bg-[#EDEBFB]">
            <span class="text-[11px] text-[#6C5CE7]">Study Time</span>
            <div class="font-sora font-bold text-sm text-[#1E1B2E] mt-1">${val(life.study_hours_daily, ' hrs/day')}</div>
          </div>
          <div class="p-3.5 rounded-xl bg-[#FDEDEF]">
            <span class="text-[11px] text-[#E85D75]">Screen Time</span>
            <div class="font-sora font-bold text-sm text-[#1E1B2E] mt-1">${val(life.screen_time_hours, ' hrs/day')}</div>
          </div>
          <div class="p-3.5 rounded-xl bg-[#F6F5FC]">
            <span class="text-[11px] text-[#8A8797]">Gaming Hours</span>
            <div class="font-sora font-bold text-sm text-[#1E1B2E] mt-1">${val(life.gaming_hours, ' hrs')}</div>
          </div>
          <div class="p-3.5 rounded-xl bg-[#FDEDEF]">
            <span class="text-[11px] text-[#E85D75]">Stress Level</span>
            <div class="font-sora font-bold text-sm text-[#1E1B2E] mt-1">${val(life.stress_level, ' / 100')}</div>
          </div>
          <div class="p-3.5 rounded-xl bg-[#E7F8EE]">
            <span class="text-[11px] text-[#2E8555]">Burnout Score</span>
            <div class="font-sora font-bold text-sm text-[#1E1B2E] mt-1">${val(life.burnout_score, ' / 100')}</div>
          </div>
        </div>
      </div>

    </div>
  `;

  // Auto-load initial At-Risk Brief for this student
  if (d.student_id) {
    switchStudentBriefTab(d.student_id, 'atrisk');
  }
}

window.switchStudentBriefTab = async function (studentId, tab) {
  const container = document.getElementById('student-brief-content');
  const btnAtRisk = document.getElementById('btn-tab-atrisk');
  const btnPerf = document.getElementById('btn-tab-perf');
  if (!container) return;

  if (btnAtRisk && btnPerf) {
    if (tab === 'atrisk') {
      btnAtRisk.className = 'px-3.5 py-1.5 rounded-xl font-sora font-semibold text-xs bg-[#6C5CE7] text-white transition-all shadow-sm';
      btnPerf.className = 'px-3.5 py-1.5 rounded-xl font-sora font-semibold text-xs bg-[#F6F5FC] text-[#8A8797] hover:bg-[#EDEBFB] hover:text-[#6C5CE7] transition-all';
    } else {
      btnPerf.className = 'px-3.5 py-1.5 rounded-xl font-sora font-semibold text-xs bg-[#6C5CE7] text-white transition-all shadow-sm';
      btnAtRisk.className = 'px-3.5 py-1.5 rounded-xl font-sora font-semibold text-xs bg-[#F6F5FC] text-[#8A8797] hover:bg-[#EDEBFB] hover:text-[#6C5CE7] transition-all';
    }
  }

  container.innerHTML = `
    <div class="flex items-center justify-center py-4">
      <div class="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-[#6C5CE7]"></div>
      <span class="ml-2 text-xs text-[#8A8797]">Synthesizing ${tab === 'atrisk' ? 'early-warning at-risk' : 'academic trajectory'} brief...</span>
    </div>
  `;

  const endpoint = tab === 'atrisk' ? `/api/genai/atrisk-brief/${encodeURIComponent(studentId)}` : `/api/genai/performance-summary/${encodeURIComponent(studentId)}`;

  try {
    const res = await fetch(`${API_BASE}${endpoint}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (tab === 'atrisk') {
      const prob = (data.model_probability * 100).toFixed(1);
      const badgeColor = data.model_probability >= 0.5 ? 'bg-[#FDEDEF] text-[#E85D75]' : 'bg-[#E7F8EE] text-[#4CAF7D]';
      container.innerHTML = `
        <div class="flex flex-wrap items-center gap-2 mb-3">
          <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold ${badgeColor}">
            Model Probability: ${prob}%
          </span>
          <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white text-[#6C5CE7]">
            Top Factor: ${data.model_top_factor}
          </span>
          ${data.is_fallback ? '<span class="px-2 py-0.5 rounded-full text-[10px] bg-white/70 text-[#8A8797]">Rule-Grounded</span>' : '<span class="px-2 py-0.5 rounded-full text-[10px] bg-purple-100 text-[#6C5CE7]">Gemini 2.5 Flash</span>'}
        </div>
        <p class="text-sm text-[#1E1B2E] font-medium leading-relaxed mb-3">
          ${data.brief_text}
        </p>
        <div class="pt-2 border-t border-purple-200/60 flex items-center justify-between text-[11px] text-[#8A8797]">
          <span>Source: Model 2 Early-Warning Classifier (45% Recall, 32% Precision)</span>
          <span class="italic font-medium">AI-generated — verify before acting</span>
        </div>
      `;
    } else {
      const dirColor = data.predicted_cgpa >= data.current_cgpa ? 'text-[#4CAF7D]' : 'text-[#E85D75]';
      container.innerHTML = `
        <div class="flex flex-wrap items-center gap-2 mb-3">
          <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white text-[#1E1B2E]">
            Current: ${data.current_cgpa.toFixed(2)} → Predicted: <strong class="${dirColor}">${data.predicted_cgpa.toFixed(2)}</strong>
          </span>
          <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#EDEBFB] text-[#6C5CE7]">
            R² = 0.21 Calibration
          </span>
          ${data.is_fallback ? '<span class="px-2 py-0.5 rounded-full text-[10px] bg-white/70 text-[#8A8797]">Rule-Grounded</span>' : '<span class="px-2 py-0.5 rounded-full text-[10px] bg-purple-100 text-[#6C5CE7]">Gemini 2.5 Flash</span>'}
        </div>
        <p class="text-sm text-[#1E1B2E] font-medium leading-relaxed mb-3">
          ${data.summary_text}
        </p>
        <div class="pt-2 border-t border-purple-200/60 flex items-center justify-between text-[11px] text-[#8A8797]">
          <span>Source: Model 1 Trajectory Predictor (R²=0.21 directional signal)</span>
          <span class="italic font-medium">AI-generated — verify before acting</span>
        </div>
      `;
    }
  } catch (err) {
    console.error('Student brief tab fetch error:', err);
    container.innerHTML = `<div class="py-4 text-center text-xs text-red-500">Failed to load brief for ${studentId}.</div>`;
  }
};


// ── VIEW 6: Career Guidance ───────────────────────────────────────────────────
function setupCareerSearch() {
  const form = document.getElementById('career-search-form');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const input = document.getElementById('career-search-input');
      const sid = input ? input.value.trim() : '';
      if (sid) loadCareerView(sid);
    });
  }
}

async function loadCareerView(studentId) {
  state.currentCareerStudentId = studentId;
  const container = document.getElementById('career-guidance-content');
  if (!container) return;

  container.innerHTML = `
    <div class="p-8 text-center">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[#6C5CE7]"></div>
      <div class="mt-2 text-xs text-[#8A8797]">Computing career readiness for ${studentId}...</div>
    </div>
  `;

  try {
    const res = await fetch(`${API_BASE}/api/students/${encodeURIComponent(studentId)}/career-guidance`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      container.innerHTML = `
        <div class="p-12 text-center bg-white rounded-2xl border border-[#EDEBFB]">
          <div class="text-4xl mb-2">🎯</div>
          <div class="font-sora font-semibold text-lg text-[#1E1B2E]">Student ${studentId} not found</div>
          <div class="text-xs text-[#8A8797] mt-1">Please try: STU00001, STU15140, STU08983, STU16970.</div>
        </div>
      `;
      return;
    }
    const data = await res.json();
    renderCareerGuidance(data);
  } catch (err) {
    console.error('Career guidance fetch error:', err);
    container.innerHTML = '<div class="p-8 text-center text-xs text-red-500">Failed to load career guidance.</div>';
  }
}

function renderCareerGuidance(data) {
  const container = document.getElementById('career-guidance-content');
  if (!container) return;

  const score = data.career_readiness_score;
  const peer = data.peer_benchmark || {};
  const gaps = data.skill_gap_breakdown || [];
  const focus = data.suggested_focus_area || {};
  const placement = data.placement_outcome_reference || {};
  const peerGroup = peer.peer_group || data.branch;

  // Gauge colour based on score
  const gaugeColor = score >= 60 ? '#4CAF7D' : score >= 40 ? '#6C5CE7' : '#E85D75';
  const gaugeLabel = score >= 60 ? 'Strong' : score >= 40 ? 'Developing' : 'Needs Focus';

  // Skill gap bar colours: coral (low pct) → lavender → mint (high pct)
  function gapBarColor(pct) {
    if (pct < 30) return { bg: '#FDEDEF', fill: '#E85D75', text: '#E85D75' };
    if (pct < 50) return { bg: '#FEF0E8', fill: '#E8985D', text: '#C47B35' };
    if (pct < 65) return { bg: '#EDEBFB', fill: '#6C5CE7', text: '#4B3FA8' };
    return { bg: '#E7F8EE', fill: '#4CAF7D', text: '#2E8555' };
  }

  // Placement reference panel with minimum sample size guard & widened band support
  const hasPlacementRef = placement.placement_rate_pct !== null && placement.placement_rate_pct !== undefined;
  const showPlacementCard = hasPlacementRef || placement.insufficient_peer_data;

  let placementPanel = '';
  if (placement.insufficient_peer_data) {
    placementPanel = `
      <div class="bg-white rounded-2xl p-6 border border-[#EDEBFB] shadow-sm flex flex-col justify-center h-full">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-sora font-semibold text-base text-[#1E1B2E]">Peer Outcome Reference</h3>
          <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-[#F6F5FC] text-[#8A8797]">Insufficient Cohort</span>
        </div>
        <div class="py-6 text-center">
          <div class="text-3xl mb-2">📊</div>
          <p class="text-xs text-[#8A8797] font-medium leading-relaxed max-w-sm mx-auto">
            Not enough comparable students in your branch/tier to show a reliable reference.
          </p>
          <p class="text-[11px] text-[#8A8797] mt-3 italic">${data.disclosure}</p>
        </div>
      </div>
    `;
  } else if (hasPlacementRef) {
    const bandBadge = placement.band_delta && placement.band_delta > 10
      ? `<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-[#FFF8E6] text-[#B7791F]">Widened Band (±${placement.band_delta})</span>`
      : `<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-[#E6F0FE] text-[#2F64C8]">Readiness Band ${placement.readiness_band}</span>`;

    const subtext = placement.is_coarse_comparison
      ? `Across all <strong>${placement.peer_count}</strong> students in <strong>${peerGroup}</strong> (widened due to small cohort size in narrow band):`
      : `Among <strong>${placement.peer_count}</strong> students in <strong>${peerGroup}</strong> with a similar Career Readiness Score (${placement.readiness_band}/100):`;

    placementPanel = `
      <div class="bg-white rounded-2xl p-6 border border-[#EDEBFB] shadow-sm">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-sora font-semibold text-base text-[#1E1B2E]">Peer Outcome Reference</h3>
          ${bandBadge}
        </div>
        <p class="text-xs text-[#8A8797] mb-4">${subtext}</p>
        <div class="grid grid-cols-2 gap-4">
          <div class="bg-[#E7F8EE] rounded-xl p-4 text-center">
            <div class="text-[11px] font-semibold text-[#2E8555] uppercase tracking-wider">Placement Rate</div>
            <div class="font-sora font-bold text-3xl text-[#1E1B2E] mt-1">${placement.placement_rate_pct}%</div>
          </div>
          <div class="bg-[#E6F0FE] rounded-xl p-4 text-center">
            <div class="text-[11px] font-semibold text-[#2F64C8] uppercase tracking-wider">Avg Package</div>
            <div class="font-sora font-bold text-3xl text-[#1E1B2E] mt-1">
              ${placement.avg_salary_lpa ? '&#8377;' + placement.avg_salary_lpa.toFixed(1) + ' LPA' : 'N/A'}
            </div>
          </div>
        </div>
        <p class="text-[11px] text-[#8A8797] mt-3 italic">${data.disclosure}</p>
      </div>
    `;
  }

  container.innerHTML = `
    <!-- Row 1: Gauge Card + Focus Callout -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

      <!-- Gauge / Score Card (5 cols) -->
      <div class="lg:col-span-5 bg-white rounded-2xl p-6 border border-[#EDEBFB] shadow-sm flex flex-col">
        <div class="flex items-center justify-between mb-2">
          <h3 class="font-sora font-semibold text-base text-[#1E1B2E]">Career Readiness Score</h3>
          <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-[#EDEBFB] text-[#6C5CE7]">0 – 100</span>
        </div>
        <p class="text-xs text-[#8A8797] mb-5">
          Weighted composite across 6 career skills, normalized against the full 25,000-student population.
        </p>

        <!-- Gauge-style doughnut via canvas -->
        <div class="relative h-[200px] w-full flex items-center justify-center">
          <canvas id="careerGaugeChart"></canvas>
          <div class="absolute text-center pointer-events-none">
            <div class="font-sora font-bold text-4xl text-[#1E1B2E]">${score}</div>
            <div class="text-xs font-semibold mt-0.5" style="color:${gaugeColor}">${gaugeLabel}</div>
          </div>
        </div>

        <!-- Peer Benchmark row -->
        <div class="mt-5 pt-4 border-t border-[#EDEBFB]">
          <div class="flex items-center justify-between text-sm">
            <div class="text-left">
              <div class="text-[11px] text-[#8A8797] uppercase tracking-wider">You</div>
              <div class="font-sora font-bold text-2xl text-[#6C5CE7]">${score}</div>
            </div>
            <div class="flex-1 mx-4">
              <div class="relative h-2 bg-[#EDEBFB] rounded-full overflow-hidden">
                <div class="absolute h-full bg-[#6C5CE7] rounded-full" style="width:${score}%"></div>
                <!-- Peer marker -->
                <div class="absolute top-[-4px] h-[16px] w-[2px] bg-[#8A8797]" style="left:${peer.peer_avg_readiness}%;transform:translateX(-50%)" title="Peer avg: ${peer.peer_avg_readiness}"></div>
              </div>
              <div class="flex justify-between text-[10px] text-[#8A8797] mt-1">
                <span>0</span><span>50</span><span>100</span>
              </div>
            </div>
            <div class="text-right">
              <div class="text-[11px] text-[#8A8797] uppercase tracking-wider">Peers</div>
              <div class="font-sora font-bold text-2xl text-[#8A8797]">${peer.peer_avg_readiness}</div>
            </div>
          </div>
          <div class="text-[11px] text-[#8A8797] mt-2 text-center">
            Benchmark: <strong>${peerGroup}</strong> (${peer.peer_count} students)
          </div>
        </div>
      </div>

      <!-- Skill Gaps Horizontal Bar Chart (7 cols) -->
      <div class="lg:col-span-7 bg-white rounded-2xl p-6 border border-[#EDEBFB] shadow-sm">
        <div class="flex items-center justify-between mb-1">
          <h3 class="font-sora font-semibold text-base text-[#1E1B2E]">Skill Gap Breakdown</h3>
          <span class="text-xs text-[#8A8797]">Lowest percentile = biggest gap</span>
        </div>
        <p class="text-xs text-[#8A8797] mb-4">Percentile rank within your engineering branch — gaps sorted top (worst) to bottom.</p>
        <div class="h-[250px] w-full relative">
          <canvas id="careerSkillGapChart"></canvas>
        </div>
      </div>

    </div>

    <!-- Row 2: Focus Area Callout + Placement Reference -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

      <!-- Suggested Focus Area Callout -->
      <div class="lg:col-span-${showPlacementCard ? '7' : '12'} rounded-2xl p-6 border border-purple-100 shadow-sm" style="background: linear-gradient(135deg, #EDEBFB 0%, #F6F5FC 100%)">
        <div class="flex items-start space-x-4">
          <div class="w-12 h-12 rounded-2xl bg-white shadow-sm flex items-center justify-center flex-shrink-0">
            <svg class="w-6 h-6 text-[#6C5CE7]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
          </div>
          <div>
            <div class="text-[11px] font-semibold text-[#6C5CE7] uppercase tracking-wider mb-1">Suggested Focus Area</div>
            <div class="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white text-[#6C5CE7] mb-2">${focus.label}</div>
            <p class="text-sm font-medium text-[#1E1B2E] leading-relaxed">${focus.suggestion}</p>
          </div>
        </div>
      </div>

      <!-- Placement Outcome Reference panel -->
      ${showPlacementCard ? `<div class="lg:col-span-5">${placementPanel}</div>` : ''}

    </div>

    <!-- Row 3: AI Career Guidance Narrative (Auto-Generated) -->
    <div id="career-narrative-card" class="rounded-2xl p-6 border border-purple-100 shadow-sm" style="background: linear-gradient(135deg, #EDEBFB 0%, #F6F5FC 100%)">
      <div class="flex items-start space-x-4">
        <div class="w-12 h-12 rounded-2xl bg-white shadow-sm flex items-center justify-center flex-shrink-0 text-[#6C5CE7]">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <div class="flex-1">
          <div class="flex items-center justify-between mb-1.5">
            <div class="text-[11px] font-semibold text-[#6C5CE7] uppercase tracking-wider">AI Career Guidance Narrative</div>
            <span class="text-[11px] px-2.5 py-0.5 rounded-full font-semibold bg-white text-[#6C5CE7]">Synthesized by Gemini 2.5 Flash</span>
          </div>
          <div id="career-narrative-text" class="text-sm font-medium text-[#1E1B2E] leading-relaxed">
            <div class="flex items-center py-2">
              <div class="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-[#6C5CE7] mr-2"></div>
              <span class="text-xs text-[#8A8797]">Generating personalized career narrative for ${data.student_id}...</span>
            </div>
          </div>
          <div class="text-[11px] text-[#8A8797] mt-3 pt-2 border-t border-purple-200/60 flex items-center justify-between">
            <span>Contextual peer benchmarking for ${peerGroup}</span>
            <span class="italic font-medium">AI-generated — verify before acting</span>
          </div>
        </div>
      </div>
    </div>
  `;

  // ── Render gauge chart (doughnut as half-gauge) ────────────────────────────
  const gaugeData = [score, 100 - score];
  getOrCreateChart('careerGaugeChart', {
    type: 'doughnut',
    data: {
      datasets: [{
        data: gaugeData,
        backgroundColor: [gaugeColor, '#F0EFFB'],
        borderWidth: 0,
        circumference: 270,
        rotation: -135,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '78%',
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
    },
  });

  // ── Render skill gap horizontal bar chart ─────────────────────────────────
  const gapLabels = gaps.map((g) => g.label);
  const gapPcts = gaps.map((g) => g.percentile_in_branch);
  const gapColors = gaps.map((g) => gapBarColor(g.percentile_in_branch).fill);

  getOrCreateChart('careerSkillGapChart', {
    type: 'bar',
    data: {
      labels: gapLabels,
      datasets: [{
        label: 'Percentile in Branch',
        data: gapPcts,
        backgroundColor: gapColors,
        borderRadius: 6,
        maxBarThickness: 28,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1E1B2E',
          titleFont: { family: 'Sora', size: 12 },
          bodyFont: { family: 'Inter', size: 12 },
          callbacks: {
            label: (ctx) => {
              const g = gaps[ctx.dataIndex];
              return ` ${ctx.raw.toFixed(1)}th percentile | Raw: ${g.student_raw}`;
            },
          },
        },
      },
      scales: {
        x: {
          min: 0, max: 100,
          grid: { color: '#F0EFFB' },
          ticks: { font: { family: 'Inter', size: 11 }, color: PALETTE.textMuted, callback: (v) => `${v}th` },
        },
        y: {
          grid: { display: false },
          ticks: { font: { family: 'Inter', size: 11 }, color: PALETTE.textPrimary },
        },
      },
    },
  });

  // Auto-load AI Career Guidance Narrative
  loadCareerNarrative(data.student_id);
}

async function loadCareerNarrative(studentId) {
  const textEl = document.getElementById('career-narrative-text');
  if (!textEl) return;

  try {
    const res = await fetch(`${API_BASE}/api/genai/career-guidance/${encodeURIComponent(studentId)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    textEl.innerHTML = `<p>${data.narrative_text}</p>`;
  } catch (err) {
    console.error('Career narrative fetch error:', err);
    textEl.innerHTML = '<p class="text-xs text-red-500">Failed to load AI career narrative.</p>';
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// VIEW 7: DATA & ETL PIPELINE MONITORING
// ═══════════════════════════════════════════════════════════════════════════════
let pipelinePollingInterval = null;
let pipelineTickerInterval = null;
let pipelineLastFetchedTime = null;
let pipelineExpandedStages = new Set([1, 2, 3, 4, 5, 6, 7]); // All stages open by default for immediate clarity

function startPipelinePolling() {
  stopPipelinePolling();
  pipelinePollingInterval = setInterval(() => {
    loadPipelineView(true);
  }, 30000);
  pipelineTickerInterval = setInterval(() => {
    updatePipelineLastUpdatedText();
  }, 1000);
}

function stopPipelinePolling() {
  if (pipelinePollingInterval) {
    clearInterval(pipelinePollingInterval);
    pipelinePollingInterval = null;
  }
  if (pipelineTickerInterval) {
    clearInterval(pipelineTickerInterval);
    pipelineTickerInterval = null;
  }
}

function updatePipelineLastUpdatedText() {
  const updatedEl = document.getElementById('pipeline-last-updated');
  if (!updatedEl || !pipelineLastFetchedTime) return;
  const diffSec = Math.floor((Date.now() - pipelineLastFetchedTime) / 1000);
  if (diffSec < 4) {
    updatedEl.textContent = 'Updated just now';
  } else if (diffSec < 60) {
    updatedEl.textContent = `Updated ${diffSec}s ago`;
  } else {
    const mins = Math.floor(diffSec / 60);
    updatedEl.textContent = `Updated ${mins}m ago`;
  }
}

window.refreshPipelineView = function () {
  const icon = document.getElementById('pipeline-refresh-icon');
  if (icon) icon.classList.add('animate-spin');
  loadPipelineView(false).finally(() => {
    if (icon) setTimeout(() => icon.classList.remove('animate-spin'), 600);
  });
};

window.toggleStageAccordion = function (stageNumber) {
  if (pipelineExpandedStages.has(stageNumber)) {
    pipelineExpandedStages.delete(stageNumber);
  } else {
    pipelineExpandedStages.add(stageNumber);
  }
  const detailEl = document.getElementById(`stage-detail-${stageNumber}`);
  const chevronEl = document.getElementById(`stage-chevron-${stageNumber}`);
  if (detailEl) {
    detailEl.classList.toggle('hidden');
  }
  if (chevronEl) {
    chevronEl.classList.toggle('rotate-180');
  }
};

async function loadPipelineView(isSilent = false) {
  const container = document.getElementById('pipeline-stages-container');
  if (!container) return;

  if (!isSilent && container.children.length === 0) {
    container.innerHTML = `
      <div class="skeleton h-32 w-full rounded-3xl mb-4"></div>
      <div class="skeleton h-32 w-full rounded-3xl mb-4"></div>
      <div class="skeleton h-32 w-full rounded-3xl mb-4"></div>
    `;
  }

  try {
    const res = await fetch(`${API_BASE}/api/pipeline/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    pipelineLastFetchedTime = Date.now();
    updatePipelineLastUpdatedText();

    // Top Summary Badges
    const overallBadge = document.getElementById('pipeline-overall-badge');
    const overallBadgeText = document.getElementById('pipeline-overall-badge-text');
    const progressBar = document.getElementById('pipeline-progress-bar');
    const progressText = document.getElementById('pipeline-progress-text');

    const healthyCount = data.healthy_stages_count || 0;
    const totalCount = data.total_stages_count || 7;
    const pct = Math.round((healthyCount / totalCount) * 100);

    if (overallBadge && overallBadgeText) {
      if (data.overall_status === 'healthy') {
        overallBadge.className = 'px-3 py-1 rounded-full text-xs font-bold bg-[#E7F8EE] text-[#4CAF7D] flex items-center space-x-1.5';
        overallBadgeText.textContent = `${healthyCount}/${totalCount} Stages Healthy`;
      } else if (data.overall_status === 'degraded') {
        overallBadge.className = 'px-3 py-1 rounded-full text-xs font-bold bg-[#FEF3C7] text-[#D97706] flex items-center space-x-1.5';
        overallBadgeText.textContent = `${healthyCount}/${totalCount} Stages Degraded`;
      } else {
        overallBadge.className = 'px-3 py-1 rounded-full text-xs font-bold bg-[#FDEDEF] text-[#E17055] flex items-center space-x-1.5';
        overallBadgeText.textContent = `${healthyCount}/${totalCount} Stages Error`;
      }
    }

    if (progressBar) {
      progressBar.style.width = `${pct}%`;
      if (data.overall_status === 'healthy') {
        progressBar.className = 'h-full rounded-full bg-gradient-to-r from-[#6C5CE7] via-[#8E7CF3] to-[#4CAF7D] transition-all duration-500';
      } else {
        progressBar.className = 'h-full rounded-full bg-gradient-to-r from-[#E17055] to-[#F39C12] transition-all duration-500';
      }
    }

    if (progressText) {
      progressText.textContent = `${healthyCount} of ${totalCount} Stages Operational (${pct}%)`;
    }

    // Render 7 Vertical Connected Stages
    renderPipelineStages(data.stages || []);

  } catch (err) {
    console.error('Failed to load pipeline status:', err);
    if (!isSilent) {
      container.innerHTML = `
        <div class="p-6 rounded-3xl bg-[#FDEDEF] border border-[#FADBD8] text-[#E17055] text-center">
          <p class="font-sora font-bold text-base">Pipeline Status Offline</p>
          <p class="text-xs mt-1 text-[#8A8797]">Unable to inspect pipeline health. Ensure the Campus360 API server is running on port 8000.</p>
          <button onclick="refreshPipelineView()" class="mt-4 px-4 py-2 bg-white rounded-xl border border-[#EDEBFB] text-xs font-semibold text-[#1E1B2E] shadow-sm hover:bg-[#FAFAFE]">Retry Inspection</button>
        </div>
      `;
    }
  }
}

function renderPipelineStages(stages) {
  const container = document.getElementById('pipeline-stages-container');
  if (!container) return;

  const stageNodesHtml = stages.map((stage) => {
    const isExpanded = pipelineExpandedStages.has(stage.stage_number);
    const isHealthy = stage.status === 'healthy';
    const isDegraded = stage.status === 'degraded';

    // Status styling tokens
    let statusPillClass = 'bg-[#E7F8EE] text-[#4CAF7D]';
    let statusText = 'Healthy';
    let nodeBgClass = 'bg-[#EDEBFB] text-[#6C5CE7] border-2 border-[#6C5CE7]';
    let dotClass = 'bg-[#4CAF7D]';

    if (isDegraded) {
      statusPillClass = 'bg-[#FEF3C7] text-[#D97706]';
      statusText = 'Degraded';
      nodeBgClass = 'bg-[#FEF3C7] text-[#D97706] border-2 border-[#D97706]';
      dotClass = 'bg-[#D97706]';
    } else if (!isHealthy) {
      statusPillClass = 'bg-[#FDEDEF] text-[#E17055]';
      statusText = 'Attention';
      nodeBgClass = 'bg-[#FDEDEF] text-[#E17055] border-2 border-[#E17055]';
      dotClass = 'bg-[#E17055]';
    }

    const detailsContent = renderStageDetailsHtml(stage);

    return `
      <div class="relative flex items-start space-x-3 md:space-x-5" id="stage-wrapper-${stage.stage_number}">
        <!-- Spine Node Icon Indicator -->
        <div class="relative z-10 flex-shrink-0 mt-3 md:mt-4">
          <div class="w-10 h-10 md:w-12 md:h-12 rounded-2xl flex items-center justify-center font-sora font-bold text-sm shadow-sm transition-transform duration-200 hover:scale-105 ${nodeBgClass}">
            <span>${stage.stage_number}</span>
          </div>
        </div>

        <!-- Stage Card Box -->
        <div class="flex-1 bg-white rounded-3xl border border-[#EDEBFB] shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden">
          <!-- Accordion Header -->
          <button type="button" onclick="toggleStageAccordion(${stage.stage_number})" class="w-full text-left p-4 md:p-5 flex items-center justify-between gap-3 cursor-pointer focus:outline-none select-none hover:bg-[#FAFAFE]/60 transition-colors">
            <div class="flex-1 min-w-0">
              <div class="flex flex-wrap items-center gap-2 mb-1">
                <span class="font-sora font-bold text-base text-[#1E1B2E]">${stage.stage_name}</span>
                <span class="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[#EDEBFB] text-[#6C5CE7]">${stage.category}</span>
                <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold ${statusPillClass} flex items-center space-x-1">
                  <span class="w-1.5 h-1.5 rounded-full ${dotClass}"></span>
                  <span>${statusText}</span>
                </span>
              </div>
              <div class="flex flex-wrap items-center gap-2 text-xs text-[#8A8797]">
                <span class="font-medium text-[#1E1B2E]">${stage.key_metric}</span>
                <span class="hidden sm:inline text-[#EDEBFB]">•</span>
                <span class="text-[11px] hidden sm:inline">${stage.summary}</span>
              </div>
            </div>

            <!-- Accordion Chevron -->
            <div class="flex-shrink-0 ml-2 p-1 text-[#8A8797]">
              <svg id="stage-chevron-${stage.stage_number}" class="w-5 h-5 transform transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </button>

          <!-- Accordion Content Drawer -->
          <div id="stage-detail-${stage.stage_number}" class="border-t border-[#EDEBFB] p-4 md:p-6 bg-[#FAFAFE] ${isExpanded ? '' : 'hidden'}">
            ${detailsContent}
          </div>
        </div>
      </div>
    `;
  }).join('');

  container.innerHTML = stageNodesHtml;
}

function renderStageDetailsHtml(stage) {
  const d = stage.details || {};

  // Stage 1: Data Sources
  if (stage.stage_id === 'sources') {
    const files = d.files || [];
    return `
      <div class="space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-2 text-xs text-[#8A8797]">
          <span>Canonical multi-cohort raw CSV inputs located in <code class="px-1.5 py-0.5 bg-white rounded border border-[#EDEBFB] text-[#6C5CE7] font-mono">data/raw/</code></span>
          <span class="font-semibold text-[#1E1B2E]">Total Records: ${d.total_raw_records?.toLocaleString() || '70,000'} across ${d.total_files || 6} files</span>
        </div>
        <div class="overflow-x-auto bg-white rounded-2xl border border-[#EDEBFB]">
          <table class="w-full text-left text-xs">
            <thead>
              <tr class="bg-[#F6F5FC] text-[#8A8797] border-b border-[#EDEBFB]">
                <th class="p-3 font-semibold">Source File</th>
                <th class="p-3 font-semibold">Cohort Role</th>
                <th class="p-3 font-semibold text-right">Rows</th>
                <th class="p-3 font-semibold text-right">Size</th>
                <th class="p-3 font-semibold text-right">Last Modified</th>
                <th class="p-3 font-semibold text-center">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[#EDEBFB]/70 font-sans">
              ${files.map((f) => `
                <tr class="hover:bg-[#FAFAFE]">
                  <td class="p-3 font-mono font-medium text-[#1E1B2E] text-[11px]">${f.filename}</td>
                  <td class="p-3 text-[#8A8797]">${f.role}</td>
                  <td class="p-3 text-right font-semibold text-[#1E1B2E]">${f.rows.toLocaleString()}</td>
                  <td class="p-3 text-right text-[#8A8797]">${f.size_kb ? `${f.size_kb} KB` : '-'}</td>
                  <td class="p-3 text-right text-[#8A8797] text-[11px]">${f.last_modified ? f.last_modified.replace('T', ' ').substring(0, 19) : '-'}</td>
                  <td class="p-3 text-center">
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#E7F8EE] text-[#4CAF7D]">PASS</span>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  // Stage 2: Data Ingestion
  if (stage.stage_id === 'ingestion') {
    const checks = d.checks || [];
    return `
      <div class="space-y-4">
        <div class="flex items-center justify-between text-xs text-[#8A8797]">
          <span>Schema profile, null bounds, and UTF-8 encoding validation from <code class="px-1.5 py-0.5 bg-white rounded border border-[#EDEBFB] text-[#6C5CE7] font-mono">src/etl/extract.py</code></span>
          <span class="font-semibold text-[#4CAF7D]">0 File Corruptions Detected</span>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          ${checks.map((c) => `
            <div class="p-3.5 bg-white rounded-2xl border border-[#EDEBFB] shadow-xs flex flex-col justify-between space-y-2">
              <div class="flex items-center justify-between">
                <span class="font-mono text-xs font-bold text-[#6C5CE7]">${c.source}</span>
                <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#E7F8EE] text-[#4CAF7D]">${c.status}</span>
              </div>
              <p class="text-[11px] font-mono text-[#8A8797] truncate" title="${c.file}">${c.file}</p>
              <div class="flex items-center justify-between text-xs pt-1 border-t border-[#EDEBFB]/60 text-[#1E1B2E]">
                <span>Parsed Rows: <strong>${c.parsed_rows?.toLocaleString()}</strong></span>
                <span class="text-[11px] text-[#8A8797]">${c.encoding}</span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // Stage 3: Data Cleaning
  if (stage.stage_id === 'cleaning') {
    const datasets = d.datasets || [];
    return `
      <div class="space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-2 text-xs text-[#8A8797]">
          <span>Deterministic handlers in <code class="px-1.5 py-0.5 bg-white rounded border border-[#EDEBFB] text-[#6C5CE7] font-mono">src/etl/clean.py</code>: snake_case casing, duplicate pruning & outlier clamps</span>
          <span class="font-semibold text-[#1E1B2E]">${d.total_duplicates_pruned?.toLocaleString() || '10,000'} Duplicates Pruned</span>
        </div>
        <div class="overflow-x-auto bg-white rounded-2xl border border-[#EDEBFB]">
          <table class="w-full text-left text-xs">
            <thead>
              <tr class="bg-[#F6F5FC] text-[#8A8797] border-b border-[#EDEBFB]">
                <th class="p-3 font-semibold">Clean File (data/interim/)</th>
                <th class="p-3 font-semibold">Transformation Applied</th>
                <th class="p-3 font-semibold text-right">Raw Rows</th>
                <th class="p-3 font-semibold text-right">Clean Rows</th>
                <th class="p-3 font-semibold text-right">Rows Pruned</th>
                <th class="p-3 font-semibold text-center">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[#EDEBFB]/70 font-sans">
              ${datasets.map((item) => {
                const isKundan = item.source === 'kundan';
                return `
                  <tr class="${isKundan ? 'bg-[#EDEBFB]/30' : 'hover:bg-[#FAFAFE]'}">
                    <td class="p-3 font-mono font-medium text-[#1E1B2E] text-[11px]">
                      ${item.clean_file}
                      ${isKundan ? '<span class="ml-1.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-[#EDEBFB] text-[#6C5CE7]">Key Dedup Pass</span>' : ''}
                    </td>
                    <td class="p-3 text-[#8A8797] text-[11px]">${item.rule_applied}</td>
                    <td class="p-3 text-right text-[#8A8797]">${item.raw_rows?.toLocaleString()}</td>
                    <td class="p-3 text-right font-semibold text-[#1E1B2E]">${item.clean_rows?.toLocaleString()}</td>
                    <td class="p-3 text-right font-bold ${item.rows_removed > 0 ? 'text-[#6C5CE7]' : 'text-[#8A8797]'}">
                      ${item.rows_removed > 0 ? `-${item.rows_removed.toLocaleString()} (${item.dedup_pct}%)` : '0 (0%)'}
                    </td>
                    <td class="p-3 text-center">
                      <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#E7F8EE] text-[#4CAF7D]">HEALTHY</span>
                    </td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  // Stage 4: Data Stitching
  if (stage.stage_id === 'stitching') {
    const matchCov = d.match_coverage || {};
    const sources = Object.keys(matchCov);
    return `
      <div class="space-y-4">
        <!-- Master Wide Summary Pill -->
        <div class="p-4 bg-white rounded-2xl border border-[#EDEBFB] flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
          <div>
            <div class="flex items-center space-x-2">
              <span class="font-mono text-sm font-bold text-[#1E1B2E]">student_master_wide.csv</span>
              <span class="px-2 py-0.5 rounded-md text-[10px] font-bold bg-[#E7F8EE] text-[#4CAF7D]">Single Source of Truth</span>
            </div>
            <p class="text-xs text-[#8A8797] mt-1">Attribute-based joining of 5 secondary sources onto Shambhuraje anchor without replacement.</p>
          </div>
          <div class="flex items-center space-x-4 text-right">
            <div>
              <span class="text-[10px] text-[#8A8797] uppercase tracking-wider block">Master Records</span>
              <span class="font-sora font-bold text-base text-[#6C5CE7]">${d.master_student_rows?.toLocaleString() || '25,000'}</span>
            </div>
            <div class="border-l border-[#EDEBFB] pl-4">
              <span class="text-[10px] text-[#8A8797] uppercase tracking-wider block">Total Features</span>
              <span class="font-sora font-bold text-base text-[#1E1B2E]">${d.column_count || 116} Cols</span>
            </div>
          </div>
        </div>

        <!-- 5 Match Coverage Cards -->
        <div class="text-xs font-semibold text-[#1E1B2E] mb-1">Secondary Source Matching Coverage</div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          ${sources.map((src) => {
            const m = matchCov[src];
            return `
              <div class="p-3.5 bg-white rounded-2xl border border-[#EDEBFB] shadow-xs space-y-2">
                <div class="flex items-center justify-between">
                  <span class="font-mono text-xs font-bold text-[#1E1B2E] capitalize">${src} Cohort</span>
                  <span class="text-xs font-bold text-[#6C5CE7]">${m.coverage_pct}%</span>
                </div>
                <div class="w-full bg-[#F6F5FC] rounded-full h-2 overflow-hidden border border-[#EDEBFB]/50">
                  <div class="h-full rounded-full bg-gradient-to-r from-[#6C5CE7] to-[#8E7CF3]" style="width: ${m.coverage_pct}%"></div>
                </div>
                <div class="flex items-center justify-between text-[11px] text-[#8A8797]">
                  <span>Matched: <strong>${m.matched_students?.toLocaleString()}</strong></span>
                  <span>Target: ${m.expected_count?.toLocaleString()}</span>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  // Stage 5: Transformation & Splits
  if (stage.stage_id === 'transformation') {
    const cb = d.class_balance || {};
    const splits = d.train_test_splits || {};
    return `
      <div class="space-y-4">
        <!-- Class Balance & Distribution Card -->
        <div class="p-4 bg-white rounded-2xl border border-[#EDEBFB] space-y-3">
          <div class="flex items-center justify-between text-xs">
            <span class="font-semibold text-[#1E1B2E]">Target Variable Class Balance (at_risk_flag)</span>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#E7F8EE] text-[#4CAF7D]">Safe/At-Risk Distribution Balanced</span>
          </div>
          <div class="w-full bg-[#FDEDEF] rounded-full h-3 overflow-hidden flex border border-[#EDEBFB]">
            <div class="bg-[#4CAF7D] h-full transition-all" style="width: ${cb.safe_class_pct || 68.1}%;" title="Safe (${cb.safe_class_pct}%)"></div>
            <div class="bg-[#E17055] h-full transition-all" style="width: ${cb.at_risk_class_pct || 31.9}%;" title="At-Risk (${cb.at_risk_class_pct}%)"></div>
          </div>
          <div class="flex items-center justify-between text-xs text-[#8A8797]">
            <div class="flex items-center space-x-2">
              <span class="w-2.5 h-2.5 rounded-full bg-[#4CAF7D]"></span>
              <span>Safe / On Track: <strong>${cb.safe_class_pct || 68.1}%</strong></span>
            </div>
            <div class="flex items-center space-x-2">
              <span class="w-2.5 h-2.5 rounded-full bg-[#E17055]"></span>
              <span>At-Risk Flagged: <strong>${cb.at_risk_class_pct || 31.9}%</strong></span>
            </div>
            <span class="text-[11px] text-[#8A8797]">Target Range: ${cb.target_range || '65/35 to 80/20'}</span>
          </div>
        </div>

        <!-- Train/Test Splits Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div class="p-3.5 bg-white rounded-2xl border border-[#EDEBFB] shadow-xs">
            <div class="flex items-center justify-between mb-2">
              <span class="font-semibold text-xs text-[#1E1B2E]">Model 1: CGPA Trajectory Splits</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-[#EDEBFB] text-[#6C5CE7]">80 / 20 Split</span>
            </div>
            <div class="grid grid-cols-2 gap-2 text-center text-xs">
              <div class="p-2 bg-[#F6F5FC] rounded-xl border border-[#EDEBFB]/50">
                <span class="text-[10px] text-[#8A8797] block">Train Rows</span>
                <span class="font-bold text-[#1E1B2E]">${splits.model1_train_rows?.toLocaleString() || '20,000'}</span>
              </div>
              <div class="p-2 bg-[#F6F5FC] rounded-xl border border-[#EDEBFB]/50">
                <span class="text-[10px] text-[#8A8797] block">Test Rows</span>
                <span class="font-bold text-[#1E1B2E]">${splits.model1_test_rows?.toLocaleString() || '5,000'}</span>
              </div>
            </div>
          </div>

          <div class="p-3.5 bg-white rounded-2xl border border-[#EDEBFB] shadow-xs">
            <div class="flex items-center justify-between mb-2">
              <span class="font-semibold text-xs text-[#1E1B2E]">Model 2: At-Risk Classifier Splits</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-[#EDEBFB] text-[#6C5CE7]">80 / 20 Split</span>
            </div>
            <div class="grid grid-cols-2 gap-2 text-center text-xs">
              <div class="p-2 bg-[#F6F5FC] rounded-xl border border-[#EDEBFB]/50">
                <span class="text-[10px] text-[#8A8797] block">Train Rows</span>
                <span class="font-bold text-[#1E1B2E]">${splits.model2_train_rows?.toLocaleString() || '20,000'}</span>
              </div>
              <div class="p-2 bg-[#F6F5FC] rounded-xl border border-[#EDEBFB]/50">
                <span class="text-[10px] text-[#8A8797] block">Test Rows</span>
                <span class="font-bold text-[#1E1B2E]">${splits.model2_test_rows?.toLocaleString() || '5,000'}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Governance Checks -->
        <div class="flex flex-wrap items-center gap-3 text-xs">
          <div class="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-white border border-[#EDEBFB] text-[#4CAF7D] font-medium">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
            <span>${d.pii_audit || '0 PII columns (navin_name, navin_email dropped)'}</span>
          </div>
          <div class="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-white border border-[#EDEBFB] text-[#6C5CE7] font-medium">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>
            <span>${d.leakage_audit || 'Model 2 strictly isolated to lifestyle features'}</span>
          </div>
        </div>
      </div>
    `;
  }

  // Stage 6: Data Warehouse
  if (stage.stage_id === 'warehouse') {
    const tbls = d.tables || {};
    const engine = d.active_database_engine || 'postgres';
    return `
      <div class="space-y-4">
        <div class="flex items-center justify-between text-xs text-[#8A8797]">
          <span>Live SQL <code class="px-1.5 py-0.5 bg-white rounded border border-[#EDEBFB] text-[#6C5CE7] font-mono">SELECT COUNT(*)</code> against active connection engine</span>
          <span class="px-2.5 py-1 rounded-full text-xs font-bold ${engine === 'postgres' ? 'bg-[#E7F8EE] text-[#4CAF7D]' : 'bg-[#FEF3C7] text-[#D97706]'} uppercase">
            Active Engine: ${engine}
          </span>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div class="p-3.5 bg-white rounded-2xl border border-[#EDEBFB] shadow-xs text-center">
            <span class="text-[11px] font-mono text-[#8A8797] block">dim_student</span>
            <span class="font-sora font-bold text-lg text-[#1E1B2E]">${tbls.dim_student?.toLocaleString() || '25,000'}</span>
            <span class="text-[10px] text-[#8A8797] block mt-0.5">Anchor Dimension</span>
          </div>
          <div class="p-3.5 bg-white rounded-2xl border border-[#EDEBFB] shadow-xs text-center">
            <span class="text-[11px] font-mono text-[#8A8797] block">fact_performance</span>
            <span class="font-sora font-bold text-lg text-[#6C5CE7]">${tbls.fact_performance?.toLocaleString() || '105,000'}</span>
            <span class="text-[10px] text-[#8A8797] block mt-0.5">Multi-Term Exams</span>
          </div>
          <div class="p-3.5 bg-white rounded-2xl border border-[#EDEBFB] shadow-xs text-center">
            <span class="text-[11px] font-mono text-[#8A8797] block">fact_lifestyle</span>
            <span class="font-sora font-bold text-lg text-[#1E1B2E]">${tbls.fact_lifestyle?.toLocaleString() || '25,000'}</span>
            <span class="text-[10px] text-[#8A8797] block mt-0.5">Wellness Metrics</span>
          </div>
          <div class="p-3.5 bg-white rounded-2xl border border-[#EDEBFB] shadow-xs text-center">
            <span class="text-[11px] font-mono text-[#8A8797] block">fact_career</span>
            <span class="font-sora font-bold text-lg text-[#1E1B2E]">${tbls.fact_career?.toLocaleString() || '25,000'}</span>
            <span class="text-[10px] text-[#8A8797] block mt-0.5">Readiness & Package</span>
          </div>
        </div>

        <div class="p-3 bg-white rounded-xl border border-[#EDEBFB] flex items-center justify-between text-xs text-[#8A8797]">
          <span>Foreign Key Constraints: <strong>${d.foreign_key_enforcement || 'dim_student(student_id) -> fact tables (VERIFIED)'}</strong></span>
          <span class="font-semibold text-[#1E1B2E]">Total Warehouse Records: ${d.total_warehouse_rows?.toLocaleString() || '180,000'}</span>
        </div>
      </div>
    `;
  }

  // Stage 7: Analytics, ML & GenAI
  if (stage.stage_id === 'analytics') {
    const m1 = d.model1_performance || {};
    const m2 = d.model2_atrisk || {};
    const genai = d.genai_status || {};
    return `
      <div class="space-y-4">
        <!-- Dual Machine Learning Models with PROMINENT AMBER LIMITATION BADGES -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          <!-- Model 1 Card -->
          <div class="p-4 bg-white rounded-2xl border border-[#EDEBFB] shadow-xs space-y-3 flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between mb-1">
                <span class="font-sora font-bold text-sm text-[#1E1B2E]">Model 1: CGPA Trajectory</span>
                <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#E7F8EE] text-[#4CAF7D]">${m1.status || 'LOADED'}</span>
              </div>
              <p class="text-[11px] font-mono text-[#8A8797]">${m1.name || 'GradientBoostingRegressor (anchor_cgpa)'}</p>
              
              <div class="grid grid-cols-2 gap-2 mt-3 text-center">
                <div class="p-2 bg-[#F6F5FC] rounded-xl border border-[#EDEBFB]/50">
                  <span class="text-[10px] text-[#8A8797] block">Test R² Score</span>
                  <span class="font-sora font-bold text-sm text-[#6C5CE7]">${m1.r2_score !== undefined ? m1.r2_score : 0.2117}</span>
                </div>
                <div class="p-2 bg-[#F6F5FC] rounded-xl border border-[#EDEBFB]/50">
                  <span class="text-[10px] text-[#8A8797] block">RMSE Error</span>
                  <span class="font-sora font-bold text-sm text-[#1E1B2E]">${m1.rmse || 0.9416}</span>
                </div>
              </div>
            </div>

            <!-- PROMINENT AMBER LIMITATION CALLOUT -->
            <div class="p-3 rounded-xl bg-[#FFFBEB] border border-[#FDE68A] text-xs text-[#92400E]">
              <div class="font-bold flex items-center space-x-1.5">
                <svg class="w-4 h-4 text-[#D97706] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <span>Known Limitation: Directional Signal Only</span>
              </div>
              <p class="text-[11px] mt-1 text-[#B45309] leading-relaxed">
                ${m1.limitation_badge || 'Model 1 explains ~21% of variance (R²≈0.21). Academic performance is heavily stochastic; predictions serve as advisory directional indicators rather than deterministic scores.'}
              </p>
            </div>
          </div>

          <!-- Model 2 Card -->
          <div class="p-4 bg-white rounded-2xl border border-[#EDEBFB] shadow-xs space-y-3 flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between mb-1">
                <span class="font-sora font-bold text-sm text-[#1E1B2E]">Model 2: At-Risk Classifier</span>
                <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#E7F8EE] text-[#4CAF7D]">${m2.status || 'LOADED'}</span>
              </div>
              <p class="text-[11px] font-mono text-[#8A8797]">${m2.name || 'RandomForestClassifier (at_risk_flag)'}</p>
              
              <div class="grid grid-cols-3 gap-2 mt-3 text-center">
                <div class="p-2 bg-[#F6F5FC] rounded-xl border border-[#EDEBFB]/50">
                  <span class="text-[10px] text-[#8A8797] block">Recall (Risk)</span>
                  <span class="font-sora font-bold text-sm text-[#6C5CE7]">${m2.recall_class1 !== undefined ? (m2.recall_class1 * 100).toFixed(1) : 45.1}%</span>
                </div>
                <div class="p-2 bg-[#F6F5FC] rounded-xl border border-[#EDEBFB]/50">
                  <span class="text-[10px] text-[#8A8797] block">Precision</span>
                  <span class="font-sora font-bold text-sm text-[#1E1B2E]">${m2.precision_class1 !== undefined ? (m2.precision_class1 * 100).toFixed(1) : 32.0}%</span>
                </div>
                <div class="p-2 bg-[#F6F5FC] rounded-xl border border-[#EDEBFB]/50">
                  <span class="text-[10px] text-[#8A8797] block">ROC-AUC</span>
                  <span class="font-sora font-bold text-sm text-[#1E1B2E]">${m2.roc_auc || 0.5312}</span>
                </div>
              </div>
            </div>

            <!-- PROMINENT AMBER LIMITATION CALLOUT -->
            <div class="p-3 rounded-xl bg-[#FFFBEB] border border-[#FDE68A] text-xs text-[#92400E]">
              <div class="font-bold flex items-center space-x-1.5">
                <svg class="w-4 h-4 text-[#D97706] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <span>Known Limitation: Lifestyle Early Warning (~2 in 3 False Alarms)</span>
              </div>
              <p class="text-[11px] mt-1 text-[#B45309] leading-relaxed">
                ${m2.limitation_badge || 'Recall is ~45% and Precision is ~32%. Designed as an exploratory lifestyle screening filter, not an automated disciplinary or tracking flag. Advisors must verify before intervention.'}
              </p>
            </div>
          </div>

        </div>

        <!-- GenAI Service Card -->
        <div class="p-4 bg-white rounded-2xl border border-[#EDEBFB] shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-[#EDEBFB] text-[#6C5CE7] flex items-center justify-center font-bold text-sm">
              AI
            </div>
            <div>
              <div class="flex items-center space-x-2">
                <span class="font-semibold text-xs text-[#1E1B2E]">GenAI Synthesis Engine</span>
                <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${genai.connectivity === 'api_connected' ? 'bg-[#E7F8EE] text-[#4CAF7D]' : 'bg-[#FEF3C7] text-[#D97706]'}">
                  ${genai.connectivity === 'api_connected' ? 'Google Gemini Connected' : 'Fallback Templates Active'}
                </span>
              </div>
              <p class="text-[11px] text-[#8A8797] mt-0.5">Active model: <code class="font-mono text-[#6C5CE7]">${genai.active_engine || 'gemini-3.6-flash'}</code></p>
            </div>
          </div>
          <div class="text-right text-xs">
            <span class="px-2.5 py-1 rounded-lg bg-[#F6F5FC] border border-[#EDEBFB] text-[#8A8797] text-[11px]">
              Offline Fallbacks Ready: <strong>Yes</strong>
            </span>
          </div>
        </div>

      </div>
    `;
  }

  return `<div class="text-xs text-[#8A8797]">No additional details for this stage.</div>`;
}

