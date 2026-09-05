import telebot
from telebot import types
from datetime import datetime
import requests
import json

# ==================== تنظیمات ====================
BOT_TOKEN = "8811093114:AAFBtc-JOkFMEvdgMOgCklGxuPNUXnd6YDM"
ADMINS = [634374331]  # آیدی ادمین‌ها — می‌تونی آیدی بقیه رو اضافه کنی
CHANNEL = "@tarvideh1"
CARD_NUM = "6104-3387-7176-8823"
CARD_OWNER = "شایان ترویده"
CARD_BANK = "بانک ملت"
DESIGN_ADMIN = "@Tarvideh_Edit"
NUMBER_BOT = "https://t.me/tarvidehnumber_bot"
FOLLOWER_LINK = "https://tarvideh.com/#add_orderbox"
# =================================================

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}
orders_db = []  # لیست سفارشات

# ==================== ابزارها ====================
def get_dollar():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        return int(r.json()["rates"]["IRR"] / 10)
    except:
        return 85000

def is_admin(uid):
    return uid in ADMINS

def add_order(user, service, data):
    order = {
        "id": len(orders_db) + 1,
        "user_id": user.id,
        "user_name": f"{user.first_name} {user.last_name or ''}",
        "username": user.username or "ندارد",
        "service": service,
        "data": data,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "در انتظار بررسی"
    }
    orders_db.append(order)
    return order

def notify_admins(text, markup=None, photo=None):
    for admin_id in ADMINS:
        try:
            if photo:
                bot.send_photo(admin_id, photo, caption=text, parse_mode="Markdown", reply_markup=markup)
            else:
                bot.send_message(admin_id, text, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            print(f"Error notifying admin {admin_id}: {e}")

def back_btn():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 بازگشت به منو"))
    return markup

# ==================== منو اصلی ====================
def main_menu(chat_id, name=""):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🔄 بازگردانی پیج دیسیبل"),
        types.KeyboardButton("🚫 رفع محدودیت"),
        types.KeyboardButton("✈️ پریمیوم تلگرام"),
        types.KeyboardButton("👥 خرید فالوور"),
        types.KeyboardButton("📱 شماره مجازی"),
        types.KeyboardButton("🛡️ امنیت پیج"),
        types.KeyboardButton("🎨 ادیت و طراحی"),
        types.KeyboardButton("📢 کانال ما"),
        types.KeyboardButton("📞 پشتیبانی")
    )
    greeting = f"سلام *{name}* عزیز! 👋\n\n" if name else ""
    bot.send_message(chat_id,
        f"{greeting}"
        "━━━━━━━━━━━━━━━━━━\n"
        "🏆 *ربات رسمی ترویده*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "⚡ خدمات ما:\n"
        "• بازگردانی پیج اینستاگرام\n"
        "• رفع محدودیت و بلاک اکشن\n"
        "• امنیت و هک‌پروف کردن پیج\n"
        "• پریمیوم تلگرام\n"
        "• شماره مجازی و فالوور\n"
        "• ادیت و طراحی محتوا\n\n"
        "👇 خدمت مورد نظرت رو انتخاب کن:",
        parse_mode="Markdown", reply_markup=markup)

# ==================== استارت ====================
@bot.message_handler(commands=['start'])
def start(message):
    user_data.pop(message.from_user.id, None)
    main_menu(message.chat.id, message.from_user.first_name)

@bot.message_handler(func=lambda m: m.text == "🔙 بازگشت به منو")
def back_to_menu(message):
    user_data.pop(message.from_user.id, None)
    main_menu(message.chat.id)

