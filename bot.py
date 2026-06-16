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

BOT_TOKEN  = os.getenv("BOT_TOKEN")
ADMIN_ID   = 6283517295
CHANNEL_ID = "@tuxum_kanal"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ai_client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

DATA_DIR   = os.path.dirname(os.path.abspath(__file__))
ADS_FILE   = os.path.join(DATA_DIR, "ads.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

# Admin xaritasi koordinatalari (o'zingizning manzilingiz)
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
    "location_sent":  {"uz": "✅ Joylashuvingiz sotuvchiga yuborildi.", "en": "✅ Location sent to seller.", "ru": "✅ Местоположение отправlено.", "de": "✅ Standort gesendet."},
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
    "user_msg_to_admin": {
        "uz": "✉️ Foydalanuvchi xabari keldi:",
        "en": "✉️ User message received:",
        "ru": "✉️ Получено сообщение от пользователя:",
        "de": "✉️ Nachricht vom Benutzer erhalten:",
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
    # "contact" o'chirildi, o'rniga "tuxumai" va "market" va "delivery" qo'shildi
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


ads        = load_json(ADS_FILE, [])
users      = load_json(USERS_FILE, {})
user_modes: dict = {}
# Foydalanuvchi holati: "normal" yoki "tuxumai" (AI bilan suhbat)
user_states: dict = {}


def save_ads():   save_json(ADS_FILE, ads)
def save_users(): save_json(USERS_FILE, users)
def get_lang(uid): return users.get(str(uid), "uz")
def get_mode(uid): return user_modes.get(str(uid), "text")
def set_mode(uid, mode): user_modes[str(uid)] = mode
def get_state(uid): return user_states.get(str(uid), "normal")
def set_state(uid, state): user_states[str(uid)] = state


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

        if t == "url":
            # URL tugmasi - to'g'ridan-to'g'ri link
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
        "Bu tuxum sotish Telegram boti. Tugmalar: Telefon, Ma'lumot, Sifat kafolati, Manzil, TuxumAI, Tuxum Market, Olib kelish.\n\n"
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = users.get(str(update.effective_user.id), "uz")
    # Holatni normal qilib tiklash
    set_state(update.effective_user.id, "normal")
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
    """TuxumAI tugmasi bosilganda - foydalanuvchini AI suhbat holatiga o'tkazish"""
    q = update.callback_query
    lang = get_lang(q.from_user.id)
    ad_id = q.data.split("_", 1)[1]
    # Foydalanuvchini tuxumai holatiga o'tkazamiz va qaysi e'lon ekanini saqlaymiz
    set_state(q.from_user.id, "tuxumai")
    context.user_data["tuxumai_ad_id"] = ad_id
    await q.answer()
    await context.bot.send_message(
        q.message.chat_id,
        tr("tuxumai_greeting", lang)
    )


async def delivery_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Olib kelish tugmasi - admin xaritasini yuborish"""
    q = update.callback_query
    lang = get_lang(q.from_user.id)
    await q.answer()
    await context.bot.send_message(
        q.message.chat_id,
        tr("delivery_location", lang)
    )
    await context.bot.send_location(
        chat_id=q.message.chat_id,
        latitude=ADMIN_LATITUDE,
        longitude=ADMIN_LONGITUDE,
    )


async def location_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    # Til tugmasi bosilganmi tekshirish
    if await lang_button_pressed(update, context):
        return

    # ── TuxumAI holati ──
    # Foydalanuvchi TuxumAI tugmasini bosib suhbat boshlagan bo'lsa
    if get_state(user.id) == "tuxumai":
        ad_id = context.user_data.get("tuxumai_ad_id")
        ad = next((a for a in ads if a["id"] == ad_id), None) if ad_id else (ads[-1] if ads else None)
        reply = get_ai_reply(ad, lang, text)
        if reply:
            await send_ai_response(context, update.effective_chat.id, user.id, reply, lang)
        return

    # ── Normal holat: xabar adminga boradi ──
    username = f"@{user.username}" if user.username else f"id:{user.id}"
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"✉️ Foydalanuvchi xabari:\n"
            f"👤 {user.full_name or ''} ({username})\n\n"
            f"{text}"
        )
    except Exception as e:
        logger.warning(f"Adminga xabar yuborib bo'lmadi: {e}")

    # Admin javob bera olishi uchun foydalanuvchi ID sini saqlaymiz
    # (Ixtiyoriy: admin /reply <user_id> <matn> kabi buyruq qo'shsa bo'ladi)
    await update.message.reply_text(tr("contact_sent", lang))


async def admin_reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin foydalanuvchiga javob berish uchun: /reply <user_id> <matn>"""
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("❌ Foydalanish: /reply <user_id> <matn>")
        return
    try:
        target_id = int(args[0])
        reply_text = " ".join(args[1:])
        await context.bot.send_message(target_id, f"💬 Admin javobi:\n\n{reply_text}")
        await update.message.reply_text(f"✅ Javob {target_id} ga yuborildi.")
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {e}")


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
    app.add_handler(CommandHandler("reply",  admin_reply_command))
    app.add_handler(conv)

    app.add_handler(CallbackQueryHandler(set_language_callback,      pattern=r"^setlang_"))
    app.add_handler(CallbackQueryHandler(phone_button_callback,      pattern=r"^phone_"))
    app.add_handler(CallbackQueryHandler(info_button_callback,       pattern=r"^info_"))
    app.add_handler(CallbackQueryHandler(tuxumai_button_callback,    pattern=r"^tuxumai_"))
    app.add_handler(CallbackQueryHandler(delivery_button_callback,   pattern=r"^delivery_"))
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


if __name__ == "__# -*- coding: utf-8 -*-

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
CUSTOM_BTNS_FILE= os.path.join(DATA_DIR, "custom_buttons.json")
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

# ── ConversationHandler states ──
WAIT_PHOTO, WAIT_TEXT, SELECT_BUTTONS, WAIT_INFO = range(4)
# /button conversation
BTN_WAIT_NAME, BTN_WAIT_ACTION = range(10, 12)
# /commands conversation
CMD_WAIT_NAME, CMD_WAIT_DESC = range(20, 22)

LANG_NAME_TO_CODE = {v: k for k, v in LANG_NAMES.items()}


# ── JSON helpers ──
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

ads          = load_json(ADS_FILE, [])
users        = load_json(USERS_FILE, {})   # {uid: lang}
custom_btns  = load_json(CUSTOM_BTNS_FILE, {})  # {name: {label, action}}
events_log   = load_json(EVENTS_FILE, [])  # [{ts, type, uid}]

user_modes:  dict = {}
user_states: dict = {}

def save_ads():        save_json(ADS_FILE, ads)
def save_users():      save_json(USERS_FILE, users)
def save_custom_btns():save_json(CUSTOM_BTNS_FILE, custom_btns)
def save_events():     save_json(EVENTS_FILE, events_log)

def get_lang(uid):  return users.get(str(uid), "uz")
def get_mode(uid):  return user_modes.get(str(uid), "text")
def set_mode(uid, mode): user_modes[str(uid)] = mode
def get_state(uid): return user_states.get(str(uid), "normal")
def set_state(uid, state): user_states[str(uid)] = state


# ── Event logger ──
def log_event(etype: str, uid: int):
    events_log.append({"ts": time.time(), "type": etype, "uid": str(uid)})
    # Faqat oxirgi 10 000 ta yozuvni saqlash
    if len(events_log) > 10000:
        events_log.pop(0)
    save_events()


# ── Keyboards ──
def lang_inline_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton(LANG_NAMES[c], callback_data=f"setlang_{c}")] for c in LANGS])

