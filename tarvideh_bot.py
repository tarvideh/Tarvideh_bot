import telebot
from telebot import types
from datetime import datetime
import requests
import sqlite3
import smtplib
import os
import shutil
import time
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from html import escape

# ==================== تنظیمات ====================
BOT_TOKEN = "8811093114:AAFBtc-JOkFMEvdgMOgCklGxuPNUXnd6YDM"
ADMINS = [634374331]
OWNER_ID = 634374331
CHANNEL = "@tarvideh1"
CARD_NUM = "6104-3387-7176-8823"
CARD_OWNER = "شایان ترویده"
CARD_BANK = "بانک ملت"
DESIGN_ADMIN = "@Tarvideh_Edit"
NUMBER_BOT = "https://t.me/tarvidehnumber_bot"
FOLLOWER_LINK = "https://tarvideh.com/#add_orderbox"

# ==================== تنظیمات ایمیل ====================
EMAIL_SENDER = "Tarvideh8@gmail.com"
EMAIL_PASSWORD = "obhhjwndxfwzrhxp"

# ==================== تنظیمات هوش مصنوعی ====================
GROQ_API_KEY = "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"

# ==================== تنظیمات بک‌آپ ====================
BACKUP_DIR = "backups"
BACKUP_INTERVAL_HOURS = 12
BACKUP_KEEP_LOCAL = 30
BACKUP_CHANNEL = "@tarvideh1"
# ======================================================

runtime_config = {
    "email_password": EMAIL_PASSWORD,
    "groq_key": GROQ_API_KEY,
}

# ==================== لیست ایمیل‌های مبدا ====================
# هر آیتم: {"email": "...", "label": "...", "active": True/False}
email_senders = [
    {"email": EMAIL_SENDER, "label": "ایمیل اصلی ترویده", "active": True}
]
# ایمیل فعال فعلی (آیندکس در email_senders)
active_sender_index = 0

bot = telebot.TeleBot(BOT_TOKEN, use_class_middlewares=True)
user_data = {}
DB_FILE = "tarvideh_orders.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, user_name TEXT, username TEXT,
        service TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL,
        status TEXT NOT NULL, history TEXT NOT NULL, admin_note TEXT DEFAULT ''
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        username TEXT,
        first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL,
        orders_count INTEGER DEFAULT 0
    )""")
    conn.commit(); conn.close()

def upsert_user(user, bump_orders=False):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn = sqlite3.connect(DB_FILE)
        if bump_orders:
            conn.execute("""
                INSERT INTO users (user_id, first_name, last_name, username, first_seen, last_seen, orders_count)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    username=excluded.username,
                    last_seen=excluded.last_seen,
                    orders_count=orders_count+1
            """, (user.id, user.first_name, user.last_name or "", user.username or "", now, now))
        else:
            conn.execute("""
                INSERT INTO users (user_id, first_name, last_name, username, first_seen, last_seen, orders_count)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(user_id) DO UPDATE SET
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    username=excluded.username,
                    last_seen=excluded.last_seen
            """, (user.id, user.first_name, user.last_name or "", user.username or "", now, now))
        conn.commit(); conn.close()
    except Exception as e:
        print(f"upsert_user error: {e}")

def load_users():
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM users ORDER BY last_seen DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except:
        return []

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
def is_owner(uid): return uid == OWNER_ID

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
    upsert_user(user, bump_orders=True)
    return o

# ==================== بک‌آپ خودکار ====================
def backup_database():
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        now_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
        backup_path = os.path.join(BACKUP_DIR, f"tarvideh_backup_{now_str}.db")

        src = sqlite3.connect(DB_FILE)
        dst = sqlite3.connect(backup_path)
        src.backup(dst)
        dst.close(); src.close()

        users_count = len(load_users())
        orders_count = len(load_orders())
        caption = (
            f"🗄 *بک‌آپ ربات ترویده*\n\n"
            f"🕐 زمان: {now_str}\n"
            f"👥 کاربران: {users_count}\n"
            f"📦 سفارشات: {orders_count}"
        )

        sent = False
        if BACKUP_CHANNEL and BACKUP_CHANNEL != "@your_backup_channel":
            try:
                with open(backup_path, 'rb') as f:
                    bot.send_document(BACKUP_CHANNEL, f, caption=caption, parse_mode="Markdown")
                sent = True
            except Exception as e:
                print(f"Backup channel error: {e}")

        if not sent:
            for aid in ADMINS:
                try:
                    with open(backup_path, 'rb') as f:
                        bot.send_document(aid, f, caption=caption, parse_mode="Markdown")
                except: pass

        # حذف نسخه‌های قدیمی
        backups = sorted([
            os.path.join(BACKUP_DIR, f)
            for f in os.listdir(BACKUP_DIR)
            if f.startswith("tarvideh_backup_") and f.endswith(".db")
        ])
        while len(backups) > BACKUP_KEEP_LOCAL:
            try:
                os.remove(backups.pop(0))
            except: pass

        print(f"✅ Backup done: {backup_path}")
    except Exception as e:
        print(f"Backup error: {e}")

def backup_loop():
    backup_database()
    while True:
        time.sleep(BACKUP_INTERVAL_HOURS * 3600)
        backup_database()

threading.Thread(target=backup_loop, daemon=True).start()

# ==================== middleware ردیابی کاربران ====================
class UserTrackerMiddleware(telebot.BaseMiddleware):
    update_types = ['message']
    def pre_process(self, message, data):
        try:
            upsert_user(message.from_user)
        except: pass
    def post_process(self, message, data, exception):
        pass

bot.setup_middleware(UserTrackerMiddleware())

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
    "disable": [
        {
            "title": "📝 متن ۱ — اعتراض رسمی",
            "subject": "Appeal for Disabled Instagram Account - {{username}}",
            "body": """Dear Instagram/Meta Support Team,

I am writing to formally appeal the disabling of my Instagram account.

Account Details:
- Username: {{username}}
- Account Name: {{page_name}}
- Registered Email: {{email}}
- Phone: {{phone}}
- Followers: {{followers}}
- Account Type: {{page_type}}

I believe my account was disabled in error. I have always followed Instagram's Community Guidelines and Terms of Service.

Details of the situation:
{{description}}

I respectfully request that you review my case and restore access to my account. I am happy to provide any additional verification if needed.

Thank you for your time and assistance.

Best regards,
{{page_name}}
{{email}}"""
        },
        {
            "title": "💼 متن ۲ — کسب و کار",
            "subject": "Business Account Disabled - Urgent Appeal - {{username}}",
            "body": """To Whom It May Concern at Instagram/Meta Support,

My Instagram business account {{username}} has been disabled, which is severely impacting my business operations.

Business Account Information:
- Username: {{username}}
- Business Name: {{page_name}}
- Contact Email: {{email}}
- Phone: {{phone}}
- Followers: {{followers}}

