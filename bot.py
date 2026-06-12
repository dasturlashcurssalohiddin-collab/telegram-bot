# -*- coding: utf-8 -*-

import json
import os
import time
import logging
import tempfile
import asyncio
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

BOT_TOKEN  = "8646422380:AAEC4hroA9IGQScyHnaIxisSz9jjYVw6z6c"
ADMIN_ID   = 6283517295
CHANNEL_ID = "@tuxum_kanal"

GROQ_API_KEY = "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"
ai_client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

DATA_DIR   = os.path.dirname(os.path.abspath(__file__))
ADS_FILE   = os.path.join(DATA_DIR, "ads.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

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
    "contact": {
        "label": {"uz": "✉️ Murojaat", "en": "✉️ Contact", "ru": "✉️ Связаться", "de": "✉️ Kontakt"},
        "type": "contact_admin",
    },
}

PHONE_NUMBER = "+998951000130"

# Til → edge-tts ovozi
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


ads        = load_json(ADS_FILE, [])
users      = load_json(USERS_FILE, {})
user_modes: dict = {}   # {str(user_id): "voice" | "text"}


def save_ads():   save_json(ADS_FILE, ads)
def save_users(): save_json(USERS_FILE, users)
def get_lang(uid): return users.get(str(uid), "uz")
def get_mode(uid): return user_modes.get(str(uid), "text")
def set_mode(uid, mode): user_modes[str(uid)] = mode


WAIT_PHOTO, WAIT_TEXT, SELECT_BUTTONS, WAIT_INFO = range(4)

LANG_NAME_TO_CODE = {v: k for k, v in LANG_NAMES.items()}


def lang_inline_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton(LANG_NAMES[c], callback_data=f"setlang_{c}")] for c in LANGS])


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
        cb = (
            f"phone_{ad['id']}"    if t == "phone"            else
            f"info_{ad['id']}"     if t == "info"             else
            f"contact_{ad['id']}"  if t == "contact_admin"    else
            f"location_{ad['id']}" if t == "location_request" else
            f"btn_{ad['id']}_{btn_id}"
        )
        row.append(InlineKeyboardButton(label, callback_data=cb))
        if len(row) == 2:
            rows.append(row); row = []
    if row: rows.append(row)
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


# ======================== TTS (edge-tts) ========================

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


# ======================== STT (Groq Whisper) ========================

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


# ======================== TuxumAI ========================

def get_ai_reply(ad, lang: str, user_message: str) -> str | None:
    ad_text = ad.get("text", "") if ad else ""
    ad_info = ad.get("info_text", "") if ad else ""
    system_prompt = (
        "Sening isming TuxumAI. Sen aqlli yordamchi sun'iy intellektsan. "
        "Har qanday savolga javob ber — mavzu cheklovlarsiz. "
        "Agar 'sen kimsan' deb so'rashsa — 'Men TuxumAI man' de. "
        "Bu tuxum sotish Telegram boti. Tugmalar: Telefon, Ma'lumot, Sifat kafolati, Manzil, Murojaat.\n\n"
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
    """Rejimga qarab matn yoki ovozli javob yuboradi"""
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


# ======================== START & TIL ========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = users.get(str(update.effective_user.id), "uz")
    await update.message.reply_text(tr("choose_lang", lang), reply_markup=lang_inline_keyboard())


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


# ======================== INLINE TUGMA CALLBACKLARI ========================

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


async def contact_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang = get_lang(q.from_user.id)
    context.user_data["awaiting_contact_for_ad"] = q.data.split("_", 1)[1]
    await q.answer()
    await context.bot.send_message(q.message.chat_id, tr("write_contact", lang))


async def location_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📍 Manzil tugmasi — Telegram'ning GPS joylashuv tugmasini ko'rsatadi"""
    q = update.callback_query
    lang = get_lang(q.from_user.id)
    context.user_data["awaiting_location_for_ad"] = q.data.split("_", 1)[1]
    await q.answer()
    loc_kb = ReplyKeyboardMarkup(
        [[KeyboardButton(tr("location_btn_label", lang), request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
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


# ======================== JOYLASHUV HANDLER ========================

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


# ======================== OVOZLI XABAR HANDLER ========================

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


# ======================== E'LON O'CHIRISH ========================

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
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer(); return
    global ads
    ad_id = q.data.split("_", 1)[1]
    before = len(ads)
    ads = [a for a in ads if a["id"] != ad_id]
    await q.answer()
    if len(ads) != before:
        save_ads()
        await q.edit_message_text("✅ E'lon muvaffaqiyatli o'chirildi.")
    else:
        await q.edit_message_text("❌ E'lon topilmadi.")


async def delete_ad_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("❌ O'chirish bekor qilindi.")


# ======================== ADMIN: E'LON QO'SHISH ========================

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


# ======================== MATN XABAR HANDLER ========================

async def generic_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_lang(user.id)
    text = update.message.text or ""
    tl   = text.lower()

    # Ovoz rejimi so'zlari
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

    # Murojaat kutilmoqda
    if context.user_data.get("awaiting_contact_for_ad"):
        ad_id    = context.user_data.pop("awaiting_contact_for_ad")
        username = f"@{user.username}" if user.username else f"id:{user.id}"
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"✉️ Murojaat (e'lon: {ad_id})\n👤 {user.full_name or ''} ({username})\n\n{text}"
            )
        except Exception as e:
            logger.warning(f"Adminga xabar yuborib bo'lmadi: {e}")
        await update.message.reply_text(tr("contact_sent", lang))
        ad = next((a for a in ads if a["id"] == ad_id), None)
        reply = get_ai_reply(ad, lang, text)
        if reply:
            await send_ai_response(context, update.effective_chat.id, user.id, reply, lang)
        return

    # Til tugmasi
    if await lang_button_pressed(update, context):
        return

    # Oddiy xabar — TuxumAI
    ad = ads[-1] if ads else None
    reply = get_ai_reply(ad, lang, text)
    if reply:
        await send_ai_response(context, update.effective_chat.id, user.id, reply, lang)


# ======================== MAIN ========================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
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

    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(conv)

    app.add_handler(CallbackQueryHandler(set_language_callback,      pattern=r"^setlang_"))
    app.add_handler(CallbackQueryHandler(phone_button_callback,      pattern=r"^phone_"))
    app.add_handler(CallbackQueryHandler(info_button_callback,       pattern=r"^info_"))
    app.add_handler(CallbackQueryHandler(contact_button_callback,    pattern=r"^contact_"))
    app.add_handler(CallbackQueryHandler(location_button_callback,   pattern=r"^location_"))
    app.add_handler(CallbackQueryHandler(text_button_callback,       pattern=r"^btn_"))
    app.add_handler(CallbackQueryHandler(delete_ad_confirm_callback, pattern=r"^deladconfirm_"))
    app.add_handler(CallbackQueryHandler(delete_ad_yes_callback,     pattern=r"^deladyes_"))
    app.add_handler(CallbackQueryHandler(delete_ad_cancel_callback,  pattern=r"^deladcancel$"))

    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(MessageHandler(filters.VOICE,    voice_message_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generic_message_handler))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
