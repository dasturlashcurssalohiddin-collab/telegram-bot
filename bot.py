# -*- coding: utf-8 -*-

import json
import os
import time
import logging
import tempfile
import asyncio
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

from deep_translator import GoogleTranslator
from openai import OpenAI
import edge_tts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN  = os.getenv("BOT_TOKEN")
ADMIN_ID   = 6283517295
CHANNEL_ID = "@tuxum_kanal"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ai_client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

DATA_DIR        = os.path.dirname(os.path.abspath(__file__))
ADS_FILE        = os.path.join(DATA_DIR, "ads.json")
USERS_FILE      = os.path.join(DATA_DIR, "users.json")
BUTTONS_FILE    = os.path.join(DATA_DIR, "custom_buttons.json")
COMMANDS_FILE   = os.path.join(DATA_DIR, "custom_commands.json")
EVENTS_FILE     = os.path.join(DATA_DIR, "events.json")
LOCATION_FILE   = os.path.join(DATA_DIR, "delivery_location.json")
ORDERS_FILE     = os.path.join(DATA_DIR, "orders.json")       # YANGI: buyurtmalar
MESSAGES_FILE   = os.path.join(DATA_DIR, "messages.json")     # YANGI: xabarlar

ADMIN_LATITUDE  = 41.2995
ADMIN_LONGITUDE = 69.2401

LANGS = ["uz", "en", "ru", "de"]
LANG_NAMES = {
    "uz": "🇺🇿 O'zbek tili",
    "en": "🇬🇧 English",
    "ru": "🇷🇺 Русский язык",
    "de": "🇩🇪 Deutsch",
}

T = {
    "choose_lang":    {"uz": "Tilni tanlang:", "en": "Choose your language:", "ru": "Выберите язык:", "de": "Wähle deine Sprache:"},
    "lang_set":       {"uz": "Til o'zbekchaga o'rnatildi ✅", "en": "Language set to English ✅", "ru": "Язык установлен на русский ✅", "de": "Sprache auf Deutsch eingestellt ✅"},
    "ad_title":       {"uz": "🥚 E'lon", "en": "🥚 Listing", "ru": "🥚 Объявление", "de": "🥚 Anzeige"},
    "no_ads":         {"uz": "Hozircha e'lonlar yo'q.", "en": "There are no listings yet.", "ru": "Пока нет объявлений.", "de": "Noch keine Anzeigen."},
    "send_photo":     {"uz": "📸 E'lon uchun rasm yuboring:"},
    "photo_received": {"uz": "✅ Rasm yuklandi."},
    "write_ad":       {"uz": "✍️ E'lon matnini yozing:"},
    "ad_received":    {"uz": "✅ E'lon qabul qilindi.\n\nTugmalarni tanlang, so'ng \"✅ Tayyor\" bosing."},
    "write_info":     {"uz": "ℹ️ Ma'lumot matnini yozing:"},
    "info_received":  {"uz": "✅ E'lon barcha foydalanuvchilarga yuborildi!"},
    "ad_done_no_info":{"uz": "✅ E'lon barcha foydalanuvchilarga yuborildi!"},
    "info_btn_msg":   {"uz": "ℹ️ Ma'lumot:", "en": "ℹ️ Information:", "ru": "ℹ️ Информация:", "de": "ℹ️ Information:"},
    "calling":        {"uz": "📞 Telefon raqami: ", "en": "📞 Phone number: ", "ru": "📞 Номер телефона: ", "de": "📞 Telefonnummer: "},
    "no_info_yet":    {"uz": "Ma'lumot kiritilmagan.", "en": "No information provided.", "ru": "Информация не указана.", "de": "Keine Information vorhanden."},
    "contact_sent":   {"uz": "✅ Xabaringiz sotuvchiga yuborildi.", "en": "✅ Message sent to seller.", "ru": "✅ Сообщение отправлено.", "de": "✅ Nachricht gesendet."},
    "send_location":  {"uz": "📍 Joylashuvingizni yuboring:", "en": "📍 Send your location:", "ru": "📍 Отправьте местоположение:", "de": "📍 Standort senden:"},
    "location_sent":  {"uz": "✅ Joylashuvingiz sotuvchiga yuborildi.", "en": "✅ Location sent to seller.", "ru": "✅ Местоположение отправлено.", "de": "✅ Standort gesendet."},
    "location_btn_label": {"uz": "📍 Joylashuvni yuborish", "en": "📍 Send Location", "ru": "📍 Отправить местоположение", "de": "📍 Standort senden"},
    "delivery_location": {
        "uz": "🚚 Olib kelish manzili:\n\nQuyidagi xaritadan manzilimizni ko'ring!",
        "en": "🚚 Delivery address:\n\nSee our location on the map below!",
        "ru": "🚚 Адрес доставки:\n\nСмотрите наш адрес на карте ниже!",
        "de": "🚚 Lieferadresse:\n\nSehen Sie unsere Adresse auf der Karte unten!",
    },
    "tuxumai_greeting": {
        "uz": "🤖 TuxumAI bilan suhbatlashmoqchimisiz? Savolingizni yozing:",
        "en": "🤖 Want to chat with TuxumAI? Write your question:",
        "ru": "🤖 Хотите пообщаться с TuxumAI? Напишите вопрос:",
        "de": "🤖 Möchten Sie mit TuxumAI chatten? Schreiben Sie Ihre Frage:",
    },
    # YANGI: Buyurtma xabarlari
    "order_ask_qty": {
        "uz": "🛒 Nechta tuxum buyurtma qilmoqchisiz? (sonini yozing):",
        "en": "🛒 How many eggs would you like to order?",
        "ru": "🛒 Сколько яиц вы хотите заказать?",
        "de": "🛒 Wie viele Eier möchten Sie bestellen?",
    },
    "order_ask_address": {
        "uz": "📦 Yetkazib berish manzilingizni yozing yoki joylashuvingizni yuboring:",
        "en": "📦 Enter your delivery address or send your location:",
        "ru": "📦 Введите адрес доставки или отправьте местоположение:",
        "de": "📦 Geben Sie Ihre Lieferadresse ein oder senden Sie Ihren Standort:",
    },
    "order_ask_phone": {
        "uz": "📞 Telefon raqamingizni yozing (masalan: +998901234567):",
        "en": "📞 Enter your phone number:",
        "ru": "📞 Введите ваш номер телефона:",
        "de": "📞 Geben Sie Ihre Telefonnummer ein:",
    },
    "order_confirm": {
        "uz": "✅ Buyurtmangiz qabul qilindi! Tez orada siz bilan bog'lanamiz.",
        "en": "✅ Your order has been received! We will contact you soon.",
        "ru": "✅ Ваш заказ принят! Мы свяжемся с вами в ближайшее время.",
        "de": "✅ Ihre Bestellung wurde erhalten! Wir werden uns bald bei Ihnen melden.",
    },
    "order_status": {
        "uz": "📋 Sizning buyurtmalaringiz:",
        "en": "📋 Your orders:",
        "ru": "📋 Ваши заказы:",
        "de": "📋 Ihre Bestellungen:",
    },
    "no_orders": {
        "uz": "Sizda hali buyurtma yo'q.",
        "en": "You have no orders yet.",
        "ru": "У вас пока нет заказов.",
        "de": "Sie haben noch keine Bestellungen.",
    },
    "write_message": {
        "uz": "✍️ Adminga xabaringizni yozing:",
        "en": "✍️ Write your message to admin:",
        "ru": "✍️ Напишите сообщение администратору:",
        "de": "✍️ Schreiben Sie Ihre Nachricht an den Admin:",
    },
    "message_sent": {
        "uz": "✅ Xabaringiz adminga yuborildi!",
        "en": "✅ Your message has been sent to admin!",
        "ru": "✅ Ваше сообщение отправлено администратору!",
        "de": "✅ Ihre Nachricht wurde an den Admin gesendet!",
    },
    "admin_replied": {
        "uz": "💬 Admin javobi:\n\n",
        "en": "💬 Admin reply:\n\n",
        "ru": "💬 Ответ администратора:\n\n",
        "de": "💬 Admin-Antwort:\n\n",
    },
    "order_cancelled": {
        "uz": "❌ Buyurtma bekor qilindi.",
        "en": "❌ Order cancelled.",
        "ru": "❌ Заказ отменён.",
        "de": "❌ Bestellung storniert.",
    },
    "invalid_qty": {
        "uz": "❌ Iltimos, to'g'ri son kiriting (masalan: 10):",
        "en": "❌ Please enter a valid number:",
        "ru": "❌ Пожалуйста, введите правильное число:",
        "de": "❌ Bitte geben Sie eine gültige Zahl ein:",
    },
}


