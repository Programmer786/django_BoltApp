"""
WhatsApp Web automation via Selenium.
Designed for LOCAL use on Windows — Chrome must be installed.
A persistent Chrome profile stores the WhatsApp Web session so QR is
scanned only once (until the session expires or user logs out).
"""
import base64
import logging
import os
import threading
import time
import urllib.parse

logger = logging.getLogger(__name__)

_driver = None
_lock = threading.RLock()   # re-entrant: one Selenium operation at a time, same thread may re-enter

# Multiple selector fallbacks — WhatsApp Web updates selectors occasionally
_SEL = {
    'logged_in': [
        '#side',
        'div[data-testid="chat-list"]',
        'header[data-testid="chatlist-header"]',
    ],
    'qr': [
        'canvas[aria-label="Scan me!"]',
        'div[data-ref] canvas',
        '[data-testid="qrcode"] canvas',
    ],
    'msg_input': [
        'div[data-testid="conversation-compose-box-input"]',
        'div[contenteditable="true"][data-tab="10"]',
        'footer div[contenteditable="true"]',
    ],
    'send_btn': [
        'button[data-testid="compose-btn-send"]',
        'span[data-testid="send"]',
        'button[aria-label="Send"]',
        'div[role="button"][aria-label="Send"]',
    ],
    # Image attachment flow
    'attach_btn': [
        'div[title="Attach"]',
        'span[data-testid="clip"]',
        'div[data-testid="conversation-clip"]',
        'button[title="Attach"]',
        'span[data-icon="plus"]',
        'span[data-icon="clip"]',
        'span[data-icon="attach-menu-plus"]',
    ],
    'image_input': [
        'input[accept*="image"]',
        'input[type="file"][accept*="image"]',
    ],
    'any_file_input': [
        'input[type="file"]',
    ],
    'caption_input': [
        'div[data-testid="media-caption-input-container"] div[contenteditable="true"]',
        'div[contenteditable="true"][data-tab="10"]',
        'div[contenteditable="true"][aria-label*="aption"]',
        'div[contenteditable="true"]',
    ],
}


# ── Driver management ──────────────────────────────────────────────────────────

def _base_dir():
    try:
        from django.conf import settings
        return str(settings.BASE_DIR)
    except Exception:
        return os.getcwd()


def _profile_dir():
    import platform
    # On Linux the gunicorn user (www-data) cannot write to the project dir
    # unless ownership was fixed manually.  /tmp is always writable by everyone.
    if platform.system() != 'Windows':
        return '/tmp/wa_session'
    return os.path.join(_base_dir(), '.whatsapp_session')


def _kill_stale_profile_chrome(profile):
    """
    Close any Chrome still holding OUR WhatsApp profile folder — typically an
    orphan left behind when the Django server was stopped or auto-reloaded
    (the Chrome child outlives it). A second Chrome on the same profile
    crashes on start ("Chrome failed to start: crashed"). Only processes whose
    command line names this exact profile are touched; a normal Chrome is safe.
    """
    needle = os.path.normcase(os.path.abspath(profile))
    killed = 0
    try:
        import psutil
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                name = (proc.info['name'] or '').lower()
                if 'chrome' not in name and 'chromium' not in name:
                    continue
                cmd = os.path.normcase(' '.join(proc.info['cmdline'] or []))
                if needle in cmd:
                    proc.kill()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        import platform
        import subprocess
        if platform.system() == 'Windows':
            ps = ("Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
                  "Where-Object { $_.CommandLine -like '*' + $env:WA_PROFILE + '*' } | "
                  "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
            try:
                subprocess.run(['powershell', '-NoProfile', '-Command', ps], timeout=20,
                               env={**os.environ, 'WA_PROFILE': os.path.abspath(profile)})
            except Exception as exc:
                logger.warning(f"could not clean stale Chrome: {exc}")
    if killed:
        logger.info(f"Closed {killed} leftover Chrome process(es) using the WhatsApp profile")
        time.sleep(1.5)  # let the OS release the profile lock


def _is_alive(driver):
    try:
        _ = driver.current_url
        return True
    except Exception:
        return False


def _show_browser():
    """Set WHATSAPP_SHOW_BROWSER=1 in .env to see the Chrome window (debugging)."""
    return os.getenv('WHATSAPP_SHOW_BROWSER', '0').strip().lower() in ('1', 'true', 'yes')


def _chrome_opts():
    import platform
    from selenium import webdriver

    opts = webdriver.ChromeOptions()
    opts.add_argument(f'--user-data-dir={_profile_dir()}')

    # Core stability flags — required on VPS/container environments
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-setuid-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-software-rasterizer')

    # Reduce resource usage
    opts.add_argument('--window-size=1280,900')
    opts.add_argument('--disable-extensions')
    opts.add_argument('--disable-default-apps')
    opts.add_argument('--disable-background-networking')
    opts.add_argument('--disable-sync')
    opts.add_argument('--no-first-run')
    opts.add_argument('--disable-logging')
    opts.add_argument('--log-level=3')

    # Bot-detection bypass
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option('excludeSwitches', ['enable-automation'])
    opts.add_experimental_option('useAutomationExtension', False)

    if platform.system() != 'Windows':
        opts.add_argument('--headless=new')
        opts.add_argument('--no-zygote')
        opts.add_argument('--disable-gpu-sandbox')
        # --single-process removed: deprecated in Chrome 115+ and causes crashes
    elif not _show_browser():
        # Run Chrome hidden on Windows too, so no separate window pops up when
        # the connection is checked (the QR is shown inside the Django modal).
        opts.add_argument('--headless=new')

    return opts


def _apply_stealth(driver):
    # Headless Chrome announces itself as "HeadlessChrome", which WhatsApp Web
    # answers with a "browser not supported" page instead of the QR code.
    try:
        ua = driver.execute_script('return navigator.userAgent')
        if 'Headless' in ua:
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {'userAgent': ua.replace('HeadlessChrome', 'Chrome')})
    except Exception:
        pass
    try:
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        })
    except Exception:
        pass


