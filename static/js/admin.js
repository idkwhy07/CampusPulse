const listEl = document.getElementById('reportList');
const emptyState = document.getElementById('emptyState');
const refreshBtn = document.getElementById('refreshBtn');
const lastUpdated = document.getElementById('lastUpdated');

const totalCount = document.getElementById('totalCount');
const newCount = document.getElementById('newCount');
const processingCount = document.getElementById('processingCount');
const doneCount = document.getElementById('doneCount');

let refreshTimer = null;
let openMenuId = null;
let isUpdatingStatus = false;

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function statusSlug(status) {
  if (status === 'Đang xử lý') return 'processing';
  if (status === 'Đã xử lý') return 'done';
  return 'new';
}

function makeStatusMenu(incident) {
  const statuses = [
    { label: 'Chưa xử lý', value: 'CONFIRMED' },
    { label: 'Đang xử lý', value: 'IN_PROGRESS' },
    { label: 'Đã xử lý', value: 'RESOLVED' },
  ];
  const items = statuses.map((status) => `
    <button type="button" class="status-menu-item ${status.label === incident.status ? 'selected' : ''}"
      data-incident-id="${incident.incident_id}" data-status="${status.value}">
      <span class="menu-status-dot menu-${statusSlug(status.label)}"></span>
      ${escapeHtml(status.label)}
    </button>
  `).join('');

  return `
    <div class="status-menu-wrap">
      <button type="button" class="dots-btn" aria-label="Thay đổi trạng thái" data-menu-trigger="${incident.incident_id}">
        <span></span><span></span><span></span>
      </button>
      <div class="status-menu ${String(openMenuId) === String(incident.incident_id) ? '' : 'hidden'}" data-menu="${incident.incident_id}">
        ${items}
      </div>
    </div>
  `;
}

function renderIncidents(incidents) {
  listEl.innerHTML = '';
  emptyState.classList.toggle('hidden', incidents.length !== 0);

  incidents.forEach((incident) => {
    const card = document.createElement('article');
    card.className = `incident-row incident-${statusSlug(incident.status)}`;
    card.innerHTML = `
      <div class="incident-id-block">
        <span class="incident-label">INCIDENT</span>
        <strong>#${incident.incident_id}</strong>
      </div>
      <div class="incident-main">
        <strong>${escapeHtml(incident.category)}</strong>
        <span>${incident.report_count} reports</span>
      </div>
      <div class="incident-location">
        <span>Tòa nhà</span>
        <strong>${escapeHtml(incident.location)}</strong>
      </div>
      <div class="incident-room">
        <span>Phòng</span>
        <strong>${escapeHtml(incident.room)}</strong>
      </div>
      <div class="incident-status-block">
        <span class="status-pill status-pill-${statusSlug(incident.status)}">${escapeHtml(incident.status)}</span>
        <span class="report-time">Hình thành ${escapeHtml(incident.emerged_at)}</span>
      </div>
      ${makeStatusMenu(incident)}
    `;
    listEl.appendChild(card);
  });

  bindMenus();
}

function bindMenus() {
  document.querySelectorAll('[data-menu-trigger]').forEach((button) => {
    button.addEventListener('click', (event) => {
      event.stopPropagation();

      const id = button.dataset.menuTrigger;
      const menu = document.querySelector(`[data-menu="${id}"]`);
      const shouldOpen = menu?.classList.contains('hidden') ?? false;

      document.querySelectorAll('.status-menu').forEach((item) => item.classList.add('hidden'));

      if (shouldOpen && menu) {
        menu.classList.remove('hidden');
        openMenuId = id;
      } else {
        openMenuId = null;
      }
    });
  });

  document.querySelectorAll('.status-menu-item').forEach((button) => {
    button.addEventListener('click', async (event) => {
      event.stopPropagation();
      openMenuId = null;
      await updateStatus(button.dataset.incidentId, button.dataset.status);
    });
  });
}

document.addEventListener('click', () => {
  openMenuId = null;
  document.querySelectorAll('.status-menu').forEach((menu) => menu.classList.add('hidden'));
});

function setMetrics(incidents) {
  totalCount.textContent = incidents.length;
  newCount.textContent = incidents.filter((i) => i.status === 'Chưa xử lý').length;
  processingCount.textContent = incidents.filter((i) => i.status === 'Đang xử lý').length;
  doneCount.textContent = incidents.filter((i) => i.status === 'Đã xử lý').length;
}

async function loadIncidents() {
  try {
    const response = await CampusPulseAPI.apiFetch('/api/incidents', {}, 'STAFF');
    if (!response.ok) throw new Error(`Không tải được incident (${response.status})`);
    const incidents = await response.json();
    if (!Array.isArray(incidents)) throw new Error('Dữ liệu incident không hợp lệ');
    renderIncidents(incidents);
    setMetrics(incidents);
    lastUpdated.classList.remove('status-update-error');
    lastUpdated.textContent = `Cập nhật ${new Date().toLocaleTimeString('vi-VN')}`;
  } catch (error) {
    lastUpdated.classList.add('status-update-error');
    lastUpdated.textContent = error.message || 'Mất kết nối server';
  }
}

async function updateStatus(id, status) {
  if (isUpdatingStatus) return;
  isUpdatingStatus = true;
  lastUpdated.classList.remove('status-update-error');
  lastUpdated.textContent = 'Đang đổi trạng thái...';
  try {
    const response = await CampusPulseAPI.apiFetch(`/api/incidents/${id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    }, 'STAFF');
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || `Đổi trạng thái thất bại (${response.status})`);
    }
    await loadIncidents();
  } catch (error) {
    lastUpdated.classList.add('status-update-error');
    lastUpdated.textContent = error.message || 'Không đổi được trạng thái';
  } finally {
    isUpdatingStatus = false;
  }
}

refreshBtn.addEventListener('click', loadIncidents);

async function boot() {
  if (!CampusPulseAPI.requireRole('STAFF')) return;
  await loadIncidents();
  refreshTimer = setInterval(() => {
    // Không re-render danh sách khi admin đang mở menu trạng thái.
    // Việc re-render mỗi 2.5 giây trước đây chính là nguyên nhân menu tự đóng.
    if (openMenuId === null && !isUpdatingStatus) {
      loadIncidents();
    }
  }, 2500);
}

boot();
