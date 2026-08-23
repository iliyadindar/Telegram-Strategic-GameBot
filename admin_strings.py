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
           'reset_all', 'country_restore', 'country_asset', 'bot_switch',
           'statement', 'campaign',
           'trade_config', 'chokepoint_owner', 'group_home', 'trade_mode',
           'asset_add', 'asset_type_edit', 'asset_hide', 'asset_cost', 'asset_kind_order',
           'asset_level')

# CatalogError codes that get their own message; anything else falls back to
# 'err_generic'. Kept next to the strings so the two stay in step.
CATALOG_ERRORS = ('bad_key', 'exists', 'reserved', 'column_exists', 'bad_kind', 'engine_key',
                  'bad_produces', 'not_a_building', 'not_a_resource', 'bad_resource', 'unknown',
                  'in_transit', 'guard_unavailable', 'bad_direction', 'bad_level',
                  'bad_output')

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
        # {sections} is one "header + <blockquote>" block per kind, in the order
        # asset_catalog.kind_order() gives.
        'group_card': "🏳 <b>{title}</b>\n👤 لرد: {lord}\n\n"
                      "{sections}\n"
                      "🚢 تجارت: فعال {active} | کامل‌شده {done}\n"
                      "⚓️ موقعیت دریایی: {home_sea} | 🏔 موقعیت زمینی: {home_land}",
        'sec_resource': "💰 دارایی:",
        'sec_unit': "⚔️ ارتش:",
        'sec_building': "🏭 ساختمان‌ها:",
        'unset': "تعیین نشده",
        'nobody': "ندارد",
        'bot_off': "⛔️ ربات موقتاً برای بازیکنان بسته است. با مدیریت تماس بگیرید.",
        'bot_turned_on': "✅ ربات برای بازیکنان باز شد.",
        'bot_turned_off': "⛔️ ربات برای بازیکنان بسته شد. پنل مدیریت همچنان کار می‌کند.",
        'bot_on_already': "ربات از قبل باز بود.",
        'bot_off_already': "ربات از قبل بسته بود.",
        'btn_players_on': "🟢 ربات برای بازیکنان باز است — برای بستن بزنید",
        'btn_players_off': "⛔️ ربات برای بازیکنان بسته است — برای باز کردن بزنید",
        'panel_closed': "\n\n⛔️ ربات برای بازیکنان بسته است (/on برای باز کردن).",
        'act_bot_switch': "باز/بسته کردن ربات",
        'act_statement': "بیانیه",
        'act_campaign': "لشکرکشی",
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
        'act_trade_mode': "باز/بسته کردن تجارت کشور",
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
        'btn_reset_all': "♻️ بازگردانی همه کشورها ({n} کشور)",
        'btn_confirm_reset_all': "✅ بله، همه را بازگردان",
        'reset_all_confirm': "♻️ <b>بازگردانی همه کشورها</b>\n<blockquote>دارایی‌ها، ارتش و "
                             "ساختمان‌های هر {n} کشور به مقدار اولیه برمی‌گردد:\n{names}\n\n"
                             "این کار فقط اعداد کشورها را صفر می‌کند؛ به فهرست دارایی‌ها و "
                             "تنظیمات بازی دست نمی‌زند.</blockquote>",
        'reset_all_done': "♻️ هر {n} کشور به حالت اولیه برگشتند.",
        'setlord_restored': "\n♻️ دارایی‌های قبلی این کشور به ایشان تحویل داده شد.",
        'act_reset_all': "بازگردانی همه کشورها",
        'act_country_restore': "تحویل دارایی به لرد جدید",
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
        'unsetlord_done': "🚫 لردی {u} پس گرفته شد. دارایی‌های کشور محفوظ می‌ماند و به لرد بعدی می‌رسد.",
        'btn_unset_group': "🔥 بله، این گروه بازنشسته شود",
        'unsetlord_group_confirm': "🔥 <b>بازنشستگی «{title}»</b>\n<blockquote>{n} لرد این گروه "
                                   "برداشته می‌شوند، اما دارایی‌ها، ارتش و ساختمان‌های کشور "
                                   "نگه داشته می‌شوند و به لرد بعدی همین گروه می‌رسند.\n\n"
                                   "♻️ اگر می‌خواهید همه‌چیز صفر شود، از دکمه «بازنشانی» در "
                                   "پنل مدیریت استفاده کنید.\n\n⚠️ برای برکناری فقط یک نفر، "
                                   "روی پیام او ریپلای کنید و /unsetlord بزنید.</blockquote>",
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
        'btn_country_assets': "🎛 دارایی هر کشور",
        'gas_pick': "🎛 دارایی‌های کدام کشور را می‌خواهید تغییر دهید؟ (صفحه {p} از {n})",
        'gas_marks': " ({off}🚫 {paused}⏸)",
        'gas_country': "🎛 <b>{g}</b>\n<blockquote>🚫 ندارد: {off}\n⏸ خاموش: {paused}</blockquote>\n"
                       "«ندارد» یعنی این مورد اصلاً برای این کشور وجود ندارد. «خاموش» یعنی "
                       "ساختمان سر جایش هست ولی تولید نمی‌کند.",
        'gas_kind_btn': "{kind} — {n} از {total}",
        'gas_kind': "🎛 {g} — {kind} (صفحه {p} از {n})\n"
                    "روی نام هر مورد بزنید تا برای این کشور حذف/اضافه شود.",
        'gas_none': "هیچ‌کدام",
        'gas_on': "✅",
        'gas_off': "🚫",
        'btn_gas_stop': "⏸ خاموش",
        'btn_gas_run': "▶️ روشن",
        'gas_removed': "🚫 «{label}» برای این کشور حذف شد.",
        'gas_restored': "✅ «{label}» برای این کشور اضافه شد.",
        'gas_stopped': "⏸ «{label}» خاموش شد؛ دیگر تولید نمی‌کند.",
        'gas_running': "▶️ «{label}» دوباره روشن شد.",
        'btn_gas_clear': "♻️ برگرداندن همه‌چیز به حالت عادی",
        'btn_gas_clear_yes': "✅ بله، همه را برگردان",
        'gas_clear_confirm': "♻️ همه تغییرهای <b>{g}</b> برداشته شود؟\n<blockquote>{off} مورد "
                             "حذف‌شده و {paused} ساختمان خاموش دوباره عادی می‌شوند. عددهای کشور "
                             "دست‌نخورده می‌مانند.</blockquote>",
        'gas_cleared': "♻️ {n} تغییر برداشته شد.",
        'act_country_asset': "دارایی یک کشور",
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
        'cat_extra_building': "🏭 تولید می‌کند: {produces}\n📈 تولید پایه هر سطح در هفته: {output}\n"
                              "💸 هزینه پایه ارتقا: {costs}\n🏁 سقف سطح: {max}\n"
                              "🎚 سطح‌های دستی‌شده: {tuned}",
        'cat_extra_resource': "🚢 قابل تجارت: {tradeable}",
        'cat_produces_none': "چیزی تولید نمی‌کند",
        'cat_costs_none': "رایگان",
        'cat_builtin_note': "\n\nℹ️ این نوع همراه بازی آمده است. مثل بقیه می‌توانید ویرایش، "
                            "غیرفعال یا حذفش کنید.",
        'cat_engine_note': "\n\n🔒 سیستم تجارت مستقیماً به این ستون وابسته است (کرایه، عوارض، "
                           "امانت و ظرفیت کشتی). می‌توانید غیرفعالش کنید، اما حذف کامل ممکن "
                           "نیست — محموله‌های در راه از بین می‌رفتند.",
        'cat_hidden_note': "\n\n🚫 این نوع از بازی حذف شده است. مقادیر ذخیره‌شده دست‌نخورده‌اند و "
                           "با بازگرداندن دوباره ظاهر می‌شوند.",
        'btn_cat_rename': "✏️ تغییر نام",
        'btn_cat_default': "🎁 مقدار اولیه",
        'btn_cat_output': "📈 تولید",
        'btn_cat_tradeable': "🚢 قابل تجارت",
        'btn_cat_costs': "💸 هزینه ارتقا",
        'btn_cat_levels': "🎚 هزینه و بازدهی سطح‌به‌سطح",
        'btn_cat_max': "🏁 سقف سطح",
        'btn_cat_level_add': "➕ تنظیم دستی یک سطح",
        'btn_cat_level': "سطح {level} — {cost} | 📈 {out}",
        'btn_cat_level_output': "📈 بازدهی این سطح",
        'btn_cat_level_clear': "♻️ برگرداندن این سطح به حالت پایه",
        'cat_levels_title': "🎚 <b>{label}</b> — تنظیم سطح‌به‌سطح\n"
                            "<blockquote>💸 هزینه پایه: {costs}\n📈 بازدهی پایه هر سطح: {output}\n"
                            "🏁 سقف سطح: {max}\n🎚 سطح‌های دستی‌شده: {tuned}</blockquote>\n"
                            "هر سطحی که اینجا نباشد از مقدار پایه استفاده می‌کند.",
        'cat_level_title': "🎚 <b>{label}</b> — سطح {level}\n"
                           "<blockquote>💸 هزینه این سطح: {cost}\n"
                           "📈 بازدهی این سطح: {out} ({source})\n"
                           "🧮 مجموع بازدهی در سطح {level}: {total}</blockquote>\n"
                           "برای تغییر هزینه روی هر منبع بزنید.",
        'cat_lvl_inherited': "طبق هزینه پایه",
        'cat_lvl_output_own': "دستی",
        'cat_lvl_output_flat': "پایه",
        'cat_levels_none': "هیچ‌کدام",
        'cat_max_none': "بدون سقف",
        'cat_ask_level': "کدام سطح را می‌خواهید دستی تنظیم کنید؟ (عددی بین ۱ تا {max})",
        'cat_ask_level_cost': "هزینه رسیدن به سطح {level} بر حسب {res} چقدر باشد؟ (صفر یعنی نیازی نیست)",
        'cat_ask_level_output': "سطح {level} در هر آپ هفتگی چقدر تولید کند؟",
        'cat_level_cleared': "♻️ سطح {level} به مقدار پایه برگشت.",
        'cat_ask_max': "بالاترین سطح این ساختمان چند باشد؟ (فعلی: {current} — صفر یعنی بدون سقف، حداکثر {ceiling})",
        'cat_max_set': "🏁 سقف سطح روی {max} تنظیم شد.",
        'cat_max_lifted': "🏁 سقف سطح برداشته شد.",
        'cat_err_bad_level': "شماره سطح معتبر نیست.",
        'cat_err_bad_output': "مقدار تولید نمی‌تواند منفی باشد.",
        'act_asset_level': "تنظیم سطح ساختمان",
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
        'cat_err_engine_key': "❌ سیستم تجارت مستقیماً به این ستون وابسته است و حذف کاملش "
                              "محموله‌های در راه را از بین می‌برد. به‌جایش «حذف از بازی» "
                              "را بزنید.",
        'cat_err_bad_produces': "❌ یک ساختمان فقط می‌تواند منبع یا واحد تولید کند.",
        'cat_err_not_a_building': "❌ این مورد ساختمان نیست.",
        'cat_err_not_a_resource': "❌ این مورد منبع نیست.",
        'cat_err_bad_resource': "❌ منبع نامعتبر است.",
        'cat_err_unknown': "❌ چنین نوعی وجود ندارد.",
        'act_asset_remove': "حذف کامل نوع دارایی",
        'act_asset_kind_order': "ترتیب بخش‌ها",
        'act_catalog_reset': "بازنشانی کامل فهرست دارایی‌ها",
        'act_log_clear': "پاک‌سازی گزارش اقدامات",
        'btn_cat_up': "⬆️ بالاتر",
        'btn_cat_down': "⬇️ پایین‌تر",
        'cat_rank': "📍 جایگاه در فهرست: {place} از {total}",
        'cat_at_top': "همین حالا اول فهرست است.",
        'cat_at_bottom': "همین حالا آخر فهرست است.",
        'cat_moved': "✅ جابه‌جا شد.",
        'btn_cat_order': "🔀 ترتیب بخش‌ها",
        'cat_order_title': "🔀 ترتیب بخش‌ها در پیام دارایی و کارت گروه:\n"
                           "<blockquote>{order}</blockquote>\n"
                           "با فلش‌ها جای هر بخش را عوض کنید.",
        'btn_cat_delete': "❌ حذف کامل و همیشگی",
        'btn_cat_delete_yes': "🔥 بله، برای همیشه حذف کن",
        'cat_delete_confirm': "🔥 <b>حذف کامل «{label}»</b>\n<blockquote>کلید <code>{key}</code> "
                              "به‌طور کامل از پایگاه داده پاک می‌شود و مقدار ذخیره‌شدهٔ همهٔ "
                              "کشورها برای آن از بین می‌رود.\n\n{holders}\n\n"
                              "⚠️ این کار برگشت‌پذیر نیست. اگر فقط می‌خواهید موقتاً از بازی "
                              "خارج شود، به‌جای این از «حذف از بازی» استفاده کنید.</blockquote>",
        'cat_delete_holders': "📊 {n} کشور مقدار غیرصفر برای این نوع دارند.",
        'cat_delete_holders_none': "📊 هیچ کشوری مقدار غیرصفری برای این نوع ندارد.",
        'cat_delete_builtin_warning': "\n\n⚠️ این نوع همراه بازی آمده است. بعد از حذف، تنها راه "
                                      "برگرداندنش «بازنشانی کامل فهرست دارایی‌ها» است، که آن هم "
                                      "همهٔ کشورها را از مقدار اولیه شروع می‌کند.",
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
        # {sections} is one "header + <blockquote>" block per kind, in the order
        # asset_catalog.kind_order() gives.
        'group_card': "🏳 <b>{title}</b>\n👤 Lord: {lord}\n\n"
                      "{sections}\n"
                      "🚢 Trades: active {active} | completed {done}\n"
                      "⚓️ Sea location: {home_sea} | 🏔 Land location: {home_land}",
        'sec_resource': "💰 Resources:",
        'sec_unit': "⚔️ Army:",
        'sec_building': "🏭 Buildings:",
        'unset': "not set",
        'nobody': "none",
        'bot_off': "⛔️ The bot is closed to players for now. Please talk to an admin.",
        'bot_turned_on': "✅ The bot is open to players again.",
        'bot_turned_off': "⛔️ The bot is closed to players. The admin panel still works.",
        'bot_on_already': "The bot was already open.",
        'bot_off_already': "The bot was already closed.",
        'btn_players_on': "🟢 Open to players — tap to close",
        'btn_players_off': "⛔️ Closed to players — tap to open",
        'panel_closed': "\n\n⛔️ The bot is closed to players (/on to reopen).",
        'act_bot_switch': "bot opened/closed",
        'act_statement': "statement",
        'act_campaign': "campaign",
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
        'act_trade_mode': "country trade opened/closed",
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
        'btn_reset_all': "♻️ Restore every country ({n})",
        'btn_confirm_reset_all': "✅ Yes, restore them all",
        'reset_all_confirm': "♻️ <b>Restore every country</b>\n<blockquote>The resources, units "
                             "and buildings of all {n} countries go back to their starting "
                             "values:\n{names}\n\nThis only zeroes the countries' numbers; the "
                             "asset catalog and the game settings are untouched.</blockquote>",
        'reset_all_done': "♻️ All {n} countries are back to their initial state.",
        'setlord_restored': "\n♻️ The country's previous assets were handed over to them.",
        'act_reset_all': "every country restored",
        'act_country_restore': "country handed to a new lord",
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
        'unsetlord_done': "🚫 {u} is no longer a lord. The country keeps what it owns; the next lord inherits it.",
        'btn_unset_group': "🔥 Yes, retire this group",
        'unsetlord_group_confirm': "🔥 <b>Retire “{title}”</b>\n<blockquote>Its {n} lord(s) are "
                                   "removed, but the country keeps every resource, unit and "
                                   "building — the next lord of this group inherits them.\n\n"
                                   "♻️ To zero everything instead, use the Reset button in the "
                                   "admin panel.\n\n⚠️ To remove just one person, reply to "
                                   "their message with /unsetlord instead.</blockquote>",
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
        'btn_country_assets': "🎛 A country's assets",
        'gas_pick': "🎛 Which country's assets do you want to change? (page {p} of {n})",
        'gas_marks': " ({off}🚫 {paused}⏸)",
        'gas_country': "🎛 <b>{g}</b>\n<blockquote>🚫 Does not have: {off}\n⏸ Switched off: "
                       "{paused}</blockquote>\n"
                       "\"Does not have\" means the type does not exist for this country at "
                       "all. \"Switched off\" means the building is still there but produces "
                       "nothing.",
        'gas_kind_btn': "{kind} — {n} of {total}",
        'gas_kind': "🎛 {g} — {kind} (page {p} of {n})\n"
                    "Tap a name to take it away from this country or give it back.",
        'gas_none': "none",
        'gas_on': "✅",
        'gas_off': "🚫",
        'btn_gas_stop': "⏸ Stop",
        'btn_gas_run': "▶️ Start",
        'gas_removed': "🚫 “{label}” was taken away from this country.",
        'gas_restored': "✅ “{label}” was given back to this country.",
        'gas_stopped': "⏸ “{label}” is switched off; it produces nothing now.",
        'gas_running': "▶️ “{label}” is running again.",
        'btn_gas_clear': "♻️ Put everything back to normal",
        'btn_gas_clear_yes': "✅ Yes, put it all back",
        'gas_clear_confirm': "♻️ Clear every override on <b>{g}</b>?\n<blockquote>{off} removed "
                             "type(s) and {paused} switched-off building(s) go back to normal. "
                             "The country's numbers are untouched.</blockquote>",
        'gas_cleared': "♻️ {n} override(s) cleared.",
        'act_country_asset': "a country's assets",
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
        'cat_extra_building': "🏭 Produces: {produces}\n📈 Base per level per week: {output}\n"
                              "💸 Base upgrade cost: {costs}\n🏁 Level ceiling: {max}\n"
                              "🎚 Hand-tuned levels: {tuned}",
        'cat_extra_resource': "🚢 Tradeable: {tradeable}",
        'cat_produces_none': "nothing",
        'cat_costs_none': "free",
        'cat_builtin_note': "\n\nℹ️ This type shipped with the game. You can edit, disable or "
                            "delete it like any other.",
        'cat_engine_note': "\n\n🔒 The trade system addresses this column directly — fees, tolls, "
                           "escrow and ship capacity. You can take it out of the game, but it "
                           "cannot be deleted for good: shipments in flight would be lost.",
        'cat_hidden_note': "\n\n🚫 This type has been removed from the game. Its stored values are "
                           "untouched and come back if you restore it.",
        'btn_cat_rename': "✏️ Rename",
        'btn_cat_default': "🎁 Starting amount",
        'btn_cat_output': "📈 Production",
        'btn_cat_tradeable': "🚢 Tradeable",
        'btn_cat_costs': "💸 Upgrade cost",
        'btn_cat_levels': "🎚 Per-level cost & yield",
        'btn_cat_max': "🏁 Level ceiling",
        'btn_cat_level_add': "➕ Tune one level",
        'btn_cat_level': "Level {level} — {cost} | 📈 {out}",
        'btn_cat_level_output': "📈 This level's yield",
        'btn_cat_level_clear': "♻️ Back to the base values",
        'cat_levels_title': "🎚 <b>{label}</b> — per-level tuning\n"
                            "<blockquote>💸 Base cost: {costs}\n📈 Base yield per level: {output}\n"
                            "🏁 Level ceiling: {max}\n🎚 Hand-tuned levels: {tuned}</blockquote>\n"
                            "Any level not listed here uses the base values.",
        'cat_level_title': "🎚 <b>{label}</b> — level {level}\n"
                           "<blockquote>💸 This level costs: {cost}\n"
                           "📈 This level yields: {out} ({source})\n"
                           "🧮 Total yield at level {level}: {total}</blockquote>\n"
                           "Tap a resource to change what this level costs.",
        'cat_lvl_inherited': "same as the base cost",
        'cat_lvl_output_own': "hand-set",
        'cat_lvl_output_flat': "base",
        'cat_levels_none': "none",
        'cat_max_none': "no ceiling",
        'cat_ask_level': "Which level do you want to tune? (a number from 1 to {max})",
        'cat_ask_level_cost': "How much {res} should reaching level {level} cost? (zero means none)",
        'cat_ask_level_output': "How much should level {level} produce each weekly cycle?",
        'cat_level_cleared': "♻️ Level {level} is back to the base values.",
        'cat_ask_max': "What is the highest level for this building? (now: {current} — zero means no ceiling, at most {ceiling})",
        'cat_max_set': "🏁 Level ceiling set to {max}.",
        'cat_max_lifted': "🏁 Level ceiling lifted.",
        'cat_err_bad_level': "That is not a valid level number.",
        'cat_err_bad_output': "Output cannot be negative.",
        'act_asset_level': "building level tuning",
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
        'cat_err_engine_key': "❌ The trade system depends on this column directly, and deleting "
                              "it would destroy shipments in flight. Use “Remove from the game” "
                              "instead.",
        'cat_err_bad_produces': "❌ A building can only produce a resource or a unit.",
        'cat_err_not_a_building': "❌ That entry is not a building.",
        'cat_err_not_a_resource': "❌ That entry is not a resource.",
        'cat_err_bad_resource': "❌ Invalid resource.",
        'cat_err_unknown': "❌ No such type.",
        'act_asset_remove': "asset type destroyed",
        'act_asset_kind_order': "section order",
        'act_catalog_reset': "asset catalog factory reset",
        'act_log_clear': "action log cleared",
        'btn_cat_up': "⬆️ Move up",
        'btn_cat_down': "⬇️ Move down",
        'cat_rank': "📍 Place in the list: {place} of {total}",
        'cat_at_top': "Already first in the list.",
        'cat_at_bottom': "Already last in the list.",
        'cat_moved': "✅ Moved.",
        'btn_cat_order': "🔀 Section order",
        'cat_order_title': "🔀 Section order in the assets message and the group card:\n"
                           "<blockquote>{order}</blockquote>\n"
                           "Use the arrows to move a section.",
        'btn_cat_delete': "❌ Delete permanently",
        'btn_cat_delete_yes': "🔥 Yes, delete it for good",
        'cat_delete_confirm': "🔥 <b>Permanently delete “{label}”</b>\n<blockquote>The key "
                              "<code>{key}</code> will be erased from the database, and every "
                              "country's stored value for it goes with it.\n\n{holders}\n\n"
                              "⚠️ This cannot be undone. To take it out of the game "
                              "temporarily, use “Remove from the game” instead.</blockquote>",
        'cat_delete_holders': "📊 {n} countries hold a non-zero value for this type.",
        'cat_delete_holders_none': "📊 No country holds a non-zero value for this type.",
        'cat_delete_builtin_warning': "\n\n⚠️ This type shipped with the game. Once it is gone, "
                                      "the only way back is a full factory reset of the catalog, "
                                      "and that restarts every country from the default amount.",
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
        # {sections} is one "header + <blockquote>" block per kind, in the order
        # asset_catalog.kind_order() gives.
        'group_card': "🏳 <b>{title}</b>\n👤 Lord: {lord}\n\n"
                      "{sections}\n"
                      "🚢 Ticaret: etkin {active} | tamamlanan {done}\n"
                      "⚓️ Deniz konumu: {home_sea} | 🏔 Kara konumu: {home_land}",
        'sec_resource': "💰 Kaynaklar:",
        'sec_unit': "⚔️ Ordu:",
        'sec_building': "🏭 Binalar:",
        'unset': "ayarlanmadı",
        'nobody': "yok",
        'bot_off': "⛔️ Bot şimdilik oyunculara kapalı. Lütfen bir yöneticiyle konuşun.",
        'bot_turned_on': "✅ Bot yeniden oyunculara açık.",
        'bot_turned_off': "⛔️ Bot oyunculara kapatıldı. Yönetim paneli çalışmaya devam ediyor.",
        'bot_on_already': "Bot zaten açıktı.",
        'bot_off_already': "Bot zaten kapalıydı.",
        'btn_players_on': "🟢 Oyunculara açık — kapatmak için dokunun",
        'btn_players_off': "⛔️ Oyunculara kapalı — açmak için dokunun",
        'panel_closed': "\n\n⛔️ Bot oyunculara kapalı (açmak için /on).",
        'act_bot_switch': "bot açıldı/kapatıldı",
        'act_statement': "bildiri",
        'act_campaign': "sefer",
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
        'act_trade_mode': "ülke ticareti açıldı/kapatıldı",
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
        'btn_reset_all': "♻️ Tüm ülkeleri geri yükle ({n})",
        'btn_confirm_reset_all': "✅ Evet, hepsini geri yükle",
        'reset_all_confirm': "♻️ <b>Tüm ülkeleri geri yükle</b>\n<blockquote>{n} ülkenin "
                             "kaynakları, birlikleri ve binaları başlangıç değerlerine "
                             "döner:\n{names}\n\nBu yalnızca ülkelerin sayılarını sıfırlar; "
                             "varlık kataloğuna ve oyun ayarlarına dokunmaz.</blockquote>",
        'reset_all_done': "♻️ {n} ülkenin hepsi başlangıç durumuna döndü.",
        'setlord_restored': "\n♻️ Ülkenin önceki varlıkları kendisine devredildi.",
        'act_reset_all': "tüm ülkeler geri yüklendi",
        'act_country_restore': "ülke yeni lorda devredildi",
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
        'unsetlord_done': "🚫 {u} artık lord değil. Ülke sahip olduklarını korur; sonraki lord devralır.",
        'btn_unset_group': "🔥 Evet, bu grubu emekliye ayır",
        'unsetlord_group_confirm': "🔥 <b>“{title}” emekliye ayrılsın mı?</b>\n<blockquote>{n} "
                                   "lordu kaldırılır, ancak ülke tüm kaynaklarını, birliklerini "
                                   "ve binalarını korur — bu grubun sonraki lordu devralır.\n\n"
                                   "♻️ Her şeyi sıfırlamak için yönetim panelindeki Sıfırla "
                                   "düğmesini kullanın.\n\n⚠️ Yalnızca bir kişiyi kaldırmak "
                                   "için onun mesajını yanıtlayıp /unsetlord gönderin.</blockquote>",
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
        'btn_country_assets': "🎛 Ülke varlıkları",
        'gas_pick': "🎛 Hangi ülkenin varlıklarını değiştirmek istiyorsunuz? (sayfa {p}/{n})",
        'gas_marks': " ({off}🚫 {paused}⏸)",
        'gas_country': "🎛 <b>{g}</b>\n<blockquote>🚫 Sahip değil: {off}\n⏸ Kapalı: "
                       "{paused}</blockquote>\n"
                       "\"Sahip değil\" bu tür bu ülke için hiç yok demektir. \"Kapalı\" bina "
                       "duruyor ama üretmiyor demektir.",
        'gas_kind_btn': "{kind} — {total} içinden {n}",
        'gas_kind': "🎛 {g} — {kind} (sayfa {p}/{n})\n"
                    "Bu ülkeden almak veya geri vermek için bir ada dokunun.",
        'gas_none': "yok",
        'gas_on': "✅",
        'gas_off': "🚫",
        'btn_gas_stop': "⏸ Durdur",
        'btn_gas_run': "▶️ Başlat",
        'gas_removed': "🚫 “{label}” bu ülkeden alındı.",
        'gas_restored': "✅ “{label}” bu ülkeye geri verildi.",
        'gas_stopped': "⏸ “{label}” kapatıldı; artık üretmiyor.",
        'gas_running': "▶️ “{label}” yeniden çalışıyor.",
        'btn_gas_clear': "♻️ Her şeyi normale döndür",
        'btn_gas_clear_yes': "✅ Evet, hepsini geri al",
        'gas_clear_confirm': "♻️ <b>{g}</b> üzerindeki tüm değişiklikler kaldırılsın mı?"
                             "\n<blockquote>{off} kaldırılan tür ve {paused} kapalı bina "
                             "normale döner. Ülkenin sayıları değişmez.</blockquote>",
        'gas_cleared': "♻️ {n} değişiklik kaldırıldı.",
        'act_country_asset': "bir ülkenin varlıkları",
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
        'cat_extra_building': "🏭 Ürettiği: {produces}\n📈 Seviye başına temel haftalık: {output}\n"
                              "💸 Temel yükseltme maliyeti: {costs}\n🏁 Seviye tavanı: {max}\n"
                              "🎚 Elle ayarlanan seviyeler: {tuned}",
        'cat_extra_resource': "🚢 Ticarete açık: {tradeable}",
        'cat_produces_none': "hiçbir şey",
        'cat_costs_none': "ücretsiz",
        'cat_builtin_note': "\n\nℹ️ Bu tür oyunla birlikte gelir. Diğerleri gibi düzenleyebilir, "
                            "devre dışı bırakabilir veya silebilirsiniz.",
        'cat_engine_note': "\n\n🔒 Ticaret sistemi bu sütunu doğrudan kullanır — ücretler, geçiş "
                           "ücretleri, emanet ve gemi kapasitesi. Oyundan kaldırabilirsiniz ama "
                           "kalıcı olarak silinemez: yoldaki sevkiyatlar kaybolurdu.",
        'cat_hidden_note': "\n\n🚫 Bu tür oyundan kaldırıldı. Kayıtlı değerleri korunuyor ve "
                           "geri getirildiğinde yeniden görünecek.",
        'btn_cat_rename': "✏️ Yeniden adlandır",
        'btn_cat_default': "🎁 Başlangıç miktarı",
        'btn_cat_output': "📈 Üretim",
        'btn_cat_tradeable': "🚢 Ticarete açık",
        'btn_cat_costs': "💸 Yükseltme maliyeti",
        'btn_cat_levels': "🎚 Seviye başına maliyet ve verim",
        'btn_cat_max': "🏁 Seviye tavanı",
        'btn_cat_level_add': "➕ Bir seviyeyi elle ayarla",
        'btn_cat_level': "Seviye {level} — {cost} | 📈 {out}",
        'btn_cat_level_output': "📈 Bu seviyenin verimi",
        'btn_cat_level_clear': "♻️ Temel değerlere döndür",
        'cat_levels_title': "🎚 <b>{label}</b> — seviye başına ayar\n"
                            "<blockquote>💸 Temel maliyet: {costs}\n📈 Seviye başına temel verim: {output}\n"
                            "🏁 Seviye tavanı: {max}\n🎚 Elle ayarlanan seviyeler: {tuned}</blockquote>\n"
                            "Burada olmayan her seviye temel değerleri kullanır.",
        'cat_level_title': "🎚 <b>{label}</b> — seviye {level}\n"
                           "<blockquote>💸 Bu seviyenin maliyeti: {cost}\n"
                           "📈 Bu seviyenin verimi: {out} ({source})\n"
                           "🧮 Seviye {level} toplam verim: {total}</blockquote>\n"
                           "Maliyeti değiştirmek için bir kaynağa dokunun.",
        'cat_lvl_inherited': "temel maliyetle aynı",
        'cat_lvl_output_own': "elle",
        'cat_lvl_output_flat': "temel",
        'cat_levels_none': "yok",
        'cat_max_none': "tavan yok",
        'cat_ask_level': "Hangi seviyeyi elle ayarlamak istiyorsunuz? (1 ile {max} arası bir sayı)",
        'cat_ask_level_cost': "Seviye {level} için ne kadar {res} gereksin? (sıfır: gerekmez)",
        'cat_ask_level_output': "Seviye {level} her haftalık döngüde ne kadar üretsin?",
        'cat_level_cleared': "♻️ Seviye {level} temel değerlere döndü.",
        'cat_ask_max': "Bu bina en fazla kaçıncı seviyeye çıksın? (şu an: {current} — sıfır: tavan yok, en çok {ceiling})",
        'cat_max_set': "🏁 Seviye tavanı {max} olarak ayarlandı.",
        'cat_max_lifted': "🏁 Seviye tavanı kaldırıldı.",
        'cat_err_bad_level': "Geçerli bir seviye numarası değil.",
        'cat_err_bad_output': "Üretim negatif olamaz.",
        'act_asset_level': "bina seviye ayarı",
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
        'cat_err_engine_key': "❌ Ticaret sistemi bu sütuna doğrudan bağlı ve silmek yoldaki "
                              "sevkiyatları yok ederdi. Bunun yerine “Oyundan kaldır” "
                              "seçeneğini kullanın.",
        'cat_err_bad_produces': "❌ Bir bina yalnızca kaynak veya birim üretebilir.",
        'cat_err_not_a_building': "❌ Bu girdi bir bina değil.",
        'cat_err_not_a_resource': "❌ Bu girdi bir kaynak değil.",
        'cat_err_bad_resource': "❌ Geçersiz kaynak.",
        'cat_err_unknown': "❌ Böyle bir tür yok.",
        'act_asset_remove': "varlık türü kalıcı olarak silindi",
        'act_asset_kind_order': "bölüm sırası",
        'act_catalog_reset': "varlık kataloğu fabrika ayarlarına döndürüldü",
        'act_log_clear': "işlem kaydı temizlendi",
        'btn_cat_up': "⬆️ Yukarı taşı",
        'btn_cat_down': "⬇️ Aşağı taşı",
        'cat_rank': "📍 Listedeki yeri: {total} içinde {place}",
        'cat_at_top': "Zaten listenin başında.",
        'cat_at_bottom': "Zaten listenin sonunda.",
        'cat_moved': "✅ Taşındı.",
        'btn_cat_order': "🔀 Bölüm sırası",
        'cat_order_title': "🔀 Varlık mesajındaki ve grup kartındaki bölüm sırası:\n"
                           "<blockquote>{order}</blockquote>\n"
                           "Bir bölümü taşımak için okları kullanın.",
        'btn_cat_delete': "❌ Kalıcı olarak sil",
        'btn_cat_delete_yes': "🔥 Evet, tamamen sil",
        'cat_delete_confirm': "🔥 <b>“{label}” kalıcı olarak silinsin mi?</b>\n<blockquote>"
                              "<code>{key}</code> anahtarı veritabanından tamamen silinecek ve "
                              "her ülkenin bu tür için kayıtlı değeri de gidecek.\n\n{holders}"
                              "\n\n⚠️ Bu geri alınamaz. Yalnızca geçici olarak oyundan çıkarmak "
                              "için “Oyundan kaldır” seçeneğini kullanın.</blockquote>",
        'cat_delete_holders': "📊 {n} ülkenin bu tür için sıfırdan farklı değeri var.",
        'cat_delete_holders_none': "📊 Hiçbir ülkenin bu tür için sıfırdan farklı değeri yok.",
        'cat_delete_builtin_warning': "\n\n⚠️ Bu tür oyunla birlikte geldi. Silindikten sonra geri "
                                      "getirmenin tek yolu kataloğu fabrika ayarlarına döndürmek, "
                                      "o da her ülkeyi başlangıç miktarından başlatır.",
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
