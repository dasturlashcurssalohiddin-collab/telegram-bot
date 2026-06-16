# -*- coding: utf-8 -*-

import json
import os
import time
import logging
import tempfile
import asyncio
from datetime import datetime, timedelta
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
    "write_contact":  {"uz": "✍️ Xabaringizni yozing, sotuvchiga yuboriladi:", "en": "✍️ Write your message:", "ru": "✍️ Напишите сообщение продавцу:", "de": "✍️ Nachricht an den Verkäufer:"},
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
}

PHONE_NUMBER = "+998951000130"

TTS_VOICES = {
    "uz": "uz-UZ-MadinaNeural",
    "en": "en-US-AriaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "de": "de-DE-KatjaNeural",
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
# custom_buttons: {btn_id: {name, action_type, action_value}}
custom_buttons  = load_json(BUTTONS_FILE, {})
# custom_commands: {cmd_name: {description, response_text}}
custom_commands = load_json(COMMANDS_FILE, {})
# events: list of {ts, type, user_id, detail}
events          = load_json(EVENTS_FILE, [])

user_modes: dict  = {}
user_states: dict = {}
# pending_reply: {admin_chat_id: target_user_id}  — /reply oqimi uchun
pending_reply: dict = {}


def save_ads():            save_json(ADS_FILE, ads)
def save_users():          save_json(USERS_FILE, users)
def save_custom_buttons(): save_json(BUTTONS_FILE, custom_buttons)
def save_custom_commands():save_json(COMMANDS_FILE, custom_commands)
def save_events():         save_json(EVENTS_FILE, events)
def get_lang(uid):         return users.get(str(uid), "uz")
def get_mode(uid):         return user_modes.get(str(uid), "text")
def set_mode(uid, mode):   user_modes[str(uid)] = mode
def get_state(uid):        return user_states.get(str(uid), "normal")
def set_state(uid, state): user_states[str(uid)] = state


def log_event(event_type: str, user_id: int, detail: str = ""):
    events.append({
        "ts": time.time(),
        "type": event_type,
        "user_id": user_id,
        "detail": detail,
    })
    # Eski eventlarni tozalash (7 kundan eskisi)
    cutoff = time.time() - 7 * 86400
    events[:] = [e for e in events if e["ts"] > cutoff]
    save_events()


# ─── ConversationHandler holatlari ───────────────────────────────────────────
WAIT_PHOTO, WAIT_TEXT, SELECT_BUTTONS, WAIT_INFO = range(4)

# /button conversation holatlari
BTN_NAME, BTN_ACTION_TYPE, BTN_ACTION_VALUE = range(10, 13)

# /cmd conversation holatlari
CMD_NAME, CMD_DESC, CMD_RESPONSE = range(20, 23)

LANG_NAME_TO_CODE = {v: k for k, v in LANG_NAMES.items()}


# ─── Yordamchi funksiyalar ────────────────────────────────────────────────────

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
    # Standart tugmalar
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
                f"phone_{ad['id']}"    if t == "phone"            else
                f"info_{ad['id']}"     if t == "info"             else
                f"tuxumai_{ad['id']}"  if t == "tuxumai"          else
                f"delivery_{ad['id']}" if t == "delivery"         else
                f"location_{ad['id']}" if t == "location_request" else
                f"btn_{ad['id']}_{btn_id}"
            )
            row.append(InlineKeyboardButton(label, callback_data=cb))
        if len(row) == 2:
            rows.append(row); row = []
    # Maxsus (custom) tugmalar
    for cbtn_id, cbtn in custom_buttons.items():
        label = cbtn.get("name", cbtn_id)
        atype = cbtn.get("action_type", "text")
        if atype == "url":
            row.append(InlineKeyboardButton(label, url=cbtn.get("action_value", "")))
        elif atype == "text":
            row.append(InlineKeyboardButton(label, callback_data=f"custombtn_{cbtn_id}"))
        elif atype == "command":
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


# ─── TTS / STT ───────────────────────────────────────────────────────────────

async def _tts_async(text: str, lang: str, output_path: str):
    voice = TTS_VOICES.get(lang, "en-US-AriaNeural")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def text_to_speech(text: str, lang: str) -> bytes | None:
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


def transcribe_voice(file_path: str) -> str | None:
    try:
        with open(file_path, "rb") as f:
            result = ai_client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=f,
            )
        return result.text
    except Exception as e:
        logger.warning(f"STT xatosi: {e}")
        return None


