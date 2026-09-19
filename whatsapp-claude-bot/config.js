import 'dotenv/config';

const DEFAULT_SYSTEM_PROMPT = `You are Aria, a warm, sharp, and genuinely helpful person chatting with someone over WhatsApp.

How you talk:
- Write like a real person texting a friend: casual, concise, natural. Usually 1-4 short sentences unless the question genuinely needs more.
- No corporate customer-service tone, no "How can I assist you today?" boilerplate.
- Use the recent conversation history you're given to stay consistent and remember what was already said in this chat.

How you answer:
- When asked a factual, mathematical, or logical question, actually work it out and give the correct, specific answer — don't deflect, don't give a generic non-answer, and don't just repeat the question back.
- For math, compute it correctly; show brief work for multi-step problems, just give the answer for simple arithmetic.
- If you're genuinely unsure or the question is ambiguous, say so plainly and ask a clarifying question instead of guessing.
- Stay on topic and actually engage with what the person just said — don't give a generic greeting when they've asked something specific.

Formatting:
- Plain text only — no markdown headers, bullet lists, or tables, since this is a text message thread.`;

function int(name, fallback) {
  const raw = process.env[name];
  if (raw === undefined || raw === '') return fallback;
  const parsed = parseInt(raw, 10);
  return Number.isNaN(parsed) ? fallback : parsed;
}

function bool(name, fallback) {
  const raw = process.env[name];
  if (raw === undefined || raw === '') return fallback;
  return raw.toLowerCase() === 'true';
}

if (!process.env.ANTHROPIC_API_KEY) {
  console.warn('[config] ANTHROPIC_API_KEY is not set. Set it in your environment or a .env file.');
}

export const config = {
  anthropicApiKey: process.env.ANTHROPIC_API_KEY,
  model: process.env.CLAUDE_MODEL || 'claude-opus-5',
  maxReplyTokens: int('MAX_REPLY_TOKENS', 1024),

  maxHistoryMessages: int('MAX_HISTORY_MESSAGES', 15),
  dataFile: process.env.DATA_FILE || './data/state.json',

  respondToGroups: bool('RESPOND_TO_GROUPS', false),

  debounceMs: int('DEBOUNCE_MS', 1500),
  minTypingDelayMs: int('MIN_TYPING_DELAY_MS', 1200),
  maxTypingDelayMs: int('MAX_TYPING_DELAY_MS', 6000),
  msPerCharTyping: int('MS_PER_CHAR_TYPING', 40),

  maxConcurrentCalls: int('MAX_CONCURRENT_CALLS', 3),
  maxRetries: int('MAX_RETRIES', 3),
  retryBaseDelayMs: int('RETRY_BASE_DELAY_MS', 1000),

  reconnectBaseDelayMs: int('RECONNECT_BASE_DELAY_MS', 3000),
  maxReconnectDelayMs: int('MAX_RECONNECT_DELAY_MS', 60000),

  sendFailureMessage: bool('SEND_FAILURE_MESSAGE', true),
  failureMessage:
    process.env.FAILURE_MESSAGE ||
    "Sorry, I'm having trouble replying right now — please try again in a moment.",

  systemPrompt: process.env.SYSTEM_PROMPT || DEFAULT_SYSTEM_PROMPT,
};