def tr(key, lang):
    d = T.get(key, {})
    return d.get(lang, d.get("uz", key))


BUTTONS_CATALOG = {
    "phone": {
        "label": {"uz": "📞 Telefon", "en": "📞 Phone", "ru": "📞 Телефон", "de": "📞 Telefon"},
        "type": "phone",
    },
    "info": {
        "label": {"uz": "🌐 Ma'lumot", "en": "🌐 Information", "ru": "🌐 Информация", "de": "🌐 Information"},
        "type": "info",
    },
    "quality": {
        "label": {"uz": "✅ Sifat kafolati", "en": "✅ Quality guarantee", "ru": "✅ Гарантия качества", "de": "✅ Qualitätsgarantie"},
        "type": "text",
        "text": {
            "uz": "✅ Mahsulot sifati kafolatlanadi. Tuxumlar yangi va sifatli.",
            "en": "✅ Product quality is guaranteed. Eggs are fresh and high quality.",
            "ru": "✅ Качество гарантировано. Яйца свежие и высококачественные.",
            "de": "✅ Qualität garantiert. Eier sind frisch und hochwertig.",
        },
    },
    "location": {
        "label": {"uz": "📍 Manzil", "en": "📍 Location", "ru": "📍 Адрес", "de": "📍 Standort"},
        "type": "location_request",
    },
    "tuxumai": {
        "label": {"uz": "🤖 TuxumAI", "en": "🤖 TuxumAI", "ru": "🤖 TuxumAI", "de": "🤖 TuxumAI"},
        "type": "tuxumai",
    },
    "market": {
        "label": {"uz": "🛒 Tuxum Market", "en": "🛒 Tuxum Market", "ru": "🛒 Tuxum Market", "de": "🛒 Tuxum Market"},
        "type": "url",
        "url": "https://salohiddin900.github.io/tuxum-market/",
    },
    "delivery": {
        "label": {"uz": "🚚 Olib kelish", "en": "🚚 Delivery", "ru": "🚚 Доставка", "de": "🚚 Lieferung"},
        "type": "delivery",
    },
    # YANGI tugmalar
    "order": {
        "label": {"uz": "🛍 Buyurtma", "en": "🛍 Order", "ru": "🛍 Заказать", "de": "🛍 Bestellen"},
        "type": "order",
    },
    "message_admin": {
        "label": {"uz": "✉️ Xabar yozish", "en": "✉️ Send message", "ru": "✉️ Написать", "de": "✉️ Nachricht"},
        "type": "message_admin",
    },
}

PHONE_NUMBER = "+998951000130"

TTS_VOICES = {
    "uz": "uz-UZ-MadinaNeural",
    "en": "en-US-AriaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "de": "de-DE-KatjaNeural",
}

ORDER_STATUSES = {
    "new":        {"uz": "🆕 Yangi", "en": "🆕 New", "ru": "🆕 Новый", "de": "🆕 Neu"},
    "confirmed":  {"uz": "✅ Tasdiqlangan", "en": "✅ Confirmed", "ru": "✅ Подтверждён", "de": "✅ Bestätigt"},
    "delivering": {"uz": "🚚 Yetkazilmoqda", "en": "🚚 Delivering", "ru": "🚚 Доставляется", "de": "🚚 Wird geliefert"},
    "done":       {"uz": "✅ Bajarildi", "en": "✅ Done", "ru": "✅ Выполнен", "de": "✅ Erledigt"},
    "cancelled":  {"uz": "❌ Bekor", "en": "❌ Cancelled", "ru": "❌ Отменён", "de": "❌ Storniert"},
}


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


ads             = load_json(ADS_FILE, [])
users           = load_json(USERS_FILE, {})
custom_buttons  = load_json(BUTTONS_FILE, {})
custom_commands = load_json(COMMANDS_FILE, {})
events          = load_json(EVENTS_FILE, [])
orders          = load_json(ORDERS_FILE, [])      # YANGI
messages_store  = load_json(MESSAGES_FILE, [])    # YANGI

_loc = load_json(LOCATION_FILE, {})
if _loc:
    ADMIN_LATITUDE  = _loc.get("lat", ADMIN_LATITUDE)
    ADMIN_LONGITUDE = _loc.get("lon", ADMIN_LONGITUDE)

user_modes:  dict = {}
user_states: dict = {}

def save_ads():             save_json(ADS_FILE, ads)
def save_users():           save_json(USERS_FILE, users)
def save_custom_buttons():  save_json(BUTTONS_FILE, custom_buttons)
def save_custom_commands(): save_json(COMMANDS_FILE, custom_commands)
def save_events():          save_json(EVENTS_FILE, events)
def save_orders():          save_json(ORDERS_FILE, orders)
def save_messages():        save_json(MESSAGES_FILE, messages_store)

def get_lang(uid):
    # Foydalanuvchi ma'lumotlari dict bo'lishi mumkin (yangi format)
    val = users.get(str(uid), "uz")
    if isinstance(val, dict):
        return val.get("lang", "uz")
    return val

def get_user_info(uid):
    val = users.get(str(uid), {})
    if isinstance(val, str):
        return {"lang": val}
    return val

def set_user_info(uid, key, value):
    val = users.get(str(uid), {})
    if isinstance(val, str):
        val = {"lang": val}
    val[key] = value
    users[str(uid)] = val
    save_users()

def get_mode(uid):          return user_modes.get(str(uid), "text")
def set_mode(uid, mode):    user_modes[str(uid)] = mode
def get_state(uid):         return user_states.get(str(uid), "normal")
def set_state(uid, state):  user_states[str(uid)] = state


def log_event(event_type: str, user_id: int, detail: str = ""):
    events.append({"ts": time.time(), "type": event_type, "user_id": user_id, "detail": detail})
    cutoff = time.time() - 7 * 86400
    events[:] = [e for e in events if e["ts"] > cutoff]
    save_events()


# ─── ConversationHandler holatlari ───────────────────────────────────────────
WAIT_PHOTO, WAIT_TEXT, SELECT_BUTTONS, WAIT_INFO = range(4)
BTN_NAME, BTN_TYPE, BTN_VALUE = range(10, 13)
CMD_NAME1, CMD_RESP1, CMD_NAME2, CMD_RESP2 = range(20, 24)

# YANGI: Buyurtma holatlari
ORDER_QTY, ORDER_ADDRESS, ORDER_PHONE = range(30, 33)

# YANGI: Foydalanuvchi xabar holati
USER_MSG = 40

# YANGI: Broadcast holati
BROADCAST_MSG = 50

LANG_NAME_TO_CODE = {v: k for k, v in LANG_NAMES.items()}