def get_ai_reply(ad, lang: str, user_message: str) -> str | None:
    ad_text = ad.get("text", "") if ad else ""
    ad_info = ad.get("info_text", "") if ad else ""
    system_prompt = (
        "Sening isming TuxumAI. Sen aqlli yordamchi sun'iy intellektsan. "
        "Har qanday savolga javob ber — mavzu cheklovlarsiz. "
        "Agar 'sen kimsan' deb so'rashsa — 'Men TuxumAI man' de. "
        "Bu tuxum sotish Telegram boti.\n\n"
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
                tmp.write(audio)
                tmp_path = tmp.name
            try:
                with open(tmp_path, "rb") as f:
                    await context.bot.send_voice(chat_id=chat_id, voice=f)
            finally:
                os.unlink(tmp_path)
            return
    await context.bot.send_message(chat_id=chat_id, text=f"🤖 TuxumAI:\n\n{text}")


# ─── /start ──────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid  = user.id
    lang = users.get(str(uid), "uz")
    set_state(uid, "normal")

    # Yangi foydalanuvchi ro'yxatdan o'tishi
    if str(uid) not in users:
        users[str(uid)] = "uz"
        save_users()
        log_event("join", uid, user.full_name or "")

    await update.message.reply_text(tr("choose_lang", lang), reply_markup=lang_inline_keyboard())


# ─── Til ─────────────────────────────────────────────────────────────────────

async def set_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang_code = query.data.split("_", 1)[1]
    users[str(query.from_user.id)] = lang_code
    save_users()
    await query.edit_message_text(tr("lang_set", lang_code))
    await context.bot.send_message(query.message.chat_id, tr("lang_set", lang_code), reply_markup=lang_reply_keyboard())
    await send_all_ads(context, query.message.chat_id, lang_code)


async def lang_button_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    text = update.message.text
    if text in LANG_NAME_TO_CODE:
        lang_code = LANG_NAME_TO_CODE[text]
        users[str(update.effective_user.id)] = lang_code
        save_users()
        await update.message.reply_text(tr("lang_set", lang_code), reply_markup=lang_reply_keyboard())
        await send_all_ads(context, update.effective_chat.id, lang_code)
        return True
    return False


# ─── Standart tugma callbacklari ─────────────────────────────────────────────

async def phone_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await context.bot.send_message(q.message.chat_id, f"{tr('calling', get_lang(q.from_user.id))}{PHONE_NUMBER}")


async def info_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang = get_lang(q.from_user.id)
    ad_id = q.data.split("_", 1)[1]
    ad = next((a for a in ads if a["id"] == ad_id), None)
    await q.answer()
    if ad and ad.get("info_text"):
        await context.bot.send_message(q.message.chat_id, f"{tr('info_btn_msg', lang)}\n\n{get_ad_info_text(ad, lang)}")
    else:
        await context.bot.send_message(q.message.chat_id, tr("no_info_yet", lang))


async def tuxumai_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang = get_lang(q.from_user.id)
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
    lang = get_lang(q.from_user.id)
    btn_id = q.data.split("_", 2)[2]
    cat = BUTTONS_CATALOG.get(btn_id)
    await q.answer()
    if cat:
        txt = cat.get("text", {}).get(lang, cat.get("text", {}).get("uz", ""))
        await context.bot.send_message(q.message.chat_id, txt)


async def custom_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maxsus tugmalar bosilganda"""
    q = update.callback_query
    cbtn_id = q.data.split("_", 1)[1]
    cbtn = custom_buttons.get(cbtn_id)
    await q.answer()
    if not cbtn:
        return
    atype = cbtn.get("action_type", "text")
    value = cbtn.get("action_value", "")
    if atype in ("text", "command"):
        await context.bot.send_message(q.message.chat_id, value)


# ─── Joylashuv ───────────────────────────────────────────────────────────────

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_lang(user.id)
    loc  = update.message.location
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


# ─── Ovoz ────────────────────────────────────────────────────────────────────

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


# ─── /delete — e'lonni o'chirish (foydalanuvchilarda ham) ───────────────────

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
            InlineKeyboardButton("❌ Yo'q",       callback_data="deladcancel"),
        ]])
    )


async def delete_ad_yes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """E'lonni o'chirish + barcha foydalanuvchilarga xabar berish"""
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer(); return
    global ads
    ad_id = q.data.split("_", 1)[1]
    before = len(ads)
    deleted_ad = next((a for a in ads if a["id"] == ad_id), None)
    ads = [a for a in ads if a["id"] != ad_id]
    await q.answer()
    if len(ads) != before:
        save_ads()
        await q.edit_message_text("✅ E'lon muvaffaqiyatli o'chirildi.")
        # Barcha foydalanuvchilarga o'chirilgan e'lon haqida xabar berish
        if deleted_ad:
            deleted_text = deleted_ad.get("text", "")[:50]
            notify_text = f"🗑 E'lon o'chirildi:\n\n{deleted_text}"
            for uid_str in list(users.keys()):
                try:
                    await context.bot.send_message(int(uid_str), notify_text)
                except Exception as e:
                    logger.warning(f"{uid_str} ga o'chirish xabari yuborib bo'lmadi: {e}")
        log_event("delete_ad", ADMIN_ID, ad_id)
    else:
        await q.edit_message_text("❌ E'lon topilmadi.")


async def delete_ad_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("❌ O'chirish bekor qilindi.")


# ─── E'lon qo'shish (ConversationHandler) ────────────────────────────────────

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
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("✅ Tayyor", callback_data="selbtn_done")])
    return InlineKeyboardMarkup(rows)


async def select_buttons_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer(); return SELECT_BUTTONS
    data = q.data.split("_", 1)[1]
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
    for uid_str, lang in users.items():
        try:
            await send_ad_to_chat(context, int(uid_str), ad, lang)
        except Exception as e:
            logger.warning(f"{uid_str} ga yuborib bo'lmadi: {e}")
    if CHANNEL_ID:
        try:
            await send_ad_to_chat(context, CHANNEL_ID, ad, "uz")
        except Exception as e:
            logger.warning(f"Kanalga yuborib bo'lmadi: {e}")


# ─── /reply — admin foydalanuvchiga javob beradi ─────────────────────────────
# Eski /reply <id> <matn> qoladi, + yangi oqim: /reply → ID so'rash → javob

async def admin_reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin foydalanuvchiga javob berish: /reply <user_id> <matn>"""
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "❌ Foydalanish: /reply <user_id> <matn>\n\nMasalan:\n/reply 123456789 Salom, javob shу!"
        )
        return
    try:
        target_id  = int(args[0])
        reply_text = " ".join(args[1:])
        await context.bot.send_message(target_id, f"💬 Admin javobi:\n\n{reply_text}")
        await update.message.reply_text(f"✅ Javob {target_id} ga yuborildi.")
        log_event("admin_reply", ADMIN_ID, f"to:{target_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {e}")


