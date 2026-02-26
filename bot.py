import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# ENV VARIABLES (Vercel)
# =========================
TOKEN = os.environ["TOKEN"]
SHEET_URL = os.environ["SHEET_URL"]
GOOGLE_CREDENTIALS = os.environ["GOOGLE_CREDENTIALS"]  # JSON string

# =========================
# GOOGLE AUTH (from ENV)
# =========================
creds_dict = json.loads(GOOGLE_CREDENTIALS)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
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
app.add_handler(MessageHandler(filters.TEXT, reply))


# =========================
# VERCEL HANDLER (Webhook)
# =========================
async def handler(request):

    body = await request.body()
    update = Update.de_json(json.loads(body), app.bot)

    await app.initialize()
    await app.process_update(update)

    return {
        "statusCode": 200,
        "body": "OK",
    }