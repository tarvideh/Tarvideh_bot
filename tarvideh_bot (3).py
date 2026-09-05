import telebot
from telebot import types
from datetime import datetime
import requests

# ==================== تنظیمات ====================
BOT_TOKEN = "8811093114:AAFBtc-JOkFMEvdgMOgCklGxuPNUXnd6YDM"
ADMINS = [634374331]
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
orders_db = []

# ===== وضعیت سفارشات =====
STATUS = {
    "pending": "⏳ در انتظار بررسی",
    "reviewing": "🔍 در حال بررسی",
    "processing": "⚙️ در حال انجام",
    "done": "✅ تکمیل شده",
    "cancelled": "❌ لغو شده"
}

# ===== فرم‌های اینستاگرام برای ادمین =====
FORMS = {
    "disabled": [
        ("🔴 فرم اصلی بازگردانی", "https://www.instagram.com/hacked/?hl=en"),
        ("🔴 فرم هک و رمز", "https://instagram.com/hacked"),
        ("📘 فرم فیسبوک/متا", "https://www.facebook.com/business/help"),
        ("📘 فرم 2 فیسبوک", "https://is.gd/xpHtXL"),
        ("📘 فرم 3 فیسبوک", "https://www.facebook.com/help/contact/507270721277573"),
        ("📘 فرم 4 فیسبوک", "http://business.facebook.com"),
        ("🔑 فرم ریست پسورد", "https://www.instagram.com/accounts/password/reset/?ref=faqhelpindex"),
        ("🆘 فرم SH", "https://help.instagram.com/contact/814820110107093"),
        ("📧 ایمیل اندروید متا", "instagram-android@meta.com"),
        ("🌐 اینستا هلپ", "https://help.instagram.com"),
    ],
    "limit": [
        ("🔴 فرم اصلی", "https://www.instagram.com/hacked/?hl=en"),
        ("⚖️ گزارش تخلف حقوق", "https://help.instagram.com/contact/372592039493026"),
        ("🛡️ گزارش حریم خصوصی", "https://help.instagram.com/contact/512241091300432"),
        ("📋 قوانین انجمن", "https://help.instagram.com/"),
        ("📘 فرم متا", "https://is.gd/xpHtXL"),
        ("🌐 اینستا هلپ", "https://help.instagram.com"),
    ],
    "fake": [
        ("👤 گزارش جعل هویت", "https://help.instagram.com/contact/636276399721841"),
        ("™️ فرم علامت تجاری", "https://help.instagram.com/contact/230197320740525"),
        ("🚫 گزارش آزار و اذیت", "https://help.instagram.com/547601325292351"),
        ("📋 گزارش تخلف", "https://help.instagram.com/contact/372592039493026"),
        ("🔴 فرم اصلی", "https://www.instagram.com/hacked/?hl=en"),
    ],
    "emails": [
        "security@mail.instagram.com",
        "support@instagram.com",
        "help@instagram.com",
    ]
}

def get_dollar():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        usd = int(r.json()["rates"]["IRR"] / 10)
        return usd
    except:
        return 85000

def get_gold():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/XAU", timeout=5)
        irr = r.json()["rates"]["IRR"]
        toman = int(irr / 10)
        return toman
    except:
        return None

def is_admin(uid): return uid in ADMINS

def add_order(user, service, data):
    order = {
        "id": len(orders_db) + 1,
        "user_id": user.id,
        "user_name": f"{user.first_name} {user.last_name or ''}".strip(),
        "username": user.username or "ندارد",
        "service": service,
        "data": data,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "pending"
    }
    orders_db.append(order)
    return order

def notify_admins(text, markup=None, photo=None):
    for aid in ADMINS:
        try:
            if photo:
                bot.send_photo(aid, photo, caption=text, parse_mode="Markdown", reply_markup=markup)
            else:
                bot.send_message(aid, text, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            print(f"Admin notify error {aid}: {e}")

def back_btn():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add(types.KeyboardButton("🔙 بازگشت به منو"))
    return m

def forms_inline(form_type):
    m = types.InlineKeyboardMarkup(row_width=1)
    for name, url in FORMS.get(form_type, []):
        if url.startswith("http"):
            m.add(types.InlineKeyboardButton(name, url=url))
        else:
            m.add(types.InlineKeyboardButton(f"📧 {url}", callback_data=f"copy_{url}"))
    return m

def order_action_markup(user_id, order_id):
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("✅ پاسخ", callback_data=f"reply_{user_id}"),
        types.InlineKeyboardButton("🔍 در بررسی", callback_data=f"status_{order_id}_reviewing"),
        types.InlineKeyboardButton("⚙️ در انجام", callback_data=f"status_{order_id}_processing"),
        types.InlineKeyboardButton("✅ تکمیل", callback_data=f"status_{order_id}_done"),
        types.InlineKeyboardButton("❌ لغو", callback_data=f"status_{order_id}_cancelled"),
    )
    return m

