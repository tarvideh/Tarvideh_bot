import telebot
from telebot import types
from datetime import datetime
import requests
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from html import escape

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

# ==================== تنظیمات ایمیل ====================
EMAIL_SENDER = "Tarvideh8@gmail.com"
EMAIL_PASSWORD = "obhh jwnd xfwz rhxp"  # ← کد App Password رو اینجا بذار

# ==================== تنظیمات هوش مصنوعی ====================
GROQ_API_KEY = "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"  # ← کلید API گروک رو اینجا بذار
# ============================================================

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}
DB_FILE = "tarvideh_orders.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, user_name TEXT, username TEXT,
        service TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL,
        status TEXT NOT NULL, history TEXT NOT NULL, admin_note TEXT DEFAULT ''
    )""")
    conn.commit(); conn.close()

def load_orders():
    import json
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM orders ORDER BY id").fetchall(); conn.close()
    result=[]
    for r in rows:
        result.append({"id":r["id"],"user_id":r["user_id"],"user_name":r["user_name"],"username":r["username"],
                       "service":r["service"],"data":json.loads(r["data"]),"time":r["created_at"],
                       "status":r["status"],"history":json.loads(r["history"]),"admin_note":r["admin_note"] or ""})
    return result

def save_order(o):
    import json
    conn=sqlite3.connect(DB_FILE)
    conn.execute("""INSERT OR REPLACE INTO orders
        (id,user_id,user_name,username,service,data,created_at,status,history,admin_note)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (o["id"],o["user_id"],o["user_name"],o["username"],o["service"],json.dumps(o["data"],ensure_ascii=False),
         o["time"],o["status"],json.dumps(o.get("history",[]),ensure_ascii=False),o.get("admin_note", "")))
    conn.commit(); conn.close()

init_db()
orders_db = load_orders()

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
        "id": (max([x["id"] for x in orders_db], default=0) + 1),
        "user_id": user.id,
        "user_name": f"{user.first_name} {user.last_name or ''}".strip(),
        "username": user.username or "ندارد",
        "service": service,
        "data": data,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "pending",
        "history": [{"status": "pending", "admin": None, "time": datetime.now().strftime("%Y-%m-%d %H:%M")}],
        "admin_note": ""
    }
    orders_db.append(o)
    save_order(o)
    return o

def notify_admins(text, markup=None, photo=None):
    """اعلان فوری سفارش جدید به چت ادمین؛ مستقل از بخش سفارشات.
    اول متن کامل ارسال می‌شود تا محدودیت کپشن عکس یا Markdown باعث از دست رفتن سفارش نشود.
    عکس/مدرک بعد از آن جداگانه ارسال می‌شود.
    """
    for aid in ADMINS:
        try:
            # متن سفارش همیشه مستقیم وارد چت ادمین می‌شود.
            # چون متن شامل ورودی کاربر است، بدون parse_mode ارسال می‌کنیم تا Markdown خراب نشود.
            clean_text = str(text).replace("*", "").replace("`", "")
            bot.send_message(aid, clean_text, reply_markup=markup, disable_notification=False)
            if photo:
                try:
                    bot.send_photo(aid, photo, caption=f"📎 مدرک/تصویر سفارش در بالا — سفارش جدید", disable_notification=False)
                except Exception as e:
                    print(f"Admin attachment notify error {aid}: {e}")
        except Exception as e:
            print(f"Admin message notify error {aid}: {e}")

def back_btn():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add(types.KeyboardButton("🔙 بازگشت به منو"))
    return m

def order_action_markup(user_id, order_id):
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("📂 پرونده کامل", callback_data=f"order_{order_id}"),
        types.InlineKeyboardButton("📝 یادداشت ادمین", callback_data=f"note_{order_id}"),
        types.InlineKeyboardButton("💬 پاسخ به کاربر", callback_data=f"reply_{user_id}"),
        types.InlineKeyboardButton("🔍 در بررسی", callback_data=f"status_{order_id}_reviewing"),
        types.InlineKeyboardButton("⚙️ در انجام", callback_data=f"status_{order_id}_processing"),
        types.InlineKeyboardButton("✅ تکمیل شد", callback_data=f"status_{order_id}_done"),
        types.InlineKeyboardButton("❌ لغو", callback_data=f"status_{order_id}_cancelled"),
    )
    return m

SEP = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"

# ==================== ایمیل ====================
EMAIL_TARGETS = {
    "security": "security@mail.instagram.com",
    "support": "support@instagram.com",
    "help": "help@instagram.com",
    "android": "instagram-android@meta.com",
}

EMAIL_TEMPLATES = {
    "disable": """Subject: Appeal for Disabled Instagram Account - {{username}}

Dear Instagram/Meta Support Team,

I am writing to appeal the disabling of my Instagram account.

Account Details:
- Username: {{username}}
- Account Name: {{page_name}}
- Email on account: {{email}}
- Phone: {{phone}}
- Followers: {{followers}}
- Account Type: {{page_type}}

Reason for appeal:
{{description}}

I confirm that this account belongs to me and I have not intentionally violated any community guidelines.
I kindly request a review of this decision and restoration of my account.

Best regards,
{{page_name}}
{{email}}""",

    "limit": """Subject: Request to Remove Restrictions - {{username}}

Dear Instagram Support Team,

I am experiencing restrictions on my Instagram account and request your assistance.

Account Details:
- Username: {{username}}
- Account Name: {{page_name}}
- Email: {{email}}

Issue Description:
{{description}}

I have not violated any community guidelines and kindly request the removal of these restrictions.

Thank you for your support.

Best regards,
{{page_name}}
{{email}}""",

    "fake": """Subject: Report Fake/Impersonation Account - {{target_id}}

Dear Instagram Safety Team,

I am reporting a fake account that is impersonating me/causing harm.

My Account:
- Username: {{username}}
- Name: {{page_name}}
- Email: {{email}}

Fake Account Details:
- Username: {{target_id}}
- Reason: {{reason}}

Description:
{{description}}

I kindly request immediate action against this account.

Best regards,
{{page_name}}
{{email}}"""
}

def send_email(to_email, subject, body):
    """ارسال ایمیل با Gmail و برگرداندن خطای واقعی برای تشخیص مشکل."""
    server = None
    try:
        if not EMAIL_SENDER or '@' not in EMAIL_SENDER:
            return False, "EMAIL_SENDER نامعتبر است."

        # App Password گوگل ممکن است با فاصله نمایش داده شود؛ فاصله‌ها حذف می‌شوند.
        app_password = ''.join(str(EMAIL_PASSWORD or '').split())
        if not app_password or app_password.startswith('XXXX'):
            return False, "App Password تنظیم نشده است. مقدار EMAIL_PASSWORD را با App Password حساب Gmail جایگزین کن."

        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # Gmail SMTP over SSL
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30)
        server.login(EMAIL_SENDER, app_password)
        server.sendmail(EMAIL_SENDER, [to_email], msg.as_string())
        return True, None

    except smtplib.SMTPAuthenticationError as e:
        return False, "احراز هویت Gmail رد شد؛ ایمیل فرستنده یا App Password را بررسی کن. (کد SMTP: %s)" % getattr(e, 'smtp_code', 'نامشخص')
    except smtplib.SMTPConnectError as e:
        return False, f"اتصال به سرور Gmail برقرار نشد: {e}"
    except smtplib.SMTPRecipientsRefused as e:
        return False, f"Gmail گیرنده را قبول نکرد: {e}"
    except smtplib.SMTPException as e:
        return False, f"خطای SMTP: {e}"
    except OSError as e:
        return False, f"خطای شبکه/اتصال: {e}"
    except Exception as e:
        return False, f"خطای غیرمنتظره: {type(e).__name__}: {e}"
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass

def fill_template(template, data):
    result = template
    for key, value in data.items():
        result = result.replace(f"{{{{{key}}}}}", str(value or "---"))
    lines = result.split("\n")
    subject = ""
    body_lines = []
    for line in lines:
        if line.startswith("Subject:"):
            subject = line.replace("Subject:", "").strip()
        else:
            body_lines.append(line)
    return subject, "\n".join(body_lines).strip()


# ==================== ابزار تشخیص و راهنمای ادمین ====================
def detect_issue(description, service=""):
    """یک تشخیص اولیه و غیرقطعی برای کمک به ادمین در انتخاب مسیر پیگیری."""
    text = f"{service} {description}".lower()
    rules = [
        (("لایک", "کامنت", "فالو", "action block", "actionblock", "اکشن بلاک"), "Action Block / محدودیت فعالیت"),
        (("دایرکت", "dm", "پیام خصوصی"), "محدودیت دایرکت"),
        (("لایو", "live"), "محدودیت Live"),
        (("تبلیغ", "ads", "advertising", "تبلیغات"), "محدودیت تبلیغات"),
        (("هشتگ", "hashtag"), "محدودیت هشتگ"),
        (("disabled", "disable", "دیسیبل", "غیرفعال", "غیرفعال شده"), "Disabled / غیرفعال شدن حساب"),
        (("هک", "hack", "hacked", "امنیت"), "مشکل دسترسی/امنیت حساب"),
        (("فیک", "جعلی", "جعل هویت", "impersonat"), "گزارش پیج جعلی / جعل هویت"),
    ]
    for keys, label in rules:
        if any(k in text for k in keys):
            return label
    return "نیازمند بررسی دستی (نوع مشکل از توضیحات مشخص نیست)"

def admin_issue_summary(service, data):
    desc = data.get("desc", "")
    diagnosis = detect_issue(desc, service)
    if service == "🔄 بازگردانی پیج دیسیبل":
        summary = f"حساب {data.get('ig_id','---')} غیرفعال شده و کاربر درخواست بازگردانی دارد. وضعیت/پیام نمایش‌داده‌شده باید با اسکرین‌شات بررسی شود."
    elif service == "🚫 رفع محدودیت":
        summary = f"پیج {data.get('ig_id','---')} دچار محدودیت شده؛ طبق توضیح کاربر: {desc}."
    elif service == "🗑 حذف پیج جعلی/آزاردهنده":
        summary = f"کاربر درخواست پیگیری پیج {data.get('target_id','---')} به دلیل «{data.get('reason','---')}» را دارد."
    else:
        summary = "درخواست ثبت شده و نیازمند بررسی دستی ادمین است."
    return diagnosis, summary