# ─── /button — maxsus tugma yaratish ─────────────────────────────────────────

async def button_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin yangi maxsus tugma yaratishni boshlaydi"""
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    await update.message.reply_text(
        "🔘 Yangi tugma yaratish\n\n"
        "1️⃣ Tugma nomini yozing (masalan: 💬 Savol bering):"
    )
    return BTN_NAME


async def button_create_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_btn_name"] = update.message.text.strip()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Matn ko'rsatsin", callback_data="btntype_text")],
        [InlineKeyboardButton("🌐 URL ochsin",       callback_data="btntype_url")],
        [InlineKeyboardButton("📋 Buyruq ishlatsin", callback_data="btntype_command")],
    ])
    await update.message.reply_text("2️⃣ Tugma nima qilsin?", reply_markup=kb)
    return BTN_ACTION_TYPE


async def button_create_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    atype = q.data.split("_", 1)[1]
    context.user_data["new_btn_type"] = atype
    prompts = {
        "text":    "3️⃣ Ko'rsatiladigan matnni yozing:",
        "url":     "3️⃣ URL manzilini yozing (https://...):",
        "command": "3️⃣ Javob matnini yozing (buyruq bosilganda ko'rsatiladi):",
    }
    await q.edit_message_text(prompts.get(atype, "3️⃣ Qiymatni yozing:"))
    return BTN_ACTION_VALUE


async def button_create_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value    = update.message.text.strip()
    btn_name = context.user_data.get("new_btn_name", "Tugma")
    btn_type = context.user_data.get("new_btn_type", "text")
    btn_id   = f"cb_{int(time.time())}"
    custom_buttons[btn_id] = {
        "name": btn_name,
        "action_type": btn_type,
        "action_value": value,
    }
    save_custom_buttons()
    await update.message.reply_text(
        f"✅ Tugma yaratildi!\n\n"
        f"🔘 Nom: {btn_name}\n"
        f"🔧 Turi: {btn_type}\n"
        f"📋 ID: {btn_id}\n\n"
        f"Bu tugma endi barcha e'lonlarda ko'rinadi."
    )
    log_event("new_button", ADMIN_ID, btn_name)
    return ConversationHandler.END


async def button_create_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END


# ─── /-button — tugmani o'chirish ────────────────────────────────────────────

async def button_delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin /deletebtn - maxsus tugmani o'chiradi"""
    if update.effective_user.id != ADMIN_ID:
        return
    if not custom_buttons:
        await update.message.reply_text("❌ Hech qanday maxsus tugma yo'q.")
        return
    rows = []
    for btn_id, btn in custom_buttons.items():
        rows.append([InlineKeyboardButton(
            f"🗑 {btn['name']}",
            callback_data=f"delbtn_{btn_id}"
        )])
    rows.append([InlineKeyboardButton("❌ Bekor", callback_data="delbtncancel")])
    await update.message.reply_text(
        "🗑 Qaysi tugmani o'chirmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(rows)
    )