# ==================== منو اصلی ====================
def main_menu(chat_id, name=""):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        types.KeyboardButton("🔄 بازگردانی پیج دیسیبل"),
        types.KeyboardButton("🚫 رفع محدودیت"),
        types.KeyboardButton("🗑️ حذف پیج جعلی/آزاردهنده"),
        types.KeyboardButton("✈️ پریمیوم تلگرام"),
        types.KeyboardButton("👥 خرید فالوور"),
        types.KeyboardButton("📱 شماره مجازی"),
        types.KeyboardButton("🛡️ امنیت پیج"),
        types.KeyboardButton("🎨 ادیت و طراحی"),
        types.KeyboardButton("💡 ایده محتوایی"),
        types.KeyboardButton("💰 قیمت دلار و طلا"),
        types.KeyboardButton("📢 کانال ما"),
        types.KeyboardButton("📞 پشتیبانی")
    )
    g = f"سلام *{name}* عزیز! 👋\n\n" if name else ""
    bot.send_message(chat_id,
        f"{g}"
        "━━━━━━━━━━━━━━━━━━\n"
        "🏆 *ربات رسمی ترویده*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "✨ خدمات تخصصی ما:\n"
        "🔄 بازگردانی پیج دیسیبل\n"
        "🚫 رفع محدودیت و بلاک اکشن\n"
        "🗑️ حذف پیج‌های جعلی و آزاردهنده\n"
        "🛡️ امنیت و هک‌پروف کردن پیج\n"
        "✈️ پریمیوم تلگرام\n"
        "📱 شماره مجازی\n"
        "👥 فالوور اینستاگرام\n"
        "🎨 ادیت و طراحی محتوا\n\n"
        "👇 خدمت مورد نظرت رو انتخاب کن:",
        parse_mode="Markdown", reply_markup=m)

@bot.message_handler(commands=['start'])
def start(message):
    user_data.pop(message.from_user.id, None)
    main_menu(message.chat.id, message.from_user.first_name)

@bot.message_handler(func=lambda m: m.text == "🔙 بازگشت به منو")
def go_back(message):
    user_data.pop(message.from_user.id, None)
    main_menu(message.chat.id)

# ==================== پنل ادمین ====================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id): return
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        types.KeyboardButton("📋 همه سفارشات"),
        types.KeyboardButton("⏳ در انتظار بررسی"),
        types.KeyboardButton("🔍 در حال بررسی"),
        types.KeyboardButton("⚙️ در حال انجام"),
        types.KeyboardButton("✅ تکمیل‌شده‌ها"),
        types.KeyboardButton("❌ لغوشده‌ها"),
        types.KeyboardButton("📊 آمار کلی"),
        types.KeyboardButton("👥 مدیریت ادمین‌ها"),
        types.KeyboardButton("📢 پیام همگانی"),
        types.KeyboardButton("🔙 بازگشت به منو")
    )
    bot.send_message(message.chat.id,
        "🔐 *پنل مدیریت ترویده*\n\n"
        f"👤 {message.from_user.first_name}\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        "گزینه مورد نظر رو انتخاب کن:",
        parse_mode="Markdown", reply_markup=m)

def show_orders_by_status(chat_id, status_key=None):
    if status_key:
        filtered = [o for o in orders_db if o["status"] == status_key]
        title = STATUS.get(status_key, "سفارشات")
    else:
        filtered = orders_db[-20:]
        title = "همه سفارشات"

    if not filtered:
        bot.send_message(chat_id, f"📭 هیچ سفارشی در وضعیت *{title}* وجود نداره.", parse_mode="Markdown")
        return

    for o in filtered[-10:]:
        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(
            types.InlineKeyboardButton("✅ پاسخ", callback_data=f"reply_{o['user_id']}"),
            types.InlineKeyboardButton("🔍 در بررسی", callback_data=f"status_{o['id']}_reviewing"),
            types.InlineKeyboardButton("⚙️ در انجام", callback_data=f"status_{o['id']}_processing"),
            types.InlineKeyboardButton("✅ تکمیل", callback_data=f"status_{o['id']}_done"),
            types.InlineKeyboardButton("❌ لغو", callback_data=f"status_{o['id']}_cancelled"),
        )
        text = (
            f"🔢 *سفارش #{o['id']}*\n"
            f"📌 {o['service']}\n"
            f"👤 {o['user_name']} | @{o['username']}\n"
            f"🆔 `{o['user_id']}`\n"
            f"📊 وضعیت: {STATUS.get(o['status'], o['status'])}\n"
            f"🕐 {o['time']}"
        )
        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=m)

@bot.message_handler(func=lambda m: m.text == "📋 همه سفارشات" and is_admin(m.from_user.id))
def all_orders(message): show_orders_by_status(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "⏳ در انتظار بررسی" and is_admin(m.from_user.id))
def pending_orders(message): show_orders_by_status(message.chat.id, "pending")

@bot.message_handler(func=lambda m: m.text == "🔍 در حال بررسی" and is_admin(m.from_user.id))
def reviewing_orders(message): show_orders_by_status(message.chat.id, "reviewing")

@bot.message_handler(func=lambda m: m.text == "⚙️ در حال انجام" and is_admin(m.from_user.id))
def processing_orders(message): show_orders_by_status(message.chat.id, "processing")