def _build_driver():
    import platform
    from selenium import webdriver

    is_linux = platform.system() != 'Windows'

    # Chrome's crashpad needs a writable HOME to create its crash database.
    # www-data's HOME is /var/www (not writable) → Chrome exits immediately.
    # /tmp is world-writable and fixes this.
    if is_linux:
        os.environ['HOME'] = '/tmp'

    profile = _profile_dir()

    # /tmp is world-writable — gunicorn (www-data), root, any user can write.
    # Project dir created by root is NOT writable by www-data.
    drv_cache = '/tmp/wa_drivers' if is_linux else os.path.join(_base_dir(), '.wdm')

    os.makedirs(profile, exist_ok=True)
    os.makedirs(drv_cache, exist_ok=True)

    _kill_stale_profile_chrome(profile)

    # Remove stale Chrome lock files left by previous crashed instances
    for _lock in ('SingletonLock', 'SingletonSocket', 'SingletonCookie', 'lockfile'):
        _lp = os.path.join(profile, _lock)
        try:
            if os.path.exists(_lp):
                os.remove(_lp)
        except Exception:
            pass

    # selenium-manager (selenium 4.6+) reads SE_CACHE_PATH
    os.environ['SE_CACHE_PATH'] = drv_cache

    opts = _chrome_opts()
    last_err = None

    # ── Attempt 1: system ChromeDriver installed via apt / manual download ─────
    # Most reliable — exact version match guaranteed.
    # Install: see README or run the one-liner in selenium_sender.py header.
    for cd_path in ('/usr/local/bin/chromedriver', '/usr/bin/chromedriver',
                    '/usr/bin/chromium-driver'):
        if not os.path.exists(cd_path):
            continue
        try:
            from selenium.webdriver.chrome.service import Service as ChromeService
            driver = webdriver.Chrome(
                service=ChromeService(cd_path), options=opts
            )
            _apply_stealth(driver)
            driver.get('https://web.whatsapp.com')
            time.sleep(3)
            return driver
        except Exception as exc:
            last_err = exc
            logger.warning(f"system chromedriver ({cd_path}) failed: {exc}")

    # ── Attempt 2: selenium-manager (built into selenium 4.6+) ────────────────
    try:
        driver = webdriver.Chrome(options=opts)
        _apply_stealth(driver)
        driver.get('https://web.whatsapp.com')
        time.sleep(5)
        return driver
    except Exception as exc:
        last_err = exc
        logger.warning(f"selenium-manager attempt failed: {exc}")

    # ── Attempt 3: webdriver-manager — HOME=/tmp so ~/.wdm = /tmp/.wdm ────────
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service

        old_home = os.environ.get('HOME')
        if is_linux:
            os.environ['HOME'] = '/tmp'
        try:
            driver_path = ChromeDriverManager().install()
        finally:
            if old_home is not None:
                os.environ['HOME'] = old_home
            else:
                os.environ.pop('HOME', None)

        driver = webdriver.Chrome(service=Service(driver_path), options=opts)
        _apply_stealth(driver)
        driver.get('https://web.whatsapp.com')
        time.sleep(5)
        return driver
    except Exception as exc:
        last_err = exc
        logger.warning(f"webdriver-manager attempt failed: {exc}")

    raise RuntimeError(f"Chrome/ChromeDriver could not start: {last_err}")


