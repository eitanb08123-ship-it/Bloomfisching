import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import {
  IgApiClient,
  IgLoginTwoFactorRequiredError,
  IgCheckpointError,
  IgLoginRequiredError,
  IgUserHasLoggedOutError,
} from 'instagram-private-api';
import { config } from './config.js';
import { log, logError, formatError } from './log.js';
import { store, scheduleReply } from './reply-engine.js';

const IG_ID_PREFIX = 'ig:';

const ig = new IgApiClient();
let ownUserId = null;

// How this platform actually sends things, for the shared reply engine.
// No typing-indicator equivalent is exposed by this library, so the
// adapter only implements sendMessage — the reply engine treats that as
// optional and just skips it.
const instagramAdapter = {
  async sendMessage(contactId, text) {
    const userId = contactId.slice(IG_ID_PREFIX.length);
    // skipLinkCheck avoids a regex-based URL scan this library recommends
    // installing a native `re2` dependency for; our replies are plain text.
    await ig.entity.directThread([userId]).broadcastText(text, true);
  },
};

function promptStdin(question) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(answer.trim());
    });
  });
}

async function saveSession() {
  try {
    fs.mkdirSync(path.dirname(config.igSessionFile), { recursive: true });
    const serialized = await ig.state.serialize();
    fs.writeFileSync(config.igSessionFile, JSON.stringify(serialized), { mode: 0o600 });
  } catch (err) {
    logError('Instagram: failed to save session:', formatError(err));
  }
}

async function tryRestoreSession() {
  let saved;
  try {
    saved = fs.readFileSync(config.igSessionFile, 'utf8');
  } catch {
    return null;
  }
  try {
    await ig.state.deserialize(JSON.parse(saved));
    const me = await ig.account.currentUser();
    return String(me.pk);
  } catch (err) {
    logError('Instagram: saved session is no longer valid, logging in fresh:', formatError(err));
    return null;
  }
}

async function freshLogin() {
  log('Instagram: logging in with username/password...');
  await ig.simulate.preLoginFlow();

  try {
    await ig.account.login(config.igUsername, config.igPassword);
  } catch (err) {
    if (err instanceof IgLoginTwoFactorRequiredError) {
      const info = err.response.body.two_factor_info;
      log(
        `Instagram: two-factor authentication required (check your ${
          info.sms_two_factor_on ? 'SMS' : 'authenticator app'
        }).`,
      );
      const code = await promptStdin('Enter the Instagram 2FA code: ');
      await ig.account.twoFactorLogin({
        username: info.username,
        verificationCode: code,
        twoFactorIdentifier: info.two_factor_identifier,
        trustThisDevice: '1',
      });
    } else if (err instanceof IgCheckpointError) {
      logError(
        'Instagram: this login was flagged for a security checkpoint. Open Instagram (the app or ' +
          'instagram.com) on this account, complete the "confirm it\'s you" prompt there, then restart the bot.',
      );
      throw err;
    } else {
      throw err;
    }
  }

  process.nextTick(() => ig.simulate.postLoginFlow().catch(() => {}));
  await saveSession();
  log('Instagram: logged in.');

  const me = await ig.account.currentUser();
  return String(me.pk);
}

async function loginToInstagram() {
  ig.state.generateDevice(config.igUsername);

  const restoredUserId = await tryRestoreSession();
  if (restoredUserId) {
    ownUserId = restoredUserId;
    log('Instagram: restored saved session.');
    return;
  }

  ownUserId = await freshLogin();
}

// ---------- Tracking which messages we've already handled ----------
// A flat { threadId: latestSeenTimestamp } map, persisted to disk. On the
// bot's very first-ever run (no file yet) the first poll only records a
// baseline for each existing thread without replying, so it doesn't
// suddenly respond to a backlog of old messages. On every later poll —
// including after a restart, using the persisted file — anything newer
// than the stored timestamp is treated as new and answered normally,
// which correctly includes messages that arrived while the bot was down.

let seenTimestamps = new Map();
let isFirstRunEver = true;

