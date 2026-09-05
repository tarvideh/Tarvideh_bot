import telebot
from telebot import types
from datetime import datetime
import requests

# ==================== تنظیمات ====================
BOT_TOKEN = "8811093114:AAFBtc-JOkFMEvdgMOgCklGxuPNUXnd6YDM"
ADMIN_ID = 634374331
# =================================================

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

def get_dollar_price():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        rate = r.json()["rates"]["IRR"]
        return int(rate / 10)
    except:
        return 85000  # قیمت پیش‌فرض

def main_menu(chat_id, name=""):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🔄 بازگردانی پیج دیسیبل"),
        types.KeyboardButton("🚫 رفع محدودیت پیج"),
        types.KeyboardButton("✈️ پریمیوم تلگرام"),
        types.KeyboardButton("👥 خرید فالوور"),
        types.KeyboardButton("📱 خرید شماره مجازی"),
        types.KeyboardButton("🛡️ امنیت پیج"),
        types.KeyboardButton("🎨 ادیت و طراحی"),
        types.KeyboardButton("📞 پشتیبانی")
    )
    bot.send_message(
        chat_id,
        f"{'سلام ' + name + ' عزیز! 👋' if name else '👋'}\n\n"
        "به ربات رسمی *ترویده* خوش اومدی 🎉\n\n"
        "لطفاً خدمت مورد نظرت رو انتخاب کن 👇",
        parse_mode="Markdown",
        reply_markup=markup
    )

# ==================== استارت ====================
@bot.message_handler(commands=['start'])
def start(message):
    user_data.pop(message.from_user.id, None)
    main_menu(message.chat.id, message.from_user.first_name)

# ==================== بازگردانی پیج دیسیبل ====================
@bot.message_handler(func=lambda m: m.text == "🔄 بازگردانی پیج دیسیبل")
def disabled_start(message):
    user_data[message.from_user.id] = {"service": "🔄 بازگردانی پیج دیسیبل", "step": "disabled_id"}
    bot.send_message(message.chat.id,
        "🔄 *بازگردانی پیج دیسیبل*\n\n"
        "📝 *مرحله ۱ از ۷*\n"
        "آیدی پیج اینستاگرامت رو بفرست:\n"
        "_مثال: @username_",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "disabled_id")
def disabled_id(message):
    user_data[message.from_user.id]["ig_id"] = message.text
    user_data[message.from_user.id]["step"] = "disabled_email"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۲ از ۷*\n"
        "ایمیل متصل به پیجت رو بفرست:\n"
        "_اگه نداری بنویس: ندارم_",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "disabled_email")
def disabled_email(message):
    user_data[message.from_user.id]["email"] = message.text
    user_data[message.from_user.id]["step"] = "disabled_lastpic"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۳ از ۷*\n"
        "آخرین تصویری که هنگام ورود به پیج مشاهده کردی رو بفرست 📸\n"
        "_اگه نداری بنویس: ندارم_",
        parse_mode="Markdown")

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "disabled_lastpic")
def disabled_lastpic_photo(message):
    user_data[message.from_user.id]["last_pic"] = message.photo[-1].file_id
    user_data[message.from_user.id]["step"] = "disabled_topic"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۴ از ۷*\n"
        "موضوع پیجت چیه؟\n"
        "_مثال: فروش محصول، آموزش، سرگرمی و..._",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "disabled_lastpic")
def disabled_lastpic_text(message):
    user_data[message.from_user.id]["last_pic"] = message.text
    user_data[message.from_user.id]["step"] = "disabled_topic"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۴ از ۷*\n"
        "موضوع پیجت چیه؟\n"
        "_مثال: فروش محصول، آموزش، سرگرمی و..._",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "disabled_topic")
def disabled_topic(message):
    user_data[message.from_user.id]["topic"] = message.text
    user_data[message.from_user.id]["step"] = "disabled_type"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("💼 کاری"), types.KeyboardButton("👤 شخصی"))
    bot.send_message(message.chat.id,
        "📝 *مرحله ۵ از ۷*\n"
        "پیجت کاری بوده یا شخصی؟",
        parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "disabled_type")
