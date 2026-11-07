"""
Free local AI (Ollama) for general chat only - never for verification answers.

The model never sees the database. If Ollama is missing, slow or errors, the
caller falls back to the fixed welcome message, so the bot always answers.
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv('OLLAMA_URL', '')  # empty = AI disabled
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:0.5b')
TIMEOUT_S = float(os.getenv('OLLAMA_TIMEOUT', '45'))

SYSTEM_PROMPT = (
    "You are the WhatsApp assistant of {brand}, a company that issues operator cards, "
    "training certificates, equipment inspection certificates, NDT reports and calibration "
    "certificates in Saudi Arabia. Your ONLY job is to help people verify a document.\n"
    "Rules:\n"
    "- To verify, the person must send the card/certificate/sticker/report number exactly as printed.\n"
    "- You have NO access to records. Never invent names, numbers, dates or statuses.\n"
    "- Never claim a document is valid or invalid.\n"
    "- For anything else (prices, bookings, complaints) tell them to contact the office.\n"
    "- Reply in the same language as the user (English, Arabic, Urdu or Hindi).\n"
    "- Keep the reply under 60 words. No markdown headings."
)


# Worked examples: small models follow examples far better than rules.
FEW_SHOT = [
    {'role': 'user', 'content': 'How do I check my card?'},
    {'role': 'assistant', 'content': 'Please send your card number exactly as it is printed on the card, '
                                     'for example 905951, and I will reply with the verified details.'},
    {'role': 'user', 'content': 'How much does training cost?'},
    {'role': 'assistant', 'content': 'I can only help with verifying documents. For prices and bookings, '
                                     'please contact our office.'},
    {'role': 'user', 'content': 'السلام عليكم، كيف أتحقق من الشهادة؟'},
    {'role': 'assistant', 'content': 'وعليكم السلام. أرسل رقم الشهادة أو رقم الملصق كما هو مطبوع، '
                                     'وسنرسل لك التفاصيل الموثقة.'},
    {'role': 'user', 'content': 'is my certificate valid?'},
    {'role': 'assistant', 'content': 'Please send the certificate number exactly as printed and I will '
                                     'check it for you.'},
]


def available():
    return bool(OLLAMA_URL)


def chat_reply(message, brand):
    """Short reply from the local model, or None on any failure."""
    if not OLLAMA_URL:
        return None
    try:
        r = requests.post(
            f'{OLLAMA_URL.rstrip("/")}/api/chat',
            json={
                'model': OLLAMA_MODEL,
                'stream': False,
                'keep_alive': '60m',
                'options': {'temperature': 0.3, 'num_predict': 120, 'num_ctx': 1024},
                'messages': [
                    {'role': 'system', 'content': SYSTEM_PROMPT.format(brand=brand)},
                    *FEW_SHOT,
                    {'role': 'user', 'content': message[:500]},
                ],
            },
            timeout=TIMEOUT_S,
        )
        r.raise_for_status()
        text = (r.json().get('message') or {}).get('content', '').strip()
        return text or None
    except (requests.RequestException, ValueError) as e:
        logger.warning('Ollama chat failed: %s', e)
        return None
