const puppeteer = require('puppeteer');

async function captureScreenshots() {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  // Mobile viewport (iPhone 14 Pro)
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2 });

  await page.goto('http://localhost:3001', { waitUntil: 'networkidle0', timeout: 30000 });

  // Wait for animations
  await new Promise(r => setTimeout(r, 2000));

  // Full page screenshot
  await page.screenshot({
    path: 'mobile-full.png',
    fullPage: true
  });

  // Hero section only
  await page.screenshot({
    path: 'mobile-hero.png'
  });

  // Scroll to features
  await page.evaluate(() => window.scrollTo(0, 900));
  await new Promise(r => setTimeout(r, 500));
  await page.screenshot({ path: 'mobile-features.png' });

  // Scroll to pricing
  await page.evaluate(() => window.scrollTo(0, 2500));
  await new Promise(r => setTimeout(r, 500));
  await page.screenshot({ path: 'mobile-pricing.png' });

  await browser.close();
  console.log('Screenshots saved: mobile-full.png, mobile-hero.png, mobile-features.png, mobile-pricing.png');
}

captureScreenshots().catch(console.error);
