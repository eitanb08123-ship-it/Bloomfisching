import fs from 'node:fs';
import path from 'node:path';
import pkg from 'whatsapp-web.js';
import qrcode from 'qrcode-terminal';
import Anthropic from '@anthropic-ai/sdk';
import { config } from './config.js';

const { Client, LocalAuth } = pkg;

// ---------- Logging ----------

function log(...args) {
  console.log(`[${new Date().toISOString()}]`, ...args);
}

function logError(...args) {
  console.error(`[${new Date().toISOString()}]`, ...args);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ---------- Persistent store: per-contact history + pause state ----------
// Kept as a small JSON file so history survives restarts. Writes are
// debounced and go through a temp-file + rename to avoid corrupting the
// file if the process dies mid-write.

class Store {
  constructor(filePath, maxHistoryMessages) {
    this.filePath = filePath;
    this.maxHistoryMessages = maxHistoryMessages;
    this.data = { global: { paused: false }, contacts: {} };
    this._saveTimer = null;
    this._load();
  }

  _load() {
    try {
      this.data = JSON.parse(fs.readFileSync(this.filePath, 'utf8'));
    } catch (err) {
      if (err.code !== 'ENOENT') {
        logError(`Failed to load ${this.filePath}, starting with empty state:`, err.message);
      }
    }
  }

  _scheduleSave() {
    clearTimeout(this._saveTimer);
    this._saveTimer = setTimeout(() => this.saveNow(), 500);
  }

  saveNow() {
    clearTimeout(this._saveTimer);
    try {
      fs.mkdirSync(path.dirname(this.filePath), { recursive: true });
      const tmpPath = `${this.filePath}.tmp`;
      fs.writeFileSync(tmpPath, JSON.stringify(this.data, null, 2));
      fs.renameSync(tmpPath, this.filePath);
    } catch (err) {
      logError('Failed to save state:', err.message);
    }
  }

  _contact(id) {
    if (!this.data.contacts[id]) {
      this.data.contacts[id] = { paused: false, history: [] };
    }
    return this.data.contacts[id];
  }

  isPaused(id) {
    return this.data.global.paused || this._contact(id).paused;
  }

  isGloballyPaused() {
    return this.data.global.paused;
  }

  setGlobalPaused(paused) {
    this.data.global.paused = paused;
    this._scheduleSave();
  }

  setContactPaused(id, paused) {
    this._contact(id).paused = paused;
    this._scheduleSave();
  }

  pushHistory(id, role, content) {
    const contact = this._contact(id);
    contact.history.push({ role, content });
    if (contact.history.length > this.maxHistoryMessages) {
      contact.history = contact.history.slice(-this.maxHistoryMessages);
    }
    // The Claude API requires the message list to start with a "user" turn.
    while (contact.history.length && contact.history[0].role !== 'user') {
      contact.history.shift();
    }
    this._scheduleSave();
  }

  getHistory(id) {
    return this._contact(id).history.map(({ role, content }) => ({ role, content }));
  }
}

const store = new Store(config.dataFile, config.maxHistoryMessages);

// ---------- Claude API ----------

const anthropic = new Anthropic({ apiKey: config.anthropicApiKey });

async function callClaudeWithRetry(params, attempt = 1) {
  try {
    return await anthropic.messages.create(params);
  } catch (err) {
    const retryable =
      err instanceof Anthropic.RateLimitError ||
      err instanceof Anthropic.APIConnectionError ||
      (err instanceof Anthropic.APIError && typeof err.status === 'number' && err.status >= 500);

    if (retryable && attempt <= config.maxRetries) {
      const delay = config.retryBaseDelayMs * 2 ** (attempt - 1);
      logError(
        `Claude API error (attempt ${attempt}/${config.maxRetries}), retrying in ${delay}ms:`,
        err.message,
      );
      await sleep(delay);
      return callClaudeWithRetry(params, attempt + 1);
    }
    throw err;
  }
}

// Cap how many Claude calls can be in flight at once so a burst of messages
// across many chats doesn't hammer the API all at the same time.
let activeCalls = 0;
const waitQueue = [];

async function withConcurrencyLimit(fn) {
  if (activeCalls >= config.maxConcurrentCalls) {
    await new Promise((resolve) => waitQueue.push(resolve));
  }
  activeCalls++;
  try {
    return await fn();
  } finally {
    activeCalls--;
    const next = waitQueue.shift();
    if (next) next();
  }
}

async function generateReply(contactId) {
  const history = store.getHistory(contactId);
  if (history.length === 0) return null;

  const response = await withConcurrencyLimit(() =>
    callClaudeWithRetry({
      model: config.model,
      max_tokens: config.maxReplyTokens,
      system: config.systemPrompt,
      messages: history,
    }),
  );

  const textBlock = response.content.find((block) => block.type === 'text');
  const reply = textBlock?.text?.trim();
  if (!reply) return null;

  store.pushHistory(contactId, 'assistant', reply);
  return reply;
}

// ---------- Natural-feeling send delay ----------

function randomInt(min, max) {
  return min + Math.floor(Math.random() * (max - min + 1));
}

function typingDelayForText(text) {
  const estimate = text.length * config.msPerCharTyping + randomInt(-300, 300);
  return Math.min(config.maxTypingDelayMs, Math.max(config.minTypingDelayMs, estimate));
}

// ---------- Debounce bursts of messages per chat, then reply ----------

const debounceTimers = new Map();

function scheduleReply(contactId) {
  clearTimeout(debounceTimers.get(contactId));
  const timer = setTimeout(() => {
    debounceTimers.delete(contactId);
    processReply(contactId).catch((err) =>
      logError(`Unhandled error replying to ${contactId}:`, err.message),
    );
  }, config.debounceMs);
  debounceTimers.set(contactId, timer);
}

async function processReply(contactId) {
  if (store.isPaused(contactId)) return;

  let reply;
  try {
    reply = await generateReply(contactId);
  } catch (err) {
    logError(`Claude API call failed for ${contactId}:`, err.message);
    if (config.sendFailureMessage) {
      try {
        const chat = await client.getChatById(contactId);
        await chat.sendMessage(config.failureMessage);
      } catch (sendErr) {
        logError(`Failed to send fallback message to ${contactId}:`, sendErr.message);
      }
    }
    return;
  }

  if (!reply) return;

  try {
    const chat = await client.getChatById(contactId);
    await chat.sendStateTyping().catch(() => {});
    await sleep(typingDelayForText(reply));
    await chat.sendMessage(reply);
    log(`Replied to ${contactId}`);
  } catch (err) {
    logError(`Failed to send WhatsApp message to ${contactId}:`, err.message);
  }
}

// ---------- WhatsApp client ----------

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: './.wwebjs_auth' }),
  puppeteer: {
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  },
});

