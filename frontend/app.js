const state = { threadId: null, socket: null, files: [], sessionPath: null, running: false, activity: 0 };
const $ = (selector) => document.querySelector(selector);
const messages = $('#messages');
const queryInput = $('#queryInput');
const sendButton = $('#sendButton');
const activityList = $('#activityList');
const connectionState = $('#connectionState');

function newId() {
  return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
function scrollMessages() { messages.scrollTop = messages.scrollHeight; }
function setRunning(value) {
  state.running = value; sendButton.disabled = value;
  sendButton.firstChild.textContent = value ? '研究进行中 ' : '开始研究 ';
}
function addMessage(role, text, isError = false) {
  const article = document.createElement('article');
  article.className = `message ${role}${isError ? ' error-message' : ''}`;
  const avatar = document.createElement('div'); avatar.className = 'avatar'; avatar.textContent = role === 'user' ? '你' : 'D';
  const body = document.createElement('div'); body.className = 'message-body';
  const author = document.createElement('span'); author.className = 'message-author'; author.textContent = role === 'user' ? '你' : 'Deep Search Pro';
  const p = document.createElement('p'); p.textContent = text;
  body.append(author, p); article.append(avatar, body); messages.append(article); scrollMessages();
}
function addActivity(title, detail, type = 'step') {
  if (state.activity === 0) activityList.innerHTML = '';
  state.activity += 1; $('#activityCount').textContent = state.activity;
  const li = document.createElement('li'); li.className = 'activity-item';
  const icon = document.createElement('span'); icon.className = 'activity-icon'; icon.textContent = type === 'error' ? '!' : type === 'done' ? '✓' : '◇';
  const strong = document.createElement('strong'); strong.textContent = title;
  const p = document.createElement('p'); p.textContent = detail || '';
  const time = document.createElement('time'); time.textContent = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit', minute:'2-digit'});
  li.append(icon, strong, p, time); activityList.append(li); li.scrollIntoView({behavior:'smooth', block:'nearest'});
}
function connectSocket(threadId) {
  return new Promise((resolve, reject) => {
    const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
    const socket = new WebSocket(`${scheme}://${location.host}/ws/${threadId}`); state.socket = socket;
    socket.onopen = () => { connectionState.classList.add('live'); connectionState.lastChild.textContent = '实时连接已建立'; resolve(); };
    socket.onerror = reject;
    socket.onclose = () => { connectionState.classList.remove('live'); connectionState.lastChild.textContent = '连接已结束'; };
    socket.onmessage = (event) => handleEvent(JSON.parse(event.data));
  });
}
function handleEvent(payload) {
  if (payload.type === 'pong') return;
  const { event, message, data = {} } = payload;
  if (event === 'session_created') { state.sessionPath = data.path; addActivity('工作区已就绪', '已创建本次任务的独立工作目录'); }
  else if (event === 'assistant_call') addActivity(data.assistant_name || '调用专业助手', data.args?.description || message);
  else if (event === 'tool_start') addActivity(data.tool_name || '执行工具', data.args?.query || message);
  else if (event === 'task_result') { addActivity('任务完成', '结果已汇总并返回', 'done'); addMessage('assistant', data.result || message); setRunning(false); refreshFiles(); }
  else if (event === 'error') { addActivity('执行遇到问题', message, 'error'); addMessage('assistant', message, true); setRunning(false); }
}
async function uploadFiles() {
  if (!state.files.length) return;
  const body = new FormData(); state.files.forEach(file => body.append('files', file)); body.append('thread_id', state.threadId);
  const response = await fetch('/api/upload', {method:'POST', body}); if (!response.ok) throw new Error('文件上传失败');
  addActivity('参考文件已上传', `${state.files.length} 个文件已加入任务`);
}
async function submitTask(event) {
  event.preventDefault(); const query = queryInput.value.trim(); if (!query || state.running) return;
  state.threadId = newId(); $('#sessionLabel').textContent = `会话 ${state.threadId.slice(0, 8)}`; setRunning(true); addMessage('user', query);
  queryInput.value = ''; queryInput.style.height = 'auto';
  try {
    await connectSocket(state.threadId); await uploadFiles();
    const response = await fetch('/api/task', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({query, thread_id:state.threadId})});
    if (!response.ok) throw new Error('任务提交失败');
    addActivity('任务已提交', '主智能体正在分析问题'); state.files = []; renderAttachments();
  } catch (error) { addMessage('assistant', error.message, true); addActivity('无法开始任务', error.message, 'error'); setRunning(false); }
}
async function refreshFiles() {
  if (!state.sessionPath) return;
  try {
    const response = await fetch(`/api/files?path=${encodeURIComponent(state.sessionPath)}`); const result = await response.json(); renderFiles(result.files || []);
  } catch (_) { /* 保留当前文件列表 */ }
}
function renderFiles(files) {
  const list = $('#filesList');
  if (!files.length) { list.innerHTML = '<div class="empty-state file-empty"><span class="file-illustration">⌁</span><strong>暂无成果</strong><p>智能体生成的报告和文档会出现在这里。</p></div>'; return; }
  list.innerHTML = '';
  files.forEach(file => {
    const link = document.createElement('a'); link.className = 'file-card'; link.href = `/api/download?path=${encodeURIComponent(file.path)}`;
    const type = document.createElement('span'); type.className = 'file-type'; type.textContent = file.name.split('.').pop().toUpperCase().slice(0,4);
    const meta = document.createElement('span'); meta.className = 'file-meta'; const name = document.createElement('strong'); name.textContent = file.name;
    const size = document.createElement('span'); size.textContent = `${Math.max(1, Math.round(file.size / 1024))} KB · 点击下载`; meta.append(name,size); link.append(type,meta); list.append(link);
  });
}
function renderAttachments() {
  const bar = $('#attachmentBar'); bar.hidden = !state.files.length; bar.textContent = state.files.length ? `已选择 ${state.files.length} 个文件：${state.files.map(f=>f.name).join('、')}` : '';
}
function resetConversation() {
  if (state.socket) state.socket.close(); location.reload();
}
$('#composer').addEventListener('submit', submitTask);
$('#fileInput').addEventListener('change', (event) => { state.files = [...event.target.files]; renderAttachments(); });
$('#refreshFiles').addEventListener('click', refreshFiles);
$('#newTaskButton').addEventListener('click', resetConversation);
document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => { queryInput.value = button.dataset.prompt; queryInput.focus(); }));
queryInput.addEventListener('input', () => { queryInput.style.height = 'auto'; queryInput.style.height = `${Math.min(queryInput.scrollHeight, 160)}px`; });
queryInput.addEventListener('keydown', (event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); $('#composer').requestSubmit(); } });
