"""
DEMS Chatbot — Multi-intent NLP engine (Upgraded v3)
Supports Arabic + English. Extracts multiple intents from one message.

Two modes:
  1. KEYWORD mode (default) — pure Python, no API key needed
  2. OPENAI mode — set OPENAI_API_KEY in .env for GPT-4o powered answers
     that handle free-form questions not covered by keyword rules.

The system always tries keyword matching first. If no intent is found AND
OpenAI is configured, it falls back to GPT-4o with a system prompt that
constrains it to election-related topics only.
"""

import re  #reglular expressions for keyword matching
import logging  #record errors in bot in file
from django.conf import settings #byshouf settings.py 3shan OpenAI key 

logger = logging.getLogger(__name__)

# ─── Intent definitions ──────────────────────────────────────────────────────
INTENTS = [
    {
        "name": "election_date",
        "keywords_en": ["date", "when", "election date", "when is", "schedule", "deadline", "period", "time"],
        "keywords_ar": ["موعد", "متى", "تاريخ", "الانتخابات متى", "جدول", "وقت", "فترة"],
        "answer_en": (
            "📅 <strong>Election Schedule:</strong><br>"
            "The Egyptian Parliamentary Elections are currently <strong>open</strong>.<br>"
            "• Voting is available online through DEMS 24/7.<br>"
            "• Check the homepage banner for live election status.<br>"
            "• For official dates, visit the <em>National Electoral Commission</em> website."
        ),
        "answer_ar": (
            "📅 <strong>موعد الانتخابات:</strong><br>"
            "الانتخابات البرلمانية المصرية <strong>مفتوحة</strong> حالياً.<br>"
            "• التصويت متاح إلكترونياً عبر DEMS على مدار الساعة.<br>"
            "• راجع الشعار في الصفحة الرئيسية لمعرفة حالة الانتخابات الآن.<br>"
            "• للتواريخ الرسمية، تفضل بزيارة موقع <em>الهيئة الوطنية للانتخابات</em>."
        ),
    },

    {
        "name": "registration",
        "keywords_en": ["register", "registration", "sign up", "enroll", "how to join", "new voter"],
        "keywords_ar": ["تسجيل", "كيف اسجل", "سجل", "انضم", "اشترك", "ناخب جديد", "تسجيل جديد"],
        "answer_en": (
            "📋 <strong>Registration:</strong><br>"
            "1️⃣ You must be registered in the national voter database.<br>"
            "2️⃣ Registration is handled by the <em>National Electoral Commission</em>.<br>"
            "3️⃣ Bring your National ID to your local election office to register.<br>"
            "✅ Once registered, you can log into DEMS with your 14-digit ID."
        ),
        "answer_ar": (
            "📋 <strong>التسجيل:</strong><br>"
            "1️⃣ يجب أن تكون مسجلاً في قاعدة بيانات الناخبين الوطنية.<br>"
            "2️⃣ يتولى التسجيل <em>الهيئة الوطنية للانتخابات</em>.<br>"
            "3️⃣ أحضر بطاقة هويتك إلى مكتب الانتخابات المحلي.<br>"
            "✅ بعد التسجيل، يمكنك الدخول إلى DEMS برقم هويتك المكون من 14 رقماً."
        ),
    },
    {
        "name": "voting",
        "keywords_en": ["vote", "voting", "cast", "how to vote", "ballot", "select candidate", "submit vote"],
        "keywords_ar": ["صوت", "تصويت", "كيف اصوت", "ازاي اصوت", "الإدلاء بالصوت", "اختيار مرشح", "ادلي بصوتي"],
        "answer_en": (
            "🗳️ <strong>How to Vote:</strong><br>"
            "1️⃣ Go to the <a href='/login/'>Login page</a><br>"
            "2️⃣ Enter your 14-digit National ID<br>"
            "3️⃣ Complete face biometric verification<br>"
            "4️⃣ Select your preferred candidate from your district<br>"
            "5️⃣ Confirm your vote — it's permanent ✅"
        ),
        "answer_ar": (
            "🗳️ <strong>كيفية التصويت:</strong><br>"
            "1️⃣ اذهب إلى <a href='/login/'>صفحة الدخول</a><br>"
            "2️⃣ أدخل رقم هويتك الوطنية المكون من 14 رقماً<br>"
            "3️⃣ أكمل التحقق ببصمة الوجه<br>"
            "4️⃣ اختر مرشحك المفضل من دائرتك<br>"
            "5️⃣ أكد صوتك — هو نهائي ✅"
        ),
    },
    {
        "name": "face_recognition",
        "keywords_en": ["face", "camera", "biometric", "face scan", "face recognition", "selfie", "photo", "face id"],
        "keywords_ar": ["وجه", "كاميرا", "بصمة وجه", "التعرف على الوجه", "سيلفي", "صورة", "بصمة"],
        "answer_en": (
            "🎭 <strong>Face Biometric Verification:</strong><br>"
            "• Your face is scanned via camera to confirm your identity.<br>"
            "• <strong>First time?</strong> Your face embedding is saved to the database.<br>"
            "• <strong>Returning?</strong> The system compares your live face to the stored record.<br>"
            "• ⚠️ No photos are stored — only a 128-number mathematical vector.<br>"
            "• Works from <em>any device</em> — data is stored in the central database."
        ),
        "answer_ar": (
            "🎭 <strong>التحقق ببصمة الوجه:</strong><br>"
            "• يتم مسح وجهك عبر الكاميرا للتحقق من هويتك.<br>"
            "• <strong>لأول مرة؟</strong> يتم حفظ بصمة وجهك في قاعدة البيانات.<br>"
            "• <strong>عائد؟</strong> يقارن النظام وجهك الحي بالسجل المحفوظ.<br>"
            "• ⚠️ لا يتم تخزين الصور — فقط متجه رياضي من 128 رقماً.<br>"
            "• يعمل من <em>أي جهاز</em> — البيانات محفوظة في قاعدة البيانات المركزية."
        ),
    },
    {
        "name": "eligibility",
        "keywords_en": ["eligible", "who can vote", "requirements", "age", "citizen", "qualify", "allowed"],
        "keywords_ar": ["من يحق له", "الأهلية", "الشروط", "العمر", "مواطن", "مؤهل", "يحق"],
        "answer_en": (
            "✅ <strong>Voting Eligibility:</strong><br>"
            "• Egyptian citizen<br>"
            "• 18 years or older<br>"
            "• Registered in the national voter database<br>"
            "• Hold a valid 14-digit National ID"
        ),
        "answer_ar": (
            "✅ <strong>شروط التصويت:</strong><br>"
            "• مواطن مصري<br>"
            "• 18 سنة أو أكثر<br>"
            "• مسجل في قاعدة بيانات الناخبين الوطنية<br>"
            "• تمتلك بطاقة هوية وطنية سارية من 14 رقماً"
        ),
    },
    {
        "name": "results",
        "keywords_en": ["result", "results", "live result", "count", "tally", "winner", "who won", "score"],
        "keywords_ar": ["نتيجة", "نتائج", "نتائج مباشرة", "فرز", "فائز", "من فاز", "احصاء"],
        "answer_en": (
            "📊 <strong>Election Results:</strong><br>"
            "Live results are available at the <a href='/results/'>Results page</a>.<br>"
            "Results update in real-time as votes are counted."
        ),
        "answer_ar": (
            "📊 <strong>نتائج الانتخابات:</strong><br>"
            "النتائج المباشرة متاحة في <a href='/results/'>صفحة النتائج</a>.<br>"
            "تتحدث النتائج في الوقت الفعلي مع تقدم عملية الفرز."
        ),
    },
    {
        "name": "security",
        "keywords_en": ["secure", "safe", "security", "encrypt", "hack", "private", "secret", "anonymous", "privacy"],
        "keywords_ar": ["أمان", "آمن", "تشفير", "اختراق", "خاص", "سري", "مجهول", "خصوصية"],
        "answer_en": (
            "🛡️ <strong>Security &amp; Privacy:</strong><br>"
            "• End-to-end encryption on all data<br>"
            "• National ID + face biometric two-factor auth<br>"
            "• No photos stored — only mathematical embeddings<br>"
            "• Your vote choice is anonymous — even admins cannot see it<br>"
            "• One-vote-per-person enforced at database level"
        ),
        "answer_ar": (
            "🛡️ <strong>الأمان والخصوصية:</strong><br>"
            "• تشفير شامل لجميع البيانات<br>"
            "• مصادقة ثنائية: الهوية الوطنية + بصمة الوجه<br>"
            "• لا تُخزَّن صور — فقط بصمات رياضية<br>"
            "• اختيارك سري — حتى المسؤولون لا يمكنهم رؤيته<br>"
            "• صوت واحد لكل شخص مُطبَّق على مستوى قاعدة البيانات"
        ),
    },
    {
        "name": "national_id",
        "keywords_en": ["national id", "id number", "14 digit", "id card", "identity", "nid"],
        "keywords_ar": ["رقم الهوية", "بطاقة الهوية", "14 رقم", "الهوية الوطنية", "هوية", "الرقم القومي"],
        "answer_en": (
            "🪪 <strong>National ID:</strong><br>"
            "Your National ID is the 14-digit number on your Egyptian national ID card.<br>"
            "It's required to authenticate and vote on DEMS.<br>"
            "If your ID doesn't work, contact the National Electoral Commission."
        ),
        "answer_ar": (
            "🪪 <strong>رقم الهوية الوطنية:</strong><br>"
            "رقم الهوية هو الرقم المكون من 14 خانة على بطاقتك الوطنية المصرية.<br>"
            "مطلوب للمصادقة والتصويت على DEMS.<br>"
            "إذا لم يعمل رقمك، تواصل مع الهيئة الوطنية للانتخابات."
        ),
    },
    {
        "name": "candidate",
        "keywords_en": ["candidate", "candidates", "party", "who is running", "district candidates", "parties"],
        "keywords_ar": ["مرشح", "مرشحون", "قائمة", "حزب", "من يترشح", "مرشحين", "احزاب"],
        "answer_en": (
            "🗳️ <strong>Candidates:</strong><br>"
            "Candidates are shown after you log in.<br>"
            "You will only see candidates from <em>your registered district</em>.<br>"
            "Each district has multiple candidates from different parties."
        ),
        "answer_ar": (
            "🗳️ <strong>المرشحون:</strong><br>"
            "يتم عرض المرشحين بعد تسجيل الدخول.<br>"
            "ستشاهد فقط مرشحي <em>دائرتك المسجلة</em>.<br>"
            "كل دائرة بها مرشحون من أحزاب مختلفة."
        ),
    },
    {
        "name": "double_vote",
        "keywords_en": ["vote twice", "double vote", "already voted", "one vote", "vote again", "revote"],
        "keywords_ar": ["صوت مرتين", "تصويت مزدوج", "صوتت مسبقاً", "صوت واحد", "اصوت تاني", "صوت للمرة"],
        "answer_en": (
            "⚠️ <strong>One Vote Per Person:</strong><br>"
            "DEMS strictly enforces one vote per voter.<br>"
            "Once you vote, the system permanently marks you as 'voted'.<br>"
            "Any attempt to vote again will be blocked."
        ),
        "answer_ar": (
            "⚠️ <strong>صوت واحد لكل شخص:</strong><br>"
            "يفرض DEMS بصرامة صوتاً واحداً لكل ناخب.<br>"
            "بمجرد التصويت، يُسجَّل حسابك نهائياً كـ 'صوّت'.<br>"
            "أي محاولة للتصويت مجدداً ستُحجب."
        ),
    },
    {
        "name": "about",
        "keywords_en": ["what is dems", "about", "system", "platform", "dems", "how does it work"],
        "keywords_ar": ["ما هو ديمز", "عن النظام", "عن المنصة", "DEMS", "ديمز", "كيف يعمل النظام"],
        "answer_en": (
            "🏛️ <strong>About DEMS:</strong><br>"
            "DEMS (Digital Election Management System) is Egypt's official digital voting platform.<br>"
            "It provides secure, transparent, and accessible elections for all Egyptian citizens.<br>"
            "Features: National ID auth, face biometric, real-time results, district-based voting."
        ),
        "answer_ar": (
            "🏛️ <strong>عن DEMS:</strong><br>"
            "DEMS (نظام إدارة الانتخابات الرقمية) هو المنصة الرسمية للتصويت الرقمي في مصر.<br>"
            "توفر انتخابات آمنة وشفافة وسهلة الوصول لجميع المواطنين.<br>"
            "المميزات: مصادقة بالهوية الوطنية، بصمة الوجه، نتائج فورية، تصويت قائم على الدوائر."
        ),
    },
    {
        "name": "districts",
        "keywords_en": ["district", "districts", "governorate", "area", "region", "where", "location"],
        "keywords_ar": ["دائرة", "دوائر", "محافظة", "منطقة", "أين", "موقع", "إقليم"],
        "answer_en": (
            "🗺️ <strong>Districts:</strong><br>"
            "DEMS covers the following districts:<br>"
            "• Qena (قنا) · Sohag (سوهاج) · Elbehira (البحيرة) · Assuit (أسيوط)<br>"
            "Your assigned district appears after you log in."
        ),
        "answer_ar": (
            "🗺️ <strong>الدوائر الانتخابية:</strong><br>"
            "يشمل DEMS الدوائر التالية:<br>"
            "• قنا · سوهاج · البحيرة · أسيوط<br>"
            "تظهر دائرتك المخصصة بعد تسجيل الدخول."
        ),
    },
]

