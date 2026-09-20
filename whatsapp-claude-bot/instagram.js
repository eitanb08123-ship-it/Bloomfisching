import http from 'node:http';
import crypto from 'node:crypto';
import { config } from './config.js';
import { log, logError, formatError } from './log.js';
import { store, scheduleReply } from './reply-engine.js';

const MAX_BODY_BYTES = 512 * 1024;
const IG_ID_PREFIX = 'ig:';

function graphApiUrl(pathSuffix) {
  return `https://graph.facebook.com/${config.igGraphApiVersion}${pathSuffix}?access_token=${encodeURIComponent(config.igPageAccessToken)}`;
}

async function sendGraphApiMessage(igsid, body) {
  const res = await fetch(graphApiUrl('/me/messages'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recipient: { id: igsid }, ...body }),
  });
  if (!res.ok) {
    const errText = await res.text().catch(() => '');
    throw new Error(`Instagram Graph API request failed: ${res.status} ${errText}`);
  }
}

// How this platform actually sends things, for the shared reply engine.
const instagramAdapter = {
  async sendMessage(contactId, text) {
    const igsid = contactId.slice(IG_ID_PREFIX.length);
    await sendGraphApiMessage(igsid, { message: { text } });
  },
  async sendTyping(contactId) {
    const igsid = contactId.slice(IG_ID_PREFIX.length);
    await sendGraphApiMessage(igsid, { sender_action: 'typing_on' });
  },
};

function verifySignature(rawBody, signatureHeader) {
  if (!signatureHeader || !signatureHeader.startsWith('sha256=')) return false;
  const expected = crypto.createHmac('sha256', config.igAppSecret).update(rawBody).digest('hex');
  const provided = signatureHeader.slice('sha256='.length);

  let expectedBuf;
  let providedBuf;
  try {
    expectedBuf = Buffer.from(expected, 'hex');
    providedBuf = Buffer.from(provided, 'hex');
  } catch {
    return false;
  }
  if (expectedBuf.length !== providedBuf.length) return false;
  return crypto.timingSafeEqual(expectedBuf, providedBuf);
}

function readRawBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY_BYTES) {
        reject(new Error('Webhook body too large'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

// One entry in payload.entry[].messaging[]. Delivery/read receipts,
// postbacks, and attachment-only messages (no .message or no .text) are
// intentionally skipped.
function handleMessagingEvent(event) {
  if (!event.message) return;

  if (event.message.is_echo) {
    // A message sent via the Page — either this bot's own reply, or a human
    // manager replying through the Instagram app. Mirrors WhatsApp's
    // fromMe handling: only used for the owner-level global /pauseall and
    // /resumeall commands, never triggers a Gemini reply.
    const body = event.message.text?.trim().toLowerCase();
    if (body === '/pauseall') {
      store.setGlobalPaused(true);
      log('Global auto-reply PAUSED (owner command via Instagram).');
    } else if (body === '/resumeall') {
      store.setGlobalPaused(false);
      log('Global auto-reply RESUMED (owner command via Instagram).');
    }
    return;
  }

  const text = event.message.text;
  const senderId = event.sender?.id;
  if (!text || !senderId) return;

  const contactId = `${IG_ID_PREFIX}${senderId}`;
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

export function startInstagramServer() {
  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, `http://${req.headers.host}`);

      if (req.method === 'GET' && url.pathname === '/webhook') {
        const mode = url.searchParams.get('hub.mode');
        const token = url.searchParams.get('hub.verify_token');
        const challenge = url.searchParams.get('hub.challenge');

        if (mode === 'subscribe' && token === config.igVerifyToken) {
          log('Instagram webhook verified by Meta.');
          res.writeHead(200, { 'Content-Type': 'text/plain' });
          res.end(challenge || '');
        } else {
          logError('Instagram webhook verification failed (mode/token mismatch).');
          res.writeHead(403);
          res.end();
        }
        return;
      }

      if (req.method === 'POST' && url.pathname === '/webhook') {
        const rawBody = await readRawBody(req);

        if (!verifySignature(rawBody, req.headers['x-hub-signature-256'])) {
          logError('Instagram webhook signature verification failed — ignoring request.');
          res.writeHead(401);
          res.end();
          return;
        }

        // Meta expects a fast ack; do the actual work after responding.
        res.writeHead(200, { 'Content-Type': 'text/plain' });
        res.end('EVENT_RECEIVED');

        let payload;
        try {
          payload = JSON.parse(rawBody.toString('utf8'));
        } catch (err) {
          logError('Failed to parse Instagram webhook payload:', formatError(err));
          return;
        }

        for (const entry of payload.entry || []) {
          for (const event of entry.messaging || []) {
            try {
              handleMessagingEvent(event);
            } catch (err) {
              logError('Error handling Instagram messaging event:', formatError(err));
            }
          }
        }
        return;
      }

      res.writeHead(404);
      res.end();
    } catch (err) {
      logError('Instagram webhook request error:', formatError(err));
      try {
        res.writeHead(500);
        res.end();
      } catch {
        // response may already have been sent
      }
    }
  });

  // localhost-only: a local tunnel tool (e.g. ngrok) connects to
  // localhost on this machine and exposes it publicly itself — this
  // process never needs to accept connections from other devices directly.
  server.listen(config.igWebhookPort, '127.0.0.1', () => {
    log(`Instagram webhook server listening on http://localhost:${config.igWebhookPort}/webhook`);
    log(
      'Expose it publicly (e.g. with ngrok) and register the resulting HTTPS URL + /webhook in your Meta App.',
    );
  });

  server.on('error', (err) => {
    logError('Instagram webhook server error:', formatError(err));
  });

  return server;
}
