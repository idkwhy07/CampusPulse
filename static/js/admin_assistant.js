(() => {
  if (!document.body.classList.contains('admin-body')) return;

  const STORAGE_KEY = 'campuspulse-admin-ai-position';
  const DRAG_THRESHOLD = 6;

  const root = document.createElement('div');
  root.className = 'admin-ai-root';
  root.innerHTML = `
    <button class="admin-ai-bubble" type="button" aria-label="Mở CampusPulse AI" aria-expanded="false">
      <span class="admin-ai-bubble-mark">CP</span>
      <span class="admin-ai-bubble-spark">✦</span>
    </button>

    <section class="admin-ai-panel hidden" aria-label="CampusPulse AI">
      <header class="admin-ai-panel-head">
        <div class="admin-ai-title-wrap">
          <div class="admin-ai-logo">CP</div>
          <div>
            <strong>CampusPulse AI</strong>
            <span>Trợ lý Admin</span>
          </div>
        </div>
        <button class="admin-ai-close" type="button" aria-label="Đóng">×</button>
      </header>

      <div class="admin-ai-conversation">
        <div class="admin-ai-empty">
          <div class="admin-ai-empty-logo">CP</div>
          <h3>Xin chào, mình có thể giúp gì?</h3>
          <p>Hỏi nhanh về incident, report hoặc cách sử dụng trang quản trị.</p>
          <div class="admin-ai-suggestions">
            <button type="button" data-admin-ai-prompt="Tóm tắt tình trạng incident hiện tại">Tóm tắt incident</button>
            <button type="button" data-admin-ai-prompt="Giải thích các trạng thái incident">Các trạng thái</button>
            <button type="button" data-admin-ai-prompt="Trang Reports dùng để làm gì?">Cách dùng Reports</button>
          </div>
        </div>
        <div class="admin-ai-messages" aria-live="polite"></div>
      </div>

      <div class="admin-ai-composer-wrap">
        <form class="admin-ai-composer">
          <textarea rows="1" placeholder="Nhắn CampusPulse AI..." aria-label="Tin nhắn"></textarea>
          <button type="submit" aria-label="Gửi">↑</button>
        </form>
        <small>AI demo có thể trả lời sai. Hãy kiểm tra thông tin quan trọng.</small>
      </div>
    </section>
  `;
  document.body.appendChild(root);

  const bubble = root.querySelector('.admin-ai-bubble');
  const panel = root.querySelector('.admin-ai-panel');
  const closeBtn = root.querySelector('.admin-ai-close');
  const form = root.querySelector('.admin-ai-composer');
  const input = form.querySelector('textarea');
  const empty = root.querySelector('.admin-ai-empty');
  const messages = root.querySelector('.admin-ai-messages');
  const promptButtons = root.querySelectorAll('[data-admin-ai-prompt]');

  let pointerId = null;
  let startX = 0;
  let startY = 0;
  let startLeft = 0;
  let startTop = 0;
  let dragged = false;
  let suppressClick = false;

  function escapeHtml(value) {
    return String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function getBubbleSize() {
    const rect = bubble.getBoundingClientRect();
    return { width: rect.width || 58, height: rect.height || 58 };
  }

  function setBubblePosition(left, top, save = true) {
    const { width, height } = getBubbleSize();
    const pad = 12;
    const x = clamp(left, pad, Math.max(pad, window.innerWidth - width - pad));
    const y = clamp(top, pad, Math.max(pad, window.innerHeight - height - pad));

    root.style.left = `${x}px`;
    root.style.top = `${y}px`;
    root.style.right = 'auto';
    root.style.bottom = 'auto';

    if (save) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ left: x, top: y }));
    }
    positionPanel();
  }

  function restoreBubblePosition() {
    try {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
      if (stored && Number.isFinite(stored.left) && Number.isFinite(stored.top)) {
        requestAnimationFrame(() => setBubblePosition(stored.left, stored.top, false));
      }
    } catch (_) {
      // Ignore an invalid stored position and use the CSS default.
    }
  }

  function positionPanel() {
    if (panel.classList.contains('hidden')) return;

    const bubbleRect = bubble.getBoundingClientRect();
    const panelRect = panel.getBoundingClientRect();
    const gap = 12;
    const pad = 12;
    const width = panelRect.width || Math.min(390, window.innerWidth - 24);
    const height = panelRect.height || Math.min(540, window.innerHeight - 24);

    let left;
    if (bubbleRect.left + bubbleRect.width / 2 > window.innerWidth / 2) {
      left = bubbleRect.left - width - gap;
    } else {
      left = bubbleRect.right + gap;
    }

    if (left < pad || left + width > window.innerWidth - pad) {
      left = clamp(bubbleRect.left + bubbleRect.width / 2 - width / 2, pad, window.innerWidth - width - pad);
    }

    let top = bubbleRect.top + bubbleRect.height / 2 - height / 2;
    top = clamp(top, pad, Math.max(pad, window.innerHeight - height - pad));

    panel.style.left = `${left}px`;
    panel.style.top = `${top}px`;
  }

  function setOpen(open) {
    panel.classList.toggle('hidden', !open);
    bubble.classList.toggle('active', open);
    bubble.setAttribute('aria-expanded', String(open));
    if (open) {
      requestAnimationFrame(() => {
        positionPanel();
        input.focus();
      });
    }
  }

  function autoSizeInput() {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 110)}px`;
  }

  function addMessage(role, text) {
    empty.classList.add('hidden');
    const row = document.createElement('div');
    row.className = `admin-ai-message ${role}`;
    row.innerHTML = `
      <div class="admin-ai-avatar">${role === 'bot' ? 'CP' : 'Bạn'}</div>
      <div class="admin-ai-message-content">${escapeHtml(text)}</div>
    `;
    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;
  }

  async function incidentSummary() {
    try {
      const response = await CampusPulseAPI.apiFetch('/api/incidents', {}, 'STAFF');
      if (!response.ok) throw new Error('Request failed');
      const incidents = await response.json();
      const newCount = incidents.filter((item) => item.status === 'Chưa xử lý').length;
      const processing = incidents.filter((item) => item.status === 'Đang xử lý').length;
      const done = incidents.filter((item) => item.status === 'Đã xử lý').length;

      if (!incidents.length) {
        return 'Hiện chưa có incident nào đạt ngưỡng 4 reports để hình thành.';
      }

      return `Hiện có ${incidents.length} incident: ${newCount} chưa xử lý, ${processing} đang xử lý và ${done} đã xử lý. Chỉ những cụm đã đạt ít nhất 4 reports mới xuất hiện ở khu vực Admin.`;
    } catch (_) {
      return 'Mình chưa đọc được dữ liệu incident lúc này. Bạn có thể thử làm mới trang rồi hỏi lại.';
    }
  }

  async function getReply(message) {
    const text = message.toLowerCase();

    if (text.includes('tóm tắt') || text.includes('bao nhiêu') || text.includes('tình trạng') || text.includes('hiện tại')) {
      return incidentSummary();
    }
    if (text.includes('trạng thái') || text.includes('chưa xử lý') || text.includes('đang xử lý') || text.includes('đã xử lý')) {
      return 'Incident có 3 trạng thái: “Chưa xử lý”, “Đang xử lý” và “Đã xử lý”. Trên Dashboard, bạn có thể đổi trạng thái bằng menu ba chấm ở cuối mỗi incident.';
    }
    if (text.includes('report') && (text.includes('4') || text.includes('ngưỡng') || text.includes('hình thành') || text.includes('gom'))) {
      return 'Hệ thống gom report theo cùng vấn đề, tòa nhà và phòng. Khi một cụm đạt đủ 4 reports thì mới hình thành incident và xuất hiện trong khu vực Admin.';
    }
    if (text.includes('reports') || text.includes('bộ lọc') || text.includes('tìm')) {
      return 'Trang Reports dùng để xem các report thuộc những incident đã hình thành. Bạn có thể tìm kiếm và lọc theo vấn đề, tòa nhà, phòng hoặc trạng thái.';
    }
    if (text.includes('dashboard') || text.includes('incident')) {
      return 'Dashboard tập trung vào các incident đã hình thành. Mỗi card cho biết vấn đề, số reports, vị trí, phòng, trạng thái và thời điểm incident hình thành.';
    }

    return 'Mình có thể hỗ trợ bạn đọc nhanh tình trạng incident, giải thích trạng thái, ngưỡng 4 reports và cách dùng trang Reports. Bạn muốn xem phần nào?';
  }

  async function sendMessage(message) {
    const clean = message.trim();
    if (!clean) return;

    addMessage('user', clean);
    input.value = '';
    autoSizeInput();

    const reply = await getReply(clean);
    window.setTimeout(() => addMessage('bot', reply), 140);
  }

  bubble.addEventListener('pointerdown', (event) => {
    if (event.button !== 0) return;
    const rect = bubble.getBoundingClientRect();
    pointerId = event.pointerId;
    startX = event.clientX;
    startY = event.clientY;
    startLeft = rect.left;
    startTop = rect.top;
    dragged = false;
    bubble.setPointerCapture(pointerId);
    bubble.classList.add('dragging');
  });

  bubble.addEventListener('pointermove', (event) => {
    if (pointerId !== event.pointerId) return;
    const dx = event.clientX - startX;
    const dy = event.clientY - startY;
    if (!dragged && Math.hypot(dx, dy) >= DRAG_THRESHOLD) dragged = true;
    if (!dragged) return;
    event.preventDefault();
    setBubblePosition(startLeft + dx, startTop + dy, false);
  });

  function finishDrag(event) {
    if (pointerId !== event.pointerId) return;
    if (dragged) {
      const rect = bubble.getBoundingClientRect();
      setBubblePosition(rect.left, rect.top, true);
      suppressClick = true;
      window.setTimeout(() => { suppressClick = false; }, 0);
    }
    bubble.classList.remove('dragging');
    if (bubble.hasPointerCapture(pointerId)) bubble.releasePointerCapture(pointerId);
    pointerId = null;
  }

  bubble.addEventListener('pointerup', finishDrag);
  bubble.addEventListener('pointercancel', finishDrag);

  bubble.addEventListener('click', (event) => {
    if (suppressClick) {
      event.preventDefault();
      return;
    }
    setOpen(panel.classList.contains('hidden'));
  });

  closeBtn.addEventListener('click', () => setOpen(false));

  input.addEventListener('input', autoSizeInput);
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    sendMessage(input.value);
  });

  promptButtons.forEach((button) => {
    button.addEventListener('click', () => sendMessage(button.dataset.adminAiPrompt || button.textContent));
  });

  window.addEventListener('resize', () => {
    const rect = bubble.getBoundingClientRect();
    setBubblePosition(rect.left, rect.top, false);
    positionPanel();
  });

  restoreBubblePosition();
})();