FALLBACK_EN = (   ## law el user katab ay kalam mesh mafhoum aw mafeesh keywords matched, elbot hayradd 3ala tool bel fallback message da
    "🤔 I didn't quite understand. You can ask me about:<br>"
    "• How to vote / كيف أصوت<br>"
    "• Registration / التسجيل<br>"
    "• Face biometric / بصمة الوجه<br>"
    "• Election results / النتائج<br>"
    "• Security &amp; privacy / الأمان<br>"
    "• Candidates / المرشحون<br>"
    "• Districts / الدوائر"
)

FALLBACK_AR = (
    "🤔 لم أفهم سؤالك تماماً. يمكنك السؤال عن:<br>"
    "• كيف أصوت / How to vote<br>"
    "• التسجيل / Registration<br>"
    "• بصمة الوجه / Face biometric<br>"
    "• نتائج الانتخابات / Results<br>"
    "• الأمان / Security<br>"
    "• المرشحون / Candidates<br>"
    "• الدوائر / Districts"
)

# ─── Language detection ───────────────────────────────────────────────────────

def _detect_lang(text: str) -> str:  #str input str output 
    """Simple heuristic: ≥2 Arabic chars → Arabic, else English."""
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF') #arabic unicode range
    return 'ar' if arabic_chars >= 2 else 'en'


