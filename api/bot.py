import os
import json
import base64
import asyncio
from http.server import BaseHTTPRequestHandler

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

application = None
sheet = None

# =========================
# GOOGLE AUTH (BASE64)
# =========================
if CREDS_BASE64 and SHEET_URL:
    try:
        creds_json = base64.b64decode(CREDS_BASE64).decode("utf-8")
        creds_dict = json.loads(creds_json)

        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )

        client = gspread.authorize(credentials)
        sheet = client.open_by_url(SHEET_URL).sheet1

    except Exception as e:
        print("Google Auth Error:", e)

# =========================
# TELEGRAM INIT
# =========================
if TOKEN:
    application = ApplicationBuilder().token(TOKEN).build()

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
    # START COMMAND
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
            "🚚 BOT DATA BAN KENDARAAN\n\n"
            "Silakan pilih kategori pencarian:",
            reply_markup=reply_markup,
        )

    # =========================
    # HANDLE MESSAGE
    # =========================
    async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):

        if not sheet:
            await update.message.reply_text("Google Sheet belum terkonfigurasi.")
            return

        text = update.message.text.strip()
        data = sheet.get_all_records()

        # =========================
        # PILIH KATEGORI
        # =========================
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
                f"Ketik salah satu untuk melihat detail\n\n"
                f"Ketik /start untuk kembali"
            )
            return

        # =========================
        # MODE FILTER
        # =========================
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

            if not hasil:
                hasil = "❌ Data tidak ditemukan"

            await update.message.reply_text(hasil)
            return

        await update.message.reply_text("Ketik /start untuk memulai")

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))


# =========================
# VERCEL HANDLER (FIX 500 ERROR)
# =========================
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def do_POST(self):
        try:
            if not application:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"TOKEN not configured")
                return

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            update = Update.de_json(data, application.bot)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            loop.run_until_complete(application.initialize())
            loop.run_until_complete(application.process_update(update))

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        except Exception as e:
            print("WEBHOOK ERROR:", e)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())