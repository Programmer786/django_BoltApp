"""
Find a verifiable record by the number a customer sends on WhatsApp, and
format the reply.

No AI here on purpose: a verification answer must be exactly what is in the
database. Only exact (case-insensitive) matches on approved, active records
count, so sending "1" or part of a number reveals nothing.
"""
import re
from dataclasses import dataclass
from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from django.db.models import Q

from authentication.models import Note
from calibration.models import Calibration
from cards.models import Card
from certificates.models import Certificate
from ndt.models import NonDestructiveTesting
from training.models import Training

# Same visibility rule as the public verification page.
VERIFIABLE = dict(isApprove=True, isActive=True, isReject=False, isCancel=False, isHold=False)

# A "number" is 4-40 chars of letters/digits/dashes/slashes containing a digit.
_TOKEN_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9\-/]{2,38}[A-Za-z0-9]')
MAX_NUMBERS_PER_MESSAGE = 3

# (label, note type, model, fields searched in order)
SOURCES = [
    ('Operator Card', 'card', Card, ['card_no']),
    ('Inspection Certificate', 'certificate', Certificate, ['cert_no', 'sticker_no']),
    ('Training Certificate', 'training', Training, ['cert_no', 'card_no']),
    ('NDT Report', 'ndt', NonDestructiveTesting, ['report_no']),
    ('Calibration Certificate', 'calibration', Calibration, ['cert_no', 'sticker_no']),
]

# Fields shown per type: (label, attribute). Iqama numbers are always masked.
DISPLAY = {
    Card: [('Card No', 'card_no'), ('Card Type', 'trade_or_type'), ('Name', 'operator_name'),
           ('Iqama No', 'iqama_no'), ('Company', 'company_name'),
           ('Issue Date', 'issue_date'), ('Expiry Date', 'expiry_date')],
    Certificate: [('Certificate No', 'cert_no'), ('Sticker No', 'sticker_no'),
                  ('Equipment', 'equipment_type'), ('Equipment Serial No', 'eq_serial_no'),
                  ('Plate No', 'plate_no'), ('Manufacturer', 'manufacturer'),
                  ('Company', 'company_name'), ('Inspection Date', 'inspection_date'),
                  ('Expiry Date', 'expiry_date'), ('Inspected By', 'inspected_by')],
    Training: [('Certificate No', 'cert_no'), ('Card No', 'card_no'), ('Name', 'name_of_trainee'),
               ('Iqama No', 'iqama_no'), ('Company', 'company_name'), ('Trade', 'trade'),
               ('Issue Date', 'issue_date'), ('Expiry Date', 'expiry_date'),
               ('Trainer / Assessed By', 'assessed_by_resource_person')],
    NonDestructiveTesting: [('Report No', 'report_no'), ('ID / Serial No', 'id_serial_no'),
                            ('Inspection Type', 'inspection_type'), ('Material', 'material'),
                            ('Company', 'company_name'), ('Inspection Date', 'inspection_date'),
                            ('Expiry Date', 'expiry_date'), ('Inspected By', 'inspected_by')],
    Calibration: [('Certificate No', 'cert_no'), ('Sticker No', 'sticker_no'),
                  ('Equipment', 'equipment_name'), ('Company', 'company_name'),
                  ('Calibration Date', 'date_of_calibration'), ('Expiry Date', 'expiry_date'),
                  ('Technician', 'technician')],
}
DATE_ATTRS = {'issue_date', 'expiry_date', 'inspection_date', 'date_of_calibration'}
_DATE_FORMATS = ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d', '%d-%b-%Y', '%d-%b-%y')


@dataclass
class Match:
    label: str
    note_type: str
    record: object
    number: str


def extract_numbers(text):
    """Candidate record numbers in a message (must contain a digit)."""
    seen, out = set(), []
    for tok in _TOKEN_RE.findall(text or ''):
        if any(c.isdigit() for c in tok) and tok.lower() not in seen:
            seen.add(tok.lower())
            out.append(tok)
    return out[:MAX_NUMBERS_PER_MESSAGE]


def find(number):
    """Exact, case-insensitive match on any verifiable record, or None."""
    number = number.strip()
    for label, note_type, model, fields in SOURCES:
        q = Q()
        for f in fields:
            q |= Q(**{f'{f}__iexact': number})
        rec = model.objects.filter(q, **VERIFIABLE).select_related('user').first()
        if rec:
            if model is Card and rec.card_type:
                label = rec.card_type  # "Operator Card", "Training Card", "Welder Card"
            return Match(label, note_type, rec, number)
    return None


def parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or '').strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def mask_iqama(value):
    digits = str(value or '').strip()
    if len(digits) <= 4:
        return '****' if digits else ''
    return '*' * (len(digits) - 4) + digits[-4:]


def validity(record, today=None):
    """('valid'|'expired'|'unknown', human text)."""
    exp = parse_date(getattr(record, 'expiry_date', None))
    if not exp:
        return 'unknown', 'Expiry date not recorded'
    today = today or date.today()
    if exp < today:
        return 'expired', f'EXPIRED on {exp:%d-%m-%Y}'
    delta = relativedelta(exp, today)
    months = delta.years * 12 + delta.months
    if months == 0:
        return 'valid', f'Valid - expires in {delta.days} day(s)'
    return 'valid', f'Valid - {months} month(s) remaining'


def _value(record, attr):
    if attr == 'trade_or_type':
        return record.trade or record.card_type
    value = getattr(record, attr, None)
    if attr == 'iqama_no':
        return mask_iqama(value)
    if attr in DATE_ATTRS:
        d = parse_date(value)
        return d.strftime('%d-%m-%Y') if d else value
    return value


def format_found(match, brand):
    rec = match.record
    state, valid_text = validity(rec)
    icon = '✅' if state == 'valid' else ('⚠️' if state == 'expired' else 'ℹ️')
    lines = [f'{icon} *VERIFIED - {match.label}*', '']
    for label, attr in DISPLAY[type(rec)]:
        v = _value(rec, attr)
        if v not in (None, ''):
            text = ' '.join(str(v).split())
            lines.append(f'*{label}:* {text[:200]}')
    lines += ['', f'*Status:* {valid_text}']
    note = Note.objects.filter(type=match.note_type).values_list('note', flat=True).first()
    if note:
        lines += ['', f'_{" ".join(note.split())[:300]}_']
    lines += ['', f'_Verified by {brand}_']
    return '\n'.join(lines)


def format_not_found(number, template):
    return template.replace('{number}', number)