def lang_reply_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(LANG_NAMES["uz"]), KeyboardButton(LANG_NAMES["en"])],
         [KeyboardButton(LANG_NAMES["ru"]), KeyboardButton(LANG_NAMES["de"])]],
        resize_keyboard=True
    )


# ── Translate ──
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


# ── Ad keyboard builder ──
def build_ad_keyboard(ad, lang):
    rows, row = [], []
    all_btns = list(ad.get("buttons", []))

    for btn_id in all_btns:
        # Custom button?
        if btn_id.startswith("custom_"):
            cname = btn_id[7:]
            cbt = custom_btns.get(cname)
            if not cbt:
                continue
            row.append(InlineKeyboardButton(cbt["label"], callback_data=f"custombtn_{cname}"))
        else:
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


# ── TTS / STT / AI ──
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


# ════════════════════════════════════════════
#   /start
# ════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = users.get(str(uid), "uz")
    set_state(uid, "normal")
    # Yangi foydalanuvchi bo'lsa log qilamiz
    if str(uid) not in users:
        log_event("new_user", uid)
    log_event("start", uid)
    await update.message.reply_text(tr("choose_lang", lang), reply_markup=lang_inline_keyboard())


# ════════════════════════════════════════════
#   /fj — Statistika
# ════════════════════════════════════════════
async def fj_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    now = time.time()
    cutoff_24h = now - 86400

    total_users = len(users)

    # 24 soat ichida /start bosgan yoki xabar yuborganlar
    active_uids_24h = set(
        e["uid"] for e in events_log
        if e["ts"] >= cutoff_24h and e["type"] in ("start", "message", "new_user")
    )
    active_24h = len(active_uids_24h)
    inactive = total_users - active_24h

    # 24 soat voqealari soat bo'yicha
    hour_counts = {}
    for e in events_log:
        if e["ts"] >= cutoff_24h:
            h = datetime.fromtimestamp(e["ts"]).strftime("%H:00")
            hour_counts[h] = hour_counts.get(h, 0) + 1

    # Statistika matni
    lines = [
        "📊 <b>Bot statistikasi</b>",
        "",
        f"👥 <b>Jami foydalanuvchilar:</b> {total_users}",
        f"🟢 <b>Faol (24h):</b> {active_24h}",
        f"🔴 <b>Nofaol:</b> {inactive}",
        "",
        "📅 <b>24 soat voqealari (soat bo'yicha jadval):</b>",
        "",
    ]

    if hour_counts:
        max_count = max(hour_counts.values()) or 1
        for h in sorted(hour_counts.keys()):
            cnt = hour_counts[h]
            bar_len = int((cnt / max_count) * 15)
            bar = "█" * bar_len + "░" * (15 - bar_len)
            lines.append(f"<code>{h} |{bar}| {cnt}</code>")
    else:
        lines.append("(24 soat ichida voqea yo'q)")

    # Yangi foydalanuvchilar 24h
    new_users_24h = sum(1 for e in events_log if e["ts"] >= cutoff_24h and e["type"] == "new_user")
    lines += ["", f"🆕 <b>Yangi foydalanuvchilar (24h):</b> {new_users_24h}"]

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ════════════════════════════════════════════
#   /commands — Buyruqlar ro'yxati
# ════════════════════════════════════════════
async def commands_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ yozsam barcha / buyruqlar nomini va ishini ko'rsatadi"""
    if update.effective_user.id != ADMIN_ID:
        return

    built_in = [
        ("/start",       "Botni boshlash, til tanlash"),
        ("/elon_photo",  "Yangi e'lon qo'shish (admin)"),
        ("/delete",      "E'lonni o'chirish (admin)"),
        ("/button",      "Yangi custom button qo'shish (admin)"),
        ("/-button",     "Custom buttonni o'chirish (admin)"),
        ("/commands",    "Barcha buyruqlar ro'yxati (admin)"),
        ("/fj",          "Foydalanuvchi statistikasi va 24h jadval (admin)"),
        ("/cancel",      "Jarayonni bekor qilish (admin)"),
    ]

    lines = ["📋 <b>Barcha buyruqlar:</b>", ""]
    for cmd, desc in built_in:
        lines.append(f"<code>{cmd}</code> — {desc}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ════════════════════════════════════════════
#   /button — Custom button qo'shish
# ════════════════════════════════════════════
async def button_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    await update.message.reply_text(
        "➕ Yangi custom button qo'shamiz.\n\n"
        "Birinchi: <b>button nomini</b> yozing (masalan: Narxlar):",
        parse_mode="HTML"
    )
    return BTN_WAIT_NAME

async def button_add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("❌ Nom bo'sh bo'lmasin, qaytadan yozing:")
        return BTN_WAIT_NAME
    context.user_data["new_btn_name"] = name
    await update.message.reply_text(
        f"✅ Nom: <b>{name}</b>\n\n"
        "Endi bu button bosilganda <b>qanday javob berishi</b> kerakligini yozing\n"
        "(matn yoki URL: https://...):",
        parse_mode="HTML"
    )
    return BTN_WAIT_ACTION

async def button_add_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = update.message.text.strip()
    name   = context.user_data.get("new_btn_name", "button")
    key    = name.lower().replace(" ", "_")
    custom_btns[key] = {"label": name, "action": action}
    save_custom_btns()
    await update.message.reply_text(
        f"✅ Custom button saqlandi!\n\n"
        f"🔘 Nom: <b>{name}</b>\n"
        f"📝 Amal: <code>{action}</code>\n\n"
        f"E'lon yaratishda tugmalar ro'yxatida ko'rinadi.",
        parse_mode="HTML"
    )
    return ConversationHandler.END

async def button_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END


# ════════════════════════════════════════════
#   /-button — Custom button o'chirish
# ════════════════════════════════════════════
async def button_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not custom_btns:
        await update.message.reply_text("❌ Custom buttonlar yo'q.")
        return
    rows = []
    for key, info in custom_btns.items():
        rows.append([InlineKeyboardButton(
            f"🗑 {info['label']}", callback_data=f"delbtn_{key}"
        )])
    rows.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="delbtncancel")])
    await update.message.reply_text(
        "🗑 Qaysi custom buttonni o'chirmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(rows)
    )

