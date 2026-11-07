"""
Fixed answers for the common non-number messages, in English, Arabic and Urdu.

These are instant and always correct, so the small free AI model is only used
for unusual messages.
"""
import re

_URDU_CHARS = set('ٹڈڑںےۓہھگکپچژ')


def language(text):
    """'ur', 'ar' or 'en' from the script used in the message."""
    if any('؀' <= ch <= 'ۿ' or 'ݐ' <= ch <= 'ݿ' for ch in text):
        return 'ur' if any(ch in _URDU_CHARS for ch in text) else 'ar'
    return 'en'


_INTENTS = [
    ('price', r'\b(price|prices|cost|fee|fees|charge|charges|rate|rates|quotation|quote|booking|book|register|enrol+)\b'
              r'|سعر|اسعار|أسعار|تكلفة|رسوم|حجز|تسجيل|قیمت|فیس|ریٹ|بکنگ'),
    ('lost', r'\b(lost|missing|stolen|damaged|replace|replacement|renew|renewal|reissue|duplicate)\b'
             r'|مفقود|ضائع|فقدت|تجديد|بدل|گم|کھو|تجدید'),
    ('contact', r'\b(contact|phone|call|office|address|location|email|where are you|working hours|timing)\b'
                r'|تواصل|اتصال|عنوان|موقع|مكتب|رابطہ|دفتر|پتہ'),
    ('verify', r'\b(verify|verification|check|valid|validity|genuine|fake|legit|authentic|expire|expiry|expired)\b'
               r'|تحقق|التحقق|صلاحية|صحة|مزور|شهادة|بطاقة|تصدیق|چیک|اصلی|جعلی|سرٹیفکیٹ|کارڈ'),
    ('greeting', r'^\s*(hi+|hello+|hey+|salam|salaam|assalam\w*|good (morning|evening|afternoon)|thanks?|thank you)\b'
                 r'|السلام|سلام|مرحبا|اهلا|أهلا|شكرا|شکریہ'),
]
_COMPILED = [(name, re.compile(rx, re.IGNORECASE)) for name, rx in _INTENTS]

_TEXT = {
    'help': {
        'en': 'Please send the *card, certificate, sticker or report number* exactly as printed '
              '(for example *905951*) and we will reply with the verified details.',
        'ar': 'يرجى إرسال *رقم البطاقة أو الشهادة أو الملصق أو التقرير* كما هو مطبوع '
              '(مثال: *905951*) وسنرسل لك التفاصيل الموثقة.',
        'ur': 'براہ کرم *کارڈ، سرٹیفکیٹ، اسٹیکر یا رپورٹ نمبر* بالکل ویسا ہی بھیجیں جیسا چھپا ہے '
              '(مثال: *905951*)، ہم تصدیق شدہ تفصیلات بھیج دیں گے۔',
    },
    'greeting': {
        'en': '👋 Welcome to *{brand}* verification.',
        'ar': '👋 أهلاً بك في خدمة التحقق من *{brand}*.',
        'ur': '👋 *{brand}* تصدیقی سروس میں خوش آمدید۔',
    },
    'office': {
        'en': 'This number only verifies documents. For prices, bookings, renewals or lost cards, please contact our office{contact}.',
        'ar': 'هذا الرقم مخصص للتحقق من المستندات فقط. للأسعار أو الحجز أو التجديد أو البطاقات المفقودة، يرجى التواصل مع مكتبنا{contact}.',
        'ur': 'یہ نمبر صرف دستاویزات کی تصدیق کے لیے ہے۔ قیمت، بکنگ، تجدید یا گم شدہ کارڈ کے لیے ہمارے دفتر سے رابطہ کریں{contact}۔',
    },
}


def detect(text):
    for name, rx in _COMPILED:
        if rx.search(text or ''):
            return name
    return None


def reply_for(intent, text, brand, office_contact=''):
    lang = language(text)
    contact = f': {office_contact}' if office_contact else ''
    help_text = _TEXT['help'][lang]
    if intent in ('price', 'lost', 'contact'):
        return _TEXT['office'][lang].format(contact=contact) + '\n\n' + help_text
    if intent == 'greeting':
        return _TEXT['greeting'][lang].format(brand=brand) + '\n\n' + help_text
    return help_text  # 'verify' and fallback


def help_text(text):
    return _TEXT['help'][language(text)]
