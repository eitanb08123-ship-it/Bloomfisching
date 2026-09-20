import { isSetupComplete, startSetupServer } from './setup-server.js';
import { log, logError } from './log.js';

// instagram-private-api's HTTP stack (the legacy `request` package) can emit
// a raw, listener-less socket 'error' event on connection failures — Node
// treats that as fatal and kills the whole process by default, which would
// take WhatsApp down too over what's really just an Instagram network hiccup
// (and Instagram, given the unofficial login this bot uses for it, is the
// platform most likely to see connection resets from rate-limiting/flagging).
// Log and keep running rather than let a third-party library's stray error
// end the whole bot.
process.on('uncaughtException', (err) => {
  logError('Uncaught exception (continuing):', err);
});

async function bootstrap() {
  if (!isSetupComplete()) {
    log('No valid Gemini API key found — starting the local setup UI...');
    await new Promise((resolve) => {
      startSetupServer({ onComplete: resolve });
    });
    log('Setup complete. Starting the bot...');
  }

  // Imported dynamically so config.js (which reads .env via dotenv) only
  // loads after the setup UI above has had a chance to write it.
  const { config } = await import('./config.js');
  const { runBot } = await import('./bot.js');

  if (config.instagramEnabled) {
    const { startInstagramService } = await import('./instagram.js');
    // Runs concurrently with WhatsApp rather than blocking it — Instagram
    // login can involve an interactive 2FA prompt, and a failure here
    // (bad password, security checkpoint, etc.) shouldn't stop WhatsApp.
    startInstagramService().catch((err) => {
      logError('Instagram failed to start:', err);
    });
  } else {
    log('Instagram not configured (IG_USERNAME / IG_PASSWORD) — skipping. Run "npm run setup" to add it.');
  }

  await runBot();
}

bootstrap().catch((err) => {
  console.error('Fatal error during startup:', err);
  process.exit(1);
});
