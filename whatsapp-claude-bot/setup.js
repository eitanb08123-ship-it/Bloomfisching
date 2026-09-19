import { startSetupServer } from './setup-server.js';

console.log('Opening the local setup UI...');

startSetupServer({
  onComplete: () => {
    console.log('Saved. Run "npm start" to launch the bot.\n');
    process.exit(0);
  },
});
