import pkg from 'whatsapp-web.js';
import qrcode from 'qrcode-terminal';
import { config } from './config.js';
import { log, logError, formatError } from './log.js';
import { store, scheduleReply } from './reply-engine.js';

const { Client, LocalAuth } = pkg;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Group chat IDs end in "@g.us"; individual contacts end in "@c.us" or the
// newer "@lid" format. Checking the ID suffix avoids fetching a full Chat
// object (via msg.getChat() / client.getChatById()) just to read .isGroup —
// that call has been observed to throw inside whatsapp-web.js's internal
// page-evaluate code for some chats, and we don't need the full object here.
function isGroupId(id) {
  return id.endsWith('@g.us');
}

// ---------- WhatsApp client ----------

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: './.wwebjs_auth' }),
  puppeteer: {
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  },
});

// How this platform actually sends things, for the shared reply engine.
// The typing indicator needs a Chat object (client.getChatById), which has
// been observed to throw for some chats — it's wired up as best-effort by
// the reply engine, so a failure here just gets logged and ignored.
const whatsappAdapter = {
  async sendMessage(contactId, text) {
    await client.sendMessage(contactId, text);
  },
  async sendTyping(contactId) {
    const chat = await client.getChatById(contactId);
    await chat.sendStateTyping();
  },
};

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
    logError('Reconnect attempt failed:', formatError(err));
  }
});

// Incoming messages: generate a Gemini reply, plus the per-contact
// /pause and /resume commands.
client.on('message', async (msg) => {
  try {
    if (msg.from === 'status@broadcast') return;
    if (msg.type !== 'chat') return; // skip media/stickers/etc. for now
    if (isGroupId(msg.from) && !config.respondToGroups) return;

    const contactId = msg.from;
    const body = msg.body.trim();
    if (!body) return;

    const lower = body.toLowerCase();
    if (lower === '/pause') {
      store.setContactPaused(contactId, true);
      await msg.reply('Auto-reply paused for this chat. Send /resume to turn it back on.');
      return;
    }
    if (lower === '/resume') {
      store.setContactPaused(contactId, false);
      await msg.reply('Auto-reply resumed for this chat.');
      return;
    }

    store.pushHistory(contactId, 'user', body);
    scheduleReply(contactId, whatsappAdapter);
  } catch (err) {
    logError('Error handling incoming message:', formatError(err));
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
    logError('Error handling self-sent command:', formatError(err));
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