@bot.message_handler(func=lambda m: m.text == "✅ تکمیل‌شده‌ها" and is_admin(m.from_user.id))
def done_orders(message): show_orders_by_status(message.chat.id, "done")

@bot.message_handler(func=lambda m: m.text == "❌ لغوشده‌ها" and is_admin(m.from_user.id))
def cancelled_orders(message): show_orders_by_status(message.chat.id, "cancelled")

@bot.message_handler(func=lambda m: m.text == "📊 آمار کلی" and is_admin(m.from_user.id))
def stats(message):
    total = len(orders_db)
    by_status = {k: 0 for k in STATUS}
    by_service = {}
    for o in orders_db:
        by_status[o["status"]] = by_status.get(o["status"], 0) + 1
        by_service[o["service"]] = by_service.get(o["service"], 0) + 1
    text = f"📊 *آمار کلی ربات*\n\n🔢 کل سفارشات: *{total}*\n\n"
    text += "📈 *به تفکیک وضعیت:*\n"
    for k, v in STATUS.items():
        text += f"{v}: {by_status.get(k, 0)}\n"
    text += "\n📈 *به تفکیک سرویس:*\n"
    for s, c in sorted(by_service.items(), key=lambda x: -x[1]):
        text += f"• {s}: {c}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👥 مدیریت ادمین‌ها" and is_admin(m.from_user.id))
def manage_admins(message):
    text = "👥 *ادمین‌های فعال:*\n\n"
    for i, aid in enumerate(ADMINS, 1):
        text += f"{i}. `{aid}`\n"
    text += "\n➕ اضافه کردن: /addadmin [آیدی]\n➖ حذف: /removeadmin [آیدی]"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    if not is_admin(message.from_user.id): return
    try:
        nid = int(message.text.split()[1])
        if nid not in ADMINS:
            ADMINS.append(nid)
            bot.send_message(message.chat.id, f"✅ ادمین `{nid}` اضافه شد.", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "⚠️ قبلاً ادمین بوده.")
    except:
        bot.send_message(message.chat.id, "❌ مثال: /addadmin 123456789")

