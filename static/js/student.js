const form = document.getElementById('reportForm');
const category = document.getElementById('category');
const locationSelect = document.getElementById('location');
const roomInput = document.getElementById('room');
const roomOptions = document.getElementById('roomOptions');
const description = document.getElementById('description');
const charCount = document.getElementById('charCount');
const submitBtn = document.getElementById('submitBtn');
const toast = document.getElementById('toast');
const toastTitle = document.getElementById('toastTitle');
const toastText = document.getElementById('toastText');
const studentLastUpdated = document.getElementById('studentLastUpdated');
const studentTotalReports = document.getElementById('studentTotalReports');

const recentReportsList = document.getElementById('recentReportsList');
const recentReportsEmpty = document.getElementById('recentReportsEmpty');
const allReportsList = document.getElementById('allReportsList');
const allReportsEmpty = document.getElementById('allReportsEmpty');

const studentReportsSearch = document.getElementById('studentReportsSearch');
const studentReportsCategory = document.getElementById('studentReportsCategory');
const studentReportsLocation = document.getElementById('studentReportsLocation');
const studentReportsRoom = document.getElementById('studentReportsRoom');
const studentRefreshReportsBtn = document.getElementById('studentRefreshReportsBtn');
const studentClearFiltersBtn = document.getElementById('studentClearFiltersBtn');

const chatMessages = document.getElementById('chatMessages');
const chatEmptyState = document.getElementById('chatEmptyState');
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const quickPromptBtns = document.querySelectorAll('.quick-prompt-btn');

let roomsByLocation = {};
let categories = [];
let locations = [];

const errorEls = {
  category: document.getElementById('categoryError'),
  location: document.getElementById('locationError'),
  room: document.getElementById('roomError'),
  description: document.getElementById('descriptionError'),
};

function escapeHtml(value = '') {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function setOptions(select, options) {
  options.forEach((item) => {
    const option = document.createElement('option');
    option.value = item;
    option.textContent = item;
    select.appendChild(option);
  });
}

function replaceOptions(select, options, defaultLabel) {
  select.innerHTML = '';
  const first = document.createElement('option');
  first.value = '';
  first.textContent = defaultLabel;
  select.appendChild(first);
  setOptions(select, options);
}

function setRoomOptions() {
  const rooms = roomsByLocation[locationSelect.value] || [];
  roomOptions.innerHTML = '';
  rooms.forEach((room) => {
    const option = document.createElement('option');
    option.value = room;
    option.textContent = `Phòng ${room}`;
    roomOptions.appendChild(option);
  });
  roomInput.value = '';
  roomInput.disabled = rooms.length === 0;
  roomInput.placeholder = rooms.length ? 'Chọn hoặc nhập 10–50' : 'Chọn tòa nhà trước';
}

function updateHistoryRoomOptions() {
  const rooms = studentReportsLocation.value
    ? (roomsByLocation[studentReportsLocation.value] || [])
    : Object.values(roomsByLocation).flat();
  const uniqueRooms = [...new Set(rooms)].sort((a, b) => Number(a) - Number(b));
  replaceOptions(studentReportsRoom, uniqueRooms, 'Mọi phòng');
}

async function fetchJSON(url) {
  const response = await CampusPulseAPI.apiFetch(url, {}, 'STUDENT');
  if (!response.ok) throw new Error('Fetch failed');
  return response.json();
}

async function loadOptions() {
  const data = await fetchJSON('/api/options');
  roomsByLocation = data.rooms_by_location || {};
  categories = data.categories || [];
  locations = data.locations || [];

  setOptions(category, categories);
  setOptions(locationSelect, locations);
  replaceOptions(studentReportsCategory, categories, 'Mọi vấn đề');
  replaceOptions(studentReportsLocation, locations, 'Mọi tòa nhà');
  updateHistoryRoomOptions();
}

function buildOwnReportsUrl({ useFilters = false } = {}) {
  const params = new URLSearchParams();
  if (useFilters) {
    const q = studentReportsSearch.value.trim();
    if (q) params.set('q', q);
    if (studentReportsCategory.value) params.set('category', studentReportsCategory.value);
    if (studentReportsLocation.value) params.set('location', studentReportsLocation.value);
    if (studentReportsRoom.value) params.set('room', studentReportsRoom.value);
  }
  return `/api/reports/me?${params.toString()}`;
}

function getStudentReportStatusStyle(status) {
  const styles = {
    'Chưa xử lý': {
      cardClass: 'student-own-report-new',
      badgeClass: 'student-status-new',
      label: 'Chưa xử lý',
    },
    'Đang xử lý': {
      cardClass: 'student-own-report-processing',
      badgeClass: 'student-status-processing',
      label: 'Đang xử lý',
    },
    'Đã xử lý': {
      cardClass: 'student-own-report-done',
      badgeClass: 'student-status-done',
      label: 'Đã xử lý',
    },
  };

  return styles[status] || {
    cardClass: 'student-own-report-submitted',
    badgeClass: 'student-status-submitted',
    label: 'Đã gửi',
  };
}

function renderReportCard(report) {
  const statusStyle = getStudentReportStatusStyle(report.status);

  return `
    <article class="student-report-card student-own-report-card ${statusStyle.cardClass}">
      <div class="student-report-card-top">
        <div>
          <span class="student-report-kicker">REPORT #${report.id}</span>
          <h3>${escapeHtml(report.category)}</h3>
        </div>
        <span class="student-report-status ${statusStyle.badgeClass}">${statusStyle.label}</span>
      </div>
      <p>${escapeHtml(report.description)}</p>
      <div class="student-report-meta">
        <span>${escapeHtml(report.location)}</span>
        <span>Phòng ${escapeHtml(report.room)}</span>
        <span>${escapeHtml(report.created_at)}</span>
      </div>
    </article>
  `;
}

function renderReportList(container, emptyEl, reports) {
  container.innerHTML = reports.map(renderReportCard).join('');
  const isEmpty = reports.length === 0;
  emptyEl.classList.toggle('hidden', !isEmpty);
}

function updateLastUpdated() {
  studentLastUpdated.textContent = `Cập nhật lúc ${new Date().toLocaleTimeString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })}`;
}

async function refreshOwnReports() {
  const reports = await fetchJSON(buildOwnReportsUrl());
  studentTotalReports.textContent = reports.length;
  renderReportList(recentReportsList, recentReportsEmpty, reports.slice(0, 5));
  updateLastUpdated();
  return reports;
}

async function refreshAllReportsList() {
  const reports = await fetchJSON(buildOwnReportsUrl({ useFilters: true }));
  renderReportList(allReportsList, allReportsEmpty, reports);
  return reports;
}

function clearErrors() {
  Object.values(errorEls).forEach((el) => (el.textContent = ''));
}

function validateRoomLocally() {
  const validRooms = roomsByLocation[locationSelect.value] || [];
  if (!validRooms.includes(roomInput.value.trim())) {
    errorEls.room.textContent = 'Phòng phải đúng một giá trị trong danh sách của tòa đã chọn.';
    return false;
  }
  return true;
}

function showToast() {
  toastTitle.textContent = 'Đã gửi report!';
  toastText.textContent = 'Report của bạn đã được ghi nhận và có thể xem lại trong lịch sử.';
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3200);
}