async def button_remove_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer(); return
    key = q.data.split("_", 1)[1]
    removed = custom_btns.pop(key, None)
    save_custom_btns()
    await q.answer()
    if removed:
        await q.edit_message_text(f"✅ <b>{removed['label']}</b> button o'chirildi.", parse_mode="HTML")
    else:
        await q.edit_message_text("❌ Button topilmadi.")

async def button_remove_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("❌ Bekor qilindi.")


# ════════════════════════════════════════════
#   Custom button bosilganda
# ════════════════════════════════════════════
async def custom_btn_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cname = q.data.split("_", 1)[1]
    cbt = custom_btns.get(cname)
    if not cbt:
        await context.bot.send_message(q.message.chat_id, "❌ Button topilmadi.")
        return
    action = cbt.get("action", "")
    if action.startswith("http://") or action.startswith("https://"):
        # URL bo'lsa - inline URL tugma yuboramiz
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Ochish", url=action)]])
        await context.bot.send_message(q.message.chat_id, f"🔗 {cbt['label']}:", reply_markup=kb)
    else:
        await context.bot.send_message(q.message.chat_id, action)


# ════════════════════════════════════════════
#   Lang callbacks
# ════════════════════════════════════════════
async def set_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang_code = query.data.split("_", 1)[1]
    users[str(query.from_user.id)] = lang_code
    save_users()
    log_event("message", query.from_user.id)
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


