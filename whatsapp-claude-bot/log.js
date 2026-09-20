export function log(...args) {
  console.log(`[${new Date().toISOString()}]`, ...args);
}

export function logError(...args) {
  console.error(`[${new Date().toISOString()}]`, ...args);
}

// A caught error's .message alone can be uselessly short (or even a single
// character, for some whatsapp-web.js internal failures) — the stack trace
// is what actually pinpoints where it came from.
export function formatError(err) {
  if (err instanceof Error) return err.stack || err.message || String(err);
  return typeof err === 'object' ? JSON.stringify(err) : String(err);
}
