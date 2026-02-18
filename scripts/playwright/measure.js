// Quick layout measurement with Playwright
// Requires: npm i playwright

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

async function readConfig() {
  const configPath = path.join(__dirname, 'layout.config.json');
  const raw = fs.readFileSync(configPath, 'utf8');
  return JSON.parse(raw);
}

async function ensureDir(dir) {
  await fs.promises.mkdir(dir, { recursive: true });
}

async function measurePage(page, pageSpec, outputDir) {
  const results = { name: pageSpec.name, url: pageSpec.url, measures: [] };

  for (const sel of pageSpec.selectors) {
    const handles = await page.$$(sel);
    for (let i = 0; i < handles.length; i++) {
      const handle = handles[i];
      const box = await handle.boundingBox();
      if (!box) continue;
      const styles = await handle.evaluate((el) => {
        const cs = window.getComputedStyle(el);
        return {
          color: cs.color,
          backgroundColor: cs.backgroundColor,
          fontSize: cs.fontSize,
          fontFamily: cs.fontFamily,
          fontWeight: cs.fontWeight,
          lineHeight: cs.lineHeight,
          border: cs.border,
          borderRadius: cs.borderRadius,
          boxShadow: cs.boxShadow,
          backdropFilter: cs.backdropFilter,
          backgroundClip: cs.backgroundClip,
          WebkitBackgroundClip: cs.webkitBackgroundClip,
        };
      });
      results.measures.push({ selector: sel, index: i, box, styles });
    }
  }

  await ensureDir(outputDir);
  const jsonPath = path.join(outputDir, `${pageSpec.name}.json`);
  fs.writeFileSync(jsonPath, JSON.stringify(results, null, 2));

  const screenshotPath = path.join(outputDir, `${pageSpec.name}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });
}

(async () => {
  const config = await readConfig();
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: config.viewport });
  const page = await context.newPage();

  const base = config.baseUrl.replace(/\/$/, '');
  const outputBase = path.join(process.cwd(), config.outputDir || 'playwright-output');
  await ensureDir(outputBase);

  for (const pageSpec of config.pages) {
    const target = base + pageSpec.url;
    console.log(`Measuring ${pageSpec.name}: ${target}`);
    await page.goto(target, { waitUntil: 'networkidle' });
    await measurePage(page, pageSpec, outputBase);
  }

  await browser.close();
  console.log(`Done. Results in ${outputBase}`);
})();
