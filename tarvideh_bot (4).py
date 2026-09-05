import telebot
from telebot import types
from datetime import datetime
import requests

BOT_TOKEN = "8811093114:AAFBtc-JOkFMEvdgMOgCklGxuPNUXnd6YDM"
ADMINS = [634374331]
CHANNEL = "@tarvideh1"
CARD_NUM = "6104-3387-7176-8823"
CARD_OWNER = "شایان ترویده"
CARD_BANK = "بانک ملت"
DESIGN_ADMIN = "@Tarvideh_Edit"
NUMBER_BOT = "https://t.me/tarvidehnumber_bot"
FOLLOWER_LINK = "https://tarvideh.com/#add_orderbox"

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}
orders_db = []

STATUS = {
    "pending":    "⏳ در انتظار بررسی",
    "reviewing":  "🔍 در حال بررسی",
    "processing": "⚙️ در حال انجام",
    "done":       "✅ تکمیل شده",
    "cancelled":  "❌ لغو شده"
}

def is_admin(uid): return uid in ADMINS

def add_order(user, service, data):
    o = {
        "id": len(orders_db) + 1,
        "user_id": user.id,
        "user_name": f"{user.first_name} {user.last_name or ''}".strip(),
        "username": user.username or "ندارد",
        "service": service,
        "data": data,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "pending"
    }
    orders_db.append(o)
    return o

def notify_admins(text, markup=None, photo=None):
    for aid in ADMINS:
        try:
            if photo:
                bot.send_photo(aid, photo, caption=text, parse_mode="Markdown", reply_markup=markup)
            else:
                bot.send_message(aid, text, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            print(f"Admin error {aid}: {e}")

def back_btn():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add(types.KeyboardButton("🔙 بازگشت به منو"))
    return m

def order_markup(uid, oid):
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("💬 پاسخ به کاربر", callback_data=f"reply_{uid}"),
        types.InlineKeyboardButton("🔍 در بررسی", callback_data=f"status_{oid}_reviewing"),
        types.InlineKeyboardButton("⚙️ در حال انجام", callback_data=f"status_{oid}_processing"),
        types.InlineKeyboardButton("✅ تکمیل شد", callback_data=f"status_{oid}_done"),
        types.InlineKeyboardButton("❌ لغو", callback_data=f"status_{oid}_cancelled"),
    )
    return m

def divider(): return "━━━━━━━━━━━━━━━━━━━━"

# ==================== منو اصلی ====================
def main_menu(chat_id, name=""):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        types.KeyboardButton("🔄 بازگردانی پیج دیسیبل"),
        types.KeyboardButton("🚫 رفع محدودیت"),
        types.KeyboardButton("🗑 حذف پیج جعلی/آزاردهنده"),
        types.KeyboardButton("✈️ پریمیوم تلگرام"),
        types.KeyboardButton("👥 خرید فالوور"),
        types.KeyboardButton("📱 شماره مجازی"),
        types.KeyboardButton("🛡 امنیت پیج"),
        types.KeyboardButton("🎨 ادیت و طراحی"),
        types.KeyboardButton("💡 ایده محتوایی"),
        types.KeyboardButton("📢 کانال ما"),
        types.KeyboardButton("📞 پشتیبانی")
    )
    g = f"👋 سلام *{name}* عزیز!\n\n" if name else ""
    bot.send_message(chat_id,
f"""{g}{divider()}
🏆 *ربات رسمی ترویده*
{divider()}

🌟 *خدمات تخصصی ما:*

🔄 بازگردانی پیج دیسیبل اینستاگرام
🚫 رفع محدودیت و بلاک اکشن
🗑 حذف پیج‌های جعلی و آزاردهنده
🛡 امنیت و هک‌پروف کردن پیج
✈️ پریمیوم تلگرام با قیمت ویژه
📱 خرید شماره مجازی
👥 فالوور واقعی اینستاگرام
🎨 ادیت و طراحی محتوای حرفه‌ای
💡 ایده‌پردازی محتوا رایگان

{divider()}
👇 *خدمت مورد نظرت رو انتخاب کن:*""",
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
f"""{divider()}
🔐 *پنل مدیریت ترویده*
{divider()}

👤 *ادمین:* {message.from_user.first_name}
🕐 *زمان:* {datetime.now().strftime('%Y-%m-%d | %H:%M')}

📌 از منوی زیر گزینه مورد نظر رو انتخاب کن:""",
        parse_mode="Markdown", reply_markup=m)