def disabled_type(message):
    user_data[message.from_user.id]["page_type"] = message.text
    user_data[message.from_user.id]["step"] = "disabled_followers"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۶ از ۷*\n"
        "تعداد تقریبی فالوور پیجت چقدر بود؟",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "disabled_followers")
def disabled_followers(message):
    user_data[message.from_user.id]["followers"] = message.text
    user_data[message.from_user.id]["step"] = "disabled_desc"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۷ از ۷*\n"
        "یه توضیح کامل از اتفاقی که افتاده بنویس:\n"
        "_چه زمانی دیسیبل شد؟ چه پیامی نشون میده؟ قبلاً اخطار گرفتی؟_",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "disabled_desc")
def disabled_desc(message):
    d = user_data[message.from_user.id]
    d["desc"] = message.text
    d["step"] = "done"
    u = message.from_user

    bot.send_message(message.chat.id,
        "✅ *اطلاعات شما ثبت شد!*\n\n"
        "تیم ترویده در اسرع وقت بررسی می‌کنه و اینجا بهت پاسخ میده.\n\n"
        "⏳ معمولاً در کمتر از ۲۴ ساعت پاسخ دریافت می‌کنی.",
        parse_mode="Markdown")
    main_menu(message.chat.id)

    # پیام ادمین
    admin_text = (
        "🔔 *سفارش جدید — بازگردانی دیسیبل*\n\n"
        f"👤 {u.first_name} {u.last_name or ''} | @{u.username or 'ندارد'} | `{u.id}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"📸 آیدی پیج: {d.get('ig_id')}\n"
        f"📧 ایمیل: {d.get('email')}\n"
        f"📌 موضوع: {d.get('topic')}\n"
        f"🏷️ نوع: {d.get('page_type')}\n"
        f"👥 فالوور: {d.get('followers')}\n"
        f"📝 توضیحات: {d.get('desc')}\n"
        f"🕐 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        "━━━━━━━━━━━━━━━\n"
        "🔗 برای رسیدگی:\n"
        "• instagram.com/hacked\n"
        "• help.instagram.com\n"
        "• facebook.com/help/instagram"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ پاسخ به کاربر", callback_data=f"reply_{u.id}"),
        types.InlineKeyboardButton("❌ رد سفارش", callback_data=f"reject_{u.id}")
    )
    if d.get("last_pic") and d["last_pic"] != "ندارم":
        try:
            bot.send_photo(ADMIN_ID, d["last_pic"], caption=admin_text, parse_mode="Markdown", reply_markup=markup)
        except:
            bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=markup)

    del user_data[message.from_user.id]

# ==================== رفع محدودیت ====================
@bot.message_handler(func=lambda m: m.text == "🚫 رفع محدودیت پیج")
def limit_start(message):
    user_data[message.from_user.id] = {"service": "🚫 رفع محدودیت", "step": "limit_screenshot"}
    bot.send_message(message.chat.id,
        "🚫 *رفع محدودیت پیج*\n\n"
        "📝 *مرحله ۱ از ۳*\n"
        "اسکرین‌شات از بخش *وضعیت حساب (Account Status)* پیجت رو بفرست 📸",
        parse_mode="Markdown")

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "limit_screenshot")
def limit_screenshot(message):
    user_data[message.from_user.id]["screenshot"] = message.photo[-1].file_id
    user_data[message.from_user.id]["step"] = "limit_id"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۲ از ۳*\n"
        "آیدی پیجت رو بفرست:",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "limit_id")
def limit_id(message):
    user_data[message.from_user.id]["ig_id"] = message.text
    user_data[message.from_user.id]["step"] = "limit_desc"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۳ از ۳*\n"
        "توضیح بده چه محدودیتی داری و از کی شروع شده:",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "limit_desc")
