import telebot
from telebot import types
import sqlite3
import html

import admin_panel
import asset_ui
import bot_config
import trade_system

# Credentials are never hardcoded: they come from the environment, from
# bot_config.json, or — the first time — from a prompt in this terminal.
_conf = bot_config.load(lang='tr')
API_TOKEN = _conf['token']
ADMIN_ID = _conf['admin_id']
CHANNEL_ID = _conf['channel_id']
WAR_CHANNEL_ID = _conf['war_channel_id']
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

# Admin dashboard: access control, feature toggles and the action log. It has
# to come first — the trade system asks it who counts as an admin.
admin_panel.init(bot, conn, ADMIN_ID, CHANNEL_ID, WAR_CHANNEL_ID, lang='tr',
                 game_menu=lambda call: send_main_menu(call.message.chat.id, call.from_user.id))

# World trade system (sea + land routes, tolls, live convoy tracking)
trade_system.init(bot, conn, ADMIN_ID, CHANNEL_ID, lang='tr',
                  is_admin=admin_panel.is_admin, audit=admin_panel.log)

# Player-facing asset, upgrade and weekly-production screens. Every entry
# comes from the asset catalog, so admin-added types work with no code change.
asset_ui.init(bot, conn, lang='tr', audit=admin_panel.log,
              is_admin=admin_panel.is_admin)

# 'trd:' callbacks that belong to the trade admin screens. They stay reachable
# even when the player-facing trade feature is switched off.
TRADE_ADMIN_OPS = ('adm', 'hm', 'hg', 'h', 'cfg', 'ck', 'ow', 'on', 'og', 'ph', 'phs', 'phc')


def escape_html(text):
    """Escape user-provided text before placing it in an HTML-parsed message."""
    return html.escape(text, quote=False) if text else text


# Sefer türü için görünen etiketler (dahili değer 'land' / 'sea' olarak kalır).
attack_type_labels = {
    'land': 'Kara',
    'sea': 'Deniz',
}


@bot.message_handler(commands=['setlord'])
def set_lord(message):
    # A lord is appointed by an admin replying to that player's message.
    admin_panel.handle_setlord(message)


@bot.message_handler(commands=['admin'])
def admin_command(message):
    """The dashboard, available in private chat and in groups."""
    if not admin_panel.open_panel(message.chat.id, message.from_user.id):
        bot.reply_to(message, "Yönetici değilsiniz.")


# Game menu buttons: callback data -> (label, feature key it belongs to)
MENU_BUTTONS = (
    ('assets', "💰 Varlıklar", 'assets'),
    ('upgrade', "🛠️ Yükseltme", 'upgrade'),
    ('statement', "🙌 Bildiri", 'statement'),
    ('private_message', "✉️ Özel Mesaj", 'private_message'),
    ('treaty', "📜 Antlaşma", 'treaty'),
    ('attack', "⚔️ Askeri Sefer", 'attack'),
    ('trd:menu', "🚢 Dünya Ticareti", 'trade'),
)


