import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ENV_PATH = path.join(__dirname, '.env');
const ENV_EXAMPLE_PATH = path.join(__dirname, '.env.example');
const DEFAULT_PORT = Number(process.env.SETUP_UI_PORT) || 3000;
const MAX_BODY_BYTES = 10 * 1024;

// Add more entries here if the bot ever needs another required value. Each
// field is written to (and read from) the local .env file only — nothing is
// ever sent back to the browser or logged.
const FIELDS = [
  {
    key: 'GEMINI_API_KEY',
    label: 'Gemini API key',
    required: true,
    placeholder: 'Paste the key from aistudio.google.com/apikey',
    help: 'From aistudio.google.com/apikey — click "Copy key" on the API key details dialog and paste it here.',
    // Google has shipped more than one key format for Gemini API keys
    // (classic "AIza..." keys and newer ones like "AQ...."), so this only
    // does a loose sanity check rather than asserting a specific prefix.
    validate: (value) => /^[A-Za-z0-9._-]{20,}$/.test(value.trim()),
    invalidMessage:
      'That doesn\'t look like a valid API key — check you copied the whole thing with no extra ' +
      'spaces or characters (use the "Copy key" button on aistudio.google.com/apikey rather than ' +
      'selecting the text by hand).',
  },
  {
    key: 'IG_PAGE_ACCESS_TOKEN',
    label: 'Instagram Page access token (optional)',
    required: false,
    placeholder: 'Leave blank to skip Instagram',
    help:
      'From your Meta App — the Page access token for the Facebook Page linked to your Instagram ' +
      'account. Only needed if you want Instagram DMs answered too; see the README for the full setup.',
    validate: (value) => /^[A-Za-z0-9._-]{20,}$/.test(value.trim()),
    invalidMessage: 'That doesn\'t look like a valid access token — check you copied the whole thing.',
  },
  {
    key: 'IG_APP_SECRET',
    label: 'Meta App secret (optional)',
    required: false,
    placeholder: 'Leave blank to skip Instagram',
    help: 'From your Meta App\'s Settings > Basic page — used to verify that webhook requests really come from Meta.',
    validate: (value) => /^[A-Za-z0-9]{20,}$/.test(value.trim()),
    invalidMessage: 'That doesn\'t look like a valid app secret — check you copied the whole thing.',
  },
  {
    key: 'IG_VERIFY_TOKEN',
    label: 'Instagram webhook verify token (optional)',
    required: false,
    placeholder: 'Any string you make up, e.g. a random password',
    help:
      'A password you invent yourself and enter in both places: here, and in the Meta App\'s webhook ' +
      'setup screen. It just has to match in both places.',
    validate: (value) => value.trim().length >= 6,
    invalidMessage: 'Use at least 6 characters — this can be anything, you\'re choosing it yourself.',
  },
];

function readEnvFileRaw() {
  try {
    return fs.readFileSync(ENV_PATH, 'utf8');
  } catch (err) {
    if (err.code === 'ENOENT') return null;
    throw err;
  }
}

function parseEnvText(text) {
  const values = {};
  if (!text) return values;
  for (const line of text.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq === -1) continue;
    values[trimmed.slice(0, eq).trim()] = trimmed.slice(eq + 1).trim();
  }
  return values;
}

function currentValues() {
  return parseEnvText(readEnvFileRaw() || '');
}

function hasValidValue(field, values) {
  const value = values[field.key] || '';
  if (!value) return false;
  return field.validate ? field.validate(value) : true;
}

export function isSetupComplete() {
  const values = currentValues();
  return FIELDS.filter((f) => f.required).every((f) => hasValidValue(f, values));
}

function baseTemplateText() {
  const existing = readEnvFileRaw();
  if (existing !== null) return existing;
  try {
    return fs.readFileSync(ENV_EXAMPLE_PATH, 'utf8');
  } catch {
    return '';
  }
}

