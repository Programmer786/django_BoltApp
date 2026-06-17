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


def _is_alive(driver):
    try:
        _ = driver.current_url
        return True
    except Exception:
        return False


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

    return opts


def _apply_stealth(driver):
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


def close_driver():
    global _driver
    with _lock:
        if _driver:
            try:
                _driver.quit()
            except Exception:
                pass
            _driver = None


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
            # Fast check: are we already logged in?
            logged_in_el = _find(driver, _SEL['logged_in'], timeout=6)
            if logged_in_el:
                return {'available': True, 'logged_in': True, 'qr_image': None, 'error': None}

            # Wait for QR canvas
            qr_b64 = None
            qr_el = _find(driver, _SEL['qr'], timeout=15)
            if qr_el:
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


def send_wa_message(phone, text):
    """
    Open WhatsApp Web chat for `phone` and send `text`.
    Returns (success: bool, error: str|None).
    This is blocking and uses a lock — safe for concurrent Django requests.
    """
    with _lock:
        try:
            driver = _get_driver()
            clean = phone.lstrip('+').replace(' ', '').replace('-', '')
            url = (
                f"https://web.whatsapp.com/send?phone={clean}"
                f"&text={urllib.parse.quote(text or '')}"
            )
            driver.get(url)

            # Wait for message input
            msg_box = _find(driver, _SEL['msg_input'], timeout=30)
            if msg_box is None:
                return False, 'Message input not found — is WhatsApp Web logged in?'

            time.sleep(1.0)

            # Click Send button
            sent = _click(driver, _SEL['send_btn'], timeout=8)
            if not sent:
                # Fallback: press Enter
                from selenium.webdriver.common.keys import Keys
                msg_box.send_keys(Keys.ENTER)

            time.sleep(1.5)
            return True, None

        except Exception as exc:
            logger.error(f"WhatsApp Web send to {phone} failed: {exc}")
            return False, str(exc)
