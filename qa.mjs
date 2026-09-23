import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const browser = await chromium.launch({ headless: true });
const url = pathToFileURL(resolve('index.html')).href;

async function inspect(name, viewport) {
  const page = await browser.newPage({ viewportSize: viewport });
  const errors = [];
  page.on('pageerror', error => errors.push(String(error)));
  await page.goto(url, { waitUntil: 'load' });

  const report = await page.evaluate(() => ({
    title: document.title,
    layers: document.querySelectorAll('[data-layer]').length,
    checkboxes: document.querySelectorAll('input[type="checkbox"]').length,
    horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    externalBlankLabels: [...document.querySelectorAll('a[href^="http"]')].filter(a => !a.textContent.trim()).length,
  }));

  const first = page.locator('input[type="checkbox"]').first();
  await first.check();
  const progressAfterCheck = await page.locator('#progress-detail').textContent();
  await page.reload();
  const persisted = await first.isChecked();
  await first.uncheck();

  await page.screenshot({ path: `qa-${name}.png`, fullPage: true });
  await page.close();
  return { name, viewport, ...report, progressAfterCheck, persisted, errors };
}

const desktop = await inspect('desktop', { width: 1440, height: 1000 });
const mobile = await inspect('mobile', { width: 390, height: 844 });
console.log(JSON.stringify({ desktop, mobile }, null, 2));
await browser.close();