# ════════════════════════════════════════════
#   Inline button callbacks
# ════════════════════════════════════════════
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


# ════════════════════════════════════════════
#   Location & Voice
# ════════════════════════════════════════════
async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_lang(user.id)
    loc  = update.message.location
    ad_id = context.user_data.pop("awaiting_location_for_ad", "nomalum")
    username = f"@{user.username}" if user.username else f"id:{user.id}"
    lat, lon = loc.latitude, loc.longitude
    # Adminga yuboring
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


# ════════════════════════════════════════════
#   /delete — E'lon o'chirish (foydalanuvchilarda ham)
# ════════════════════════════════════════════
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
    """E'lonni o'chirib, barcha foydalanuvchilarga ham o'chirish xabarini yuborish"""
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer(); return
    global ads
    ad_id = q.data.split("_", 1)[1]
    ad = next((a for a in ads if a["id"] == ad_id), None)
    await q.answer()
    if not ad:
        await q.edit_message_text("❌ E'lon topilmadi.")
        return

    ads = [a for a in ads if a["id"] != ad_id]
    save_ads()
    await q.edit_message_text("✅ E'lon o'chirildi. Foydalanuvchilarga xabar yuborilmoqda...")

    # Barcha foydalanuvchilarga xabar
    short = ad.get("text", "")[:60] + ("..." if len(ad.get("text", "")) > 60 else "")
    deleted_text = f"🗑 E'lon o'chirildi:\n\n📝 {short}"
    sent = 0
    for uid_str in users:
        try:
            await context.bot.send_message(int(uid_str), deleted_text)
            sent += 1
        except Exception as e:
            logger.warning(f"{uid_str} ga xabar yuborib bo'lmadi: {e}")

    await context.bot.send_message(ADMIN_ID, f"✅ Xabar {sent} ta foydalanuvchiga yuborildi.")

async def delete_ad_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("❌ O'chirish bekor qilindi.")