async def button_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer(); return
    if q.data == "delbtncancel":
        await q.answer()
        await q.edit_message_text("❌ Bekor qilindi.")
        return
    btn_id = q.data.split("_", 1)[1]
    btn = custom_buttons.pop(btn_id, None)
    save_custom_buttons()
    await q.answer()
    if btn:
        await q.edit_message_text(f"✅ '{btn['name']}' tugmasi o'chirildi.")
        log_event("delete_button", ADMIN_ID, btn["name"])
    else:
        await q.edit_message_text("❌ Tugma topilmadi.")


# ─── /cmd — maxsus buyruq yaratish ───────────────────────────────────────────

async def cmd_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/cmd buyrug'i: yangi maxsus buyruq yaratish"""
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    await update.message.reply_text(
        "⚙️ Yangi buyruq yaratish\n\n"
        "1️⃣ Buyruq nomini yozing (/ belgisiz, masalan: narx):"
    )
    return CMD_NAME


async def cmd_create_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip().lstrip("/").replace(" ", "_").lower()
    context.user_data["new_cmd_name"] = name
    await update.message.reply_text(
        f"✅ Buyruq nomi: /{name}\n\n"
        "2️⃣ Qisqa tavsif yozing (foydalanuvchiga ko'rsatiladi):"
    )
    return CMD_DESC


async def cmd_create_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_cmd_desc"] = update.message.text.strip()
    await update.message.reply_text("3️⃣ Bu buyruq bosilganda qanday matn ko'rsatilsin?")
    return CMD_RESPONSE


async def cmd_create_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd_name = context.user_data.get("new_cmd_name", "cmd")
    cmd_desc = context.user_data.get("new_cmd_desc", "")
    cmd_resp = update.message.text.strip()
    custom_commands[cmd_name] = {
        "description": cmd_desc,
        "response_text": cmd_resp,
    }
    save_custom_commands()
    await update.message.reply_text(
        f"✅ Buyruq yaratildi!\n\n"
        f"📌 /{cmd_name} — {cmd_desc}\n\n"
        f"Javob matni:\n{cmd_resp}"
    )
    log_event("new_command", ADMIN_ID, cmd_name)
    return ConversationHandler.END


async def cmd_create_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END


# ─── /-cmd — maxsus buyruqni o'chirish ───────────────────────────────────────

async def cmd_delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not custom_commands:
        await update.message.reply_text("❌ Hech qanday maxsus buyruq yo'q.")
        return
    rows = []
    for cname, cdata in custom_commands.items():
        rows.append([InlineKeyboardButton(
            f"🗑 /{cname} — {cdata.get('description','')}",
            callback_data=f"delcmd_{cname}"
        )])
    rows.append([InlineKeyboardButton("❌ Bekor", callback_data="delcmdcancel")])
    await update.message.reply_text(
        "🗑 Qaysi buyruqni o'chirmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(rows)
    )