@bot.message_handler(commands=['removeadmin'])
def remove_admin(message):
    if not is_admin(message.from_user.id): return
    try:
        rid = int(message.text.split()[1])
        if rid == 634374331:
            bot.send_message(message.chat.id, "❌ ادمین اصلی قابل حذف نیست."); return
        if rid in ADMINS:
            ADMINS.remove(rid)
            bot.send_message(message.chat.id, f"✅ ادمین `{rid}` حذف شد.", parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ مثال: /removeadmin 123456789")

@bot.message_handler(func=lambda m: m.text == "📢 پیام همگانی" and is_admin(m.from_user.id))
def broadcast_ask(message):
    user_data[message.from_user.id] = {"step": "broadcast"}
    bot.send_message(message.chat.id, "📢 پیامت رو بنویس:", reply_markup=back_btn())

@bot.callback_query_handler(func=lambda c: c.data.startswith("status_"))
def change_status(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ دسترسی ندارید!"); return
    parts = call.data.split("_")
    order_id = int(parts[1])
    new_status = parts[2]
    for o in orders_db:
        if o["id"] == order_id:
            o["status"] = new_status
            try:
                bot.send_message(o["user_id"],
                    f"📢 *آپدیت سفارش #{order_id}*\n\n"
                    f"📊 وضعیت جدید: *{STATUS.get(new_status)}*\n\n"
                    "تیم ترویده در حال پیگیری سفارش شماست.",
                    parse_mode="Markdown")
            except: pass
            bot.answer_callback_query(call.id, f"✅ وضعیت به {STATUS[new_status]} تغییر کرد.")
            return
    bot.answer_callback_query(call.id, "❌ سفارش پیدا نشد.")

# ==================== بازگردانی دیسیبل ====================
@bot.message_handler(func=lambda m: m.text == "🔄 بازگردانی پیج دیسیبل")
def dis_start(message):
    user_data[message.from_user.id] = {"service": "🔄 بازگردانی پیج دیسیبل", "step": "dis_id"}
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n"
        "🔄 *بازگردانی پیج دیسیبل*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *خدمات ما شامل:*\n"
        "• بازگردانی پیج‌های permanently disabled\n"
        "• بازگردانی پیج‌های هک شده\n"
        "• بازگردانی پیج‌های دیسیبل به دلیل تخلف\n\n"
        "⭐ نرخ موفقیت: ۹۸٪\n"
        "⏰ زمان تحویل: ۲۴ تا ۷۲ ساعت\n\n"
        "📝 *مرحله ۱ از ۷*\n"
        "آیدی پیج اینستاگرامت رو بفرست:\n_مثال: @username_",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_id")
def dis_id(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"ig_id": message.text, "step": "dis_email"})
    bot.send_message(message.chat.id, "📝 *مرحله ۲ از ۷*\nایمیل متصل به پیجت:\n_اگه نداری: ندارم_", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_email")
def dis_email(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"email": message.text, "step": "dis_pic"})
    bot.send_message(message.chat.id, "📝 *مرحله ۳ از ۷*\nآخرین تصویر هنگام ورود به پیج رو بفرست 📸\n_اگه نداری بنویس: ندارم_", parse_mode="Markdown")

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_pic")
def dis_pic_photo(message):
    user_data[message.from_user.id].update({"last_pic": message.photo[-1].file_id, "pic_type": "photo", "step": "dis_topic"})
    bot.send_message(message.chat.id, "📝 *مرحله ۴ از ۷*\nموضوع پیجت چیه؟\n_مثال: فروش محصول، آموزش، پزشکی_", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_pic")
def dis_pic_text(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"last_pic": message.text, "pic_type": "text", "step": "dis_topic"})
    bot.send_message(message.chat.id, "📝 *مرحله ۴ از ۷*\nموضوع پیجت چیه؟", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_topic")
def dis_topic(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"topic": message.text, "step": "dis_type"})
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    mk.add("💼 کاری", "👤 شخصی", "🔙 بازگشت به منو")
    bot.send_message(message.chat.id, "📝 *مرحله ۵ از ۷*\nپیجت کاری بوده یا شخصی؟", parse_mode="Markdown", reply_markup=mk)

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_type")
def dis_type(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"page_type": message.text, "step": "dis_followers"})
    bot.send_message(message.chat.id, "📝 *مرحله ۶ از ۷*\nتعداد تقریبی فالوور پیج؟", parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_followers")
def dis_followers(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"followers": message.text, "step": "dis_desc"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۷ از ۷*\nتوضیح کامل:\n\n• چه زمانی دیسیبل شد؟\n• چه پیامی نشون میده؟\n• قبلاً اخطار گرفتی؟\n• دلیل احتمالی؟",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_desc")
def dis_desc(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    d = user_data[message.from_user.id]; d["desc"] = message.text
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id,
        f"✅ *سفارش #{order['id']} ثبت شد!*\n\nتیم ما در کمتر از *۲۴ ساعت* بررسی می‌کنه.\n📢 {CHANNEL}",
        parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_action_markup(u.id, order["id"])
    admin_text = (
        f"🔔 *سفارش #{order['id']} — بازگردانی دیسیبل*\n\n"
        f"👤 {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"📸 پیج: {d.get('ig_id')}\n📧 ایمیل: {d.get('email')}\n"
        f"📌 موضوع: {d.get('topic')}\n🏷️ نوع: {d.get('page_type')}\n"
        f"👥 فالوور: {d.get('followers')}\n📝 توضیحات: {d.get('desc')}\n"
        f"🕐 {order['time']}\n"
        "━━━━━━━━━━━━━━━\n🔗 *فرم‌های مرتبط:*\n"
        "• instagram.com/hacked\n• instagram.com/hacked/?hl=en\n"
        "• is.gd/xpHtXL (متا)\n• facebook.com/help/contact/507270721277573\n"
        "• help.instagram.com/contact/814820110107093\n"
        "📧 security@mail.instagram.com"
    )
    if d.get("pic_type") == "photo":
        notify_admins(admin_text, mk, d["last_pic"])
    else:
        notify_admins(admin_text, mk)
    del user_data[message.from_user.id]

# ==================== رفع محدودیت ====================
@bot.message_handler(func=lambda m: m.text == "🚫 رفع محدودیت")
def lim_start(message):
    user_data[message.from_user.id] = {"service": "🚫 رفع محدودیت", "step": "lim_pic"}
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n🚫 *رفع محدودیت پیج*\n━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *انواع محدودیت‌هایی که رفع می‌کنیم:*\n"
        "• بلاک اکشن (لایک، کامنت، فالو)\n• محدودیت هشتگ\n"
        "• محدودیت دایرکت\n• محدودیت لایو\n• سایر محدودیت‌ها\n\n"
        "📝 *مرحله ۱ از ۳*\n"
        "اسکرین‌شات از *وضعیت حساب* پیجت بفرست 📸\n"
        "_(تنظیمات ← حساب ← وضعیت حساب)_",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "lim_pic")
def lim_pic(message):
    user_data[message.from_user.id].update({"screenshot": message.photo[-1].file_id, "step": "lim_id"})
    bot.send_message(message.chat.id, "📝 *مرحله ۲ از ۳*\nآیدی پیجت رو بفرست:", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "lim_id")
def lim_id(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"ig_id": message.text, "step": "lim_desc"})
    bot.send_message(message.chat.id, "📝 *مرحله ۳ از ۳*\nچه محدودیتی داری و از کی شروع شده؟", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "lim_desc")
