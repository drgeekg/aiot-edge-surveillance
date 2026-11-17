const assert = require('assert');
const fs = require('fs');
const path = require('path');

function loadPlaywright() {
  try {
    return require('playwright');
  } catch {
    const userModules = path.join(
      process.env.USERPROFILE || process.env.HOME || '',
      'node_modules',
      'playwright'
    );
    return require(userModules);
  }
}

const { chromium } = loadPlaywright();

const EDGE_URL = process.env.EDGE_URL || 'http://localhost:5174';
const ANALYTICS_URL = process.env.ANALYTICS_URL || 'http://localhost:5173';
const SCREENSHOTS_DIR = path.resolve(__dirname, '..', 'screenshots');
const REVIEW_DIR = path.resolve(__dirname, '..', '.impeccable', 'review');

async function assertNoOverflow(page, label) {
  const overflow = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  assert(
    overflow.scrollWidth <= overflow.clientWidth,
    `${label} horizontal overflow: scrollWidth=${overflow.scrollWidth} > clientWidth=${overflow.clientWidth}`
  );
}

async function run() {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
  fs.mkdirSync(REVIEW_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const errors = [];

  const attachErrorHooks = (page, tag) => {
    const failedUrls = new Map();
    page.on('response', (res) => {
      if (res.status() >= 400) {
        failedUrls.set(res.url(), res.status());
      }
    });
    page.on('pageerror', (err) => errors.push(`[${tag}] pageerror: ${err.message}`));
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        // Polling /edge/frame or /frames/latest returns 404 briefly before first frame is emitted.
        if (text.includes('status of 404')) {
          const allFrame404 = Array.from(failedUrls.keys()).every(
            (u) => u.includes('/edge/frame') || u.includes('/frames/latest')
          );
          if (allFrame404 && failedUrls.size > 0) return;
        }
        errors.push(`[${tag}] console.error: ${text}`);
      }
    });
  };

  try {
    // 1. Verify Edge Control Deck (:5174)
    const edgeContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const edgePage = await edgeContext.newPage();
    attachErrorHooks(edgePage, 'edge');

    await edgePage.goto(EDGE_URL, { waitUntil: 'domcontentloaded' });
    await edgePage.waitForSelector('h1.page-title');
    await edgePage.waitForSelector('.source-btn');

    assert.strictEqual(await edgePage.title(), 'Edge Control Deck (:5174)');
    assert.strictEqual(await edgePage.textContent('h1.page-title'), 'Edge Emitter Control');
    assert.strictEqual(await edgePage.locator('.custom-cursor-ring').count(), 0);
    assert.strictEqual(await edgePage.locator('.metric-strip .metric-cell').count(), 6);
    await assertNoOverflow(edgePage, 'Edge Desktop 1440');

    // Switch to non-active source if present so live preview + source switcher get exercised.
    const selectableSource = edgePage.locator('.source-btn:not(.source-btn--active)').first();
    if ((await selectableSource.count()) > 0) {
      await selectableSource.click();
      await edgePage.waitForTimeout(700);
    }
    await edgePage.screenshot({
      path: path.join(SCREENSHOTS_DIR, 'react_edge_deck.png'),
      fullPage: true,
    });
    await edgePage.screenshot({
      path: path.join(REVIEW_DIR, 'edge_desktop.png'),
      fullPage: true,
    });

    // Encoder tab
    await edgePage.click('#tab-encoder');
    await edgePage.waitForSelector('#encoder-fps');
    await edgePage.click('button:has-text("Save Settings")');
    await edgePage.waitForSelector('.notice-bar');
    await edgePage.screenshot({
      path: path.join(SCREENSHOTS_DIR, 'react_edge_encoder.png'),
      fullPage: true,
    });

    // Event Injector tab -> send synthetic R1 trigger
    await edgePage.click('#tab-inject');
    await edgePage.waitForSelector('button:has-text("Trigger R1")');
    await edgePage.click('button:has-text("Trigger R1")');
    await edgePage.waitForSelector('.notice-bar:has-text("Synthetic R1 sent")');
    await edgePage.screenshot({
      path: path.join(SCREENSHOTS_DIR, 'react_edge_inject.png'),
      fullPage: true,
    });

    // Responsive tablet & mobile check on Edge Deck
    await edgePage.click('#tab-sources');
    await edgePage.setViewportSize({ width: 768, height: 1024 });
    await edgePage.waitForTimeout(200);
    await assertNoOverflow(edgePage, 'Edge Tablet 768');
    await edgePage.screenshot({
      path: path.join(REVIEW_DIR, 'edge_tablet.png'),
      fullPage: true,
    });

    await edgePage.setViewportSize({ width: 390, height: 844 });
    await edgePage.waitForTimeout(200);
    await assertNoOverflow(edgePage, 'Edge Mobile 390');
    await edgePage.screenshot({
      path: path.join(REVIEW_DIR, 'edge_mobile.png'),
      fullPage: true,
    });

    // Restore default unattended bag scenario source after switch test
    const defaultSource = edgePage.locator('.source-btn:has-text("data/demo.mp4")').first();
    if ((await defaultSource.count()) > 0) {
      await defaultSource.click();
      await edgePage.waitForTimeout(300);
    }
    await edgeContext.close();

    // 2. Verify Analytics Console (:5173)
    const analyticsContext = await browser.newContext({
      viewport: { width: 1440, height: 900 },
    });
    const analyticsPage = await analyticsContext.newPage();
    attachErrorHooks(analyticsPage, 'analytics');

    await analyticsPage.goto(ANALYTICS_URL, { waitUntil: 'domcontentloaded' });
    await analyticsPage.waitForSelector('h1.page-title');
    await analyticsPage.waitForSelector('table.data-table, .compact-list, .empty-state');

    assert.strictEqual(await analyticsPage.title(), 'Analytics Console (:5173)');
    assert.strictEqual(await analyticsPage.textContent('h1.page-title'), 'Live Pipeline Monitor');
    assert.strictEqual(await analyticsPage.locator('.custom-cursor-ring').count(), 0);
    assert.strictEqual(await analyticsPage.locator('.metric-strip .metric-cell').count(), 6);
    assert((await analyticsPage.locator('.chart-svg').count()) === 1, 'Occupancy chart SVG missing');

    // Wait briefly so recent injected telemetry & frame poll settle cleanly
    await analyticsPage.waitForTimeout(1000);
    await assertNoOverflow(analyticsPage, 'Analytics Desktop 1440');
    await analyticsPage.screenshot({
      path: path.join(SCREENSHOTS_DIR, 'react_analytics_live.png'),
      fullPage: true,
    });
    await analyticsPage.screenshot({
      path: path.join(REVIEW_DIR, 'analytics_desktop.png'),
      fullPage: true,
    });

    // Anomalies tab should list our injected occupancy_spike
    await analyticsPage.click('#tab-anomalies');
    await analyticsPage.waitForSelector('table.data-table');
    const anomalyText = await analyticsPage.textContent('table.data-table');
    assert(
      anomalyText && anomalyText.includes('occupancy_spike'),
      'Expected injected occupancy_spike in Anomalies table'
    );
    await analyticsPage.screenshot({
      path: path.join(SCREENSHOTS_DIR, 'react_analytics_anomalies.png'),
      fullPage: true,
    });

    // Detections tab
    await analyticsPage.click('#tab-detections');
    await analyticsPage.waitForTimeout(200);
    await assertNoOverflow(analyticsPage, 'Analytics Detections Desktop');
    await analyticsPage.screenshot({
      path: path.join(REVIEW_DIR, 'analytics_detections.png'),
      fullPage: true,
    });

    // Nodes & Rules tab
    await analyticsPage.click('#tab-nodes');
    await analyticsPage.waitForSelector('h2:has-text("System Health")');
    await analyticsPage.screenshot({
      path: path.join(SCREENSHOTS_DIR, 'react_analytics_nodes.png'),
      fullPage: true,
    });

    // Return to Live Monitor for tablet & mobile screenshots
    await analyticsPage.click('#tab-live');
    await analyticsPage.setViewportSize({ width: 768, height: 1024 });
    await analyticsPage.waitForTimeout(250);
    await assertNoOverflow(analyticsPage, 'Analytics Tablet 768');
    await analyticsPage.screenshot({
      path: path.join(REVIEW_DIR, 'analytics_tablet.png'),
      fullPage: true,
    });

    await analyticsPage.setViewportSize({ width: 390, height: 844 });
    await analyticsPage.waitForTimeout(250);
    await assertNoOverflow(analyticsPage, 'Analytics Mobile 390');
    await analyticsPage.screenshot({
      path: path.join(REVIEW_DIR, 'analytics_mobile.png'),
      fullPage: true,
    });
    await analyticsContext.close();

    assert.strictEqual(
      errors.length,
      0,
      `Console/page errors detected:\n${errors.join('\n')}`
    );
    console.log('ALL FRONTEND E2E CHECKS PASSED');
  } finally {
    await browser.close();
  }
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
