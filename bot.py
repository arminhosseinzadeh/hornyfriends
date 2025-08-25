import sqlite3
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler


BOT_TOKEN = "8284001146:AAEjCfaiaINDpMaFEXV9NwuuJZl6q5tkh7k"
CHANNEL_ID = "@irtelcoins" # https://t.me/TestHornyFriends - -1002231359801
ADMINS = [593655077]  # آیدی عددی تلگرام خودت یا چند ادمین
DB_FILE = "videos.db"

# ====== دیتابیس ======
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_key TEXT,
            file_id TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS links (
            link_key TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

def add_link(link_key):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO links (link_key) VALUES (?)", (link_key,))
    conn.commit()
    conn.close()

def get_links():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT link_key FROM links")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def add_video(link_key, file_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO videos (link_key, file_id) VALUES (?, ?)", (link_key, file_id))
    conn.commit()
    conn.close()

def get_videos(link_key):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT file_id FROM videos WHERE link_key=?", (link_key,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def delete_video(file_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM videos WHERE file_id=?", (file_id,))
    conn.commit()
    conn.close()

def delete_link(link_key):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM videos WHERE link_key=?", (link_key,))
    c.execute("DELETE FROM links WHERE link_key=?", (link_key,))
    conn.commit()
    conn.close()

# ====== session ادمین ======
admin_sessions = {}

# ====== بررسی عضویت ======
async def check_membership(user_id, context: CallbackContext):
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ====== ارسال ویدیوها با پیام هشدار مشترک ======
async def send_videos(chat_id, context, videos):
    sent_messages = []

    # پیام هشدار یکبار
    warning_msg = await context.bot.send_message(chat_id=chat_id, text="⚠️ فیلم های ارسالی ربات بعد از 20 ثانیه از ربات پاک میشوند - فیلم را در پی وی دوستان خود یا در پیام های ذخیر شده ارسال و بعد دانلود کنید")
    sent_messages.append(warning_msg.message_id)

    # ارسال ویدیوها
    async def send_video(file_id):
        sent = await context.bot.send_video(chat_id=chat_id, video=file_id)
        sent_messages.append(sent.message_id)

    tasks = [asyncio.create_task(send_video(fid)) for fid in videos]
    await asyncio.gather(*tasks)

    # صبر ۲۰ ثانیه
    await asyncio.sleep(20)

    # حذف پیام‌ها
    for msg_id in sent_messages:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except:
            pass

# ====== /start ======
async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    args = context.args

    if user_id in ADMINS:
        await admin_panel(update, context)
        return

    if not args:
        await update.message.reply_text("👋 سلام! لینک معتبر وارد نشده.")
        return

    link_key = args[0]
    videos = get_videos(link_key)
    if not videos:
        await update.message.reply_text("❌ برای این لینک ویدیویی موجود نیست یا حذف شده.")
        return

    # بررسی عضویت
    if not await check_membership(user_id, context):
        keyboard = [
            [InlineKeyboardButton("👆 عضو کانال شوید", url=f"https://t.me/{CHANNEL_ID.strip('@')}")],
            [InlineKeyboardButton("✅ بررسی عضویت", callback_data=f"check_membership:{link_key}")]
        ]
        await update.message.reply_text(
            "❌ لطفاً ابتدا عضو کانال شوید تا ویدیو را دریافت کنید.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ارسال ویدیوها اگر عضو بود
    await send_videos(update.effective_chat.id, context, videos)

# ====== پنل ادمین ======
async def admin_panel(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("➕ افزودن لینک جدید", callback_data="add_link")],
        [InlineKeyboardButton("📄 مشاهده لینک‌ها و ویدیوها", callback_data="view_links")]
    ]
    await update.message.reply_text("🎛️ پنل ادمین", reply_markup=InlineKeyboardMarkup(keyboard))

# ====== هندلر دکمه‌ها ======
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # ===== مسیر کاربر =====
    if data.startswith("check_membership:"):
        link_key = data.split(":")[1]
        videos = get_videos(link_key)
        if not videos:
            await query.edit_message_text("❌ برای این لینک ویدیویی موجود نیست یا حذف شده.")
            return

        if await check_membership(user_id, context):
            await query.edit_message_text("✅ شما عضو کانال شدید! ویدیوها در حال ارسال هستند...")
            await send_videos(query.message.chat.id, context, videos)
        else:
            await query.answer("❌ هنوز عضو کانال نیستید!", show_alert=True)
        return  # جلوگیری از ورود به مسیر ادمین

    # ===== مسیر ادمین =====
    if user_id not in ADMINS:
        await query.edit_message_text("❌ دسترسی ندارید.")
        return

    if data == "add_link":
        admin_sessions[user_id] = {"action": "await_link"}
        await query.edit_message_text("لطفاً کلید لینک جدید را تایپ کنید:")

    elif data == "view_links":
        links = get_links()
        if not links:
            await query.edit_message_text("📭 هیچ لینکی ثبت نشده.")
            return
        text = "📄 لینک‌ها و تعداد ویدیوها:\n"
        keyboard = []
        for link in links:
            videos = get_videos(link)
            text += f"- {link}: {len(videos)} ویدیو\n"
            keyboard.append([InlineKeyboardButton(f"❌ حذف لینک {link}", callback_data=f"delete_link:{link}")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("delete_link:"):
        link_key = data.split(":")[1]
        delete_link(link_key)
        await query.edit_message_text(f"✅ لینک {link_key} و همه ویدیوهایش حذف شد.")

# ====== هندلر پیام ادمین ======
async def admin_text(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        return

    if user_id in admin_sessions:
        action = admin_sessions[user_id].get("action")
        if action == "await_link":
            link_key = update.message.text.strip()
            add_link(link_key)
            admin_sessions[user_id] = {"action": "await_video", "link": link_key}
            await update.message.reply_text(f"✅ لینک جدید `{link_key}` اضافه شد. حالا می‌توانید ویدیو ارسال کنید.", parse_mode="Markdown")

# ====== هندلر ویدیو ادمین ======
async def video_handler_admin(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        return
    if user_id not in admin_sessions or admin_sessions[user_id].get("action") != "await_video":
        await update.message.reply_text("❌ ابتدا لینک را اضافه کنید یا انتخاب کنید.")
        return

    file_id = None
    if update.message.video:
        file_id = update.message.video.file_id
    elif update.message.document and update.message.document.mime_type.startswith("video/"):
        file_id = update.message.document.file_id

    if not file_id:
        await update.message.reply_text("❌ لطفاً یک ویدیوی معتبر ارسال کنید.")
        return

    link_key = admin_sessions[user_id]["link"]
    add_video(link_key, file_id)
    await update.message.reply_text(f"✅ ویدیو برای لینک `{link_key}` ذخیره شد.", parse_mode="Markdown")

# ====== ران ربات ======
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT, admin_text))
    video_filter = filters.VIDEO | (filters.Document.MimeType("video/mp4"))
    app.add_handler(MessageHandler(video_filter, video_handler_admin))
    print("🤖 ربات آماده و اجرا شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