def appeal_templates(data, kind):
    username = data.get("ig_id") or data.get("username") or "@username"
    email = data.get("email", "---")
    desc = data.get("desc", "---")
    page_name = data.get("topic") or data.get("page_type") or "Instagram account"
    target = data.get("target_id", "---")
    reason = data.get("reason", "---")
    if kind == "disable":
        return (
            "📩 *متن پیشنهادی اعتراض دیسیبل:*\n\n"
            f"Hello Instagram Support,\n\nI am requesting a review of my Instagram account {username}, which has been disabled. "
            f"I believe this action may have been taken in error.\n\nAccount details:\nUsername: {username}\nEmail: {email}\n"
            f"Issue details: {desc}\n\nPlease review my account and restore access if the disablement was made in error.\n\nThank you."
        )
    if kind == "limit":
        return (
            "📩 *متن پیشنهادی درخواست رفع محدودیت:*\n\n"
            f"Hello Instagram Support,\n\nMy account {username} is currently experiencing a restriction. "
            f"Issue: {desc}\n\nI believe the restriction may have been applied in error. Please review my account and remove the restriction if appropriate.\n\n"
            f"Email: {email}\nThank you."
        )
    return (
        "📩 *متن پیشنهادی گزارش پیج جعلی/جعل هویت:*\n\n"
        f"Hello Instagram Support,\n\nI would like to report the Instagram account {target}.\n"
        f"Reason: {reason}\nOriginal account: {username}\nDetails: {desc}\n\n"
        "Please review this report and take appropriate action according to Instagram's policies.\n\nThank you."
    )

def admin_path_guide(service):
    guides = {
        "🔄 بازگردانی پیج دیسیبل": (
            "🧭 *مسیر پیشنهادی پیگیری دیسیبل*\n\n"
            "1️⃣ اول اسکرین‌شات آخرین پیام Instagram را بررسی کن.\n"
            "2️⃣ مشخص کن مشکل Disabled است یا Login/Access.\n"
            "3️⃣ اطلاعات آیدی + ایمیل + نوع پیج + توضیحات را با فرم مناسب تطبیق بده.\n"
            "4️⃣ در صورت نیاز از مسیرهای رسمی بازیابی/اعتراض Instagram استفاده کن.\n"
            "5️⃣ متن پیشنهادی زیر را با اطلاعات سفارش بررسی و سپس دستی ارسال کن.\n\n"
            "🔗 مسیرهای موجود در سفارش: instagram.com/hacked و فرم‌های Help Center.\n"
            "⚠️ اگر Instagram احراز هویت، Video Selfie یا کد امنیتی خواست، ادامه کار باید توسط صاحب حساب انجام شود."
        ),
        "🚫 رفع محدودیت": (
            "🧭 *مسیر پیشنهادی پیگیری محدودیت*\n\n"
            "1️⃣ اسکرین‌شات Account Status را بازبینی کن.\n"
            "2️⃣ نوع محدودیت را مشخص کن: Action Block، DM، Live، Ads، Hashtag یا مورد دیگر.\n"
            "3️⃣ تاریخ شروع و شرح دقیق کاربر را بررسی کن.\n"
            "4️⃣ ابتدا مسیر Appeal/Review مرتبط با همان محدودیت را انتخاب کن.\n"
            "5️⃣ متن پیشنهادی را شخصی‌سازی و دستی ارسال کن.\n\n"
            "⚠️ از ارسال تکراری و پشت‌سرهم درخواست‌های یکسان خودداری کن."
        ),
        "🗑 حذف پیج جعلی/آزاردهنده": (
            "🧭 *مسیر پیشنهادی گزارش پیج جعلی*\n\n"
            "1️⃣ پیج هدف و پیج اصلی را با اطلاعات سفارش تطبیق بده.\n"
            "2️⃣ دلیل گزارش را مشخص کن: جعل هویت، آزار، سوءاستفاده از عکس یا مورد دیگر.\n"
            "3️⃣ مدارک مرتبط را بررسی کن.\n"
            "4️⃣ از فرم رسمی متناسب با نوع گزارش استفاده کن.\n"
            "5️⃣ متن گزارش را بر اساس اطلاعات واقعی سفارش ارسال کن.\n\n"
            "⚠️ فقط اطلاعات و مدارک واقعی کاربر ارسال شود."
        )
    }
    return guides.get(service, "🧭 این سفارش نیازمند بررسی دستی و تعیین مسیر توسط ادمین است.")

def admin_order_extra(service, data):
    diagnosis, summary = admin_issue_summary(service, data)
    extra = f"🧠 *تشخیص اولیه:* {diagnosis}\n📌 *خلاصه مشکل:* {summary}\n\n{admin_path_guide(service)}"
    if service == "🔄 بازگردانی پیج دیسیبل":
        extra += "\n\n" + appeal_templates(data, "disable")
    elif service == "🚫 رفع محدودیت":
        extra += "\n\n" + appeal_templates(data, "limit")
    elif service == "🗑 حذف پیج جعلی/آزاردهنده":
        extra += "\n\n" + appeal_templates(data, "fake")
    return extra

# ==================== منوی اصلی ====================
def admin_main_keyboard():
    """کیبورد اصلی ادمین؛ همه قابلیت‌ها از همین صفحه در دسترس هستند."""
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        types.KeyboardButton("🚨 سفارش‌های جدید"),
        types.KeyboardButton("📂 داشبورد مدیریت"),
        types.KeyboardButton("📋 همه سفارشات"),
        types.KeyboardButton("⏳ در انتظار بررسی"),
        types.KeyboardButton("🔍 در حال بررسی"),
        types.KeyboardButton("⚙️ در حال انجام"),
        types.KeyboardButton("✅ تکمیل‌شده‌ها"),
        types.KeyboardButton("❌ لغوشده‌ها"),
        types.KeyboardButton("📊 آمار کلی"),
        types.KeyboardButton("🧭 راهنمای پیگیری"),
        types.KeyboardButton("🔐 کنترل دسترسی ادمین"),
        types.KeyboardButton("📢 پیام همگانی"),
        types.KeyboardButton("📧 سیستم ایمیل"),
        types.KeyboardButton("🔄 تازه‌سازی داشبورد")
    )
    return m

def send_admin_order_card(chat_id, o):
    """کارت کامل سفارش با اقدامات سریع؛ مستقیم در چت ادمین."""
    diagnosis, summary = admin_issue_summary(o['service'], o['data'])
    username = o.get('username') or 'ندارد'
    text = (
        f"🚨 سفارش جدید #{o['id']}\n"
        f"{SEP}\n\n"
        f"🛒 خدمت: {o['service']}\n"
        f"👤 کاربر: {o.get('user_name') or '—'}\n"
        f"🆔 آیدی تلگرام: {o['user_id']}\n"
        f"🔗 یوزرنیم: @{username}\n"
        f"🕐 زمان ثبت: {o['time']}\n"
        f"📊 وضعیت: {STATUS.get(o['status'], o['status'])}\n\n"
        f"🧠 تشخیص اولیه: {diagnosis}\n"
        f"📌 خلاصه: {summary}\n\n"
        "👇 برای رسیدگی سریع از دکمه‌های همین سفارش استفاده کن."
    )
    bot.send_message(
        chat_id, text,
        reply_markup=order_action_markup(o['user_id'], o['id']),
        disable_notification=False
    )

def admin_dashboard(chat_id, name="", show_pending=True):
    """صفحه اصلی ادمین؛ سفارش جدید را همان‌جا قابل مشاهده می‌کند."""
    global orders_db
    orders_db = load_orders()
    pending = [o for o in orders_db if o.get('status') == 'pending']
    text = (
        "👑 داشبورد مدیریت ترویده\n"
        f"{SEP}\n\n"
        f"👤 ادمین: {name or 'مدیر'}\n"
        f"📦 کل سفارش‌ها: {len(orders_db)}\n"
        f"🚨 منتظر بررسی: {len(pending)}\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        "همه امکانات از همین صفحه در دسترسه.\n"
        "هر سفارش جدید هم بلافاصله مستقیم در همین چت ارسال می‌شود."
    )
    bot.send_message(chat_id, text, reply_markup=admin_main_keyboard())
    if show_pending and pending:
        bot.send_message(chat_id, f"🚨 {len(pending)} سفارش منتظر بررسی داری:", reply_markup=admin_main_keyboard())
        for o in reversed(pending[-10:]):
            send_admin_order_card(chat_id, o)

def order_status_chart(order):
    steps = ["pending", "reviewing", "processing", "done"]
    icons_map = {"pending": "⏳", "reviewing": "🔍", "processing": "⚙️", "done": "✅"}
    labels_map = {"pending": "ثبت سفارش", "reviewing": "در حال بررسی", "processing": "در حال انجام", "done": "تکمیل شده"}
    current = order["status"]

    if current == "cancelled":
        return (
            f"❌ *سفارش #{order['id']} لغو شده*\n\n"
            f"🛒 {order['service']}\n"
            f"🕐 {order['time']}\n\n"
            "متأسفانه سفارش شما لغو شد.\n"
            "برای اطلاعات بیشتر با پشتیبانی تماس بگیرید:\n@tarvideh"
        )

    chart_lines = []
    current_found = False
    for i, step in enumerate(steps):
        icon = icons_map[step]
        label = labels_map[step]
        connector = "│\n" if i < len(steps) - 1 else ""
        if step == current:
            current_found = True
            chart_lines.append(f"▶️ *{icon} {label}*  ← الان اینجاست\n{connector}")
        elif not current_found:
            chart_lines.append(f"✅ {icon} {label}\n{connector}")
        else:
            chart_lines.append(f"⬜️ {icon} {label}\n{connector}")

    chart = "".join(chart_lines)

    history_text = ""
    if order.get("history"):
        history_text = f"\n{SEP}\n🕘 *تاریخچه تغییرات:*\n"
        for h in order["history"][-5:]:
            history_text += f"• {h['time']} — {STATUS.get(h['status'], h['status'])}\n"

    note_text = ""
    if order.get("admin_note"):
        note_text = f"\n{SEP}\n📩 *پیام از تیم ترویده:*\n_{order['admin_note']}_"

    return (
        f"📦 *سفارش #{order['id']}*\n"
        f"🛒 {order['service']}\n"
        f"🕐 {order['time']}\n"
        f"{SEP}\n\n"
        f"📊 *مسیر پیشرفت سفارش:*\n\n"
        f"{chart}"
        f"{history_text}"
        f"{note_text}"
    )

