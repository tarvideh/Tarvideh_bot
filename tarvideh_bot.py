import telebot
from telebot import types
from datetime import datetime

# ==================== تنظیمات ====================
BOT_TOKEN = "8811093114:AAFBtc-JOkFMEvdgMOgCklGxuPNUXnd6YDM"
ADMIN_ID = 634374331  # آیدی شایان ترویده
# =================================================

bot = telebot.TeleBot(BOT_TOKEN)

# ذخیره اطلاعات کاربران در حال پر کردن فرم
user_data = {}

SERVICES = {
    "restore": "🔄 بازگردانی پیج دیسیبل",
    "limit": "🚫 رفع محدودیت پیج",
    "security": "🛡️ امنیت پیج",
    "follower": "👥 خرید فالوور",
    "number": "📱 خرید شماره مجازی",
    "telegram": "✈️ پریمیوم تلگرام",
    "design": "🎨 ادیت و طراحی",
}

# ==================== استارت ====================
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📋 ثبت سفارش جدید"))
    markup.add(types.KeyboardButton("📞 پشتیبانی"), types.KeyboardButton("ℹ️ درباره ما"))

    bot.send_message(
        message.chat.id,
        f"سلام {message.from_user.first_name} عزیز! 👋\n\n"
        "به ربات رسمی *ترویده* خوش اومدی 🎉\n\n"
        "ما در زمینه:\n"
        "🔄 بازگردانی پیج اینستاگرام\n"
        "🚫 رفع محدودیت\n"
        "🛡️ امنیت حساب\n"
        "👥 افزایش فالوور\n\n"
        "خدمات ارائه می‌دیم.\n\n"
        "برای ثبت سفارش دکمه زیر رو بزن 👇",
        parse_mode="Markdown",
        reply_markup=markup
    )