This account is essential to my livelihood and business communications. I have not knowingly violated any Instagram policies.

Situation details:
{{description}}

I urgently request an immediate review and reinstatement of my account. I can provide business registration documents or any other verification required.

Respectfully,
{{page_name}}
{{email}}"""
        },
        {
            "title": "🔐 متن ۳ — یکپارچگی حساب (Integrity)",
            "subject": "Account Integrity Appeal - {{username}}",
            "body": """Dear Instagram Trust & Safety Team,

I am reaching out regarding the disabling of my account {{username}} due to an account integrity issue.

Account Information:
- Username: {{username}}
- Name: {{page_name}}
- Email: {{email}}
- Phone: {{phone}}
- Followers: {{followers}}

I want to clarify that:
1. This account is completely authentic and belongs to me personally.
2. I have never used any third-party automation tools, bots, or purchased followers.
3. All activity on this account has been genuine and compliant with your policies.

{{description}}

I respectfully request a manual review of my account. I am willing to complete any identity verification process required.

Thank you,
{{page_name}}
{{email}}"""
        },
        {
            "title": "🆘 متن ۴ — فوری و احساسی",
            "subject": "Urgent: Please Review My Disabled Account - {{username}}",
            "body": """Dear Instagram Support,

I am extremely distressed to find my account {{username}} has been disabled without any prior warning.

My Account:
- Username: {{username}}
- Name: {{page_name}}
- Email: {{email}}
- Followers: {{followers}}

I have invested years building this account and community. This account represents:
- My personal/business identity
- Years of hard work and genuine content
- A community of {{followers}} engaged followers

{{description}}

I sincerely request you to reconsider this decision. I have always acted in good faith and within Instagram's guidelines.

Please restore my account.

With respect,
{{page_name}}
{{email}}"""
        },
        {
            "title": "⚖️ متن ۵ — حقوقی و رسمی",
            "subject": "Formal Appeal Against Account Suspension - {{username}}",
            "body": """Dear Meta/Instagram Legal & Policy Team,

I am formally disputing the suspension of my Instagram account, username: {{username}}.

Account Holder Information:
- Full Name: {{page_name}}
- Username: {{username}}
- Registered Email: {{email}}
- Contact Phone: {{phone}}
- Account Followers: {{followers}}

Grounds for Appeal:
I have not received any prior notice or warning before this account suspension. The suspension appears to violate Instagram's own stated policies regarding fair enforcement.

Statement of Facts:
{{description}}

I formally request:
1. An immediate review of this suspension
2. Clear identification of which specific policy was allegedly violated
3. Restoration of full account access

I reserve all rights available to me under applicable laws and Meta's own Terms of Service.

Sincerely,
{{page_name}}
{{email}}"""
        }
    ],
    "limit": [
        {
            "title": "📝 متن ۱ — رفع محدودیت عمومی",
            "subject": "Request to Remove Account Restrictions - {{username}}",
            "body": """Dear Instagram Support Team,

I am experiencing unexpected restrictions on my Instagram account and kindly request your assistance.

Account Information:
- Username: {{username}}
- Name: {{page_name}}
- Email: {{email}}

Issue Description:
{{description}}

I have been following Instagram's Community Guidelines and have not engaged in any prohibited activities. I believe these restrictions were applied in error.

I respectfully request the removal of these restrictions and restoration of full account functionality.

Thank you for your support.

Best regards,
{{page_name}}
{{email}}"""
        },
        {
            "title": "⚡ متن ۲ — بلاک اکشن",
            "subject": "Action Block Issue on Account {{username}}",
            "body": """Dear Instagram Support,

I am writing about an action block affecting my Instagram account {{username}}.

My Account:
- Username: {{username}}
- Email: {{email}}
- Followers: {{followers}}

The Problem:
{{description}}

I want to clarify that all my account activity is completely genuine. I use Instagram manually without any automation tools or third-party applications.

I kindly request:
1. Investigation of this action block
2. Confirmation of which specific actions triggered this block
3. Removal of the restriction as soon as possible

I appreciate your assistance.

Best regards,
{{page_name}}
{{email}}"""
        },
        {
            "title": "🏷 متن ۳ — محدودیت هشتگ",
            "subject": "Hashtag Restriction Appeal - {{username}}",
            "body": """Dear Instagram Support,

I am experiencing hashtag restrictions on my account {{username}} and need your help.

Account Details:
- Username: {{username}}
- Email: {{email}}
- Followers: {{followers}}

Issue:
{{description}}

All hashtags I use are relevant to my content and comply with Instagram's policies. I have not used any banned or spammy hashtags intentionally.

Please review my account and remove the hashtag restriction.

Thank you,
{{page_name}}
{{email}}"""
        }
    ],
    "fake": [
        {
            "title": "👤 متن ۱ — جعل هویت",
            "subject": "Report: Impersonation Account - {{target_id}}",
            "body": """Dear Instagram Safety Team,

I am reporting an account that is impersonating me and my identity.

My Verified Account:
- Username: {{username}}
- Name: {{page_name}}
- Email: {{email}}

Impersonating Account:
- Username: {{target_id}}

This account is using my name, photos, and identity to deceive people. This is causing serious harm to my reputation and potentially defrauding my followers.

{{description}}

I request immediate action:
1. Removal or suspension of the impersonating account {{target_id}}
2. Investigation of any damage caused

I can provide ID verification or other documentation to confirm my identity.

Best regards,
{{page_name}}
{{email}}"""
        },
        {
            "title": "📸 متن ۲ — سوءاستفاده از تصاویر",
            "subject": "Copyright & Privacy Violation - Unauthorized Use of Images - {{target_id}}",
            "body": """Dear Instagram Copyright & Safety Team,

I am reporting a serious violation involving unauthorized use of my personal photos.

My Account:
- Username: {{username}}
- Name: {{page_name}}
- Email: {{email}}

Violating Account:
- Username: {{target_id}}

This account has been using my personal photos without my permission. This constitutes a violation of both copyright law and Instagram's policies on privacy and intellectual property.

Details:
{{description}}

I request:
1. Immediate removal of my photos from account {{target_id}}
2. Appropriate action against this account for policy violations

Thank you for protecting creator rights on your platform.

Sincerely,
{{page_name}}
{{email}}"""
        },
        {
            "title": "😡 متن ۳ — آزار و اذیت",
            "subject": "Report: Harassment and Bullying - {{target_id}}",
            "body": """Dear Instagram Trust & Safety Team,

I am reporting an account that has been engaging in harassment and harmful behavior toward me.

My Account:
- Username: {{username}}
- Name: {{page_name}}
- Email: {{email}}

Harassing Account:
- Username: {{target_id}}

Nature of Harassment:
{{description}}

This behavior is causing me significant emotional distress and violates Instagram's Community Guidelines on harassment and bullying.