BTN_TYPES = {
    "link":    "🔗 Link (URL)",
    "text":    "📝 Matn (oddiy xabar)",
    "phone":   "📞 Telefon raqam",
}


def lang_inline_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(LANG_NAMES[c], callback_data=f"setlang_{c}")] for c in LANGS]
    )


def lang_reply_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(LANG_NAMES["uz"]), KeyboardButton(LANG_NAMES["en"])],
         [KeyboardButton(LANG_NAMES["ru"]), KeyboardButton(LANG_NAMES["de"])]],
        resize_keyboard=True
    )


def translate_text(text, target_lang):
    if not text or target_lang == "uz":
        return text
    try:
        return GoogleTranslator(source="auto", target=target_lang).translate(text)
    except Exception as e:
        logger.warning(f"Tarjima xatosi: {e}")
        return text


def get_ad_text(ad, lang):
    cache = ad.setdefault("text_translations", {})
    if lang not in cache:
        cache[lang] = translate_text(ad.get("text", ""), lang)
        save_ads()
    return cache[lang]


def get_ad_info_text(ad, lang):
    if not ad.get("info_text"):
        return ""
    cache = ad.setdefault("info_translations", {})
    if lang not in cache:
        cache[lang] = translate_text(ad.get("info_text", ""), lang)
        save_ads()
    return cache[lang]


def build_ad_keyboard(ad, lang):
    rows, row = [], []

    for btn_id in ad.get("buttons", []):
        cat = BUTTONS_CATALOG.get(btn_id)
        if not cat:
            continue
        label = cat["label"].get(lang, cat["label"]["uz"])
        t = cat["type"]
        if t == "url":
            row.append(InlineKeyboardButton(label, url=cat["url"]))
        else:
            cb = (
                f"phone_{ad['id']}"        if t == "phone"            else
                f"info_{ad['id']}"         if t == "info"             else
                f"tuxumai_{ad['id']}"      if t == "tuxumai"          else
                f"delivery_{ad['id']}"     if t == "delivery"         else
                f"location_{ad['id']}"     if t == "location_request" else
                f"order_{ad['id']}"        if t == "order"            else
                f"msgadmin_{ad['id']}"     if t == "message_admin"    else
                f"btn_{ad['id']}_{btn_id}"
            )
            row.append(InlineKeyboardButton(label, callback_data=cb))
        if len(row) == 2:
            rows.append(row); row = []

    for cbtn_id, cbtn in custom_buttons.items():
        label = cbtn.get("name", cbtn_id)
        btn_type = cbtn.get("btn_type", "text")
        if btn_type == "link":
            row.append(InlineKeyboardButton(label, url=cbtn.get("action_value", "#")))
        else:
            row.append(InlineKeyboardButton(label, callback_data=f"custombtn_{cbtn_id}"))
        if len(row) == 2:
            rows.append(row); row = []

    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows) if rows else None


async def send_ad_to_chat(context, chat_id, ad, lang):
    try:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=ad["photo_file_id"],
            caption=f"{tr('ad_title', lang)}\n\n{get_ad_text(ad, lang)}",
            reply_markup=build_ad_keyboard(ad, lang),
        )
    except Exception as e:
        logger.error(f"E'lon yuborishda xato {chat_id}: {e}")


async def send_all_ads(context, chat_id, lang):
    if not ads:
        await context.bot.send_message(chat_id=chat_id, text=tr("no_ads", lang))
        return
    for ad in ads:
        await send_ad_to_chat(context, chat_id, ad, lang)


async def _tts_async(text: str, lang: str, output_path: str):
    voice = TTS_VOICES.get(lang, "en-US-AriaNeural")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def text_to_speech(text: str, lang: str):
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
        asyncio.get_event_loop().run_until_complete(_tts_async(text, lang, tmp_path))
        with open(tmp_path, "rb") as f:
            data = f.read()
        os.unlink(tmp_path)
        return data
    except Exception as e:
        logger.warning(f"TTS xatosi: {e}")
        return None


def transcribe_voice(file_path: str):
    try:
        with open(file_path, "rb") as f:
            result = ai_client.audio.transcriptions.create(model="whisper-large-v3", file=f)
        return result.text
    except Exception as e:
        logger.warning(f"STT xatosi: {e}")
        return None


def get_ai_reply(ad, lang: str, user_message: str):
    ad_text = ad.get("text", "") if ad else ""
    ad_info = ad.get("info_text", "") if ad else ""
    system_prompt = (
        "Sening isming TuxumAI. Sen aqlli yordamchi sun'iy intellektsan. "
        "Har qanday savolga javob ber. Agar 'sen kimsan' deb so'rashsa — 'Men TuxumAI man' de.\n\n"
        f"E'lon: {ad_text}\nQo'shimcha: {ad_info or 'yoq'}\n\n"
        f"Javobni {lang} tilida yoz. Qisqa, do'stona, aniq."
    )
    try:
        r = ai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=400,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"TuxumAI xatosi: {e}")
        return None


async def send_ai_response(context, chat_id: int, user_id: int, text: str, lang: str):
    if get_mode(user_id) == "voice":
        audio = text_to_speech(text, lang)
        if audio:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp.write(audio); tmp_path = tmp.name
            try:
                with open(tmp_path, "rb") as f:
                    await context.bot.send_voice(chat_id=chat_id, voice=f)
            finally:
                os.unlink(tmp_path)
            return
    await context.bot.send_message(chat_id=chat_id, text=f"🤖 TuxumAI:\n\n{text}")


# ═══════════════════════════════════════════════════════════════════════════════
# START
# ═══════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid  = user.id
    lang = get_lang(uid)
    set_state(uid, "normal")

    is_new = str(uid) not in users
    if is_new:
        users[str(uid)] = {"lang": "uz", "name": user.full_name or "", "joined": time.time()}
        save_users()
        log_event("join", uid, user.full_name or "")
        # Adminga yangi foydalanuvchi haqida xabar
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"🆕 Yangi foydalanuvchi!\n"
                f"👤 {user.full_name or 'Noma\'lum'}\n"
                f"🆔 {uid}\n"
                f"📱 @{user.username or 'username yo\'q'}"
            )
        except Exception:
            pass

    await update.message.reply_text(tr("choose_lang", lang), reply_markup=lang_inline_keyboard())


# ═══════════════════════════════════════════════════════════════════════════════
# TIL
# ═══════════════════════════════════════════════════════════════════════════════

async def set_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang_code = query.data.split("_", 1)[1]
    set_user_info(query.from_user.id, "lang", lang_code)
    await query.edit_message_text(tr("lang_set", lang_code))
    await context.bot.send_message(query.message.chat_id, tr("lang_set", lang_code), reply_markup=lang_reply_keyboard())
    await send_all_ads(context, query.message.chat_id, lang_code)


async def lang_button_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    text = update.message.text
    if text in LANG_NAME_TO_CODE:
        lang_code = LANG_NAME_TO_CODE[text]
        set_user_info(update.effective_user.id, "lang", lang_code)
        await update.message.reply_text(tr("lang_set", lang_code), reply_markup=lang_reply_keyboard())
        await send_all_ads(context, update.effective_chat.id, lang_code)
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# YANGI: BUYURTMA TIZIMI
# ═══════════════════════════════════════════════════════════════════════════════

async def order_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """E'londagi Buyurtma tugmasi bosilganda"""
    q = update.callback_query
    lang = get_lang(q.from_user.id)
    ad_id = q.data.split("_", 1)[1]
    context.user_data["order_ad_id"] = ad_id
    set_state(q.from_user.id, "ordering")
    await q.answer()
    await context.bot.send_message(
        q.message.chat_id,
        tr("order_ask_qty", lang),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Bekor", callback_data="order_cancel")
        ]])
    )
    return ORDER_QTY


