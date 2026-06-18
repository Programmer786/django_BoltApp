"""
WhatsApp Business Cloud API (Meta / Graph API) sender.

Unlike Twilio, images can be sent WITHOUT a public HTTPS URL — we upload the
file to Meta's /media endpoint to get a media ID, then send by that ID.

Note on Meta's messaging rules:
- Free-form text/image messages can only be sent inside the 24-hour customer
  service window (i.e. after the recipient messaged your number). Outside that
  window only approved *template* messages are delivered.
- A test number can only message recipients added/verified in the Meta dashboard.
"""
import logging
import mimetypes
import os

from django.conf import settings

logger = logging.getLogger(__name__)


def _config():
    token = getattr(settings, 'META_WA_ACCESS_TOKEN', '')
    phone_id = getattr(settings, 'META_WA_PHONE_NUMBER_ID', '')
    version = getattr(settings, 'META_WA_API_VERSION', 'v21.0')
    return token, phone_id, version


def is_configured():
    token, phone_id, _ = _config()
    return bool(token and phone_id)


def _clean_phone(phone):
    return phone.lstrip('+').replace(' ', '').replace('-', '')


def _upload_media(base, headers, image_path):
    """Upload an image to Meta and return its media_id (or raise)."""
    import requests
    mime = mimetypes.guess_type(image_path)[0] or 'image/jpeg'
    with open(image_path, 'rb') as fh:
        files = {'file': (os.path.basename(image_path), fh, mime)}
        data = {'messaging_product': 'whatsapp', 'type': mime}
        resp = requests.post(f'{base}/media', headers=headers, data=data, files=files, timeout=60)
    payload = resp.json()
    if resp.status_code >= 400 or 'id' not in payload:
        err = payload.get('error', {}).get('message', resp.text)
        raise RuntimeError(f'Media upload failed: {err}')
    return payload['id']


def send_meta_message(phone, text, image_path=None, mode='text',
                      template_name=None, template_lang='en_US', template_vars=None):
    """
    Send a WhatsApp message via Meta Cloud API.
    `template_vars` is an optional list of strings mapped to body {{1}}, {{2}}…
    Returns (success: bool, error: str|None, message_id: str|None).
    """
    try:
        import requests
    except ImportError:
        return False, 'requests library not installed — run: pip install requests', None

    token, phone_id, version = _config()
    if not token or not phone_id:
        return False, 'Meta Cloud API not configured (set META_WA_ACCESS_TOKEN and META_WA_PHONE_NUMBER_ID in .env).', None

    to = _clean_phone(phone)
    base = f'https://graph.facebook.com/{version}/{phone_id}'
    auth_headers = {'Authorization': f'Bearer {token}'}
    json_headers = {**auth_headers, 'Content-Type': 'application/json'}

    try:
        # ── Template message ──────────────────────────────────────────────
        if mode == 'template':
            name = (template_name or '').strip() or 'hello_world'
            template_obj = {
                'name': name,
                'language': {'code': template_lang or 'en_US'},
            }
            # Map variable values to body parameters {{1}}, {{2}}…
            clean_vars = [v for v in (template_vars or []) if v not in (None, '')]
            if clean_vars:
                template_obj['components'] = [{
                    'type': 'body',
                    'parameters': [{'type': 'text', 'text': str(v)} for v in clean_vars],
                }]
            payload = {
                'messaging_product': 'whatsapp',
                'to': to,
                'type': 'template',
                'template': template_obj,
            }

        # ── Image message (upload file → send by media id) ────────────────
        elif image_path and os.path.exists(image_path):
            media_id = _upload_media(base, auth_headers, image_path)
            image_obj = {'id': media_id}
            if text:
                image_obj['caption'] = text
            payload = {
                'messaging_product': 'whatsapp',
                'to': to,
                'type': 'image',
                'image': image_obj,
            }

        # ── Plain text message ────────────────────────────────────────────
        else:
            payload = {
                'messaging_product': 'whatsapp',
                'to': to,
                'type': 'text',
                'text': {'body': text or ''},
            }

        resp = requests.post(f'{base}/messages', headers=json_headers, json=payload, timeout=60)
        data = resp.json()

        if resp.status_code >= 400 or 'error' in data:
            err = data.get('error', {}).get('message', resp.text)
            logger.error(f"Meta Cloud API send to {phone} failed: {err}")
            return False, err, None

        msg_id = None
        if data.get('messages'):
            msg_id = data['messages'][0].get('id')
        return True, None, msg_id

    except Exception as exc:
        logger.error(f"Meta Cloud API send to {phone} failed: {exc}")
        return False, str(exc), None
