import { chromium } from 'playwright';
import { mkdir, writeFile } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const login = process.argv.includes('--login');
const cdp = process.argv.includes('--cdp');
const edgeCookies = process.argv.includes('--edge-cookies');
const execFileAsync = promisify(execFile);
await mkdir(path.join(root, 'staging'), { recursive: true });
let browser;
let context;
if (cdp) {
  browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
  context = browser.contexts()[0];
  if (!context) throw new Error('Edge 没有可用的浏览器上下文');
} else {
  await mkdir(path.join(root, '.browser-profile'), { recursive: true, mode: 0o700 });
  context = await chromium.launchPersistentContext(path.join(root, '.browser-profile'), {
    channel: 'msedge', headless: !login, chromiumSandbox: true,
    viewport: { width: 1280, height: 900 },
  });
}
const page = context.pages()[0] || await context.newPage();
try {
  if (edgeCookies) {
    const { stdout } = await execFileAsync('python3', [
      path.join(root, 'scripts/read_edge_cookies.py'),
    ], { maxBuffer: 1024 * 1024 });
    const cookies = JSON.parse(stdout);
    await context.addCookies(cookies);
  }
  await page.goto('https://github.com/explore', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('main').waitFor({ timeout: 20000 });
  console.log('Page:', await page.title(), page.url());
  if (login && !cdp) {
    console.log('Browser ready. Sign in manually, then close this dedicated browser window.');
    await new Promise(resolve => context.on('close', resolve));
    process.exit(0);
  }
  const pageInfo = await page.evaluate(() => ({
    title: document.title,
    url: location.href,
    user_login: document.querySelector('meta[name="user-login"]')?.content || null,
    logged_in: document.body.classList.contains('logged-in') ||
      Boolean(document.querySelector('meta[name="user-login"]')?.content),
  }));
  await Promise.all([
    writeFile(path.join(root, 'staging/explore.txt'), await page.locator('main').innerText()),
    writeFile(path.join(root, 'staging/explore.html'), await page.content()),
    writeFile(path.join(root, 'staging/page.json'), JSON.stringify({
      ...pageInfo,
      observed_at: new Date().toISOString(),
    }, null, 2) + '\n'),
  ]);
  await page.screenshot({ path: path.join(root, 'staging/explore.png'), fullPage: true, timeout: 60000 })
    .catch(error => console.warn(`Screenshot skipped: ${error.message}`));
  console.log('Saved Explore text, HTML, page metadata, and screenshot in staging/');
} finally {
  // A CDP connection belongs to the user-started Edge process. Let this Node
  // process disconnect naturally instead of closing their browser.
  if (!cdp) await context.close();
}
