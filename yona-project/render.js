const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto('file://' + __dirname + '/game.html');
  await p.pdf({ path: __dirname + '/yona-game.pdf', format: 'A4', printBackground: true });
  await b.close();
})();