def limit_desc(message):
    d = user_data[message.from_user.id]
    d["desc"] = message.text
    u = message.from_user

    bot.send_message(message.chat.id,
        "✅ *اطلاعات ثبت شد!*\n\n"
        "تیم ما بررسی می‌کنه و همینجا در چت پاسخ میده.\n"
        "⏳ معمولاً در کمتر از ۲۴ ساعت.",
        parse_mode="Markdown")
    main_menu(message.chat.id)

    admin_text = (
        "🔔 *سفارش جدید — رفع محدودیت*\n\n"
        f"👤 {u.first_name} {u.last_name or ''} | @{u.username or 'ندارد'} | `{u.id}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"📸 آیدی پیج: {d.get('ig_id')}\n"
        f"📝 توضیحات: {d.get('desc')}\n"
        f"🕐 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ پاسخ به کاربر", callback_data=f"reply_{u.id}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{u.id}")
    )
    try:
        bot.send_photo(ADMIN_ID, d["screenshot"], caption=admin_text, parse_mode="Markdown", reply_markup=markup)
    except:
        bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=markup)

    del user_data[message.from_user.id]

# ==================== پریمیوم تلگرام ====================
@bot.message_handler(func=lambda m: m.text == "✈️ پریمیوم تلگرام")
def premium_start(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    toman = get_dollar_price()
    p3 = f"{17 * toman:,}"
    p6 = f"{21 * toman:,}"
    p12 = f"{34 * toman:,}"
    markup.add(
        types.InlineKeyboardButton(f"3️⃣ ماهه — 17$ ({p3} تومان)", callback_data="premium_3"),
        types.InlineKeyboardButton(f"6️⃣ ماهه — 21$ ({p6} تومان)", callback_data="premium_6"),
        types.InlineKeyboardButton(f"1️⃣ ساله — 34$ ({p12} تومان)", callback_data="premium_12"),
    )
    bot.send_message(message.chat.id,
        "✈️ *پریمیوم تلگرام*\n\nیه پلن رو انتخاب کن:",
        parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("premium_"))
def premium_plan(call):
    plan = call.data.replace("premium_", "")
    toman = get_dollar_price()
    plans = {"3": ("3 ماهه", 17), "6": ("6 ماهه", 21), "12": ("1 ساله", 34)}
    name, dollar = plans[plan]
    amount = f"{dollar * toman:,}"

    user_data[call.from_user.id] = {
        "service": f"✈️ پریمیوم {name}",
        "plan": name,
        "amount": amount,
        "step": "premium_tgid"
    }

    bot.edit_message_text(
        f"✈️ *پریمیوم {name} — {dollar}$ ({amount} تومان)*\n\n"
        "💳 *شماره کارت:*\n"
        "`6104-3387-7176-8823`\n"
        "🏦 بانک ملت | شایان ترویده\n\n"
        f"⚡ مبلغ {dollar}$ × نرخ دلار = *{amount} تومان* رو واریز کن\n\n"
        "📝 *مرحله ۱ از ۳*\n"
        "آیدی تلگرامی که میخوای پریمیوم روش فعال بشه رو بفرست:",
        call.message.chat.id, call.message.message_id,
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "premium_tgid")
def premium_tgid(message):
    user_data[message.from_user.id]["tg_id"] = message.text
    user_data[message.from_user.id]["step"] = "premium_phone"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۲ از ۳*\n"
        "شماره تلگرام اون حساب رو هم بفرست:",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "premium_phone")
def premium_phone(message):
    user_data[message.from_user.id]["tg_phone"] = message.text
    user_data[message.from_user.id]["step"] = "premium_receipt"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۳ از ۳*\n"
        "عکس رسید پرداخت رو بفرست 📸",
        parse_mode="Markdown")

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "premium_receipt")
def premium_receipt(message):
    d = user_data[message.from_user.id]
    u = message.from_user

    bot.send_message(message.chat.id,
        "✅ *سفارش ثبت شد!*\n\n"
        "بعد از تأیید پرداخت، پریمیوم فعال میشه.\n"
        "⏳ معمولاً در کمتر از ۲ ساعت.",
        parse_mode="Markdown")
    main_menu(message.chat.id)

    admin_text = (
        f"🔔 *سفارش جدید — {d.get('service')}*\n\n"
        f"👤 {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"📱 آیدی تلگرام: {d.get('tg_id')}\n"
        f"📞 شماره تلگرام: {d.get('tg_phone')}\n"
        f"💰 مبلغ: {d.get('amount')} تومان\n"
        f"🕐 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ تأیید پرداخت", callback_data=f"reply_{u.id}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{u.id}")
    )
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=admin_text, parse_mode="Markdown", reply_markup=markup)
    del user_data[message.from_user.id]