# ==================== ثبت سفارش ====================
@bot.message_handler(func=lambda m: m.text == "📋 ثبت سفارش جدید")
def new_order(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for key, value in SERVICES.items():
        markup.add(types.InlineKeyboardButton(value, callback_data=f"svc_{key}"))

    bot.send_message(
        message.chat.id,
        "🛒 *ثبت سفارش جدید*\n\nلطفاً نوع خدمت مورد نظرت رو انتخاب کن:",
        parse_mode="Markdown",
        reply_markup=markup
    )

# ==================== انتخاب سرویس ====================
@bot.callback_query_handler(func=lambda c: c.data.startswith("svc_"))
def select_service(call):
    service_key = call.data.replace("svc_", "")
    service_name = SERVICES.get(service_key, "نامشخص")

    user_data[call.from_user.id] = {
        "service": service_name,
        "step": "username",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    bot.edit_message_text(
        f"✅ سرویس انتخاب شده: *{service_name}*\n\n"
        "📝 *مرحله ۱ از ۴*\n"
        "آیدی یا لینک پیج اینستاگرامت رو بفرست:\n"
        "_(مثال: @username یا instagram.com/username)_",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )

# ==================== دریافت مراحل فرم ====================
@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "username")
def get_username(message):
    user_data[message.from_user.id]["username"] = message.text
    user_data[message.from_user.id]["step"] = "phone"

    bot.send_message(
        message.chat.id,
        "📝 *مرحله ۲ از ۴*\n"
        "شماره تلفن ثبت شده در اینستاگرام رو بفرست:\n"
        "_(اگه نداری بنویس: ندارم)_",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "phone")
def get_phone(message):
    user_data[message.from_user.id]["phone"] = message.text
    user_data[message.from_user.id]["step"] = "email"

    bot.send_message(
        message.chat.id,
        "📝 *مرحله ۳ از ۴*\n"
        "ایمیل ثبت شده در اینستاگرام رو بفرست:\n"
        "_(اگه نداری بنویس: ندارم)_",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "email")
def get_email(message):
    user_data[message.from_user.id]["email"] = message.text
    user_data[message.from_user.id]["step"] = "description"

    bot.send_message(
        message.chat.id,
        "📝 *مرحله ۴ از ۴*\n"
        "مشکلت رو کامل توضیح بده:\n"
        "_(چه زمانی پیج دیسیبل شد، چه پیامی نشون میده، و هر اطلاعات دیگه‌ای)_",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "description")
def get_description(message):
    user_data[message.from_user.id]["description"] = message.text
    user_data[message.from_user.id]["step"] = "done"

    data = user_data[message.from_user.id]
    user = message.from_user

    # خلاصه سفارش برای کاربر
    summary = (
        "✅ *سفارش شما ثبت شد!*\n\n"
        "━━━━━━━━━━━━━━━\n"
        f"🛒 *سرویس:* {data['service']}\n"
        f"📸 *پیج:* {data['username']}\n"
        f"📱 *شماره:* {data['phone']}\n"
        f"📧 *ایمیل:* {data['email']}\n"
        f"📝 *توضیحات:* {data['description']}\n"
        "━━━━━━━━━━━━━━━\n\n"
        "⏳ تیم ما در کمترین زمان بررسی می‌کنه و باهات تماس می‌گیره.\n\n"
        "🔗 *لینک فرم اینستاگرام:*\n"
        "instagram.com/hacked\n\n"
        "📌 مراحل:\n"
        "۱. لینک بالا رو باز کن\n"
        "۲. My account was disabled رو بزن\n"
        "۳. I think my account was disabled by mistake رو بزن\n"
        "۴. اطلاعات بالا رو وارد کن"
    )

    bot.send_message(message.chat.id, summary, parse_mode="Markdown")

    # اطلاع‌رسانی به ادمین
    admin_msg = (
        "🔔 *سفارش جدید!*\n\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 *کاربر:* {user.first_name} {user.last_name or ''}\n"
        f"🆔 *یوزرنیم:* @{user.username or 'ندارد'}\n"
        f"🔢 *آیدی:* `{user.id}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"🛒 *سرویس:* {data['service']}\n"
        f"📸 *پیج اینستاگرام:* {data['username']}\n"
        f"📱 *شماره:* {data['phone']}\n"
        f"📧 *ایمیل:* {data['email']}\n"
        f"📝 *توضیحات:* {data['description']}\n"
        f"🕐 *زمان:* {data['timestamp']}\n"
        "━━━━━━━━━━━━━━━"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ تایید و پاسخ", callback_data=f"reply_{user.id}"),
        types.InlineKeyboardButton("❌ رد سفارش", callback_data=f"reject_{user.id}")
    )

    bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown", reply_markup=markup)

    # پاک کردن اطلاعات موقت
    del user_data[message.from_user.id]

# ==================== پاسخ ادمین ====================
@bot.callback_query_handler(func=lambda c: c.data.startswith("reply_") or c.data.startswith("reject_"))
def admin_action(call):
    parts = call.data.split("_")
    action = parts[0]
    target_id = int(parts[1])

    if action == "reply":
        bot.send_message(call.message.chat.id, f"✏️ پیام خودت رو بنویس تا برای کاربر {target_id} بفرستم:")
        user_data[f"admin_reply_{call.from_user.id}"] = target_id
    elif action == "reject":
        bot.send_message(target_id, "❌ متأسفانه سفارش شما در این مرحله قابل پردازش نیست.\nلطفاً با پشتیبانی تماس بگیرید.")
        bot.answer_callback_query(call.id, "سفارش رد شد.")

@bot.message_handler(func=lambda m: f"admin_reply_{m.from_user.id}" in user_data)
def send_admin_reply(message):
    target_id = user_data[f"admin_reply_{message.from_user.id}"]
    bot.send_message(target_id, f"📩 *پیام از تیم ترویده:*\n\n{message.text}", parse_mode="Markdown")
    bot.send_message(message.chat.id, "✅ پیام ارسال شد!")
    del user_data[f"admin_reply_{message.from_user.id}"]

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support(message):
    bot.send_message(
        message.chat.id,
        "📞 *پشتیبانی ترویده*\n\n"
        "برای ارتباط با تیم ما:\n"
        "📱 تلگرام: @tarvideh\n"
        "📸 اینستاگرام: @tarvideh\n\n"
        "⏰ ساعات پاسخگویی: ۲۴/۷",
        parse_mode="Markdown"
    )

# ==================== درباره ما ====================
@bot.message_handler(func=lambda m: m.text == "ℹ️ درباره ما")
def about(message):
    bot.send_message(
        message.chat.id,
        "ℹ️ *درباره ترویده*\n\n"
        "ما یه تیم متخصص در زمینه خدمات اینستاگرام هستیم:\n\n"
        "✅ بیش از ۵۰۰۰ پیج بازگردانی شده\n"
        "✅ نرخ موفقیت ۹۸٪\n"
        "✅ پشتیبانی ۲۴ ساعته\n"
        "✅ تضمین کامل\n\n"
        "🌐 سایت: tarvideh.com",
        parse_mode="Markdown"
    )

# ==================== اجرا ====================
print("✅ ربات ترویده در حال اجراست...")
bot.infinity_polling()
