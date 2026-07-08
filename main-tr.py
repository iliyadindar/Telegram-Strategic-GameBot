import telebot
from telebot import types
import sqlite3
import html

# Initialize the bot with your token
API_TOKEN = 'YOUR TOKEN'
ADMIN_ID = 000
CHANNEL_ID = "YOUR CHANNEL ID, EXAMPLE : @SOMETHING"
bot = telebot.TeleBot(API_TOKEN)

# Initialize the database
conn = sqlite3.connect('game_bot.db', check_same_thread=False)
cursor = conn.cursor()

# Create the necessary tables
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    group_id INTEGER,
                    clothes INTEGER DEFAULT 2000,
                    money INTEGER DEFAULT 2000,
                    stones INTEGER DEFAULT 2000,
                    wood INTEGER DEFAULT 2000,
                    iron INTEGER DEFAULT 2000,
                    gold INTEGER DEFAULT 2000,
                    food INTEGER DEFAULT 2000,
                    meat INTEGER DEFAULT 2000,
                    swordsmen INTEGER DEFAULT 1500,
                    gunmen INTEGER DEFAULT 1500,
                    cavalry_swordsmen INTEGER DEFAULT 1500,
                    cavalry_gunmen INTEGER DEFAULT 1500,
                    special_guard INTEGER DEFAULT 1500,
                    medium_cannons INTEGER DEFAULT 1500,
                    large_cannons INTEGER DEFAULT 1500,
                    small_ships INTEGER DEFAULT 1500,
                    medium_ships INTEGER DEFAULT 1500,
                    large_ships INTEGER DEFAULT 1500,
                    stone_factory INTEGER DEFAULT 0,
                    wood_factory INTEGER DEFAULT 0,
                    iron_factory INTEGER DEFAULT 0,
                    gold_mine INTEGER DEFAULT 0,
                    farm INTEGER DEFAULT 0,
                    animal_farm INTEGER DEFAULT 0,
                    clothes_factory INTEGER DEFAULT 0,
                    bank INTEGER DEFAULT 0,
                    swordsmen_camp INTEGER DEFAULT 0,
                    gunmen_camp INTEGER DEFAULT 0,
                    cavalry_swordsmen_camp INTEGER DEFAULT 0,
                    cavalry_gunmen_camp INTEGER DEFAULT 0,
                    special_guard_camp INTEGER DEFAULT 0,
                    medium_cannon_factory INTEGER DEFAULT 0,
                    large_cannon_factory INTEGER DEFAULT 0,
                    small_shipyard INTEGER DEFAULT 0,
                    medium_shipyard INTEGER DEFAULT 0,
                    large_shipyard INTEGER DEFAULT 0,
                    treaties TEXT DEFAULT ''
                    )''')
conn.commit()

user_context = {}

# Yöneticinin düzenleyebileceği geçerli varlık sütunları — hem düzenleyici
# butonlarını oluşturmak hem de sütun adını SQL'de kullanmadan önce doğrulamak için.
VALID_ASSETS = (
    'clothes', 'stones', 'wood', 'iron', 'gold', 'money', 'food', 'meat',
    'swordsmen', 'gunmen', 'cavalry_swordsmen', 'cavalry_gunmen', 'special_guard',
    'medium_cannons', 'large_cannons', 'small_ships', 'medium_ships', 'large_ships',
)


def escape_html(text):
    """Escape user-provided text before placing it in an HTML-parsed message."""
    return html.escape(text, quote=False) if text else text


# Varlık sütunları için görünen etiketler (yönetici varlık düzenleyicisi kullanır).
# Alttaki callback verisi ve veritabanı sütun adı İngilizce kalır.
asset_labels = {
    'clothes': 'Giysi',
    'stones': 'Taş',
    'wood': 'Odun',
    'iron': 'Demir',
    'gold': 'Altın',
    'money': 'Para',
    'food': 'Yiyecek',
    'meat': 'Et',
    'swordsmen': 'Kılıçlı Asker',
    'gunmen': 'Tüfekçi',
    'cavalry_swordsmen': 'Atlı Kılıçlı',
    'cavalry_gunmen': 'Atlı Tüfekçi',
    'special_guard': 'Özel Muhafız',
    'medium_cannons': 'Orta Top',
    'large_cannons': 'Büyük Top',
    'small_ships': 'Küçük Gemi',
    'medium_ships': 'Orta Gemi',
    'large_ships': 'Büyük Gemi',
}

# Sefer türü için görünen etiketler (dahili değer 'land' / 'sea' olarak kalır).
attack_type_labels = {
    'land': 'Kara',
    'sea': 'Deniz',
}


def is_group_chat(message):
    return message.chat.type in ['supergroup']


@bot.message_handler(commands=['setlord'])
def set_lord(message):
    if is_group_chat(message):
        user_id = message.from_user.id
        group_id = message.chat.id
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, group_id) VALUES (?, ?)",
            (user_id, group_id))
        conn.commit()
        bot.reply_to(message, "Bu grupta lord olarak kaydoldunuz.")
    else:
        bot.reply_to(message, "Bu komut yalnızca gruplarda kullanılabilir.")


@bot.message_handler(commands=['start'])
def start(message):
    if is_group_chat(message):
        user_id = message.from_user.id
        cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = cursor.fetchone()
        if user:
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(types.InlineKeyboardButton("💰 Varlıklar", callback_data='assets'))
            markup.add(types.InlineKeyboardButton("🛠️ Yükseltme", callback_data='upgrade'))
            markup.add(types.InlineKeyboardButton("🙌 Bildiri", callback_data='statement'))
            markup.add(types.InlineKeyboardButton("✉️ Özel Mesaj", callback_data='private_message'))
            markup.add(types.InlineKeyboardButton("📜 Antlaşma", callback_data='treaty'))
            markup.add(types.InlineKeyboardButton("⚔️ Askeri Sefer", callback_data='attack'))
            if user_id == ADMIN_ID:
                markup.add(types.InlineKeyboardButton("🔨 Haftalık Güncelleme", callback_data='weekly_update'))
                markup.add(types.InlineKeyboardButton("🛠️ Varlık Ayarı", callback_data='change_assets'))
            bot.send_message(message.chat.id, "Hoş geldiniz lordum", reply_markup=markup)
        else:
            bot.reply_to(message, "Önce /setlord ile kayıt olmalısınız.")
    else:
        bot.reply_to(message, "Bu bot yalnızca gruplarda kullanılabilir.")


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    data_parts = call.data.split('_')
    global item_to_upgrade
    item_to_upgrade = '_'.join(call.data.split('_')[1:])
    #print(data_parts)

    if data_parts[0] == 'assets':
        show_assets(call.message)
    elif data_parts[0] == 'upgrade':
        if len(data_parts) == 1:
            show_upgrade_options(call.message)
        elif len(data_parts) == 3:
            confirm_upgrade(call.message)
        elif '_'.join(data_parts[0:2]) == 'upgrade_confirm':
            process_upgrade_confirmation(call)
    elif call.data == 'treaty_confirmed' or call.data == 'treaty_not_confirmed':
        process_treaty_confirmation(call)
    elif data_parts[0] == 'private':
        if len(data_parts) == 2 and data_parts[1] == 'message':
            ask_for_private_message(call.message, user_id)
        elif len(data_parts) == 3 and data_parts[1] == 'send':
            group_id = int(data_parts[2])
            send_private_message(call, group_id)
    elif data_parts[0] == 'change':
        if len(data_parts) == 2 and data_parts[1] == 'assets':
            if user_id == ADMIN_ID:
                show_asset_change_options(call.message)
            else:
                bot.answer_callback_query(call.id, "Yönetici değilsiniz.")
        elif len(data_parts) >= 3 and data_parts[1] == 'asset':
            asset_type = '_'.join(data_parts[2:])
            ask_for_new_asset_value(call.message, asset_type)
    elif data_parts[0] == 'weekly':
        if data_parts[1] == 'update':
            if user_id == ADMIN_ID:
                collect_factory_output(call.message)
            else:
                bot.answer_callback_query(call.id, "Yönetici değilsiniz.")
    elif data_parts[0] == 'attack':
        if len(data_parts) == 1:
            ask_for_attack_type(call.message)
        else:
            handle_attack_type_selection(call)
    elif data_parts[0] == 'statement':
        if len(data_parts) == 1:
            ask_for_statement(call.message, user_id)
    elif data_parts[0] == 'treaty':
        if len(data_parts) == 1:
            show_treaty_options(call.message)
        elif len(data_parts) == 2 and data_parts[1] == 'new':
            ask_for_treaty_content(call.message, user_id)
        elif len(data_parts) == 3 and data_parts[1] == 'send':
            group_id = int(data_parts[2])
            send_treaty_confirmation(call, group_id)
    else:
        bot.answer_callback_query(call.id, "Geçersiz komut.")


def show_assets(message):
    group_id = message.chat.id
    cursor.execute(
        "SELECT clothes, money, stones, wood, iron, gold, food, meat, swordsmen, gunmen, cavalry_swordsmen, cavalry_gunmen, special_guard, medium_cannons, large_cannons, small_ships, medium_ships, large_ships, "
        "stone_factory, wood_factory, iron_factory, gold_mine, farm, animal_farm, clothes_factory, bank, "
        "swordsmen_camp, gunmen_camp, cavalry_swordsmen_camp, cavalry_gunmen_camp, special_guard_camp, medium_cannon_factory, large_cannon_factory, small_shipyard, medium_shipyard, large_shipyard, treaties FROM users WHERE group_id=?",
        (group_id,))
    user = cursor.fetchone()
    if user:
        assets_message = (
            f"💰 Varlıklar:\n"
            f"<blockquote>Giysi🥋 : {user[0]}\n"
            f"Para💵 : {user[1]}\n"
            f"🪨 Taş: {user[2]}\n"
            f"🌲 Odun: {user[3]}\n"
            f"🪛 Demir: {user[4]}\n"
            f"🏅 Altın: {user[5]}\n"
            f"🍞 Yiyecek: {user[6]}\n"
            f"🍖 Et: {user[7]}\n"
            f"🗡️ Kılıçlı Asker: {user[8]}\n"
            f"🔫 Tüfekçi: {user[9]}\n"
            f"🗡️ Atlı Kılıçlı: {user[10]}\n"
            f"🔫 Atlı Tüfekçi: {user[11]}\n"
            f"🛡️ Özel Muhafız: {user[12]}\n"
            f"🎯 Orta Top: {user[13]}\n"
            f"🎯 Büyük Top: {user[14]}\n"
            f"⛵ Küçük Gemi: {user[15]}\n"
            f"🚢 Orta Gemi: {user[16]}\n"
            f"🛳️ Büyük Gemi: {user[17]}</blockquote>\n\n"
            f"🏭 Fabrikalar:\n"
            f"<blockquote>Taş Fabrikası: {user[18]}\n"
            f"Odun Fabrikası: {user[19]}\n"
            f"Demir Fabrikası: {user[20]}\n"
            f"Altın Madeni: {user[21]}\n"
            f"Çiftlik: {user[22]}\n"
            f"Hayvan Çiftliği: {user[23]}\n"
            f"Giysi Fabrikası: {user[24]}\n"
            f"Banka🏦: {user[25]}</blockquote>\n\n"
            f"⚔️ Kamplar:\n"
            f"<blockquote>Kılıçlı Asker Kampı: {user[26]}\n"
            f"Tüfekçi Kampı: {user[27]}\n"
            f"Atlı Kılıçlı Kampı: {user[28]}\n"
            f"Atlı Tüfekçi Kampı: {user[29]}\n"
            f"Özel Muhafız Kampı: {user[30]}</blockquote>\n\n"
            f"🔧 Topçu Fabrikaları:\n"
            f"<blockquote>Orta Top Fabrikası: {user[31]}\n"
            f"Büyük Top Fabrikası: {user[32]}</blockquote>\n\n"
            f"⚓ Tersaneler:\n"
            f"<blockquote>Küçük Tersane: {user[33]}\n"
            f"Orta Tersane: {user[34]}\n"
            f"Büyük Tersane: {user[35]}</blockquote>\n\n"
            f"📜 Antlaşmalar:\n<blockquote>{user[36]}</blockquote>"
        )
        bot.send_message(message.chat.id, assets_message, parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, "Önce /setlord ile kayıt olmalısınız.")


def show_upgrade_options(message):
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(types.InlineKeyboardButton("Taş Fabrikası", callback_data='upgrade_stone_factory'))
    markup.add(types.InlineKeyboardButton("Odun Fabrikası", callback_data='upgrade_wood_factory'))
    markup.add(types.InlineKeyboardButton("Demir Fabrikası", callback_data='upgrade_iron_factory'))
    markup.add(types.InlineKeyboardButton("Altın Madeni", callback_data='upgrade_gold_mine'))
    markup.add(types.InlineKeyboardButton("Çiftlik", callback_data='upgrade_farm_farm'))
    markup.add(types.InlineKeyboardButton("Hayvan Çiftliği", callback_data='upgrade_animal_farm'))
    markup.add(types.InlineKeyboardButton("Giysi Fabrikası", callback_data='upgrade_clothes_factory'))
    markup.add(types.InlineKeyboardButton("Banka", callback_data='upgrade_bank_bank'))
    markup.add(types.InlineKeyboardButton("Kılıçlı Asker Kampı", callback_data='upgrade_swordsmen_camp'))
    markup.add(types.InlineKeyboardButton("Tüfekçi Kampı", callback_data='upgrade_gunmen_camp'))
    markup.add(types.InlineKeyboardButton("Atlı Kılıçlı Kampı", callback_data='upgrade_cavalryswordsmen_camp'))
    markup.add(types.InlineKeyboardButton("Atlı Tüfekçi Kampı", callback_data='upgrade_cavalrygunmen_camp'))
    markup.add(types.InlineKeyboardButton("Özel Muhafız Kampı", callback_data='upgrade_specialguard_camp'))
    markup.add(types.InlineKeyboardButton("Orta Top Fabrikası", callback_data='upgrade_mediumcannon_factory'))
    markup.add(types.InlineKeyboardButton("Büyük Top Fabrikası", callback_data='upgrade_largecannon_factory'))
    markup.add(types.InlineKeyboardButton("Küçük Tersane", callback_data='upgrade_small_shipyard'))
    markup.add(types.InlineKeyboardButton("Orta Tersane", callback_data='upgrade_medium_shipyard'))
    markup.add(types.InlineKeyboardButton("Büyük Tersane", callback_data='upgrade_large_shipyard'))
    bot.send_message(message.chat.id, "Hangi bölümü yükseltmek istediğinizi seçin", reply_markup=markup)


def confirm_upgrade(message):
    cost_message = get_upgrade_cost_message()
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("Evet", callback_data=f'upgrade_confirm_{item_to_upgrade}'))
    bot.send_message(message.chat.id, cost_message, reply_markup=markup)


def get_upgrade_cost_message():
    if item_to_upgrade == 'stone_factory':
        return "Taş Fabrikasını yükseltmek için 500 odun ve 500 para gerekir."
    elif item_to_upgrade == 'wood_factory':
        return "Odun Fabrikasını yükseltmek için 500 taş ve 500 para gerekir."
    elif item_to_upgrade == 'iron_factory':
        return "Demir Fabrikasını yükseltmek için 500 taş ve 500 para gerekir."
    elif item_to_upgrade == 'gold_mine':
        return "Altın Madenini yükseltmek için 500 odun, 500 taş ve 500 para gerekir."
    elif item_to_upgrade == 'farm_farm':
        return "Çiftliği yükseltmek için 500 odun ve 500 taş gerekir."
    elif item_to_upgrade == 'animal_farm':
        return "Hayvan Çiftliğini yükseltmek için 500 odun, 500 demir ve 500 taş gerekir."
    elif item_to_upgrade == 'clothes_factory':
        return "Giysi Fabrikasını yükseltmek için 500 altın, 500 para ve 500 taş gerekir."
    elif item_to_upgrade == 'bank_bank':
        return "Bankayı yükseltmek için 500 taş, 500 demir ve 500 altın gerekir."
    elif item_to_upgrade == 'swordsmen_camp':
        return "Kılıçlı Asker Kampını yükseltmek için 500 para, 500 taş ve 500 odun gerekir."
    elif item_to_upgrade == 'gunmen_camp':
        return "Tüfekçi Kampını yükseltmek için 500 para, 500 altın ve 500 demir gerekir."
    elif item_to_upgrade == 'cavalryswordsmen_camp':
        return "Atlı Kılıçlı Kampını yükseltmek için 500 demir, 250 altın, 500 taş ve 250 para gerekir."
    elif item_to_upgrade == 'cavalrygunmen_camp':
        return "Atlı Tüfekçi Kampını yükseltmek için 800 altın, 800 taş ve 500 para gerekir."
    elif item_to_upgrade == 'specialguard_camp':
        return "Özel Muhafız Kampını yükseltmek için 1000 para, 1000 taş ve 1000 odun gerekir."
    elif item_to_upgrade == 'mediumcannon_factory':
        return "Orta Top Fabrikasını yükseltmek için 500 demir, 250 para ve 250 odun gerekir."
    elif item_to_upgrade == 'largecannon_factory':
        return "Büyük Top Fabrikasını yükseltmek için 500 demir, 500 taş, 250 para ve 200 altın gerekir."
    elif item_to_upgrade == 'small_shipyard':
        return "Küçük Tersaneyi yükseltmek için 200 demir, 200 odun ve 200 para gerekir."
    elif item_to_upgrade == 'medium_shipyard':
        return "Orta Tersaneyi yükseltmek için 500 demir, 500 odun ve 500 para gerekir."
    elif item_to_upgrade == 'large_shipyard':
        return "Büyük Tersaneyi yükseltmek için 1000 demir, 1000 odun ve 1000 para gerekir."
    else:
        return "Yükseltme için belirtilen öğe mevcut değil."


def process_upgrade_confirmation(call):
    group_id = call.message.chat.id
    if check_upgrade_cost(group_id):
        apply_upgrade(group_id)
        bot.send_message(call.message.chat.id, f"Yükseltildi")
    else:
        bot.send_message(call.message.chat.id, "Yeterli kaynağınız yok")
    bot.answer_callback_query(call.id)


def check_upgrade_cost(group_id):
    cursor.execute("SELECT stones, wood, iron, gold, money FROM users WHERE group_id=?", (group_id,))
    resources = cursor.fetchone()
    #print(item_to_upgrade)
    if item_to_upgrade == 'confirm_stone_factory':
        return resources[1] >= 500 and resources[4] >= 500
    elif item_to_upgrade == 'confirm_wood_factory':
        return resources[0] >= 500 and resources[4] >= 500
    elif item_to_upgrade == 'confirm_iron_factory':
        return resources[0] >= 500 and resources[4] >= 500
    elif item_to_upgrade == 'confirm_gold_mine':
        return resources[2] >= 500 and resources[0] >= 500 and resources[4] >= 500
    elif item_to_upgrade == 'confirm_farm_farm':
        return resources[2] >= 500 and resources[0] >= 500
    elif item_to_upgrade == 'confirm_animal_farm':
        return resources[2] >= 500 and resources[3] >= 500 and resources[0] >= 500
    elif item_to_upgrade == 'confirm_clothes_factory':
        return resources[3] >= 500 and resources[4] >= 500 and resources[0] >= 500
    elif item_to_upgrade == 'confirm_bank_bank':
        return resources[0] >= 500 and resources[2] >= 500 and resources[3] >= 500
    elif item_to_upgrade == 'confirm_swordsmen_camp':
        return resources[4] >= 500 and resources[0] >= 500 and resources[2] >= 500
    elif item_to_upgrade == 'confirm_gunmen_camp':
        return resources[4] >= 500 and resources[3] >= 500 and resources[2] >= 500
    elif item_to_upgrade == 'confirm_cavalryswordsmen_camp':
        return resources[2] >= 500 and resources[3] >= 250 and resources[0] >= 500 and resources[4] >= 250
    elif item_to_upgrade == 'confirm_cavalrygunmen_camp':
        return resources[3] >= 800 and resources[0] >= 800 and resources[4] >= 500
    elif item_to_upgrade == 'confirm_specialguard_camp':
        return resources[4] >= 1000 and resources[0] >= 1000 and resources[2] >= 1000
    elif item_to_upgrade == 'confirm_mediumcannon_factory':
        return resources[2] >= 500 and resources[4] >= 250 and resources[1] >= 250
    elif item_to_upgrade == 'confirm_largecannon_factory':
        return resources[2] >= 500 and resources[0] >= 500 and resources[4] >= 250 and resources[3] >= 200
    elif item_to_upgrade == 'confirm_small_shipyard':
        return resources[2] >= 200 and resources[1] >= 200 and resources[4] >= 200
    elif item_to_upgrade == 'confirm_medium_shipyard':
        return resources[2] >= 500 and resources[1] >= 500 and resources[4] >= 500
    elif item_to_upgrade == 'confirm_large_shipyard':
        return resources[2] >= 1000 and resources[1] >= 1000 and resources[4] >= 1000
    else:
        return False


def apply_upgrade(group_id):
    if item_to_upgrade == 'confirm_stone_factory':
        cursor.execute(
            "UPDATE users SET wood = wood - 500, money = money - 500, stone_factory = stone_factory + 1 WHERE group_id=?",
            (group_id,))
    elif item_to_upgrade == 'confirm_wood_factory':
        cursor.execute(
            "UPDATE users SET stones = stones - 500, money = money - 500, wood_factory = wood_factory + 1 WHERE group_id=?",
            (group_id,))
    elif item_to_upgrade == 'confirm_iron_factory':
        cursor.execute(
            "UPDATE users SET stones = stones - 500, money = money - 500, iron_factory = iron_factory + 1 WHERE group_id=?",
            (group_id,))
    elif item_to_upgrade == 'confirm_gold_mine':
        cursor.execute(
            "UPDATE users SET wood = wood - 500, stones = stones - 500, money = money - 500, gold_mine = gold_mine + 1 WHERE group_id=?",
            (group_id,))
    elif item_to_upgrade == 'confirm_farm_farm':
        cursor.execute(
            "UPDATE users SET wood = wood - 500, stones = stones - 500, farm = farm + 1 WHERE group_id=?",
            (group_id,))
    elif item_to_upgrade == 'confirm_animal_farm':
        cursor.execute(
            "UPDATE users SET wood = wood - 500, iron = iron - 500, stones = stones - 500, animal_farm = animal_farm + 1 WHERE group_id=?",
            (group_id,))
    elif item_to_upgrade == 'confirm_clothes_factory':
        cursor.execute(
            "UPDATE users SET gold = gold - 500, money = money - 500, stones = stones - 500, clothes_factory = clothes_factory + 1 WHERE group_id=?",
            (group_id,))
    elif item_to_upgrade == 'confirm_bank_bank':
        cursor.execute(
            "UPDATE users SET stones = stones - 500, iron = iron - 500, gold = gold - 500, bank = bank + 1 WHERE group_id=?",
            (group_id,))
    elif item_to_upgrade == 'confirm_swordsmen_camp':
        cursor.execute(
            "UPDATE users SET money = money - 500, stones = stones - 500, wood = wood - 500, swordsmen_camp = swordsmen_camp + 1 WHERE group_id=?",
            (group_id,))
    elif item_to_upgrade == 'confirm_gunmen_camp':
        cursor.execute(
            "UPDATE users SET money = money - 500, gold = gold - 500, iron = iron - 500, gunmen_camp = gunmen_camp + 1 WHERE group_id=?",
            (group_id,))
    elif item_to_upgrade == 'confirm_cavalryswordsmen_camp':
        cursor.execute(
            "UPDATE users SET iron = iron - 500, gold = gold - 250, stones = stones - 500, money = money - 250, cavalry_swordsmen_camp = cavalry_swordsmen_camp + 1 WHERE group_id=?",
            (group_id,))
    elif item_to_upgrade == 'confirm_cavalrygunmen_camp':
        cursor.execute(
            "UPDATE users SET gold = gold - 800, stones = stones - 800, money = money - 500, cavalry_gunmen_camp = cavalry_gunmen_camp + 1 WHERE group_id=?",
            (group_id,))
    elif item_to_upgrade == 'confirm_specialguard_camp':
        cursor.execute(
            "UPDATE users SET money = money - 1000, stones = stones - 1000, wood = wood - 1000, special_guard_camp = special_guard_camp + 1 WHERE group_id=?",
            (group_id,))
    elif item_to_upgrade == 'confirm_mediumcannon_factory':
        cursor.execute(
            "UPDATE users SET iron = iron - 500, money = money - 250, wood = wood - 250, medium_cannon_factory = medium_cannon_factory + 1 WHERE group_id=?",
            (group_id,))
    elif item_to_upgrade == 'confirm_largecannon_factory':
        cursor.execute(
            "UPDATE users SET iron = iron - 500, stones = stones - 500, money = money - 250, gold = gold - 200, large_cannon_factory = large_cannon_factory + 1 WHERE group_id=?",
            (group_id,))
    elif item_to_upgrade == 'confirm_small_shipyard':
        cursor.execute(
            "UPDATE users SET iron = iron - 200, wood = wood - 200, money = money - 200, small_shipyard = small_shipyard + 1 WHERE group_id=?",
            (group_id,))
    elif item_to_upgrade == 'confirm_medium_shipyard':
        cursor.execute(
            "UPDATE users SET iron = iron - 500, wood = wood - 500, money = money - 500, medium_shipyard = medium_shipyard + 1 WHERE group_id=?",
            (group_id,))
    elif item_to_upgrade == 'confirm_large_shipyard':
        cursor.execute(
            "UPDATE users SET iron = iron - 1000, wood = wood - 1000, money = money - 1000, large_shipyard = large_shipyard + 1 WHERE group_id=?",
            (group_id,))
    #print('done')
    conn.commit()


def ask_for_private_message(message, user_id):
    bot.send_message(message.chat.id, "Lütfen özel mesajınızı girin:")
    bot.register_next_step_handler(message, lambda msg: get_private_message(msg, user_id))


def get_private_message(message, user_id):
    private_message = escape_html(message.text)
    user_context[user_id] = {'private_message': private_message}
    cursor.execute("SELECT DISTINCT group_id FROM users")
    groups = cursor.fetchall()
    if groups:
        markup = types.InlineKeyboardMarkup(row_width=2)
        for group in groups:
            bot_name = bot.get_chat(group[0]).title
            markup.add(types.InlineKeyboardButton(bot_name, callback_data=f'private_send_{group[0]}'))
        bot.send_message(message.chat.id, "Hangi gruba gönderileceğini seçin:", reply_markup=markup)


def send_private_message(call, group_id):
    user_id = call.from_user.id
    private_message = user_context.get(user_id, {}).get('private_message')
    user_info = bot.get_chat(user_id)
    user_name = f"<a href='tg://user?id={user_id}'>{escape_html(user_info.first_name)}</a>"
    if private_message:
        bot.send_message(group_id, f"📬 {user_name} tarafından özel mesaj:\n\n{private_message}", parse_mode='HTML')
        bot.answer_callback_query(call.id, "Özel mesaj gönderildi.")
    else:
        bot.answer_callback_query(call.id, "Özel mesaj bulunamadı.")


def show_asset_change_options(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    asset_types = VALID_ASSETS
    for asset in asset_types:
        markup.add(types.InlineKeyboardButton(asset_labels.get(asset, asset), callback_data=f'change_asset_{asset}'))
    bot.send_message(message.chat.id, "Hangi varlığı değiştirmek istediğinizi seçin:", reply_markup=markup)


def ask_for_new_asset_value(message, asset_type):
    group_id = message.chat.id
    user_context[group_id] = {'asset_type': asset_type}
    bot.send_message(message.chat.id, f"Lütfen {asset_labels.get(asset_type, asset_type)} için yeni değeri girin:")
    bot.register_next_step_handler(message, lambda msg: set_new_asset_value(msg, group_id))


def set_new_asset_value(message, group_id):
    try:
        new_value = int(message.text)
        asset_type = user_context[group_id].get('asset_type')
        if asset_type not in VALID_ASSETS:
            bot.send_message(message.chat.id, "Geçersiz varlık.")
            return
        cursor.execute(f"UPDATE users SET {asset_type} = ? WHERE group_id = ?", (new_value, group_id))
        conn.commit()
        bot.send_message(message.chat.id, f"{asset_labels.get(asset_type, asset_type)} {new_value} olarak değiştirildi.")
    except ValueError:
        bot.send_message(message.chat.id, "Girilen değer geçersiz. Lütfen bir sayı girin.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Hata: {e}")


def show_treaty_options(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Yeni Antlaşma Kaydet", callback_data='treaty_new'))
    bot.send_message(message.chat.id, "Hangi işlemi yapmak istediğinizi seçin", reply_markup=markup)


def ask_for_treaty_content(message, user_id):
    bot.send_message(message.chat.id, "Lütfen antlaşma içeriğini girin:")
    bot.register_next_step_handler(message, lambda msg: get_treaty_content(msg, user_id))


def get_treaty_content(message, user_id):
    treaty_content = escape_html(message.text)
    user_context[user_id] = {'treaty_content': treaty_content}
    cursor.execute("SELECT DISTINCT group_id FROM users")
    groups = cursor.fetchall()
    if groups:
        markup = types.InlineKeyboardMarkup()
        for group in groups:
            bot_name = bot.get_chat(group[0]).title
            markup.add(types.InlineKeyboardButton(bot_name, callback_data=f'treaty_send_{group[0]}'))
        bot.send_message(message.chat.id, "Hangi gruba gönderileceğini seçin:", reply_markup=markup)


def send_treaty_confirmation(call, group_id):
    user_id = call.from_user.id
    treaty_content = user_context.get(user_id, {}).get('treaty_content')
    if treaty_content:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("Evet", callback_data='treaty_confirmed'))
        markup.add(types.InlineKeyboardButton("Hayır", callback_data='treaty_not_confirmed'))
        user_info = bot.get_chat(user_id)
        user_name = f"<a href='tg://user?id={user_id}'>{escape_html(user_info.first_name)}</a>"
        bot.send_message(group_id, f"📜 {user_name} tarafından yeni antlaşma:\n\n{treaty_content}\n\nOnaylıyor musunuz?",
                         reply_markup=markup, parse_mode='HTML')
        user_context[user_id]['group_id'] = group_id
        bot.answer_callback_query(call.id, "Antlaşma gönderildi.")
    else:
        bot.answer_callback_query(call.id, "Antlaşma içeriği bulunamadı.")


def process_treaty_confirmation(call):
    user_id = call.from_user.id
    group_id = user_context[user_id]['group_id']
    #print(call.data)
    if call.data == 'treaty_confirmed':
        cursor.execute("SELECT treaties FROM users WHERE user_id = ?", (user_id,))
        user_treaties = cursor.fetchone()[0]
        new_treaties = user_treaties + "\n\n" + user_context[user_id].get('treaty_content') if user_treaties else \
            user_context[user_id].get('treaty_content')
        cursor.execute("UPDATE users SET treaties = ? WHERE user_id = ?", (new_treaties, user_id))
        conn.commit()
        bot.send_message(group_id, 'Antlaşma onaylandı')
    else:
        bot.send_message(group_id, 'Antlaşma reddedildi')
    bot.answer_callback_query(call.id, 'Antlaşma sonucu kaydedildi')


def collect_factory_output(call):
    group_id = call.chat.id
    cursor.execute(
        "SELECT stone_factory, wood_factory, iron_factory, gold_mine, farm, animal_farm, clothes_factory, bank, swordsmen_camp, gunmen_camp, cavalry_swordsmen_camp, cavalry_gunmen_camp, special_guard_camp, medium_cannon_factory, large_cannon_factory, small_shipyard, medium_shipyard, large_shipyard FROM users WHERE group_id=?",
        (group_id,))
    user_factories = cursor.fetchone()
    #print(call.chat.id)
    #print(user_factories)

    if user_factories:
        stones_collected = user_factories[0] * 1500
        wood_collected = user_factories[1] * 1500
        iron_collected = user_factories[2] * 1500
        gold_collected = user_factories[3] * 1500
        food_collected = user_factories[4] * 1500
        meat_collected = user_factories[5] * 1500
        clothes_collected = user_factories[6] * 1500
        money_collected = user_factories[7] * 1500
        swordsmen_collected = user_factories[8] * 500
        gunmen_collected = user_factories[9] * 500
        cavalry_swordsmen_collected = user_factories[10] * 500
        cavalry_gunmen_collected = user_factories[11] * 500
        special_guard_collected = user_factories[12] * 500
        medium_cannons_collected = user_factories[13] * 1500
        large_cannons_collected = user_factories[14] * 1500
        small_ships_collected = user_factories[15] * 500
        medium_ships_collected = user_factories[16] * 500
        large_ships_collected = user_factories[17] * 500

        cursor.execute(
            "UPDATE users SET money = money + ?, stones = stones + ?, wood = wood + ?, iron = iron + ?, gold = gold + ?, food = food + ?, meat = meat + ?, clothes = clothes + ?, small_ships = small_ships + ?, medium_ships = medium_ships + ?, large_ships = large_ships + ?, swordsmen = swordsmen + ?, gunmen = gunmen + ?, cavalry_swordsmen = cavalry_swordsmen + ?, cavalry_gunmen = cavalry_gunmen + ?, special_guard = special_guard + ?, medium_cannons = medium_cannons + ?, large_cannons = large_cannons + ? WHERE group_id=?",
            (money_collected, stones_collected, wood_collected, iron_collected, gold_collected, food_collected,
             meat_collected, clothes_collected, small_ships_collected, medium_ships_collected, large_ships_collected,
             swordsmen_collected, gunmen_collected, cavalry_swordsmen_collected, cavalry_gunmen_collected,
             special_guard_collected, medium_cannons_collected, large_cannons_collected,
             group_id))
        conn.commit()

        collection_message = (f"🏭 Toplanan ürünler:\n"
                              f"Para💵 : {money_collected}\n"
                              f"🪨 Taş: {stones_collected}\n"
                              f"🌲 Odun: {wood_collected}\n"
                              f"🪛 Demir: {iron_collected}\n"
                              f"🏅 Altın: {gold_collected}\n"
                              f"🍞 Yiyecek: {food_collected}\n"
                              f"🍖 Et: {meat_collected}\n"
                              f"👗 Giysi: {clothes_collected}\n"
                              f"⛵ Küçük Gemi: {small_ships_collected}\n"
                              f"🚢 Orta Gemi: {medium_ships_collected}\n"
                              f"🛳️ Büyük Gemi: {large_ships_collected}\n"
                              f"🗡️ Kılıçlı Asker: {swordsmen_collected}\n"
                              f"🔫 Tüfekçi: {gunmen_collected}\n"
                              f"🗡️ Atlı Kılıçlı: {cavalry_swordsmen_collected}\n"
                              f"🔫 Atlı Tüfekçi: {cavalry_gunmen_collected}\n"
                              f"🛡️ Özel Muhafız: {special_guard_collected}\n"
                              f"🎯 Orta Top: {medium_cannons_collected}\n"
                              f"🎯 Büyük Top: {large_cannons_collected}\n")

        bot.send_message(call.chat.id, collection_message)
    else:
        bot.send_message(call.chat.id, "Hata")


def ask_for_statement(message, user_id):
    bot.send_message(message.chat.id, "<b>Lütfen bildirinizi gönderin </b>", parse_mode='HTML')
    bot.register_next_step_handler(message, lambda msg: send_statement(msg, user_id))


def send_statement(message, user_id):
    user_info = bot.get_chat(user_id)
    user_link = f"<a href='tg://user?id={user_id}'>{escape_html(user_info.first_name)}</a>"
    group_name = escape_html(message.chat.title) if message.chat.title else "Bilinmiyor"
    bot.send_message(message.chat.id, "Bildiriniz <b>gönderildi</b>", parse_mode='HTML')

    additional_caption = f"\n\n🌍 {group_name} grubundan\n👤 Komutan: {user_link}"

    if message.text:
        bot.send_message(CHANNEL_ID, f"{escape_html(message.text)}{additional_caption}", parse_mode='HTML')
    elif message.photo:
        original_caption = escape_html(message.caption) if message.caption else " "
        bot.send_photo(CHANNEL_ID, message.photo[-1].file_id, caption=f"{original_caption}{additional_caption}",
                       parse_mode='HTML')
    elif message.video:
        original_caption = escape_html(message.caption) if message.caption else " "
        bot.send_video(CHANNEL_ID, message.video.file_id, caption=f"{original_caption}{additional_caption}",
                       parse_mode='HTML')
    elif message.document:
        original_caption = escape_html(message.caption) if message.caption else " "
        bot.send_document(CHANNEL_ID, message.document.file_id, caption=f"{original_caption}{additional_caption}",
                          parse_mode='HTML')
    elif message.audio:
        original_caption = escape_html(message.caption) if message.caption else " "
        bot.send_audio(CHANNEL_ID, message.audio.file_id, caption=f"{original_caption}{additional_caption}",
                       parse_mode='HTML')
    elif message.voice:
        original_caption = escape_html(message.caption) if message.caption else " "
        bot.send_voice(CHANNEL_ID, message.voice.file_id, caption=f"{original_caption}{additional_caption}",
                       parse_mode='HTML')


def ask_for_attack_type(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("Kara", callback_data='attack_type_land'))
    markup.add(types.InlineKeyboardButton("Deniz", callback_data='attack_type_sea'))
    #markup.add(types.InlineKeyboardButton("Hava", callback_data='attack_type_air'))
    bot.send_message(message.chat.id, "Sefer türünü seçin:", reply_markup=markup)


def handle_attack_type_selection(call):
    global photo_url
    user_id = call.from_user.id
    attack_type = call.data.split('_')[2]
    user_context[user_id] = {'attack_type': attack_type}
    if attack_type == "land":
        photo_url = "https://t.me/bsnsjwjwiiwjwjw92u2b29hwnwns/2"
    elif attack_type == "sea":
        photo_url = "https://t.me/bsnsjwjwiiwjwjw92u2b29hwnwns/3"
    bot.send_message(call.message.chat.id, "Lütfen ordu bilgilerinizi girin:")
    bot.register_next_step_handler(call.message, lambda msg: get_attack_origin(msg, user_id))


def get_attack_origin(message, user_id):
    attack_details = escape_html(message.text)
    user_context[user_id]['attack_details'] = attack_details
    bot.send_message(message.chat.id, "Seferin çıkış noktasını girin:")
    bot.register_next_step_handler(message, lambda msg: get_attack_destination(msg, user_id))


def get_attack_destination(message, user_id):
    attack_origin = escape_html(message.text)
    user_context[user_id]['attack_origin'] = attack_origin
    bot.send_message(message.chat.id, "Seferin hedefini girin:")
    bot.register_next_step_handler(message, lambda msg: get_attack_time(msg, user_id))


def get_attack_time(message, user_id):
    attack_destination = escape_html(message.text)
    user_context[user_id]['attack_destination'] = attack_destination
    bot.send_message(message.chat.id, "Varış zamanını girin:")
    bot.register_next_step_handler(message, lambda msg: send_attack_details(msg, user_id))


def send_attack_details(message, user_id):
    attack_time = escape_html(message.text)
    attack_type = user_context[user_id]['attack_type']
    attack_details = user_context[user_id]['attack_details']
    attack_origin = user_context[user_id]['attack_origin']
    attack_destination = user_context[user_id]['attack_destination']
    attack_type_label = attack_type_labels.get(attack_type, attack_type)
    # Get user info
    user_info = bot.get_chat(user_id)
    user_name = f"<a href='tg://user?id={user_id}'>{escape_html(user_info.first_name)}</a>"

    # Send details to admin
    bot.send_message(ADMIN_ID,
                     f"🔖 {attack_origin} ordusu {attack_destination} hedefine doğru harekete geçti ({attack_type_label})\n\n⚜️ "
                     f"Komutan: {user_name}\n⌛️ Varış zamanı: {attack_time}\n📝 Detaylar: {attack_details}",
                     parse_mode='HTML')

    # Send summary to channel
    bot.send_photo(CHANNEL_ID, photo_url, caption=
    f"🔖 {attack_origin} ordusu {attack_destination} hedefine doğru harekete geçti ({attack_type_label})\n\n⚜️ "
    f"Komutan: {user_name}\n⌛️ Varış zamanı: {attack_time}",
                   parse_mode='HTML')

    bot.send_message(message.chat.id, "Sefer bilgileri gönderildi.")


# Start the bot
bot.infinity_polling()
