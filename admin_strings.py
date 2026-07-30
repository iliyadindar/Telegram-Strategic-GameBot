# -*- coding: utf-8 -*-
"""Column metadata and localised text for the admin dashboard.

Kept apart from admin_panel.py so the panel file stays about behaviour. Every
language must define exactly the same key set — admin_panel.init() asserts it.
"""

# ---------------------------------------------------------------------------
# Asset columns. Order here is the order shown on screen; the DEFAULT values
# mirror the CREATE TABLE defaults in main*.py and drive "reset to initial".
# ---------------------------------------------------------------------------

RESOURCE_COLS = ('money', 'gold', 'iron', 'stones', 'wood', 'food', 'meat', 'clothes')
RESOURCE_DEFAULT = 2000

UNIT_COLS = ('swordsmen', 'gunmen', 'cavalry_swordsmen', 'cavalry_gunmen', 'special_guard',
             'medium_cannons', 'large_cannons', 'small_ships', 'medium_ships', 'large_ships')
UNIT_DEFAULT = 1500

BUILDING_COLS = ('stone_factory', 'wood_factory', 'iron_factory', 'gold_mine', 'farm',
                 'animal_farm', 'clothes_factory', 'bank', 'swordsmen_camp', 'gunmen_camp',
                 'cavalry_swordsmen_camp', 'cavalry_gunmen_camp', 'special_guard_camp',
                 'medium_cannon_factory', 'large_cannon_factory', 'small_shipyard',
                 'medium_shipyard', 'large_shipyard')
BUILDING_DEFAULT = 0

ALL_COLS = RESOURCE_COLS + UNIT_COLS + BUILDING_COLS

DEFAULTS = {}
DEFAULTS.update({c: RESOURCE_DEFAULT for c in RESOURCE_COLS})
DEFAULTS.update({c: UNIT_DEFAULT for c in UNIT_COLS})
DEFAULTS.update({c: BUILDING_DEFAULT for c in BUILDING_COLS})