def lim_desc(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    d = user_data[message.from_user.id]; d["desc"] = message.text
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id, f"✅ *سفارش #{order['id']} ثبت شد!*\n\nتیم ما بررسی می‌کنه و همینجا پاسخ میده.\n⏳ کمتر از ۲۴ ساعت", parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_action_markup(u.id, order["id"])
    admin_text = (
        f"🔔 *سفارش #{order['id']} — رفع محدودیت*\n\n"
        f"👤 {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"📸 پیج: {d.get('ig_id')}\n📝 محدودیت: {d.get('desc')}\n🕐 {order['time']}\n"
        "━━━━━━━━━━━━━━━\n🔗 *فرم‌های مرتبط:*\n"
        "• instagram.com/hacked\n• help.instagram.com/contact/372592039493026\n"
        "• help.instagram.com/contact/512241091300432\n• is.gd/xpHtXL"
    )
    try: notify_admins(admin_text, mk, d["screenshot"])
    except: notify_admins(admin_text, mk)
    del user_data[message.from_user.id]

# ==================== حذف پیج جعلی ====================
@bot.message_handler(func=lambda m: m.text == "🗑️ حذف پیج جعلی/آزاردهنده")
def fake_start(message):
    user_data[message.from_user.id] = {"service": "🗑️ حذف پیج جعلی/آزاردهنده", "step": "fake_id"}
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=1)
    mk.add("👤 جعل هویت (پیج فیک از من)", "😡 آزار و اذیت", "📸 استفاده از عکس‌هام", "🔙 بازگشت به منو")
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n🗑️ *حذف پیج جعلی/آزاردهنده*\n━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *موارد قابل پیگیری:*\n• پیج‌های جعل هویت\n• پیج‌های آزاردهنده\n"
        "• سوءاستفاده از تصاویر\n• پیج‌های تهدیدآمیز\n\n"
        "📝 *مرحله ۱ از ۵*\nدلیل درخواست حذف رو انتخاب کن:",
        parse_mode="Markdown", reply_markup=mk)

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "fake_id")
def fake_reason(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"reason": message.text, "step": "fake_target"})
    bot.send_message(message.chat.id, "📝 *مرحله ۲ از ۵*\nآیدی پیجی که میخوای حذف بشه رو بفرست:", parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "fake_target")
def fake_target(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"target_id": message.text, "step": "fake_original"})
    reason = user_data[message.from_user.id].get("reason", "")
    if "جعل هویت" in reason:
        bot.send_message(message.chat.id, "📝 *مرحله ۳ از ۵*\nآیدی پیج اصلی خودت رو بفرست (که جعل شده):", parse_mode="Markdown")
    else:
        user_data[message.from_user.id]["original_id"] = "---"
        user_data[message.from_user.id]["step"] = "fake_desc"
        bot.send_message(message.chat.id, "📝 *مرحله ۳ از ۵*\nتوضیح کامل بده چه آزار و اذیتی صورت گرفته:", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "fake_original")
def fake_original(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"original_id": message.text, "step": "fake_desc"})
    bot.send_message(message.chat.id, "📝 *مرحله ۴ از ۵*\nتوضیح کامل بده:", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "fake_desc")
def fake_desc(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"desc": message.text, "step": "fake_proof"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۵ از ۵*\n"
        "برای تأیید هویتت یکی از موارد زیر رو بفرست:\n\n"
        "• عکس کارت شناسایی (ملی یا پاسپورت)\n"
        "• یا اسکرین‌شات از پیج اصلی خودت\n\n"
        "_این برای اطمینان از صاحب اصلی چهره/پیج هست_",
        parse_mode="Markdown")

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "fake_proof")
def fake_proof(message):
    d = user_data[message.from_user.id]; d["proof"] = message.photo[-1].file_id
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id,
        f"✅ *سفارش #{order['id']} ثبت شد!*\n\n"
        "تیم ما بررسی می‌کنه و هزینه و زمان مورد نیاز رو بهت اعلام می‌کنه.\n⏳ کمتر از ۲۴ ساعت",
        parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_action_markup(u.id, order["id"])
    admin_text = (
        f"🔔 *سفارش #{order['id']} — حذف پیج جعلی*\n\n"
        f"👤 {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"⚠️ دلیل: {d.get('reason')}\n🎯 پیج هدف: {d.get('target_id')}\n"
        f"✅ پیج اصلی: {d.get('original_id')}\n📝 توضیحات: {d.get('desc')}\n🕐 {order['time']}\n"
        "━━━━━━━━━━━━━━━\n🔗 *فرم‌های مرتبط:*\n"
        "• help.instagram.com/contact/636276399721841 (جعل هویت)\n"
        "• help.instagram.com/547601325292351 (آزار)\n"
        "• help.instagram.com/contact/372592039493026 (تخلف)"
    )
    notify_admins(admin_text, mk, d["proof"])
    del user_data[message.from_user.id]

# ==================== پریمیوم تلگرام ====================
@bot.message_handler(func=lambda m: m.text == "✈️ پریمیوم تلگرام")
def premium_start(message):
    t = get_dollar()
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton(f"3️⃣ ماهه — 17$ | {17*t:,} تومان", callback_data="pr_3"),
        types.InlineKeyboardButton(f"6️⃣ ماهه — 21$ | {21*t:,} تومان", callback_data="pr_6"),
        types.InlineKeyboardButton(f"1️⃣ ساله  — 34$ | {34*t:,} تومان", callback_data="pr_12"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="pr_back")
    )
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n✈️ *پریمیوم تلگرام*\n━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *مزایای پریمیوم:*\n• آپلود فایل تا ۴ گیگابایت\n• استیکر و ری‌اکشن انحصاری\n"
        "• پروفایل ویدیویی انیمیشن\n• سرعت دانلود ۴ برابر بیشتر\n"
        "• بدون تبلیغات\n• ۱۰ اکانت همزمان\n\n"
        "💰 *قیمت‌ها (بر اساس نرخ لحظه‌ای دلار):*\n\n👇 پلن مورد نظرت رو انتخاب کن:",
        parse_mode="Markdown", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pr_"))