def _get_driver():
    global _driver
    with _lock:
        if _driver is None or not _is_alive(_driver):
            _driver = _build_driver()
        return _driver


import atexit  # noqa: E402


def close_driver():
    global _driver
    with _lock:
        if _driver:
            try:
                _driver.quit()
            except Exception:
                pass
            _driver = None


atexit.register(close_driver)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _find(driver, selectors, timeout=8):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    for sel in selectors:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, sel))
            )
            return el
        except Exception:
            continue
    return None


def _click(driver, selectors, timeout=8):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    for sel in selectors:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
            )
            el.click()
            return True
        except Exception:
            continue
    return False


# ── Public API ─────────────────────────────────────────────────────────────────

def get_status():
    """
    Returns:
        {
            'available': bool,    # selenium importable?
            'logged_in': bool,
            'qr_image': str|None, # base64 PNG of QR (if not logged in)
            'error': str|None,
        }
    """
    try:
        import selenium  # noqa
    except ImportError:
        return {
            'available': False,
            'logged_in': False,
            'qr_image': None,
            'error': 'selenium not installed — run: pip install selenium webdriver-manager',
        }

    # Serialize all driver access — only one thread may touch Chrome at a time
    with _lock:
        try:
            driver = _get_driver()
        except Exception as exc:
            err = str(exc).split('\n')[0]  # first line only — cleaner for UI
            logger.error(f"WhatsApp Web driver start failed: {exc}")
            return {'available': True, 'logged_in': False, 'qr_image': None, 'error': err}

        try:
            # Wait ONCE for whichever appears first: the chat list (logged in)
            # or the QR canvas — instead of trying each selector in turn.
            state, qr_el = _wait_login_state(driver, timeout=25)
            if state == 'logged_in':
                return {'available': True, 'logged_in': True, 'qr_image': None, 'error': None}

            qr_b64 = None
            if qr_el is not None:
                try:
                    qr_b64 = base64.b64encode(qr_el.screenshot_as_png).decode('utf-8')
                except Exception:
                    pass

            if qr_b64 is None:
                # Fallback: full-page screenshot (user can see what Chrome rendered)
                try:
                    qr_b64 = base64.b64encode(driver.get_screenshot_as_png()).decode('utf-8')
                except Exception:
                    pass

            return {'available': True, 'logged_in': False, 'qr_image': qr_b64, 'error': None}

        except Exception as exc:
            logger.error(f"WhatsApp Web get_status error: {exc}")
            return {'available': True, 'logged_in': False, 'qr_image': None, 'error': str(exc)}


def _wait_login_state(driver, timeout=25):
    """Return ('logged_in', None), ('qr', <canvas element>) or (None, None)."""
    from selenium.webdriver.common.by import By
    logged_in_css = ', '.join(_SEL['logged_in'])
    qr_css = ', '.join(_SEL['qr'])
    end = time.time() + timeout
    while time.time() < end:
        if driver.find_elements(By.CSS_SELECTOR, logged_in_css):
            return 'logged_in', None
        qr = driver.find_elements(By.CSS_SELECTOR, qr_css)
        if qr:
            time.sleep(1.5)  # a restoring session can flash the QR briefly
            if driver.find_elements(By.CSS_SELECTOR, logged_in_css):
                return 'logged_in', None
            return 'qr', qr[0]
        time.sleep(0.5)
    return None, None