async def order_qty_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_lang(user.id)
    text = update.message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text(tr("invalid_qty", lang))
        return ORDER_QTY
    context.user_data["order_qty"] = int(text)
    await update.message.reply_text(
        tr("order_ask_address", lang),
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(tr("location_btn_label", lang), request_location=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
    )
    return ORDER_ADDRESS


async def order_address_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_lang(user.id)
    if update.message.location:
        loc = update.message.location
        context.user_data["order_address"] = f"📍 {loc.latitude}, {loc.longitude}"
        context.user_data["order_location"] = {"lat": loc.latitude, "lon": loc.longitude}
    else:
        context.user_data["order_address"] = update.message.text.strip()
    await update.message.reply_text(tr("order_ask_phone", lang), reply_markup=lang_reply_keyboard())
    return ORDER_PHONE


async def order_phone_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_lang(user.id)
    phone = update.message.text.strip()

    # Buyurtmani saqlash
    order_id = f"ORD{int(time.time())}"
    order = {
        "id":        order_id,
        "user_id":   user.id,
        "user_name": user.full_name or "",
        "username":  f"@{user.username}" if user.username else f"id:{user.id}",
        "ad_id":     context.user_data.get("order_ad_id", ""),
        "qty":       context.user_data.get("order_qty", 0),
        "address":   context.user_data.get("order_address", ""),
        "phone":     phone,
        "status":    "new",
        "ts":        time.time(),
    }
    orders.append(order)
    save_orders()
    set_state(user.id, "normal")

    # Foydalanuvchiga tasdiqlash
    await update.message.reply_text(tr("order_confirm", lang), reply_markup=lang_reply_keyboard())

    # Adminga xabar
    status_label = ORDER_STATUSES["new"].get(lang, "🆕 Yangi")
    try:
        msg = (
            f"🛍 <b>Yangi buyurtma!</b> #{order_id}\n\n"
            f"👤 {user.full_name or 'Noma\'lum'} ({order['username']})\n"
            f"🆔 {user.id}\n"
            f"🥚 Miqdor: <b>{order['qty']} ta</b>\n"
            f"📍 Manzil: {order['address']}\n"
            f"📞 Telefon: {phone}\n"
            f"📊 Holat: {status_label}"
        )
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"ordstatus_confirmed_{order_id}"),
                InlineKeyboardButton("❌ Bekor", callback_data=f"ordstatus_cancelled_{order_id}"),
            ],
            [
                InlineKeyboardButton("🚚 Yetkazilmoqda", callback_data=f"ordstatus_delivering_{order_id}"),
                InlineKeyboardButton("✅ Bajarildi", callback_data=f"ordstatus_done_{order_id}"),
            ],
        ])
        await context.bot.send_message(ADMIN_ID, msg, parse_mode="HTML", reply_markup=kb)
        # Agar manzil joylashuv bo'lsa
        loc = context.user_data.get("order_location")
        if loc:
            await context.bot.send_location(ADMIN_ID, latitude=loc["lat"], longitude=loc["lon"])
    except Exception as e:
        logger.warning(f"Adminga buyurtma yuborib bo'lmadi: {e}")

    log_event("new_order", user.id, order_id)
    context.user_data.clear()
    return ConversationHandler.END


async def order_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang = get_lang(q.from_user.id)
    await q.answer()
    set_state(q.from_user.id, "normal")
    context.user_data.clear()
    await context.bot.send_message(q.message.chat_id, tr("order_cancelled", lang))
    return ConversationHandler.END


async def order_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin buyurtma holatini o'zgartiradi"""
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer("❌ Ruxsat yo'q"); return
    await q.answer()

    parts    = q.data.split("_", 2)  # ordstatus_STATUS_ORDERID
    new_stat = parts[1]
    order_id = parts[2]

    order = next((o for o in orders if o["id"] == order_id), None)
    if not order:
        await q.edit_message_text("❌ Buyurtma topilmadi."); return

    old_stat = order["status"]
    order["status"] = new_stat
    save_orders()

    status_uz = ORDER_STATUSES.get(new_stat, {}).get("uz", new_stat)
    await q.edit_message_text(
        q.message.text + f"\n\n✅ Holat yangilandi: {status_uz}",
        reply_markup=None
    )

    # Foydalanuvchiga xabar
    user_lang = get_lang(order["user_id"])
    status_local = ORDER_STATUSES.get(new_stat, {}).get(user_lang, new_stat)
    try:
        await context.bot.send_message(
            order["user_id"],
            f"📦 Buyurtmangiz holati yangilandi!\n\n"
            f"🆔 #{order_id}\n"
            f"📊 Holat: <b>{status_local}</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Foydalanuvchiga xabar yuborib bo'lmadi: {e}")

    log_event("order_status", ADMIN_ID, f"{order_id}:{old_stat}->{new_stat}")


async def my_orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi o'z buyurtmalarini ko'radi"""
    user = update.effective_user
    lang = get_lang(user.id)
    my = [o for o in orders if o["user_id"] == user.id]
    if not my:
        await update.message.reply_text(tr("no_orders", lang))
        return
    lines = [tr("order_status", lang)]
    for o in reversed(my[-10:]):
        stat = ORDER_STATUSES.get(o["status"], {}).get(lang, o["status"])
        dt   = datetime.fromtimestamp(o["ts"]).strftime("%d.%m.%Y %H:%M")
        lines.append(f"\n🆔 #{o['id']}\n🥚 {o['qty']} ta | 📊 {stat}\n📅 {dt}")
    await update.message.reply_text("\n".join(lines))


# ═══════════════════════════════════════════════════════════════════════════════
# YANGI: FOYDALANUVCHI ↔ ADMIN XABAR TIZIMI
# ═══════════════════════════════════════════════════════════════════════════════

async def msgadmin_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """E'londagi Xabar yozish tugmasi"""
    q = update.callback_query
    lang = get_lang(q.from_user.id)
    set_state(q.from_user.id, "writing_message")
    await q.answer()
    await context.bot.send_message(q.message.chat_id, tr("write_message", lang))


