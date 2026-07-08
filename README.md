# 🏰 Telegram Strategic GameBot

🌐 **[فارسی](README_FA.md)** | **[Türkçe](README_TR.md)** | **English**

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.6+](https://img.shields.io/badge/Python-3.6%2B-brightgreen.svg)](https://www.python.org/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram-Bot%20API-blue.svg?logo=telegram)](https://core.telegram.org/bots/api)
[![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey.svg?logo=sqlite)](https://www.sqlite.org/)

A **multiplayer strategic resource-management game bot** for Telegram groups. Players become lords of their own territory — managing economies, upgrading buildings, training armies, forging treaties, and launching attacks against rival lords — all within Telegram.

> 🌍 **The bot now speaks three languages.** Run the variant that matches your community: `main.py` (Persian / فارسی), `main-en.py` (English), or `main-tr.py` (Turkish / Türkçe). See [Bot Language](#-bot-language).

---

## 📑 Table of Contents

- [Features](#-features)
- [Game Mechanics](#-game-mechanics)
- [Bot Language](#-bot-language)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
- [Usage](#-usage)
  - [Commands](#commands)
  - [Menu Options](#menu-options)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)
- [License](#-license)
- [Contact](#-contact)

---

## ✨ Features

| Category | Details |
|---|---|
| 🏗️ **Resource Management** | Manage 8 resource types: money, stones, wood, iron, gold, food, meat, and clothes |
| 🏭 **Building & Factory Upgrades** | Upgrade stone quarries, lumber mills, iron mines, gold mines, farms, animal farms, clothing factories, and banks |
| ⚔️ **Military System** | Train swordsmen, gunmen, cavalry, special guards, cannons, and naval ships |
| 📜 **Diplomacy & Treaties** | Create, send, and confirm treaties between players with interactive confirmations |
| 🔔 **Weekly Production Cycles** | Collect factory and building outputs on a weekly schedule |
| 💬 **In-Game Communication** | Send private messages between groups and publish statements to channels |
| 🛡️ **Attack & Defense** | Plan and record military campaigns with detailed attack tracking |
| 🔧 **Admin Controls** | Adjust asset values and trigger weekly updates |

---

## 🎮 Game Mechanics

### Resources

Players start with a base supply of resources and military units. Upgrade factories and buildings to boost production:

- **Economy**: Money 💰 · Stones 🪨 · Wood 🪵 · Iron ⛏️ · Gold 🥇 · Food 🌾 · Meat 🥩 · Clothes 👕
- **Military**: Swordsmen ⚔️ · Gunmen 🔫 · Cavalry Swordsmen 🐴 · Cavalry Gunmen 🏇 · Special Guard 🛡️ · Medium Cannons 💣 · Large Cannons 🎯 · Small/Medium/Large Ships 🚢

### Buildings & Factories

Each building can be upgraded through multiple levels. Higher levels produce more resources per weekly cycle:

- Stone Factory · Wood Factory · Iron Factory · Gold Mine
- Farm · Animal Farm · Clothes Factory · Bank
- Military camps and shipyards for each unit type

---

## 🌍 Bot Language

The bot's in-game interface — buttons, prompts, resource names, and channel announcements — is available in **three languages**. Each language is a self-contained, ready-to-run entry point. Pick the one that fits your group and run it; there is no configuration flag to set.

| Language | File to run | In-game menu example |
|---|---|---|
| 🇮🇷 **Persian / فارسی** | `main.py` | `💰 دارایی` · `🛠️ ارتقا` · `⚔️ لشکرکشی` |
| 🇬🇧 **English** | `main-en.py` | `💰 Assets` · `🛠️ Upgrade` · `⚔️ Military Campaign` |
| 🇹🇷 **Turkish / Türkçe** | `main-tr.py` | `💰 Varlıklar` · `🛠️ Yükseltme` · `⚔️ Askeri Sefer` |

> All three variants share identical game logic, commands, database schema (`game_bot.db`), and balance — only the player-facing text differs. You can switch languages at any time by running a different file against the same database.

---

## 🚀 Getting Started

### Prerequisites

- **Python** 3.6 or higher
- A **Telegram Bot Token** from [@BotFather](https://t.me/BotFather)
- **SQLite3** (included with Python)

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/iliyadindar/Telegram-Strategic-GameBot.git
   cd Telegram-Strategic-GameBot
   ```

2. **Install dependencies:**

   ```bash
   pip install pyTelegramBotAPI
   ```

### Configuration

Choose your language file — `main.py` (Persian), `main-en.py` (English), or `main-tr.py` (Turkish) — and update the following values at the top of it:

```python
API_TOKEN = 'YOUR_TELEGRAM_BOT_API_TOKEN'
ADMIN_ID = 123456789          # Your Telegram user ID
CHANNEL_ID = "@your_channel"  # Your Telegram channel username
```

Then start the bot with your chosen language:

```bash
python main-en.py   # English  (or: python main.py for Persian, python main-tr.py for Turkish)
```

> The SQLite database (`game_bot.db`) is created automatically on the first run.

---

## 📖 Usage

### Commands

| Command | Description |
|---|---|
| `/setlord` | Register as a lord in the current group |
| `/start` | Open the main menu and start playing |

### Menu Options

| Button | Action |
|---|---|
| 💰 **Assets** | View your current resources and military units |
| 🛠️ **Upgrade** | Upgrade buildings and factories |
| 🙌 **Statement** | Publish a statement to the game channel |
| ✉️ **Private Message** | Send a private message to another group |
| 📜 **Treaty** | Create, send, or confirm treaties with other players |
| ⚔️ **Military Campaign** | Plan and record attack details |
| 🔨 **Weekly Update** | Collect weekly factory outputs *(admin only)* |
| 🛠️ **Set Assets** | Adjust asset values *(admin only)* |

---

## 📁 Project Structure

```
Telegram-Strategic-GameBot/
├── main.py          # Bot (Persian / فارسی) — logic, handlers, and database setup
├── main-en.py       # Bot (English) — same logic, English interface
├── main-tr.py       # Bot (Turkish / Türkçe) — same logic, Turkish interface
├── LICENSE          # MIT License
├── SECURITY.md      # Security policy
├── README.md        # Project documentation (English)
├── README_FA.md     # Project documentation (Persian / فارسی)
└── README_TR.md     # Project documentation (Turkish / Türkçe)
```

---

## 🤝 Contributing

Contributions are welcome! To get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

For major changes, please open an issue first to discuss what you would like to change.

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## 📬 Contact

**Iliya Dindar** — Creator & Maintainer

- Telegram: [@iliyadindar](https://t.me/iliyadindar)
- GitHub: [@iliyadindar](https://github.com/iliyadindar)

<p align="center">
  ⭐ If you find this project useful, please consider giving it a star!
</p>