function loadSeenTimestamps() {
  try {
    const raw = fs.readFileSync(config.igSeenFile, 'utf8');
    const obj = JSON.parse(raw);
    seenTimestamps = new Map(Object.entries(obj));
    isFirstRunEver = seenTimestamps.size === 0;
  } catch {
    seenTimestamps = new Map();
    isFirstRunEver = true;
  }
}

function saveSeenTimestamps() {
  try {
    fs.mkdirSync(path.dirname(config.igSeenFile), { recursive: true });
    fs.writeFileSync(config.igSeenFile, JSON.stringify(Object.fromEntries(seenTimestamps)));
  } catch (err) {
    logError('Instagram: failed to save seen-message state:', formatError(err));
  }
}

function isNewerThanSeen(item, threadId) {
  const seen = seenTimestamps.get(threadId);
  return !seen || Number(item.timestamp) > Number(seen);
}

function handleOwnCommand(text) {
  const lower = text.trim().toLowerCase();
  if (lower === '/pauseall') {
    store.setGlobalPaused(true);
    log('Global auto-reply PAUSED (owner command via Instagram).');
  } else if (lower === '/resumeall') {
    store.setGlobalPaused(false);
    log('Global auto-reply RESUMED (owner command via Instagram).');
  }
  // Any other text the account itself sent (this bot's own replies, or the
  // owner just chatting manually) is not something we need to act on.
}

function handleContactMessage(userId, text) {
  const contactId = `${IG_ID_PREFIX}${userId}`;
  const lower = text.trim().toLowerCase();

  if (lower === '/pause') {
    store.setContactPaused(contactId, true);
    instagramAdapter
      .sendMessage(contactId, 'Auto-reply paused for this chat. Send /resume to turn it back on.')
      .catch((err) => logError(`Failed to send /pause confirmation to ${contactId}:`, formatError(err)));
    return;
  }
  if (lower === '/resume') {
    store.setContactPaused(contactId, false);
    instagramAdapter
      .sendMessage(contactId, 'Auto-reply resumed for this chat.')
      .catch((err) => logError(`Failed to send /resume confirmation to ${contactId}:`, formatError(err)));
    return;
  }

  store.pushHistory(contactId, 'user', text);
  scheduleReply(contactId, instagramAdapter);
}

async function poll() {
  let threads;
  try {
    threads = await ig.feed.directInbox().items();
  } catch (err) {
    if (err instanceof IgLoginRequiredError || err instanceof IgUserHasLoggedOutError) {
      logError('Instagram: session expired — logging in again...');
      try {
        await freshLogin();
      } catch (loginErr) {
        logError('Instagram: re-login failed:', formatError(loginErr));
      }
      return;
    }
    logError('Instagram: failed to poll inbox:', formatError(err));
    return;
  }

  let changed = false;

  for (const thread of threads) {
    const textItems = (thread.items || []).filter((item) => item.item_type === 'text' && item.text);

    if (isFirstRunEver) {
      // Seed a baseline for this thread from its most recent item, without
      // replying, so we don't respond to a backlog of pre-existing messages.
      const newest = thread.last_permanent_item || textItems[0];
      if (newest) {
        seenTimestamps.set(thread.thread_id, newest.timestamp);
        changed = true;
      }
      continue;
    }

    const newItems = textItems
      .filter((item) => isNewerThanSeen(item, thread.thread_id))
      .sort((a, b) => Number(a.timestamp) - Number(b.timestamp));

    if (newItems.length === 0) continue;

    for (const item of newItems) {
      try {
        if (String(item.user_id) === ownUserId) {
          handleOwnCommand(item.text);
        } else {
          handleContactMessage(item.user_id, item.text);
        }
      } catch (err) {
        logError('Instagram: error handling message:', formatError(err));
      }
    }

    seenTimestamps.set(thread.thread_id, newItems[newItems.length - 1].timestamp);
    changed = true;
  }

  isFirstRunEver = false;
  if (changed) saveSeenTimestamps();
}

export async function startInstagramService() {
  await loginToInstagram();
  loadSeenTimestamps();
  log(`Instagram: polling for new messages every ${config.igPollIntervalMs}ms.`);
  await poll();
  setInterval(() => {
    poll().catch((err) => logError('Instagram: unhandled polling error:', formatError(err)));
  }, config.igPollIntervalMs);
}