# Picks the media-preview's OWN Send button and caption box.
# Critical: the normal chat compose box must never be chosen — typing there and
# clicking its send button fires the text as a separate message and leaves the
# picture sitting unsent in the preview.
_ANALYSE_PREVIEW_JS = r"""
const skip = arguments[0];   // the chat's compose box, if still known
const vis = e => { const r = e.getBoundingClientRect(); return r.width > 2 && r.height > 2; };
const topmost = e => {       // false for anything covered by the preview overlay
  const r = e.getBoundingClientRect();
  const vw = innerWidth, vh = innerHeight;
  // Outside the viewport we simply cannot tell — don't reject on that basis.
  if (r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw) return true;
  const x = Math.min(Math.max(r.x + r.width / 2, 1), vw - 1);
  const y = Math.min(Math.max(r.y + r.height / 2, 1), vh - 1);
  const hit = document.elementFromPoint(x, y);
  if (!hit) return true;
  return hit === e || e.contains(hit) || hit.contains(e);
};
const sharesPanel = (a, b) => {
  let n = a.parentElement;
  while (n && n !== document.body) { if (n.contains(b)) return true; n = n.parentElement; }
  return false;
};

document.querySelectorAll('[data-wa-pick]').forEach(e => e.removeAttribute('data-wa-pick'));

const sends = [], seen = new Set();
for (const el of document.querySelectorAll('[aria-label],[data-icon],[data-testid]')) {
  const label = (el.getAttribute('aria-label') || '').trim();
  const icon = el.getAttribute('data-icon') || '';
  const tid = el.getAttribute('data-testid') || '';
  if (!(/^send\b/i.test(label) || /send/i.test(icon) || /send/i.test(tid))) continue;
  const t = el.closest('button,[role="button"]') || el;
  if (seen.has(t) || !vis(t)) continue;
  seen.add(t);
  const r = t.getBoundingClientRect();
  sends.push({el: t, label: t.getAttribute('aria-label') || label, icon: icon, x: r.x, y: r.y, w: r.width, h: r.height});
}
// "Send 1 selected" (media preview) wins over a plain "Send" (chat compose)
const send = sends.find(v => /selected|\d/.test(v.label || '')) || sends[sends.length - 1] || null;

const eds = [];
for (const e of document.querySelectorAll('[contenteditable="true"],[contenteditable=""]')) {
  if (!vis(e)) continue;
  const r = e.getBoundingClientRect();
  eds.push({el: e, label: e.getAttribute('aria-label') || '', ph: e.getAttribute('aria-placeholder') || '',
            x: r.x, y: r.y, w: r.width, skip: (skip && e === skip) || false, top: topmost(e)});
}
const usable = eds.filter(e => !e.skip && e.top);
let caption = usable.find(e => /caption/i.test(e.label + ' ' + e.ph)) || null;
if (!caption && send) caption = usable.find(e => sharesPanel(e.el, send.el)) || null;

if (send) send.el.setAttribute('data-wa-pick', 'send');
if (caption) caption.el.setAttribute('data-wa-pick', 'caption');
return {
  sends: sends.map(v => ({label: v.label, icon: v.icon, x: Math.round(v.x), y: Math.round(v.y)})),
  editables: eds.map(e => ({label: e.label, ph: e.ph, x: Math.round(e.x), y: Math.round(e.y),
                            w: Math.round(e.w), skipped: e.skip, topmost: e.top})),
  picked_send: send ? (send.label || send.icon) : null,
  picked_caption: caption ? (caption.label || caption.ph || '(unlabelled)') : null,
};
"""


def _analyse_preview(driver, compose_box=None):
    """
    Locate the media preview's Send button and caption box.
    Returns (send_el, caption_el, info_dict) — any of which may be None.
    """
    from selenium.webdriver.common.by import By
    info = None
    for arg in (compose_box, None):   # compose_box may have gone stale
        try:
            info = driver.execute_script(_ANALYSE_PREVIEW_JS, arg)
            break
        except Exception as exc:
            logger.debug(f"preview analysis with skip={arg is not None} failed: {exc}")
    if info is None:
        return None, None, {}
    send = driver.find_elements(By.CSS_SELECTOR, '[data-wa-pick="send"]')
    cap = driver.find_elements(By.CSS_SELECTOR, '[data-wa-pick="caption"]')
    return (send[0] if send else None), (cap[0] if cap else None), info