async def admin_reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin /reply <user_id> <matn> orqali javob beradi"""
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("❌ Foydalanish: /reply <user_id> <matn>")
        return
    try:
        target_id  = int(args[0])
        reply_text = " ".join(args[1:])
        user_lang  = get_lang(target_id)
        await context.bot.send_message(
            target_id,
            f"{tr('admin_replied', user_lang)}{reply_text}"
        )
        await update.message.reply_text(f"✅ Javob {target_id} ga yuborildi.")
        log_event("admin_reply", ADMIN_ID, f"to:{target_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# YANGI: BROADCAST — barcha foydalanuvchilarga xabar
# ═══════════════════════════════════════════════════════════════════════════════

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    await update.message.reply_text(
        "📢 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabarni yozing:\n\n"
        "/cancel — bekor qilish"
    )
    return BROADCAST_MSG


async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    text    = update.message.text
    sent    = 0
    failed  = 0
    for uid_str in list(users.keys()):
        try:
            await context.bot.send_message(int(uid_str), f"📢 <b>Yangilik!</b>\n\n{text}", parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"✅ Yuborildi: {sent} ta\n❌ Yuborilmadi: {failed} ta")
    log_event("broadcast", ADMIN_ID, f"sent:{sent}")
    return ConversationHandler.END


async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════════════════════
# YANGI: FOYDALANUVCHILAR RO'YXATI
# ═══════════════════════════════════════════════════════════════════════════════

async def users_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    total = len(users)
    lines = [f"👥 Jami foydalanuvchilar: <b>{total}</b>\n"]
    for uid_str, info in list(users.items())[-20:]:
        if isinstance(info, dict):
            name = info.get("name", "Noma'lum")
            lang = info.get("lang", "uz")
        else:
            name = "Noma'lum"
            lang = info
        lines.append(f"🆔 <code>{uid_str}</code> | {name} | {lang}")
    lines.append(f"\n<i>(Oxirgi 20 ta ko'rsatildi)</i>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════════════════
# YANGI: BUYURTMALAR RO'YXATI (admin uchun)
# ═══════════════════════════════════════════════════════════════════════════════

async def orders_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not orders:
        await update.message.reply_text("❌ Hali buyurtma yo'q.")
        return
    new_orders = [o for o in orders if o["status"] == "new"]
    lines = [
        f"📋 <b>Buyurtmalar</b>",
        f"Jami: {len(orders)} | 🆕 Yangi: {len(new_orders)}\n"
    ]
    for o in reversed(orders[-15:]):
        stat = ORDER_STATUSES.get(o["status"], {}).get("uz", o["status"])
        dt   = datetime.fromtimestamp(o["ts"]).strftime("%d.%m %H:%M")
        lines.append(
            f"#{o['id'][-6:]} | {o['user_name']} | "
            f"🥚{o['qty']}ta | {stat} | {dt}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════════════════
# E'LON QO'SHISH / O'CHIRISH
# ═══════════════════════════════════════════════════════════════════════════════

async def elon_photo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz.")
        return ConversationHandler.END
    context.user_data.clear()
    await update.message.reply_text(tr("send_photo", "uz"))
    return WAIT_PHOTO


async def elon_photo_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Iltimos rasm yuboring.")
        return WAIT_PHOTO
    context.user_data["new_ad"] = {
        "id": str(int(time.time() * 1000)),
        "photo_file_id": update.message.photo[-1].file_id,
        "buttons": [],
        "info_text": "",
        "views": 0,
    }
    await update.message.reply_text(tr("photo_received", "uz"))
    await update.message.reply_text(tr("write_ad", "uz"))
    return WAIT_TEXT


async def elon_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_ad"]["text"] = update.message.text
    context.user_data["selected_buttons"] = set()
    await update.message.reply_text(tr("ad_received", "uz"), reply_markup=_btn_sel_kb(set()))
    return SELECT_BUTTONS


def _btn_sel_kb(selected: set):
    rows, row = [], []
    for btn_id, info in BUTTONS_CATALOG.items():
        prefix = "✅ " if btn_id in selected else ""
        row.append(InlineKeyboardButton(prefix + info["label"]["uz"], callback_data=f"selbtn_{btn_id}"))
        if len(row) == 2:
            rows.append(row); row = []
    for cbtn_id, cbtn in custom_buttons.items():
        prefix = "✅ " if cbtn_id in selected else ""
        row.append(InlineKeyboardButton(prefix + cbtn["name"], callback_data=f"selbtn_c_{cbtn_id}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("✅ Tayyor", callback_data="selbtn_done")])
    return InlineKeyboardMarkup(rows)


async def select_buttons_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer(); return SELECT_BUTTONS
    data = q.data[len("selbtn_"):]
    selected = context.user_data.get("selected_buttons", set())
    if data == "done":
        await q.answer()
        new_ad = context.user_data["new_ad"]
        new_ad["buttons"] = list(selected)
        if "info" in selected:
            await q.edit_message_text(tr("ad_received", "uz"))
            await context.bot.send_message(q.message.chat_id, tr("write_info", "uz"))
            return WAIT_INFO
        ads.append(new_ad); save_ads()
        await q.edit_message_text(tr("ad_done_no_info", "uz"))
        await broadcast_new_ad(context, new_ad)
        log_event("new_ad", ADMIN_ID, new_ad["id"])
        return ConversationHandler.END
    selected.discard(data) if data in selected else selected.add(data)
    context.user_data["selected_buttons"] = selected
    await q.answer()
    await q.edit_message_reply_markup(reply_markup=_btn_sel_kb(selected))
    return SELECT_BUTTONS


async def info_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_ad = context.user_data["new_ad"]
    new_ad["info_text"] = update.message.text
    ads.append(new_ad); save_ads()
    await update.message.reply_text(tr("info_received", "uz"))
    await broadcast_new_ad(context, new_ad)
    log_event("new_ad", ADMIN_ID, new_ad["id"])
    return ConversationHandler.END


async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Bekor qilindi.")
    return ConversationHandler.END


async def broadcast_new_ad(context, ad):
    for uid_str, info in users.items():
        lang = info.get("lang", "uz") if isinstance(info, dict) else info
        try:
            await send_ad_to_chat(context, int(uid_str), ad, lang)
        except Exception as e:
            logger.warning(f"{uid_str} ga yuborib bo'lmadi: {e}")
    if CHANNEL_ID:
        try:
            await send_ad_to_chat(context, CHANNEL_ID, ad, "uz")
        except Exception as e:
            logger.warning(f"Kanalga yuborib bo'lmadi: {e}")


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not ads:
        await update.message.reply_text("❌ O'chirish uchun e'lonlar yo'q.")
        return
    rows = []
    for ad in ads:
        short = ad.get("text", "")[:40] + ("..." if len(ad.get("text", "")) > 40 else "")
        rows.append([InlineKeyboardButton(f"🗑 {short}", callback_data=f"deladconfirm_{ad['id']}")])
    rows.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="deladcancel")])
    await update.message.reply_text("🗑 Qaysi e'lonni o'chirmoqchisiz?", reply_markup=InlineKeyboardMarkup(rows))


async def delete_ad_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer(); return
    ad_id = q.data.split("_", 1)[1]
    ad = next((a for a in ads if a["id"] == ad_id), None)
    if not ad:
        await q.answer(); await q.edit_message_text("❌ E'lon topilmadi."); return
    short = ad.get("text", "")[:60] + ("..." if len(ad.get("text", "")) > 60 else "")
    await q.answer()
    await q.edit_message_text(
        f"⚠️ Tasdiqlaysizmi?\n\n📝 {short}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Ha, o'chir", callback_data=f"deladyes_{ad_id}"),
            InlineKeyboardButton("❌ Yo'q", callback_data="deladcancel"),
        ]])
    )


async def delete_ad_yes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer(); return
    global ads
    ad_id = q.data.split("_", 1)[1]
    deleted_ad = next((a for a in ads if a["id"] == ad_id), None)
    before = len(ads)
    ads = [a for a in ads if a["id"] != ad_id]
    await q.answer()
    if len(ads) != before:
        save_ads()
        await q.edit_message_text("✅ E'lon muvaffaqiyatli o'chirildi.")
        if deleted_ad:
            notify = f"🗑 E'lon o'chirildi:\n\n{deleted_ad.get('text','')[:60]}"
            for uid_str in list(users.keys()):
                try:
                    await context.bot.send_message(int(uid_str), notify)
                except Exception as e:
                    logger.warning(f"{uid_str} ga xabar yuborib bo'lmadi: {e}")
        log_event("delete_ad", ADMIN_ID, ad_id)
    else:
        await q.edit_message_text("❌ E'lon topilmadi.")


async def delete_ad_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("❌ O'chirish bekor qilindi.")


# ═══════════════════════════════════════════════════════════════════════════════
# TUGMA YARATISH
# ═══════════════════════════════════════════════════════════════════════════════

def _btn_type_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Link (URL)",    callback_data="btntype_link")],
        [InlineKeyboardButton("📝 Matn (xabar)",  callback_data="btntype_text")],
        [InlineKeyboardButton("📞 Telefon raqam", callback_data="btntype_phone")],
        [InlineKeyboardButton("❌ Bekor",          callback_data="btntype_cancel")],
    ])


async def button_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    context.user_data.clear()
    await update.message.reply_text(
        "🔘 Yangi tugma yaratish\n\n1️⃣ Tugma nomini yozing:\n(masalan: 📸 Instagram)"
    )
    return BTN_NAME


async def button_create_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_btn_name"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ Nom: <b>{context.user_data['new_btn_name']}</b>\n\n2️⃣ Tugma turini tanlang:",
        parse_mode="HTML",
        reply_markup=_btn_type_kb(),
    )
    return BTN_TYPE


async def button_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "btntype_cancel":
        context.user_data.clear()
        await q.edit_message_text("❌ Bekor qilindi.")
        return ConversationHandler.END
    chosen = q.data.split("_", 1)[1]
    context.user_data["new_btn_type"] = chosen
    prompts = {
        "link":  "3️⃣ Link (URL) yozing:\n\nMasalan: https://instagram.com/...",
        "text":  "3️⃣ Tugma bosilganda ko'rsatiladigan matnni yozing:",
        "phone": "3️⃣ Telefon raqamini yozing:\n\nMasalan: +998901234567",
    }
    await q.edit_message_text(prompts[chosen], parse_mode="HTML")
    return BTN_VALUE


async def button_create_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btn_name  = context.user_data.get("new_btn_name", "Tugma")
    btn_type  = context.user_data.get("new_btn_type", "text")
    btn_value = update.message.text.strip()
    if btn_type == "link" and not (btn_value.startswith("http://") or btn_value.startswith("https://")):
        await update.message.reply_text("❌ Link https:// bilan boshlanishi kerak!\n\nQaytadan yozing:")
        return BTN_VALUE
    btn_id = f"cb_{int(time.time())}"
    custom_buttons[btn_id] = {"name": btn_name, "btn_type": btn_type, "action_value": btn_value}
    save_custom_buttons()
    type_labels = {"link": "🔗 Link", "text": "📝 Matn", "phone": "📞 Telefon"}
    await update.message.reply_text(
        f"✅ Tugma yaratildi!\n\n🔘 Nom: <b>{btn_name}</b>\n"
        f"📌 Tur: {type_labels.get(btn_type, btn_type)}\n"
        f"📋 Qiymat: {btn_value[:80]}\n\nBu tugma endi barcha e'lonlarda ko'rinadi.",
        parse_mode="HTML",
    )
    log_event("new_button", ADMIN_ID, btn_name)
    return ConversationHandler.END


async def button_create_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END


async def button_delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not custom_buttons:
        await update.message.reply_text("❌ Hech qanday maxsus tugma yo'q.")
        return
    rows = []
    for btn_id, btn in custom_buttons.items():
        type_icon = {"link": "🔗", "text": "📝", "phone": "📞"}.get(btn.get("btn_type", "text"), "📝")
        rows.append([InlineKeyboardButton(f"🗑 {type_icon} {btn['name']}", callback_data=f"delbtn_{btn_id}")])
    rows.append([InlineKeyboardButton("❌ Bekor", callback_data="delbtncancel")])
    await update.message.reply_text("🗑 Qaysi tugmani o'chirmoqchisiz?", reply_markup=InlineKeyboardMarkup(rows))


async def button_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer(); return
    if q.data == "delbtncancel":
        await q.answer(); await q.edit_message_text("❌ Bekor qilindi."); return
    btn_id = q.data.split("_", 1)[1]
    btn    = custom_buttons.pop(btn_id, None)
    save_custom_buttons()
    await q.answer()
    if btn:
        await q.edit_message_text(f"✅ '{btn['name']}' tugmasi o'chirildi.")
        log_event("delete_button", ADMIN_ID, btn["name"])
    else:
        await q.edit_message_text("❌ Tugma topilmadi.")


# ═══════════════════════════════════════════════════════════════════════════════
# BUYRUQ YARATISH
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    context.user_data.clear()
    await update.message.reply_text(
        "⚙️ Juft buyruq yaratish\n\n"
        "1️⃣ Birinchi buyruq nomini yozing (/ belgisiz):\n<i>Masalan: narx</i>",
        parse_mode="HTML",
    )
    return CMD_NAME1


async def cmd_create_name1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip().lstrip("/").replace(" ", "_").lower()
    context.user_data["cmd1_name"] = name
    await update.message.reply_text(
        f"✅ Birinchi buyruq: <b>/{name}</b>\n\n2️⃣ /{name} bosilganda qanday javob?",
        parse_mode="HTML",
    )
    return CMD_RESP1


async def cmd_create_resp1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cmd1_resp"] = update.message.text.strip()
    name1 = context.user_data["cmd1_name"]
    await update.message.reply_text(
        f"✅ Birinchi buyruq saqlandi!\n\n3️⃣ Ikkinchi buyruq nomini yozing:\n<i>Masalan: {name1}_batafsil</i>",
        parse_mode="HTML",
    )
    return CMD_NAME2


async def cmd_create_name2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip().lstrip("/").replace(" ", "_").lower()
    context.user_data["cmd2_name"] = name
    await update.message.reply_text(
        f"✅ Ikkinchi buyruq: <b>/{name}</b>\n\n4️⃣ /{name} bosilganda qanday javob?",
        parse_mode="HTML",
    )
    return CMD_RESP2


async def cmd_create_resp2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd1_name = context.user_data.get("cmd1_name", "cmd1")
    cmd1_resp = context.user_data.get("cmd1_resp", "")
    cmd2_name = context.user_data.get("cmd2_name", "cmd2")
    cmd2_resp = update.message.text.strip()
    custom_commands[cmd1_name] = {"response_text": cmd1_resp}
    custom_commands[cmd2_name] = {"response_text": cmd2_resp}
    save_custom_commands()
    await update.message.reply_text(
        f"✅ Ikkala buyruq yaratildi!\n\n"
        f"📌 <b>/{cmd1_name}</b>\n{cmd1_resp[:80]}\n\n"
        f"📌 <b>/{cmd2_name}</b>\n{cmd2_resp[:80]}",
        parse_mode="HTML",
    )
    log_event("new_command", ADMIN_ID, f"{cmd1_name}+{cmd2_name}")
    return ConversationHandler.END


async def cmd_create_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END


async def cmd_delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not custom_commands:
        await update.message.reply_text("❌ Hech qanday maxsus buyruq yo'q.")
        return
    rows = []
    for cname in custom_commands:
        rows.append([InlineKeyboardButton(f"🗑 /{cname}", callback_data=f"delcmd_{cname}")])
    rows.append([InlineKeyboardButton("❌ Bekor", callback_data="delcmdcancel")])
    await update.message.reply_text("🗑 Qaysi buyruqni o'chirmoqchisiz?", reply_markup=InlineKeyboardMarkup(rows))


async def cmd_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer(); return
    if q.data == "delcmdcancel":
        await q.answer(); await q.edit_message_text("❌ Bekor qilindi."); return
    cname = q.data.split("_", 1)[1]
    custom_commands.pop(cname, None)
    save_custom_commands()
    await q.answer()
    await q.edit_message_text(f"✅ /{cname} buyrug'i o'chirildi.")
    log_event("delete_command", ADMIN_ID, cname)


# ═══════════════════════════════════════════════════════════════════════════════
# FAOLLIK JADVALI (kengaytirilgan)
# ═══════════════════════════════════════════════════════════════════════════════

async def faollik_jadvali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    now        = time.time()
    total      = len(users)
    cutoff_24h = now - 86400

    new_24h    = sum(1 for e in events if e["type"] == "join" and e["ts"] > cutoff_24h)
    active_ids = {e["user_id"] for e in events if e["ts"] > cutoff_24h and e["type"] in ("message", "join")}
    active     = len(active_ids)
    inactive   = total - active

    total_orders   = len(orders)
    new_orders     = sum(1 for o in orders if o["status"] == "new")
    done_orders    = sum(1 for o in orders if o["status"] == "done")

    hourly = {}
    for i in range(24):
        t0    = now - (24 - i) * 3600
        t1    = t0 + 3600
        label = datetime.fromtimestamp(t0).strftime("%H:00")
        count = sum(1 for e in events if t0 <= e["ts"] < t1)
        hourly[label] = count

    lines = [
        "📊 <b>Faollik jadvali (oxirgi 24 soat)</b>",
        "",
        f"👥 Jami foydalanuvchilar: <b>{total}</b>",
        f"🟢 Faol (24h): <b>{active}</b>",
        f"🔴 Faol emas (24h): <b>{inactive}</b>",
        f"🆕 Yangi a'zolar (24h): <b>{new_24h}</b>",
        "",
        f"🛍 Jami buyurtmalar: <b>{total_orders}</b>",
        f"🆕 Yangi buyurtmalar: <b>{new_orders}</b>",
        f"✅ Bajarilgan: <b>{done_orders}</b>",
        "",
        "⏰ Soatlik faollik:",
        "─" * 28,
    ]
    mx = max(hourly.values(), default=1) or 1
    for lbl, cnt in hourly.items():
        bar = "█" * int(cnt / mx * 14) + "░" * (14 - int(cnt / mx * 14))
        lines.append(f"<code>{lbl} {bar} {cnt}</code>")

    ev_24h = [e for e in events if e["ts"] > cutoff_24h]
    type_counts: dict = {}
    for e in ev_24h:
        type_counts[e["type"]] = type_counts.get(e["type"], 0) + 1

    emoji_map = {
        "join":           "🆕 Yangi a'zo",
        "message":        "✉️ Xabarlar",
        "new_ad":         "📢 Yangi e'lonlar",
        "delete_ad":      "🗑 O'chirilgan e'lonlar",
        "admin_reply":    "💬 Admin javoblari",
        "new_button":     "🔘 Yangi tugmalar",
        "delete_button":  "🗑 O'chirilgan tugmalar",
        "new_command":    "⚙️ Yangi buyruqlar",
        "delete_command": "🗑 O'chirilgan buyruqlar",
        "new_order":      "🛍 Yangi buyurtmalar",
        "order_status":   "📦 Holat o'zgarishi",
        "broadcast":      "📢 Broadcast",
    }
    lines += ["", "📋 Voqealar (24h):"]
    if type_counts:
        for etype, cnt in type_counts.items():
            lines.append(f"  {emoji_map.get(etype, etype)}: <b>{cnt}</b>")
    else:
        lines.append("  Hozircha voqealar yo'q.")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════════════════
# CALLBACK HANDLERLARI
# ═══════════════════════════════════════════════════════════════════════════════

async def phone_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await context.bot.send_message(q.message.chat_id, f"{tr('calling', get_lang(q.from_user.id))}{PHONE_NUMBER}")


async def info_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang  = get_lang(q.from_user.id)
    ad_id = q.data.split("_", 1)[1]
    ad = next((a for a in ads if a["id"] == ad_id), None)
    await q.answer()
    if ad and ad.get("info_text"):
        await context.bot.send_message(q.message.chat_id, f"{tr('info_btn_msg', lang)}\n\n{get_ad_info_text(ad, lang)}")
    else:
        await context.bot.send_message(q.message.chat_id, tr("no_info_yet", lang))


async def tuxumai_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang  = get_lang(q.from_user.id)
    ad_id = q.data.split("_", 1)[1]
    set_state(q.from_user.id, "tuxumai")
    context.user_data["tuxumai_ad_id"] = ad_id
    await q.answer()
    await context.bot.send_message(q.message.chat_id, tr("tuxumai_greeting", lang))


async def delivery_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang = get_lang(q.from_user.id)
    await q.answer()
    await context.bot.send_message(q.message.chat_id, tr("delivery_location", lang))
    await context.bot.send_location(chat_id=q.message.chat_id, latitude=ADMIN_LATITUDE, longitude=ADMIN_LONGITUDE)


async def location_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang = get_lang(q.from_user.id)
    context.user_data["awaiting_location_for_ad"] = q.data.split("_", 1)[1]
    await q.answer()
    loc_kb = ReplyKeyboardMarkup(
        [[KeyboardButton(tr("location_btn_label", lang), request_location=True)]],
        resize_keyboard=True, one_time_keyboard=True,
    )
    await context.bot.send_message(q.message.chat_id, tr("send_location", lang), reply_markup=loc_kb)


async def text_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang   = get_lang(q.from_user.id)
    btn_id = q.data.split("_", 2)[2]
    cat = BUTTONS_CATALOG.get(btn_id)
    await q.answer()
    if cat:
        txt = cat.get("text", {}).get(lang, cat.get("text", {}).get("uz", ""))
        await context.bot.send_message(q.message.chat_id, txt)


async def custom_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cbtn_id = q.data.split("_", 1)[1]
    cbtn = custom_buttons.get(cbtn_id)
    if not cbtn:
        return
    btn_type = cbtn.get("btn_type", "text")
    if btn_type == "phone":
        await context.bot.send_message(q.message.chat_id, f"📞 Telefon: {cbtn.get('action_value', '')}")
    else:
        await context.bot.send_message(q.message.chat_id, cbtn.get("action_value", ""))


# ═══════════════════════════════════════════════════════════════════════════════
# LOCATION VA VOICE HANDLERLARI
# ═══════════════════════════════════════════════════════════════════════════════

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user  = update.effective_user
    lang  = get_lang(user.id)

    # Buyurtma jarayonida joylashuv
    if get_state(user.id) == "ordering":
        context.user_data["order_address"] = f"📍 {update.message.location.latitude}, {update.message.location.longitude}"
        context.user_data["order_location"] = {
            "lat": update.message.location.latitude,
            "lon": update.message.location.longitude
        }
        await update.message.reply_text(tr("order_ask_phone", lang), reply_markup=lang_reply_keyboard())
        return ORDER_PHONE

    loc   = update.message.location
    ad_id = context.user_data.pop("awaiting_location_for_ad", "nomalum")
    username = f"@{user.username}" if user.username else f"id:{user.id}"
    lat, lon = loc.latitude, loc.longitude
    try:
        await context.bot.send_location(ADMIN_ID, latitude=lat, longitude=lon)
        await context.bot.send_message(
            ADMIN_ID,
            f"📍 Joylashuv (e'lon: {ad_id})\n"
            f"👤 {user.full_name or ''} ({username})\n"
            f"🗺 https://maps.google.com/maps?q={lat},{lon}"
        )
    except Exception as e:
        logger.warning(f"Adminga joylashuv yuborib bo'lmadi: {e}")
    await update.message.reply_text(tr("location_sent", lang), reply_markup=lang_reply_keyboard())


async def voice_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_lang(user.id)
    voice_file = await context.bot.get_file(update.message.voice.file_id)
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        await voice_file.download_to_drive(tmp_path)
        transcribed = transcribe_voice(tmp_path)
    finally:
        os.unlink(tmp_path)
    if not transcribed:
        await update.message.reply_text("❌ Ovozni tanib bo'lmadi, qayta urinib ko'ring.")
        return
    set_mode(user.id, "voice")
    ad = ads[-1] if ads else None
    reply = get_ai_reply(ad, lang, transcribed)
    if reply:
        await send_ai_response(context, update.effective_chat.id, user.id, reply, lang)


# ═══════════════════════════════════════════════════════════════════════════════
# UMUMIY XABAR HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

async def generic_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_lang(user.id)
    text = update.message.text or ""
    tl   = text.lower()

    voice_on  = ["ovozli javob ber", "voice", "ovoz", "speak", "голос", "говори"]
    voice_off = ["ovosiz", "matnli", "text", "без голоса", "without voice", "текст"]
    if any(t in tl for t in voice_on):
        set_mode(user.id, "voice"); await update.message.reply_text("🎙 Endi ovozli javob beraman!"); return
    if any(t in tl for t in voice_off):
        set_mode(user.id, "text");  await update.message.reply_text("💬 Endi matnli javob beraman!"); return

    if await lang_button_pressed(update, context):
        return

    if text.startswith("/"):
        cmd = text.lstrip("/").split()[0].lower()
        if cmd in custom_commands:
            await update.message.reply_text(custom_commands[cmd]["response_text"])
            log_event("message", user.id, f"cmd:{cmd}")
            return

    # Foydalanuvchi adminga xabar yozmoqda
    if get_state(user.id) == "writing_message":
        username = f"@{user.username}" if user.username else f"id:{user.id}"
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"✉️ <b>Foydalanuvchi xabari</b>\n"
                f"👤 {user.full_name or ''} ({username})\n"
                f"🆔 <code>{user.id}</code>\n\n"
                f"💬 {text}\n\n"
                f"↩️ Javob: /reply {user.id} &lt;matn&gt;",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"Adminga xabar yuborib bo'lmadi: {e}")
        set_state(user.id, "normal")
        await update.message.reply_text(tr("message_sent", lang), reply_markup=lang_reply_keyboard())
        log_event("message", user.id, text[:50])
        return

    if get_state(user.id) == "tuxumai":
        ad_id = context.user_data.get("tuxumai_ad_id")
        ad    = next((a for a in ads if a["id"] == ad_id), None) if ad_id else (ads[-1] if ads else None)
        reply = get_ai_reply(ad, lang, text)
        if reply:
            await send_ai_response(context, update.effective_chat.id, user.id, reply, lang)
        log_event("message", user.id, "tuxumai")
        return

    # Oddiy xabar — adminga yuborish
    username = f"@{user.username}" if user.username else f"id:{user.id}"
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"✉️ <b>Yangi xabar</b>\n"
            f"👤 {user.full_name or ''} ({username})\n"
            f"🆔 <code>{user.id}</code>\n\n"
            f"💬 {text}\n\n"
            f"↩️ Javob: /reply {user.id} &lt;matn&gt;",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning(f"Adminga xabar yuborib bo'lmadi: {e}")

    log_event("message", user.id, text[:50])
    await update.message.reply_text(tr("contact_sent", lang))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # E'lon qo'shish
    elon_conv = ConversationHandler(
        entry_points=[CommandHandler("elon_photo", elon_photo_start)],
        states={
            WAIT_PHOTO:     [MessageHandler(filters.PHOTO, elon_photo_received)],
            WAIT_TEXT:      [MessageHandler(filters.TEXT & ~filters.COMMAND, elon_text_received)],
            SELECT_BUTTONS: [CallbackQueryHandler(select_buttons_callback, pattern=r"^selbtn_")],
            WAIT_INFO:      [MessageHandler(filters.TEXT & ~filters.COMMAND, info_text_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel_admin)],
        allow_reentry=True,
    )

    # Tugma yaratish
    btn_conv = ConversationHandler(
        entry_points=[CommandHandler("button", button_create_start)],
        states={
            BTN_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, button_create_name)],
            BTN_TYPE:  [CallbackQueryHandler(button_type_callback, pattern=r"^btntype_")],
            BTN_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, button_create_value)],
        },
        fallbacks=[CommandHandler("cancel", button_create_cancel)],
        allow_reentry=True,
    )

    # Buyruq yaratish
    cmd_conv = ConversationHandler(
        entry_points=[CommandHandler("cmd", cmd_create_start)],
        states={
            CMD_NAME1: [MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_create_name1)],
            CMD_RESP1: [MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_create_resp1)],
            CMD_NAME2: [MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_create_name2)],
            CMD_RESP2: [MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_create_resp2)],
        },
        fallbacks=[CommandHandler("cancel", cmd_create_cancel)],
        allow_reentry=True,
    )

    # YANGI: Buyurtma conversation
    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(order_button_callback, pattern=r"^order_")],
        states={
            ORDER_QTY:     [MessageHandler(filters.TEXT & ~filters.COMMAND, order_qty_received)],
            ORDER_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, order_address_received),
                MessageHandler(filters.LOCATION, order_address_received),
            ],
            ORDER_PHONE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, order_phone_received)],
        },
        fallbacks=[
            CallbackQueryHandler(order_cancel_callback, pattern=r"^order_cancel$"),
            CommandHandler("cancel", order_cancel_callback),
        ],
        allow_reentry=True,
    )

    # YANGI: Broadcast conversation
    broadcast_conv = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_start)],
        states={
            BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_send)],
        },
        fallbacks=[CommandHandler("cancel", broadcast_cancel)],
        allow_reentry=True,
    )

    # Buyruqlar
    app.add_handler(CommandHandler("start",      start))
    app.add_handler(CommandHandler("delete",     delete_command))
    app.add_handler(CommandHandler("reply",      admin_reply_command))
    app.add_handler(CommandHandler("deletebtn",  button_delete_command))
    app.add_handler(CommandHandler("deletecmd",  cmd_delete_command))
    app.add_handler(CommandHandler("fj",         faollik_jadvali))
    app.add_handler(CommandHandler("users",      users_list_command))       # YANGI
    app.add_handler(CommandHandler("orders",     orders_list_command))      # YANGI
    app.add_handler(CommandHandler("myorders",   my_orders_command))        # YANGI

    # Conversation handlerlar
    app.add_handler(elon_conv)
    app.add_handler(btn_conv)
    app.add_handler(cmd_conv)
    app.add_handler(order_conv)       # YANGI
    app.add_handler(broadcast_conv)   # YANGI

    # Callback handlerlar
    app.add_handler(CallbackQueryHandler(set_language_callback,      pattern=r"^setlang_"))
    app.add_handler(CallbackQueryHandler(phone_button_callback,      pattern=r"^phone_"))
    app.add_handler(CallbackQueryHandler(info_button_callback,       pattern=r"^info_"))
    app.add_handler(CallbackQueryHandler(tuxumai_button_callback,    pattern=r"^tuxumai_"))
    app.add_handler(CallbackQueryHandler(delivery_button_callback,   pattern=r"^delivery_"))
    app.add_handler(CallbackQueryHandler(location_button_callback,   pattern=r"^location_"))
    app.add_handler(CallbackQueryHandler(text_button_callback,       pattern=r"^btn_"))
    app.add_handler(CallbackQueryHandler(custom_button_callback,     pattern=r"^custombtn_"))
    app.add_handler(CallbackQueryHandler(delete_ad_confirm_callback, pattern=r"^deladconfirm_"))
    app.add_handler(CallbackQueryHandler(delete_ad_yes_callback,     pattern=r"^deladyes_"))
    app.add_handler(CallbackQueryHandler(delete_ad_cancel_callback,  pattern=r"^deladcancel$"))
    app.add_handler(CallbackQueryHandler(button_delete_callback,     pattern=r"^(delbtn_|delbtncancel)"))
    app.add_handler(CallbackQueryHandler(cmd_delete_callback,        pattern=r"^(delcmd_|delcmdcancel)"))
    app.add_handler(CallbackQueryHandler(order_status_callback,      pattern=r"^ordstatus_"))   # YANGI
    app.add_handler(CallbackQueryHandler(msgadmin_button_callback,   pattern=r"^msgadmin_"))    # YANGI

    # Media handlerlar
    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(MessageHandler(filters.VOICE,    voice_message_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generic_message_handler))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