def show_orders(chat_id, status_key=None):
    filtered = [o for o in orders_db if o["status"] == status_key] if status_key else orders_db[-20:]
    title = STATUS.get(status_key, "همه سفارشات") if status_key else "📋 همه سفارشات"
    if not filtered:
        bot.send_message(chat_id, f"📭 هیچ سفارشی در وضعیت *{title}* وجود نداره.", parse_mode="Markdown")
        return
    bot.send_message(chat_id, f"📋 *{title}* — {len(filtered)} سفارش", parse_mode="Markdown")
    for o in filtered[-10:]:
        mk = order_markup(o["user_id"], o["id"])
        bot.send_message(chat_id,
f"""{divider()}
🔢 *سفارش شماره #{o['id']}*
{divider()}

🛒 *سرویس:* {o['service']}
👤 *نام:* {o['user_name']}
🆔 *یوزرنیم:* @{o['username']}
📱 *آیدی:* `{o['user_id']}`
📊 *وضعیت:* {STATUS.get(o['status'])}
🕐 *زمان ثبت:* {o['time']}""",
            parse_mode="Markdown", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "📋 همه سفارشات" and is_admin(m.from_user.id))
def all_orders(msg): show_orders(msg.chat.id)

@bot.message_handler(func=lambda m: m.text == "⏳ در انتظار بررسی" and is_admin(m.from_user.id))
def pending_orders(msg): show_orders(msg.chat.id, "pending")

@bot.message_handler(func=lambda m: m.text == "🔍 در حال بررسی" and is_admin(m.from_user.id))
def reviewing_orders(msg): show_orders(msg.chat.id, "reviewing")

@bot.message_handler(func=lambda m: m.text == "⚙️ در حال انجام" and is_admin(m.from_user.id))
def processing_orders(msg): show_orders(msg.chat.id, "processing")

@bot.message_handler(func=lambda m: m.text == "✅ تکمیل‌شده‌ها" and is_admin(m.from_user.id))
def done_orders(msg): show_orders(msg.chat.id, "done")

@bot.message_handler(func=lambda m: m.text == "❌ لغوشده‌ها" and is_admin(m.from_user.id))
def cancelled_orders(msg): show_orders(msg.chat.id, "cancelled")

@bot.message_handler(func=lambda m: m.text == "📊 آمار کلی" and is_admin(m.from_user.id))
def stats(message):
    total = len(orders_db)
    bs = {k: 0 for k in STATUS}
    bsvc = {}
    for o in orders_db:
        bs[o["status"]] = bs.get(o["status"], 0) + 1
        bsvc[o["service"]] = bsvc.get(o["service"], 0) + 1
    text = f"""{divider()}
📊 *آمار کلی ربات ترویده*
{divider()}

🔢 *کل سفارشات:* {total}

📈 *به تفکیک وضعیت:*\n"""
    for k, v in STATUS.items():
        text += f"  {v}: {bs.get(k, 0)} سفارش\n"
    text += f"\n📈 *به تفکیک سرویس:*\n"
    for s, c in sorted(bsvc.items(), key=lambda x: -x[1]):
        text += f"  • {s}: {c}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👥 مدیریت ادمین‌ها" and is_admin(m.from_user.id))
def manage_admins(message):
    text = f"{divider()}\n👥 *ادمین‌های فعال*\n{divider()}\n\n"
    for i, aid in enumerate(ADMINS, 1):
        text += f"  {i}. `{aid}`\n"
    text += f"\n➕ اضافه کردن:\n`/addadmin [آیدی]`\n\n➖ حذف:\n`/removeadmin [آیدی]`"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    if not is_admin(message.from_user.id): return
    try:
        nid = int(message.text.split()[1])
        if nid not in ADMINS:
            ADMINS.append(nid)
            bot.send_message(message.chat.id, f"✅ ادمین `{nid}` با موفقیت اضافه شد.", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "⚠️ این آیدی قبلاً ادمین بوده.")
    except:
        bot.send_message(message.chat.id, "❌ فرمت اشتباه!\nمثال: `/addadmin 123456789`", parse_mode="Markdown")

