import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from telegram.error import TelegramError

# Load .env values
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
STORAGE_CHANNEL = int(os.getenv("STORAGE_CHANNEL"))
JOIN_LINK = os.getenv("JOIN_LINK")
F_CHANNEL = int(os.getenv("F_CHANNEL"))  # Force subscribe channel ID
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))

# ---------------------- HELPER FUNCTIONS ---------------------- #

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def check_user_joined(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=F_CHANNEL, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except TelegramError:
        return False

# ---------------------- START HANDLER ---------------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user_id = update.effective_user.id

    if len(args) == 0:
        await update.message.reply_text("🟢 Bot Online!\nSend any media to generate a shareable link.")
        return

    try:
        msg_id = int(args[0])
        
        # Check if user joined F_CHANNEL
        user_joined = await check_user_joined(context, user_id)
        
        if not user_joined:
            buttons = [
                [InlineKeyboardButton("✅ Join Now", url=JOIN_LINK)],
                [InlineKeyboardButton("♻️ Retry", callback_data=f"retry_{msg_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await update.message.reply_text(
                "You must join our channel to access this file.\n\nJoin the channel and click Retry.",
                reply_markup=reply_markup
            )
            return

        # User joined, send file
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

    except Exception as e:
        await update.message.reply_text("❌ File not found!")

# ---------------------- RETRY BUTTON HANDLER ---------------------- #

async def retry_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    msg_id = int(query.data.split("_")[1])

    await query.answer()

    # Check if user joined
    user_joined = await check_user_joined(context, user_id)

    if not user_joined:
        await query.edit_message_text(
            text="You still haven't joined the channel. Please join first and then click Retry.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Join Now", url=JOIN_LINK)],
                [InlineKeyboardButton("♻️ Retry", callback_data=f"retry_{msg_id}")]
            ])
        )
        return

    # User joined, send file
    await query.edit_message_text(text="✅ Verification successful! Sending file...")

    try:
        buttons = [
            [InlineKeyboardButton("Join Now", url=JOIN_LINK)]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)

        await context.bot.copy_message(
            chat_id=query.from_user.id,
            from_chat_id=STORAGE_CHANNEL,
            message_id=msg_id,
            caption="",
            reply_markup=reply_markup
        )

    except Exception as e:
        await query.edit_message_text("❌ File not found!")

# ---------------------- MEDIA HANDLER ---------------------- #

async def media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    # Check if message exists and has from_user
    if not msg or not msg.from_user:
        return

    user_id = msg.from_user.id

    # Check if user is admin
    if not is_admin(user_id):
        await msg.reply_text("❌ Sorry! Only admins can upload files.")
        return

    copied = await context.bot.copy_message(
        chat_id=STORAGE_CHANNEL,
        from_chat_id=msg.chat.id,
        message_id=msg.message_id
    )

    file_msg_id = copied.message_id

    bot_username = (await context.bot.get_me()).username
    deep_link = f"https://t.me/{bot_username}?start={file_msg_id}"

    await msg.reply_text(
        f"📥 **Shareable Link:**\n{deep_link}",
        parse_mode="Markdown"
    )

# ---------------------- RUN BOT ---------------------- #

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(retry_callback, pattern="^retry_"))

    app.add_handler(MessageHandler(
        filters.ALL & ~filters.TEXT & ~filters.COMMAND,
        media_handler
    ))

    app.run_polling()

if __name__ == "__main__":
    main()