COL_NAMES = {
    'fa': {
        'money': '💵 پول', 'gold': '🏅 طلا', 'iron': '🪛 آهن', 'stones': '🪨 سنگ',
        'wood': '🌲 چوب', 'food': '🍞 غذا', 'meat': '🍖 گوشت', 'clothes': '🥋 لباس',
        'swordsmen': '🗡️ سرباز شمشیرزن', 'gunmen': '🔫 سرباز تفنگدار',
        'cavalry_swordsmen': '🗡️ سواره‌نظام شمشیرزن', 'cavalry_gunmen': '🔫 سواره‌نظام تفنگدار',
        'special_guard': '🛡️ گارد ویژه', 'medium_cannons': '🎯 توپ متوسط',
        'large_cannons': '🎯 توپ بزرگ', 'small_ships': '⛵ کشتی کوچک',
        'medium_ships': '🚢 کشتی متوسط', 'large_ships': '🛳️ کشتی بزرگ',
        'stone_factory': 'کارخونه سنگ', 'wood_factory': 'کارخونه چوب',
        'iron_factory': 'کارخونه آهن', 'gold_mine': 'معدن طلا', 'farm': 'زمین کشاورزی',
        'animal_farm': 'دامداری', 'clothes_factory': 'کارخانه لباس', 'bank': '🏦 بانک',
        'swordsmen_camp': 'کمپ سرباز شمشیرزن', 'gunmen_camp': 'کمپ سرباز تفنگدار',
        'cavalry_swordsmen_camp': 'کمپ سواره‌نظام شمشیرزن',
        'cavalry_gunmen_camp': 'کمپ سواره‌نظام تفنگدار', 'special_guard_camp': 'کمپ گارد ویژه',
        'medium_cannon_factory': 'کارخانه توپ متوسط', 'large_cannon_factory': 'کارخانه توپ بزرگ',
        'small_shipyard': 'کشتی‌سازی کوچک', 'medium_shipyard': 'کشتی‌سازی متوسط',
        'large_shipyard': 'کشتی‌سازی بزرگ',
    },
    'en': {
        'money': '💵 Money', 'gold': '🏅 Gold', 'iron': '🪛 Iron', 'stones': '🪨 Stone',
        'wood': '🌲 Wood', 'food': '🍞 Food', 'meat': '🍖 Meat', 'clothes': '🥋 Clothes',
        'swordsmen': '🗡️ Swordsmen', 'gunmen': '🔫 Gunmen',
        'cavalry_swordsmen': '🗡️ Cavalry Swordsmen', 'cavalry_gunmen': '🔫 Cavalry Gunmen',
        'special_guard': '🛡️ Special Guard', 'medium_cannons': '🎯 Medium Cannons',
        'large_cannons': '🎯 Large Cannons', 'small_ships': '⛵ Small Ships',
        'medium_ships': '🚢 Medium Ships', 'large_ships': '🛳️ Large Ships',
        'stone_factory': 'Stone Factory', 'wood_factory': 'Wood Factory',
        'iron_factory': 'Iron Factory', 'gold_mine': 'Gold Mine', 'farm': 'Farm',
        'animal_farm': 'Animal Farm', 'clothes_factory': 'Clothes Factory', 'bank': '🏦 Bank',
        'swordsmen_camp': 'Swordsman Camp', 'gunmen_camp': 'Gunman Camp',
        'cavalry_swordsmen_camp': 'Cavalry Swordsman Camp',
        'cavalry_gunmen_camp': 'Cavalry Gunman Camp', 'special_guard_camp': 'Special Guard Camp',
        'medium_cannon_factory': 'Medium Cannon Factory',
        'large_cannon_factory': 'Large Cannon Factory', 'small_shipyard': 'Small Shipyard',
        'medium_shipyard': 'Medium Shipyard', 'large_shipyard': 'Large Shipyard',
    },
    'tr': {
        'money': '💵 Para', 'gold': '🏅 Altın', 'iron': '🪛 Demir', 'stones': '🪨 Taş',
        'wood': '🌲 Odun', 'food': '🍞 Yiyecek', 'meat': '🍖 Et', 'clothes': '🥋 Giysi',
        'swordsmen': '🗡️ Kılıçlı Asker', 'gunmen': '🔫 Tüfekçi',
        'cavalry_swordsmen': '🗡️ Atlı Kılıçlı', 'cavalry_gunmen': '🔫 Atlı Tüfekçi',
        'special_guard': '🛡️ Özel Muhafız', 'medium_cannons': '🎯 Orta Top',
        'large_cannons': '🎯 Büyük Top', 'small_ships': '⛵ Küçük Gemi',
        'medium_ships': '🚢 Orta Gemi', 'large_ships': '🛳️ Büyük Gemi',
        'stone_factory': 'Taş Fabrikası', 'wood_factory': 'Odun Fabrikası',
        'iron_factory': 'Demir Fabrikası', 'gold_mine': 'Altın Madeni', 'farm': 'Çiftlik',
        'animal_farm': 'Hayvan Çiftliği', 'clothes_factory': 'Giysi Fabrikası', 'bank': '🏦 Banka',
        'swordsmen_camp': 'Kılıçlı Asker Kampı', 'gunmen_camp': 'Tüfekçi Kampı',
        'cavalry_swordsmen_camp': 'Atlı Kılıçlı Kampı',
        'cavalry_gunmen_camp': 'Atlı Tüfekçi Kampı', 'special_guard_camp': 'Özel Muhafız Kampı',
        'medium_cannon_factory': 'Orta Top Fabrikası', 'large_cannon_factory': 'Büyük Top Fabrikası',
        'small_shipyard': 'Küçük Tersane', 'medium_shipyard': 'Orta Tersane',
        'large_shipyard': 'Büyük Tersane',
    },
}

# ---------------------------------------------------------------------------
# Toggleable features. The key is what main*.py passes to feature_enabled().
# ---------------------------------------------------------------------------

FEATURES = ('assets', 'upgrade', 'statement', 'private_message', 'treaty',
            'attack', 'trade', 'weekly_update', 'setlord')

# Actions written to admin_log; label lives under 'act_<name>' in STRINGS.
ACTIONS = ('asset_edit', 'feature_toggle', 'weekly_update', 'reset_country', 'lord_assign',
           'admin_add', 'admin_remove', 'trade_photo', 'war_photo',
           'trade_config', 'chokepoint_owner', 'group_home')