def _enter_caption(driver, caption, text):
    """Type `text` into the caption box; True only once it's actually in there."""
    from selenium.webdriver.common.keys import Keys
    probe = ''.join(text.split())[:12]

    def landed():
        try:
            got = driver.execute_script('return arguments[0].innerText || arguments[0].textContent || ""', caption)
            return probe in ''.join(got.split())
        except Exception:
            return False

    _paste_text(driver, caption, text)  # keeps emoji
    if landed():
        return True
    try:  # fallback: real keystrokes (BMP only); Shift+Enter so it never sends
        caption.click()
        for i, line in enumerate(''.join(c for c in text if ord(c) <= 0xFFFF).split(chr(10))):
            if i:
                caption.send_keys(Keys.SHIFT, Keys.ENTER)
            caption.send_keys(line)
        time.sleep(0.3)
    except Exception as exc:
        logger.warning(f"typing caption failed: {exc}")
    return landed()


def _wait_element_gone(driver, element, timeout=15):
    """True once this exact element is gone or hidden (the preview closed)."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            if not element.is_displayed():
                return True
        except Exception:      # stale = removed from the page = sent
            return True
        time.sleep(0.5)
    return False


def _paste_text(driver, element, text):
    """
    Insert `text` (including emoji / non-BMP chars) into a WhatsApp Web
    contenteditable. ChromeDriver's send_keys can't type emoji, so we
    dispatch a synthetic paste event WhatsApp listens for. No click — the
    caller focuses the element to avoid 'click intercepted' on overlays.
    """
    if not text:
        return
    js = """
    const el = arguments[0], txt = arguments[1];
    el.focus();
    const dt = new DataTransfer();
    dt.setData('text/plain', txt);
    el.dispatchEvent(new ClipboardEvent('paste',
        {clipboardData: dt, bubbles: true, cancelable: true}));
    """
    try:
        driver.execute_script(js, element, text)
        time.sleep(0.4)
    except Exception:
        bmp = ''.join(c for c in text if ord(c) <= 0xFFFF)  # strip emoji fallback
        element.send_keys(bmp)


def _collect_file_inputs(driver):
    """Return file inputs ordered best-first: image-accepting ones, then the rest."""
    from selenium.webdriver.common.by import By
    inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
    image_first, others = [], []
    for el in inputs:
        acc = (el.get_attribute('accept') or '').lower()
        (image_first if 'image' in acc else others).append(el)
    return image_first + others


def _open_chat(driver, chat_url):
    """(Re)open the chat and wait for its compose box. Returns the box or None."""
    driver.get(chat_url)
    box = _find(driver, _SEL['msg_input'], timeout=30)
    if box is not None:
        time.sleep(1.5)
    return box


def _upload_and_open_preview(driver, abspath, chat_url, timeout_each=8):
    """
    Try each file input until the media preview opens (Send button appears).
    WhatsApp Web has several file inputs; only the right one triggers the
    image preview. Returns the Send button element, or None if all failed.
    """
    # NOTE: never press Escape here — in current WhatsApp Web it CLOSES the open
    # chat, leaving no attach button / compose box to upload into.

    # Best-effort: open the attach (+) menu so media inputs become active
    _click(driver, _SEL['attach_btn'], timeout=3)
    time.sleep(0.8)

    inputs = _collect_file_inputs(driver)
    if not inputs:
        return None

    for inp in inputs:
        try:
            inp.send_keys(abspath)
        except Exception:
            continue
        btn = _wait_send_button(driver, timeout=timeout_each)
        if btn is not None:
            return btn
        # Reset partial state before the next input by reopening the chat
        try:
            if _open_chat(driver, chat_url) is None:
                return None
            _click(driver, _SEL['attach_btn'], timeout=3)
            time.sleep(0.8)
        except Exception:
            pass
    return None


# Any visible control that looks like "Send". WhatsApp renames its icons
# (send / wds-ic-send-filled / ...) every few months, so match loosely; the
# caller only uses this right after an attachment, when the compose box is
# empty and therefore only the media-preview overlay can show a Send control.
_VISIBLE_SEND_JS = """
const out = [];
const seen = new Set();
for (const el of document.querySelectorAll(
        '[aria-label="Send"], [data-icon*="send"], [data-testid*="send"]')) {
    const target = el.closest('button, [role="button"]') || el;
    if (seen.has(target)) continue;
    const r = target.getBoundingClientRect();
    if (r.width > 0 && r.height > 0) { seen.add(target); out.push(target); }
}
return out;
"""


def _visible_send_controls(driver):
    try:
        return driver.execute_script(_VISIBLE_SEND_JS) or []
    except Exception:
        return []


def _preview_send_button(driver):
    """The media preview's own Send button ("Send 1 selected"), or None."""
    for el in _visible_send_controls(driver):
        try:
            label = (el.get_attribute('aria-label') or '').lower()
        except Exception:
            continue
        if 'selected' in label or any(ch.isdigit() for ch in label):
            return el
    return None


