# 💼 Savastan Account Checker Bot

**Savastan Account Checker Bot** is a powerful Telegram bot built with Python that allows authorized users to check the validity of account credentials (in `username:password` format), either one-by-one or in bulk through a text file upload.

This bot supports features like:
- ✅ Account verification
- 📊 Balance & card info extraction
- 🧠 CAPTCHA solving with OCR
- 🔐 Proxy support
- 🔄 Progress tracking
- 📁 File upload processing
- 🛡️ Admin-only user access system

> Developed by [@AkarshxD](https://t.me/akarshxd) — feel free to reach out for queries or collaborations.

---

## 📌 Features

| Feature                        | Description                                                                 |
|-------------------------------|-----------------------------------------------------------------------------|
| 🔐 **Authorization System**    | Only authorized users can access the bot. Admin can `/adduser` or `/removeuser`. |
| 📩 **Combo Input**             | Accepts single or multiple `username:password` combos directly or via `.txt` files. |
| ⚙️ **Mass Combo Checking**     | Reads hundreds of lines from uploaded files and processes them sequentially. |
| 🔎 **CAPTCHA Bypass**         | Uses OCR (EasyOCR) to automatically solve CAPTCHA on login pages. |
| 🌐 **Proxy Support**           | Allows requests to be routed through proxies for anonymity or anti-bot evasion. |
| 📊 **Balance/Card Extraction** | Extracts balance & card data from account after login (logic to be implemented). |
| 🧾 **Progress Tracking**       | Shows updates while processing accounts every 20 attempts. |
| 💌 **Hit Notifications**       | Instantly notifies the user and admin when a valid account (HIT) is found. |
| 🖼️ **Image-enhanced UX**      | Uses random themed images for a better user experience (e.g. welcome, hits, errors). |

---

## 🚀 How It Works

### ➤ Welcome Screen

When an authorized user sends `/start`, they receive a warm welcome along with usage instructions:


### ➤ Input Formats

- Text message: Each line should be a combo like `user@example.com:password123`
- File upload: A `.txt` file with each combo on a new line

---

## 🔐 Admin Controls

Only the `ADMIN_ID` (set in code) can run the following commands:

### `/adduser <user_id>`
Add a Telegram user ID to the authorized list.

### `/removeuser <user_id>`
Remove a Telegram user from the authorized list.

### `/users`
List all currently authorized users.

---

## 🔄 Process Flow

1. **Authorization Check**  
   Users are validated against the authorized list. Unauthorized users get a custom denial message.

2. **Text or File Input**  
   Bot processes input combo(s). If a file is uploaded, the content is decoded with fallback encodings (`utf-8`, `latin-1`, `cp1252`).

3. **CAPTCHA Handling**  
   Each login attempt fetches a CAPTCHA, which is solved using EasyOCR. If solving fails, the combo is skipped.

4. **Login Attempt**  
   Bot simulates login using the combo and solved CAPTCHA. A "hit" means a successful login.

5. **Notification System**  
   Valid hits are sent to both the user and the admin with a formatted caption and a themed image.

6. **Final Summary**  
   After processing all combos, the bot sends a result summary including total processed and success rate.

---

## 🧠 Technologies Used

| Tech            | Purpose                                  |
|-----------------|------------------------------------------|
| **Python**      | Core language                            |
| **Telebot (pyTelegramBotAPI)** | Telegram Bot Framework    |
| **Requests**    | HTTP sessions and proxy support          |
| **EasyOCR**     | CAPTCHA solving                          |
| **InlineKeyboardMarkup** | Enhanced UX with buttons        |
| **Logging**     | Logs crashes and internal errors         |
| **Random**      | Randomized image usage & proxies         |
| **Time/OS**     | Timestamping, file operations            |

---
Send accounts in format: username:password
Or upload a text file containing accounts

## 📂 Project Structure (Suggested)

```bash
SavastanBot/
├── main.py               # Main bot code
├── utils.py              # Functions: load_proxies, is_authorized, etc.
├── captcha_solver.py     # Uses EasyOCR to solve CAPTCHA images
├── authorized_users.json # List of allowed users (optional, or database)
├── WELCOME_IMAGES/       # Folder with themed images
├── requirements.txt      # Python dependencies
├── README.md             # You’re reading this!
```
🛠️ Installation & Setup
🔧 Requirements

Python 3.8+

Telegram Bot Token from @BotFather

Optional: Proxies (HTTP/S) list

📦 Install Dependencies
pip install -r requirements.txt


Example requirements.txt:

pyTelegramBotAPI
requests
easyocr
Pillow

⚙️ Configure Bot

Inside your main.py, set your:

ADMIN_ID = YOUR_TELEGRAM_USER_ID

BOT_TOKEN = "YOUR_BOT_TOKEN"

WELCOME_IMAGES = ["img1.jpg", "img2.png", ...]
(Make sure images are available locally or via URL)

🧪 Run the Bot
python main.py


Console output:

🤖 Initializing Account Checker Bot...
✅ Bot is running and ready!

🔐 Security Note

This bot is restricted to authorized users only.

If you plan to host this publicly or commercially, ensure you follow all ethical and legal guidelines for credential checking.

Avoid misuse. This bot should be used for educational or authorized testing purposes only.

📜 License

This repository is distributed under the MIT License. See LICENSE for details.

🤝 Credits

Developer: @AkarshxD

Telegram: Channel Link

🧠 Disclaimer

This bot is for educational and informational purposes only. Any misuse or illegal activity using this bot is strictly discouraged and the responsibility lies solely with the user. The author assumes no liability for any damage or misuse caused by this project.

🔗 Connect

Feel free to connect or report issues:

📬 Telegram: @AkarshxD

📣 Channel: Join Updates


---

### ✅ Optional: Create `requirements.txt` file

```txt
pyTelegramBotAPI
requests
easyocr
Pillow
