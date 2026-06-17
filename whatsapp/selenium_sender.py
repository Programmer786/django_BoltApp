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
_lock = threading.Lock()   # one Selenium operation at a time

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
    """Project root — always writable (Django process runs from here)."""
    try:
        from django.conf import settings
        return str(settings.BASE_DIR)
    except Exception:
        return os.getcwd()


def _profile_dir():
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
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=1280,900')
    opts.add_argument('--disable-extensions')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option('excludeSwitches', ['enable-automation'])
    opts.add_experimental_option('useAutomationExtension', False)

    # VPS Linux — no display → headless. QR captured as screenshot and shown in web UI.
    if platform.system() != 'Windows':
        opts.add_argument('--headless=new')
        opts.add_argument('--remote-debugging-port=9222')

    return opts


def _apply_stealth(driver):
    try:
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        })
    except Exception:
        pass


def _build_driver():
    from selenium import webdriver

    base = _base_dir()
    profile = _profile_dir()
    wdm_cache = os.path.join(base, '.wdm')       # /var/www/django_project/.wdm
    sel_cache = os.path.join(base, '.selenium')  # /var/www/django_project/.selenium

    os.makedirs(profile, exist_ok=True)
    os.makedirs(wdm_cache, exist_ok=True)
    os.makedirs(sel_cache, exist_ok=True)

    # Pin BOTH driver managers to the project dir — never HOME (/var/www)
    # SE_CACHE_PATH → selenium-manager (selenium 4.6+)
    # WDM_LOCAL / path arg → webdriver-manager
    os.environ['SE_CACHE_PATH'] = sel_cache
    os.environ['WDM_LOCAL'] = '0'  # disable local-dir mode so path= arg takes effect

    opts = _chrome_opts()
    last_err = None

    # ── Attempt 1: selenium-manager (bundled with selenium 4.6+) ──────────────
    # Uses SE_CACHE_PATH — writes to project dir, not HOME.
    try:
        driver = webdriver.Chrome(options=opts)
        _apply_stealth(driver)
        driver.get('https://web.whatsapp.com')
        time.sleep(5)
        return driver
    except Exception as exc:
        last_err = exc
        logger.warning(f"selenium-manager attempt failed: {exc}")

    # ── Attempt 2: webdriver-manager with explicit project-dir cache ──────────
    # path= forces the .wdm download into the project, not /var/www/.wdm.
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager(path=wdm_cache).install()),
            options=opts,
        )
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
        qr_el = _find(driver, _SEL['qr'], timeout=25)
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
