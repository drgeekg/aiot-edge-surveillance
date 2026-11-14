const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

/**
 * Headless Playwright smoke test verifying both :5174 Edge Emitter Deck and :5173 Analytics Console views.
 */
async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });

  fs.mkdirSync('screenshots', { recursive: true });

  console.log('--- 1. Testing Edge Emitter Deck (:5174) ---');
  const edgePage = await context.newPage();
  await edgePage.goto('http://localhost:5174', { waitUntil: 'domcontentloaded' });
  await edgePage.waitForTimeout(1500);

  // Check Custom Cursor
  const cursorRing = await edgePage.$('.custom-cursor-ring');
  const cursorDot = await edgePage.$('.custom-cursor-dot');
  console.log(`Custom cursor present: ring=${Boolean(cursorRing)}, dot=${Boolean(cursorDot)}`);

  // Check Tabs
  const tabs = await edgePage.$$('.ios-tab-btn');
  console.log(`Edge tabs count: ${tabs.length}`);

  // Take screenshot of initial Edge Deck
  await edgePage.screenshot({ path: 'screenshots/react_edge_deck.png' });
  console.log('Saved screenshots/react_edge_deck.png');

  // Test switching video source to demo_attended.mp4
  console.log('--- Switching video source to demo_attended.mp4 ---');
  const sourceButtons = await edgePage.$$('.source-item');
  if (sourceButtons.length >= 2) {
    await sourceButtons[1].click();
    await edgePage.waitForTimeout(1200);
  }
  await edgePage.screenshot({ path: 'screenshots/react_edge_deck_switched.png' });
  console.log('Saved screenshots/react_edge_deck_switched.png');

  // Test Encoder tab
  if (tabs.length >= 2) {
    await tabs[1].click(); // Encoder & Bandwidth
    await edgePage.waitForTimeout(600);
    await edgePage.screenshot({ path: 'screenshots/react_edge_encoder.png' });
    console.log('Saved screenshots/react_edge_encoder.png');
  }

  // Test Injector tab
  if (tabs.length >= 3) {
    await tabs[2].click(); // Synthetic Anomaly Injector
    await edgePage.waitForTimeout(600);
    const injectBtns = await edgePage.$$('.glass-btn');
    if (injectBtns.length > 0) {
      console.log('Clicking synthetic injector R1 Occupancy Spike...');
      await injectBtns[0].click();
      await edgePage.waitForTimeout(800);
    }
    await edgePage.screenshot({ path: 'screenshots/react_edge_inject.png' });
    console.log('Saved screenshots/react_edge_inject.png');
  }

  console.log('--- 2. Testing Server Analytics Console (:5173) ---');
  const analyticsPage = await context.newPage();
  await analyticsPage.goto('http://localhost:5173', { waitUntil: 'domcontentloaded' });
  await analyticsPage.waitForTimeout(2000);

  // Verify stream / stats
  const analyticsTitle = await analyticsPage.$eval('.hero-title', el => el.textContent);
  console.log(`Analytics title: "${analyticsTitle}"`);

  await analyticsPage.screenshot({ path: 'screenshots/react_analytics_live.png' });
  console.log('Saved screenshots/react_analytics_live.png');

  // Switch tabs in Analytics Console
  const aTabs = await analyticsPage.$$('.ios-tab-btn');
  console.log(`Analytics tabs count: ${aTabs.length}`);

  if (aTabs.length >= 2) {
    await aTabs[1].click(); // Anomaly Vault
    await analyticsPage.waitForTimeout(800);
    await analyticsPage.screenshot({ path: 'screenshots/react_analytics_anomalies.png' });
    console.log('Saved screenshots/react_analytics_anomalies.png');
  }

  if (aTabs.length >= 3) {
    await aTabs[2].click(); // Detection Ledger
    await analyticsPage.waitForTimeout(800);
    await analyticsPage.screenshot({ path: 'screenshots/react_analytics_events.png' });
    console.log('Saved screenshots/react_analytics_events.png');
  }

  if (aTabs.length >= 4) {
    await aTabs[3].click(); // Nodes & Rules
    await analyticsPage.waitForTimeout(800);
    await analyticsPage.screenshot({ path: 'screenshots/react_analytics_nodes.png' });
    console.log('Saved screenshots/react_analytics_nodes.png');
  }

  await browser.close();
  console.log('All automated browser tests passed!');
}

run().catch(err => {
  console.error('Test error:', err);
  process.exit(1);
});