async def cmd_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer(); return
    if q.data == "delcmdcancel":
        await q.answer()
        await q.edit_message_text("❌ Bekor qilindi.")
        return
    cname = q.data.split("_", 1)[1]
    cdata = custom_commands.pop(cname, None)
    save_custom_commands()
    await q.answer()
    if cdata:
        await q.edit_message_text(f"✅ /{cname} buyrug'i o'chirildi.")
        log_event("delete_command", ADMIN_ID, cname)
    else:
        await q.edit_message_text("❌ Buyruq topilmadi.")


# ─── /fj — faollik jadvali ───────────────────────────────────────────────────

async def faollik_jadvali(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    now = time.time()
    total_users = len(users)

    # 24 soat ichidagi yangi foydalanuvchilar
    cutoff_24h = now - 86400
    new_in_24h = sum(
        1 for e in events
        if e["type"] == "join" and e["ts"] > cutoff_24h
    )

    # Faol foydalanuvchilar (24 soatda xabar yuborganlar)
    # events orqali hisoblash
    active_ids_24h = set(
        e["user_id"] for e in events
        if e["ts"] > cutoff_24h and e["type"] in ("message", "join")
    )
    active_24h = len(active_ids_24h)
    inactive_24h = total_users - active_24h

    # 24 soatlik voqealar jadvali (soat bo'yicha)
    hourly = {}
    for i in range(24):
        t_start = now - (24 - i) * 3600
        t_end   = t_start + 3600
        label   = datetime.fromtimestamp(t_start).strftime("%H:00")
        count   = sum(1 for e in events if t_start <= e["ts"] < t_end)
        hourly[label] = count

    # Jadval matni
    lines = [
        "📊 <b>Faollik jadvali (oxirgi 24 soat)</b>",
        "",
        f"👥 Jami foydalanuvchilar: <b>{total_users}</b>",
        f"🟢 Faol (24h): <b>{active_24h}</b>",
        f"🔴 Faol emas (24h): <b>{inactive_24h}</b>",
        f"🆕 Yangi qo'shilganlar (24h): <b>{new_in_24h}</b>",
        "",
        "⏰ Soatlik faollik:",
        "─" * 30,
    ]
    max_count = max(hourly.values(), default=1) or 1
    for label, count in hourly.items():
        bar_len = int((count / max_count) * 15)
        bar = "█" * bar_len + "░" * (15 - bar_len)
        lines.append(f"<code>{label} {bar} {count}</code>")

    # 24 soatdagi muhim voqealar
    lines += ["", "📋 Muhim voqealar (24h):"]
    ev_24h = [e for e in events if e["ts"] > cutoff_24h]
    type_counts = {}
    for e in ev_24h:
        type_counts[e["type"]] = type_counts.get(e["type"], 0) + 1

    emoji_map = {
        "join":           "🆕 Yangi foydalanuvchi",
        "message":        "✉️ Xabarlar",
        "new_ad":         "📢 Yangi e'lonlar",
        "delete_ad":      "🗑 O'chirilgan e'lonlar",
        "admin_reply":    "💬 Admin javoblari",
        "new_button":     "🔘 Yangi tugmalar",
        "delete_button":  "🗑 O'chirilgan tugmalar",
        "new_command":    "⚙️ Yangi buyruqlar",
        "delete_command": "🗑 O'chirilgan buyruqlar",
    }
    if type_counts:
        for etype, cnt in type_counts.items():
            label = emoji_map.get(etype, etype)
            lines.append(f"  {label}: <b>{cnt}</b>")
    else:
        lines.append("  Hozircha voqealar yo'q.")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="HTML"
    )


# ─── Umumiy xabar handler ────────────────────────────────────────────────────