# ─── Intent scoring ───────────────────────────────────────────────────────────

def _score_intent(text_lower: str, intent: dict, lang: str) -> int: #bt7sb kam keyword matched for this intent, btakhod el text lowercase 3shan el matching yeb2a case-insensitive
    """Count keyword hits for this intent."""
    key = f"keywords_{lang}"  #en or ar from list of intents
    keywords = intent.get(key, intent.get("keywords_en", []))
    return sum(1 for kw in keywords if kw in text_lower)
# بيشوف الكلمة المفتاحية موجودة في النص ولا لا لو لقاها يديها 1


def classify_intents(text: str): #بتنظم العملية كلها وبترجع قائمة بالـ Intents المكتشفة.
    """
    Multi-intent classifier.
    Returns list of (intent, lang) pairs ordered by score descending.
    """
    lang = _detect_lang(text) #3shan ye3raf el language 
    text_lower = text.lower()

    scored = []
    for intent in INTENTS: #loop 3ala kol intent we y7sb el score bta3o ex) voting, candidate
        score = _score_intent(text_lower, intent, lang)
        # Also check cross-language keywords (for mixed messages)
        other_lang = 'ar' if lang == 'en' else 'en'
        score += _score_intent(text_lower, intent, other_lang)
        if score > 0:
            scored.append((score, intent)) #adding score and intent to list

    scored.sort(key=lambda x: -x[0])  #byrateb el intents 3ala hasab el score mn akbar asghar, el intent elly fe kalmaty aktar yezhar awel wa7ed
    return [(intent, lang) for _, intent in scored] #list feha el intents, lang 3shan yegahez response