def main_menu(chat_id, name=""):
    # ادمین هم همان صفحه اصلی خدمات را می‌بیند؛ فقط یک دکمه اختصاصی مدیریت
    # در انتهای منو برای ورود سریع به کنترل ربات اضافه می‌شود.
    is_admin_user = is_admin(chat_id)

    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        types.KeyboardButton("🔄 بازگردانی پیج دیسیبل"),
        types.KeyboardButton("🚫 رفع محدودیت"),
        types.KeyboardButton("🗑 حذف پیج جعلی"),
        types.KeyboardButton("✈️ پریمیوم تلگرام"),
        types.KeyboardButton("👥 خرید فالوور"),
        types.KeyboardButton("📱 شماره مجازی"),
        types.KeyboardButton("🛡 امنیت پیج"),
        types.KeyboardButton("🎨 ادیت و طراحی"),
        types.KeyboardButton("💡 ایده محتوایی"),
        types.KeyboardButton("🤖 تشخیص هوشمند مشکل"),
        types.KeyboardButton("📦 سفارشات من"),
        types.KeyboardButton("👤 پروفایل من"),
        types.KeyboardButton("📢 کانال ما"),
        types.KeyboardButton("📞 پشتیبانی")
    )
    if is_admin_user:
        # فقط ادمین این دکمه را می‌بیند. با یک کلیک وارد کنترل کامل مدیریت می‌شود.
        m.add(types.KeyboardButton("👑 کنترل مدیریت"))

    g = f"سلام *{name}* عزیز 👋\n\n" if name else ""
    footer = (
        "\n\n👑 *مدیریت ربات:* دکمه «کنترل مدیریت» برای شما فعال است."
        if is_admin_user else ""
    )
    bot.send_message(chat_id,
        f"{g}"
        "🏆 *به ربات رسمی ترویده خوش اومدی!*\n"
        f"{SEP}\n\n"
        "📌 *خدمات تخصصی ما:*\n\n"
        "🔄 بازگردانی پیج‌های غیرفعال شده\n"
        "🚫 رفع انواع محدودیت‌های اینستاگرام\n"
        "🗑 حذف پیج‌های جعلی و آزاردهنده\n"
        "🛡 امنیت و محافظت از پیج\n"
        "✈️ پریمیوم تلگرام با قیمت مناسب\n"
        "📱 شماره مجازی برای همه پلتفرم‌ها\n"
        "👥 فالوور واقعی اینستاگرام\n"
        "🎨 ادیت و طراحی محتوای حرفه‌ای\n"
        "💡 ایده‌پردازی محتوا (رایگان)\n\n"
        f"{SEP}\n"
        "👇 *خدمت مورد نظرت رو انتخاب کن:*" + footer,
        parse_mode="Markdown", reply_markup=m)

@bot.message_handler(func=lambda m: m.text == "👑 کنترل مدیریت" and is_admin(m.from_user.id))
def admin_control_button(message):
    # ورود مستقیم به پنل کنترل ادمین؛ بدون نیاز به /admin
    admin_dashboard(message.chat.id, message.from_user.first_name, show_pending=True)

@bot.message_handler(commands=['start'])
def start(message):
    user_data.pop(message.from_user.id, None)
    # ادمین هم از همان صفحه اصلی وارد می‌شود؛ دکمه «👑 کنترل مدیریت»
    # در همان صفحه برای او نمایش داده می‌شود.
    main_menu(message.chat.id, message.from_user.first_name)

@bot.message_handler(func=lambda m: m.text == "🔙 بازگشت به منو")
def go_back(message):
    user_data.pop(message.from_user.id, None)
    if is_admin(message.from_user.id):
        admin_dashboard(message.chat.id, message.from_user.first_name, show_pending=True)
    else:
        main_menu(message.chat.id)

# /admin فقط به‌عنوان میانبر قدیمی باقی می‌ماند؛ استفاده از آن لازم نیست.
@bot.message_handler(commands=['admin'])
def admin_command_alias(message):
    if is_admin(message.from_user.id):
        admin_dashboard(message.chat.id, message.from_user.first_name, show_pending=True)

@bot.message_handler(func=lambda m: m.text == "📂 داشبورد مدیریت" and is_admin(m.from_user.id))
def admin_dashboard_button(message):
    admin_dashboard(message.chat.id, message.from_user.first_name, show_pending=True)

@bot.message_handler(func=lambda m: m.text == "🚨 سفارش‌های جدید" and is_admin(m.from_user.id))
def new_orders_button(message):
    global orders_db
    orders_db = load_orders()
    pending = [o for o in orders_db if o.get('status') == 'pending']
    if not pending:
        bot.send_message(message.chat.id, "✅ فعلاً سفارش جدیدی در انتظار بررسی نیست.", reply_markup=admin_main_keyboard())
        return
    bot.send_message(message.chat.id, f"🚨 {len(pending)} سفارش جدید:", reply_markup=admin_main_keyboard())
    for o in reversed(pending[-20:]):
        send_admin_order_card(message.chat.id, o)

def show_orders(chat_id, status_key=None):
    global orders_db
    orders_db = load_orders()
    filtered = [o for o in orders_db if o['status'] == status_key] if status_key else orders_db[-20:]
    title = STATUS.get(status_key, "همه سفارشات") if status_key else "همه سفارشات"
    if not filtered:
        bot.send_message(chat_id, f"📭 هیچ سفارشی در وضعیت {title} وجود نداره.", reply_markup=admin_main_keyboard())
        return
    bot.send_message(chat_id, f"📋 {title} — {len(filtered)} مورد", reply_markup=admin_main_keyboard())
    for o in reversed(filtered[-20:]):
        send_admin_order_card(chat_id, o)

@bot.message_handler(commands=['orders'])
def orders_command(message):
    if is_admin(message.from_user.id): show_orders(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "📋 همه سفارشات" and is_admin(m.from_user.id))
def all_orders(message): show_orders(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "⏳ در انتظار بررسی" and is_admin(m.from_user.id))
def pending_orders(message): show_orders(message.chat.id, "pending")

@bot.message_handler(func=lambda m: m.text == "🔍 در حال بررسی" and is_admin(m.from_user.id))
def reviewing_orders(message): show_orders(message.chat.id, "reviewing")

@bot.message_handler(func=lambda m: m.text == "⚙️ در حال انجام" and is_admin(m.from_user.id))
def processing_orders(message): show_orders(message.chat.id, "processing")

@bot.message_handler(func=lambda m: m.text == "✅ تکمیل‌شده‌ها" and is_admin(m.from_user.id))
def done_orders(message): show_orders(message.chat.id, "done")

@bot.message_handler(func=lambda m: m.text == "❌ لغوشده‌ها" and is_admin(m.from_user.id))
def cancelled_orders(message): show_orders(message.chat.id, "cancelled")

@bot.message_handler(func=lambda m: m.text == "📊 آمار کلی" and is_admin(m.from_user.id))
def stats(message):
    global orders_db
    orders_db = load_orders()
    total = len(orders_db)
    by_s = {k: 0 for k in STATUS}
    by_svc = {}
    for o in orders_db:
        by_s[o['status']] = by_s.get(o['status'], 0) + 1
        by_svc[o['service']] = by_svc.get(o['service'], 0) + 1
    text = f"📊 آمار کلی ربات\n{SEP}\n\n🔢 کل سفارشات: {total}\n\n📈 وضعیت‌ها:\n"
    for k, v in STATUS.items(): text += f"{v}: {by_s.get(k, 0)}\n"
    text += "\n📈 سرویس‌ها:\n"
    for svc, c in sorted(by_svc.items(), key=lambda x: -x[1]): text += f"• {svc}: {c}\n"
    bot.send_message(message.chat.id, text, reply_markup=admin_main_keyboard())

@bot.message_handler(func=lambda m: m.text == "🧭 راهنمای پیگیری" and is_admin(m.from_user.id))
def admin_guide_menu(message):
    bot.send_message(message.chat.id,
        "🧭 راهنمای سریع ادمین\n" + SEP + "\n\n"
        "1️⃣ سفارش جدید مستقیم در چت ادمین می‌آید.\n"
        "2️⃣ اطلاعات سفارش را همان پیام بررسی کن.\n"
        "3️⃣ «📂 پرونده کامل» را بزن تا جزئیات کامل را ببینی.\n"
        "4️⃣ با دکمه‌های «در بررسی» و «در انجام» وضعیت را تغییر بده.\n"
        "5️⃣ برای ارتباط، «💬 پاسخ به کاربر» را بزن.\n"
        "6️⃣ بعد از پایان، «✅ تکمیل شد» را بزن.\n\n"
        "💡 برای سفارش جدید لازم نیست وارد هیچ بخش جداگانه‌ای شوی.\n"
        "⚠️ کد ورود، رمز عبور، Backup Code یا کد 2FA از کاربر درخواست نشود.",
        reply_markup=admin_main_keyboard())

@bot.message_handler(func=lambda m: m.text in ("🔐 کنترل دسترسی ادمین", "👥 مدیریت ادمین‌ها") and is_admin(m.from_user.id))
def manage_admins(message):
    """صفحه کنترل دسترسی ادمین‌ها؛ بدون نیاز به تایپ /admin یا دستورات مدیریتی."""
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("➕ افزودن ادمین", callback_data="admins_add"),
        types.InlineKeyboardButton("➖ حذف ادمین", callback_data="admins_remove"),
        types.InlineKeyboardButton("🔄 بروزرسانی لیست", callback_data="admins_list"),
        types.InlineKeyboardButton("🔙 بازگشت به داشبورد", callback_data="admins_back")
    )
    active = "\n".join(f"{i}. <code>{aid}</code>" for i, aid in enumerate(ADMINS, 1)) or "— هیچ ادمینی ثبت نشده —"
    text = (
        "🔐 <b>کنترل دسترسی ادمین</b>\n"
        f"{SEP}\n\n"
        "از این بخش می‌تونی دسترسی مدیران ربات رو مدیریت کنی.\n\n"
        "👑 <b>ادمین‌های فعال:</b>\n" + active + "\n\n"
        "⚠️ فقط ادمین فعلی می‌تونه این بخش رو باز کنه."
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data in ("admins_add", "admins_remove", "admins_list", "admins_back"))
def admin_access_controls(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ دسترسی ندارید!"); return

    if call.data == "admins_back":
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        admin_dashboard(call.message.chat.id, call.from_user.first_name, show_pending=False)
        return

    if call.data == "admins_list":
        active = "\n".join(f"{i}. <code>{aid}</code>" for i, aid in enumerate(ADMINS, 1)) or "— هیچ ادمینی ثبت نشده —"
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(
            types.InlineKeyboardButton("➕ افزودن ادمین", callback_data="admins_add"),
            types.InlineKeyboardButton("➖ حذف ادمین", callback_data="admins_remove"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="admins_back")
        )
        bot.edit_message_text(
            "🔐 <b>کنترل دسترسی ادمین</b>\n"
            f"{SEP}\n\n"
            "👑 <b>ادمین‌های فعال:</b>\n" + active + "\n\n"
            "⚡ مدیریت دسترسی‌ها از همین صفحه انجام می‌شود.",
            call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=mk
        )
        bot.answer_callback_query(call.id, "🔄 لیست بروزرسانی شد")
        return

    if call.data == "admins_add":
        user_data[f"admin_access_{call.from_user.id}"] = {"action": "add"}
        bot.send_message(
            call.message.chat.id,
            "➕ <b>افزودن ادمین</b>\n\nآیدی عددی تلگرام فرد موردنظر را ارسال کن.\nمثال: <code>123456789</code>",
            parse_mode="HTML", reply_markup=back_btn()
        )
        bot.answer_callback_query(call.id)
        return

    if call.data == "admins_remove":
        user_data[f"admin_access_{call.from_user.id}"] = {"action": "remove"}
        bot.send_message(
            call.message.chat.id,
            "➖ <b>حذف ادمین</b>\n\nآیدی عددی ادمینی که باید دسترسی‌اش حذف شود را ارسال کن.\nمثال: <code>123456789</code>",
            parse_mode="HTML", reply_markup=back_btn()
        )
        bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: f"admin_access_{m.from_user.id}" in user_data and is_admin(m.from_user.id))