function activateTab(tabName) {
  document.querySelectorAll('[data-student-tab]').forEach((item) => {
    item.classList.toggle('active', item.dataset.studentTab === tabName);
  });

  document.querySelectorAll('.student-tab-section').forEach((section) => section.classList.add('hidden'));
  const id = `studentTab${tabName.charAt(0).toUpperCase()}${tabName.slice(1)}`;
  document.getElementById(id)?.classList.remove('hidden');

  if (tabName === 'history') refreshAllReportsList().catch(() => {});
  if (tabName === 'chatbot') chatInput.focus();
}

function autoSizeChatInput() {
  chatInput.style.height = 'auto';
  chatInput.style.height = `${Math.min(chatInput.scrollHeight, 160)}px`;
}

function addChatMessage(role, text) {
  chatEmptyState.classList.add('hidden');
  const row = document.createElement('div');
  row.className = `chat-message chat-message-modern ${role}`;
  row.innerHTML = `
    <div class="chat-avatar">${role === 'bot' ? 'CP' : 'Bạn'}</div>
    <div class="chat-message-content">${escapeHtml(text)}</div>
  `;
  chatMessages.appendChild(row);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function getBotReply(message) {
  const text = message.toLowerCase();

  if (text.includes('wifi') || text.includes('wi-fi') || text.includes('mạng') || text.includes('internet')) {
    return 'Bạn nên ghi rõ vị trí, thời điểm bắt đầu, biểu hiện cụ thể và phạm vi ảnh hưởng. Ví dụ: “Wi-Fi phòng 24 H1 mất kết nối từ 9h15, nhiều thiết bị trong lớp đều không truy cập được Internet.”';
  }
  if (text.includes('xem lại') || text.includes('đã gửi') || text.includes('lịch sử') || text.includes('ở đâu')) {
    return 'Bạn có thể mở mục “Tất cả báo cáo đã gửi” ở thanh bên trái. Trang đó chỉ hiển thị report của chính bạn.';
  }
  if (text.includes('viết') || text.includes('mô tả') || text.includes('rõ ràng') || text.includes('report')) {
    return 'Một report rõ ràng nên có 4 ý: vấn đề gì, xảy ra ở đâu, bắt đầu khi nào và ảnh hưởng như thế nào. Tránh mô tả quá chung như “bị lỗi” hoặc “không dùng được”.';
  }
  if (text.includes('phòng') || text.includes('tòa')) {
    return 'Hãy chọn đúng tòa nhà và phòng nơi sự cố xảy ra. Nếu vấn đề xuất hiện ở nhiều vị trí, hãy gửi thông tin cho vị trí bạn trực tiếp quan sát được.';
  }

  return 'Mình có thể hỗ trợ bạn cách viết report, chọn thông tin cần điền và xem lại những report bạn đã gửi. Hãy mô tả điều bạn đang cần.';
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  clearErrors();
  if (!validateRoomLocally()) return;

  submitBtn.disabled = true;
  submitBtn.querySelector('span').textContent = 'Đang gửi...';

  try {
    const response = await CampusPulseAPI.apiFetch('/api/reports', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        category: category.value,
        location: locationSelect.value,
        room: roomInput.value.trim(),
        description: description.value,
      }),
    }, 'STUDENT');

    const data = await response.json();
    if (!response.ok) {
      errorEls.description.textContent = data.error || 'Dữ liệu report chưa hợp lệ.';
      return;
    }

    form.reset();
    roomOptions.innerHTML = '';
    roomInput.disabled = true;
    roomInput.placeholder = 'Chọn tòa nhà trước';
    charCount.textContent = '0';
    showToast();
    await Promise.all([refreshOwnReports(), refreshAllReportsList()]);
  } catch (error) {
    errorEls.description.textContent = 'Không kết nối được server Go. Hãy kiểm tra backend đang chạy.';
  } finally {
    submitBtn.disabled = false;
    submitBtn.querySelector('span').textContent = 'Gửi report';
  }
});