# ─── OpenAI fallback ─────────────────────────────────────────────────────────

OPENAI_SYSTEM_PROMPT = """You are the official DEMS (Digital Election Management System) assistant for Egyptian parliamentary elections.
Answer ONLY questions about the election system: voting, registration, face recognition login, candidates, districts, results, security.
Do NOT answer questions unrelated to the election system.
Keep answers concise (max 5 lines). Use HTML for formatting (bold, line breaks).
Always respond in the same language as the user's question (Arabic or English)."""

def _openai_fallback(message: str, lang: str) -> str | None:
    """
    Call OpenAI GPT-4o for questions the keyword engine couldn't answer.
    Returns HTML string or None if OpenAI is not configured / call fails.
    """
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key:
        return None

    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": OPENAI_SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ],
            max_tokens=300,
            temperature=0.3,  #for logical response 
        )
        return response.choices[0].message.content.strip()   #strip btsheel el spaces
    except Exception as e:
        logger.warning(f"OpenAI chatbot fallback failed: {e}")
        return None


# ─── Main entry point ─────────────────────────────────────────────────────────

#views.py hayestakhdem el function di 3shan ygeb el response elly hayt3rd 3ala el chatbot interface
def get_bot_response(text: str) -> str:
    """
    Accepts any message (Arabic/English/mixed).
    Returns HTML-formatted answer.

    Flow:
    1. Keyword-based multi-intent matching
    2. If no match → try OpenAI (if configured)
    3. If still no answer → generic fallback
    """
    matches = classify_intents(text)
    lang = _detect_lang(text)

    if not matches:
        # Try OpenAI fallback before giving up
        ai_reply = _openai_fallback(text, lang)
        if ai_reply:
            return f"🤖 {ai_reply}"
        return FALLBACK_AR if lang == 'ar' else FALLBACK_EN

    # Build multi-intent response
    answers = []
    seen = set()  #3shan tmna3 el duplicate law the same intent tel3 marteen 
    for intent, detected_lang in matches:
        name = intent["name"]
        if name in seen:
            continue
        seen.add(name)
        answer_key = f"answer_{lang}"
        answers.append(intent.get(answer_key, intent.get("answer_en", "")))

    if len(answers) == 1:
        return answers[0]

    # Multiple intents — join with visual separator
    sep = '<hr style="border:none;border-top:1px solid rgba(255,255,255,0.15);margin:10px 0">'
    return sep.join(answers)
