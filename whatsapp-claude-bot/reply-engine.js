import fs from 'node:fs';
import path from 'node:path';
import { GoogleGenAI, ApiError } from '@google/genai';
import { config } from './config.js';
import { log, logError, formatError } from './log.js';

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ---------- Persistent store: per-contact history + pause state ----------
// Shared across every platform (WhatsApp, Instagram, ...). Contact IDs are
// namespaced per platform by the caller (e.g. "ig:<id>") so they can never
// collide. Kept as a small JSON file so history survives restarts. Writes
// are debounced and go through a temp-file + rename to avoid corrupting the
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
        logError(`Failed to load ${this.filePath}, starting with empty state:`, formatError(err));
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
      logError('Failed to save state:', formatError(err));
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
    // The Gemini API requires the message list to start with a "user" turn.
    while (contact.history.length && contact.history[0].role !== 'user') {
      contact.history.shift();
    }
    this._scheduleSave();
  }

  getHistory(id) {
    return this._contact(id).history.map(({ role, content }) => ({ role, content }));
  }
}

export const store = new Store(config.dataFile, config.maxHistoryMessages);

// ---------- Gemini API ----------

const ai = new GoogleGenAI({ apiKey: config.geminiApiKey });

async function callGeminiWithRetry(params, attempt = 1) {
  try {
    return await ai.models.generateContent(params);
  } catch (err) {
    const retryable =
      err instanceof ApiError && typeof err.status === 'number'
        ? err.status === 429 || err.status >= 500
        : true; // network-level errors that aren't a structured ApiError are treated as transient

    if (retryable && attempt <= config.maxRetries) {
      const delay = config.retryBaseDelayMs * 2 ** (attempt - 1);
      logError(
        `Gemini API error (attempt ${attempt}/${config.maxRetries}), retrying in ${delay}ms:`,
        formatError(err),
      );
      await sleep(delay);
      return callGeminiWithRetry(params, attempt + 1);
    }
    throw err;
  }
}

// Cap how many Gemini calls can be in flight at once (across every platform)
// so a burst of messages doesn't hammer the API all at the same time.
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

  const contents = history.map(({ role, content }) => ({
    role,
    parts: [{ text: content }],
  }));

  const response = await withConcurrencyLimit(() =>
    callGeminiWithRetry({
      model: config.model,
      contents,
      config: {
        systemInstruction: config.systemPrompt,
        maxOutputTokens: config.maxReplyTokens,
      },
    }),
  );

  const reply = response.text?.trim();
  if (!reply) return null;

  store.pushHistory(contactId, 'model', reply);
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

// ---------- Debounce bursts of messages per contact, then reply ----------
// Platform-agnostic: each caller (WhatsApp, Instagram, ...) pushes the
// incoming text into `store` itself, then calls scheduleReply with a small
// adapter describing how to actually send on that platform.
//
// adapter: {
//   sendMessage(contactId, text): Promise<void>  (required)
//   sendTyping(contactId): Promise<void>          (optional, best-effort)
// }

const debounceTimers = new Map();

export function scheduleReply(contactId, adapter) {
  clearTimeout(debounceTimers.get(contactId));
  const timer = setTimeout(() => {
    debounceTimers.delete(contactId);
    processReply(contactId, adapter).catch((err) =>
      logError(`Unhandled error replying to ${contactId}:`, formatError(err)),
    );
  }, config.debounceMs);
  debounceTimers.set(contactId, timer);
}

async function processReply(contactId, adapter) {
  if (store.isPaused(contactId)) return;

  let reply;
  try {
    reply = await generateReply(contactId);
  } catch (err) {
    logError(`Gemini API call failed for ${contactId}:`, formatError(err));
    if (config.sendFailureMessage) {
      try {
        await adapter.sendMessage(contactId, config.failureMessage);
      } catch (sendErr) {
        logError(`Failed to send fallback message to ${contactId}:`, formatError(sendErr));
      }
    }
    return;
  }

  if (!reply) return;

  if (adapter.sendTyping) {
    try {
      await adapter.sendTyping(contactId);
    } catch (err) {
      logError(`Could not show typing indicator for ${contactId} (continuing anyway):`, formatError(err));
    }
  }

  await sleep(typingDelayForText(reply));

  try {
    await adapter.sendMessage(contactId, reply);
    log(`Replied to ${contactId}`);
  } catch (err) {
    logError(`Failed to send message to ${contactId}:`, formatError(err));
  }
}