def premium_plan(call):
    if call.data == "pr_back":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        main_menu(call.message.chat.id); return
    pm = {"pr_3": ("3 ماهه", 17), "pr_6": ("6 ماهه", 21), "pr_12": ("1 ساله", 34)}
    name, dollar = pm[call.data]; t = get_dollar(); amount = dollar * t
    user_data[call.from_user.id] = {"service": f"✈️ پریمیوم {name}", "plan": name, "dollar": dollar, "amount": amount, "step": "pr_receipt"}
    bot.edit_message_text(
        f"✈️ *پریمیوم {name} — {dollar}$*\n\n"
        "💳 *اطلاعات پرداخت:*\n"
        f"🏦 {CARD_BANK}\n👤 {CARD_OWNER}\n💳 شماره کارت:\n`{CARD_NUM}`\n\n"
        f"💰 مبلغ قابل پرداخت:\n*{amount:,} تومان*\n_(${dollar} × نرخ روز دلار)_\n\n"
        "━━━━━━━━━━━━━━━━━━\n📝 *مرحله ۱ از ۳*\nبعد از واریز، عکس رسید رو بفرست 📸",
        call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "pr_receipt")
def pr_receipt(message):
    user_data[message.from_user.id].update({"receipt": message.photo[-1].file_id, "step": "pr_tgid"})
    bot.send_message(message.chat.id, "📝 *مرحله ۲ از ۳*\nآیدی تلگرامی که میخوای پریمیوم روش فعال بشه:\n_مثال: @username_", parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "pr_tgid")
def pr_tgid(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"tg_id": message.text, "step": "pr_phone"})
    bot.send_message(message.chat.id, "📝 *مرحله ۳ از ۳*\nشماره تلفن اون حساب تلگرام:", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "pr_phone")
def pr_phone(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    d = user_data[message.from_user.id]; d["tg_phone"] = message.text
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id, f"✅ *سفارش #{order['id']} ثبت شد!*\n\nبعد از تأیید رسید، پریمیوم فعال میشه.\n⏳ کمتر از ۲ ساعت", parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_action_markup(u.id, order["id"])
    admin_text = (f"🔔 *سفارش #{order['id']} — {d.get('service')}*\n\n👤 {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n━━━━━━━━━━━━━━━\n"
        f"📱 آیدی: {d.get('tg_id')}\n📞 شماره: {d.get('tg_phone')}\n💰 مبلغ: {d.get('amount'):,} تومان\n🕐 {order['time']}")
    notify_admins(admin_text, mk, d["receipt"])
    del user_data[message.from_user.id]

# ==================== فالوور + شماره مجازی ====================
@bot.message_handler(func=lambda m: m.text == "👥 خرید فالوور")
def follower(message):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("🛒 ثبت سفارش فالوور", url=FOLLOWER_LINK))
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n👥 *خرید فالوور اینستاگرام*\n━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *انواع فالوور:*\n• فالوور ایرانی واقعی\n• فالوور خارجی\n• فالوور میکس\n\n"
        "💎 *ویژگی‌ها:*\n• ریزش کمتر از ۵٪\n• شروع سریع\n• قیمت رقابتی\n• پشتیبانی کامل\n\n👇",
        parse_mode="Markdown", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "📱 شماره مجازی")
def number(message):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("📱 ربات خرید شماره مجازی", url=NUMBER_BOT))
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n📱 *خرید شماره مجازی*\n━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *کاربردها:*\n• ساخت اکانت اینستاگرام\n• ساخت اکانت تلگرام\n"
        "• دریافت OTP\n• ثبت‌نام سایت‌های خارجی\n• تأیید هویت\n\n"
        "🌍 شماره‌های کشورهای مختلف موجوده\n\n👇",
        parse_mode="Markdown", reply_markup=mk)

# ==================== امنیت پیج ====================
@bot.message_handler(func=lambda m: m.text == "🛡️ امنیت پیج")
def sec_start(message):
    user_data[message.from_user.id] = {"service": "🛡️ امنیت پیج", "step": "sec_id"}
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n🛡️ *امنیت پیج اینستاگرام*\n━━━━━━━━━━━━━━━━━━\n\n"
        "🔒 *خدمات امنیتی ما:*\n• بررسی کامل سطح امنیت\n• هک‌پروف کردن اکانت\n"
        "• فعال‌سازی تأیید دو مرحله‌ای\n• بررسی و قطع دسترسی‌های مشکوک\n"
        "• آموزش جلوگیری از هک\n\n"
        "📝 *مرحله ۱ از ۳*\nآیدی پیجت رو بفرست:",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "sec_id")
