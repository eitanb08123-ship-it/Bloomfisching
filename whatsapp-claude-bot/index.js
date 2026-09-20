import { isSetupComplete, startSetupServer } from './setup-server.js';

function log(...args) {
  console.log(`[${new Date().toISOString()}]`, ...args);
}

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
    const { startInstagramServer } = await import('./instagram.js');
    startInstagramServer();
  } else {
    log(
      'Instagram not configured (IG_PAGE_ACCESS_TOKEN / IG_APP_SECRET / IG_VERIFY_TOKEN) — skipping. ' +
        'Run "npm run setup" to add it.',
    );
  }

  await runBot();
}

bootstrap().catch((err) => {
  console.error('Fatal error during startup:', err);
  process.exit(1);
});
