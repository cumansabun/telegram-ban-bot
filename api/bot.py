import os
import json
import base64
import asyncio
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# ENV VARIABLES
# =========================
TOKEN = os.environ.get("TOKEN")
SHEET_URL = os.environ.get("SHEET_URL")
CREDS_BASE64 = os.environ.get("GOOGLE_CREDENTIALS_BASE64")

if not TOKEN:
    raise Exception("TOKEN not set")

if not SHEET_URL:
    raise Exception("SHEET_URL not set")

if not CREDS_BASE64:
    raise Exception("GOOGLE_CREDENTIALS_BASE64 not set")

# =========================
# GOOGLE AUTH (BASE64 SAFE)
# =========================
creds_json = base64.b64decode(CREDS_BASE64).decode("utf-8")
creds_dict = json.loads(creds_json)

credentials = Credentials.from_service_account_info(
    creds_dict,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

client = gspread.authorize(credentials)
sheet = client.open_by_url(SHEET_URL).sheet1

# =========================
# TELEGRAM APP
# =========================
app = ApplicationBuilder().token(TOKEN).build()

kategori_list = [
    "NOMOR LAMBUNG",
    "CABANG",
    "GOLONGAN",
    "MERK//TYPE",
    "NOPOL",
    "PEMAKAI",
    "JENIS KENDARAAN",
]

# =========================
# START MENU
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        ["NOMOR LAMBUNG", "CABANG"],
        ["GOLONGAN", "MERK//TYPE"],
        ["NOPOL", "PEMAKAI"],
        ["JENIS KENDARAAN"],
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "🚚 BOT DATA BAN KENDARAAN\n\nSilakan pilih kategori pencarian:",
        reply_markup=reply_markup,
    )

# =========================
# HANDLE MESSAGE
# =========================
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()
    data = sheet.get_all_records()

    # Pilih kategori
    if text in kategori_list:

        daftar = set()

        for row in data:
            value = str(row.get(text, "")).strip()
            if value:
                daftar.add(value)

        context.user_data["kategori"] = text

        daftar_text = "\n".join(sorted(daftar))

        await update.message.reply_text(
            f"📋 DAFTAR {text}\n\n{daftar_text}\n\n"
            f"Ketik {text} yang ingin dicari\n\nKetik /start untuk kembali"
        )
        return

    # Mode filter
    kategori = context.user_data.get("kategori")

    if kategori:
        hasil = ""

        for row in data:
            value = str(row.get(kategori, "")).strip()

            if value.upper() == text.upper():

                hasil += f"""
🚚 DATA KENDARAAN

Nomor Lambung : {row.get('NOMOR LAMBUNG','')}
Cabang : {row.get('CABANG','')}
Golongan : {row.get('GOLONGAN','')}

Merk : {row.get('MERK//TYPE','')}
Nopol : {row.get('NOPOL','')}

Pemakai :
{row.get('PEMAKAI','')}

Jenis Kendaraan :
{row.get('JENIS KENDARAAN','')}

Nomor Ban : {row.get('NOMOR BAN','')}
Qty : {row.get('QTY','')}

----------------------------
"""

        if hasil == "":
            hasil = "❌ Data tidak ditemukan"

        await update.message.reply_text(hasil)
        return

    await update.message.reply_text("Ketik /start untuk memulai")

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

# =========================
# VERCEL HANDLER (SYNC SAFE)
# =========================
def handler(request):

    try:
        body = request.get_body()
        update = Update.de_json(json.loads(body), app.bot)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(app.initialize())
        loop.run_until_complete(app.process_update(update))

        return {
            "statusCode": 200,
            "body": "OK"
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": str(e)
        }