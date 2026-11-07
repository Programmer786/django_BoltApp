// Bolt WhatsApp verification listener.
//
// Keeps one WhatsApp Web session open (headless Chromium), forwards every
// private text message to the Bolt app (/wa-bot/api/incoming/) and sends back
// the reply it returns. All decisions — lookups, wording, rate limits, AI —
// live in the Django app; this process is only the WhatsApp "pipe".
//
// Status (QR code, connected number) is reported to /wa-bot/api/status/ so
// the "WhatsApp Verification" page can show the QR to scan.

const fs = require('fs');
const path = require('path');
const { Client, LocalAuth } = require('whatsapp-web.js');

// Host name must not contain "_" (Django rejects it), hence the "bolt-web" alias.
const API = (process.env.BOLT_API_URL || 'http://bolt-web:8000/wa-bot/api').replace(/\/$/, '');
const KEY = process.env.WA_BOT_KEY || '';
const AUTH_PATH = process.env.AUTH_PATH || '/data/session';
const READY_TIMEOUT_MS = Number(process.env.READY_TIMEOUT_MS || 180000);
const HEARTBEAT_MS = 30000;

const log = (...a) => console.log(new Date().toISOString(), ...a);

if (!KEY) {
  log('FATAL: WA_BOT_KEY is not set.');
  process.exit(1);
}

// --- Self-healing (same approach as the laptop agent's listener) -----------
// Chromium leaves Singleton* lock files when a container is killed uncleanly.
const SESSION_DIR = path.join(AUTH_PATH, 'session');
for (const f of ['SingletonLock', 'SingletonSocket', 'SingletonCookie']) {
  try { fs.rmSync(path.join(SESSION_DIR, f), { force: true }); } catch (e) { /* ignore */ }
}
// If start-up keeps failing, the saved login itself is dead (e.g. unlinked
// from the phone): move it aside so the next start shows a fresh QR code.
const FAIL_FILE = path.join(AUTH_PATH, '.init_failures');
const MAX_INIT_FAILURES = Number(process.env.MAX_INIT_FAILURES || 5);
const readFailures = () => { try { return Number(fs.readFileSync(FAIL_FILE, 'utf8')) || 0; } catch (e) { return 0; } };
const writeFailures = (n) => { try { fs.writeFileSync(FAIL_FILE, String(n)); } catch (e) { /* ignore */ } };
function quarantineDeadSession(reason) {
  try {
    if (!fs.existsSync(SESSION_DIR)) return;
    const dest = `${SESSION_DIR}.LOGGED-OUT-${Date.now()}`;
    fs.renameSync(SESSION_DIR, dest);
    log(`Dead WhatsApp login set aside (${reason}). A new QR code will be shown.`);
    const old = fs.readdirSync(AUTH_PATH).filter((n) => n.startsWith('session.LOGGED-OUT-')).sort().slice(0, -1);
    for (const n of old) { try { fs.rmSync(path.join(AUTH_PATH, n), { recursive: true, force: true }); } catch (e) { /* ignore */ } }
  } catch (e) {
    log('could not set the dead login aside:', e.message);
  }
}
// Errors after start-up (WhatsApp Web glitches) must not kill a working bot.
process.on('unhandledRejection', (reason) => {
  log('Unhandled rejection (ignored):', reason && reason.message ? reason.message : reason);
});

let state = 'starting';
let currentQr = '';
let phone = '';

async function api(path, body, timeoutMs = 15000) {
  const res = await fetch(`${API}/${path}/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Bot-Key': KEY },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}`);
  return res.json();
}

async function reportStatus() {
  try {
    const out = await api('status', { state, qr: state === 'qr' ? currentQr : '', phone });
    if (out.command === 'logout') {
      log('Logout requested from the Bolt page.');
      try { await client.logout(); } catch (e) { log('logout error:', e.message); }
      // Exit so Docker restarts us cleanly with no session -> fresh QR code.
      process.exit(0);
    }
  } catch (e) {
    log('status report failed:', e.message);
  }
}

function setState(s, extra = {}) {
  state = s;
  if ('qr' in extra) currentQr = extra.qr;
  if ('phone' in extra) phone = extra.phone;
  reportStatus();
}

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: AUTH_PATH }),
  restartOnAuthFail: true,
  takeoverOnConflict: true,
  takeoverTimeoutMs: 10000,
  puppeteer: {
    headless: true,
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || '/usr/bin/chromium',
    args: [
      '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
      // No JS heap cap: WhatsApp Web needs well over 256 MB while it syncs
      // after a QR scan, and a cap makes the login stall silently.
      '--disable-gpu', '--no-first-run', '--disable-extensions',
    ],
  },
});

// whatsapp-web.js sometimes authenticates but never fires 'ready'. If that
// happens, exit and let Docker's restart policy start a clean instance.
let ready = false;
let readyTimer = null;
function armReadyWatchdog() {
  clearTimeout(readyTimer);
  readyTimer = setTimeout(() => {
    if (!ready) {
      log(`not ready ${READY_TIMEOUT_MS}ms after login - restarting.`);
      process.exit(1);
    }
  }, READY_TIMEOUT_MS);
}