# ==================== پنل ادمین ====================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id):
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📋 لیست سفارشات"),
        types.KeyboardButton("👥 مدیریت ادمین‌ها"),
        types.KeyboardButton("📊 آمار"),
        types.KeyboardButton("📢 ارسال پیام همگانی"),
        types.KeyboardButton("🔙 بازگشت به منو")
    )
    bot.send_message(message.chat.id,
        "🔐 *پنل مدیریت ترویده*\n\n"
        f"👤 ادمین: {message.from_user.first_name}\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        "گزینه مورد نظر رو انتخاب کن:",
        parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📋 لیست سفارشات" and is_admin(m.from_user.id))
def orders_list(message):
    if not orders_db:
        bot.send_message(message.chat.id, "📭 هیچ سفارشی ثبت نشده.")
        return
    text = "📋 *لیست سفارشات:*\n\n"
    for o in orders_db[-10:]:
        text += (
            f"🔢 سفارش #{o['id']}\n"
            f"👤 {o['user_name']} | @{o['username']}\n"
            f"🛒 {o['service']}\n"
            f"📌 وضعیت: {o['status']}\n"
            f"🕐 {o['time']}\n"
            "─────────────\n"
        )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👥 مدیریت ادمین‌ها" and is_admin(m.from_user.id))
def manage_admins(message):
    text = "👥 *ادمین‌های فعال:*\n\n"
    for i, aid in enumerate(ADMINS, 1):
        text += f"{i}. `{aid}`\n"
    text += "\n➕ برای اضافه کردن ادمین جدید:\n/addadmin [آیدی عددی]\n\n➖ برای حذف:\n/removeadmin [آیدی عددی]"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    if not is_admin(message.from_user.id):
        return
    try:
        new_id = int(message.text.split()[1])
        if new_id not in ADMINS:
            ADMINS.append(new_id)
            bot.send_message(message.chat.id, f"✅ ادمین `{new_id}` اضافه شد.", parse_mode="Markdown")
            notify_admins(f"🔔 ادمین جدید اضافه شد: `{new_id}`")
        else:
            bot.send_message(message.chat.id, "⚠️ این آیدی قبلاً ادمین بوده.")
    except:
        bot.send_message(message.chat.id, "❌ فرمت اشتباه.\nمثال: /addadmin 123456789")

@bot.message_handler(commands=['removeadmin'])
def remove_admin(message):
    if not is_admin(message.from_user.id):
        return
    try:
        rem_id = int(message.text.split()[1])
        if rem_id == 634374331:
            bot.send_message(message.chat.id, "❌ نمیشه ادمین اصلی رو حذف کرد.")
            return
        if rem_id in ADMINS:
            ADMINS.remove(rem_id)
            bot.send_message(message.chat.id, f"✅ ادمین `{rem_id}` حذف شد.", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "⚠️ این آیدی ادمین نیست.")
    except:
        bot.send_message(message.chat.id, "❌ فرمت اشتباه.\nمثال: /removeadmin 123456789")

@bot.message_handler(func=lambda m: m.text == "📊 آمار" and is_admin(m.from_user.id))
def stats(message):
    total = len(orders_db)
    services = {}
    for o in orders_db:
        services[o['service']] = services.get(o['service'], 0) + 1
    text = f"📊 *آمار ربات*\n\n🔢 کل سفارشات: {total}\n\n📈 به تفکیک سرویس:\n"
    for s, c in services.items():
        text += f"• {s}: {c} سفارش\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📢 ارسال پیام همگانی" and is_admin(m.from_user.id))
def broadcast_start(message):
    user_data[message.from_user.id] = {"step": "broadcast"}
    bot.send_message(message.chat.id, "📢 پیام همگانی رو بنویس:", reply_markup=back_btn())

# ==================== بازگردانی دیسیبل ====================
@bot.message_handler(func=lambda m: m.text == "🔄 بازگردانی پیج دیسیبل")
def disabled_start(message):
    user_data[message.from_user.id] = {"service": "🔄 بازگردانی پیج دیسیبل", "step": "dis_id"}
    markup = back_btn()
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n"
        "🔄 *بازگردانی پیج دیسیبل*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "ℹ️ برای بررسی و بازگردانی پیجت به اطلاعات زیر نیاز داریم.\n\n"
        "📝 *مرحله ۱ از ۷*\n"
        "آیدی پیج اینستاگرامت رو بفرست:\n"
        "_مثال: @username_",
        parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_id")
