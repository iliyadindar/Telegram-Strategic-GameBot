# -*- coding: utf-8 -*-
"""Localised text for the admin dashboard.

Kept apart from admin_panel.py so the panel file stays about behaviour. Every
language must define exactly the same key set — admin_panel.init() asserts it.

Asset names are *not* here: resources, units and buildings are data now, so
their labels live in the asset_labels table. See asset_catalog.py.
"""

# ---------------------------------------------------------------------------
# Toggleable features. The key is what main*.py passes to feature_enabled().
# ---------------------------------------------------------------------------

FEATURES = ('assets', 'upgrade', 'statement', 'private_message', 'treaty',
            'attack', 'trade', 'weekly_update', 'setlord')

# Actions written to admin_log; label lives under 'act_<name>' in STRINGS.
ACTIONS = ('asset_edit', 'feature_toggle', 'weekly_update', 'reset_country', 'lord_assign',
           'lord_unassign', 'group_unassign',
           'admin_add', 'admin_remove', 'trade_photo', 'war_photo',
           'trade_config', 'chokepoint_owner', 'group_home',
           'asset_add', 'asset_type_edit', 'asset_hide', 'asset_cost')

# CatalogError codes that get their own message; anything else falls back to
# 'err_generic'. Kept next to the strings so the two stay in step.
CATALOG_ERRORS = ('bad_key', 'exists', 'reserved', 'column_exists', 'bad_kind', 'builtin',
                  'bad_produces', 'not_a_building', 'not_a_resource', 'bad_resource', 'unknown',
                  'in_transit', 'guard_unavailable', 'bad_direction')

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
        'act_lord_unassign': "برکناری لرد",
        'act_group_unassign': "بازنشستگی گروه",
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
        'unsetlord_not_admin': "فقط ادمین ربات می‌تواند لردی را پس بگیرد.",
        'unsetlord_not_owner': "برای بازنشسته کردن کل گروه باید مالک ربات باشید.",
        'unsetlord_no_lords': "این گروه اصلاً لردی ندارد.",
        'unsetlord_done': "🚫 لردی {u} پس گرفته شد و دارایی‌های کشورش پاک شد.",
        'btn_unset_group': "🔥 بله، این گروه بازنشسته شود",
        'unsetlord_group_confirm': "🔥 <b>بازنشستگی «{title}»</b>\n<blockquote>{n} لرد این گروه "
                                   "و تمام دارایی‌ها، ارتش و ساختمان‌هایشان برای همیشه حذف "
                                   "می‌شوند.\n\n⚠️ برای برکناری فقط یک نفر، روی پیام او ریپلای "
                                   "کنید و /unsetlord بزنید.</blockquote>",
        'unsetlord_group_done': "🔥 «{title}» بازنشسته شد؛ {n} لرد حذف شدند.",
        'unsetlord_err_not_lord': "این کاربر لرد این گروه نیست.",
        'unsetlord_err_no_lords': "این گروه اصلاً لردی ندارد.",
        'unsetlord_err_in_trade': "همین حالا محموله‌ای در راه این کشور است. تا رسیدن آن "
                                  "نمی‌توان لردش را برداشت.",
        'unsetlord_err_guard_unavailable': "وضعیت محموله‌های در راه مشخص نشد، پس چیزی حذف نشد.",
        'act_asset_add': "افزودن نوع دارایی",
        'act_asset_type_edit': "ویرایش نوع دارایی",
        'act_asset_hide': "حذف نوع دارایی",
        'act_asset_cost': "هزینه ارتقا",
        'btn_catalog': "🧩 دارایی‌ها و واحدها",
        'cat_title': "🧩 فهرست دارایی‌های بازی — یک دسته را انتخاب کنید:\n"
                     "<blockquote>📦 منابع: {resources}\n⚔️ واحدها: {units}\n"
                     "🏭 ساختمان‌ها: {buildings}</blockquote>",
        'kind_resource': "📦 منابع",
        'kind_unit': "⚔️ واحدها",
        'kind_building': "🏭 ساختمان‌ها",
        'cat_list_title': "{kind} (صفحه {p} از {n}) — برای ویرایش روی یکی بزنید:",
        'cat_hidden_mark': "🚫",
        'btn_cat_add': "➕ افزودن نوع جدید",
        'cat_entry': "🧩 <b>{label}</b>\n<blockquote>🔑 کلید: <code>{key}</code>\n"
                     "📁 دسته: {kind}\n🎁 مقدار اولیه: {default}\n{extra}</blockquote>{note}",
        'cat_extra_building': "🏭 تولید می‌کند: {produces}\n📈 تولید هر سطح در هفته: {output}\n"
                              "💸 هزینه ارتقا: {costs}",
        'cat_extra_resource': "🚢 قابل تجارت: {tradeable}",
        'cat_produces_none': "چیزی تولید نمی‌کند",
        'cat_costs_none': "رایگان",
        'cat_builtin_note': "\n\nℹ️ این نوع همراه بازی آمده است؛ قابل ویرایش هست اما حذف نمی‌شود.",
        'cat_hidden_note': "\n\n🚫 این نوع از بازی حذف شده است. مقادیر ذخیره‌شده دست‌نخورده‌اند و "
                           "با بازگرداندن دوباره ظاهر می‌شوند.",
        'btn_cat_rename': "✏️ تغییر نام",
        'btn_cat_default': "🎁 مقدار اولیه",
        'btn_cat_output': "📈 تولید",
        'btn_cat_tradeable': "🚢 قابل تجارت",
        'btn_cat_costs': "💸 هزینه ارتقا",
        'btn_cat_hide': "🗑 حذف از بازی",
        'btn_cat_unhide': "♻️ بازگرداندن به بازی",
        'cat_ask_key': "کلید انگلیسی نوع جدید را بفرستید (حروف کوچک و زیرخط، مثل archers):",
        'cat_ask_label': "نام نمایشی به {lang} را بفرستید (می‌توانید ایموجی هم بگذارید):",
        'cat_ask_default': "مقدار اولیه هر کشور برای این نوع را وارد کنید:",
        'cat_bad_number': "مقدار معتبر نیست. یک عدد صحیح غیرمنفی بفرستید.",
        'cat_ask_output': "در هر آپ هفتگی، هر سطح این ساختمان چه مقدار تولید کند؟",
        'cat_ask_cost': "هزینه ارتقا بر حسب {res} چقدر باشد؟ (صفر یعنی نیازی نیست)",
        'cat_pick_produces': "این ساختمان چه چیزی تولید می‌کند؟",
        'btn_produces_none': "🚫 هیچ‌چیز",
        'cat_costs_title': "💸 هزینه یک سطح از {label} — برای تغییر روی هر منبع بزنید:",
        'cat_added': "✅ «{label}» به بازی اضافه شد.",
        'cat_renamed': "✅ نام‌ها به‌روزرسانی شد.",
        'cat_default_set': "✅ مقدار اولیه روی {value} تنظیم شد.",
        'cat_output_set': "✅ تولید به‌روزرسانی شد.",
        'cat_tradeable_on': "✅ این منبع اکنون قابل تجارت است.",
        'cat_tradeable_off': "🚫 این منبع دیگر قابل تجارت نیست.",
        'cat_cost_set': "✅ هزینه به‌روزرسانی شد.",
        'cat_hidden': "🗑 «{label}» از بازی حذف شد.",
        'cat_unhidden': "♻️ «{label}» به بازی بازگشت.",
        'cat_lang_fa': "فارسی",
        'cat_lang_en': "انگلیسی",
        'cat_lang_tr': "ترکی",
        'cat_yes': "بله",
        'cat_no': "خیر",
        'cat_err_bad_key': "❌ کلید نامعتبر است. فقط حروف کوچک انگلیسی، عدد و زیرخط؛ "
                           "با حرف شروع شود و بین ۲ تا ۳۱ کاراکتر باشد.",
        'cat_err_exists': "❌ نوعی با این کلید از قبل وجود دارد.",
        'cat_err_reserved': "❌ این کلید رزرو شده است.",
        'cat_err_column_exists': "❌ ستونی با این نام از قبل در پایگاه داده هست.",
        'cat_err_bad_kind': "❌ دسته نامعتبر است.",
        'cat_err_builtin': "❌ انواع پیش‌فرض بازی قابل حذف نیستند.",
        'cat_err_bad_produces': "❌ یک ساختمان فقط می‌تواند منبع یا واحد تولید کند.",
        'cat_err_not_a_building': "❌ این مورد ساختمان نیست.",
        'cat_err_not_a_resource': "❌ این مورد منبع نیست.",
        'cat_err_bad_resource': "❌ منبع نامعتبر است.",
        'cat_err_unknown': "❌ چنین نوعی وجود ندارد.",
        'act_asset_remove': "حذف کامل نوع دارایی",
        'act_catalog_reset': "بازنشانی کامل فهرست دارایی‌ها",
        'act_log_clear': "پاک‌سازی گزارش اقدامات",
        'btn_cat_up': "⬆️ بالاتر",
        'btn_cat_down': "⬇️ پایین‌تر",
        'cat_rank': "📍 جایگاه در فهرست: {place} از {total}",
        'cat_at_top': "همین حالا اول فهرست است.",
        'cat_at_bottom': "همین حالا آخر فهرست است.",
        'cat_moved': "✅ جابه‌جا شد.",
        'btn_cat_delete': "❌ حذف کامل و همیشگی",
        'btn_cat_delete_yes': "🔥 بله، برای همیشه حذف کن",
        'cat_delete_confirm': "🔥 <b>حذف کامل «{label}»</b>\n<blockquote>کلید <code>{key}</code> "
                              "به‌طور کامل از پایگاه داده پاک می‌شود و مقدار ذخیره‌شدهٔ همهٔ "
                              "کشورها برای آن از بین می‌رود.\n\n{holders}\n\n"
                              "⚠️ این کار برگشت‌پذیر نیست. اگر فقط می‌خواهید موقتاً از بازی "
                              "خارج شود، به‌جای این از «حذف از بازی» استفاده کنید.</blockquote>",
        'cat_delete_holders': "📊 {n} کشور مقدار غیرصفر برای این نوع دارند.",
        'cat_delete_holders_none': "📊 هیچ کشوری مقدار غیرصفری برای این نوع ندارد.",
        'cat_deleted': "🔥 «{label}» برای همیشه حذف شد.",
        'cat_deleted_kept_column': "🔥 «{label}» از بازی حذف شد، اما نسخهٔ SQLite این سرور "
                                   "قدیمی‌تر از ۳٫۳۵ است و ستون آن در پایگاه داده باقی ماند. "
                                   "این ستون دیگر جایی استفاده نمی‌شود.",
        'cat_err_in_transit': "❌ همین حالا یک محمولهٔ تجاری این مورد را حمل می‌کند. "
                              "تا رسیدن یا لغو آن محموله نمی‌توان حذفش کرد.",
        'cat_err_guard_unavailable': "❌ وضعیت محموله‌های در راه مشخص نشد، پس حذف انجام نشد. "
                                     "دوباره تلاش کنید.",
        'cat_err_bad_direction': "❌ جهت جابه‌جایی نامعتبر است.",
        'btn_factory': "🔥 بازنشانی کامل فهرست دارایی‌ها",
        'btn_confirm_factory': "🔥 بله، همه را به حالت اولیه برگردان",
        'factory_confirm': "🔥 <b>بازنشانی کامل فهرست دارایی‌ها</b>\n<blockquote>"
                           "{customs}\n\nهمهٔ انواع پیش‌فرض (نام، مقدار اولیه، ترتیب، تولید و "
                           "هزینهٔ ارتقا) دقیقاً به همان چیزی که بازی با آن منتشر شده بازمی‌گردند، "
                           "و گزارش اقدامات هم پاک می‌شود.\n\n"
                           "✅ دارایی فعلی کشورها دست‌نخورده می‌ماند.\n"
                           "⚠️ این کار برگشت‌پذیر نیست.</blockquote>",
        'factory_customs': "🗑 این انواع افزوده‌شده برای همیشه حذف می‌شوند: {keys}",
        'factory_customs_none': "🗑 هیچ نوع افزوده‌شده‌ای برای حذف وجود ندارد.",
        'factory_done': "🔥 فهرست دارایی‌ها به حالت اولیه بازگشت و گزارش اقدامات پاک شد.",
        'factory_kept': "\n\nℹ️ ستون این موارد در پایگاه داده باقی ماند (SQLite قدیمی): {keys}",
        'btn_log_clear': "🧹 پاک کردن گزارش",
        'btn_confirm_log_clear': "🧹 بله، گزارش را پاک کن",
        'log_clear_confirm': "🧹 <b>پاک کردن گزارش اقدامات</b>\n<blockquote>هر {n} ردیف گزارش "
                             "حذف می‌شود و صفحهٔ گزارش خالی خواهد بود.\n\n"
                             "ℹ️ به همهٔ ادمین‌ها پیام داده می‌شود که چه کسی گزارش را پاک کرده "
                             "است.\n⚠️ این کار برگشت‌پذیر نیست.</blockquote>",
        'log_clear_done': "🧹 گزارش اقدامات پاک شد ({n} ردیف).",
        'log_clear_notice': "🧹 گزارش اقدامات توسط {u} پاک شد ({n} ردیف).",
        'factory_notice': "🔥 {u} فهرست دارایی‌ها را به حالت اولیه بازگرداند و گزارش اقدامات "
                          "را پاک کرد ({n} ردیف).",
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
        'act_lord_unassign': "lord removed",
        'act_group_unassign': "group retired",
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
        'unsetlord_not_admin': "Only a bot admin can take a lordship back.",
        'unsetlord_not_owner': "Retiring a whole group is for the bot owner only.",
        'unsetlord_no_lords': "This group has no lord to remove.",
        'unsetlord_done': "🚫 {u} is no longer a lord; their country's assets are gone.",
        'btn_unset_group': "🔥 Yes, retire this group",
        'unsetlord_group_confirm': "🔥 <b>Retire “{title}”</b>\n<blockquote>Its {n} lord(s) and "
                                   "every resource, unit and building they hold will be deleted "
                                   "for good.\n\n⚠️ To remove just one person, reply to their "
                                   "message with /unsetlord instead.</blockquote>",
        'unsetlord_group_done': "🔥 “{title}” has been retired; {n} lord(s) removed.",
        'unsetlord_err_not_lord': "That user is not a lord of this group.",
        'unsetlord_err_no_lords': "This group has no lord to remove.",
        'unsetlord_err_in_trade': "A shipment is on its way to this country right now. Its lord "
                                  "cannot be removed until that trade arrives.",
        'unsetlord_err_guard_unavailable': "Could not check what is in transit, so nothing was "
                                           "deleted.",
        'act_asset_add': "asset type added",
        'act_asset_type_edit': "asset type edited",
        'act_asset_hide': "asset type removed",
        'act_asset_cost': "upgrade cost",
        'btn_catalog': "🧩 Assets & units",
        'cat_title': "🧩 The game's asset catalog — pick a category:\n"
                     "<blockquote>📦 Resources: {resources}\n⚔️ Units: {units}\n"
                     "🏭 Buildings: {buildings}</blockquote>",
        'kind_resource': "📦 Resources",
        'kind_unit': "⚔️ Units",
        'kind_building': "🏭 Buildings",
        'cat_list_title': "{kind} (page {p} of {n}) — tap one to edit it:",
        'cat_hidden_mark': "🚫",
        'btn_cat_add': "➕ Add a new type",
        'cat_entry': "🧩 <b>{label}</b>\n<blockquote>🔑 Key: <code>{key}</code>\n"
                     "📁 Category: {kind}\n🎁 Starting amount: {default}\n{extra}</blockquote>{note}",
        'cat_extra_building': "🏭 Produces: {produces}\n📈 Per level per week: {output}\n"
                              "💸 Upgrade cost: {costs}",
        'cat_extra_resource': "🚢 Tradeable: {tradeable}",
        'cat_produces_none': "nothing",
        'cat_costs_none': "free",
        'cat_builtin_note': "\n\nℹ️ This type shipped with the game — it can be retuned but not removed.",
        'cat_hidden_note': "\n\n🚫 This type has been removed from the game. Its stored values are "
                           "untouched and come back if you restore it.",
        'btn_cat_rename': "✏️ Rename",
        'btn_cat_default': "🎁 Starting amount",
        'btn_cat_output': "📈 Production",
        'btn_cat_tradeable': "🚢 Tradeable",
        'btn_cat_costs': "💸 Upgrade cost",
        'btn_cat_hide': "🗑 Remove from the game",
        'btn_cat_unhide': "♻️ Restore to the game",
        'cat_ask_key': "Send the internal key for the new type (lowercase and underscores, e.g. archers):",
        'cat_ask_label': "Send the display name in {lang} (emoji are welcome):",
        'cat_ask_default': "How much of this should each country start with?",
        'cat_bad_number': "That is not a valid amount. Send a non-negative whole number.",
        'cat_ask_output': "How much should each level of this building produce per weekly update?",
        'cat_ask_cost': "How much {res} should one upgrade cost? (zero means none)",
        'cat_pick_produces': "What does this building produce?",
        'btn_produces_none': "🚫 Nothing",
        'cat_costs_title': "💸 Cost of one level of {label} — tap a resource to change it:",
        'cat_added': "✅ “{label}” was added to the game.",
        'cat_renamed': "✅ The names were updated.",
        'cat_default_set': "✅ The starting amount is now {value}.",
        'cat_output_set': "✅ Production updated.",
        'cat_tradeable_on': "✅ This resource can now be traded.",
        'cat_tradeable_off': "🚫 This resource can no longer be traded.",
        'cat_cost_set': "✅ The cost was updated.",
        'cat_hidden': "🗑 “{label}” was removed from the game.",
        'cat_unhidden': "♻️ “{label}” is back in the game.",
        'cat_lang_fa': "Persian",
        'cat_lang_en': "English",
        'cat_lang_tr': "Turkish",
        'cat_yes': "yes",
        'cat_no': "no",
        'cat_err_bad_key': "❌ Invalid key. Lowercase letters, digits and underscores only; "
                           "must start with a letter and be 2 to 31 characters long.",
        'cat_err_exists': "❌ A type with that key already exists.",
        'cat_err_reserved': "❌ That key is reserved.",
        'cat_err_column_exists': "❌ A database column with that name already exists.",
        'cat_err_bad_kind': "❌ Invalid category.",
        'cat_err_builtin': "❌ Types that shipped with the game cannot be removed.",
        'cat_err_bad_produces': "❌ A building can only produce a resource or a unit.",
        'cat_err_not_a_building': "❌ That entry is not a building.",
        'cat_err_not_a_resource': "❌ That entry is not a resource.",
        'cat_err_bad_resource': "❌ Invalid resource.",
        'cat_err_unknown': "❌ No such type.",
        'act_asset_remove': "asset type destroyed",
        'act_catalog_reset': "asset catalog factory reset",
        'act_log_clear': "action log cleared",
        'btn_cat_up': "⬆️ Move up",
        'btn_cat_down': "⬇️ Move down",
        'cat_rank': "📍 Place in the list: {place} of {total}",
        'cat_at_top': "Already first in the list.",
        'cat_at_bottom': "Already last in the list.",
        'cat_moved': "✅ Moved.",
        'btn_cat_delete': "❌ Delete permanently",
        'btn_cat_delete_yes': "🔥 Yes, delete it for good",
        'cat_delete_confirm': "🔥 <b>Permanently delete “{label}”</b>\n<blockquote>The key "
                              "<code>{key}</code> will be erased from the database, and every "
                              "country's stored value for it goes with it.\n\n{holders}\n\n"
                              "⚠️ This cannot be undone. To take it out of the game "
                              "temporarily, use “Remove from the game” instead.</blockquote>",
        'cat_delete_holders': "📊 {n} countries hold a non-zero value for this type.",
        'cat_delete_holders_none': "📊 No country holds a non-zero value for this type.",
        'cat_deleted': "🔥 “{label}” was deleted for good.",
        'cat_deleted_kept_column': "🔥 “{label}” is out of the game, but this server's SQLite is "
                                   "older than 3.35, so its column stayed in the database. "
                                   "Nothing reads that column any more.",
        'cat_err_in_transit': "❌ A trade in flight is carrying this right now. It cannot be "
                              "deleted until that shipment arrives or is cancelled.",
        'cat_err_guard_unavailable': "❌ Could not check what is in flight, so nothing was "
                                     "deleted. Please try again.",
        'cat_err_bad_direction': "❌ Invalid direction.",
        'btn_factory': "🔥 Factory-reset the asset catalog",
        'btn_confirm_factory': "🔥 Yes, restore everything to shipped values",
        'factory_confirm': "🔥 <b>Factory-reset the asset catalog</b>\n<blockquote>{customs}\n\n"
                           "Every shipped type (name, starting amount, order, production and "
                           "upgrade cost) goes back to exactly what the game shipped with, and "
                           "the action log is cleared.\n\n"
                           "✅ Countries keep their current assets.\n"
                           "⚠️ This cannot be undone.</blockquote>",
        'factory_customs': "🗑 These added types will be deleted for good: {keys}",
        'factory_customs_none': "🗑 There are no added types to delete.",
        'factory_done': "🔥 The asset catalog is back to its shipped state and the action log "
                        "is empty.",
        'factory_kept': "\n\nℹ️ These kept their database column (old SQLite): {keys}",
        'btn_log_clear': "🧹 Clear the log",
        'btn_confirm_log_clear': "🧹 Yes, clear the log",
        'log_clear_confirm': "🧹 <b>Clear the action log</b>\n<blockquote>All {n} rows are "
                             "deleted and the log screen will be empty.\n\n"
                             "ℹ️ Every admin gets a message saying who cleared it.\n"
                             "⚠️ This cannot be undone.</blockquote>",
        'log_clear_done': "🧹 Action log cleared ({n} rows).",
        'log_clear_notice': "🧹 {u} cleared the action log ({n} rows).",
        'factory_notice': "🔥 {u} factory-reset the asset catalog and cleared the action log "
                          "({n} rows).",
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
        'act_lord_unassign': "lordluk geri alındı",
        'act_group_unassign': "grup emekliye ayrıldı",
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
        'unsetlord_not_admin': "Bir lordluğu yalnızca bot yöneticisi geri alabilir.",
        'unsetlord_not_owner': "Bir grubu tümüyle emekliye ayırmak yalnızca bot sahibine özeldir.",
        'unsetlord_no_lords': "Bu grupta kaldırılacak bir lord yok.",
        'unsetlord_done': "🚫 {u} artık lord değil; ülkesinin varlıkları silindi.",
        'btn_unset_group': "🔥 Evet, bu grubu emekliye ayır",
        'unsetlord_group_confirm': "🔥 <b>“{title}” emekliye ayrılsın mı?</b>\n<blockquote>{n} "
                                   "lordu ve sahip oldukları tüm kaynaklar, birlikler ve "
                                   "binalar kalıcı olarak silinecek.\n\n⚠️ Yalnızca bir kişiyi "
                                   "kaldırmak için onun mesajını yanıtlayıp /unsetlord "
                                   "gönderin.</blockquote>",
        'unsetlord_group_done': "🔥 “{title}” emekliye ayrıldı; {n} lord kaldırıldı.",
        'unsetlord_err_not_lord': "Bu kullanıcı bu grubun lordu değil.",
        'unsetlord_err_no_lords': "Bu grupta kaldırılacak bir lord yok.",
        'unsetlord_err_in_trade': "Şu anda bu ülkeye bir sevkiyat yolda. O ticaret varana kadar "
                                  "lordu kaldırılamaz.",
        'unsetlord_err_guard_unavailable': "Yolda ne olduğu kontrol edilemedi, bu yüzden hiçbir "
                                           "şey silinmedi.",
        'act_asset_add': "varlık türü eklendi",
        'act_asset_type_edit': "varlık türü düzenlendi",
        'act_asset_hide': "varlık türü kaldırıldı",
        'act_asset_cost': "yükseltme maliyeti",
        'btn_catalog': "🧩 Varlıklar ve birimler",
        'cat_title': "🧩 Oyunun varlık kataloğu — bir kategori seçin:\n"
                     "<blockquote>📦 Kaynaklar: {resources}\n⚔️ Birimler: {units}\n"
                     "🏭 Binalar: {buildings}</blockquote>",
        'kind_resource': "📦 Kaynaklar",
        'kind_unit': "⚔️ Birimler",
        'kind_building': "🏭 Binalar",
        'cat_list_title': "{kind} ({p}/{n}. sayfa) — düzenlemek için birine dokunun:",
        'cat_hidden_mark': "🚫",
        'btn_cat_add': "➕ Yeni tür ekle",
        'cat_entry': "🧩 <b>{label}</b>\n<blockquote>🔑 Anahtar: <code>{key}</code>\n"
                     "📁 Kategori: {kind}\n🎁 Başlangıç miktarı: {default}\n{extra}</blockquote>{note}",
        'cat_extra_building': "🏭 Ürettiği: {produces}\n📈 Seviye başına haftalık: {output}\n"
                              "💸 Yükseltme maliyeti: {costs}",
        'cat_extra_resource': "🚢 Ticarete açık: {tradeable}",
        'cat_produces_none': "hiçbir şey",
        'cat_costs_none': "ücretsiz",
        'cat_builtin_note': "\n\nℹ️ Bu tür oyunla birlikte gelir — ayarlanabilir ama kaldırılamaz.",
        'cat_hidden_note': "\n\n🚫 Bu tür oyundan kaldırıldı. Kayıtlı değerleri korunuyor ve "
                           "geri getirildiğinde yeniden görünecek.",
        'btn_cat_rename': "✏️ Yeniden adlandır",
        'btn_cat_default': "🎁 Başlangıç miktarı",
        'btn_cat_output': "📈 Üretim",
        'btn_cat_tradeable': "🚢 Ticarete açık",
        'btn_cat_costs': "💸 Yükseltme maliyeti",
        'btn_cat_hide': "🗑 Oyundan kaldır",
        'btn_cat_unhide': "♻️ Oyuna geri getir",
        'cat_ask_key': "Yeni tür için dahili anahtarı gönderin (küçük harf ve alt çizgi, örn. archers):",
        'cat_ask_label': "{lang} dilindeki görünen adı gönderin (emoji kullanabilirsiniz):",
        'cat_ask_default': "Her ülke bundan ne kadarla başlasın?",
        'cat_bad_number': "Geçersiz miktar. Negatif olmayan bir tam sayı gönderin.",
        'cat_ask_output': "Bu binanın her seviyesi haftalık güncellemede ne kadar üretsin?",
        'cat_ask_cost': "Bir yükseltme ne kadar {res} tutsun? (sıfır: gerekmez)",
        'cat_pick_produces': "Bu bina ne üretiyor?",
        'btn_produces_none': "🚫 Hiçbir şey",
        'cat_costs_title': "💸 {label} için bir seviyenin maliyeti — değiştirmek için bir kaynağa dokunun:",
        'cat_added': "✅ “{label}” oyuna eklendi.",
        'cat_renamed': "✅ Adlar güncellendi.",
        'cat_default_set': "✅ Başlangıç miktarı artık {value}.",
        'cat_output_set': "✅ Üretim güncellendi.",
        'cat_tradeable_on': "✅ Bu kaynak artık ticarete açık.",
        'cat_tradeable_off': "🚫 Bu kaynak artık ticarete açık değil.",
        'cat_cost_set': "✅ Maliyet güncellendi.",
        'cat_hidden': "🗑 “{label}” oyundan kaldırıldı.",
        'cat_unhidden': "♻️ “{label}” yeniden oyunda.",
        'cat_lang_fa': "Farsça",
        'cat_lang_en': "İngilizce",
        'cat_lang_tr': "Türkçe",
        'cat_yes': "evet",
        'cat_no': "hayır",
        'cat_err_bad_key': "❌ Geçersiz anahtar. Yalnızca küçük harf, rakam ve alt çizgi; "
                           "bir harfle başlamalı ve 2-31 karakter olmalı.",
        'cat_err_exists': "❌ Bu anahtara sahip bir tür zaten var.",
        'cat_err_reserved': "❌ Bu anahtar ayrılmış.",
        'cat_err_column_exists': "❌ Bu adda bir veritabanı sütunu zaten var.",
        'cat_err_bad_kind': "❌ Geçersiz kategori.",
        'cat_err_builtin': "❌ Oyunla gelen türler kaldırılamaz.",
        'cat_err_bad_produces': "❌ Bir bina yalnızca kaynak veya birim üretebilir.",
        'cat_err_not_a_building': "❌ Bu girdi bir bina değil.",
        'cat_err_not_a_resource': "❌ Bu girdi bir kaynak değil.",
        'cat_err_bad_resource': "❌ Geçersiz kaynak.",
        'cat_err_unknown': "❌ Böyle bir tür yok.",
        'act_asset_remove': "varlık türü kalıcı olarak silindi",
        'act_catalog_reset': "varlık kataloğu fabrika ayarlarına döndürüldü",
        'act_log_clear': "işlem kaydı temizlendi",
        'btn_cat_up': "⬆️ Yukarı taşı",
        'btn_cat_down': "⬇️ Aşağı taşı",
        'cat_rank': "📍 Listedeki yeri: {total} içinde {place}",
        'cat_at_top': "Zaten listenin başında.",
        'cat_at_bottom': "Zaten listenin sonunda.",
        'cat_moved': "✅ Taşındı.",
        'btn_cat_delete': "❌ Kalıcı olarak sil",
        'btn_cat_delete_yes': "🔥 Evet, tamamen sil",
        'cat_delete_confirm': "🔥 <b>“{label}” kalıcı olarak silinsin mi?</b>\n<blockquote>"
                              "<code>{key}</code> anahtarı veritabanından tamamen silinecek ve "
                              "her ülkenin bu tür için kayıtlı değeri de gidecek.\n\n{holders}"
                              "\n\n⚠️ Bu geri alınamaz. Yalnızca geçici olarak oyundan çıkarmak "
                              "için “Oyundan kaldır” seçeneğini kullanın.</blockquote>",
        'cat_delete_holders': "📊 {n} ülkenin bu tür için sıfırdan farklı değeri var.",
        'cat_delete_holders_none': "📊 Hiçbir ülkenin bu tür için sıfırdan farklı değeri yok.",
        'cat_deleted': "🔥 “{label}” kalıcı olarak silindi.",
        'cat_deleted_kept_column': "🔥 “{label}” oyundan çıktı, ancak bu sunucudaki SQLite "
                                   "3.35'ten eski olduğu için sütunu veritabanında kaldı. "
                                   "Artık o sütunu hiçbir yer okumuyor.",
        'cat_err_in_transit': "❌ Yolda olan bir ticaret şu anda bunu taşıyor. Sevkiyat varana "
                              "veya iptal edilene kadar silinemez.",
        'cat_err_guard_unavailable': "❌ Yolda ne olduğu kontrol edilemedi, bu yüzden hiçbir şey "
                                     "silinmedi. Lütfen tekrar deneyin.",
        'cat_err_bad_direction': "❌ Geçersiz yön.",
        'btn_factory': "🔥 Varlık kataloğunu fabrika ayarlarına döndür",
        'btn_confirm_factory': "🔥 Evet, her şeyi ilk haline döndür",
        'factory_confirm': "🔥 <b>Varlık kataloğunu fabrika ayarlarına döndür</b>\n<blockquote>"
                           "{customs}\n\nOyunla gelen her tür (ad, başlangıç miktarı, sıra, "
                           "üretim ve yükseltme maliyeti) tam olarak oyunun çıktığı haline "
                           "döner ve işlem kaydı temizlenir.\n\n"
                           "✅ Ülkelerin mevcut varlıkları korunur.\n"
                           "⚠️ Bu geri alınamaz.</blockquote>",
        'factory_customs': "🗑 Şu eklenen türler kalıcı olarak silinecek: {keys}",
        'factory_customs_none': "🗑 Silinecek eklenmiş tür yok.",
        'factory_done': "🔥 Varlık kataloğu ilk haline döndü ve işlem kaydı boşaltıldı.",
        'factory_kept': "\n\nℹ️ Şunların veritabanı sütunu kaldı (eski SQLite): {keys}",
        'btn_log_clear': "🧹 Kaydı temizle",
        'btn_confirm_log_clear': "🧹 Evet, kaydı temizle",
        'log_clear_confirm': "🧹 <b>İşlem kaydını temizle</b>\n<blockquote>{n} satırın tamamı "
                             "silinecek ve kayıt ekranı boş olacak.\n\n"
                             "ℹ️ Kaydı kimin temizlediği tüm yöneticilere bildirilir.\n"
                             "⚠️ Bu geri alınamaz.</blockquote>",
        'log_clear_done': "🧹 İşlem kaydı temizlendi ({n} satır).",
        'log_clear_notice': "🧹 {u} işlem kaydını temizledi ({n} satır).",
        'factory_notice': "🔥 {u} varlık kataloğunu fabrika ayarlarına döndürdü ve işlem kaydını "
                          "temizledi ({n} satır).",
    },
}