async def generic_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_lang(user.id)
    text = update.message.text or ""
    tl   = text.lower()

    voice_on  = ["ovozli javob ber", "voice", "ovoz", "speak", "голос", "говори"]
    voice_off = ["ovosiz", "matnli", "text", "без голоса", "without voice", "текст"]

    if any(t in tl for t in voice_on):
        set_mode(user.id, "voice")
        await update.message.reply_text("🎙 Endi ovozli javob beraman!")
        return
    if any(t in tl for t in voice_off):
        set_mode(user.id, "text")
        await update.message.reply_text("💬 Endi matnli javob beraman!")
        return

    # Til tugmasi bosilganmi
    if await lang_button_pressed(update, context):
        return

    # Maxsus buyruqlarni tekshirish (/ bilan boshlanuvchi)
    if text.startswith("/"):
        cmd = text.lstrip("/").split()[0].lower()
        if cmd in custom_commands:
            await update.message.reply_text(custom_commands[cmd]["response_text"])
            log_event("message", user.id, f"cmd:{cmd}")
            return

    # TuxumAI holati
    if get_state(user.id) == "tuxumai":
        ad_id = context.user_data.get("tuxumai_ad_id")
        ad = next((a for a in ads if a["id"] == ad_id), None) if ad_id else (ads[-1] if ads else None)
        reply = get_ai_reply(ad, lang, text)
        if reply:
            await send_ai_response(context, update.effective_chat.id, user.id, reply, lang)
        log_event("message", user.id, "tuxumai")
        return

    # Normal holat: xabar adminga boradi
    # Admin o'zi yozsa — foydalanuvchiga javob berish imkoni
    if user.id == ADMIN_ID and str(user.id) in pending_reply:
        target_id = pending_reply.pop(str(user.id))
        try:
            await context.bot.send_message(target_id, f"💬 Admin javobi:\n\n{text}")
            await update.message.reply_text(f"✅ Javob {target_id} ga yuborildi.")
        except Exception as e:
            await update.message.reply_text(f"❌ Xato: {e}")
        return

    username = f"@{user.username}" if user.username else f"id:{user.id}"

    # Adminga xabarni forward qilish + "Javob berish" tugmasi
    try:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "💬 Javob berish",
                callback_data=f"replyto_{user.id}"
            )
        ]])
        await context.bot.send_message(
            ADMIN_ID,
            f"✉️ Foydalanuvchi xabari:\n"
            f"👤 {user.full_name or ''} ({username})\n"
            f"🆔 ID: <code>{user.id}</code>\n\n"
            f"{text}",
            parse_mode="HTML",
            reply_markup=kb,
        )
    except Exception as e:
        logger.warning(f"Adminga xabar yuborib bo'lmadi: {e}")

    log_event("message", user.id, text[:50])
    await update.message.reply_text(tr("contact_sent", lang))


async def reply_to_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin 'Javob berish' tugmasini bosadi — pending_reply ga yoziladi"""
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer(); return
    target_id = int(q.data.split("_", 1)[1])
    pending_reply[str(ADMIN_ID)] = target_id
    await q.answer()
    await context.bot.send_message(
        ADMIN_ID,
        f"✏️ {target_id} ga javob yozing (keyingi xabaringiz yuboriladi):"
    )


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # E'lon qo'shish conversation
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

    # Tugma yaratish conversation
    btn_conv = ConversationHandler(
        entry_points=[CommandHandler("button", button_create_start)],
        states={
            BTN_NAME:         [MessageHandler(filters.TEXT & ~filters.COMMAND, button_create_name)],
            BTN_ACTION_TYPE:  [CallbackQueryHandler(button_create_type_callback, pattern=r"^btntype_")],
            BTN_ACTION_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, button_create_value)],
        },
        fallbacks=[CommandHandler("cancel", button_create_cancel)],
        allow_reentry=True,
    )

    # Buyruq yaratish conversation
    cmd_conv = ConversationHandler(
        entry_points=[CommandHandler("cmd", cmd_create_start)],
        states={
            CMD_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_create_name)],
            CMD_DESC:     [MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_create_desc)],
            CMD_RESPONSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_create_response)],
        },
        fallbacks=[CommandHandler("cancel", cmd_create_cancel)],
        allow_reentry=True,
    )

    # Asosiy buyruqlar
    app.add_handler(CommandHandler("start",       start))
    app.add_handler(CommandHandler("delete",      delete_command))
    app.add_handler(CommandHandler("reply",       admin_reply_command))
    app.add_handler(CommandHandler("deletebtn",   button_delete_command))   # /-button
    app.add_handler(CommandHandler("deletecmd",   cmd_delete_command))      # /-cmd
    app.add_handler(CommandHandler("fj",          faollik_jadvali))

    # ConversationHandlerlar
    app.add_handler(elon_conv)
    app.add_handler(btn_conv)
    app.add_handler(cmd_conv)

    # Callback querylar
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
    app.add_handler(CallbackQueryHandler(reply_to_user_callback,     pattern=r"^replyto_"))

    # Xabar handlerlari
    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(MessageHandler(filters.VOICE,    voice_message_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generic_message_handler))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
