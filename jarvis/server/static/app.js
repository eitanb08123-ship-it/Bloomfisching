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

  const activityList = document.getElementById('activity-list');

  let ws;
  const MAX_ACTIVITY_ENTRIES = 20;

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
      case 'activity':
        addActivity(data.tool, data.args, data.result);
        break;
      case 'error':
        addMessage('system', `⚠ ${data.message}`);
        break;
      default:
        console.warn('Unknown message', data);
    }
  }

  function addActivity(tool, args, result) {
    const empty = activityList.querySelector('.activity-empty');
    if (empty) empty.remove();

    const el = document.createElement('li');
    const toolSpan = document.createElement('span');
    toolSpan.className = 'activity-tool';
    toolSpan.textContent = tool;

    const time = new Date().toLocaleTimeString();
    // Built with textContent/appendChild (not innerHTML): args/result can
    // contain arbitrary text from files, notes, or model output, and must
    // never be interpreted as markup in this page.
    el.appendChild(toolSpan);
    el.appendChild(document.createTextNode(`(${JSON.stringify(args)}) → ${result} (${time})`));
    activityList.prepend(el);

    while (activityList.children.length > MAX_ACTIVITY_ENTRIES) {
      activityList.removeChild(activityList.lastChild);
    }
  }

  function setBar(barEl, valEl, percent) {
    barEl.style.width = `${percent}%`;
    valEl.textContent = `${Math.round(percent)}%`;
  }

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