I urgently request:
1. Immediate investigation of account {{target_id}}
2. Removal of all harassing content
3. Appropriate sanctions against this account

Please take prompt action to ensure my safety on your platform.

Best regards,
{{page_name}}
{{email}}"""
        }
    ]
}

# ==================== سیستم مرور قالب‌ها ====================
def get_template(em_type, index=0):
    templates = EMAIL_TEMPLATES.get(em_type, EMAIL_TEMPLATES["disable"])
    idx = index % len(templates)
    return templates[idx], idx, len(templates)

def make_template_preview(em_type, index, fill_data):
    template, idx, total = get_template(em_type, index)
    subject, body = fill_template(template["body"], fill_data)
    subject = fill_template_str(template["subject"], fill_data)
    return template["title"], subject, body, idx, total

def fill_template_str(text, data):
    for key, value in data.items():
        text = text.replace(f"{{{{{key}}}}}", str(value or "---"))
    return text

def send_email(to_email, subject, body):
    """ارسال ایمیل با Gmail و برگرداندن خطای واقعی برای تشخیص مشکل."""
    server = None
    try:
        if not EMAIL_SENDER or '@' not in EMAIL_SENDER:
            return False, "EMAIL_SENDER نامعتبر است."

        app_password = ''.join(str(runtime_config.get("email_password", EMAIL_PASSWORD) or '').split())
        if not app_password or app_password.startswith('XXXX'):
            return False, "⚠️ App Password تنظیم نشده!\n\nدستور زیر رو بفرست:\n/setpassword [App Password]"

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

def fill_template(template_body, data):
    result = template_body
    for key, value in data.items():
        result = result.replace(f"{{{{{key}}}}}", str(value or "---"))
    return "", result.strip()


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
    """کیبورد اصلی ادمین — دسته‌بندی شده"""
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        types.KeyboardButton("📊 داشبورد"),
        types.KeyboardButton("🚨 سفارش‌های جدید"),
        types.KeyboardButton("📋 مدیریت سفارشات"),
        types.KeyboardButton("🛠 ابزارها"),
        types.KeyboardButton("🔙 بازگشت به منو")
    )
    return m

def admin_orders_keyboard():
    """کیبورد مدیریت سفارشات"""
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        types.KeyboardButton("📋 همه سفارشات"),
        types.KeyboardButton("⏳ در انتظار بررسی"),
        types.KeyboardButton("🔍 در حال بررسی"),
        types.KeyboardButton("⚙️ در حال انجام"),
        types.KeyboardButton("✅ تکمیل‌شده‌ها"),
        types.KeyboardButton("❌ لغوشده‌ها"),
        types.KeyboardButton("🔙 برگشت به پنل")
    )
    return m

def admin_tools_keyboard():
    """کیبورد ابزارهای ادمین"""
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        types.KeyboardButton("📊 آمار کلی"),
        types.KeyboardButton("👥 لیست کاربران"),
        types.KeyboardButton("📢 پیام همگانی"),
        types.KeyboardButton("📧 سیستم ایمیل"),
        types.KeyboardButton("🔐 کنترل دسترسی ادمین"),
        types.KeyboardButton("💾 بک‌آپ دستی"),
        types.KeyboardButton("🔄 تازه‌سازی داشبورد"),
        types.KeyboardButton("🔙 برگشت به پنل")
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
    is_admin_user = is_admin(chat_id)
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        types.KeyboardButton("🔄 مشکل اینستاگرام دارم"),
        types.KeyboardButton("🛒 خرید خدمات"),
        types.KeyboardButton("🤖 تشخیص هوشمند مشکل"),
        types.KeyboardButton("📦 سفارشات من"),
        types.KeyboardButton("👤 پروفایل من"),
        types.KeyboardButton("📢 کانال ما"),
        types.KeyboardButton("📞 پشتیبانی")
    )
    if is_admin_user:
        m.add(types.KeyboardButton("👑 کنترل مدیریت"))

    g = f"سلام *{name}* عزیز 👋\n\n" if name else ""
    footer = "\n\n👑 *مدیریت ربات:* دکمه «کنترل مدیریت» برای شما فعال است." if is_admin_user else ""
    bot.send_message(chat_id,
        f"{g}"
        "🏆 *به ربات رسمی ترویده خوش اومدی!*\n"
        f"{SEP}\n\n"
        "📌 *خدمات تخصصی ما:*\n\n"
        "🔄 بازگردانی پیج دیسیبل\n"
        "🚫 رفع محدودیت اینستاگرام\n"
        "🗑 حذف پیج جعلی\n"
        "🛡 امنیت پیج\n"
        "✈️ پریمیوم تلگرام\n"
        "📱 شماره مجازی\n"
        "👥 فالوور اینستاگرام\n"
        "🎨 ادیت و طراحی محتوا\n\n"
        f"{SEP}\n"
        "👇 *از کجا شروع کنیم؟*" + footer,
        parse_mode="Markdown", reply_markup=m)

# ==================== زیرمنوی مشکل اینستاگرام ====================
@bot.message_handler(func=lambda m: m.text == "🔄 مشکل اینستاگرام دارم")
def instagram_problems(message):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        types.KeyboardButton("🔄 بازگردانی پیج دیسیبل"),
        types.KeyboardButton("🚫 رفع محدودیت"),
        types.KeyboardButton("🗑 حذف پیج جعلی"),
        types.KeyboardButton("🛡 امنیت پیج"),
        types.KeyboardButton("🔙 بازگشت به منو")
    )
    bot.send_message(message.chat.id,
        f"🔄 *مشکل اینستاگرام*\n{SEP}\n\n"
        "مشکلت رو انتخاب کن 👇",
        parse_mode="Markdown", reply_markup=m)

# ==================== زیرمنوی خرید خدمات ====================
@bot.message_handler(func=lambda m: m.text == "🛒 خرید خدمات")
def buy_services(message):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        types.KeyboardButton("✈️ پریمیوم تلگرام"),
        types.KeyboardButton("👥 خرید فالوور"),
        types.KeyboardButton("📱 شماره مجازی"),
        types.KeyboardButton("🎨 ادیت و طراحی"),
        types.KeyboardButton("💡 ایده محتوایی"),
        types.KeyboardButton("🔙 بازگشت به منو")
    )
    bot.send_message(message.chat.id,
        f"🛒 *خرید خدمات*\n{SEP}\n\n"
        "خدمت مورد نظرت رو انتخاب کن 👇",
        parse_mode="Markdown", reply_markup=m)

@bot.message_handler(func=lambda m: m.text == "👑 کنترل مدیریت" and is_admin(m.from_user.id))
def admin_control_button(message):
    bot.send_message(message.chat.id,
        f"👑 *پنل مدیریت ترویده*\n{SEP}\n\n"
        "یه بخش رو انتخاب کن 👇",
        parse_mode="Markdown", reply_markup=admin_main_keyboard())

@bot.message_handler(func=lambda m: m.text == "📊 داشبورد" and is_admin(m.from_user.id))
def admin_dashboard_btn(message):
    admin_dashboard(message.chat.id, message.from_user.first_name, show_pending=True)

@bot.message_handler(func=lambda m: m.text == "📋 مدیریت سفارشات" and is_admin(m.from_user.id))
def orders_submenu(message):
    bot.send_message(message.chat.id,
        f"📋 *مدیریت سفارشات*\n{SEP}\n\n"
        "فیلتر مورد نظر رو انتخاب کن 👇",
        parse_mode="Markdown", reply_markup=admin_orders_keyboard())

@bot.message_handler(func=lambda m: m.text == "🛠 ابزارها" and is_admin(m.from_user.id))
def tools_submenu(message):
    bot.send_message(message.chat.id,
        f"🛠 *ابزارهای مدیریت*\n{SEP}\n\n"
        "ابزار مورد نظر رو انتخاب کن 👇",
        parse_mode="Markdown", reply_markup=admin_tools_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔙 برگشت به پنل" and is_admin(m.from_user.id))
def back_to_panel(message):
    bot.send_message(message.chat.id,
        f"👑 *پنل مدیریت ترویده*\n{SEP}\n\n"
        "یه بخش رو انتخاب کن 👇",
        parse_mode="Markdown", reply_markup=admin_main_keyboard())

@bot.message_handler(commands=['start'])
def start(message):
    user_data.pop(message.from_user.id, None)
    upsert_user(message.from_user)
    main_menu(message.chat.id, message.from_user.first_name)

@bot.message_handler(commands=['users'])
def users_list(message):
    if not is_admin(message.from_user.id): return
    users = load_users()
    total = len(users)
    text = (
        f"👥 *لیست کاربران ربات*\n{SEP}\n\n"
        f"📊 کل کاربران: *{total}*\n\n"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
    for u in users[:30]:
        name = f"{u.get('first_name','')} {u.get('last_name','') or ''}".strip()
        uname = f"@{u['username']}" if u.get('username') else "—"
        bot.send_message(message.chat.id,
            f"👤 *{name}*\n"
            f"🔗 {uname} | `{u['user_id']}`\n"
            f"📅 اول: {u['first_seen']}\n"
            f"🕐 آخر: {u['last_seen']}\n"
            f"📦 سفارشات: {u['orders_count']}",
            parse_mode="Markdown")
    if total > 30:
        bot.send_message(message.chat.id, f"... و {total-30} کاربر دیگه")

@bot.message_handler(commands=['backup'])
def manual_backup(message):
    if not is_admin(message.from_user.id): return
    bot.send_message(message.chat.id, "⏳ در حال گرفتن بک‌آپ...")
    threading.Thread(target=backup_database, daemon=True).start()
    bot.send_message(message.chat.id, "✅ بک‌آپ در حال ارسال به کانال است.")

@bot.message_handler(commands=['setgroq'])
def set_groq_key(message):
    if not is_owner(message.from_user.id): return
    try:
        key = message.text.split(maxsplit=1)[1].strip()
        runtime_config["groq_key"] = key
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "✅ کلید Groq API با موفقیت تنظیم شد!")
    except IndexError:
        bot.send_message(message.chat.id, "❌ فرمت اشتباه\nمثال: /setgroq gsk_xxxxxxxx")

@bot.message_handler(commands=['setemail'])
def set_email_pass(message):
    if not is_owner(message.from_user.id): return
    try:
        pwd = message.text.split(maxsplit=1)[1].strip()
        runtime_config["email_password"] = pwd
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "✅ App Password ایمیل با موفقیت تنظیم شد!")
    except IndexError:
        bot.send_message(message.chat.id, "❌ فرمت اشتباه\nمثال: /setemail abcd efgh ijkl mnop")

@bot.message_handler(commands=['settings'])
def show_settings(message):
    if not is_owner(message.from_user.id): return
    groq = runtime_config.get("groq_key", "")
    email = runtime_config.get("email_password", "")
    groq_status = "✅ تنظیم شده" if groq and groq != "YOUR_GROQ_API_KEY" else "❌ تنظیم نشده"
    email_status = "✅ تنظیم شده" if email and not email.startswith("XXXX") else "❌ تنظیم نشده"
    bot.send_message(message.chat.id,
        f"⚙️ *تنظیمات ربات*\n{SEP}\n\n"
        f"🤖 Groq API: {groq_status}\n"
        f"📧 App Password: {email_status}\n\n"
        "برای تنظیم:\n"
        "/setgroq [API_KEY]\n"
        "/setemail [APP_PASSWORD]",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔙 بازگشت به منو")
def go_back(message):
    user_data.pop(message.from_user.id, None)
    main_menu(message.chat.id)

@bot.message_handler(commands=['admin'])
def admin_command_alias(message):
    if is_admin(message.from_user.id):
        admin_dashboard(message.chat.id, message.from_user.first_name, show_pending=True)

@bot.message_handler(func=lambda m: m.text in ("📂 داشبورد مدیریت", "📊 داشبورد") and is_admin(m.from_user.id))
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
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id,
            "⛔️ *دسترسی محدود*\n\n"
            "فقط مدیر اصلی می‌تونه ادمین‌ها رو مدیریت کنه.",
            parse_mode="Markdown")
        return
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("➕ افزودن ادمین", callback_data="admins_add"),
        types.InlineKeyboardButton("➖ حذف ادمین", callback_data="admins_remove"),
        types.InlineKeyboardButton("🔄 بروزرسانی لیست", callback_data="admins_list"),
        types.InlineKeyboardButton("🔙 بازگشت به داشبورد", callback_data="admins_back")
    )
    active = "\n".join(f"{i}. <code>{aid}</code>{'  👑 مدیر اصلی' if aid == OWNER_ID else ''}" for i, aid in enumerate(ADMINS, 1)) or "— هیچ ادمینی ثبت نشده —"
    text = (
        "🔐 <b>کنترل دسترسی ادمین</b>\n"
        f"{SEP}\n\n"
        "⚠️ فقط مدیر اصلی می‌تونه این بخش رو مدیریت کنه.\n\n"
        "👑 <b>ادمین‌های فعال:</b>\n" + active
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data in ("admins_add", "admins_remove", "admins_list", "admins_back"))
def admin_access_controls(call):
    if not is_owner(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔️ فقط مدیر اصلی دسترسی داره!"); return

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

@bot.message_handler(func=lambda m: f"admin_access_{m.from_user.id}" in user_data and is_owner(m.from_user.id))
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
            try:
                bot.send_message(target,
                    "🎉 *شما به عنوان ادمین ربات ترویده تعیین شدید!*\n\n"
                    "برای ورود به پنل مدیریت: /admin",
                    parse_mode="Markdown")
            except: pass
    else:
        if target == OWNER_ID:
            msg = "⛔️ مدیر اصلی قابل حذف نیست."
        elif target not in ADMINS:
            msg = "ℹ️ این آیدی در لیست ادمین‌ها نیست."
        else:
            ADMINS.remove(target)
            msg = f"✅ دسترسی آیدی <code>{target}</code> حذف شد."
            try:
                bot.send_message(target, "⚠️ دسترسی ادمین شما توسط مدیر اصلی لغو شد.")
            except: pass

    user_data.pop(key, None)
    bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=admin_main_keyboard())
    manage_admins(message)

def get_active_sender():
    """برگرداندن ایمیل مبدا فعال"""
    global active_sender_index
    if not email_senders:
        return None
    idx = min(active_sender_index, len(email_senders) - 1)
    return email_senders[idx]

def email_main_keyboard():
    """کیبورد اصلی مدیریت ایمیل"""
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        types.KeyboardButton("📤 ارسال ایمیل جدید"),
        types.KeyboardButton("📋 لیست ایمیل‌های مبدا"),
        types.KeyboardButton("➕ افزودن ایمیل مبدا"),
        types.KeyboardButton("🔙 برگشت به پنل")
    )
    return m

@bot.message_handler(func=lambda m: m.text == "📧 سیستم ایمیل" and is_admin(m.from_user.id))
def email_menu_button(message):
    sender = get_active_sender()
    sender_text = f"✅ {sender['label']}\n📧 {sender['email']}" if sender else "❌ هیچ ایمیل مبدایی ثبت نشده"
    bot.send_message(message.chat.id,
        f"📧 *سیستم مدیریت ایمیل*\n"
        f"{SEP}\n\n"
        f"📤 *ایمیل فعال فعلی:*\n{sender_text}\n\n"
        "یه گزینه انتخاب کن 👇",
        parse_mode="Markdown", reply_markup=email_main_keyboard())

# ==================== لیست ایمیل‌های مبدا ====================
@bot.message_handler(func=lambda m: m.text == "📋 لیست ایمیل‌های مبدا" and is_admin(m.from_user.id))
def list_senders(message):
    if not email_senders:
        bot.send_message(message.chat.id,
            "📭 هیچ ایمیل مبدایی ثبت نشده.\n\nاز دکمه ➕ افزودن ایمیل مبدا استفاده کن.",
            reply_markup=email_main_keyboard())
        return

    mk = types.InlineKeyboardMarkup(row_width=1)
    text = f"📋 *لیست ایمیل‌های مبدا*\n{SEP}\n\n"
    for i, s in enumerate(email_senders):
        active_mark = "✅ فعال" if i == active_sender_index else "⚪️ غیرفعال"
        text += f"{'🟢' if i == active_sender_index else '⚪️'} *{s['label']}*\n📧 {s['email']}\n{active_mark}\n\n"
        mk.add(
            types.InlineKeyboardButton(
                f"{'✅' if i == active_sender_index else '🔘'} انتخاب: {s['email']}",
                callback_data=f"sel_sender_{i}"
            ),
            types.InlineKeyboardButton(
                f"🗑 حذف: {s['email']}",
                callback_data=f"del_sender_{i}"
            )
        )

    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("sel_sender_") or c.data.startswith("del_sender_"))
def manage_sender_cb(call):
    if not is_admin(call.from_user.id): return
    global active_sender_index

    parts = call.data.split("_")
    action = parts[0] + "_" + parts[1]  # sel_sender یا del_sender
    idx = int(parts[2])

    if action == "sel_sender":
        if 0 <= idx < len(email_senders):
            active_sender_index = idx
            s = email_senders[idx]
            bot.answer_callback_query(call.id, f"✅ {s['email']} انتخاب شد!")
            bot.send_message(call.message.chat.id,
                f"✅ *ایمیل مبدا تغییر کرد*\n\n"
                f"📧 {s['email']}\n"
                f"🏷 {s['label']}",
                parse_mode="Markdown", reply_markup=email_main_keyboard())
        else:
            bot.answer_callback_query(call.id, "❌ ایمیل پیدا نشد")

    elif action == "del_sender":
        if 0 <= idx < len(email_senders):
            removed = email_senders.pop(idx)
            if active_sender_index >= len(email_senders):
                active_sender_index = max(0, len(email_senders) - 1)
            bot.answer_callback_query(call.id, f"🗑 حذف شد")
            bot.send_message(call.message.chat.id,
                f"🗑 *ایمیل حذف شد:*\n📧 {removed['email']}",
                parse_mode="Markdown", reply_markup=email_main_keyboard())
        else:
            bot.answer_callback_query(call.id, "❌ ایمیل پیدا نشد")

# ==================== افزودن ایمیل مبدا ====================
@bot.message_handler(func=lambda m: m.text == "➕ افزودن ایمیل مبدا" and is_admin(m.from_user.id))
def add_sender_start(message):
    user_data[f"add_sender_{message.from_user.id}"] = {"step": "email"}
    bot.send_message(message.chat.id,
        f"➕ *افزودن ایمیل مبدا جدید*\n{SEP}\n\n"
        "📧 آدرس ایمیل جدید رو بفرست:\n"
        "_(مثال: myemail@gmail.com)_",
        parse_mode="Markdown", reply_markup=back_btn())

@bot.message_handler(func=lambda m: f"add_sender_{m.from_user.id}" in user_data
                     and user_data[f"add_sender_{m.from_user.id}"].get("step") == "email")
def add_sender_email(message):
    if message.text == "🔙 بازگشت به منو":
        user_data.pop(f"add_sender_{message.from_user.id}", None)
        go_back(message); return

    email = message.text.strip()
    if "@" not in email or "." not in email:
        bot.send_message(message.chat.id, "❌ فرمت ایمیل اشتباهه. دوباره بفرست:")
        return

    user_data[f"add_sender_{message.from_user.id}"]["email"] = email
    user_data[f"add_sender_{message.from_user.id}"]["step"] = "label"
    bot.send_message(message.chat.id,
        "🏷 یه اسم/برچسب برای این ایمیل بذار:\n"
        "_(مثال: ایمیل پشتیبانی، ایمیل شایان)_",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: f"add_sender_{m.from_user.id}" in user_data
                     and user_data[f"add_sender_{m.from_user.id}"].get("step") == "label")
def add_sender_label(message):
    if message.text == "🔙 بازگشت به منو":
        user_data.pop(f"add_sender_{message.from_user.id}", None)
        go_back(message); return

    key = f"add_sender_{message.from_user.id}"
    d = user_data[key]
    label = message.text.strip()
    email = d["email"]

    # چک تکراری نبودن
    if any(s["email"] == email for s in email_senders):
        bot.send_message(message.chat.id,
            f"⚠️ این ایمیل قبلاً ثبت شده!\n📧 {email}",
            reply_markup=email_main_keyboard())
        user_data.pop(key, None)
        return

    email_senders.append({"email": email, "label": label, "active": True})
    user_data.pop(key, None)

    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("✅ فعال کن", callback_data=f"sel_sender_{len(email_senders)-1}"))
    bot.send_message(message.chat.id,
        f"✅ *ایمیل جدید اضافه شد!*\n{SEP}\n\n"
        f"📧 {email}\n🏷 {label}\n\n"
        "برای فعال کردن این ایمیل دکمه زیر رو بزن 👇",
        parse_mode="Markdown", reply_markup=mk)

# ==================== ارسال ایمیل جدید ====================
@bot.message_handler(func=lambda m: m.text == "📤 ارسال ایمیل جدید" and is_admin(m.from_user.id))
def send_email_btn(message):
    sender = get_active_sender()
    if not sender:
        bot.send_message(message.chat.id,
            "❌ هیچ ایمیل مبدایی ثبت نشده!\nاول از ➕ افزودن ایمیل مبدا استفاده کن.",
            reply_markup=email_main_keyboard())
        return

    # نمایش ایمیل فعال + انتخاب مقصد
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("🔴 security@mail.instagram.com", callback_data="emto_security"),
        types.InlineKeyboardButton("🔵 support@instagram.com", callback_data="emto_support"),
        types.InlineKeyboardButton("🟢 help@instagram.com", callback_data="emto_help"),
        types.InlineKeyboardButton("🟡 instagram-android@meta.com", callback_data="emto_android"),
        types.InlineKeyboardButton("✏️ ایمیل دلخواه", callback_data="emto_custom"),
    )
    bot.send_message(message.chat.id,
        f"📤 *ارسال ایمیل جدید*\n{SEP}\n\n"
        f"📧 *ایمیل مبدا:*\n{sender['label']}\n{sender['email']}\n\n"
        "📨 *ایمیل مقصد رو انتخاب کن:*",
        parse_mode="Markdown", reply_markup=mk)

EMAIL_TARGETS_MAP = {
    "emto_security": "security@mail.instagram.com",
    "emto_support": "support@instagram.com",
    "emto_help": "help@instagram.com",
    "emto_android": "instagram-android@meta.com",
}

@bot.callback_query_handler(func=lambda c: c.data.startswith("emto_"))
def email_target_selected(call):
    if not is_admin(call.from_user.id): return

    if call.data == "emto_custom":
        user_data[f"email_custom_to_{call.from_user.id}"] = True
        bot.send_message(call.message.chat.id,
            "✏️ ایمیل مقصد رو بنویس:",
            reply_markup=back_btn())
        bot.answer_callback_query(call.id)
        return

    to_email = EMAIL_TARGETS_MAP.get(call.data, "")
    user_data[f"email_to_{call.from_user.id}"] = to_email
    user_data[f"email_step_{call.from_user.id}"] = "type"

    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("🔄 بازگردانی پیج دیسیبل", callback_data="emtype_disable"),
        types.InlineKeyboardButton("🚫 رفع محدودیت", callback_data="emtype_limit"),
        types.InlineKeyboardButton("🗑 حذف پیج جعلی", callback_data="emtype_fake"),
    )
    bot.send_message(call.message.chat.id,
        f"📨 مقصد: `{to_email}`\n\nنوع مشکل رو انتخاب کن:",
        parse_mode="Markdown", reply_markup=mk)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: f"email_custom_to_{m.from_user.id}" in user_data)
def email_custom_to(message):
    if message.text == "🔙 بازگشت به منو":
        user_data.pop(f"email_custom_to_{message.from_user.id}", None)
        go_back(message); return
    if "@" not in message.text:
        bot.send_message(message.chat.id, "❌ فرمت اشتباه. دوباره بفرست:"); return
    user_data.pop(f"email_custom_to_{message.from_user.id}", None)
    user_data[f"email_to_{message.from_user.id}"] = message.text.strip()
    user_data[f"email_step_{message.from_user.id}"] = "type"
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("🔄 بازگردانی پیج دیسیبل", callback_data="emtype_disable"),
        types.InlineKeyboardButton("🚫 رفع محدودیت", callback_data="emtype_limit"),
        types.InlineKeyboardButton("🗑 حذف پیج جعلی", callback_data="emtype_fake"),
    )
    bot.send_message(message.chat.id,
        f"📨 مقصد: `{message.text.strip()}`\n\nنوع مشکل رو انتخاب کن:",
        parse_mode="Markdown", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("emtype_"))
def email_type_selected(call):
    if not is_admin(call.from_user.id): return
    em_type = call.data.replace("emtype_", "")
    user_data[f"email_type_{call.from_user.id}"] = em_type
    user_data[f"email_step_{call.from_user.id}"] = "info"
    bot.send_message(call.message.chat.id,
        "📝 اطلاعات پیج رو بفرست:\n\n"
        "آیدی: @username\n"
        "نام: اسم پیج\n"
        "ایمیل: email@gmail.com\n"
        "تلفن: 09xxxxxxxx\n"
        "فالوور: تعداد\n"
        "توضیحات: متن کامل مشکل",
        reply_markup=back_btn())
    bot.answer_callback_query(call.id)

def show_email_template(chat_id, uid, em_type, to_email, fill_data, sender, t_idx=0):
    """نمایش یک قالب ایمیل با دکمه‌های قبلی/بعدی"""
    import urllib.parse
    templates = EMAIL_TEMPLATES.get(em_type, EMAIL_TEMPLATES["disable"])
    t_idx = t_idx % len(templates)
    t = templates[t_idx]
    total = len(templates)

    subject = fill_template_str(t["subject"], fill_data)
    body = fill_template_str(t["body"], fill_data)

    # ذخیره اطلاعات
    user_data[f"tpl_data_{uid}"] = {
        "em_type": em_type, "to": to_email,
        "fill_data": fill_data, "sender": sender,
        "t_idx": t_idx, "subject": subject, "body": body
    }

    to_enc = urllib.parse.quote(to_email)
    sub_enc = urllib.parse.quote(subject)
    body_enc = urllib.parse.quote(body)
    mailto = f"mailto:{to_enc}?subject={sub_enc}&body={body_enc}"

    sender_text = f"{sender['label']}" if sender else "نامشخص"
    mk = types.InlineKeyboardMarkup(row_width=3)

    # دکمه‌های قبلی/بعدی
    nav_btns = []
    if total > 1:
        nav_btns.append(types.InlineKeyboardButton("⬅️ قبلی", callback_data=f"tpl_prev_{uid}"))
        nav_btns.append(types.InlineKeyboardButton(f"{t_idx+1}/{total}", callback_data="tpl_noop"))
        nav_btns.append(types.InlineKeyboardButton("بعدی ➡️", callback_data=f"tpl_next_{uid}"))
        mk.add(*nav_btns)

    mk.add(
        types.InlineKeyboardButton("📧 باز در Gmail", url=mailto),
        types.InlineKeyboardButton("📋 کپی متن", callback_data=f"tpl_copy_{uid}"),
    )
    mk.add(types.InlineKeyboardButton("❌ لغو", callback_data=f"cancel_email_{uid}"))

    text = (
        f"📧 *پیش‌نمایش ایمیل*\n{SEP}\n\n"
        f"🏷 *قالب:* {t['title']}\n"
        f"📤 *مبدا:* {sender_text}\n"
        f"📨 *مقصد:* `{to_email}`\n"
        f"📌 *موضوع:* `{subject}`\n\n"
        f"{SEP}\n\n"
        f"```\n{body[:1000]}{'...' if len(body)>1000 else ''}\n```\n\n"
        f"{'🔄 ' + str(total) + ' قالب مختلف موجوده — با دکمه‌های قبلی/بعدی مرور کن' if total > 1 else ''}"
    )
    return text, mk

@bot.message_handler(func=lambda m: user_data.get(f"email_step_{m.from_user.id}") == "info")
def email_info_received(message):
    if message.text == "🔙 بازگشت به منو":
        for k in [f"email_to_{message.from_user.id}", f"email_type_{message.from_user.id}",
                  f"email_step_{message.from_user.id}"]:
            user_data.pop(k, None)
        go_back(message); return

    uid = message.from_user.id
    to_email = user_data.get(f"email_to_{uid}", "")
    em_type = user_data.get(f"email_type_{uid}", "disable")
    sender = get_active_sender()

    lines = message.text.strip().split("\n")
    info = {}
    for line in lines:
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip()] = v.strip()

    fill_data = {
        "username": info.get("آیدی", info.get("username", "@username")),
        "page_name": info.get("نام", info.get("name", "---")),
        "email": info.get("ایمیل", info.get("email", "---")),
        "phone": info.get("تلفن", info.get("phone", "---")),
        "followers": info.get("فالوور", info.get("followers", "---")),
        "description": info.get("توضیحات", info.get("desc", "---")),
        "page_type": info.get("نوع پیج", "---"),
        "target_id": info.get("پیج هدف", "---"),
        "reason": info.get("دلیل", "---"),
    }

    for k in [f"email_to_{uid}", f"email_type_{uid}", f"email_step_{uid}"]:
        user_data.pop(k, None)

    text, mk = show_email_template(message.chat.id, uid, em_type, to_email, fill_data, sender, 0)
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("tpl_"))
def template_nav(call):
    if not is_admin(call.from_user.id): return
    uid = call.from_user.id

    if call.data == "tpl_noop":
        bot.answer_callback_query(call.id); return

    key = f"tpl_data_{uid}"
    if key not in user_data:
        bot.answer_callback_query(call.id, "❌ اطلاعات پیدا نشد"); return

    d = user_data[key]

    if call.data == f"tpl_copy_{uid}":
        # ارسال متن کامل برای کپی
        bot.send_message(call.message.chat.id,
            f"📋 *متن کامل ایمیل برای کپی:*\n{SEP}\n\n"
            f"موضوع: {d['subject']}\n\n"
            f"```\n{d['body']}\n```",
            parse_mode="Markdown")
        bot.answer_callback_query(call.id, "✅ متن ارسال شد — کپی کن!")
        return

    t_idx = d["t_idx"]
    if call.data == f"tpl_next_{uid}":
        t_idx += 1
    elif call.data == f"tpl_prev_{uid}":
        t_idx -= 1

    text, mk = show_email_template(
        call.message.chat.id, uid,
        d["em_type"], d["to"], d["fill_data"], d["sender"], t_idx
    )
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode="Markdown", reply_markup=mk)
    except:
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=mk)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("switch_send_"))
def switch_and_send(call):
    if not is_admin(call.from_user.id): return
    parts = call.data.split("_")
    new_idx = int(parts[2])
    uid = int(parts[3])
    global active_sender_index
    active_sender_index = new_idx
    bot.answer_callback_query(call.id, f"✅ ایمیل مبدا تغییر کرد")
    bot.send_message(call.message.chat.id,
        f"✅ ایمیل مبدا تغییر کرد به:\n📧 {email_senders[new_idx]['email']}\n\nدوباره ارسال ایمیل رو بزن.")

@bot.message_handler(commands=['email'])
def email_cmd(message):
    if not is_admin(message.from_user.id): return
    email_menu_button(message)

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
    del user_data[key]
    bot.answer_callback_query(call.id)

    import urllib.parse
    to = urllib.parse.quote(email_data["to"])
    subject = urllib.parse.quote(email_data["subject"])
    body = urllib.parse.quote(email_data["body"])
    mailto = f"mailto:{to}?subject={subject}&body={body}"

    # متن کامل ایمیل برای کپی
    full_text = (
        f"📧 *اطلاعات ایمیل آماده شد*\n"
        f"{SEP}\n\n"
        f"📤 *مقصد:*\n`{email_data['to']}`\n\n"
        f"📌 *موضوع:*\n`{email_data['subject']}`\n\n"
        f"📝 *متن ایمیل:*\n```\n{email_data['body']}\n```\n\n"
        f"{SEP}\n"
        "👆 متن بالا رو کپی کن و در Gmail پیست کن\n"
        "یا روی دکمه زیر بزن تا Gmail باز بشه 👇"
    )

    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("📧 باز کردن در Gmail", url=mailto))

    try:
        bot.edit_message_text(
            full_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=mk
        )
    except:
        bot.send_message(
            call.message.chat.id,
            full_text,
            parse_mode="Markdown",
            reply_markup=mk
        )

@bot.message_handler(func=lambda m: m.text == "👥 لیست کاربران" and is_admin(m.from_user.id))
def users_list_btn(message):
    users = load_users()
    total = len(users)
    bot.send_message(message.chat.id,
        f"👥 *کاربران ربات*\n{SEP}\n\n"
        f"📊 کل کاربران: *{total}*\n"
        f"📦 کل سفارشات: *{len(orders_db)}*\n\n"
        "_(۳۰ کاربر آخر نمایش داده میشه)_",
        parse_mode="Markdown")
    for u in users[:30]:
        name = f"{u.get('first_name','') or ''} {u.get('last_name','') or ''}".strip() or "—"
        uname = f"@{u['username']}" if u.get('username') else "—"
        bot.send_message(message.chat.id,
            f"👤 *{name}*\n"
            f"🔗 {uname} | `{u['user_id']}`\n"
            f"📅 اول: {u.get('first_seen','—')}\n"
            f"🕐 آخر: {u.get('last_seen','—')}\n"
            f"📦 سفارشات: {u.get('orders_count', 0)}",
            parse_mode="Markdown")
    if total > 30:
        bot.send_message(message.chat.id, f"📋 ... و {total-30} کاربر دیگه")

@bot.message_handler(func=lambda m: m.text == "💾 بک‌آپ دستی" and is_admin(m.from_user.id))
def backup_btn(message):
    bot.send_message(message.chat.id, "⏳ در حال گرفتن بک‌آپ...", reply_markup=admin_tools_keyboard())
    threading.Thread(target=backup_database, daemon=True).start()

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
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
    mk.add("🛍 فروش محصول","📚 آموزش","🏥 پزشکی","🎭 سرگرمی",
           "💪 فیتنس و ورزش","🍳 آشپزی","✈️ گردشگری","💻 تکنولوژی",
           "🎨 هنر و طراحی","📰 خبری","🔙 بازگشت به منو")
    bot.send_message(message.chat.id,
        "📝 *مرحله ۴ از ۷*\n\n"
        "📌 موضوع پیجت چیه؟\n"
        "_(یکی رو انتخاب کن یا خودت بنویس)_",
        parse_mode="Markdown", reply_markup=mk)

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "dis_pic")
def dis_pic_text(message):
    if message.text == "🔙 بازگشت به منو": go_back(message); return
    user_data[message.from_user.id].update({"last_pic": message.text, "pic_type": "text", "step": "dis_topic"})
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
    mk.add("🛍 فروش محصول","📚 آموزش","🏥 پزشکی","🎭 سرگرمی",
           "💪 فیتنس و ورزش","🍳 آشپزی","✈️ گردشگری","💻 تکنولوژی",
           "🎨 هنر و طراحی","📰 خبری","🔙 بازگشت به منو")
    bot.send_message(message.chat.id,
        "📝 *مرحله ۴ از ۷*\n\n"
        "📌 موضوع پیجت چیه؟\n"
        "_(یکی رو انتخاب کن یا خودت بنویس)_",
        parse_mode="Markdown", reply_markup=mk)

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
    if runtime_config.get("groq_key", GROQ_API_KEY) in ("YOUR_GROQ_API_KEY", "", None):
        return None, "کلید Groq API هنوز تنظیم نشده — دستور /setgroq [API_KEY] رو بفرست"
    
    GROQ_MODELS = [
        "openai/gpt-oss-120b",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "gemma2-9b-it",
        "qwen/qwen3.6-27b",
    ]
    
    try:
        headers = {
            "Authorization": f"Bearer {runtime_config.get('groq_key', GROQ_API_KEY)}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {
                "role": "system",
                "content": "تو یک متخصص امنیت و بازیابی اینستاگرام هستی که برای تیم ترویده کار می‌کنی. پاسخ‌هایت باید فقط به فارسی، ساده، کوتاه و بدون جدول یا HTML باشه. فقط از ایموجی و متن استفاده کن."
            },
            {
                "role": "user",
                "content": f"""یک متخصص اینستاگرام هستی که به کاربران ایرانی کمک می‌کنی. پاسخت باید:
