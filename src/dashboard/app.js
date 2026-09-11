/**
 * Campus360 Dashboard Application Logic
 * Modern Ed-Tech SaaS Dashboard
 */

// API Base URL resolution (supports both same-origin and separate dashboard server)
const API_BASE = (window.location.port === '8501' || window.location.port === '5500' || window.location.port === '3000')
  ? 'http://localhost:8000'
  : '';

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
};

// ── Initialization ────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupSliders();
  setupStudentSearch();
  loadCurrentDate();

  // Initial View Load
  switchView('overview');
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

function switchView(viewName) {
  state.currentView = viewName;

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
}

// Global Helper to jump to a student from lists
window.jumpToStudent = function (studentId) {
  state.currentStudentId = studentId;
  const input = document.getElementById('student-search-input');
  if (input) input.value = studentId;
  switchView('student');
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
}