# ════════════════════════════════════════════
#   /elon_photo — E'lon qo'shish (ConversationHandler)
# ════════════════════════════════════════════
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
    # Asosiy tugmalar
    for btn_id, info in BUTTONS_CATALOG.items():
        prefix = "✅ " if btn_id in selected else ""
        row.append(InlineKeyboardButton(prefix + info["label"]["uz"], callback_data=f"selbtn_{btn_id}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row: rows.append(row); row = []

    # Custom tugmalar
    for key, info in custom_btns.items():
        cid = f"custom_{key}"
        prefix = "✅ " if cid in selected else ""
        row.append(InlineKeyboardButton(prefix + info["label"], callback_data=f"selbtn_{cid}"))
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


# ════════════════════════════════════════════
#   Generic message → Adminning o'z Telegram-iga
# ════════════════════════════════════════════
async def generic_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_lang(user.id)
    text = update.message.text or ""
    tl   = text.lower()

    log_event("message", user.id)

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

    if await lang_button_pressed(update, context):
        return

    # TuxumAI holati
    if get_state(user.id) == "tuxumai":
        ad_id = context.user_data.get("tuxumai_ad_id")
        ad = next((a for a in ads if a["id"] == ad_id), None) if ad_id else (ads[-1] if ads else None)
        reply = get_ai_reply(ad, lang, text)
        if reply:
            await send_ai_response(context, update.effective_chat.id, user.id, reply, lang)
        return

    # ── Normal: xabar ADMINGA (sizning Telegramingizga) boradi ──
    username = f"@{user.username}" if user.username else f"id:{user.id}"
    try:
        await context.bot.send_message(
            ADMIN_ID,   # ← /reply emas, to'g'ridan-to'g'ri sizga
            f"✉️ Foydalanuvchi xabari:\n"
            f"👤 {user.full_name or ''} ({username})\n"
            f"🆔 ID: <code>{user.id}</code>\n\n"
            f"{text}",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Adminga xabar yuborib bo'lmadi: {e}")

    await update.message.reply_text(tr("contact_sent", lang))


# ════════════════════════════════════════════
#   main
# ════════════════════════════════════════════
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

    # Custom button qo'shish
    btn_conv = ConversationHandler(
        entry_points=[CommandHandler("button", button_add_start)],
        states={
            BTN_WAIT_NAME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, button_add_name)],
            BTN_WAIT_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, button_add_action)],
        },
        fallbacks=[CommandHandler("cancel", button_cancel)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start",    start))
    app.add_handler(CommandHandler("delete",   delete_command))
    app.add_handler(CommandHandler("fj",       fj_command))
    app.add_handler(CommandHandler("commands", commands_list))
    app.add_handler(CommandHandler("button",   button_add_start))   # conv ichida ham
    app.add_handler(elon_conv)
    app.add_handler(btn_conv)

    # /-button
    app.add_handler(MessageHandler(filters.Regex(r"^/-button$"), button_remove_command))

    # Callback handlers
    app.add_handler(CallbackQueryHandler(set_language_callback,      pattern=r"^setlang_"))
    app.add_handler(CallbackQueryHandler(phone_button_callback,      pattern=r"^phone_"))
    app.add_handler(CallbackQueryHandler(info_button_callback,       pattern=r"^info_"))
    app.add_handler(CallbackQueryHandler(tuxumai_button_callback,    pattern=r"^tuxumai_"))
    app.add_handler(CallbackQueryHandler(delivery_button_callback,   pattern=r"^delivery_"))
    app.add_handler(CallbackQueryHandler(location_button_callback,   pattern=r"^location_"))
    app.add_handler(CallbackQueryHandler(text_button_callback,       pattern=r"^btn_"))
    app.add_handler(CallbackQueryHandler(custom_btn_callback,        pattern=r"^custombtn_"))
    app.add_handler(CallbackQueryHandler(delete_ad_confirm_callback, pattern=r"^deladconfirm_"))
    app.add_handler(CallbackQueryHandler(delete_ad_yes_callback,     pattern=r"^deladyes_"))
    app.add_handler(CallbackQueryHandler(delete_ad_cancel_callback,  pattern=r"^deladcancel$"))
    app.add_handler(CallbackQueryHandler(button_remove_callback,     pattern=r"^delbtn_"))
    app.add_handler(CallbackQueryHandler(button_remove_cancel,       pattern=r"^delbtncancel$"))

    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(MessageHandler(filters.VOICE,    voice_message_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generic_message_handler))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
main__":
    main()