// Merges `updates` into the .env file: replaces the value on a matching
// uncommented `KEY=...` line if one exists, otherwise appends a new line.
// Creates .env from .env.example as a starting point if it doesn't exist yet.
function writeEnvValues(updates) {
  const baseText = baseTemplateText();
  const lines = baseText.length ? baseText.split('\n') : [];
  const handled = new Set();

  const updatedLines = lines.map((line) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) return line;
    const eq = trimmed.indexOf('=');
    if (eq === -1) return line;
    const key = trimmed.slice(0, eq).trim();
    if (!Object.prototype.hasOwnProperty.call(updates, key)) return line;
    handled.add(key);
    return `${key}=${updates[key]}`;
  });

  const appended = Object.entries(updates)
    .filter(([key]) => !handled.has(key))
    .map(([key, value]) => `${key}=${value}`);

  const finalText = `${[...updatedLines, ...appended].join('\n').replace(/\n+$/, '')}\n`;
  fs.writeFileSync(ENV_PATH, finalText, { mode: 0o600 });
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function renderPage({ errors = [], saved = false } = {}) {
  const values = currentValues();

  const fieldsHtml = FIELDS.map((field) => {
    const placeholder = hasValidValue(field, values)
      ? '•••••••••••••••• (already set — leave blank to keep it)'
      : field.placeholder || '';
    return `
      <label class="field">
        <span class="field-label">${escapeHtml(field.label)}${
          field.required ? ' <span class="req">*</span>' : ''
        }</span>
        <input type="text" name="${escapeHtml(field.key)}" placeholder="${escapeHtml(placeholder)}" autocomplete="off" spellcheck="false" />
        ${field.help ? `<span class="field-help">${escapeHtml(field.help)}</span>` : ''}
      </label>`;
  }).join('\n');

  const errorsHtml = errors.length
    ? `<div class="banner banner-error">${errors.map((e) => `<p>${escapeHtml(e)}</p>`).join('')}</div>`
    : '';

  const savedHtml = saved
    ? '<div class="banner banner-success"><p>Saved. Starting the bot now — you can close this tab.</p></div>'
    : '';

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>WhatsApp Gemini Bot — Setup</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #0b141a;
    color: #e9edef;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    padding: 24px;
  }
  .card {
    width: 100%;
    max-width: 440px;
    background: #111b21;
    border: 1px solid #2a3942;
    border-radius: 12px;
    padding: 28px;
  }
  h1 { font-size: 20px; margin: 0 0 4px; }
  .subtitle { color: #8696a0; font-size: 14px; margin: 0 0 20px; }
  .field { display: block; margin-bottom: 18px; }
  .field-label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; }
  .req { color: #f15c6d; }
  input[type="text"] {
    width: 100%;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid #2a3942;
    background: #0b141a;
    color: #e9edef;
    font-size: 14px;
  }
  input[type="text"]:focus { outline: none; border-color: #00a884; }
  .field-help { display: block; font-size: 12px; color: #8696a0; margin-top: 6px; }
  button {
    width: 100%;
    padding: 12px;
    border: none;
    border-radius: 8px;
    background: #00a884;
    color: #05221c;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    margin-top: 6px;
  }
  button:hover { background: #06cf9c; }
  .banner { border-radius: 8px; padding: 12px 14px; margin-bottom: 18px; font-size: 13px; }
  .banner p { margin: 0; }
  .banner-error { background: #3a1f22; border: 1px solid #f15c6d; color: #ffb3bb; }
  .banner-success { background: #0f2e26; border: 1px solid #00a884; color: #6fe6c6; }
</style>
</head>
<body>
  <div class="card">
    <h1>WhatsApp Gemini Bot</h1>
    <p class="subtitle">One-time local setup — values are written only to your local .env file.</p>
    ${errorsHtml}
    ${savedHtml}
    <form method="POST" action="/save">
      ${fieldsHtml}
      <button type="submit">Save</button>
    </form>
  </div>
</body>
</html>`;
}

function sendHtml(res, status, html) {
  res.writeHead(status, {
    'Content-Type': 'text/html; charset=utf-8',
    'Cache-Control': 'no-store',
    'Content-Length': Buffer.byteLength(html),
  });
  res.end(html);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY_BYTES) {
        reject(new Error('Request body too large'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}

// Starts the local-only setup UI. `onComplete` (if given) fires once after a
// successful save, right after the server stops listening.
export function startSetupServer({ port = DEFAULT_PORT, onComplete } = {}) {
  const server = http.createServer(async (req, res) => {
    try {
      if (req.method === 'GET' && req.url === '/') {
        sendHtml(res, 200, renderPage());
        return;
      }

      if (req.method === 'POST' && req.url === '/save') {
        const contentType = req.headers['content-type'] || '';
        if (!contentType.includes('application/x-www-form-urlencoded')) {
          sendHtml(res, 400, renderPage({ errors: ['Unexpected form submission.'] }));
          return;
        }

        const body = await readBody(req);
        const submitted = Object.fromEntries(new URLSearchParams(body));
        const existing = currentValues();

        const errors = [];
        const updates = {};

        for (const field of FIELDS) {
          const raw = (submitted[field.key] || '').trim();
          if (raw === '') {
            if (field.required && !hasValidValue(field, existing)) {
              errors.push(`${field.label} is required.`);
            }
            continue; // blank submission keeps whatever is already saved
          }
          if (field.validate && !field.validate(raw)) {
            errors.push(field.invalidMessage || `${field.label} looks invalid.`);
            continue;
          }
          updates[field.key] = raw;
        }

        if (errors.length) {
          sendHtml(res, 400, renderPage({ errors }));
          return;
        }

        if (Object.keys(updates).length) {
          writeEnvValues(updates);
        }

        sendHtml(res, 200, renderPage({ saved: true }));

        if (onComplete) {
          server.close();
          onComplete();
        }
        return;
      }

      sendHtml(res, 404, renderPage({ errors: ['Not found.'] }));
    } catch (err) {
      console.error(`[setup-ui] request error: ${err.message}`);
      sendHtml(
        res,
        500,
        renderPage({ errors: ['Something went wrong saving your settings. Please try again.'] }),
      );
    }
  });

  server.listen(port, '127.0.0.1', () => {
    console.log(
      `\nSetup required: open http://localhost:${port} in your browser to enter your Gemini API key.\n`,
    );
  });

  server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      console.error(
        `[setup-ui] Port ${port} is already in use. Set SETUP_UI_PORT to a different port and try again.`,
      );
    } else {
      console.error('[setup-ui] server error:', err.message);
    }
  });

  return server;
}