def sec_id(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"ig_id": message.text, "step": "sec_followers"})
    bot.send_message(message.chat.id, "📝 *مرحله ۲ از ۳*\nتعداد فالوور پیجت؟", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "sec_followers")
def sec_followers(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"followers": message.text, "step": "sec_topic"})
    bot.send_message(message.chat.id, "📝 *مرحله ۳ از ۳*\nموضوع پیجت؟", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "sec_topic")
def sec_topic(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    d = user_data[message.from_user.id]; d["topic"] = message.text
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id, f"✅ *سفارش #{order['id']} ثبت شد!*\n\nتیم ما بررسی می‌کنه و هزینه رو اعلام می‌کنه.\n⏳ کمتر از ۲۴ ساعت", parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_action_markup(u.id, order["id"])
    admin_text = (f"🔔 *سفارش #{order['id']} — امنیت پیج*\n\n👤 {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n━━━━━━━━━━━━━━━\n"
        f"📸 پیج: {d.get('ig_id')}\n👥 فالوور: {d.get('followers')}\n📌 موضوع: {d.get('topic')}\n🕐 {order['time']}")
    notify_admins(admin_text, mk)
    del user_data[message.from_user.id]

# ==================== ادیت و طراحی ====================
@bot.message_handler(func=lambda m: m.text == "🎨 ادیت و طراحی")
def des_start(message):
    user_data[message.from_user.id] = {"service": "🎨 ادیت و طراحی", "step": "des_topic"}
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n🎨 *ادیت و طراحی محتوا*\n━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *خدمات ما:*\n• طراحی پست و استوری\n• ادیت ویدیو و ریلز\n"
        "• طراحی بنر و پوستر\n• ساخت تیزر تبلیغاتی\n• طراحی لوگو و برندینگ\n"
        "• طراحی هایلایت\n\n📝 *مرحله ۱ از ۳*\nموضوع محتوای مورد نظرت رو بنویس:",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "des_topic")
def des_topic(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"topic": message.text, "step": "des_type"})
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=3)
    mk.add("🖼️ پست/استوری","🎬 ویدیو/ریلز","🖌️ بنر","📋 پوستر","📺 تیزر","🎯 لوگو","🔙 بازگشت به منو")
    bot.send_message(message.chat.id, "📝 *مرحله ۲ از ۳*\nنوع محتوا:", parse_mode="Markdown", reply_markup=mk)

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "des_type")
def des_type(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"content_type": message.text, "step": "des_desc"})
    bot.send_message(message.chat.id, "📝 *مرحله ۳ از ۳*\nتوضیح کامل:\n\n• رنگ و استایل\n• متن مورد نظر\n• ابعاد یا فرمت خاص\n• هر جزئیاتی", parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "des_desc")
def des_desc(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    d = user_data[message.from_user.id]; d["desc"] = message.text
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id,
        f"━━━━━━━━━━━━━━━━━━\n📋 *خلاصه سفارش #{order['id']}*\n━━━━━━━━━━━━━━━━━━\n\n"
        f"📌 موضوع: {d.get('topic')}\n🎯 نوع: {d.get('content_type')}\n📝 توضیحات: {d.get('desc')}\n\n"
        f"━━━━━━━━━━━━━━━━━━\nاین لیست رو به {DESIGN_ADMIN} ارسال کن تا تیم ادیت قیمت رو اعلام کنه.",
        parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_action_markup(u.id, order["id"])
    admin_text = (f"🔔 *سفارش #{order['id']} — ادیت و طراحی*\n\n👤 {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n━━━━━━━━━━━━━━━\n"
        f"📌 موضوع: {d.get('topic')}\n🎯 نوع: {d.get('content_type')}\n📝 توضیحات: {d.get('desc')}\n🕐 {order['time']}")
    notify_admins(admin_text, mk)
    del user_data[message.from_user.id]

# ==================== ایده محتوایی ====================
@bot.message_handler(func=lambda m: m.text == "💡 ایده محتوایی")
def idea_start(message):
    user_data[message.from_user.id] = {"step": "idea_topic"}
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n💡 *ایده‌پردازی محتوا (رایگان)*\n━━━━━━━━━━━━━━━━━━\n\n"
        "موضوع پیج یا پستت رو بنویس تا ایده‌های محتوایی بهت بدیم 👇\n\n"
        "_مثال: فروش لباس، آموزش آشپزی، فیتنس_",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "idea_topic")