- فقط فارسی باشه
- ساده و قابل فهم
- بدون HTML، جدول، کد یا مارک‌داون
- فقط از ایموجی و متن ساده استفاده کن

کاربر این مشکل رو داره:
{user_description}

دقیقاً به این شکل جواب بده:

🔍 نوع مشکل:
[یک جمله ساده]

📊 احتمال حل:
[درصد + یک دلیل ساده]

❓ دلیل احتمالی:
[۲ تا ۳ دلیل ساده با خط جدید]

⚡ اقدام فوری:
۱. [کار اول]
۲. [کار دوم]
۳. [کار سوم]

🛡 خدمت پیشنهادی ترویده:
[نام سرویس + یک جمله توضیح]

⚠️ هشدار مهم:
[یک یا دو چیزی که نباید انجام بده]

📞 برای ثبت سفارش و پیگیری با تیم ترویده در ارتباط باش:
👤 @tarvideh"""
            }
        ]

        last_err = None
        for model in GROQ_MODELS:
            try:
                payload = {
                    "model": model,
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "messages": messages
                }
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers, json=payload, timeout=30
                )
                if r.status_code == 200:
                    print(f"Groq: using model {model}")
                    return r.json()["choices"][0]["message"]["content"], None
                else:
                    err_data = r.json().get("error", {})
                    last_err = err_data.get("message", r.text)
                    if "decommissioned" in last_err or "does not exist" in last_err:
                        print(f"Groq: model {model} unavailable, trying next...")
                        continue
                    return None, last_err
            except requests.exceptions.Timeout:
                return None, "timeout — سرور جواب نداد"
            except Exception as e:
                last_err = str(e)
                continue
        
        return None, f"هیچ مدلی در دسترس نیست: {last_err}"
    
    except Exception as e:
        print(f"AI outer error: {e}")
        return None, str(e)

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
        result, error = ai_diagnose(description)

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
            mk = types.InlineKeyboardMarkup()
            mk.add(types.InlineKeyboardButton("💬 مشاوره با کارشناس", url="https://t.me/tarvideh"))
            err_text = f"\n\n🔎 جزئیات خطا: `{error}`" if error else ""
            try:
                bot.send_message(message.chat.id,
                    f"⚠️ *سیستم هوشمند موقتاً در دسترس نیست*\n"
                    f"{SEP}\n\n"
                    "نگران نباش! کارشناسان ما میتونن مشکلت رو بررسی کنن.\n"
                    f"{err_text}\n\n"
                    "📞 همین الان با تیم ترویده در ارتباط باش:",
                    parse_mode="Markdown", reply_markup=mk)
            except: pass

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
    # ترکیب همه کاربران از جدول users + orders_db
    all_uids = set([o["user_id"] for o in orders_db])
    for u in load_users():
        all_uids.add(u["user_id"])
    sent = 0
    failed = 0
    for uid in all_uids:
        try:
            bot.send_message(uid,
                f"📢 *پیام رسمی از ترویده*\n"
                f"{SEP}\n\n"
                f"{message.text}",
                parse_mode="Markdown")
            sent += 1
        except:
            failed += 1
    bot.send_message(message.chat.id,
        f"✅ *پیام همگانی ارسال شد*\n\n"
        f"📤 ارسال موفق: *{sent}*\n"
        f"❌ ناموفق: *{failed}*",
        parse_mode="Markdown")
    del user_data[message.from_user.id]
    main_menu(message.chat.id)

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ("🔄 تازه‌سازی داشبورد", "🔄 تازه‌سازی سفارشات"))
def refresh_orders(message):
    admin_dashboard(message.chat.id, message.from_user.first_name, show_pending=True)

print("✅ ربات ترویده آماده‌ست...")
bot.infinity_polling(skip_pending=True)
