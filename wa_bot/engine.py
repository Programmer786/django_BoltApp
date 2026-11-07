"""Decide the reply to one incoming WhatsApp message.

Order: record numbers (exact database lookup) -> common questions (fixed
answers, EN/AR/UR) -> free local AI for anything else -> help message.
"""
import re
import time
from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from . import ai, intents
from .lookup import extract_numbers, find, format_found, format_not_found
from .models import BotConversation, BotSettings


@dataclass
class Reply:
    text: str
    result: str
    matched_type: str = ''
    matched_number: str = ''
    used_ai: bool = False


def lookups_last_hour(phone):
    since = timezone.now() - timedelta(hours=1)
    return BotConversation.objects.filter(
        phone=phone, created_at__gte=since, result__in=('found', 'not_found')
    ).count()


def build_reply(text, phone='', settings=None, check_rate_limit=True):
    settings = settings or BotSettings.load()
    brand = settings.brand

    if not settings.enabled:
        return Reply('', 'disabled')

    numbers = extract_numbers(text)
    if numbers:
        if check_rate_limit and lookups_last_hour(phone) >= settings.max_lookups_per_hour:
            return Reply(settings.rate_limited_text, 'rate_limited')
        parts, found_any, first = [], False, None
        for number in numbers:
            match = find(number)
            if match:
                found_any = True
                first = first or match
                parts.append(format_found(match, brand))
            else:
                parts.append(format_not_found(number, settings.not_found_text))
        return Reply(
            '\n\n────────────\n\n'.join(parts),
            'found' if found_any else 'not_found',
            matched_type=first.label if first else '',
            matched_number=first.number if first else numbers[0],
        )

    text = text or ''
    lang = intents.language(text)
    # English welcome is editable on the page; Arabic/Urdu use built-in text.
    welcome = (settings.welcome_text.replace('{brand}', brand) if lang == 'en'
               else intents.reply_for('greeting', text, brand))

    intent = intents.detect(text)
    if intent:
        return Reply(intents.reply_for(intent, text, brand, settings.office_contact), 'chat')

    if settings.use_ai and ai.available() and len(text.strip()) > 3:
        answer = ai.chat_reply(text, brand)
        if answer and not _REFUSAL.search(answer):
            return Reply(answer + '\n\n' + intents.help_text(text), 'chat', used_ai=True)
    return Reply(welcome, 'chat')


# Small models sometimes answer with an unhelpful refusal; send help instead.
_REFUSAL = re.compile(r"can['’]?t assist|cannot assist|can['’]?t help|cannot help|unable to (help|assist)|as an ai", re.I)


def handle_incoming(phone, name, text):
    """Build the reply and log the conversation. Returns the Reply."""
    started = time.monotonic()
    reply = build_reply(text, phone=phone)
    BotConversation.objects.create(
        phone=phone[:40], name=(name or '')[:120], message=(text or '')[:4000],
        reply=reply.text, result=reply.result, matched_type=reply.matched_type,
        matched_number=reply.matched_number[:120], used_ai=reply.used_ai,
        response_ms=int((time.monotonic() - started) * 1000),
    )
    return reply
