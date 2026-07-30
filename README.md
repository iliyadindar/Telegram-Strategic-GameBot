# 🏰 Telegram Strategic GameBot

🌐 **[فارسی](README_FA.md)** | **[Türkçe](README_TR.md)** | **English**

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.6+](https://img.shields.io/badge/Python-3.6%2B-brightgreen.svg)](https://www.python.org/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram-Bot%20API-blue.svg?logo=telegram)](https://core.telegram.org/bots/api)
[![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey.svg?logo=sqlite)](https://www.sqlite.org/)

A **multiplayer strategic resource-management game bot** for Telegram groups. Players become lords of their own territory — managing economies, upgrading buildings, training armies, forging treaties, and launching attacks against rival lords — all within Telegram.

> 🌍 **The bot now speaks three languages.** Run the variant that matches your community: `main.py` (Persian / فارسی), `main-en.py` (English), or `main-tr.py` (Turkish / Türkçe). See [Bot Language](#-bot-language).

> 🚢 **NEW — World Trade.** Lords can now trade with each other by sea and land across a real world map: pick your route (pay the Suez Canal toll or sail around Africa), own straits and canals to collect tolls, and watch your convoy's progress live. See [World Trade](#world-trade).

---

## 📑 Table of Contents

- [Features](#-features)
- [Game Mechanics](#-game-mechanics)
- [Admin Dashboard](#-admin-dashboard)
- [Asset Catalog](#-asset-catalog)
- [Bot Language](#-bot-language)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
- [Usage](#-usage)
  - [Commands](#commands)
  - [Menu Options](#menu-options)
- [Testing](#-testing)
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
| 🚢 **World Trade** | Send goods to other lords by sea or land across a world map of oceans, straits, canals and Silk-Road passes — route choice, tolls, chokepoint ownership, and live convoy tracking |
| 🛡️ **Admin Dashboard** | An inline `/admin` panel: player and world statistics, economy and military overviews, per-feature on/off switches, an admin action log, extra admins, country reset, and campaign/trade photos |
| 🧩 **Custom Asset Types** | Resources, units and buildings are data, not code. Add archers, their training camp, its weekly output and its upgrade cost from inside Telegram — no Python, no migration |
| 🔧 **Admin Controls** | Adjust asset values, trigger weekly updates, and manage trade locations, chokepoint owners, and trade settings |

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

### World Trade

Lords trade resources with each other across two world-map graphs, entirely through inline buttons:

- **Sea routes** 🚢 — oceans, seas and gulfs connected through straits and canals (Suez, Panama, Hormuz, Bab-el-Mandeb, Malacca…). Chokepoints charge a toll; free-but-long detours exist around the Cape of Good Hope and Cape Horn.
- **Land routes** 🐫 — Silk-Road regions (Persia, Anatolia, India, China…) linked through tolled passes such as Khyber, Pamir and the Sahara Route.
- **Route choice** — the bot quotes up to three routes (fastest / toll-free / cheapest) with duration, fees and tolls; the sender picks the trade-off.
- **Ships & caravans** — sea trades require ships with cargo capacity (locked until delivery); land trades hire caravans.
- **Offers & escrow** — goods, vehicles and fees are deducted when the offer is sent; the receiving lord accepts or declines, and declined, cancelled or expired offers are fully refunded.
- **Live tracking** — a background ticker moves convoys in real time and edits the tracking message at every waypoint ("the shipment passed the Suez Canal — toll paid"), announcing departures and arrivals to the game channel.
- **Chokepoint ownership** 🪙 — the admin can grant a group ownership of any strait, canal or pass: passage tolls are then paid into that group's treasury, and its own convoys pass free. Tolls on unowned chokepoints are burned.
- **Admin tuning** — each group's sea/land home location plus every speed, fee, toll and capacity value is editable in-game from the trade admin panel.
- **Trade photo** 🖼 — an admin can attach a photo to trade messages; the offer card, the live tracking message and the channel announcements are then sent as photos with captions. Bodies longer than Telegram's 1024-character caption limit fall back to plain text automatically.

---

## 🛡️ Admin Dashboard

Send `/admin` in a group **or** in the bot's private chat to open the dashboard. Every button re-checks who tapped it, so a panel left open in a group is useless to non-admins.

| Screen | What it does |
|---|---|
| 📊 **Statistics** | Group and lord counts, total wealth, total troops, total buildings, and trade activity (active / pending / completed) |
| 💰 **Economy** | World totals per resource plus the richest group; drills down to a per-group card |
| ⚔️ **Military** | World totals per unit type plus the strongest army; drills down to a per-group card |
| ⚙️ **Enable/disable sections** | One switch per feature — assets, upgrade, statement, private message, treaty, campaign, trade, weekly update, lord registration. A disabled section vanishes from the `/start` menu **and** its callbacks are refused, so an old open menu cannot be used to get around it |
| 🧾 **Action log** | Every admin change — who, what, when — newest first, 10 per page |
| 👑 **Admins** | *(owner only)* Promote extra admins by forwarding one of their messages or sending their numeric id, and demote them again. The owner from the configuration is always an admin and cannot be removed |
| 🧩 **Assets & units** | Add, rename, retune or remove resource, unit and building types — see [Asset Catalog](#-asset-catalog) |
| ♻️ **Reset a country** | Return one group's resources, troops and buildings to their starting values, behind a confirmation step. Treaties and trade locations are left alone, and the previous values are written to the action log |
| 🖼 **Trade photo** | Set or clear the photo used on trade messages |
| 🖼 **War photos** | Set or clear separate photos for land and sea campaign announcements |
| 🌍 **Trade administration** | The existing trade admin screens — home locations, chokepoint owners, trade settings |
| 🎮 **Game menu** | Opens the normal player menu without leaving the panel |

### Appointing lords

Players can no longer register themselves. An admin **replies to the player's message** in the group and sends `/setlord`; the bot verifies the sender is an admin and registers the replied-to user as that group's lord.

### Campaigns and the war channel

Public campaign announcements go to the **war channel** (`WAR_CHANNEL_ID`) and carry only the commander, origin, destination and arrival time. The full report, including the army details the player typed, is sent privately to the owner and every admin.

---

## 🧩 Asset Catalog

Everything a country can own — every resource, unit and building — lives in the database rather than in Python literals. **Assets & units** in the admin panel is where you shape the game.

### Adding archers

1. 🧩 Assets & units → ⚔️ Units → ➕ Add a new type
2. Internal key: `archers` · display name in Persian, English and Turkish · starting amount
3. Back to 🧩 → 🏭 Buildings → ➕ Add a new type → `archery_range`, pick **Archers** as what it produces, and how many per level per weekly update
4. Open the new building → 💸 Upgrade cost → set what one level costs in each resource

Archers now appear in the assets screen, the upgrade menu, the weekly production cycle, the military overview and the admin asset editor. Nothing was recompiled.

### What you can change

| Field | Applies to | Notes |
|---|---|---|
| Display name | everything | Independently per language |
| Starting amount | everything | Used by ♻️ *Reset a country* |
| Produces / output | buildings | Which type it yields and how much per level per weekly update |
| Upgrade cost | buildings | Any combination of resources; zero removes a line |
| Tradeable | resources | Controls whether convoys can carry it |

### Built-ins and removal

The 8 resources, 10 units and 18 buildings that shipped with the game are seeded as **built-in**. They can be renamed and retuned but not removed, because the trade system and the war flow refer to them by key.

Removing a custom type **hides** it: it disappears from every menu, but its database column and its numbers stay. Restoring it brings the values back. Nothing is destroyed, and no live table is rebuilt.

### A bug this fixed

Upgrade costs used to be written twice in each of the three bot files — once to test affordability, once to deduct. For **gold mine, farm, animal farm, swordsman camp and special guard camp** the two lists named different resources, so an upgrade could be approved against your iron and paid for with wood you did not have, driving the balance negative. There is now one cost table driving both, applied in a single transaction.

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

**Nothing is hardcoded.** Just start the bot and paste the values when it asks:

```bash
python main-en.py   # English  (or: python main.py for Persian, python main-tr.py for Turkish)
```

```
=== Bot configuration ===
These values are asked once and stored in bot_config.json.
(That file is gitignored — never commit it.)

Bot token (from @BotFather): 123456:ABC-DEF...
Owner numeric user id (from @userinfobot): 123456789
News channel id (e.g. @mychannel or -100…): @your_channel
War channel id (leave blank to reuse the news channel): @your_war_channel
```

Answers are written to `bot_config.json`, so later runs start silently. Each value is resolved in this order:

| Setting | Environment variable | Purpose |
|---|---|---|
| Bot token | `BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
| Owner id | `ADMIN_ID` | The permanent owner; can promote other admins from the panel |
| News channel | `CHANNEL_ID` | Statements and trade announcements |
| War channel | `WAR_CHANNEL_ID` | Campaign announcements. Blank reuses the news channel |

**environment variable → `bot_config.json` → prompt.** Environment variables always win, so a server deployment never needs the file:

```bash
BOT_TOKEN=123456:ABC ADMIN_ID=123456789 CHANNEL_ID=@news python main-en.py
```

> The SQLite database (`game_bot.db`) is created automatically on the first run, and existing databases are migrated in place — no manual steps when upgrading.

---

## 📖 Usage

### Commands

| Command | Description |
|---|---|
| `/setlord` | **Admin only.** Reply to a player's message with this to make them the lord of that group |
| `/start` | Open the main menu and start playing |
| `/admin` | Open the admin dashboard — works in a group or in private chat *(admin only)* |

### Menu Options

| Button | Action |
|---|---|
| 💰 **Assets** | View your current resources and military units |
| 🛠️ **Upgrade** | Upgrade buildings and factories |
| 🙌 **Statement** | Publish a statement to the game channel |
| ✉️ **Private Message** | Send a private message to another group |
| 📜 **Treaty** | Create, send, or confirm treaties with other players |
| ⚔️ **Military Campaign** | Plan and record attack details |
| 🚢 **World Trade** | Send trade convoys to other lords by sea or land |
| 🛡️ **Admin Panel** | Open the admin dashboard *(admin only)* |
| 🔨 **Weekly Update** | Collect weekly factory outputs *(admin only)* |
| 🛠️ **Set Assets** | Adjust asset values *(admin only)* |
| 🌍 **Trade Admin** | Assign home locations, chokepoint owners and trade settings *(admin only)* |

> Any button whose feature has been switched off in the admin panel is left out of the menu entirely.

---

## 🧪 Testing

The test suite runs offline against an in-memory database and a stub Telegram client — no token needed:

```bash
cd tests
python -m unittest discover -s . -t .
```

It covers configuration resolution, access control, feature toggles, the action log, statistics, country reset, lord appointment, the RTL arrow direction, photo handling, the asset catalog (adding, retuning, hiding, upgrade accounting) and loads all three entry points end to end — including adding archers through the panel and checking a player can then train them.

---

## 📁 Project Structure

```
Telegram-Strategic-GameBot/
├── main.py           # Bot (Persian / فارسی) — logic, handlers, and database setup
├── main-en.py        # Bot (English) — same logic, English interface
├── main-tr.py        # Bot (Turkish / Türkçe) — same logic, Turkish interface
├── bot_config.py     # Token / owner / channel ids: environment → bot_config.json → prompt
├── admin_panel.py    # Inline /admin dashboard: access, statistics, toggles, log, reset
├── admin_strings.py  # The dashboard's text in all three languages
├── asset_catalog.py  # Resources, units and buildings as data: seeding, costs, production
├── asset_admin.py    # Panel screens for adding and retuning catalog types
├── asset_ui.py       # Player screens: assets, upgrades, weekly production, asset editor
├── trade_system.py   # World trade engine shared by all three bots (map graphs, routing, tolls, live tracking)
├── tests/            # Offline test suite (stub bot + in-memory SQLite)
├── LICENSE           # MIT License
├── SECURITY.md       # Security policy
├── README.md         # Project documentation (English)
├── README_FA.md      # Project documentation (Persian / فارسی)
└── README_TR.md      # Project documentation (Turkish / Türkçe)
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
