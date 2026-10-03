const $ = (id) => document.getElementById(id);
let busy = false;
async function api(path, data) {
  const response = await fetch(path, {
    method: data === undefined ? 'GET' : 'POST',
    headers: data === undefined ? {} : {'Content-Type': 'application/json'},
    body: data === undefined ? undefined : JSON.stringify(data),
    signal: AbortSignal.timeout(900000)
  });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'Không thể kết nối server.');
  return value;
}
function addMessage(text, role) {
  const article = document.createElement('article'); article.className = 'message ' + role;
  const sender = document.createElement('div'); sender.className = 'sender';
  sender.textContent = role === 'user' ? 'BẠN' : 'TRỢ LÝ CAMPUSPULSE';
  const p = document.createElement('p'); p.textContent = text;
  article.append(sender, p); $('messages').append(article);
  article.scrollIntoView({block: 'nearest'}); return article;
}
async function refreshStatus() {
  try {
    const s = await api('/internal/admin/status');
    $('status').textContent = `${s.report_count} phản ánh ACTIVE · ${s.retrieval_mode === 'semantic' ? 'Embedding' : 'Từ khóa'}\n${s.understanding_mode === 'llm' ? 'Hiểu câu hỏi: LLM · ' + s.chat_model : 'Hiểu câu hỏi: quy tắc'}\n${s.ai_required ? 'Bắt buộc AI · Báo lỗi nếu mất kết nối' : 'Cho phép fallback khi AI lỗi'}\nĐồng bộ: ${new Date(s.synced_at).toLocaleString('vi-VN')}${s.warning ? '\n' + s.warning : ''}`;
  } catch (error) { $('status').textContent = error.message; }
}
function setBusy(value) {
  busy = value; $('send').disabled = value; $('sync').disabled = value;
  document.querySelectorAll('#samples button').forEach(b => b.disabled = value);
}
$('chat-form').addEventListener('submit', async (event) => {
  event.preventDefault(); const question = $('question').value.trim();
  if (!question || busy) return;
  setBusy(true); addMessage(question, 'user'); $('question').value = '';
  const pending = addMessage('Đang tìm dữ liệu…', 'bot');
  try {
    const r = await api('/internal/admin/chat', {question});
    pending.querySelector('p').textContent = r.answer;
    const meta = document.createElement('div'); meta.className = 'meta';
    const modes = {llm:'AI tạo câu trả lời', template:'Trích xuất theo mẫu', deterministic:'Thống kê bằng code'};
    meta.textContent = `Hiểu câu hỏi: ${r.understanding_mode} · ${modes[r.generation_mode]} · ${r.retrieval_mode} · Dữ liệu ${new Date(r.synced_at).toLocaleString('vi-VN')}`;
    pending.append(meta);
    for (const warning of r.warnings) {
      const p = document.createElement('p'); p.className='warning'; p.textContent=warning; pending.append(p);
    }
    if (r.sources.length) {
      const details = document.createElement('details'); const summary = document.createElement('summary');
      summary.textContent = `Xem bằng chứng (${r.sources.length} phản ánh)`; details.append(summary);
      for (const source of r.sources) {
        const item = document.createElement('div'); item.className = 'evidence';
        item.textContent = `[PA${source.report_id}] ${source.building} · ${source.category}\n${source.raw_text}\nSự cố: ${source.incident_id ?? 'chưa liên kết'} · ${source.incident_status ?? 'chưa rõ'}\nGửi lúc: ${new Date(source.created_at).toLocaleString('vi-VN')}`;
        details.append(item);
      }
      pending.append(details);
    }
  } catch (error) {
    pending.querySelector('p').textContent = `Lỗi: ${error.message} Bạn có thể gửi lại câu hỏi.`;
    $('question').value = question;
  } finally { setBusy(false); $('question').focus(); }
});
$('question').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); $('chat-form').requestSubmit(); }
});
document.querySelectorAll('#samples button').forEach(button => button.addEventListener('click', () => {
  $('question').value = button.textContent; $('chat-form').requestSubmit();
}));
$('sync').addEventListener('click', async () => {
  if (busy) return; setBusy(true);
  try { await api('/internal/admin/sync', {}); await refreshStatus(); addMessage('Đã đồng bộ dữ liệu. Câu hỏi tiếp theo sẽ dùng bản mới.', 'bot'); }
  catch(error) { addMessage(error.message, 'bot'); }
  finally { setBusy(false); }
});
refreshStatus();