@bot.message_handler(commands=['removeadmin'])
def remove_admin(message):
    if not is_admin(message.from_user.id): return
    try:
        rid = int(message.text.split()[1])
        if rid == 634374331:
            bot.send_message(message.chat.id, "❌ ادمین اصلی قابل حذف نیست!"); return
        if rid in ADMINS:
            ADMINS.remove(rid)
            bot.send_message(message.chat.id, f"✅ ادمین `{rid}` حذف شد.", parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ فرمت اشتباه!\nمثال: `/removeadmin 123456789`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📢 پیام همگانی" and is_admin(m.from_user.id))
def broadcast_ask(message):
    user_data[message.from_user.id] = {"step": "broadcast"}
    bot.send_message(message.chat.id, "📢 *پیام همگانی*\n\nمتن پیامت رو بنویس:", parse_mode="Markdown", reply_markup=back_btn())

@bot.callback_query_handler(func=lambda c: c.data.startswith("status_"))
def change_status(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ دسترسی ندارید!"); return
    parts = call.data.split("_")
    oid, ns = int(parts[1]), parts[2]
    for o in orders_db:
        if o["id"] == oid:
            o["status"] = ns
            try:
                bot.send_message(o["user_id"],
f"""{divider()}
📢 *آپدیت وضعیت سفارش*
{divider()}

🔢 *سفارش:* #{oid}
📊 *وضعیت جدید:* {STATUS.get(ns)}

✨ تیم ترویده در حال پیگیری سفارش شماست.
📞 برای پیگیری: @tarvideh""", parse_mode="Markdown")
            except: pass
            bot.answer_callback_query(call.id, f"✅ {STATUS[ns]}")
            return
    bot.answer_callback_query(call.id, "❌ سفارش پیدا نشد.")

# ==================== بازگردانی دیسیبل ====================
@bot.message_handler(func=lambda m: m.text == "🔄 بازگردانی پیج دیسیبل")
def dis_start(message):
    user_data[message.from_user.id] = {"service": "🔄 بازگردانی پیج دیسیبل", "step": "dis_id"}
    bot.send_message(message.chat.id,
f"""{divider()}
🔄 *بازگردانی پیج دیسیبل*
{divider()}

🌟 *خدمات ما شامل:*
• بازگردانی پیج‌های permanently disabled
• بازگردانی پیج‌های هک و دزدیده شده
• بازگردانی پیج‌های دیسیبل به دلیل تخلف
• پیگیری مستمر تا نتیجه نهایی

📊 *نرخ موفقیت:* ۹۸٪
⏰ *زمان تحویل:* ۲۴ تا ۷۲ ساعت
🔒 *تضمین:* بازگشت وجه در صورت عدم موفقیت

{divider()}
📝 *مرحله ۱ از ۷*
🔹 آیدی پیج اینستاگرامت رو بفرست:
_مثال: @username_""",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_id")
def dis_id(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"ig_id": message.text, "step": "dis_email"})
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۲ از ۷*
🔹 ایمیل متصل به پیجت رو بفرست:
_اگه نداری بنویس: ندارم_""", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_email")
def dis_email(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"email": message.text, "step": "dis_pic"})
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۳ از ۷*
🔹 آخرین تصویری که هنگام ورود به پیج دیدی رو بفرست 📸
_اگه نداری بنویس: ندارم_""", parse_mode="Markdown")

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_pic")
def dis_pic_photo(message):
    user_data[message.from_user.id].update({"last_pic": message.photo[-1].file_id, "pic_type": "photo", "step": "dis_topic"})
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۴ از ۷*
🔹 موضوع پیجت چیه؟
_مثال: فروش محصول، آموزش، پزشکی، سرگرمی_""", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_pic")
def dis_pic_text(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"last_pic": message.text, "pic_type": "text", "step": "dis_topic"})
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۴ از ۷*
🔹 موضوع پیجت چیه؟
_مثال: فروش محصول، آموزش، پزشکی، سرگرمی_""", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_topic")
def dis_topic(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"topic": message.text, "step": "dis_type"})
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    mk.add("💼 کاری/تجاری", "👤 شخصی", "🔙 بازگشت به منو")
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۵ از ۷*
🔹 پیجت کاری بوده یا شخصی؟""", parse_mode="Markdown", reply_markup=mk)

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_type")
def dis_type(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"page_type": message.text, "step": "dis_followers"})
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۶ از ۷*
🔹 تعداد تقریبی فالوور پیجت چقدر بود؟""", parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_followers")
def dis_followers(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"followers": message.text, "step": "dis_desc"})
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۷ از ۷*
🔹 توضیح کامل از اتفاقی که افتاده:

لطفاً به این سوالات پاسخ بده:
• چه زمانی دیسیبل شد؟
• چه پیامی نشون میده؟
• قبلاً اخطار گرفتی؟
• دلیل احتمالی از نظر خودت چیه؟""", parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_desc")
def dis_desc(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    d = user_data[message.from_user.id]; d["desc"] = message.text
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id,
f"""{divider()}
✅ *سفارش #{order['id']} با موفقیت ثبت شد!*
{divider()}

📋 *خلاصه سفارش:*
🔹 پیج: {d.get('ig_id')}
🔹 موضوع: {d.get('topic')}
🔹 نوع: {d.get('page_type')}
🔹 فالوور: {d.get('followers')}

⏳ تیم ما در کمتر از *۲۴ ساعت* بررسی می‌کنه و همینجا بهت پاسخ میده.

📢 کانال ما: {CHANNEL}""", parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_markup(u.id, order["id"])
    admin_text = f"""{divider()}
🔔 *سفارش جدید #{order['id']}*
🔄 *بازگردانی پیج دیسیبل*
{divider()}

👤 *کاربر:* {u.first_name} {u.last_name or ''}
🆔 *یوزرنیم:* @{u.username or 'ندارد'}
📱 *آیدی:* `{u.id}`

