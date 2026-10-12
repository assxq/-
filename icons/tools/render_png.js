// Renders icons/svg-color/*.svg to transparent 512px PNGs in icons/png/.
// Requires Playwright with a Chromium build.  Usage:  node icons/tools/render_png.js
const fs = require('fs');
const path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node-tools/node_modules/playwright')); }

const root = path.resolve(__dirname, '..');
const src = path.join(root, 'svg-color');
const out = path.join(root, 'png');
const SIZE = 512;

(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH || undefined,
    args: ['--no-sandbox']
  });
  const page = await browser.newPage({ viewport: { width: SIZE, height: SIZE } });
  for (const f of fs.readdirSync(src).filter(n => n.endsWith('.svg'))) {
    const svg = fs.readFileSync(path.join(src, f), 'utf8').replace('width="48" height="48"', `width="${SIZE}" height="${SIZE}"`);
    await page.setContent(`<html><body style="margin:0;background:transparent">${svg}</body></html>`);
    await page.screenshot({ path: path.join(out, f.replace('.svg', '.png')), omitBackground: true, clip: { x: 0, y: 0, width: SIZE, height: SIZE } });
  }
  await browser.close();
  console.log('rendered', fs.readdirSync(out).length, 'PNGs');
})();
