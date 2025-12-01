import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Load .env values
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
STORAGE_CHANNEL = int(os.getenv("STORAGE_CHANNEL"))
JOIN_LINK = os.getenv("JOIN_LINK")

# ---------------------- START HANDLER ---------------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if len(args) == 0:
        await update.message.reply_text("🟢 Bot Online!\nSend any media to generate a shareable link.")
        return

    try:
        msg_id = int(args[0])

        buttons = [
            [InlineKeyboardButton("Join Now", url=JOIN_LINK)]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)

        await context.bot.copy_message(
            chat_id=update.effective_chat.id,
            from_chat_id=STORAGE_CHANNEL,
            message_id=msg_id,
            caption="",  
            reply_markup=reply_markup
        )

    except:
        await update.message.reply_text("❌ File not found!")

# ---------------------- MEDIA HANDLER ---------------------- #

async def media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    copied = await context.bot.copy_message(
        chat_id=STORAGE_CHANNEL,
        from_chat_id=msg.chat.id,
        message_id=msg.message_id
    )

    file_msg_id = copied.message_id

    bot_username = (await context.bot.get_me()).username
    deep_link = f"https://t.me/{bot_username}?start={file_msg_id}"

    await msg.reply_text(
        f"🔗 **Shareable Link:**\n{deep_link}",
        parse_mode="Markdown"
    )

# ---------------------- RUN BOT ---------------------- #

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(
        filters.ALL & ~filters.TEXT & ~filters.COMMAND,
        media_handler
    ))

    app.run_polling()

if __name__ == "__main__":
    main()