def _wait_send_button(driver, timeout=20, strict=False):
    """
    Wait for a Send button. strict=True accepts only the media preview's own
    button — needed when the chat box may hold text, because then the chat's
    plain "Send" is on screen too and must not be mistaken for the preview.
    """
    end = time.time() + timeout
    while time.time() < end:
        el = _preview_send_button(driver)
        if el is not None:
            return el
        if not strict:
            controls = _visible_send_controls(driver)
            if controls:
                return controls[-1]
        time.sleep(0.5)
    return None


def _clear_composer(driver, box):
    """Empty the chat box (a leftover draft would otherwise become the caption)."""
    from selenium.webdriver.common.keys import Keys
    try:
        if (driver.execute_script('return arguments[0].innerText', box) or '').strip():
            driver.execute_script('arguments[0].focus()', box)
            box.send_keys(Keys.CONTROL, 'a')
            box.send_keys(Keys.DELETE)
            time.sleep(0.4)
    except Exception as exc:
        logger.debug(f"could not clear composer: {exc}")


def _paste_image(driver, element, path):
    """
    Fallback when no file input triggers the preview: paste the image into
    the chat box (what Ctrl+V of an image does). Doesn't depend on the attach
    menu / file-input markup, which is what WhatsApp changes most often.
    """
    import mimetypes
    with open(path, 'rb') as fh:
        b64 = base64.b64encode(fh.read()).decode('ascii')
    mime = mimetypes.guess_type(path)[0] or 'image/png'
    js = """
    const el = arguments[0], b64 = arguments[1], name = arguments[2], mime = arguments[3];
    const bin = atob(b64), arr = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
    const dt = new DataTransfer();
    dt.items.add(new File([arr], name, {type: mime}));
    el.focus();
    el.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
    """
    driver.execute_script(js, element, b64, os.path.basename(path), mime)


