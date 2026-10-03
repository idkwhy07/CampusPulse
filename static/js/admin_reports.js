const clusterList = document.getElementById('clusterList');
const reportsEmpty = document.getElementById('reportsEmpty');
const reportsUpdated = document.getElementById('reportsUpdated');
const refreshBtn = document.getElementById('reportsRefreshBtn');
const clearFiltersBtn = document.getElementById('clearFiltersBtn');

const searchInput = document.getElementById('reportsSearch');
const categoryFilter = document.getElementById('reportsCategory');
const locationFilter = document.getElementById('reportsLocation');
const roomFilter = document.getElementById('reportsRoom');
const statusFilter = document.getElementById('reportsStatus');
const visibleReportCount = document.getElementById('visibleReportCount');

let roomsByLocation = {};
let typingTimer = null;

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function fillSelect(select, items) {
  items.forEach((item) => {
    const option = document.createElement('option');
    option.value = item;
    option.textContent = item;
    select.appendChild(option);
  });
}

function setRoomFilter() {
  const current = roomFilter.value;
  const rooms = locationFilter.value
    ? (roomsByLocation[locationFilter.value] || [])
    : [...new Set(Object.values(roomsByLocation).flat())];

  roomFilter.innerHTML = '<option value="">Mọi phòng</option>';
  fillSelect(roomFilter, rooms);
  if (rooms.includes(current)) roomFilter.value = current;
}

async function loadOptions() {
  const response = await fetch('/api/options');
  const data = await response.json();
  roomsByLocation = data.rooms_by_location || {};
  fillSelect(categoryFilter, data.categories);
  fillSelect(locationFilter, data.locations);
  setRoomFilter();
}

function statusSlug(status) {
  if (status === 'Đang xử lý') return 'processing';
  if (status === 'Đã xử lý') return 'done';
  return 'new';
}

function renderCluster(cluster) {
  const reportsHtml = cluster.reports.map((report) => `
    <article class="raw-report-card">
      <div class="raw-report-topline">
        <strong>Report #${report.id}</strong>
        <span>${escapeHtml(report.created_at)}</span>
      </div>
      <p>${escapeHtml(report.description)}</p>
      <div class="raw-report-meta">
        <span>${escapeHtml(report.category)}</span>
        <span>${escapeHtml(report.location)}</span>
        <span>Phòng ${escapeHtml(report.room)}</span>
      </div>
    </article>
  `).join('');

  const formedText = `Incident #${cluster.incident_id}`;

  return `
    <article class="cluster-card cluster-${statusSlug(cluster.status)}">
      <div class="cluster-head">
        <div class="cluster-title-block">
          <span class="cluster-kicker">${formedText}</span>
          <h3>${escapeHtml(cluster.category)}</h3>
          <div class="cluster-location-line">
            <span>${escapeHtml(cluster.location)}</span>
            <span>•</span>
            <span>Phòng ${escapeHtml(cluster.room)}</span>
          </div>
        </div>
        <div class="cluster-badges">
          <span class="count-badge">${cluster.report_count} reports</span>
          <span class="status-pill status-pill-${statusSlug(cluster.status)}">${escapeHtml(cluster.status)}</span>
        </div>
      </div>

      <div class="cluster-stats">
        <div><span>Report đầu tiên</span><strong>${escapeHtml(cluster.first_report_at)}</strong></div>
        <div><span>Report gần nhất</span><strong>${escapeHtml(cluster.latest_report_at)}</strong></div>
        <div><span>Điều kiện gom</span><strong>Cùng vấn đề + tòa + phòng</strong></div>
      </div>

      <div class="cluster-report-section">
        <div class="cluster-report-heading">
          <strong>Toàn bộ report trong cụm</strong>
          <span>${cluster.report_count} báo cáo sinh viên</span>
        </div>
        <div class="raw-report-list">${reportsHtml}</div>
      </div>
    </article>
  `;
}

function renderClusters(clusters) {
  clusterList.innerHTML = clusters.map(renderCluster).join('');
  reportsEmpty.classList.toggle('hidden', clusters.length !== 0);
  visibleReportCount.textContent = clusters.reduce((sum, cluster) => sum + cluster.report_count, 0);
}

async function loadClusters() {
  const params = new URLSearchParams();

  if (searchInput.value.trim()) {
    params.set('q', searchInput.value.trim());
  }

  if (categoryFilter.value) {
    params.set('category', categoryFilter.value);
  }

  if (locationFilter.value) {
    params.set('location', locationFilter.value);
  }

  if (roomFilter.value) {
    params.set('room', roomFilter.value);
  }

  if (statusFilter.value) {
    params.set('status', statusFilter.value);
  }

  try {
    const response = await CampusPulseAPI.apiFetch(
      `/api/incidents?${params.toString()}`,
      {},
      'STAFF',
    );

    if (!response.ok) {
      throw new Error(
        `Không tải được incident (${response.status})`,
      );
    }

    const summaries = await response.json();

    if (!Array.isArray(summaries)) {
      throw new Error(
        'Dữ liệu incident không hợp lệ',
      );
    }

    const clusters = await Promise.all(
      summaries.map(async (summary) => {
        const detailResponse =
          await CampusPulseAPI.apiFetch(
            `/api/incidents/${summary.incident_id}`,
            {},
            'STAFF',
          );

        if (!detailResponse.ok) {
          throw new Error(
            `Không tải được incident #${summary.incident_id}`,
          );
        }

        const detail =
          await detailResponse.json();

        return {
          ...summary,
          ...detail,

          reports:
            Array.isArray(detail.reports)
              ? detail.reports
              : [],
        };
      }),
    );

    renderClusters(clusters);

    reportsUpdated.textContent =
      `Cập nhật ${new Date().toLocaleTimeString('vi-VN')}`;
  } catch (error) {
    reportsUpdated.textContent =
      error.message || 'Mất kết nối server';
  }
}

[categoryFilter, roomFilter, statusFilter].forEach((el) => {
  el.addEventListener('change', loadClusters);
});

locationFilter.addEventListener('change', () => {
  setRoomFilter();
  loadClusters();
});

searchInput.addEventListener('input', () => {
  clearTimeout(typingTimer);
  typingTimer = setTimeout(loadClusters, 250);
});

refreshBtn.addEventListener('click', loadClusters);
clearFiltersBtn.addEventListener('click', () => {
  searchInput.value = '';
  categoryFilter.value = '';
  locationFilter.value = '';
  roomFilter.value = '';
  statusFilter.value = '';
  setRoomFilter();
  loadClusters();
});

async function boot() {
  if (!CampusPulseAPI.requireRole('STAFF')) return;
  await loadOptions();
  await loadClusters();
  setInterval(loadClusters, 3000);
}

boot();
