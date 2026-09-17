(function () {
  const chatLog = document.getElementById('chat-log');
  const chatForm = document.getElementById('chat-form');
  const chatText = document.getElementById('chat-text');
  const micBtn = document.getElementById('mic-btn');
  const connDot = document.getElementById('conn-indicator');
  const connText = document.getElementById('conn-text');
  const modeBadge = document.getElementById('mode-badge');

  const cpuBar = document.getElementById('cpu-bar');
  const memBar = document.getElementById('mem-bar');
  const diskBar = document.getElementById('disk-bar');
  const cpuVal = document.getElementById('cpu-val');
  const memVal = document.getElementById('mem-val');
  const diskVal = document.getElementById('disk-val');

  const confirmBackdrop = document.getElementById('confirm-backdrop');
  const confirmTier = document.getElementById('confirm-tier');
  const confirmTitle = document.getElementById('confirm-title');
  const confirmDesc = document.getElementById('confirm-desc');
  const confirmArgs = document.getElementById('confirm-args');
  const confirmApprove = document.getElementById('confirm-approve');
  const confirmDeny = document.getElementById('confirm-deny');

  let ws;
  let currentConfirmRequestId = null;

  const BUBBLE_LIFETIME_MS = 6000;
  const BUBBLE_FADE_MS = 500;

  function addMessage(role, text) {
    const el = document.createElement('div');
    el.className = `msg ${role}`;
    el.textContent = text;
    chatLog.appendChild(el);
    chatLog.scrollTop = chatLog.scrollHeight;

    setTimeout(() => el.classList.add('fade-out'), BUBBLE_LIFETIME_MS - BUBBLE_FADE_MS);
    setTimeout(() => el.remove(), BUBBLE_LIFETIME_MS);
  }

  function setConnected(connected) {
    connDot.classList.toggle('connected', connected);
    connText.textContent = connected ? 'Online' : 'Disconnected';
  }

  function connect() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/ws`);

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      setTimeout(connect, 2000);
    };
    ws.onmessage = (event) => handleServerMessage(JSON.parse(event.data));
  }

  function handleServerMessage(data) {
    switch (data.type) {
      case 'mode':
        modeBadge.textContent = `MODE: ${data.mode}`;
        break;
      case 'user_message':
        addMessage('user', data.text);
        break;
      case 'assistant_message':
        addMessage('assistant', data.text);
        break;
      case 'voice_transcript':
        addMessage('system', `🎙 heard: "${data.text}"`);
        break;
      case 'thinking':
        window.JarvisSphere.setActivity(data.value ? 0.9 : 0.15);
        break;
      case 'listening':
        micBtn.classList.toggle('listening', data.value);
        break;
      case 'status_update':
        setBar(cpuBar, cpuVal, data.cpu);
        setBar(memBar, memVal, data.mem);
        setBar(diskBar, diskVal, data.disk);
        break;
      case 'confirmation_request':
        showConfirmation(data);
        break;
      case 'error':
        addMessage('system', `⚠ ${data.message}`);
        break;
      default:
        console.warn('Unknown message', data);
    }
  }

  function setBar(barEl, valEl, percent) {
    barEl.style.width = `${percent}%`;
    valEl.textContent = `${Math.round(percent)}%`;
  }

  function showConfirmation(data) {
    currentConfirmRequestId = data.request_id;
    confirmTier.textContent = data.tier.toUpperCase() + (data.stage === 2 ? ' · FINAL CONFIRMATION' : '');
    confirmTier.className = `modal-tier ${data.tier}`;
    confirmTitle.textContent = `Run: ${data.tool}`;
    confirmDesc.textContent = data.description;
    confirmArgs.textContent = JSON.stringify(data.args, null, 2);
    confirmBackdrop.classList.add('open');
  }

  function respondConfirmation(approved) {
    if (!currentConfirmRequestId) return;
    ws.send(JSON.stringify({ type: 'confirm_response', request_id: currentConfirmRequestId, approved }));
    currentConfirmRequestId = null;
    confirmBackdrop.classList.remove('open');
  }

  confirmApprove.addEventListener('click', () => respondConfirmation(true));
  confirmDeny.addEventListener('click', () => respondConfirmation(false));

  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = chatText.value.trim();
    if (!text || ws.readyState !== WebSocket.OPEN) return;
    addMessage('user', text);
    ws.send(JSON.stringify({ type: 'user_message', text }));
    chatText.value = '';
  });

  micBtn.addEventListener('click', () => {
    if (ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: 'voice_listen' }));
  });

  connect();
})();