def dis_id(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    user_data[message.from_user.id]["ig_id"] = message.text
    user_data[message.from_user.id]["step"] = "dis_email"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۲ از ۷*\n"
        "ایمیل متصل به پیجت رو بفرست:\n"
        "_اگه نداری بنویس: ندارم_",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_email")
def dis_email(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    user_data[message.from_user.id]["email"] = message.text
    user_data[message.from_user.id]["step"] = "dis_pic"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۳ از ۷*\n"
        "آخرین تصویری که هنگام ورود به پیج دیدی رو بفرست 📸\n"
        "_اگه نداری بنویس: ندارم_",
        parse_mode="Markdown")

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_pic")
def dis_pic_photo(message):
    user_data[message.from_user.id]["last_pic"] = message.photo[-1].file_id
    user_data[message.from_user.id]["last_pic_type"] = "photo"
    user_data[message.from_user.id]["step"] = "dis_topic"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۴ از ۷*\n"
        "موضوع پیجت چیه؟\n"
        "_مثال: فروش محصول، آموزش، پزشکی و..._",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_pic")
def dis_pic_text(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    user_data[message.from_user.id]["last_pic"] = message.text
    user_data[message.from_user.id]["last_pic_type"] = "text"
    user_data[message.from_user.id]["step"] = "dis_topic"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۴ از ۷*\n"
        "موضوع پیجت چیه؟\n"
        "_مثال: فروش محصول، آموزش، پزشکی و..._",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_topic")
def dis_topic(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    user_data[message.from_user.id]["topic"] = message.text
    user_data[message.from_user.id]["step"] = "dis_type"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("💼 کاری"), types.KeyboardButton("👤 شخصی"))
    markup.add(types.KeyboardButton("🔙 بازگشت به منو"))
    bot.send_message(message.chat.id,
        "📝 *مرحله ۵ از ۷*\n"
        "پیجت کاری بوده یا شخصی؟",
        parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_type")
def dis_type(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    user_data[message.from_user.id]["page_type"] = message.text
    user_data[message.from_user.id]["step"] = "dis_followers"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۶ از ۷*\n"
        "تعداد تقریبی فالوور پیج چقدر بود؟",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_followers")
def dis_followers(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    user_data[message.from_user.id]["followers"] = message.text
    user_data[message.from_user.id]["step"] = "dis_desc"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۷ از ۷*\n"
        "توضیح کامل از اتفاقی که افتاده:\n\n"
        "• چه زمانی دیسیبل شد؟\n"
        "• چه پیامی نشون میده؟\n"
        "• قبلاً اخطار گرفتی؟\n"
        "• دلیل احتمالی چیه؟",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_desc")
def dis_desc(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    d = user_data[message.from_user.id]
    d["desc"] = message.text
    u = message.from_user
    order = add_order(u, d["service"], d)

    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n"
        f"✅ *سفارش #{order['id']} ثبت شد!*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📋 خلاصه سفارش:\n"
        f"📸 پیج: {d.get('ig_id')}\n"
        f"📌 موضوع: {d.get('topic')}\n"
        f"🏷️ نوع: {d.get('page_type')}\n"
        f"👥 فالوور: {d.get('followers')}\n\n"
        "⏳ تیم ما در کمتر از *۲۴ ساعت* بررسی می‌کنه و اینجا بهت پاسخ میده.\n\n"
        f"📢 کانال ما: {CHANNEL}",
        parse_mode="Markdown")
    main_menu(message.chat.id)

    admin_text = (
        f"🔔 *سفارش جدید #{order['id']} — بازگردانی دیسیبل*\n\n"
        f"👤 {u.first_name} {u.last_name or ''}\n"
        f"🆔 @{u.username or 'ندارد'} | `{u.id}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"📸 آیدی پیج: {d.get('ig_id')}\n"
        f"📧 ایمیل: {d.get('email')}\n"
        f"📌 موضوع: {d.get('topic')}\n"
        f"🏷️ نوع: {d.get('page_type')}\n"
        f"👥 فالوور: {d.get('followers')}\n"
        f"📝 توضیحات: {d.get('desc')}\n"
        f"🕐 {order['time']}\n"
        "━━━━━━━━━━━━━━━\n"
        "🔗 لینک‌های رسیدگی:\n"
        "• instagram.com/hacked\n"
        "• help.instagram.com\n"
        "• facebook.com/help/instagram"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ پاسخ", callback_data=f"reply_{u.id}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{u.id}"),
        types.InlineKeyboardButton("✔️ تأیید سفارش", callback_data=f"confirm_{order['id']}"),
    )
    if d.get("last_pic_type") == "photo":
        notify_admins(admin_text, markup, d["last_pic"])
    else:
        notify_admins(admin_text, markup)
    del user_data[message.from_user.id]

# ==================== رفع محدودیت ====================
@bot.message_handler(func=lambda m: m.text == "🚫 رفع محدودیت")
def limit_start(message):
    user_data[message.from_user.id] = {"service": "🚫 رفع محدودیت", "step": "lim_pic"}
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n"
        "🚫 *رفع محدودیت پیج*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📝 *مرحله ۱ از ۳*\n"
        "اسکرین‌شات از بخش *وضعیت حساب* پیجت بفرست:\n\n"
        "📌 مسیر: تنظیمات ← حساب ← وضعیت حساب",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "lim_pic")
def lim_pic(message):
    user_data[message.from_user.id]["screenshot"] = message.photo[-1].file_id
    user_data[message.from_user.id]["step"] = "lim_id"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۲ از ۳*\n"
        "آیدی پیجت رو بفرست:",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "lim_id")
def lim_id(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    user_data[message.from_user.id]["ig_id"] = message.text
    user_data[message.from_user.id]["step"] = "lim_desc"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۳ از ۳*\n"
        "چه محدودیتی داری و از کی شروع شده؟\n\n"
        "مثال: بلاک اکشن، محدودیت هشتگ، محدودیت کامنت، و...",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "lim_desc")
def lim_desc(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    d = user_data[message.from_user.id]
    d["desc"] = message.text
    u = message.from_user
    order = add_order(u, d["service"], d)

    bot.send_message(message.chat.id,
        f"✅ *سفارش #{order['id']} ثبت شد!*\n\n"
        "تیم ما بررسی می‌کنه و همینجا پاسخ میده.\n"
        "⏳ کمتر از ۲۴ ساعت",
        parse_mode="Markdown")
    main_menu(message.chat.id)

    admin_text = (
        f"🔔 *سفارش #{order['id']} — رفع محدودیت*\n\n"
        f"👤 {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"📸 آیدی: {d.get('ig_id')}\n"
        f"📝 محدودیت: {d.get('desc')}\n"
        f"🕐 {order['time']}"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ پاسخ", callback_data=f"reply_{u.id}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{u.id}")
    )
    try:
        notify_admins(admin_text, markup, d["screenshot"])
    except:
        notify_admins(admin_text, markup)
    del user_data[message.from_user.id]

# ==================== پریمیوم تلگرام ====================
@bot.message_handler(func=lambda m: m.text == "✈️ پریمیوم تلگرام")
def premium_start(message):
    toman = get_dollar()
    p3, p6, p12 = 17*toman, 21*toman, 34*toman
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(f"3️⃣ ماهه — 17$ | {p3:,} تومان", callback_data="pr_3"),
        types.InlineKeyboardButton(f"6️⃣ ماهه — 21$ | {p6:,} تومان", callback_data="pr_6"),
        types.InlineKeyboardButton(f"1️⃣ ساله  — 34$ | {p12:,} تومان", callback_data="pr_12"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="pr_back")
    )
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n"
        "✈️ *پریمیوم تلگرام*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "✅ مزایای پریمیوم:\n"
        "• آپلود فایل تا ۴ گیگ\n"
        "• استیکر و ری‌اکشن بیشتر\n"
        "• پروفایل انیمیشن\n"
        "• سرعت دانلود بیشتر\n"
        "• بدون تبلیغات\n\n"
        "👇 پلن مورد نظرت رو انتخاب کن:",
        parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pr_"))
def premium_plan(call):
    if call.data == "pr_back":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        main_menu(call.message.chat.id)
        return
    plan_map = {"pr_3": ("3 ماهه", 17), "pr_6": ("6 ماهه", 21), "pr_12": ("1 ساله", 34)}
    plan_name, dollar = plan_map[call.data]
    toman = get_dollar()
    amount = dollar * toman

    user_data[call.from_user.id] = {
        "service": f"✈️ پریمیوم {plan_name}",
        "plan": plan_name,
        "dollar": dollar,
        "amount": amount,
        "step": "pr_receipt"
    }
    bot.edit_message_text(
        "━━━━━━━━━━━━━━━━━━\n"
        f"✈️ *پریمیوم {plan_name} — {dollar}$*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "💳 *اطلاعات پرداخت:*\n\n"
        f"🏦 بانک: {CARD_BANK}\n"
        f"👤 صاحب: {CARD_OWNER}\n"
        f"💳 شماره کارت:\n`{CARD_NUM}`\n\n"
        f"💰 مبلغ: *{amount:,} تومان*\n"
        f"_(${dollar} × نرخ روز دلار)_\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📝 *مرحله ۱ از ۳*\n"
        "بعد از واریز، *عکس رسید* رو بفرست 📸",
        call.message.chat.id, call.message.message_id,
        parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "pr_receipt")
def pr_receipt(message):
    user_data[message.from_user.id]["receipt"] = message.photo[-1].file_id
    user_data[message.from_user.id]["step"] = "pr_tgid"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۲ از ۳*\n"
        "آیدی تلگرامی که میخوای پریمیوم روش فعال بشه:\n"
        "_مثال: @username_",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "pr_tgid")
def pr_tgid(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    user_data[message.from_user.id]["tg_id"] = message.text
    user_data[message.from_user.id]["step"] = "pr_phone"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۳ از ۳*\n"
        "شماره تلفن اون حساب تلگرام رو بفرست:",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "pr_phone")
def pr_phone(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    d = user_data[message.from_user.id]
    d["tg_phone"] = message.text
    u = message.from_user
    order = add_order(u, d["service"], d)

    bot.send_message(message.chat.id,
        f"✅ *سفارش #{order['id']} ثبت شد!*\n\n"
        "بعد از تأیید رسید، پریمیوم فعال میشه.\n"
        "⏳ معمولاً کمتر از ۲ ساعت",
        parse_mode="Markdown")
    main_menu(message.chat.id)

    admin_text = (
        f"🔔 *سفارش #{order['id']} — {d.get('service')}*\n\n"
        f"👤 {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"📱 آیدی تلگرام: {d.get('tg_id')}\n"
        f"📞 شماره: {d.get('tg_phone')}\n"
        f"💰 مبلغ: {d.get('amount'):,} تومان\n"
        f"🕐 {order['time']}"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ تأیید پرداخت", callback_data=f"reply_{u.id}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{u.id}")
    )
    notify_admins(admin_text, markup, d["receipt"])
    del user_data[message.from_user.id]

# ==================== خرید فالوور ====================
@bot.message_handler(func=lambda m: m.text == "👥 خرید فالوور")
def follower(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🛒 ثبت سفارش فالوور", url=FOLLOWER_LINK))
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n"
        "👥 *خرید فالوور اینستاگرام*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "✅ انواع فالوور:\n"
        "• فالوور ایرانی واقعی\n"
        "• فالوور خارجی\n"
        "• فالوور میکس\n\n"
        "💎 ویژگی‌ها:\n"
        "• ریزش کمتر از ۵٪\n"
        "• تحویل سریع\n"
        "• قیمت مناسب\n\n"
        "👇 برای ثبت سفارش:",
        parse_mode="Markdown", reply_markup=markup)

# ==================== شماره مجازی ====================
@bot.message_handler(func=lambda m: m.text == "📱 شماره مجازی")
def number(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📱 ربات خرید شماره مجازی", url=NUMBER_BOT))
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n"
        "📱 *خرید شماره مجازی*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "✅ کاربردها:\n"
        "• ساخت اکانت اینستاگرام\n"
        "• ساخت اکانت تلگرام\n"
        "• دریافت OTP\n"
        "• ثبت‌نام سایت‌های خارجی\n\n"
        "👇 برای خرید به ربات اختصاصی ما مراجعه کن:",
        parse_mode="Markdown", reply_markup=markup)

# ==================== امنیت پیج ====================
@bot.message_handler(func=lambda m: m.text == "🛡️ امنیت پیج")
def security_start(message):
    user_data[message.from_user.id] = {"service": "🛡️ امنیت پیج", "step": "sec_id"}
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n"
        "🛡️ *امنیت پیج اینستاگرام*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🔒 خدمات امنیتی ما:\n"
        "• بررسی سطح امنیت پیج\n"
        "• هک‌پروف کردن اکانت\n"
        "• فعال‌سازی تأیید دو مرحله‌ای\n"
        "• بررسی دسترسی‌های مشکوک\n\n"
        "📝 *مرحله ۱ از ۳*\n"
        "آیدی پیجت رو بفرست:",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "sec_id")
def sec_id(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    user_data[message.from_user.id]["ig_id"] = message.text
    user_data[message.from_user.id]["step"] = "sec_followers"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۲ از ۳*\n"
        "تعداد فالوور پیجت چقدره؟",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "sec_followers")
def sec_followers(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    user_data[message.from_user.id]["followers"] = message.text
    user_data[message.from_user.id]["step"] = "sec_topic"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۳ از ۳*\n"
        "موضوع پیجت چیه؟",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "sec_topic")
def sec_topic(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    d = user_data[message.from_user.id]
    d["topic"] = message.text
    u = message.from_user
    order = add_order(u, d["service"], d)

    bot.send_message(message.chat.id,
        f"✅ *سفارش #{order['id']} ثبت شد!*\n\n"
        "تیم ما بررسی می‌کنه و هزینه و شرایط رو اعلام می‌کنه.\n"
        "⏳ کمتر از ۲۴ ساعت",
        parse_mode="Markdown")
    main_menu(message.chat.id)

    admin_text = (
        f"🔔 *سفارش #{order['id']} — امنیت پیج*\n\n"
        f"👤 {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"📸 آیدی: {d.get('ig_id')}\n"
        f"👥 فالوور: {d.get('followers')}\n"
        f"📌 موضوع: {d.get('topic')}\n"
        f"🕐 {order['time']}"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ پاسخ", callback_data=f"reply_{u.id}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{u.id}")
    )
    notify_admins(admin_text, markup)
    del user_data[message.from_user.id]

# ==================== ادیت و طراحی ====================
@bot.message_handler(func=lambda m: m.text == "🎨 ادیت و طراحی")
def design_start(message):
    user_data[message.from_user.id] = {"service": "🎨 ادیت و طراحی", "step": "des_topic"}
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n"
        "🎨 *ادیت و طراحی محتوا*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "✅ خدمات ما:\n"
        "• طراحی پست و استوری\n"
        "• ادیت ویدیو و ریلز\n"
        "• طراحی بنر و پوستر\n"
        "• ساخت تیزر تبلیغاتی\n"
        "• طراحی لوگو و هایلایت\n\n"
        "📝 *مرحله ۱ از ۳*\n"
        "موضوع محتوایی که میخوای بنویس:",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "des_topic")
def des_topic(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    user_data[message.from_user.id]["topic"] = message.text
    user_data[message.from_user.id]["step"] = "des_type"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=3)
    markup.add(
        types.KeyboardButton("🖼️ عکس/پست"),
        types.KeyboardButton("🎬 ویدیو/ریلز"),
        types.KeyboardButton("🖌️ بنر"),
        types.KeyboardButton("📋 پوستر"),
        types.KeyboardButton("📺 تیزر"),
        types.KeyboardButton("🎯 لوگو"),
        types.KeyboardButton("🔙 بازگشت به منو")
    )
    bot.send_message(message.chat.id,
        "📝 *مرحله ۲ از ۳*\n"
        "نوع محتوا رو انتخاب کن:",
        parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "des_type")
def des_type(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    user_data[message.from_user.id]["content_type"] = message.text
    user_data[message.from_user.id]["step"] = "des_desc"
    bot.send_message(message.chat.id,
        "📝 *مرحله ۳ از ۳*\n"
        "توضیح کامل بده:\n\n"
        "• رنگ و استایل مورد نظر\n"
        "• متن و محتوای دلخواه\n"
        "• ابعاد یا فرمت خاص\n"
        "• هر جزئیات دیگه‌ای",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "des_desc")
def des_desc(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    d = user_data[message.from_user.id]
    d["desc"] = message.text
    u = message.from_user
    order = add_order(u, d["service"], d)

    summary = (
        "━━━━━━━━━━━━━━━━━━\n"
        f"📋 *خلاصه سفارش #{order['id']}*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📌 موضوع: {d.get('topic')}\n"
        f"🎯 نوع: {d.get('content_type')}\n"
        f"📝 توضیحات: {d.get('desc')}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"این لیست رو به {DESIGN_ADMIN} ارسال کن تا تیم ادیت قیمت و شرایط رو اعلام کنن."
    )
    bot.send_message(message.chat.id, summary, parse_mode="Markdown")
    main_menu(message.chat.id)

    admin_text = (
        f"🔔 *سفارش #{order['id']} — ادیت و طراحی*\n\n"
        f"👤 {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"📌 موضوع: {d.get('topic')}\n"
        f"🎯 نوع: {d.get('content_type')}\n"
        f"📝 توضیحات: {d.get('desc')}\n"
        f"🕐 {order['time']}"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ پاسخ", callback_data=f"reply_{u.id}"),
        types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{u.id}")
    )
    notify_admins(admin_text, markup)
    del user_data[message.from_user.id]

# ==================== کانال و پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == "📢 کانال ما")
def channel(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 ورود به کانال ترویده", url=f"https://t.me/{CHANNEL.replace('@','')}"))
    bot.send_message(message.chat.id,
        "📢 *کانال رسمی ترویده*\n\n"
        "آخرین اخبار، تخفیف‌ها و نمونه کارها رو در کانال ما ببین 👇",
        parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 تماس با پشتیبانی", url="https://t.me/tarvideh"))
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n"
        "📞 *پشتیبانی ترویده*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📱 تلگرام: @tarvideh\n"
        f"📢 کانال: {CHANNEL}\n"
        "🌐 سایت: tarvideh.com\n\n"
        "⏰ پاسخگویی: ۲۴/۷\n\n"
        "👇 برای تماس مستقیم:",
        parse_mode="Markdown", reply_markup=markup)

# ==================== پاسخ ادمین ====================
@bot.callback_query_handler(func=lambda c: c.data.startswith("reply_") or c.data.startswith("reject_") or c.data.startswith("confirm_"))
def admin_callbacks(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ شما ادمین نیستید!")
        return

    parts = call.data.split("_")
    action = parts[0]

    if action == "confirm":
        order_id = int(parts[1])
        for o in orders_db:
            if o["id"] == order_id:
                o["status"] = "تأیید شده ✅"
        bot.answer_callback_query(call.id, "✅ سفارش تأیید شد!")
        bot.send_message(call.message.chat.id, f"✅ سفارش #{order_id} تأیید شد.")
        return

    target_id = int(parts[1])
    if action == "reply":
        user_data[f"admin_reply_{call.from_user.id}"] = target_id
        bot.send_message(call.message.chat.id,
            f"✏️ پیامت رو برای کاربر `{target_id}` بنویس:",
            parse_mode="Markdown")
        bot.answer_callback_query(call.id)
    elif action == "reject":
        try:
            bot.send_message(target_id,
                "━━━━━━━━━━━━━━━━━━\n"
                "❌ *سفارش شما رد شد*\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "متأسفانه سفارش شما در این مرحله قابل پردازش نیست.\n\n"
                "برای اطلاعات بیشتر:\n@tarvideh",
                parse_mode="Markdown")
        except:
            pass
        bot.answer_callback_query(call.id, "❌ رد شد.")

@bot.message_handler(func=lambda m: f"admin_reply_{m.from_user.id}" in user_data)
def send_reply(message):
    target_id = user_data[f"admin_reply_{message.from_user.id}"]
    try:
        bot.send_message(target_id,
            "━━━━━━━━━━━━━━━━━━\n"
            "📩 *پیام از تیم ترویده*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"{message.text}",
            parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ پیام ارسال شد!")
    except:
        bot.send_message(message.chat.id, "❌ خطا در ارسال!")
    del user_data[f"admin_reply_{message.from_user.id}"]

# ==================== broadcast ====================
@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "broadcast")
def do_broadcast(message):
    if message.text == "🔙 بازگشت به منو":
        back_to_menu(message); return
    sent = 0
    user_ids = list(set([o["user_id"] for o in orders_db]))
    for uid in user_ids:
        try:
            bot.send_message(uid, f"📢 *پیام از ترویده:*\n\n{message.text}", parse_mode="Markdown")
            sent += 1
        except:
            pass
    bot.send_message(message.chat.id, f"✅ پیام به {sent} کاربر ارسال شد.")
    del user_data[message.from_user.id]
    main_menu(message.chat.id)

# ==================== اجرا ====================
print("✅ ربات ترویده آماده‌ست...")
bot.infinity_polling()