{divider()}
📋 *اطلاعات پیج:*
📸 آیدی: {d.get('ig_id')}
📧 ایمیل: {d.get('email')}
📌 موضوع: {d.get('topic')}
🏷 نوع: {d.get('page_type')}
👥 فالوور: {d.get('followers')}
📝 توضیحات: {d.get('desc')}
🕐 زمان: {order['time']}

{divider()}
🔗 *فرم‌های پیشنهادی برای رسیدگی:*
• instagram.com/hacked
• instagram.com/hacked/?hl=en
• is.gd/xpHtXL _(فرم متا)_
• facebook.com/help/contact/507270721277573
• help.instagram.com/contact/814820110107093
📧 security@mail.instagram.com"""
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
f"""{divider()}
🚫 *رفع محدودیت پیج اینستاگرام*
{divider()}

🌟 *انواع محدودیت‌هایی که رفع می‌کنیم:*
• 🚷 بلاک اکشن (لایک، کامنت، فالو)
• #️⃣ محدودیت هشتگ
• 💬 محدودیت دایرکت
• 🔴 محدودیت لایو
• 📊 محدودیت تبلیغات
• 🔇 سایر محدودیت‌ها

⏰ *زمان رفع:* ۱۲ تا ۴۸ ساعت

{divider()}
📝 *مرحله ۱ از ۳*
🔹 اسکرین‌شات از *وضعیت حساب* پیجت بفرست 📸

📌 مسیر: *تنظیمات ← حساب ← وضعیت حساب*""",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "lim_pic")
def lim_pic(message):
    user_data[message.from_user.id].update({"screenshot": message.photo[-1].file_id, "step": "lim_id"})
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۲ از ۳*
🔹 آیدی پیجت رو بفرست:""", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "lim_id")
def lim_id(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"ig_id": message.text, "step": "lim_desc"})
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۳ از ۳*
🔹 چه محدودیتی داری و از کی شروع شده؟

_مثال: از ۳ روز پیش نمی‌تونم لایک کنم، پیام خطای action blocked میده_""", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "lim_desc")
def lim_desc(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    d = user_data[message.from_user.id]; d["desc"] = message.text
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id,
f"""{divider()}
✅ *سفارش #{order['id']} ثبت شد!*
{divider()}

⏳ تیم ما بررسی می‌کنه و همینجا پاسخ میده.
🕐 زمان پاسخ: کمتر از *۲۴ ساعت*""", parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_markup(u.id, order["id"])
    admin_text = f"""{divider()}
🔔 *سفارش جدید #{order['id']}*
🚫 *رفع محدودیت پیج*
{divider()}

