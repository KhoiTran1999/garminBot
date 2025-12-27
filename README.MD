
---

# 🏃‍♂️ Garmin AI Coach Pro

**Automated Personal Training Coach powered by Garmin Data & Google Gemini AI.**

This tool automates the process of fetching your daily health metrics from Garmin Connect, calculates professional training metrics (TRIMP, Readiness), and uses Google Gemini AI to analyze your status and send personalized training advice via Telegram.

## ✨ Features

* **📊 Advanced Metrics Calculation:**
* **Training Readiness:** Weighted score based on Sleep, Stress, and Body Battery (with limiting factor logic).
* **Acute Training Load (7-Day):** Calculates TRIMP (Training Impulse) using the Banister formula based on Heart Rate Reserve.


* **🤖 AI Coach Analysis:** Uses **Google Gemini 2.0 Flash** to act as a professional running coach, analyzing your specific data to recommend workouts (Rest, Base Run, Interval, etc.).
* **👥 Multi-User Support:** Configure multiple accounts to run in parallel. Perfect for families or running groups.
* **📲 Telegram Integration:**
* **Daily Report (5:00 PM):** Detailed health & load report with AI advice.
* **Sync Reminder (4:00 PM):** Friendly reminder to sync your watch before analysis.


* **☁️ Fully Automated:** Designed to run 100% free on GitHub Actions (Cron Job).

## 🛠️ Prerequisites

To run this project, you need:

1. **Garmin Connect Account:** Email and Password.
2. **Google Gemini API Key:** Get a free key from [Google AI Studio](https://aistudio.google.com/).
3. **Telegram Bot:**
* Create a bot via [@BotFather](https://t.me/BotFather) to get the **Token**.
* Get your **Chat ID** (via [@userinfobot](https://t.me/userinfobot)).



## 🚀 Installation (Local Run)

1. **Clone the repository:**
```bash
git clone https://github.com/khoitran1999/garminbot.git
cd garminbot

```


2. **Install dependencies:**
```bash
pip install -r requirements.txt

```


3. **Configure Environment Variables:**
Create a `.env` file in the root directory:
```env
TELEGRAM_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key

# JSON list of users
USERS_JSON='[{"name": "User1", "email": "email1@gm.com", "password": "pass1", "telegram_chat_id": "123"}, {"name": "User2", "email": "email2@gm.com", "password": "pass2", "telegram_chat_id": "456"}]'

```


4. **Run the script:**
```bash
python main.py

```



## ⚙️ GitHub Actions Setup (Automation)

You don't need a server! This project runs automatically on GitHub.

1. **Fork** this repository.
2. Go to **Settings** > **Secrets and variables** > **Actions**.
3. Click **New repository secret** and add the following 3 secrets:

| Secret Name | Value Example | Description |
| --- | --- | --- |
| `GEMINI_API_KEY` | `AIzaSy...` | Your Google AI Studio Key. |
| `TELEGRAM_TOKEN` | `123456:ABC-Def...` | Your Telegram Bot Token. |
| `USERS_JSON` | See below | JSON String containing all users. |

### 📝 `USERS_JSON` Format

This secret must be a valid JSON string array. **Do not use trailing commas.**

```json
[
  {
    "name": "Alex",
    "email": "alex@example.com",
    "password": "alex_garmin_password",
    "telegram_chat_id": "11223344"
  },
  {
    "name": "Sarah",
    "email": "sarah@example.com",
    "password": "sarah_garmin_password",
    "telegram_chat_id": "55667788"
  }
]

```

## ⏰ Schedule

The workflows are configured in `.github/workflows/`:

* **Daily Reminder:** Runs at **16:00 (UTC+7)** - Reminds users to sync data.
* **Daily Report:** Runs at **17:00 (UTC+7)** - Fetches data, runs AI analysis, and sends the report.

*Note: You can modify the Cron schedule in the `.yml` files.*

## 🧮 How It Works

1. **Data Collection:** Connects to Garmin API to fetch:
* *Daily Stats:* Resting Heart Rate (RHR), Stress, Body Battery, Sleep.
* *Activities:* Detailed list of workouts in the last 7 days.


2. **Processing:**
* **Readiness Score:** `(0.4 * Sleep) + (0.2 * Stress) + (0.4 * BodyBattery)`.
* **Acute Load:** Calculates TRIMP for every activity in the last 7 days and averages them.
* **Max HR Correction:** Automatically detects your *real* Max HR from recent activities if the profile setting is incorrect.


3. **AI Analysis:** Sends the processed data context to Google Gemini to generate a human-like coaching advice.
4. **Delivery:** Pushes the final formatted message to your Telegram via Bot.

## ⚠️ Disclaimer

This tool is for informational and educational purposes only. The AI advice is generated based on data patterns and general sports science principles but does not replace professional medical advice. Always listen to your body first.

---

**Author:** [Trần Quốc Khôi]