// Start-up watchdog: a half-written saved login (e.g. after an out-of-memory
// kill mid-sync) can leave WhatsApp Web loading forever with no QR and no
// login event. Count it as a failed start; after MAX_INIT_FAILURES the dead
// login is set aside and a fresh QR is shown.
const STARTUP_TIMEOUT_MS = Number(process.env.STARTUP_TIMEOUT_MS || 180000);
const startupTimer = setTimeout(() => {
  const n = readFailures() + 1;
  log(`no QR code or login ${STARTUP_TIMEOUT_MS / 1000}s after start (${n} in a row) - restarting.`);
  writeFailures(n);
  if (n >= 2) {  // two stuck starts in a row: the saved login is the problem
    quarantineDeadSession('stuck loading twice in a row');
    writeFailures(0);
  }
  process.exit(1);
}, STARTUP_TIMEOUT_MS);

client.on('qr', (qr) => {
  clearTimeout(startupTimer);
  log('QR code received - scan it on the WhatsApp Verification page.');
  setState('qr', { qr });
});
client.on('authenticated', () => {
  clearTimeout(startupTimer);
  log('Authenticated.');
  setState('starting', { qr: '' });
  armReadyWatchdog();
});
client.on('auth_failure', (m) => log('AUTH FAILURE:', m));
client.on('ready', () => {
  ready = true;
  clearTimeout(readyTimer);
  writeFailures(0);
  const me = (client.info && client.info.wid && client.info.wid.user) || '';
  log(`READY as +${me}`);
  setState('ready', { qr: '', phone: me });
});
client.on('disconnected', (reason) => {
  log('Disconnected:', reason);
  state = 'disconnected';
  reportStatus().finally(() => process.exit(1));
});

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function resolveContact(msg) {
  for (let attempt = 1; attempt <= 2; attempt++) {
    try { return await msg.getContact(); } catch (e) {
      log(`getContact() attempt ${attempt} failed:`, e.message);
      if (attempt === 1) await sleep(600);
    }
  }
  try { return await client.getContactById(msg.from); } catch (e) { return null; }
}

async function processMessage(msg) {
  if (msg.fromMe || msg.from === 'status@broadcast') return;
  if (String(msg.from).endsWith('@g.us')) return; // ignore groups
  if (msg.isStatus) return;

  // WhatsApp often gives a hidden "@lid" id instead of the phone number;
  // contact.id.user is the real number when it is available.
  const contact = await resolveContact(msg);
  const number = String(
    (contact && contact.id && contact.id.user) || (contact && contact.number) || String(msg.from).split('@')[0]
  );
  const name = (contact && (contact.pushname || contact.name)) || '';
  const text = msg.type === 'chat' ? (msg.body || '') : '';
  log(`IN  +${number} ${name}: ${text.slice(0, 80) || `[${msg.type}]`}`);

  let chat = null;
  try { chat = await msg.getChat(); await chat.sendStateTyping(); } catch (e) { /* best effort */ }

  let reply = '';
  try {
    // Long timeout: the free AI model on a 1-CPU server can take a while.
    const out = await api('incoming', { phone: number, name, text }, 90000);
    reply = out.reply || '';
  } catch (e) {
    log('incoming failed:', e.message);
    reply = 'Sorry, the verification service is temporarily unavailable. Please try again in a few minutes.';
  }

  try { if (chat) await chat.clearState(); } catch (e) { /* best effort */ }
  if (!reply) return; // bot disabled
  try {
    await client.sendMessage(msg.from, reply);
    log(`OUT +${number}: ${reply.split('\n')[0].slice(0, 80)}`);
  } catch (e) {
    log('send failed:', e.message);
  }
}

// One message at a time per chat, so replies stay in order.
const chains = new Map();
client.on('message', (msg) => {
  const prev = chains.get(msg.from) || Promise.resolve();
  const run = prev.then(() => processMessage(msg)).catch((e) => log('handler error:', e.message));
  chains.set(msg.from, run);
  run.finally(() => { if (chains.get(msg.from) === run) chains.delete(msg.from); });
});

setInterval(reportStatus, HEARTBEAT_MS);
process.on('SIGTERM', () => { state = 'offline'; reportStatus().finally(() => process.exit(0)); });

log(`Starting WhatsApp listener (API ${API})`);
setState('starting');
// A failed initialize() is usually a Chromium/WhatsApp Web start-up race; a
// fresh container (Docker restart policy) fixes it, an in-process retry doesn't.
client.initialize().catch((e) => {
  const n = readFailures() + 1;
  log(`initialize failed (${n} in a row) - exiting so Docker restarts fresh:`, e.message);
  writeFailures(n);
  if (n >= MAX_INIT_FAILURES) {
    quarantineDeadSession(`${n} failed starts in a row`);
    writeFailures(0);
  }
  process.exit(1);
});