def _dump_debug(driver, tag):
    """
    On failure, save a screenshot + a summary of file inputs and visible
    labelled controls to media/whatsapp_debug/ so a changed WhatsApp Web
    layout can be diagnosed without guessing. Returns the file stem or None.
    """
    import json
    try:
        out_dir = os.path.join(_base_dir(), 'media', 'whatsapp_debug')
        os.makedirs(out_dir, exist_ok=True)
        stem = f"{time.strftime('%Y%m%d-%H%M%S')}-{tag}"
        driver.save_screenshot(os.path.join(out_dir, stem + '.png'))
        info = driver.execute_script("""
            const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
            return {
              url: location.href,
              file_inputs: Array.from(document.querySelectorAll('input[type=file]')).map(i => ({accept: i.accept, multiple: i.multiple})),
              visible_controls: Array.from(document.querySelectorAll('[aria-label],[data-icon]')).filter(vis).slice(0, 80).map(e => ({
                tag: e.tagName, label: e.getAttribute('aria-label'), icon: e.getAttribute('data-icon'), role: e.getAttribute('role')})),
              contenteditables: Array.from(document.querySelectorAll('[contenteditable=true]')).filter(vis).map(e => ({
                label: e.getAttribute('aria-label'), placeholder: e.getAttribute('aria-placeholder')})),
            };""")
        with open(os.path.join(out_dir, stem + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(info, fh, indent=2, ensure_ascii=False)
        return stem
    except Exception as exc:
        logger.warning(f"could not write WhatsApp debug dump: {exc}")
        return None


def _wait_no_send_control(driver, timeout=15):
    """True once no Send control is visible any more (= preview closed / sent)."""
    end = time.time() + timeout
    while time.time() < end:
        if not _visible_send_controls(driver):
            return True
        time.sleep(0.5)
    return False


def _wait_gone(driver, css, timeout=15):
    """Return True once the element matching `css` is gone/hidden (= sent)."""
    from selenium.webdriver.common.by import By
    end = time.time() + timeout
    while time.time() < end:
        els = driver.find_elements(By.CSS_SELECTOR, css)
        if not els or not any(e.is_displayed() for e in els):
            return True
        time.sleep(0.5)
    return False


def send_wa_message(phone, text, image_path=None):
    """
    Open WhatsApp Web chat for `phone` and send `text` (and optional image).
    Returns (success: bool, error: str|None).
    Blocking; uses a re-entrant lock — safe for concurrent Django requests.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains

    with _lock:
        try:
            driver = _get_driver()
            clean = phone.lstrip('+').replace(' ', '').replace('-', '')

            # ── With image: attach file → caption → send ──────────────────────
            if image_path and os.path.exists(image_path):
                chat_url = f"https://web.whatsapp.com/send?phone={clean}"
                compose_box = _open_chat(driver, chat_url)
                if compose_box is None:
                    return False, 'Chat did not load — is WhatsApp Web logged in?'

                # Paste the picture into the chat box. This opens the normal PHOTO
                # preview (with a caption box). Do NOT go through the attach-menu file
                # input instead: WhatsApp Web's image input there is the "New sticker"
                # one, which sends the picture as a sticker — no caption possible.
                send_btn = None
                try:
                    _clear_composer(driver, compose_box)
                    _paste_image(driver, compose_box, os.path.abspath(image_path))
                    send_btn = _wait_send_button(driver, timeout=15, strict=True)
                except Exception as exc:
                    logger.warning(f"pasting the image failed: {exc}")
                if send_btn is None:
                    stem = _dump_debug(driver, 'image-preview-failed')
                    hint = f' (diagnostics saved: media/whatsapp_debug/{stem})' if stem else ''
                    return False, 'Image preview did not open — WhatsApp Web rejected the picture or its layout changed' + hint + '.'

                # Caption + Send must come from the preview itself, never from
                # the chat compose box behind it.
                send_btn, caption, info = _analyse_preview(driver, compose_box)
                for _ in range(8):   # the caption box can render a moment after the preview
                    if caption is not None or not text:
                        break
                    time.sleep(0.5)
                    send_btn, caption, info = _analyse_preview(driver, compose_box)
                if send_btn is None:
                    send_btn = _wait_send_button(driver, timeout=5)
                logger.info(f"WhatsApp preview: send={info.get('picked_send')!r} caption={info.get('picked_caption')!r}")

                caption_ok = False
                if text and caption is not None:
                    caption_ok = _enter_caption(driver, caption, text)
                    time.sleep(0.5)
                    fresh_send, _, _ = _analyse_preview(driver, compose_box)
                    send_btn = fresh_send or send_btn
                if text and not caption_ok:
                    # Send the picture on its own, then the text — never type into
                    # the chat box, which would fire the text and strand the picture.
                    _dump_debug(driver, 'caption-not-entered')

                if send_btn is None:
                    stem = _dump_debug(driver, 'send-button-missing')
                    hint = f' (diagnostics: media/whatsapp_debug/{stem})' if stem else ''
                    return False, 'Could not find the picture\'s Send button' + hint + '.'

                try:
                    send_btn.click()
                except Exception:
                    try:
                        driver.execute_script("arguments[0].click();", send_btn)
                    except Exception as exc:
                        return False, f'Could not click Send on the picture: {exc}'

                # VERIFY: that exact Send button disappears once the picture goes.
                if not _wait_element_gone(driver, send_btn, timeout=20):
                    stem = _dump_debug(driver, 'image-send-unconfirmed')
                    hint = f' (diagnostics: media/whatsapp_debug/{stem})' if stem else ''
                    return False, 'Picture send not confirmed - the preview is still open after clicking Send' + hint + '.'

                # Caption could not be attached: deliver the text as its own
                # message so nothing is silently dropped.
                if text and not caption_ok:
                    time.sleep(2)
                    ok, err = send_wa_message(phone, text)
                    if not ok:
                        return False, f'Picture sent, but the text message failed: {err}'

                time.sleep(1.5)
                return True, None

            # ── Text only: URL pre-fills text (handles emoji natively) ────────
            url = (
                f"https://web.whatsapp.com/send?phone={clean}"
                f"&text={urllib.parse.quote(text or '')}"
            )
            driver.get(url)

            msg_box = _find(driver, _SEL['msg_input'], timeout=30)
            if msg_box is None:
                return False, 'Message input not found — is WhatsApp Web logged in?'
            time.sleep(1.0)

            if not _click(driver, _SEL['send_btn'], timeout=8):
                msg_box.send_keys(Keys.ENTER)
            time.sleep(1.5)
            return True, None

        except Exception as exc:
            logger.error(f"WhatsApp Web send to {phone} failed: {exc}")
            return False, str(exc)