👤 *کاربر:* {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`

📸 *آیدی پیج:* {d.get('ig_id')}
📝 *محدودیت:* {d.get('desc')}
🕐 *زمان:* {order['time']}

{divider()}
🔗 *فرم‌های پیشنهادی:*
• instagram.com/hacked
• help.instagram.com/contact/372592039493026
• help.instagram.com/contact/512241091300432
• is.gd/xpHtXL _(فرم متا)_"""
    try: notify_admins(admin_text, mk, d["screenshot"])
    except: notify_admins(admin_text, mk)
    del user_data[message.from_user.id]

# ==================== حذف پیج جعلی ====================
@bot.message_handler(func=lambda m: m.text == "🗑 حذف پیج جعلی/آزاردهنده")
def fake_start(message):
    user_data[message.from_user.id] = {"service": "🗑 حذف پیج جعلی/آزاردهنده", "step": "fake_reason"}
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=1)
    mk.add("👤 جعل هویت (پیج فیک از من)", "😡 آزار و اذیت / تهدید", "📸 سوءاستفاده از تصاویرم", "🔙 بازگشت به منو")
    bot.send_message(message.chat.id,
f"""{divider()}
🗑 *حذف پیج جعلی / آزاردهنده*
{divider()}

🌟 *موارد قابل پیگیری:*
• 👤 پیج‌های جعل هویت و فیک
• 😡 پیج‌های آزاردهنده و تهدیدآمیز
• 📸 سوءاستفاده از تصاویر شخصی
• ™️ نقض علامت تجاری و برند

✅ ما با استفاده از فرم‌های رسمی اینستاگرام پیگیری می‌کنیم.

{divider()}
📝 *مرحله ۱ از ۵*
🔹 دلیل درخواست حذف رو انتخاب کن:""",
        parse_mode="Markdown", reply_markup=mk)

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "fake_reason")
def fake_reason(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"reason": message.text, "step": "fake_target"})
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۲ از ۵*
🔹 آیدی پیجی که میخوای حذف بشه:""", parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "fake_target")
def fake_target(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"target_id": message.text, "step": "fake_original"})
    reason = user_data[message.from_user.id].get("reason", "")
    if "جعل هویت" in reason:
        bot.send_message(message.chat.id,
f"""📝 *مرحله ۳ از ۵*
🔹 آیدی پیج اصلی خودت رو بفرست _(که جعل شده)_:""", parse_mode="Markdown")
    else:
        user_data[message.from_user.id]["original_id"] = "---"
        user_data[message.from_user.id]["step"] = "fake_desc"
        bot.send_message(message.chat.id,
f"""📝 *مرحله ۳ از ۵*
🔹 توضیح کامل بده چه آزار و اذیتی صورت گرفته:""", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "fake_original")
def fake_original(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"original_id": message.text, "step": "fake_desc"})
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۴ از ۵*
🔹 توضیح کامل بده:""", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "fake_desc")
def fake_desc(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"desc": message.text, "step": "fake_proof"})
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۵ از ۵*
🔹 برای تأیید هویتت یکی از موارد زیر رو ارسال کن:

📌 *کارت ملی یا پاسپورت* _(با عکس)_
📌 یا *اسکرین‌شات پیج اصلی خودت*

⚠️ این اطلاعات فقط برای تأیید هویت استفاده میشه و محرمانه می‌مونه.""",
        parse_mode="Markdown")

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "fake_proof")
def fake_proof(message):
    d = user_data[message.from_user.id]; d["proof"] = message.photo[-1].file_id
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id,
f"""{divider()}
✅ *سفارش #{order['id']} ثبت شد!*
{divider()}

📋 تیم ما بررسی می‌کنه و هزینه و زمان مورد نیاز رو اعلام می‌کنه.
⏳ زمان پاسخ: کمتر از *۲۴ ساعت*""", parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_markup(u.id, order["id"])
    admin_text = f"""{divider()}
🔔 *سفارش جدید #{order['id']}*
🗑 *حذف پیج جعلی/آزاردهنده*
{divider()}

👤 *کاربر:* {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`

⚠️ *دلیل:* {d.get('reason')}
🎯 *پیج هدف:* {d.get('target_id')}
✅ *پیج اصلی:* {d.get('original_id')}
📝 *توضیحات:* {d.get('desc')}
🕐 *زمان:* {order['time']}

{divider()}
🔗 *فرم‌های پیشنهادی:*
• help.instagram.com/contact/636276399721841 _(جعل هویت)_
• help.instagram.com/547601325292351 _(آزار)_
• help.instagram.com/contact/372592039493026 _(تخلف)_
• help.instagram.com/contact/230197320740525 _(علامت تجاری)_"""
    notify_admins(admin_text, mk, d["proof"])
    del user_data[message.from_user.id]

# ==================== پریمیوم تلگرام ====================
@bot.message_handler(func=lambda m: m.text == "✈️ پریمیوم تلگرام")
def premium_start(message):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("3️⃣  پریمیوم ۳ ماهه  —  17$", callback_data="pr_3"),
        types.InlineKeyboardButton("6️⃣  پریمیوم ۶ ماهه  —  21$", callback_data="pr_6"),
        types.InlineKeyboardButton("1️⃣  پریمیوم ۱ ساله   —  34$", callback_data="pr_12"),
        types.InlineKeyboardButton("🔙 بازگشت به منو", callback_data="pr_back")
    )
    bot.send_message(message.chat.id,
f"""{divider()}
✈️ *پریمیوم تلگرام*
{divider()}

💎 *مزایای اشتراک پریمیوم:*
• 📁 آپلود فایل تا *۴ گیگابایت*
• 🎭 استیکر و ری‌اکشن انحصاری
• 🎬 پروفایل ویدیویی انیمیشن‌دار
• ⚡ سرعت دانلود ۴ برابر بیشتر
• 🚫 بدون تبلیغات
• 👥 مدیریت تا ۱۰ اکانت همزمان
• ✏️ ویرایش پیام‌ها بدون محدودیت

{divider()}
💰 *قیمت‌ها به دلار:*
_(برای تبدیل به تومان، نرخ روز دلار رو ضربدر کنید)_

👇 *پلن مورد نظرت رو انتخاب کن:*""",
        parse_mode="Markdown", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pr_"))
def premium_plan(call):
    if call.data == "pr_back":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        main_menu(call.message.chat.id); return
    pm = {"pr_3": ("۳ ماهه", 17), "pr_6": ("۶ ماهه", 21), "pr_12": ("۱ ساله", 34)}
    name, dollar = pm[call.data]
    user_data[call.from_user.id] = {"service": f"✈️ پریمیوم {name}", "plan": name, "dollar": dollar, "step": "pr_receipt"}
    bot.edit_message_text(
f"""{divider()}
✈️ *پریمیوم تلگرام {name}*
{divider()}

💰 *مبلغ:* {dollar}$
_(نرخ روز دلار × {dollar} = مبلغ به تومان)_

{divider()}
💳 *اطلاعات پرداخت:*

🏦 بانک: *{CARD_BANK}*
👤 به نام: *{CARD_OWNER}*
💳 شماره کارت:
`{CARD_NUM}`

{divider()}
📝 *مرحله ۱ از ۳*
🔹 بعد از واریز، عکس *رسید پرداخت* رو بفرست 📸""",
        call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "pr_receipt")
def pr_receipt(message):
    user_data[message.from_user.id].update({"receipt": message.photo[-1].file_id, "step": "pr_tgid"})
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۲ از ۳*
🔹 آیدی تلگرامی که میخوای پریمیوم روش فعال بشه:
_مثال: @username_""", parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "pr_tgid")
def pr_tgid(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"tg_id": message.text, "step": "pr_phone"})
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۳ از ۳*
🔹 شماره تلفن اون حساب تلگرام رو بفرست:
_مثال: 09123456789_""", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "pr_phone")
def pr_phone(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    d = user_data[message.from_user.id]; d["tg_phone"] = message.text
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id,
f"""{divider()}
✅ *سفارش #{order['id']} ثبت شد!*
{divider()}