# ==================== خرید فالوور ====================
@bot.message_handler(func=lambda m: m.text == "👥 خرید فالوور")
def follower(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🛒 ثبت سفارش فالوور", url="https://tarvideh.com/#add_orderbox"))
    bot.send_message(message.chat.id,
        "👥 *خرید فالوور*\n\n"
        "برای ثبت سفارش فالوور از طریق سایت اقدام کن 👇",
        parse_mode="Markdown", reply_markup=markup)

# ==================== خرید شماره مجازی ====================
@bot.message_handler(func=lambda m: m.text == "📱 خرید شماره مجازی")
def virtual_number(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📱 ربات خرید شماره مجازی", url="https://t.me/tarvidehnumber_bot"))
    bot.send_message(message.chat.id,
        "📱 *خرید شماره مجازی*\n\n"
        "برای خرید شماره مجازی به ربات اختصاصی ما مراجعه کن 👇",
        parse_mode="Markdown", reply_markup=markup)

# ==================== امنیت پیج ====================
@bot.message_handler(func=lambda m: m.text == "🛡️ امنیت پیج")
def security_start(message):
    user_data[message.from_user.id] = {"service": "🛡️ امنیت پیج", "step": "sec_id"}
    bot.send_message(message.chat.id,
        "🛡️ *امنیت پیج*\n\n"
        "📝 *مرحله ۱ از ۳*\n"
        "آیدی پیجت رو بفرست:",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "sec_id")
def sec_id(message):
    user_data[message.from_user.id]["ig_id"] = message.text
    user_data[message.from_user.id]["step"] = "sec_followers"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۲ از ۳*\n"
        "تعداد فالوور پیجت چقدره؟",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "sec_followers")
def sec_followers(message):
    user_data[message.from_user.id]["followers"] = message.text
    user_data[message.from_user.id]["step"] = "sec_topic"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۳ از ۳*\n"
        "موضوع پیجت چیه؟",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "sec_topic")
def sec_topic(message):
    d = user_data[message.from_user.id]
    d["topic"] = message.text
    u = message.from_user

    bot.send_message(message.chat.id,
        "✅ *اطلاعات ثبت شد!*\n\n"
        "تیم ما بررسی می‌کنه و هزینه و شرایط همکاری رو بهت اعلام می‌کنه.\n"
        "⏳ معمولاً در کمتر از ۲۴ ساعت.",
        parse_mode="Markdown")
    main_menu(message.chat.id)

    admin_text = (
        "🔔 *سفارش جدید — امنیت پیج*\n\n"
        f"👤 {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"📸 آیدی پیج: {d.get('ig_id')}\n"
        f"👥 فالوور: {d.get('followers')}\n"
        f"📌 موضوع: {d.get('topic')}\n"
        f"🕐 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ پاسخ به کاربر", callback_data=f"reply_{u.id}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{u.id}")
    )
    bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=markup)
    del user_data[message.from_user.id]

# ==================== ادیت و طراحی ====================
@bot.message_handler(func=lambda m: m.text == "🎨 ادیت و طراحی")
def design_start(message):
    user_data[message.from_user.id] = {"service": "🎨 ادیت و طراحی", "step": "design_topic"}
    bot.send_message(message.chat.id,
        "🎨 *ادیت و طراحی*\n\n"
        "📝 *مرحله ۱ از ۳*\n"
        "موضوعی که میخوای محتوا براش ساخته بشه رو بنویس:",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "design_topic")