def send_main_menu(chat_id, user_id):
    """The /start keyboard. Disabled features are left out entirely."""
    cursor.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        bot.send_message(chat_id, "Henüz lord değilsiniz. Bir yöneticinin gruptaki mesajınızı "
                                  "yanıtlayıp /setlord göndermesi gerekir.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    for data, label, feature in MENU_BUTTONS:
        if admin_panel.feature_enabled(feature):
            markup.add(types.InlineKeyboardButton(label, callback_data=data))
    if admin_panel.is_admin(user_id):
        markup.add(types.InlineKeyboardButton("🛡 Yönetim Paneli", callback_data='ap:home'))
        if admin_panel.feature_enabled('weekly_update'):
            markup.add(types.InlineKeyboardButton("🔨 Haftalık Güncelleme", callback_data='weekly_update'))
        markup.add(types.InlineKeyboardButton("🛠️ Varlık Ayarı", callback_data='change_assets'))
        markup.add(types.InlineKeyboardButton("🌍 Ticaret Yönetimi", callback_data='trd:adm'))
    bot.send_message(chat_id, "Hoş geldiniz lordum", reply_markup=markup)


@bot.message_handler(commands=['start'])
def start(message):
    # The menu works in the group and in private chat alike; every button
    # re-checks the tapper, so nothing is unlocked by opening it privately.
    send_main_menu(message.chat.id, message.from_user.id)


# Typing the word on its own is a plain alias for /start, so nobody has to
# remember the command.
PANEL_WORDS = ('panel', 'menü')


def is_panel_word(message):
    return (message.text or '').strip().lower() in PANEL_WORDS


@bot.message_handler(func=is_panel_word)
def panel_word(message):
    send_main_menu(message.chat.id, message.from_user.id)


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
    user_id = call.from_user.id
    attack_type = call.data.split('_')[2]
    # Per-user, not a module global: two campaigns can be in flight at once.
    user_context[user_id] = {'attack_type': attack_type}
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

    headline = (f"🔖 {attack_origin} ordusu {attack_destination} hedefine doğru harekete geçti "
                f"({attack_type_label})\n\n⚜️ Komutan: {user_name}\n"
                f"⌛️ Varış zamanı: {attack_time}")

    # Troop numbers stay private: the owner and every bot admin get the
    # full report, the public post below carries none of it.
    admin_panel.notify_admins(f"{headline}\n📝 Detaylar: {attack_details}", parse_mode='HTML')

    # Public announcement in the war channel — flavour only.
    war_photo = admin_panel.war_photo(attack_type)
    if war_photo:
        bot.send_photo(WAR_CHANNEL_ID, war_photo, caption=headline, parse_mode='HTML')
    else:
        bot.send_message(WAR_CHANNEL_ID, headline, parse_mode='HTML')

    user_context.pop(user_id, None)
    bot.send_message(message.chat.id, "Sefer bilgileri gönderildi.")


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data.startswith('ap:'):
        admin_panel.handle_callback(call)
        return
    if call.data.startswith('ag:'):
        # Assets, upgrades and the asset editor all live in asset_ui now.
        feature = 'upgrade' if call.data.startswith('ag:up') else 'assets'
        if not call.data.startswith('ag:ed') and not admin_panel.require_feature(call, feature):
            return
        asset_ui.handle_callback(call)
        return
    if call.data.startswith('trd:'):
        op = call.data.split(':')[1] if ':' in call.data else ''
        # Admin trade screens keep working while the player-facing feature is off.
        if op not in TRADE_ADMIN_OPS and not admin_panel.require_feature(call, 'trade'):
            return
        trade_system.handle_callback(call)
        return
    user_id = call.from_user.id
    data_parts = call.data.split('_')

    if call.data == 'assets':
        if not admin_panel.require_feature(call, 'assets'):
            return
        bot.answer_callback_query(call.id)
        asset_ui.show_assets(call.message.chat.id, call.message.chat.id)
    elif call.data == 'upgrade':
        if not admin_panel.require_feature(call, 'upgrade'):
            return
        bot.answer_callback_query(call.id)
        asset_ui.upgrade_menu(call.message.chat.id)
    elif call.data == 'change_assets':
        if not admin_panel.is_admin(user_id):
            bot.answer_callback_query(call.id, 'Yönetici değilsiniz.')
            return
        bot.answer_callback_query(call.id)
        asset_ui.editor_menu(call.message.chat.id)
    elif call.data == 'weekly_update':
        if not admin_panel.is_admin(user_id):
            bot.answer_callback_query(call.id, 'Yönetici değilsiniz.')
            return
        if not admin_panel.require_feature(call, 'weekly_update'):
            return
        bot.answer_callback_query(call.id)
        asset_ui.weekly_update(call.message.chat.id, call.message.chat.id)
        admin_panel.log(user_id, 'weekly_update', call.message.chat.title or call.message.chat.id)
    elif call.data == 'treaty_confirmed' or call.data == 'treaty_not_confirmed':
        if not admin_panel.require_feature(call, 'treaty'):
            return
        process_treaty_confirmation(call)
    elif data_parts[0] == 'private':
        if not admin_panel.require_feature(call, 'private_message'):
            return
        if len(data_parts) == 2 and data_parts[1] == 'message':
            ask_for_private_message(call.message, user_id)
        elif len(data_parts) == 3 and data_parts[1] == 'send':
            group_id = int(data_parts[2])
            send_private_message(call, group_id)
    elif data_parts[0] == 'attack':
        if not admin_panel.require_feature(call, 'attack'):
            return
        if len(data_parts) == 1:
            ask_for_attack_type(call.message)
        else:
            handle_attack_type_selection(call)
    elif data_parts[0] == 'statement':
        if not admin_panel.require_feature(call, 'statement'):
            return
        if len(data_parts) == 1:
            ask_for_statement(call.message, user_id)
    elif data_parts[0] == 'treaty':
        if not admin_panel.require_feature(call, 'treaty'):
            return
        if len(data_parts) == 1:
            show_treaty_options(call.message)
        elif len(data_parts) == 2 and data_parts[1] == 'new':
            ask_for_treaty_content(call.message, user_id)
        elif len(data_parts) == 3 and data_parts[1] == 'send':
            group_id = int(data_parts[2])
            send_treaty_confirmation(call, group_id)
    else:
        bot.answer_callback_query(call.id, 'Geçersiz komut.')


# Start the bot
bot.infinity_polling()