def process_admin_access(message):
    key = f"admin_access_{message.from_user.id}"
    action = user_data[key].get("action")
    if message.text == "🔙 بازگشت به منو":
        user_data.pop(key, None)
        admin_dashboard(message.chat.id, message.from_user.first_name, show_pending=False)
        return
    try:
        target = int(message.text.strip())
    except (TypeError, ValueError):
        bot.send_message(message.chat.id, "❌ آیدی نامعتبره. فقط آیدی عددی تلگرام رو بفرست.", reply_markup=back_btn())
        return

    if action == "add":
        if target in ADMINS:
            msg = "ℹ️ این آیدی از قبل ادمین است."
        else:
            ADMINS.append(target)
            msg = f"✅ آیدی <code>{target}</code> با موفقیت ادمین شد."
    else:
        if target == message.from_user.id:
            msg = "⚠️ نمی‌تونی دسترسی خودت رو حذف کنی."
        elif target not in ADMINS:
            msg = "ℹ️ این آیدی در لیست ادمین‌ها نیست."
        else:
            ADMINS.remove(target)
            msg = f"✅ دسترسی آیدی <code>{target}</code> حذف شد."

    user_data.pop(key, None)
    bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=admin_main_keyboard())
    manage_admins(message)

@bot.message_handler(func=lambda m: m.text == "📧 سیستم ایمیل" and is_admin(m.from_user.id))
def email_menu_button(message):
    email_cmd(message)

@bot.message_handler(commands=['email'])
def email_cmd(message):
    if not is_admin(message.from_user.id): return
    bot.send_message(message.chat.id,
        f"📧 *سیستم ارسال ایمیل*\n"
        f"{SEP}\n\n"
        "📌 *دستورات:*\n\n"
        "برای ارسال ایمیل، اطلاعات پیج رو اینطور بفرست:\n\n"
        "```\n"
        "/send_email\n"
        "نوع: disable (یا limit یا fake)\n"
        "آیدی: @username\n"
        "نام: اسم پیج\n"
        "ایمیل: email@gmail.com\n"
        "تلفن: 09xxxxxxxxx\n"
        "فالوور: تعداد\n"
        "نوع پیج: کاری یا شخصی\n"
        "توضیحات: متن توضیحات\n"
        "مقصد: security (یا support یا help)\n"
        "```\n\n"
        "📧 *ایمیل‌های موجود:*\n"
        "• security → security@mail.instagram.com\n"
        "• support → support@instagram.com\n"
        "• help → help@instagram.com\n"
        "• android → instagram-android@meta.com",
        parse_mode="Markdown")