⏳ بعد از تأیید رسید، پریمیوم فعال میشه.
🕐 زمان فعال‌سازی: کمتر از *۲ ساعت*""", parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_markup(u.id, order["id"])
    admin_text = f"""{divider()}
🔔 *سفارش جدید #{order['id']}*
✈️ *{d.get('service')}*
{divider()}

👤 *کاربر:* {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`

📱 *آیدی تلگرام:* {d.get('tg_id')}
📞 *شماره:* {d.get('tg_phone')}
💰 *مبلغ:* {d.get('dollar')}$
🕐 *زمان:* {order['time']}"""
    notify_admins(admin_text, mk, d["receipt"])
    del user_data[message.from_user.id]

# ==================== فالوور + شماره ====================
@bot.message_handler(func=lambda m: m.text == "👥 خرید فالوور")
def follower(message):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("🛒 ثبت سفارش فالوور در سایت", url=FOLLOWER_LINK))
    bot.send_message(message.chat.id,
f"""{divider()}
👥 *خرید فالوور اینستاگرام*
{divider()}

🌟 *انواع فالوور:*
• 🇮🇷 فالوور ایرانی واقعی
• 🌍 فالوور خارجی
• 🔀 فالوور میکس ایرانی/خارجی

💎 *ویژگی‌ها:*
• ✅ ریزش کمتر از ۵٪
• ⚡ شروع سریع ظرف ۱ ساعت
• 💰 قیمت رقابتی و مناسب
• 🔒 بدون نیاز به پسورد
• 🎯 تضمین کیفیت

👇 *برای مشاهده قیمت‌ها و ثبت سفارش:*""",
        parse_mode="Markdown", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "📱 شماره مجازی")
def number(message):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("📱 ربات خرید شماره مجازی", url=NUMBER_BOT))
    bot.send_message(message.chat.id,
f"""{divider()}
📱 *خرید شماره مجازی*
{divider()}

🌟 *کاربردها:*
• 📸 ساخت اکانت اینستاگرام
• ✈️ ساخت اکانت تلگرام
• 🔐 دریافت کد OTP
• 🌐 ثبت‌نام سایت‌های خارجی
• ✅ تأیید هویت آنلاین

🌍 *کشورهای موجود:*
ایران، آمریکا، انگلیس، روسیه و +۵۰ کشور دیگر

💰 *قیمت‌ها:* بسیار مناسب و رقابتی

👇 *برای خرید به ربات اختصاصی ما مراجعه کن:*""",
        parse_mode="Markdown", reply_markup=mk)

# ==================== امنیت پیج ====================
@bot.message_handler(func=lambda m: m.text == "🛡 امنیت پیج")
def sec_start(message):
    user_data[message.from_user.id] = {"service": "🛡 امنیت پیج", "step": "sec_id"}
    bot.send_message(message.chat.id,
f"""{divider()}
🛡 *امنیت پیج اینستاگرام*
{divider()}

🔒 *خدمات امنیتی ما:*
• 🔍 بررسی کامل سطح امنیت حساب
• 🛡 هک‌پروف کردن اکانت
• 🔑 فعال‌سازی تأیید دو مرحله‌ای
• 🚫 قطع دسترسی‌های مشکوک
• 📱 امنیت دستگاه‌های متصل
• 📚 آموزش پیشگیری از هک

{divider()}
📝 *مرحله ۱ از ۳*
🔹 آیدی پیجت رو بفرست:""",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "sec_id")
def sec_id(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"ig_id": message.text, "step": "sec_followers"})
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۲ از ۳*
🔹 تعداد فالوور پیجت چقدره؟""", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "sec_followers")
def sec_followers(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"followers": message.text, "step": "sec_topic"})
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۳ از ۳*
🔹 موضوع پیجت چیه؟
_مثال: فروش محصول، آموزش، ورزشی_""", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "sec_topic")
def sec_topic(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    d = user_data[message.from_user.id]; d["topic"] = message.text
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id,
f"""{divider()}
✅ *سفارش #{order['id']} ثبت شد!*
{divider()}

📋 تیم ما بررسی می‌کنه و هزینه و شرایط همکاری رو اعلام می‌کنه.
⏳ زمان پاسخ: کمتر از *۲۴ ساعت*""", parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_markup(u.id, order["id"])
    admin_text = f"""{divider()}
🔔 *سفارش جدید #{order['id']}*
🛡 *امنیت پیج*
{divider()}

👤 *کاربر:* {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`

📸 *پیج:* {d.get('ig_id')}
👥 *فالوور:* {d.get('followers')}
📌 *موضوع:* {d.get('topic')}
🕐 *زمان:* {order['time']}"""
    notify_admins(admin_text, mk)
    del user_data[message.from_user.id]

# ==================== ادیت و طراحی ====================
@bot.message_handler(func=lambda m: m.text == "🎨 ادیت و طراحی")
def des_start(message):
    user_data[message.from_user.id] = {"service": "🎨 ادیت و طراحی", "step": "des_topic"}
    bot.send_message(message.chat.id,
f"""{divider()}
🎨 *ادیت و طراحی محتوای حرفه‌ای*
{divider()}

🌟 *خدمات تیم طراحی ما:*
• 🖼 طراحی پست و استوری اینستاگرام
• 🎬 ادیت ویدیو و ریلز حرفه‌ای
• 🖌 طراحی بنر تبلیغاتی
• 📋 طراحی پوستر و فلایر
• 📺 ساخت تیزر تبلیغاتی
• 🎯 طراحی لوگو و برندینگ
• ✨ طراحی هایلایت و آیکون

{divider()}
📝 *مرحله ۱ از ۳*
🔹 موضوع محتوای مورد نظرت رو بنویس:""",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "des_topic")
def des_topic(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"topic": message.text, "step": "des_type"})
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=3)
    mk.add("🖼 پست/استوری","🎬 ویدیو/ریلز","🖌 بنر","📋 پوستر","📺 تیزر","🎯 لوگو","🔙 بازگشت به منو")
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۲ از ۳*
🔹 نوع محتوا رو انتخاب کن:""", parse_mode="Markdown", reply_markup=mk)

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "des_type")
def des_type(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"content_type": message.text, "step": "des_desc"})
    bot.send_message(message.chat.id,
f"""📝 *مرحله ۳ از ۳*
🔹 توضیح کامل بده:

• 🎨 رنگ و استایل مورد نظر
• ✍️ متن و محتوای دلخواه
• 📐 ابعاد یا فرمت خاص
• 💡 هر ایده یا نمونه‌ای که داری""", parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "des_desc")
def des_desc(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    d = user_data[message.from_user.id]; d["desc"] = message.text
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id,
f"""{divider()}
📋 *خلاصه سفارش #{order['id']}*
{divider()}

📌 *موضوع:* {d.get('topic')}
🎯 *نوع:* {d.get('content_type')}
📝 *توضیحات:* {d.get('desc')}

{divider()}
✅ این لیست رو به {DESIGN_ADMIN} ارسال کن تا تیم ادیت قیمت و شرایط رو اعلام کنه.""",
        parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_markup(u.id, order["id"])
    admin_text = f"""{divider()}
🔔 *سفارش جدید #{order['id']}*
🎨 *ادیت و طراحی*
{divider()}

👤 *کاربر:* {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`

📌 *موضوع:* {d.get('topic')}
🎯 *نوع:* {d.get('content_type')}
📝 *توضیحات:* {d.get('desc')}
🕐 *زمان:* {order['time']}"""
    notify_admins(admin_text, mk)
    del user_data[message.from_user.id]

# ==================== ایده محتوایی ====================
@bot.message_handler(func=lambda m: m.text == "💡 ایده محتوایی")
def idea_start(message):
    user_data[message.from_user.id] = {"step": "idea_topic"}
    bot.send_message(message.chat.id,
f"""{divider()}
💡 *ایده‌پردازی محتوا — رایگان!*
{divider()}

✨ موضوع پیج یا پستت رو بنویس تا ایده‌های محتوایی حرفه‌ای بهت بدیم 🎯

_مثال: فروش لباس، آموزش آشپزی، فیتنس و بدنسازی_""",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "idea_topic")
def idea_generate(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    t = message.text
    bot.send_message(message.chat.id,
f"""{divider()}
💡 *ایده‌های محتوایی برای «{t}»*
{divider()}

🖼 *ایده پست:*
• قبل و بعد مرتبط با {t}
• پشت‌صحنه و فرآیند کار
• نکات طلایی و ترفندهای کاربردی
• معرفی محصول/خدمت با استوری‌تلینگ
• سوال از مخاطبان

🎬 *ایده ریلز:*
• یه روز کاری در {t} (time-lapse)
• ۵ اشتباه رایج در {t}
• چالش مرتبط با {t}
• آموزش سریع ۳۰ ثانیه‌ای

📊 *ایده استوری:*
• پرسش و پاسخ تعاملی
• نظرسنجی و رای‌گیری
• اعلام تخفیف و آفر ویژه
• پشت‌صحنه لحظه‌ای

📅 *تقویم محتوایی پیشنهادی:*
• 🔵 شنبه: محتوای آموزشی
• 🟢 دوشنبه: سرگرمی و ترند
• 🟡 سه‌شنبه: معرفی محصول/خدمت
• 🔴 پنجشنبه: تعاملی و نظرسنجی
• 🟣 جمعه: انگیزشی و الهام‌بخش

{divider()}
💬 *برای طراحی و تولید محتوا:*
گزینه 🎨 *ادیت و طراحی* رو از منو انتخاب کن!""",
        parse_mode="Markdown")
    del user_data[message.from_user.id]
    main_menu(message.chat.id)

# ==================== کانال و پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == "📢 کانال ما")
def channel(message):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("📢 ورود به کانال رسمی ترویده", url=f"https://t.me/{CHANNEL.replace('@','')}"))
    bot.send_message(message.chat.id,
f"""{divider()}
📢 *کانال رسمی ترویده*
{divider()}

🌟 در کانال ما چی پیدا می‌کنی؟

• 🏆 نمونه کارهای اخیر
• 🎁 تخفیف‌های ویژه
• 📰 آخرین اخبار اینستاگرام
• 💡 نکات و ترفندهای کاربردی
• 📊 آمار و اطلاعات مفید

👇 *همین الان عضو شو:*""",
        parse_mode="Markdown", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support(message):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("💬 تماس مستقیم با پشتیبانی", url="https://t.me/tarvideh"))
    bot.send_message(message.chat.id,
f"""{divider()}
📞 *پشتیبانی ۲۴ ساعته ترویده*
{divider()}

👋 *تیم پشتیبانی ما آماده کمکه!*

📱 *تلگرام:* @tarvideh
📢 *کانال:* {CHANNEL}
🌐 *سایت:* tarvideh.com

⏰ *ساعات پاسخگویی:* ۲۴ ساعته / ۷ روز هفته
⚡ *میانگین زمان پاسخ:* کمتر از ۳۰ دقیقه

{divider()}
👇 *برای تماس مستقیم:*""",
        parse_mode="Markdown", reply_markup=mk)

# ==================== پاسخ ادمین ====================
@bot.callback_query_handler(func=lambda c: c.data.startswith("reply_") or c.data.startswith("reject_"))
def admin_reply_cb(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ دسترسی ندارید!"); return
    parts = call.data.split("_"); action = parts[0]; target = int(parts[1])
    if action == "reply":
        user_data[f"admin_reply_{call.from_user.id}"] = target
        bot.send_message(call.message.chat.id,
            f"✏️ پیامت رو برای کاربر `{target}` بنویس:\n_پیام بعدی شما ارسال خواهد شد_",
            parse_mode="Markdown")
        bot.answer_callback_query(call.id, "✍️ منتظر پیامت هستم")
    elif action == "reject":
        try:
            bot.send_message(target,
f"""{divider()}
❌ *سفارش شما رد شد*
{divider()}

متأسفانه در این مرحله امکان پردازش سفارش شما وجود ندارد.

📞 برای اطلاعات بیشتر با پشتیبانی تماس بگیرید:
@tarvideh""", parse_mode="Markdown")
        except: pass
        bot.answer_callback_query(call.id, "❌ سفارش رد شد.")

@bot.message_handler(func=lambda m: f"admin_reply_{m.from_user.id}" in user_data)
def send_reply(message):
    target = user_data[f"admin_reply_{message.from_user.id}"]
    try:
        bot.send_message(target,
f"""{divider()}
📩 *پیام از تیم ترویده*
{divider()}

{message.text}

{divider()}
📞 برای پیگیری بیشتر: @tarvideh""", parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ پیام با موفقیت ارسال شد!")
    except:
        bot.send_message(message.chat.id, "❌ خطا در ارسال پیام!")
    del user_data[f"admin_reply_{message.from_user.id}"]

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "broadcast")
def do_broadcast(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    sent = 0
    for uid in list(set([o["user_id"] for o in orders_db])):
        try:
            bot.send_message(uid,
f"""{divider()}
📢 *پیام رسمی از ترویده*
{divider()}

{message.text}

{divider()}
📢 {CHANNEL}""", parse_mode="Markdown")
            sent += 1
        except: pass
    bot.send_message(message.chat.id, f"✅ پیام با موفقیت به *{sent}* کاربر ارسال شد.", parse_mode="Markdown")
    del user_data[message.from_user.id]
    main_menu(message.chat.id)

print("✅ ربات ترویده آماده‌ست و در حال اجراست...")
bot.infinity_polling()