def design_topic(message):
    user_data[message.from_user.id]["topic"] = message.text
    user_data[message.from_user.id]["step"] = "design_type"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=3)
    markup.add(
        types.KeyboardButton("🖼️ عکس"),
        types.KeyboardButton("🎬 فیلم"),
        types.KeyboardButton("🖌️ بنر"),
        types.KeyboardButton("📋 پوستر"),
        types.KeyboardButton("📺 تیزر")
    )
    bot.send_message(message.chat.id,
        "📝 *مرحله ۲ از ۳*\n"
        "نوع محتوا رو انتخاب کن:",
        parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "design_type")
def design_type(message):
    user_data[message.from_user.id]["content_type"] = message.text
    user_data[message.from_user.id]["step"] = "design_desc"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۳ از ۳*\n"
        "یه توضیح کامل از چیزی که میخوای بنویس:\n"
        "_رنگ، استایل، متن مورد نظر، و هر جزئیاتی که داری_",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "design_desc")
def design_desc(message):
    d = user_data[message.from_user.id]
    d["desc"] = message.text
    u = message.from_user

    summary = (
        "📋 *خلاصه سفارش شما:*\n\n"
        f"📌 موضوع: {d.get('topic')}\n"
        f"🎯 نوع محتوا: {d.get('content_type')}\n"
        f"📝 توضیحات: {d.get('desc')}\n\n"
        "━━━━━━━━━━━━━━━\n"
        "این لیست رو به آیدی زیر ارسال کن تا ادمین‌ها بررسی کنن و قیمت و شرایط رو اعلام کنن:\n\n"
        "👤 @Tarvideh\\_Edit"
    )
    bot.send_message(message.chat.id, summary, parse_mode="Markdown")
    main_menu(message.chat.id)

    admin_text = (
        "🔔 *سفارش جدید — ادیت و طراحی*\n\n"
        f"👤 {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"📌 موضوع: {d.get('topic')}\n"
        f"🎯 نوع: {d.get('content_type')}\n"
        f"📝 توضیحات: {d.get('desc')}\n"
        f"🕐 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ پاسخ به کاربر", callback_data=f"reply_{u.id}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{u.id}")
    )
    bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=markup)
    del user_data[message.from_user.id]

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support(message):
    bot.send_message(message.chat.id,
        "📞 *پشتیبانی ترویده*\n\n"
        "📱 تلگرام: @tarvideh\n"
        "📸 اینستاگرام: @tarvideh\n\n"
        "⏰ پاسخگویی: ۲۴/۷",
        parse_mode="Markdown")

# ==================== پاسخ ادمین ====================
@bot.callback_query_handler(func=lambda c: c.data.startswith("reply_") or c.data.startswith("reject_"))
def admin_action(call):
    if call.from_user.id != ADMIN_ID:
        return
    parts = call.data.split("_")
    action = parts[0]
    target_id = int(parts[1])

    if action == "reply":
        user_data[f"admin_reply_{call.from_user.id}"] = target_id
        bot.send_message(call.message.chat.id, f"✏️ پیامت رو بنویس برای کاربر {target_id}:")
        bot.answer_callback_query(call.id)
    elif action == "reject":
        try:
            bot.send_message(target_id,
                "❌ *متأسفانه سفارش شما در این مرحله قابل پردازش نیست.*\n\n"
                "برای اطلاعات بیشتر با پشتیبانی تماس بگیرید:\n@tarvideh",
                parse_mode="Markdown")
        except:
            pass
        bot.answer_callback_query(call.id, "❌ سفارش رد شد.")

@bot.message_handler(func=lambda m: f"admin_reply_{m.from_user.id}" in user_data)
def send_admin_reply(message):
    target_id = user_data[f"admin_reply_{message.from_user.id}"]
    try:
        bot.send_message(target_id,
            f"📩 *پیام از تیم ترویده:*\n\n{message.text}",
            parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ پیام ارسال شد!")
    except:
        bot.send_message(message.chat.id, "❌ خطا در ارسال پیام!")
    del user_data[f"admin_reply_{message.from_user.id}"]

# ==================== اجرا ====================
print("✅ ربات ترویده شروع به کار کرد...")
bot.infinity_polling()