@bot.message_handler(commands=['send_email'])
def send_email_cmd(message):
    if not is_admin(message.from_user.id): return
    try:
        lines = message.text.strip().split("\n")
        data = {}
        for line in lines[1:]:
            if ":" in line:
                key, val = line.split(":", 1)
                data[key.strip()] = val.strip()

        type_map = {"disable": "disable", "limit": "limit", "fake": "fake",
                    "دیسیبل": "disable", "محدودیت": "limit", "جعلی": "fake"}
        email_type = type_map.get(data.get("نوع", "").lower(), "disable")

        fill_data = {
            "username": data.get("آیدی", ""),
            "page_name": data.get("نام", ""),
            "email": data.get("ایمیل", ""),
            "phone": data.get("تلفن", ""),
            "followers": data.get("فالوور", ""),
            "page_type": data.get("نوع پیج", ""),
            "description": data.get("توضیحات", ""),
            "target_id": data.get("پیج هدف", ""),
            "reason": data.get("دلیل", ""),
        }

        dest_key = data.get("مقصد", "security").lower()
        to_email = EMAIL_TARGETS.get(dest_key, "security@mail.instagram.com")
        template = EMAIL_TEMPLATES.get(email_type, EMAIL_TEMPLATES["disable"])
        subject, body = fill_template(template, fill_data)

        # ذخیره برای تأیید
        user_data[f"pending_email_{message.from_user.id}"] = {
            "to": to_email, "subject": subject, "body": body
        }

        mk = types.InlineKeyboardMarkup()
        mk.add(
            types.InlineKeyboardButton("✅ تأیید و ارسال", callback_data=f"confirm_email_{message.from_user.id}"),
            types.InlineKeyboardButton("❌ لغو", callback_data=f"cancel_email_{message.from_user.id}")
        )

        bot.send_message(message.chat.id,
            f"📧 *پیش‌نمایش ایمیل*\n"
            f"{SEP}\n\n"
            f"📤 *مقصد:* `{to_email}`\n"
            f"📌 *موضوع:* {subject}\n\n"
            f"{SEP}\n\n"
            f"```\n{body}\n```\n\n"
            f"{SEP}\n\n"
            "✅ آیا این ایمیل ارسال بشه؟",
            parse_mode="Markdown", reply_markup=mk)
    except Exception as e:
        bot.send_message(message.chat.id,
            f"❌ *خطا در پردازش:*\n`{str(e)}`\n\n"
            "فرمت صحیح رو چک کن با /email",
            parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_email_") or c.data.startswith("cancel_email_"))
def email_confirm(call):
    if not is_admin(call.from_user.id): return
    action = "confirm" if call.data.startswith("confirm_email_") else "cancel"
    uid = int(call.data.split("_")[-1])
    key = f"pending_email_{uid}"

    if action == "cancel":
        if key in user_data: del user_data[key]
        bot.edit_message_text("❌ ارسال ایمیل لغو شد.", call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "❌ لغو شد.")
        return

    if key not in user_data:
        bot.answer_callback_query(call.id, "❌ اطلاعات پیدا نشد."); return

    email_data = user_data[key]
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    del user_data[key]
    bot.answer_callback_query(call.id, "⏳ در حال ارسال...")

    import threading
    def do_send():
        try:
            bot.edit_message_text(
                "📤 *در حال ارسال ایمیل...*\n\n⏳ لطفاً صبر کن...",
                chat_id, msg_id, parse_mode="Markdown")
        except: pass

        success, email_error = send_email(email_data["to"], email_data["subject"], email_data["body"])

        if success:
            try:
                bot.edit_message_text(
                    f"✅ *ایمیل با موفقیت ارسال شد!*\n"
                    f"{SEP}\n\n"
                    f"📤 مقصد: `{email_data['to']}`\n"
                    f"📌 موضوع: {email_data['subject']}\n"
                    f"🕐 زمان: {datetime.now().strftime('%H:%M')}",
                    chat_id, msg_id, parse_mode="Markdown")
            except: pass
        else:
            safe_error = str(email_error or "خطای نامشخص")
            try:
                bot.edit_message_text(
                    f"❌ *خطا در ارسال ایمیل!*\n\n"
                    f"🔎 *جزئیات:*\n`{safe_error}`\n\n"
                    "📌 موارد بررسی:\n"
                    "• App Password درست وارد شده؟\n"
                    "• EMAIL_PASSWORD در کد جایگزین شده؟\n"
                    "• Gmail دو مرحله‌ای فعاله؟",
                    chat_id, msg_id, parse_mode="Markdown")
            except: pass

    threading.Thread(target=do_send, daemon=True).start()

@bot.message_handler(func=lambda m: m.text == "📢 پیام همگانی" and is_admin(m.from_user.id))
def broadcast_ask(message):
    user_data[message.from_user.id] = {"step": "broadcast"}
    bot.send_message(message.chat.id, "📢 پیامت رو بنویس تا به همه کاربران ارسال بشه:", reply_markup=back_btn())

@bot.callback_query_handler(func=lambda c: c.data.startswith("order_") or c.data.startswith("note_"))
def order_management_cb(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ دسترسی ندارید!"); return
    action, oid_text = call.data.split("_", 1)
    try: oid = int(oid_text)
    except:
        bot.answer_callback_query(call.id, "❌ شناسه سفارش نامعتبر است."); return
    order = next((o for o in orders_db if o["id"] == oid), None)
    if not order:
        bot.answer_callback_query(call.id, "❌ سفارش پیدا نشد."); return
    if action == "note":
        user_data[f"admin_note_{call.from_user.id}"] = oid
        bot.send_message(call.message.chat.id, f"📝 یادداشت داخلی برای سفارش #{oid} را بنویس.\nاین یادداشت برای کاربر ارسال نمی‌شود:", parse_mode="Markdown")
        bot.answer_callback_query(call.id); return
    d = order.get("data", {})
    diagnosis, summary = admin_issue_summary(order["service"], d)
    text = (f"📂 *پرونده کامل سفارش #{oid}*\n{SEP}\n\n"
            f"🛒 *خدمت:* {order['service']}\n"
            f"👤 *کاربر:* {order['user_name']} | @{order['username']}\n"
            f"🆔 `{order['user_id']}`\n"
            f"🕐 *ثبت:* {order['time']}\n"
            f"📊 *وضعیت:* {STATUS.get(order['status'])}\n\n"
            f"🧠 *تشخیص اولیه:* {diagnosis}\n"
            f"📌 *خلاصه:* {summary}\n\n"
            f"📋 *اطلاعات ثبت‌شده:*\n")
    for k, v in d.items():
        if k in ("last_pic", "screenshot", "proof"): continue
        if k == "service": continue
        label = {"ig_id":"آیدی پیج","email":"ایمیل","phone":"تلفن","topic":"موضوع","page_type":"نوع پیج","followers":"فالوور","desc":"توضیحات","reason":"دلیل","target_id":"پیج هدف","original_id":"پیج اصلی","content_type":"نوع محتوا"}.get(k, k)
        text += f"• {label}: {v}\n"
    text += f"\n{admin_path_guide(order['service'])}"
    if order.get("admin_note"):
        text += f"\n\n📝 *یادداشت داخلی:* {order['admin_note']}"
    if order.get("history"):
        text += "\n\n🕘 *تاریخچه وضعیت:*\n"
        for h in order["history"][-8:]:
            admin_name = h.get("admin") or "—"
            text += f"• {h['time']} — {STATUS.get(h['status'], h['status'])} — ادمین: {admin_name}\n"
    if order["service"] == "🔄 بازگردانی پیج دیسیبل": text += "\n\n" + appeal_templates(d, "disable")
    elif order["service"] == "🚫 رفع محدودیت": text += "\n\n" + appeal_templates(d, "limit")
    elif order["service"] == "🗑 حذف پیج جعلی/آزاردهنده": text += "\n\n" + appeal_templates(d, "fake")
    bot.send_message(call.message.chat.id, text, reply_markup=order_action_markup(order["user_id"], oid))
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: f"admin_note_{m.from_user.id}" in user_data)
def save_admin_note(message):
    if not is_admin(message.from_user.id): return
    key = f"admin_note_{message.from_user.id}"
    oid = user_data.pop(key)
    order = next((o for o in orders_db if o["id"] == oid), None)
    if not order:
        bot.send_message(message.chat.id, "❌ سفارش پیدا نشد."); return
    order["admin_note"] = message.text
    save_order(order)
    bot.send_message(message.chat.id, f"✅ یادداشت داخلی سفارش #{oid} ذخیره شد.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("status_"))
def change_status(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ دسترسی ندارید!"); return
    parts = call.data.split("_", 2)
    try:
        oid, ns = int(parts[1]), parts[2]
    except (ValueError, IndexError):
        bot.answer_callback_query(call.id, "❌ اطلاعات وضعیت نامعتبر است.")
        return
    for o in orders_db:
        if o["id"] == oid:
            o["status"] = ns
            o.setdefault("history", []).append({"status": ns, "admin": call.from_user.id, "time": datetime.now().strftime("%Y-%m-%d %H:%M")})
            save_order(o)
            try:
                chart = order_status_chart(o)
                mk = types.InlineKeyboardMarkup()
                mk.add(types.InlineKeyboardButton("📊 مشاهده جزئیات", callback_data=f"myorder_{oid}"))
                bot.send_message(o["user_id"],
                    f"📬 *آپدیت سفارش #{oid}*\n"
                    f"{SEP}\n\n"
                    f"{chart}",
                    parse_mode="Markdown", reply_markup=mk)
            except: pass
            bot.answer_callback_query(call.id, f"✅ {STATUS[ns]}")
            return
    bot.answer_callback_query(call.id, "❌ سفارش پیدا نشد.")

# ==================== بازگردانی دیسیبل ====================
@bot.message_handler(func=lambda m: m.text == "🔄 بازگردانی پیج دیسیبل")
def dis_start(message):
    user_data[message.from_user.id] = {"service": "🔄 بازگردانی پیج دیسیبل", "step": "dis_id"}
    bot.send_message(message.chat.id,
        f"🔄 *بازگردانی پیج دیسیبل*\n"
        f"{SEP}\n\n"
        "📌 *این سرویس شامل چه مواردیه؟*\n\n"
        "✔️ پیج‌های permanently disabled\n"
        "✔️ پیج‌های دیسیبل به دلیل تخلف\n"
        "✔️ پیج‌های هک و دیسیبل شده\n"
        "✔️ پیج‌های دیسیبل به دلیل یکپارچگی\n\n"
        "⭐ *نرخ موفقیت: ۹۸٪*\n"
        "⏰ *زمان تحویل: ۲۴ تا ۷۲ ساعت*\n\n"
        f"{SEP}\n"
        "📝 *مرحله ۱ از ۷*\n\n"
        "🔹 آیدی پیج اینستاگرامت رو بفرست:\n"
        "_(مثال: @username)_",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_id")
def dis_id(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"ig_id": message.text, "step": "dis_email"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۲ از ۷*\n\n"
        "📧 ایمیل متصل به پیجت رو بفرست:\n"
        "_(اگه نداری بنویس: ندارم)_",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_email")
def dis_email(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"email": message.text, "step": "dis_pic"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۳ از ۷*\n\n"
        "📸 آخرین تصویری که هنگام ورود به پیج دیدی رو بفرست:\n"
        "_(اگه نداری بنویس: ندارم)_",
        parse_mode="Markdown")

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_pic")
def dis_pic_photo(message):
    user_data[message.from_user.id].update({"last_pic": message.photo[-1].file_id, "pic_type": "photo", "step": "dis_topic"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۴ از ۷*\n\n"
        "📌 موضوع پیجت چیه؟\n"
        "_(مثال: فروش محصول، آموزش، پزشکی، سرگرمی)_",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_pic")
def dis_pic_text(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"last_pic": message.text, "pic_type": "text", "step": "dis_topic"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۴ از ۷*\n\n"
        "📌 موضوع پیجت چیه؟\n"
        "_(مثال: فروش محصول، آموزش، پزشکی)_",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_topic")
def dis_topic(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"topic": message.text, "step": "dis_type"})
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    mk.add("💼 کاری", "👤 شخصی", "🔙 بازگشت به منو")
    bot.send_message(message.chat.id,
        "📝 *مرحله ۵ از ۷*\n\n"
        "🏷 پیجت کاری بوده یا شخصی؟",
        parse_mode="Markdown", reply_markup=mk)

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_type")
def dis_type(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"page_type": message.text, "step": "dis_followers"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۶ از ۷*\n\n"
        "👥 تعداد تقریبی فالوور پیج رو بنویس:",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_followers")
def dis_followers(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"followers": message.text, "step": "dis_desc"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۷ از ۷*\n\n"
        "📋 توضیح کامل از اتفاقی که افتاده:\n\n"
        "🔹 چه زمانی دیسیبل شد؟\n"
        "🔹 چه پیامی نشون میده؟\n"
        "🔹 قبلاً اخطار گرفتی؟\n"
        "🔹 دلیل احتمالی چیه؟",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_desc")
def dis_desc(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    d = user_data[message.from_user.id]; d["desc"] = message.text
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id,
        f"✅ *سفارش #{order['id']} با موفقیت ثبت شد!*\n"
        f"{SEP}\n\n"
        "📋 *خلاصه سفارش:*\n\n"
        f"📸 پیج: {d.get('ig_id')}\n"
        f"📌 موضوع: {d.get('topic')}\n"
        f"🏷 نوع: {d.get('page_type')}\n"
        f"👥 فالوور: {d.get('followers')}\n\n"
        f"{SEP}\n"
        "⏳ تیم ما در کمتر از *۲۴ ساعت* بررسی می‌کنه و همینجا پاسخ میده.\n\n"
        f"📢 کانال ما: {CHANNEL}",
        parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_action_markup(u.id, order["id"])
    admin_text = (
        f"🔔 *اعلان سفارش جدید — #{order['id']}*\n"
        f"🔄 *بازگردانی پیج دیسیبل*\n"
        f"{SEP}\n\n"
        f"👤 *کاربر:* {u.first_name} {u.last_name or ''}\n"
        f"🆔 @{u.username or 'ندارد'} | `{u.id}`\n\n"
        f"📸 *پیج:* {d.get('ig_id')}\n"
        f"📧 *ایمیل:* {d.get('email')}\n"
        f"📌 *موضوع:* {d.get('topic')}\n"
        f"🏷 *نوع:* {d.get('page_type')}\n"
        f"👥 *فالوور:* {d.get('followers')}\n"
        f"📝 *توضیحات:* {d.get('desc')}\n"
        f"🕐 *زمان:* {order['time']}\n"
        f"{SEP}\n"
        "🔗 *فرم‌های پیشنهادی:*\n"
        "• instagram.com/hacked\n"
        "• instagram.com/hacked/?hl=en\n"
        "• is.gd/xpHtXL\n"
        "• facebook.com/help/contact/507270721277573\n"
        "• help.instagram.com/contact/814820110107093\n"
        "📧 security@mail.instagram.com"
        f"\n\n{SEP}\n"
        + admin_order_extra(d["service"], d)
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
        f"🚫 *رفع محدودیت پیج اینستاگرام*\n"
        f"{SEP}\n\n"
        "📌 *انواع محدودیت‌هایی که رفع می‌کنیم:*\n\n"
        "✔️ بلاک اکشن (لایک، کامنت، فالو)\n"
        "✔️ محدودیت هشتگ\n"
        "✔️ محدودیت دایرکت\n"
        "✔️ محدودیت لایو\n"
        "✔️ محدودیت تبلیغات\n"
        "✔️ سایر محدودیت‌های اینستاگرام\n\n"
        f"{SEP}\n"
        "📝 *مرحله ۱ از ۳*\n\n"
        "📸 اسکرین‌شات از بخش *وضعیت حساب* پیجت بفرست:\n"
        "_(مسیر: تنظیمات ← حساب ← وضعیت حساب)_",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "lim_pic")
def lim_pic(message):
    user_data[message.from_user.id].update({"screenshot": message.photo[-1].file_id, "step": "lim_id"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۲ از ۳*\n\n"
        "🔹 آیدی پیجت رو بفرست:",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "lim_id")
def lim_id(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"ig_id": message.text, "step": "lim_desc"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۳ از ۳*\n\n"
        "📋 چه محدودیتی داری و از کی شروع شده؟\n\n"
        "_(مثال: بلاک اکشن از ۳ روز پیش، نمیتونم لایک کنم)_",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "lim_desc")
def lim_desc(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    d = user_data[message.from_user.id]; d["desc"] = message.text
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id,
        f"✅ *سفارش #{order['id']} با موفقیت ثبت شد!*\n"
        f"{SEP}\n\n"
        "⏳ تیم ما بررسی می‌کنه و همینجا پاسخ میده.\n"
        "🕐 *زمان پاسخ: کمتر از ۲۴ ساعت*",
        parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_action_markup(u.id, order["id"])
    admin_text = (
        f"🔔 *اعلان سفارش جدید — #{order['id']}*\n"
        f"🚫 *رفع محدودیت*\n"
        f"{SEP}\n\n"
        f"👤 *کاربر:* {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n\n"
        f"📸 *پیج:* {d.get('ig_id')}\n"
        f"📝 *محدودیت:* {d.get('desc')}\n"
        f"🕐 *زمان:* {order['time']}\n"
        f"{SEP}\n"
        "🔗 *فرم‌های پیشنهادی:*\n"
        "• instagram.com/hacked\n"
        "• help.instagram.com/contact/372592039493026\n"
        "• help.instagram.com/contact/512241091300432\n"
        "• is.gd/xpHtXL"
        f"\n\n{SEP}\n"
        + admin_order_extra(d["service"], d)
    )
    try: notify_admins(admin_text, mk, d["screenshot"])
    except: notify_admins(admin_text, mk)
    del user_data[message.from_user.id]

# ==================== حذف پیج جعلی ====================
@bot.message_handler(func=lambda m: m.text == "🗑 حذف پیج جعلی")
def fake_start(message):
    user_data[message.from_user.id] = {"service": "🗑 حذف پیج جعلی/آزاردهنده", "step": "fake_reason"}
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=1)
    mk.add("👤 جعل هویت (پیج فیک از من)", "😡 آزار و اذیت", "📸 سوءاستفاده از عکس‌هام", "🔙 بازگشت به منو")
    bot.send_message(message.chat.id,
        f"🗑 *حذف پیج جعلی / آزاردهنده*\n"
        f"{SEP}\n\n"
        "📌 *موارد قابل پیگیری:*\n\n"
        "✔️ پیج‌هایی که جعل هویت می‌کنن\n"
        "✔️ پیج‌هایی که آزار و اذیت می‌کنن\n"
        "✔️ پیج‌هایی که از عکس‌هات سوءاستفاده کردن\n"
        "✔️ پیج‌های تهدیدآمیز\n\n"
        f"{SEP}\n"
        "📝 *مرحله ۱ از ۵*\n\n"
        "🔹 دلیل درخواست حذف رو انتخاب کن:",
        parse_mode="Markdown", reply_markup=mk)

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "fake_reason")
def fake_reason(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"reason": message.text, "step": "fake_target"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۲ از ۵*\n\n"
        "🎯 آیدی پیجی که میخوای حذف بشه رو بفرست:",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "fake_target")
def fake_target(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"target_id": message.text, "step": "fake_original"})
    reason = user_data[message.from_user.id].get("reason", "")
    if "جعل هویت" in reason:
        bot.send_message(message.chat.id,
            "📝 *مرحله ۳ از ۵*\n\n"
            "✅ آیدی پیج اصلی خودت رو بفرست:\n"
            "_(پیجی که از اسم یا هویتش کپی شده)_",
            parse_mode="Markdown")
    else:
        user_data[message.from_user.id].update({"original_id": "---", "step": "fake_desc"})
        bot.send_message(message.chat.id,
            "📝 *مرحله ۳ از ۵*\n\n"
            "📋 توضیح کامل بده چه آزار و اذیتی صورت گرفته:",
            parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "fake_original")
def fake_original(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"original_id": message.text, "step": "fake_desc"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۴ از ۵*\n\n"
        "📋 توضیح کامل بده چه اتفاقی افتاده:",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "fake_desc")
def fake_desc(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"desc": message.text, "step": "fake_proof"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۵ از ۵*\n\n"
        "🔐 *تأیید هویت*\n\n"
        "برای اطمینان از صاحب اصلی چهره/پیج، یکی از موارد زیر رو بفرست:\n\n"
        "✔️ عکس کارت ملی یا پاسپورت\n"
        "✔️ اسکرین‌شات از پیج اصلی خودت\n\n"
        "⚠️ _اطلاعات شما محرمانه می‌ماند_",
        parse_mode="Markdown")

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "fake_proof")
def fake_proof(message):
    d = user_data[message.from_user.id]; d["proof"] = message.photo[-1].file_id
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id,
        f"✅ *سفارش #{order['id']} با موفقیت ثبت شد!*\n"
        f"{SEP}\n\n"
        "🔍 تیم ما بررسی می‌کنه و:\n"
        "💰 هزینه رو اعلام می‌کنیم\n"
        "⏰ زمان مورد نیاز رو می‌گیم\n\n"
        "🕐 *پاسخ: کمتر از ۲۴ ساعت*",
        parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_action_markup(u.id, order["id"])
    admin_text = (
        f"🔔 *اعلان سفارش جدید — #{order['id']}*\n"
        f"🗑 *حذف پیج جعلی/آزاردهنده*\n"
        f"{SEP}\n\n"
        f"👤 *کاربر:* {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n\n"
        f"⚠️ *دلیل:* {d.get('reason')}\n"
        f"🎯 *پیج هدف:* {d.get('target_id')}\n"
        f"✅ *پیج اصلی:* {d.get('original_id')}\n"
        f"📝 *توضیحات:* {d.get('desc')}\n"
        f"🕐 *زمان:* {order['time']}\n"
        f"{SEP}\n"
        "🔗 *فرم‌های پیشنهادی:*\n"
        "• help.instagram.com/contact/636276399721841 (جعل هویت)\n"
        "• help.instagram.com/547601325292351 (آزار)\n"
        "• help.instagram.com/contact/372592039493026 (تخلف)\n"
        "• help.instagram.com/contact/230197320740525 (علامت تجاری)"
        f"\n\n{SEP}\n"
        + admin_order_extra(d["service"], d)
    )
    notify_admins(admin_text, mk, d["proof"])
    del user_data[message.from_user.id]

# ==================== پریمیوم تلگرام ====================
@bot.message_handler(func=lambda m: m.text == "✈️ پریمیوم تلگرام")
def premium_start(message):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("3️⃣ ماهه  —  17$", callback_data="pr_3"),
        types.InlineKeyboardButton("6️⃣ ماهه  —  21$", callback_data="pr_6"),
        types.InlineKeyboardButton("1️⃣ ساله   —  34$", callback_data="pr_12"),
        types.InlineKeyboardButton("🔙 بازگشت به منو", callback_data="pr_back")
    )
    bot.send_message(message.chat.id,
        f"✈️ *پریمیوم تلگرام*\n"
        f"{SEP}\n\n"
        "🌟 *مزایای اشتراک پریمیوم:*\n\n"
        "✔️ آپلود فایل تا ۴ گیگابایت\n"
        "✔️ استیکر و ری‌اکشن‌های انحصاری\n"
        "✔️ پروفایل ویدیویی انیمیشن\n"
        "✔️ سرعت دانلود ۴ برابر بیشتر\n"
        "✔️ بدون تبلیغات\n"
        "✔️ مدیریت ۱۰ اکانت همزمان\n"
        "✔️ ترجمه پیام‌ها\n\n"
        f"{SEP}\n"
        "💰 *قیمت‌ها به دلار:*\n\n"
        "👇 پلن مورد نظرت رو انتخاب کن:",
        parse_mode="Markdown", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pr_"))
def premium_plan(call):
    if call.data == "pr_back":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        main_menu(call.message.chat.id); return
    pm = {"pr_3": ("3 ماهه", 17), "pr_6": ("6 ماهه", 21), "pr_12": ("1 ساله", 34)}
    name, dollar = pm[call.data]
    user_data[call.from_user.id] = {"service": f"✈️ پریمیوم {name}", "plan": name, "dollar": dollar, "amount": dollar, "step": "pr_receipt"}
    bot.edit_message_text(
        f"✈️ *پریمیوم {name}  —  {dollar}$*\n"
        f"{SEP}\n\n"
        "💳 *اطلاعات پرداخت:*\n\n"
        f"🏦 بانک: {CARD_BANK}\n"
        f"👤 صاحب کارت: {CARD_OWNER}\n\n"
        "💳 *شماره کارت:*\n"
        f"`{CARD_NUM}`\n\n"
        f"💰 *مبلغ: {dollar}$*\n"
        "_(قیمت روز دلار رو ضربدر مبلغ کنید و به تومان واریز کنید)_\n\n"
        f"{SEP}\n"
        "📝 *مرحله ۱ از ۳*\n\n"
        "📸 بعد از واریز، عکس رسید رو بفرست:",
        call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "pr_receipt")
def pr_receipt(message):
    user_data[message.from_user.id].update({"receipt": message.photo[-1].file_id, "step": "pr_tgid"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۲ از ۳*\n\n"
        "📱 آیدی تلگرامی که میخوای پریمیوم روش فعال بشه:\n"
        "_(مثال: @username)_",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "pr_tgid")
def pr_tgid(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"tg_id": message.text, "step": "pr_phone"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۳ از ۳*\n\n"
        "📞 شماره تلفن اون حساب تلگرام رو بفرست:",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "pr_phone")
def pr_phone(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    d = user_data[message.from_user.id]; d["tg_phone"] = message.text
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id,
        f"✅ *سفارش #{order['id']} با موفقیت ثبت شد!*\n"
        f"{SEP}\n\n"
        "🔍 رسید پرداخت بررسی میشه.\n"
        "✈️ بعد از تأیید، پریمیوم فعال میشه.\n"
        "⏰ *زمان فعال‌سازی: کمتر از ۲ ساعت*",
        parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_action_markup(u.id, order["id"])
    admin_text = (
        f"🔔 *اعلان سفارش جدید — #{order['id']}*\n"
        f"✈️ *{d.get('service')}*\n"
        f"{SEP}\n\n"
        f"👤 *کاربر:* {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n\n"
        f"📱 *آیدی تلگرام:* {d.get('tg_id')}\n"
        f"📞 *شماره:* {d.get('tg_phone')}\n"
        f"💰 *مبلغ:* {d.get('amount')}$\n"
        f"🕐 *زمان:* {order['time']}"
    )
    notify_admins(admin_text, mk, d["receipt"])
    del user_data[message.from_user.id]

# ==================== فالوور ====================
@bot.message_handler(func=lambda m: m.text == "👥 خرید فالوور")
def follower(message):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("🛒 ثبت سفارش فالوور", url=FOLLOWER_LINK))
    bot.send_message(message.chat.id,
        f"👥 *خرید فالوور اینستاگرام*\n"
        f"{SEP}\n\n"
        "📌 *انواع فالوور:*\n\n"
        "🇮🇷 فالوور ایرانی واقعی\n"
        "🌍 فالوور خارجی\n"
        "🔀 فالوور میکس\n\n"
        "💎 *ویژگی‌ها:*\n\n"
        "✔️ ریزش کمتر از ۵٪\n"
        "✔️ شروع سریع (۱ تا ۶ ساعت)\n"
        "✔️ قیمت رقابتی\n"
        "✔️ پشتیبانی کامل\n"
        "✔️ بدون نیاز به پسورد\n\n"
        f"{SEP}\n"
        "👇 برای ثبت سفارش:",
        parse_mode="Markdown", reply_markup=mk)

# ==================== شماره مجازی ====================
@bot.message_handler(func=lambda m: m.text == "📱 شماره مجازی")
def number(message):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("📱 ربات خرید شماره مجازی", url=NUMBER_BOT))
    bot.send_message(message.chat.id,
        f"📱 *خرید شماره مجازی*\n"
        f"{SEP}\n\n"
        "📌 *کاربردها:*\n\n"
        "✔️ ساخت اکانت اینستاگرام\n"
        "✔️ ساخت اکانت تلگرام\n"
        "✔️ دریافت کد OTP\n"
        "✔️ ثبت‌نام در سایت‌های خارجی\n"
        "✔️ تأیید هویت آنلاین\n\n"
        "🌍 *شماره‌های موجود:*\n"
        "ایران، روسیه، آمریکا، اروپا و...\n\n"
        f"{SEP}\n"
        "👇 برای خرید:",
        parse_mode="Markdown", reply_markup=mk)

# ==================== امنیت پیج ====================
@bot.message_handler(func=lambda m: m.text == "🛡 امنیت پیج")
def sec_start(message):
    user_data[message.from_user.id] = {"service": "🛡 امنیت پیج", "step": "sec_id"}
    bot.send_message(message.chat.id,
        f"🛡 *امنیت پیج اینستاگرام*\n"
        f"{SEP}\n\n"
        "📌 *خدمات امنیتی ما:*\n\n"
        "✔️ بررسی کامل سطح امنیت پیج\n"
        "✔️ هک‌پروف کردن اکانت\n"
        "✔️ فعال‌سازی تأیید دو مرحله‌ای\n"
        "✔️ بررسی و قطع دسترسی‌های مشکوک\n"
        "✔️ آموزش جلوگیری از هک\n"
        "✔️ محافظت از پیج در برابر ریپورت\n\n"
        f"{SEP}\n"
        "📝 *مرحله ۱ از ۳*\n\n"
        "🔹 آیدی پیجت رو بفرست:",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "sec_id")
def sec_id(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"ig_id": message.text, "step": "sec_followers"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۲ از ۳*\n\n"
        "👥 تعداد فالوور پیجت رو بنویس:",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "sec_followers")
def sec_followers(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"followers": message.text, "step": "sec_topic"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۳ از ۳*\n\n"
        "📌 موضوع پیجت چیه؟",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "sec_topic")
def sec_topic(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    d = user_data[message.from_user.id]; d["topic"] = message.text
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id,
        f"✅ *سفارش #{order['id']} با موفقیت ثبت شد!*\n"
        f"{SEP}\n\n"
        "🔍 تیم ما پیجت رو بررسی می‌کنه.\n"
        "💰 هزینه و شرایط رو اعلام می‌کنیم.\n"
        "⏰ *پاسخ: کمتر از ۲۴ ساعت*",
        parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_action_markup(u.id, order["id"])
    admin_text = (
        f"🔔 *اعلان سفارش جدید — #{order['id']}*\n"
        f"🛡 *امنیت پیج*\n"
        f"{SEP}\n\n"
        f"👤 *کاربر:* {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n\n"
        f"📸 *پیج:* {d.get('ig_id')}\n"
        f"👥 *فالوور:* {d.get('followers')}\n"
        f"📌 *موضوع:* {d.get('topic')}\n"
        f"🕐 *زمان:* {order['time']}\n\n"
        f"🧠 *خلاصه:* درخواست بررسی امنیتی برای پیج {d.get('ig_id')} با موضوع {d.get('topic')}."
    )
    notify_admins(admin_text, mk)
    del user_data[message.from_user.id]

# ==================== ادیت و طراحی ====================
@bot.message_handler(func=lambda m: m.text == "🎨 ادیت و طراحی")
def des_start(message):
    user_data[message.from_user.id] = {"service": "🎨 ادیت و طراحی", "step": "des_topic"}
    bot.send_message(message.chat.id,
        f"🎨 *ادیت و طراحی محتوای حرفه‌ای*\n"
        f"{SEP}\n\n"
        "📌 *خدمات ما:*\n\n"
        "✔️ طراحی پست و استوری\n"
        "✔️ ادیت ویدیو و ریلز\n"
        "✔️ طراحی بنر و پوستر\n"
        "✔️ ساخت تیزر تبلیغاتی\n"
        "✔️ طراحی لوگو و برندینگ\n"
        "✔️ طراحی هایلایت\n\n"
        f"{SEP}\n"
        "📝 *مرحله ۱ از ۳*\n\n"
        "🔹 موضوع محتوای مورد نظرت رو بنویس:",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "des_topic")
def des_topic(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"topic": message.text, "step": "des_type"})
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=3)
    mk.add("🖼 پست/استوری","🎬 ویدیو/ریلز","🖌 بنر","📋 پوستر","📺 تیزر","🎯 لوگو","🔙 بازگشت به منو")
    bot.send_message(message.chat.id,
        "📝 *مرحله ۲ از ۳*\n\n"
        "🎯 نوع محتوا رو انتخاب کن:",
        parse_mode="Markdown", reply_markup=mk)

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "des_type")
def des_type(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"content_type": message.text, "step": "des_desc"})
    bot.send_message(message.chat.id,
        "📝 *مرحله ۳ از ۳*\n\n"
        "📋 توضیح کامل بده:\n\n"
        "🔹 رنگ و استایل مورد نظر\n"
        "🔹 متن و محتوای دلخواه\n"
        "🔹 ابعاد یا فرمت خاص\n"
        "🔹 هر جزئیات دیگه‌ای",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "des_desc")
def des_desc(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    d = user_data[message.from_user.id]; d["desc"] = message.text
    u = message.from_user; order = add_order(u, d["service"], d)
    bot.send_message(message.chat.id,
        f"📋 *خلاصه سفارش #{order['id']}*\n"
        f"{SEP}\n\n"
        f"📌 موضوع: {d.get('topic')}\n"
        f"🎯 نوع: {d.get('content_type')}\n"
        f"📝 توضیحات: {d.get('desc')}\n\n"
        f"{SEP}\n"
        f"✉️ این لیست رو به {DESIGN_ADMIN} ارسال کن.\n"
        "تیم ادیت قیمت و شرایط رو اعلام می‌کنه 🎨",
        parse_mode="Markdown")
    main_menu(message.chat.id)
    mk = order_action_markup(u.id, order["id"])
    admin_text = (
        f"🔔 *اعلان سفارش جدید — #{order['id']}*\n"
        f"🎨 *ادیت و طراحی*\n"
        f"{SEP}\n\n"
        f"👤 *کاربر:* {u.first_name} | @{u.username or 'ندارد'} | `{u.id}`\n\n"
        f"📌 *موضوع:* {d.get('topic')}\n"
        f"🎯 *نوع:* {d.get('content_type')}\n"
        f"📝 *توضیحات:* {d.get('desc')}\n"
        f"🕐 *زمان:* {order['time']}"
    )
    notify_admins(admin_text, mk)
    del user_data[message.from_user.id]

# ==================== ایده محتوایی ====================
@bot.message_handler(func=lambda m: m.text == "💡 ایده محتوایی")
def idea_start(message):
    user_data[message.from_user.id] = {"step": "idea_topic"}
    bot.send_message(message.chat.id,
        f"💡 *ایده‌پردازی محتوا*\n"
        f"{SEP}\n\n"
        "🎁 *این سرویس کاملاً رایگانه!*\n\n"
        "موضوع پیج یا پستت رو بنویس تا ایده‌های محتوایی بهت بدیم 👇\n\n"
        "_(مثال: فروش لباس، آموزش آشپزی، فیتنس، روانشناسی)_",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "idea_topic")
def idea_generate(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    topic = message.text
    bot.send_message(message.chat.id,
        f"💡 *ایده‌های محتوایی برای «{topic}»*\n"
        f"{SEP}\n\n"
        "📸 *ایده برای پست:*\n\n"
        f"🔹 قبل و بعد مرتبط با {topic}\n"
        f"🔹 پشت‌صحنه کار در حوزه {topic}\n"
        f"🔹 ۵ نکته طلایی درباره {topic}\n"
        f"🔹 معرفی خدمات با استوری‌تلینگ\n"
        f"🔹 سوال از مخاطب درباره {topic}\n\n"
        f"{SEP}\n"
        "🎬 *ایده برای ریلز:*\n\n"
        f"🔹 یه روز کاری در حوزه {topic}\n"
        f"🔹 ۳ اشتباه رایج در {topic}\n"
        f"🔹 آموزش سریع مرتبط با {topic}\n"
        f"🔹 چالش ترند با موضوع {topic}\n\n"
        f"{SEP}\n"
        "📊 *ایده برای استوری:*\n\n"
        "🔹 پرسش و پاسخ با مخاطبان\n"
        "🔹 نظرسنجی تعاملی\n"
        "🔹 اعلام تخفیف یا آفر ویژه\n"
        "🔹 پشت‌صحنه لحظه‌ای\n\n"
        f"{SEP}\n"
        "📅 *تقویم محتوایی پیشنهادی:*\n\n"
        "• شنبه: 📚 آموزشی\n"
        "• یکشنبه: 🎬 ریلز\n"
        "• دوشنبه: 💬 تعاملی\n"
        "• سه‌شنبه: 🛍 معرفی محصول\n"
        "• چهارشنبه: 🎉 سرگرمی\n"
        "• پنجشنبه: 🌟 انگیزشی\n\n"
        "💬 برای ایده‌های اختصاصی‌تر با @tarvideh تماس بگیر!",
        parse_mode="Markdown")
    del user_data[message.from_user.id]
    main_menu(message.chat.id)

# ==================== کانال و پشتیبانی ====================
# ==================== سفارشات من ====================
@bot.message_handler(func=lambda m: m.text == "📦 سفارشات من")
def my_orders(message):
    uid = message.from_user.id
    my = [o for o in orders_db if o["user_id"] == uid]
    if not my:
        bot.send_message(message.chat.id,
            f"📦 *سفارشات من*\n{SEP}\n\n"
            "📭 هنوز هیچ سفارشی ثبت نکردی.\n\n"
            "برای ثبت سفارش از منو اقدام کن 👇",
            parse_mode="Markdown", reply_markup=back_btn())
        return

    bot.send_message(message.chat.id,
        f"📦 *سفارشات من*\n{SEP}\n\n"
        f"📊 تعداد کل سفارشات: *{len(my)}*\n\n"
        "برای مشاهده وضعیت هر سفارش روی دکمه‌اش بزن 👇",
        parse_mode="Markdown", reply_markup=back_btn())

    for o in my[-5:]:
        status_icon = {"pending":"⏳","reviewing":"🔍","processing":"⚙️","done":"✅","cancelled":"❌"}.get(o["status"],"❓")
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton(f"📊 وضعیت سفارش #{o['id']}", callback_data=f"myorder_{o['id']}"))
        bot.send_message(message.chat.id,
            f"{status_icon} *سفارش #{o['id']}*\n"
            f"🛒 {o['service']}\n"
            f"📊 {STATUS.get(o['status'])}\n"
            f"🕐 {o['time']}",
            parse_mode="Markdown", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("myorder_"))
def show_my_order(call):
    oid = int(call.data.replace("myorder_", ""))
    order = next((o for o in orders_db if o["id"] == oid and o["user_id"] == call.from_user.id), None)
    if not order:
        bot.answer_callback_query(call.id, "❌ سفارش پیدا نشد."); return
    chart = order_status_chart(order)
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"myorder_{oid}"))
    bot.send_message(call.message.chat.id, chart, parse_mode="Markdown", reply_markup=mk)
    bot.answer_callback_query(call.id, "✅ وضعیت سفارش")

# ==================== پروفایل من ====================
@bot.message_handler(func=lambda m: m.text == "👤 پروفایل من")
def my_profile(message):
    u = message.from_user
    uid = u.id
    my_orders_list = [o for o in orders_db if o["user_id"] == uid]
    total = len(my_orders_list)
    done_count = len([o for o in my_orders_list if o["status"] == "done"])
    pending_count = len([o for o in my_orders_list if o["status"] == "pending"])
    processing_count = len([o for o in my_orders_list if o["status"] in ("reviewing","processing")])
    cancelled_count = len([o for o in my_orders_list if o["status"] == "cancelled"])
    first_order = my_orders_list[0]["time"] if my_orders_list else "---"
    last_order = my_orders_list[-1]["time"] if my_orders_list else "---"

    bot.send_message(message.chat.id,
        f"👤 *پروفایل من*\n{SEP}\n\n"
        f"🏷 *نام:* {u.first_name} {u.last_name or ''}\n"
        f"📱 *یوزرنیم:* @{u.username or 'ندارد'}\n"
        f"🆔 *آیدی:* `{uid}`\n\n"
        f"{SEP}\n"
        f"📊 *آمار سفارشات:*\n\n"
        f"📦 کل سفارشات: *{total}*\n"
        f"✅ تکمیل‌شده: *{done_count}*\n"
        f"⚙️ در حال انجام: *{processing_count}*\n"
        f"⏳ در انتظار: *{pending_count}*\n"
        f"❌ لغو‌شده: *{cancelled_count}*\n\n"
        f"{SEP}\n"
        f"🗓 *اولین سفارش:* {first_order}\n"
        f"🕐 *آخرین سفارش:* {last_order}\n\n"
        f"{SEP}\n"
        "📞 *پشتیبانی:* @tarvideh\n"
        f"📢 *کانال:* {CHANNEL}",
        parse_mode="Markdown", reply_markup=back_btn())

# ==================== تشخیص هوشمند مشکل ====================
def ai_diagnose(user_description):
    """ارسال توضیح کاربر به Groq API و دریافت تشخیص هوشمند (رایگان)"""
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        prompt = f"""تو یک متخصص بازیابی و امنیت اینستاگرام هستی که برای یک شرکت ایرانی به نام ترویده کار می‌کنی.

کاربر این مشکل را توضیح داده:
{user_description}

لطفاً به فارسی و کاملاً حرفه‌ای:
1. **نوع مشکل:** دقیقاً بگو مشکل چیه (دیسیبل، محدودیت، هک، جعل هویت و...)
2. **احتمال حل:** یه عدد از ۰ تا ۱۰۰ درصد بده و توضیح بده چرا
3. **دلیل احتمالی:** چرا این اتفاق افتاده
4. **اقدام فوری:** ۳ کار که کاربر باید همین الان انجام بده
5. **خدمت پیشنهادی ترویده:** کدام سرویس ما مناسبه (بازگردانی، رفع محدودیت، امنیت پیج، حذف پیج جعلی)
6. **هشدار:** اگه کاری هست که نباید انجام بده

پاسخ رو کوتاه، واضح و کاربردی بده. از ایموجی استفاده کن."""

        payload = {
            "model": "llama-3.3-70b-versatile",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "system",
                    "content": "تو یک متخصص حرفه‌ای امنیت و بازیابی اینستاگرام هستی. پاسخ‌هایت باید دقیق، کاربردی و به فارسی باشد."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers, json=payload, timeout=30
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            print(f"Groq error: {r.status_code} - {r.text}")
            return None
    except Exception as e:
        print(f"AI error: {e}")
        return None

@bot.message_handler(func=lambda m: m.text == "🤖 تشخیص هوشمند مشکل")
def ai_start(message):
    user_data[message.from_user.id] = {"step": "ai_describe"}
    bot.send_message(message.chat.id,
        f"🤖 *تشخیص هوشمند مشکل اینستاگرام*\n"
        f"{SEP}\n\n"
        "✨ *این سرویس کاملاً رایگانه!*\n\n"
        "📌 *چطور کار می‌کنه؟*\n"
        "مشکل پیجت رو به زبان ساده توضیح بده — هوش مصنوعی ما:\n\n"
        "✔️ نوع دقیق مشکل رو تشخیص میده\n"
        "✔️ احتمال حل شدن رو میگه\n"
        "✔️ دلیل اتفاق رو توضیح میده\n"
        "✔️ اقدامات فوری رو پیشنهاد میده\n"
        "✔️ بهترین سرویس ترویده رو معرفی میکنه\n\n"
        f"{SEP}\n\n"
        "📝 *مشکلت رو اینجا بنویس:*\n\n"
        "_(مثال: پیجم دیروز دیسیبل شد، ۵۰ هزار فالوور داشت، "
        "قبلاً هیچ اخطاری نگرفته بودم و نمیدونم چرا...)_",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "ai_describe")
def ai_analyze(message):
    if message.text == "🔙 بازگشت به منو":
        go_back(message); return

    description = message.text
    if len(description) < 20:
        bot.send_message(message.chat.id,
            "⚠️ توضیحات خیلی کوتاهه!\n\n"
            "لطفاً مشکلت رو کامل‌تر توضیح بده تا بتونیم بهتر تشخیص بدیم.",
            reply_markup=back_btn())
        return

    # پیام در حال تحلیل
    wait_msg = bot.send_message(message.chat.id,
        "🤖 *در حال تحلیل مشکل شما...*\n\n"
        "⏳ هوش مصنوعی داره بررسی می‌کنه، چند ثانیه صبر کن...",
        parse_mode="Markdown")

    import threading
    def do_analysis():
        result = ai_diagnose(description)

        try:
            bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass

        if result:
            mk = types.InlineKeyboardMarkup(row_width=1)
            mk.add(
                types.InlineKeyboardButton("🔄 ثبت سفارش بازگردانی", callback_data="quick_order_disable"),
                types.InlineKeyboardButton("🚫 ثبت سفارش رفع محدودیت", callback_data="quick_order_limit"),
                types.InlineKeyboardButton("🛡 ثبت سفارش امنیت پیج", callback_data="quick_order_security"),
                types.InlineKeyboardButton("💬 مشاوره با تیم ترویده", url="https://t.me/tarvideh"),
            )
            bot.send_message(message.chat.id,
                f"🤖 *نتیجه تشخیص هوشمند*\n"
                f"{SEP}\n\n"
                f"{result}\n\n"
                f"{SEP}\n"
                "👇 *برای ثبت سفارش یا مشاوره:*",
                parse_mode="Markdown", reply_markup=mk)

            # گزارش به ادمین
            for aid in ADMINS:
                try:
                    bot.send_message(aid,
                        f"🤖 *تشخیص هوشمند جدید*\n"
                        f"{SEP}\n\n"
                        f"👤 {message.from_user.first_name} | @{message.from_user.username or 'ندارد'} | `{message.from_user.id}`\n\n"
                        f"📝 *توضیح کاربر:*\n{description}\n\n"
                        f"{SEP}\n"
                        f"🤖 *تشخیص AI:*\n{result}",
                        parse_mode="Markdown")
                except: pass
        else:
            # اگه AI جواب نداد، تشخیص دستی
            mk = types.InlineKeyboardMarkup()
            mk.add(types.InlineKeyboardButton("💬 مشاوره با کارشناس", url="https://t.me/tarvideh"))
            bot.send_message(message.chat.id,
                f"⚠️ *سیستم هوشمند موقتاً در دسترس نیست*\n"
                f"{SEP}\n\n"
                "نگران نباش! کارشناسان ما میتونن مشکلت رو بررسی کنن.\n\n"
                "📞 همین الان با تیم ترویده در ارتباط باش:",
                parse_mode="Markdown", reply_markup=mk)

        del user_data[message.from_user.id]
        main_menu(message.chat.id)

    threading.Thread(target=do_analysis, daemon=True).start()

@bot.callback_query_handler(func=lambda c: c.data.startswith("quick_order_"))
def quick_order(call):
    mapping = {
        "quick_order_disable": "🔄 بازگردانی پیج دیسیبل",
        "quick_order_limit": "🚫 رفع محدودیت",
        "quick_order_security": "🛡 امنیت پیج"
    }
    service = mapping.get(call.data, "")
    if service:
        bot.send_message(call.message.chat.id,
            f"✅ برای ثبت سفارش *{service}* از منو اقدام کن 👇",
            parse_mode="Markdown")
        main_menu(call.message.chat.id)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.text == "📢 کانال ما")
def channel(message):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("📢 ورود به کانال رسمی ترویده", url=f"https://t.me/{CHANNEL.replace('@','')}"))
    bot.send_message(message.chat.id,
        f"📢 *کانال رسمی ترویده*\n"
        f"{SEP}\n\n"
        "✨ در کانال ما چی پیدا می‌کنی؟\n\n"
        "✔️ آخرین اخبار و آپدیت‌ها\n"
        "✔️ تخفیف‌های ویژه\n"
        "✔️ نمونه کارهای موفق\n"
        "✔️ آموزش‌های رایگان\n"
        "✔️ جوایز و مسابقات\n\n"
        "👇 همین الان عضو شو:",
        parse_mode="Markdown", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support(message):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("💬 تماس مستقیم با پشتیبانی", url="https://t.me/tarvideh"))
    bot.send_message(message.chat.id,
        f"📞 *پشتیبانی ترویده*\n"
        f"{SEP}\n\n"
        "🌐 *راه‌های ارتباطی:*\n\n"
        "📱 تلگرام: @tarvideh\n"
        f"📢 کانال: {CHANNEL}\n"
        "🌍 سایت: tarvideh.com\n\n"
        f"{SEP}\n"
        "⏰ *ساعات پاسخگویی:* ۲۴ ساعته، ۷ روز هفته\n\n"
        "👇 برای تماس مستقیم:",
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
            f"✏️ پیامت رو برای کاربر `{target}` بنویس:",
            parse_mode="Markdown")
        bot.answer_callback_query(call.id)
    elif action == "reject":
        try:
            bot.send_message(target,
                f"❌ *سفارش شما رد شد*\n"
                f"{SEP}\n\n"
                "متأسفانه سفارش شما در این مرحله قابل پردازش نیست.\n\n"
                "📞 برای اطلاعات بیشتر:\n@tarvideh",
                parse_mode="Markdown")
        except: pass
        bot.answer_callback_query(call.id, "❌ رد شد.")

@bot.message_handler(func=lambda m: f"admin_reply_{m.from_user.id}" in user_data)
def send_reply(message):
    target = user_data[f"admin_reply_{message.from_user.id}"]
    try:
        bot.send_message(target,
            f"📩 *پیام از تیم ترویده*\n"
            f"{SEP}\n\n"
            f"{message.text}")
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
                f"📢 *پیام رسمی از ترویده*\n"
                f"{SEP}\n\n"
                f"{message.text}")
            sent += 1
        except: pass
    bot.send_message(message.chat.id, f"✅ پیام به *{sent}* کاربر ارسال شد.", parse_mode="Markdown")
    del user_data[message.from_user.id]
    main_menu(message.chat.id)

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("🔄 تازه‌سازی داشبورد", "🔄 تازه‌سازی سفارشات"))
def refresh_orders(message):
    admin_dashboard(message.chat.id, message.from_user.first_name, show_pending=True)

print("✅ ربات ترویده آماده‌ست...")
bot.infinity_polling(skip_pending=True)