STRINGS = {
    'fa': {
        'not_admin': "شما ادمین نیستید.",
        'not_owner': "فقط مالک ربات می‌تواند این کار را انجام دهد.",
        'err_generic': "خطایی رخ داد. دوباره تلاش کنید.",
        'feature_disabled': "این بخش توسط مدیریت غیرفعال شده است.",
        'panel_title': "🛡 پنل مدیریت\n<blockquote>👑 مالک: {owner}\n👤 ادمین‌ها: {admins}\n"
                       "🏳 گروه‌ها: {groups}\n⚙️ بخش‌های فعال: {on}/{total}</blockquote>",
        'btn_stats': "📊 آمار کلی",
        'btn_eco': "💰 اقتصاد",
        'btn_mil': "⚔️ وضعیت نظامی",
        'btn_features': "⚙️ فعال/غیرفعال کردن بخش‌ها",
        'btn_logs': "🧾 گزارش اقدامات",
        'btn_admins': "👑 مدیران",
        'btn_trade_photo': "🖼 عکس تجارت",
        'btn_war_photo': "🖼 عکس‌های جنگ",
        'btn_trade_adm': "🌍 مدیریت تجارت",
        'btn_reset': "♻️ بازنشانی دارایی کشور",
        'btn_game_menu': "🎮 منوی بازی",
        'btn_back': "🔙 بازگشت",
        'btn_prev': "➡️ قبلی",
        'btn_next': "بعدی ⬅️",
        'btn_per_group': "🏳 مشاهده به تفکیک گروه",
        'no_groups': "هنوز هیچ گروهی ثبت نشده است.",
        'stats_title': "📊 آمار کلی\n<blockquote>🏳 گروه‌ها: {groups}\n👤 لردها: {lords}\n"
                       "💰 مجموع ثروت: {wealth}\n⚔️ مجموع نیروها: {troops}\n"
                       "🏭 مجموع ساختمان‌ها: {buildings}\n"
                       "🚢 تجارت‌های فعال: {active}\n📨 پیشنهادهای در انتظار: {offered}\n"
                       "✅ تجارت‌های کامل‌شده: {done}</blockquote>",
        'eco_title': "💰 اقتصاد جهانی\n<blockquote>{lines}</blockquote>\n"
                     "🏆 ثروتمندترین: {richest}",
        'mil_title': "⚔️ وضعیت نظامی جهانی\n<blockquote>{lines}</blockquote>\n"
                     "🏆 قوی‌ترین ارتش: {strongest}",
        'group_list_title': "🏳 گروه را انتخاب کنید (صفحه {p} از {n}):",
        'group_card': "🏳 <b>{title}</b>\n👤 لرد: {lord}\n\n"
                      "💰 دارایی:\n<blockquote>{resources}</blockquote>\n"
                      "⚔️ ارتش:\n<blockquote>{units}</blockquote>\n"
                      "🏭 ساختمان‌ها:\n<blockquote>{buildings}</blockquote>\n"
                      "🚢 تجارت: فعال {active} | کامل‌شده {done}\n"
                      "⚓️ موقعیت دریایی: {home_sea} | 🏔 موقعیت زمینی: {home_land}",
        'unset': "تعیین نشده",
        'nobody': "ندارد",
        'feat_title': "⚙️ بخش‌های ربات — برای تغییر وضعیت روی هر مورد بزنید:",
        'feat_on': "✅",
        'feat_off': "❌",
        'feat_toggled': "{name}: {state}",
        'feat_assets': "💰 دارایی",
        'feat_upgrade': "🛠️ ارتقا",
        'feat_statement': "🙌 بیانیه",
        'feat_private_message': "✉️ پیام خصوصی",
        'feat_treaty': "📜 معاهده",
        'feat_attack': "⚔️ لشکرکشی",
        'feat_trade': "🚢 تجارت جهانی",
        'feat_weekly_update': "🔨 آپ هفتگی",
        'feat_setlord': "👤 ثبت لرد",
        'log_title': "🧾 گزارش اقدامات (صفحه {p} از {n}):",
        'log_empty': "هنوز هیچ اقدامی ثبت نشده است.",
        'log_row': "▫️ <b>{action}</b> — {actor}\n   {target}{detail}\n   🕓 {ts}",
        'act_asset_edit': "تغییر دارایی",
        'act_feature_toggle': "تغییر وضعیت بخش",
        'act_weekly_update': "آپ هفتگی",
        'act_reset_country': "بازنشانی دارایی کشور",
        'act_lord_assign': "تعیین لرد",
        'act_admin_add': "افزودن ادمین",
        'act_admin_remove': "حذف ادمین",
        'act_trade_photo': "عکس تجارت",
        'act_war_photo': "عکس جنگ",
        'act_trade_config': "تنظیمات تجارت",
        'act_chokepoint_owner': "مالکیت گذرگاه",
        'act_group_home': "موقعیت تجاری گروه",
        'adm_title': "👑 مدیران ربات\n<blockquote>👑 مالک: {owner}</blockquote>\n"
                     "برای حذف روی یک ادمین بزنید:",
        'adm_none': "غیر از مالک، ادمین دیگری وجود ندارد.",
        'btn_add_admin': "➕ افزودن ادمین",
        'adm_add_ask': "پیامی از کاربر مورد نظر را فوروارد کنید یا شناسه عددی او را بفرستید:",
        'adm_added': "✅ {u} به ادمین‌ها اضافه شد.",
        'adm_removed': "🗑 {u} از ادمین‌ها حذف شد.",
        'adm_exists': "این کاربر از قبل ادمین است.",
        'adm_is_owner': "این کاربر مالک ربات است و همیشه دسترسی کامل دارد.",
        'adm_bad_id': "شناسه معتبر نیست. یک عدد بفرستید یا پیامی از کاربر را فوروارد کنید.",
        'reset_pick': "♻️ کدام کشور به حالت اولیه بازگردانده شود؟ (صفحه {p} از {n})",
        'reset_confirm': "♻️ آیا مطمئنید که دارایی‌ها، نیروها و ساختمان‌های <b>{title}</b> "
                         "به مقادیر اولیه بازگردانده شوند؟\n"
                         "معاهدات و موقعیت‌های تجاری دست نخورده باقی می‌مانند. "
                         "این کار قابل بازگشت نیست.",
        'btn_confirm_reset': "✅ بله، بازنشانی کن",
        'reset_done': "♻️ دارایی‌های <b>{title}</b> به حالت اولیه بازگشت.",
        'war_photo_title': "🖼 عکس‌های لشکرکشی — برای تنظیم روی هر مورد بزنید:",
        'wp_land': "🐫 عکس لشکرکشی زمینی",
        'wp_sea': "🚢 عکس لشکرکشی دریایی",
        'wp_set': "تنظیم شده",
        'wp_unset': "تنظیم نشده",
        'wp_ask': "اکنون عکس مورد نظر را بفرستید:",
        'wp_saved': "✅ عکس {kind} ذخیره شد.",
        'wp_cleared': "🗑 عکس {kind} حذف شد.",
        'wp_not_photo': "این پیام عکس نیست؛ عملیات لغو شد.",
        'btn_wp_clear': "🗑 حذف عکس",
        'setlord_group_only': "این دستور فقط در گروه‌ها قابل استفاده است.",
        'setlord_not_admin': "فقط ادمین ربات می‌تواند لرد تعیین کند.",
        'setlord_need_reply': "روی پیام بازیکنی که می‌خواهید لرد شود ریپلای کنید و /setlord بزنید.",
        'setlord_bot_target': "نمی‌توان یک ربات را به عنوان لرد ثبت کرد.",
        'setlord_done': "👤 {u} به عنوان لرد این گروه ثبت شد.",
        'setlord_already': "👤 {u} از قبل لرد این گروه است.",
    },
    'en': {
        'not_admin': "You are not an admin.",
        'not_owner': "Only the bot owner can do that.",
        'err_generic': "Something went wrong. Please try again.",
        'feature_disabled': "This section has been disabled by the administration.",
        'panel_title': "🛡 Admin Panel\n<blockquote>👑 Owner: {owner}\n👤 Admins: {admins}\n"
                       "🏳 Groups: {groups}\n⚙️ Enabled sections: {on}/{total}</blockquote>",
        'btn_stats': "📊 Statistics",
        'btn_eco': "💰 Economy",
        'btn_mil': "⚔️ Military",
        'btn_features': "⚙️ Enable/disable sections",
        'btn_logs': "🧾 Action log",
        'btn_admins': "👑 Admins",
        'btn_trade_photo': "🖼 Trade photo",
        'btn_war_photo': "🖼 War photos",
        'btn_trade_adm': "🌍 Trade administration",
        'btn_reset': "♻️ Reset a country",
        'btn_game_menu': "🎮 Game menu",
        'btn_back': "🔙 Back",
        'btn_prev': "⬅️ Prev",
        'btn_next': "Next ➡️",
        'btn_per_group': "🏳 Break down by group",
        'no_groups': "No group has registered yet.",
        'stats_title': "📊 Global statistics\n<blockquote>🏳 Groups: {groups}\n👤 Lords: {lords}\n"
                       "💰 Total wealth: {wealth}\n⚔️ Total troops: {troops}\n"
                       "🏭 Total buildings: {buildings}\n"
                       "🚢 Active trades: {active}\n📨 Pending offers: {offered}\n"
                       "✅ Completed trades: {done}</blockquote>",
        'eco_title': "💰 World economy\n<blockquote>{lines}</blockquote>\n"
                     "🏆 Richest: {richest}",
        'mil_title': "⚔️ World military\n<blockquote>{lines}</blockquote>\n"
                     "🏆 Strongest army: {strongest}",
        'group_list_title': "🏳 Choose a group (page {p} of {n}):",
        'group_card': "🏳 <b>{title}</b>\n👤 Lord: {lord}\n\n"
                      "💰 Resources:\n<blockquote>{resources}</blockquote>\n"
                      "⚔️ Army:\n<blockquote>{units}</blockquote>\n"
                      "🏭 Buildings:\n<blockquote>{buildings}</blockquote>\n"
                      "🚢 Trades: active {active} | completed {done}\n"
                      "⚓️ Sea location: {home_sea} | 🏔 Land location: {home_land}",
        'unset': "not set",
        'nobody': "none",
        'feat_title': "⚙️ Bot sections — tap one to toggle it:",
        'feat_on': "✅",
        'feat_off': "❌",
        'feat_toggled': "{name}: {state}",
        'feat_assets': "💰 Assets",
        'feat_upgrade': "🛠️ Upgrade",
        'feat_statement': "🙌 Statement",
        'feat_private_message': "✉️ Private message",
        'feat_treaty': "📜 Treaty",
        'feat_attack': "⚔️ Military campaign",
        'feat_trade': "🚢 World trade",
        'feat_weekly_update': "🔨 Weekly update",
        'feat_setlord': "👤 Lord registration",
        'log_title': "🧾 Admin action log (page {p} of {n}):",
        'log_empty': "No admin action has been recorded yet.",
        'log_row': "▫️ <b>{action}</b> — {actor}\n   {target}{detail}\n   🕓 {ts}",
        'act_asset_edit': "asset edited",
        'act_feature_toggle': "section toggled",
        'act_weekly_update': "weekly update",
        'act_reset_country': "country reset",
        'act_lord_assign': "lord assigned",
        'act_admin_add': "admin added",
        'act_admin_remove': "admin removed",
        'act_trade_photo': "trade photo",
        'act_war_photo': "war photo",
        'act_trade_config': "trade setting",
        'act_chokepoint_owner': "chokepoint owner",
        'act_group_home': "group trade location",
        'adm_title': "👑 Bot admins\n<blockquote>👑 Owner: {owner}</blockquote>\n"
                     "Tap an admin to remove them:",
        'adm_none': "There are no admins besides the owner.",
        'btn_add_admin': "➕ Add admin",
        'adm_add_ask': "Forward a message from the user, or send their numeric id:",
        'adm_added': "✅ {u} was added to the admins.",
        'adm_removed': "🗑 {u} was removed from the admins.",
        'adm_exists': "That user is already an admin.",
        'adm_is_owner': "That user is the bot owner and always has full access.",
        'adm_bad_id': "That is not a valid id. Send a number or forward a message from the user.",
        'reset_pick': "♻️ Which country should be reset to its initial state? (page {p} of {n})",
        'reset_confirm': "♻️ Reset the resources, troops and buildings of <b>{title}</b> "
                         "to their starting values?\n"
                         "Treaties and trade locations are left untouched. "
                         "This cannot be undone.",
        'btn_confirm_reset': "✅ Yes, reset it",
        'reset_done': "♻️ The assets of <b>{title}</b> were reset to their initial values.",
        'war_photo_title': "🖼 Campaign photos — tap one to set it:",
        'wp_land': "🐫 Land campaign photo",
        'wp_sea': "🚢 Sea campaign photo",
        'wp_set': "set",
        'wp_unset': "not set",
        'wp_ask': "Send the photo now:",
        'wp_saved': "✅ The {kind} photo was saved.",
        'wp_cleared': "🗑 The {kind} photo was removed.",
        'wp_not_photo': "That message is not a photo; the operation was cancelled.",
        'btn_wp_clear': "🗑 Remove photo",
        'setlord_group_only': "This command can only be used in groups.",
        'setlord_not_admin': "Only a bot admin can appoint a lord.",
        'setlord_need_reply': "Reply to the message of the player you want to make lord, then send /setlord.",
        'setlord_bot_target': "A bot cannot be registered as a lord.",
        'setlord_done': "👤 {u} has been registered as the lord of this group.",
        'setlord_already': "👤 {u} is already the lord of this group.",
    },
    'tr': {
        'not_admin': "Yönetici değilsiniz.",
        'not_owner': "Bunu yalnızca bot sahibi yapabilir.",
        'err_generic': "Bir hata oluştu. Lütfen tekrar deneyin.",
        'feature_disabled': "Bu bölüm yönetim tarafından devre dışı bırakıldı.",
        'panel_title': "🛡 Yönetim Paneli\n<blockquote>👑 Sahip: {owner}\n👤 Yöneticiler: {admins}\n"
                       "🏳 Gruplar: {groups}\n⚙️ Etkin bölümler: {on}/{total}</blockquote>",
        'btn_stats': "📊 İstatistikler",
        'btn_eco': "💰 Ekonomi",
        'btn_mil': "⚔️ Askeri durum",
        'btn_features': "⚙️ Bölümleri aç/kapat",
        'btn_logs': "🧾 İşlem kaydı",
        'btn_admins': "👑 Yöneticiler",
        'btn_trade_photo': "🖼 Ticaret fotoğrafı",
        'btn_war_photo': "🖼 Savaş fotoğrafları",
        'btn_trade_adm': "🌍 Ticaret yönetimi",
        'btn_reset': "♻️ Ülkeyi sıfırla",
        'btn_game_menu': "🎮 Oyun menüsü",
        'btn_back': "🔙 Geri",
        'btn_prev': "⬅️ Önceki",
        'btn_next': "Sonraki ➡️",
        'btn_per_group': "🏳 Gruplara göre ayır",
        'no_groups': "Henüz hiçbir grup kayıtlı değil.",
        'stats_title': "📊 Genel istatistikler\n<blockquote>🏳 Gruplar: {groups}\n👤 Lordlar: {lords}\n"
                       "💰 Toplam servet: {wealth}\n⚔️ Toplam asker: {troops}\n"
                       "🏭 Toplam bina: {buildings}\n"
                       "🚢 Etkin ticaretler: {active}\n📨 Bekleyen teklifler: {offered}\n"
                       "✅ Tamamlanan ticaretler: {done}</blockquote>",
        'eco_title': "💰 Dünya ekonomisi\n<blockquote>{lines}</blockquote>\n"
                     "🏆 En zengin: {richest}",
        'mil_title': "⚔️ Dünya askeri gücü\n<blockquote>{lines}</blockquote>\n"
                     "🏆 En güçlü ordu: {strongest}",
        'group_list_title': "🏳 Bir grup seçin ({p}/{n}. sayfa):",
        'group_card': "🏳 <b>{title}</b>\n👤 Lord: {lord}\n\n"
                      "💰 Kaynaklar:\n<blockquote>{resources}</blockquote>\n"
                      "⚔️ Ordu:\n<blockquote>{units}</blockquote>\n"
                      "🏭 Binalar:\n<blockquote>{buildings}</blockquote>\n"
                      "🚢 Ticaret: etkin {active} | tamamlanan {done}\n"
                      "⚓️ Deniz konumu: {home_sea} | 🏔 Kara konumu: {home_land}",
        'unset': "ayarlanmadı",
        'nobody': "yok",
        'feat_title': "⚙️ Bot bölümleri — durumu değiştirmek için birine dokunun:",
        'feat_on': "✅",
        'feat_off': "❌",
        'feat_toggled': "{name}: {state}",
        'feat_assets': "💰 Varlıklar",
        'feat_upgrade': "🛠️ Yükseltme",
        'feat_statement': "🙌 Bildiri",
        'feat_private_message': "✉️ Özel mesaj",
        'feat_treaty': "📜 Antlaşma",
        'feat_attack': "⚔️ Askeri sefer",
        'feat_trade': "🚢 Dünya ticareti",
        'feat_weekly_update': "🔨 Haftalık güncelleme",
        'feat_setlord': "👤 Lord kaydı",
        'log_title': "🧾 Yönetici işlem kaydı ({p}/{n}. sayfa):",
        'log_empty': "Henüz hiçbir yönetici işlemi kaydedilmedi.",
        'log_row': "▫️ <b>{action}</b> — {actor}\n   {target}{detail}\n   🕓 {ts}",
        'act_asset_edit': "varlık düzenlendi",
        'act_feature_toggle': "bölüm değiştirildi",
        'act_weekly_update': "haftalık güncelleme",
        'act_reset_country': "ülke sıfırlandı",
        'act_lord_assign': "lord atandı",
        'act_admin_add': "yönetici eklendi",
        'act_admin_remove': "yönetici çıkarıldı",
        'act_trade_photo': "ticaret fotoğrafı",
        'act_war_photo': "savaş fotoğrafı",
        'act_trade_config': "ticaret ayarı",
        'act_chokepoint_owner': "geçit sahipliği",
        'act_group_home': "grup ticaret konumu",
        'adm_title': "👑 Bot yöneticileri\n<blockquote>👑 Sahip: {owner}</blockquote>\n"
                     "Çıkarmak için bir yöneticiye dokunun:",
        'adm_none': "Sahip dışında yönetici yok.",
        'btn_add_admin': "➕ Yönetici ekle",
        'adm_add_ask': "Kullanıcıdan bir mesaj iletin veya sayısal kimliğini gönderin:",
        'adm_added': "✅ {u} yöneticilere eklendi.",
        'adm_removed': "🗑 {u} yöneticilerden çıkarıldı.",
        'adm_exists': "Bu kullanıcı zaten yönetici.",
        'adm_is_owner': "Bu kullanıcı bot sahibidir ve her zaman tam yetkilidir.",
        'adm_bad_id': "Geçerli bir kimlik değil. Bir sayı gönderin veya kullanıcıdan bir mesaj iletin.",
        'reset_pick': "♻️ Hangi ülke başlangıç durumuna döndürülsün? ({p}/{n}. sayfa)",
        'reset_confirm': "♻️ <b>{title}</b> grubunun kaynakları, askerleri ve binaları "
                         "başlangıç değerlerine döndürülsün mü?\n"
                         "Antlaşmalar ve ticaret konumları değişmez. "
                         "Bu işlem geri alınamaz.",
        'btn_confirm_reset': "✅ Evet, sıfırla",
        'reset_done': "♻️ <b>{title}</b> grubunun varlıkları başlangıç değerlerine döndürüldü.",
        'war_photo_title': "🖼 Sefer fotoğrafları — ayarlamak için birine dokunun:",
        'wp_land': "🐫 Kara seferi fotoğrafı",
        'wp_sea': "🚢 Deniz seferi fotoğrafı",
        'wp_set': "ayarlandı",
        'wp_unset': "ayarlanmadı",
        'wp_ask': "Fotoğrafı şimdi gönderin:",
        'wp_saved': "✅ {kind} fotoğrafı kaydedildi.",
        'wp_cleared': "🗑 {kind} fotoğrafı kaldırıldı.",
        'wp_not_photo': "Bu mesaj bir fotoğraf değil; işlem iptal edildi.",
        'btn_wp_clear': "🗑 Fotoğrafı kaldır",
        'setlord_group_only': "Bu komut yalnızca gruplarda kullanılabilir.",
        'setlord_not_admin': "Yalnızca bir bot yöneticisi lord atayabilir.",
        'setlord_need_reply': "Lord yapmak istediğiniz oyuncunun mesajını yanıtlayıp /setlord gönderin.",
        'setlord_bot_target': "Bir bot lord olarak kaydedilemez.",
        'setlord_done': "👤 {u} bu grubun lordu olarak kaydedildi.",
        'setlord_already': "👤 {u} zaten bu grubun lordu.",
    },
}