def idea_generate(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    topic = message.text
    ideas = (
        f"💡 *ایده‌های محتوایی برای «{topic}»*\n\n"
        "📸 *پست:*\n"
        f"• قبل و بعد مرتبط با {topic}\n"
        f"• پشت‌صحنه کار در {topic}\n"
        f"• نکات طلایی درباره {topic}\n"
        f"• معرفی محصول/خدمت با استوری‌تلینگ\n\n"
        "🎬 *ریلز:*\n"
        f"• یه روز کاری در {topic} (time-lapse)\n"
        f"• ۵ اشتباه رایج در {topic}\n"
        f"• چالش مرتبط با {topic}\n\n"
        "📊 *استوری:*\n"
        "• پرسش و پاسخ با مخاطبان\n"
        "• نظرسنجی\n"
        "• اعلام تخفیف یا آفر ویژه\n\n"
        "📅 *تقویم محتوایی:*\n"
        "• دوشنبه: آموزشی\n• سه‌شنبه: سرگرمی\n"
        "• پنجشنبه: معرفی محصول\n• جمعه: انگیزشی\n\n"
        "💬 *هشتگ‌های پیشنهادی را از تیم ما بخواه!*"
    )
    bot.send_message(message.chat.id, ideas, parse_mode="Markdown")
    del user_data[message.from_user.id]
    main_menu(message.chat.id)

# ==================== قیمت دلار و طلا ====================
@bot.message_handler(func=lambda m: m.text == "💰 قیمت دلار و طلا")
def prices(message):
    bot.send_message(message.chat.id, "⏳ در حال دریافت قیمت‌های لحظه‌ای...")
    try:
        usd = get_dollar()
        gold = get_gold()
        gold_text = f"{gold:,} تومان" if gold else "در دسترس نیست"
        gold_gram = int(gold / 31.1) if gold else None
        gold_gram_text = f"{gold_gram:,} تومان" if gold_gram else "---"
        bot.send_message(message.chat.id,
            "━━━━━━━━━━━━━━━━━━\n💰 *قیمت‌های لحظه‌ای*\n━━━━━━━━━━━━━━━━━━\n\n"
            f"💵 *دلار آمریکا:*\n`{usd:,}` تومان\n\n"
            f"🥇 *طلا (هر اونس):*\n`{gold_text}`\n\n"
            f"🥇 *طلا (هر گرم):*\n`{gold_gram_text}`\n\n"
            f"🕐 آخرین بروزرسانی: {datetime.now().strftime('%H:%M')}",
            parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ خطا در دریافت قیمت‌ها. لطفاً دوباره امتحان کن.")

# ==================== کانال و پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == "📢 کانال ما")
def channel(message):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("📢 کانال رسمی ترویده", url=f"https://t.me/{CHANNEL.replace('@','')}"))
    bot.send_message(message.chat.id,
        "📢 *کانال رسمی ترویده*\n\nآخرین اخبار، تخفیف‌ها و نمونه کارها رو ببین 👇",
        parse_mode="Markdown", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support(message):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("💬 تماس مستقیم", url="https://t.me/tarvideh"))
    bot.send_message(message.chat.id,
        "━━━━━━━━━━━━━━━━━━\n📞 *پشتیبانی ترویده*\n━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 تلگرام: @tarvideh\n📢 کانال: {CHANNEL}\n🌐 سایت: tarvideh.com\n\n⏰ پاسخگویی: ۲۴/۷\n\n👇",
        parse_mode="Markdown", reply_markup=mk)

# ==================== پاسخ ادمین ====================
@bot.callback_query_handler(func=lambda c: c.data.startswith("reply_") or c.data.startswith("reject_"))
def admin_reply_cb(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ دسترسی ندارید!"); return
    parts = call.data.split("_"); action = parts[0]; target = int(parts[1])
    if action == "reply":
        user_data[f"admin_reply_{call.from_user.id}"] = target
        bot.send_message(call.message.chat.id, f"✏️ پیامت رو برای کاربر `{target}` بنویس:", parse_mode="Markdown")
        bot.answer_callback_query(call.id)
    elif action == "reject":
        try:
            bot.send_message(target,
                "━━━━━━━━━━━━━━━━━━\n❌ *سفارش شما رد شد*\n━━━━━━━━━━━━━━━━━━\n\n"
                "متأسفانه سفارش شما قابل پردازش نیست.\nبرای اطلاعات بیشتر: @tarvideh",
                parse_mode="Markdown")
        except: pass
        bot.answer_callback_query(call.id, "❌ رد شد.")

@bot.message_handler(func=lambda m: f"admin_reply_{m.from_user.id}" in user_data)
def send_reply(message):
    target = user_data[f"admin_reply_{message.from_user.id}"]
    try:
        bot.send_message(target,
            "━━━━━━━━━━━━━━━━━━\n📩 *پیام از تیم ترویده*\n━━━━━━━━━━━━━━━━━━\n\n"
            f"{message.text}", parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ پیام ارسال شد!")
    except:
        bot.send_message(message.chat.id, "❌ خطا در ارسال!")
    del user_data[f"admin_reply_{message.from_user.id}"]

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "broadcast")
def do_broadcast(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    sent = 0
    for uid in list(set([o["user_id"] for o in orders_db])):
        try:
            bot.send_message(uid, f"📢 *پیام از ترویده:*\n\n{message.text}", parse_mode="Markdown")
            sent += 1
        except: pass
    bot.send_message(message.chat.id, f"✅ پیام به {sent} کاربر ارسال شد.")
    del user_data[message.from_user.id]
    main_menu(message.chat.id)

print("✅ ربات ترویده آماده‌ست...")
bot.infinity_polling()