client.on('qr', (qr) => {
  log('Scan this QR code with WhatsApp (Settings > Linked Devices > Link a Device):');
  qrcode.generate(qr, { small: true });
});

client.on('authenticated', () => {
  log('WhatsApp authenticated.');
});

client.on('auth_failure', (msg) => {
  logError('WhatsApp authentication failed:', msg);
});

let reconnectAttempts = 0;

client.on('ready', () => {
  reconnectAttempts = 0;
  log('WhatsApp client is ready. Listening for messages...');
});

client.on('disconnected', async (reason) => {
  logError('WhatsApp client disconnected:', reason);
  reconnectAttempts++;
  const delay = Math.min(
    config.maxReconnectDelayMs,
    config.reconnectBaseDelayMs * 2 ** (reconnectAttempts - 1),
  );
  log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttempts})...`);
  await sleep(delay);
  try {
    await client.initialize();
  } catch (err) {
    logError('Reconnect attempt failed:', err.message);
  }
});

// Incoming messages: generate a Claude reply, plus the per-contact
// /pause and /resume commands.
client.on('message', async (msg) => {
  try {
    if (msg.from === 'status@broadcast') return;
    if (msg.type !== 'chat') return; // skip media/stickers/etc. for now

    const chat = await msg.getChat();
    if (chat.isGroup && !config.respondToGroups) return;

    const contactId = msg.from;
    const body = msg.body.trim();
    if (!body) return;

    const lower = body.toLowerCase();
    if (lower === '/pause') {
      store.setContactPaused(contactId, true);
      await chat.sendMessage('Auto-reply paused for this chat. Send /resume to turn it back on.');
      return;
    }
    if (lower === '/resume') {
      store.setContactPaused(contactId, false);
      await chat.sendMessage('Auto-reply resumed for this chat.');
      return;
    }

    store.pushHistory(contactId, 'user', body);
    scheduleReply(contactId);
  } catch (err) {
    logError('Error handling incoming message:', err.message);
  }
});

// Outgoing messages (including ones you send yourself from your phone):
// used only for the owner-level global /pauseall and /resumeall commands.
client.on('message_create', async (msg) => {
  try {
    if (!msg.fromMe) return; // incoming messages are handled above
    if (msg.type !== 'chat') return;

    const body = msg.body.trim().toLowerCase();
    if (body === '/pauseall') {
      store.setGlobalPaused(true);
      log('Global auto-reply PAUSED (owner command).');
    } else if (body === '/resumeall') {
      store.setGlobalPaused(false);
      log('Global auto-reply RESUMED (owner command).');
    } else if (body === '/status') {
      log(`Global paused: ${store.isGloballyPaused()}`);
    }
  } catch (err) {
    logError('Error handling self-sent command:', err.message);
  }
});

process.on('SIGINT', async () => {
  log('Shutting down...');
  store.saveNow();
  try {
    await client.destroy();
  } catch {
    // ignore errors during shutdown
  }
  process.exit(0);
});

process.on('unhandledRejection', (reason) => {
  logError('Unhandled promise rejection:', reason);
});

export async function runBot() {
  log('Starting WhatsApp client...');
  await client.initialize();
}