locationSelect.addEventListener('change', () => {
  setRoomOptions();
  errorEls.room.textContent = '';
});

description.addEventListener('input', () => {
  charCount.textContent = description.value.length;
});

roomInput.addEventListener('input', () => {
  errorEls.room.textContent = '';
});

studentReportsSearch.addEventListener('input', () => refreshAllReportsList().catch(() => {}));
studentReportsCategory.addEventListener('change', () => refreshAllReportsList().catch(() => {}));
studentReportsRoom.addEventListener('change', () => refreshAllReportsList().catch(() => {}));
studentReportsLocation.addEventListener('change', () => {
  updateHistoryRoomOptions();
  refreshAllReportsList().catch(() => {});
});

studentRefreshReportsBtn.addEventListener('click', () => {
  Promise.all([refreshOwnReports(), refreshAllReportsList()]).catch(() => {});
});

studentClearFiltersBtn.addEventListener('click', () => {
  studentReportsSearch.value = '';
  studentReportsCategory.value = '';
  studentReportsLocation.value = '';
  updateHistoryRoomOptions();
  refreshAllReportsList().catch(() => {});
});

document.querySelectorAll('[data-student-tab]').forEach((tab) => {
  tab.addEventListener('click', (event) => {
    event.preventDefault();
    activateTab(tab.dataset.studentTab);
  });
});

chatInput.addEventListener('input', autoSizeChatInput);
chatInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

chatForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;

  addChatMessage('user', message);
  chatInput.value = '';
  autoSizeChatInput();
  const reply = getBotReply(message);
  setTimeout(() => addChatMessage('bot', reply), 180);
});

quickPromptBtns.forEach((button) => {
  button.addEventListener('click', () => {
    chatInput.value = button.dataset.prompt || button.textContent.trim();
    autoSizeChatInput();
    chatForm.requestSubmit();
  });
});

async function refreshStudentStatusViews() {
  try {
    await refreshOwnReports();
    const historyTab = document.getElementById('studentTabHistory');
    if (historyTab && !historyTab.classList.contains('hidden')) {
      await refreshAllReportsList();
    }
  } catch (_) {
    // Giữ UI hiện tại nếu một lần auto-refresh bị lỗi.
  }
}

async function init() {
  if (!CampusPulseAPI.requireRole('STUDENT')) return;
  try {
    await loadOptions();
    await Promise.all([refreshOwnReports(), refreshAllReportsList()]);
    activateTab('recent');
    setInterval(refreshStudentStatusViews, 3000);
  } catch (error) {
    errorEls.category.textContent = 'Không tải được dữ liệu ban đầu. Hãy kiểm tra backend Go và PostgreSQL.';
  }
}

init();
