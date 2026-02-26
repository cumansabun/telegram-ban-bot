import json
import os
import asyncio
from http.server import BaseHTTPRequestHandler

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Ambil token dari Environment Variable
TOKEN = os.environ.get("BOT_TOKEN")

application = None

# Hanya build bot kalau TOKEN tersedia
if TOKEN:
    application = ApplicationBuilder().token(TOKEN).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Bot aktif 🔥")

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Gunakan /start untuk memulai.")

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))


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
                self.wfile.write(b"BOT_TOKEN not configured")
                return

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            update = Update.de_json(data, application.bot)

            asyncio.run(application.process_update(update))

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())