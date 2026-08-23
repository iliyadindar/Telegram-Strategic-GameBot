# -*- coding: utf-8 -*-
"""World trade system (sea + land) shared by main.py / main-en.py / main-tr.py.

All trade logic lives here once: route finding, fees and tolls, the trade
wizard (inline buttons), the offer lifecycle and the background ticker that
moves convoys in real time and live-edits the tracking message. Player-facing
strings are provided in fa/en/tr; each main*.py calls
init(bot, conn, ADMIN_ID, CHANNEL_ID, lang=...) once and forwards callback
queries whose data starts with 'trd:' to handle_callback().

The world map itself is data, owned by trade_map. This module asks it for
nodes, names and adjacency and never keeps its own copy beyond the caches that
trade_map invalidates on every edit.
"""

import heapq
import html
import json
import sqlite3
import threading
import time
import traceback

from telebot import types

import asset_catalog
import trade_map
import trade_map_admin

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------
_bot = None
_conn = None
_ADMIN = 0
_CHANNEL = None
_lang = 'fa'
_is_admin = None     # set by init(); predicate deciding who reaches trd:adm
_is_owner = None     # set by init(); predicate deciding who may delete map pieces
_audit = None        # set by init(); optional (actor_id, action, target, detail) sink
# RLock: refund/credit helpers are called from code that already holds the lock.
_lock = threading.RLock()
_ctx = {}            # per-user wizard state (in-memory; nothing escrowed before confirm)
_title_cache = {}
_ticker_started = False

TRADE_PREFIX = 'trd:'

# Callbacks that belong to the admin screens. They stay reachable when the
# player-facing trade feature is switched off, so main*.py checks against this
# list rather than keeping a copy of its own that silently falls behind.
ADMIN_OPS = frozenset({
    'adm', 'hm', 'hg', 'h', 'cfgh', 'cfg', 'ck', 'ow', 'on', 'og',
    'ph', 'phm', 'phs', 'phc', 'tm', 'tmg', 'tmt',
}) | frozenset(trade_map_admin.OPS)

# ---------------------------------------------------------------------------
# Config (all admin-editable, persisted in trade_config)
# ---------------------------------------------------------------------------
CONFIG_DEFAULTS = {
    'sea_min_per_unit': 30,
    'land_min_per_unit': 45,
    'fee_per_unit': 20,
    'cap_small': 500, 'cap_medium': 1500, 'cap_large': 4000,
    'cap_caravan': 250, 'caravan_cost': 50,
    'offer_expiry_min': 120,
    'toll_sue': 500, 'toll_pan': 500, 'toll_kie': 150, 'toll_dan': 50,
    'toll_gib': 100, 'toll_bos': 100, 'toll_dar': 100, 'toll_hor': 100,
    'toll_bab': 100, 'toll_mal': 200, 'toll_sun': 100, 'toll_lom': 100,
    'toll_tsu': 100, 'toll_ber': 100, 'toll_mag': 150, 'toll_moz': 50,
    'toll_sin': 50, 'toll_sah': 100, 'toll_cau': 100, 'toll_zag': 100,
    'toll_pam': 150, 'toll_khy': 100,
}

# The settings screen used to be four pages of `sea_min_per_unit = 30`, which
# tells an admin the name of a variable and nothing about what it changes. Each
# setting now carries a name and a sentence, and they are filed under three
# sections instead of paged through alphabetically.
#
# Anything not named here — a toll for a chokepoint an admin drew themselves —
# is labelled from the map, so a new strait is legible the moment it exists.

# section key -> the settings in it, in the order they are shown. 'toll' is
# filled in at render time from whatever chokepoints the map currently has.
CONFIG_SECTIONS = (
    ('journey', ('sea_min_per_unit', 'land_min_per_unit', 'fee_per_unit', 'offer_expiry_min')),
    ('capacity', ('cap_small', 'cap_medium', 'cap_large', 'cap_caravan', 'caravan_cost')),
    ('toll', ()),
)

CONFIG_LABELS = {
    'fa': {
        'sea_min_per_unit': "⏱ زمان سفر دریایی",
        'land_min_per_unit': "⏱ زمان سفر زمینی",
        'fee_per_unit': "💵 کرایه مسیر",
        'offer_expiry_min': "⌛️ مهلت پاسخ به پیشنهاد",
        'cap_small': "⛵ ظرفیت بار کشتی کوچک",
        'cap_medium': "🚢 ظرفیت بار کشتی متوسط",
        'cap_large': "🛳 ظرفیت بار کشتی بزرگ",
        'cap_caravan': "🐫 ظرفیت بار هر کاروان",
        'caravan_cost': "💰 هزینه هر کاروان در هر سفر",
    },
    'en': {
        'sea_min_per_unit': "⏱ Sea travel time",
        'land_min_per_unit': "⏱ Land travel time",
        'fee_per_unit': "💵 Route fee",
        'offer_expiry_min': "⌛️ Offer expiry",
        'cap_small': "⛵ Small ship cargo capacity",
        'cap_medium': "🚢 Medium ship cargo capacity",
        'cap_large': "🛳 Large ship cargo capacity",
        'cap_caravan': "🐫 Cargo capacity per caravan",
        'caravan_cost': "💰 Cost per caravan per trip",
    },
    'tr': {
        'sea_min_per_unit': "⏱ Deniz yolculuk süresi",
        'land_min_per_unit': "⏱ Kara yolculuk süresi",
        'fee_per_unit': "💵 Rota ücreti",
        'offer_expiry_min': "⌛️ Teklif süresi",
        'cap_small': "⛵ Küçük gemi yük kapasitesi",
        'cap_medium': "🚢 Orta gemi yük kapasitesi",
        'cap_large': "🛳 Büyük gemi yük kapasitesi",
        'cap_caravan': "🐫 Kervan başına yük kapasitesi",
        'caravan_cost': "💰 Sefer başına kervan maliyeti",
    },
}

CONFIG_HELP = {
    'fa': {
        'sea_min_per_unit': "چند دقیقه طول بکشد تا یک ناوگان دریایی یک واحد فاصله را طی کند. "
                            "عدد بزرگ‌تر یعنی سفرهای کندتر.",
        'land_min_per_unit': "چند دقیقه طول بکشد تا یک کاروان یک واحد فاصله را طی کند. "
                             "عدد بزرگ‌تر یعنی سفرهای کندتر.",
        'fee_per_unit': "به ازای هر واحد از طول مسیر، چقدر پول از فرستنده گرفته شود. "
                        "این جدا از عوارض گذرگاه‌هاست.",
        'offer_expiry_min': "اگر گیرنده تا این تعداد دقیقه جواب ندهد، پیشنهاد باطل می‌شود و "
                            "همه‌چیز به فرستنده برمی‌گردد.",
        'cap_small': "هر کشتی کوچک چند واحد کالا می‌برد.",
        'cap_medium': "هر کشتی متوسط چند واحد کالا می‌برد.",
        'cap_large': "هر کشتی بزرگ چند واحد کالا می‌برد.",
        'cap_caravan': "هر کاروان چند واحد کالا می‌برد. تعداد کاروان هر کشور در دارایی‌هایش است.",
        'caravan_cost': "بابت هر کاروانی که در یک سفر راه می‌افتد، چقدر پول گرفته شود. "
                        "خود کاروان بعد از رسیدن برمی‌گردد.",
    },
    'en': {
        'sea_min_per_unit': "Minutes a sea convoy takes to cross one unit of distance. "
                            "Larger means slower journeys.",
        'land_min_per_unit': "Minutes a caravan takes to cross one unit of distance. "
                             "Larger means slower journeys.",
        'fee_per_unit': "Money charged to the sender per unit of route length. "
                        "This is separate from chokepoint tolls.",
        'offer_expiry_min': "If the receiver has not answered within this many minutes the "
                            "offer lapses and everything goes back to the sender.",
        'cap_small': "How many units of cargo one small ship carries.",
        'cap_medium': "How many units of cargo one medium ship carries.",
        'cap_large': "How many units of cargo one large ship carries.",
        'cap_caravan': "How many units of cargo one caravan carries. How many caravans a "
                       "country owns is one of its assets.",
        'caravan_cost': "Money charged for each caravan sent on a trip. The caravan itself "
                        "comes home when the convoy arrives.",
    },
    'tr': {
        'sea_min_per_unit': "Bir deniz konvoyunun bir birim mesafeyi geçme süresi (dakika). "
                            "Büyük değer daha yavaş yolculuk demektir.",
        'land_min_per_unit': "Bir kervanın bir birim mesafeyi geçme süresi (dakika). "
                             "Büyük değer daha yavaş yolculuk demektir.",
        'fee_per_unit': "Rota uzunluğunun her birimi için göndericiden alınan para. "
                        "Geçit ücretlerinden ayrıdır.",
        'offer_expiry_min': "Alıcı bu kadar dakika içinde yanıt vermezse teklif düşer ve her "
                            "şey göndericiye döner.",
        'cap_small': "Bir küçük geminin taşıdığı yük birimi.",
        'cap_medium': "Bir orta geminin taşıdığı yük birimi.",
        'cap_large': "Bir büyük geminin taşıdığı yük birimi.",
        'cap_caravan': "Bir kervanın taşıdığı yük birimi. Bir ülkenin kaç kervanı olduğu "
                       "varlıklarından biridir.",
        'caravan_cost': "Sefere çıkan her kervan için alınan para. Kervanın kendisi konvoy "
                        "vardığında geri döner.",
    },
}


def toll_keys():
    """One setting per chokepoint the map currently has, in map order.

    Read from the map rather than from CONFIG_DEFAULTS so a strait an admin
    draws gets a priceable row, and a strait they delete stops showing one.
    """
    return tuple('toll_' + nid for nid in trade_map.chokepoints())


def config_keys(section):
    """The settings filed under one section."""
    if section == 'toll':
        return toll_keys()
    for key, keys in CONFIG_SECTIONS:
        if key == section:
            return keys
    return ()


def config_label(key):
    """A setting's name. A toll is named after the chokepoint it is charged at."""
    named = CONFIG_LABELS[_lang].get(key)
    if named:
        return named
    if key.startswith('toll_'):
        nid = key[len('toll_'):]
        mode = trade_map.mode_of(nid)
        if mode:
            return _t('cfg_toll_label', node=trade_map.name(nid, _lang))
    return key


def config_help(key):
    helped = CONFIG_HELP[_lang].get(key)
    if helped:
        return helped
    if key.startswith('toll_'):
        return _t('cfg_toll_help')
    return ''


# Tradeable resources come from the asset catalog, so a resource an admin adds
# in-game can be shipped without a code change. The catalog key doubles as the
# callback code; it is validated as an identifier before it is ever stored.
def resource_codes():
    return asset_catalog.tradeable_resources()


def _res_column(code):
    """Map a callback code back to a column, or None if it is not tradeable."""
    return code if code in resource_codes() else None


def _res_name(col):
    return asset_catalog.label(col, _lang)

# sea vehicles: short code, users column, capacity config key
SHIPS = (
    ('s', 'small_ships', 'cap_small'),
    ('m', 'medium_ships', 'cap_medium'),
    ('l', 'large_ships', 'cap_large'),
)
SHIP_BY_CODE = {c: col for c, col, _ in SHIPS}

# The land fleet, in the same shape. A caravan is an owned unit like a ship: a
# country has a stock of them, a convoy takes some out and brings them back.
CARAVANS = (('c', 'caravans', 'cap_caravan'),)

# Which vehicles a mode may use, so capacity, escrow and the picker all read
# from one table instead of three separate 'if mode == sea' branches.
VEHICLES = {'sea': SHIPS, 'land': CARAVANS}
VEH_BY_CODE = {code: col for table in VEHICLES.values() for code, col, _ in table}
CAP_KEY = {col: cap for table in VEHICLES.values() for _, col, cap in table}

# Fallback names only. Every vehicle is a catalog type now, so _veh_name()
# prefers the catalog's label and an admin's rename shows up here too.
VEH_NAMES = {
    'fa': {'small_ships': '⛵ کشتی کوچک', 'medium_ships': '🚢 کشتی متوسط',
           'large_ships': '🛳 کشتی بزرگ', 'caravans': '🐫 کاروان'},
    'en': {'small_ships': '⛵ Small Ship', 'medium_ships': '🚢 Medium Ship',
           'large_ships': '🛳 Large Ship', 'caravans': '🐫 Caravan'},
    'tr': {'small_ships': '⛵ Küçük Gemi', 'medium_ships': '🚢 Orta Gemi',
           'large_ships': '🛳 Büyük Gemi', 'caravans': '🐫 Kervan'},
}


def _veh_name(col):
    label = asset_catalog.label(col, _lang)
    return label if label != col else VEH_NAMES[_lang].get(col, col)


def _veh_capacity(col):
    """How much cargo one of these carries, straight from the trade config."""
    key = CAP_KEY.get(col)
    return cfg(key) if key else 0

# ---------------------------------------------------------------------------
# Strings (fa is the primary language; key sets asserted identical in init())
# ---------------------------------------------------------------------------
STRINGS = {
    'fa': {
        'err_generic': "خطایی رخ داد. دوباره تلاش کنید.",
        'session_expired': "جلسه تجارت یافت نشد. از دکمه «🚢 تجارت جهانی» دوباره شروع کنید.",
        'not_registered': "این گروه هنوز لردی ندارد. ابتدا با /setlord ثبت‌نام کنید.",
        'not_lord': "فقط لرد این گروه می‌تواند این کار را انجام دهد.",
        'admin_only': "شما ادمین نیستید.",
        'already_handled': "این پیشنهاد دیگر معتبر نیست.",
        'menu_title': "🌍 تجارت جهانی\n\nنوع تجارت را انتخاب کنید قربان:",
        'menu_active': "\n\n🧭 تجارت‌های در جریان شما: {n}",
        'btn_sea': "🚢 تجارت دریایی",
        'btn_land': "🐫 تجارت زمینی",
        'mode_sea': "دریایی",
        'mode_land': "زمینی",
        'need_home': "🏠 موقعیت {mode} گروه شما هنوز توسط ادمین تعیین نشده است.",
        'no_dest': "مقصدی برای تجارت {mode} در دسترس نیست؛ گروه‌های دیگر باید موقعیت داشته باشند.",
        'choose_dest': "🎯 مقصد تجارت را انتخاب کنید:",
        'btn_cancel': "❌ لغو",
        'goods_title': "📦 کالاهای تجارت را انتخاب کنید (روی هر کالا بزنید و مقدار بدهید):\n<blockquote>{lines}</blockquote>📊 حجم کل بار: {vol}",
        'goods_none': "هنوز کالایی انتخاب نشده",
        'btn_goods_done': "✅ ادامه",
        'ask_amount': "مقدار {res} را وارد کنید (موجودی: {bal}):",
        'bad_number': "مقدار وارد شده معتبر نیست. لطفا یک عدد وارد کنید.",
        'too_much': "بیشتر از موجودی شماست (موجودی: {bal}).",
        'need_goods': "حداقل یک کالا انتخاب کنید.",
        'veh_title_sea': "⚓️ ناوگان تجاری را انتخاب کنید:\n<blockquote>{fleet}</blockquote>\n🧾 انتخاب شما:\n<blockquote>{lines}</blockquote>📦 حجم بار: {vol}\n🚢 ظرفیت ناوگان: {cap}",
        'veh_title_land': "🐫 کاروان تجاری را آماده کنید:\n<blockquote>{fleet}</blockquote>\n🧾 انتخاب شما:\n<blockquote>{lines}</blockquote>📦 حجم بار: {vol}\n🐫 ظرفیت کاروان‌ها: {cap}\n💵 هزینه هر کاروان در این سفر: {p} پول",
        'ask_vcount': "تعداد {v} را وارد کنید (در اختیار: {bal} | ظرفیت هرکدام: {cap}):",
        'veh_row': "{name}: ظرفیت هرکدام {cap} — در اختیار شما {own}",
        'ask_caravans': "تعداد کاروان را وارد کنید (در اختیار: {bal} | ظرفیت هرکدام: {cap} | هزینه هر کاروان {p} پول):",
        'not_enough_units': "بیشتر از تعداد موجود است (موجودی: {bal}).",
        'not_enough_cap': "ظرفیت کافی نیست! حجم بار {vol} است اما ظرفیت فقط {cap}.",
        'btn_veh_done': "🗺 محاسبه مسیرها",
        'routes_title': "🗺 مسیرهای پیشنهادی از {src} به {dst}:",
        'route_fast': "⚡️ سریع‌ترین مسیر",
        'route_free': "🆓 مسیر بدون عوارض",
        'route_cheap': "💰 ارزان‌ترین مسیر",
        'route_block': "{label}\n<blockquote>⏱ مدت سفر: {dur}\n🧭 مسیر: {path}\n💵 کارمزد: {fee}\n🪙 عوارض: {tolls}\n💰 هزینه کل: {total}</blockquote>",
        'tolls_none': "ندارد",
        'no_route': "مسیری بین این دو موقعیت پیدا نشد!",
        'btn_route': "انتخاب مسیر {i}",
        'confirm_title': "📜 خلاصه تجارت:\n<blockquote>🎯 مقصد: {dest}\n📦 کالاها:\n{goods}\n🚛 وسایل: {veh}\n🧭 مسیر: {path}\n⏱ مدت سفر: {dur}\n💰 هزینه کل (کارمزد + عوارض): {cost} پول</blockquote>\nتایید می‌کنید قربان؟",
        'btn_send': "✅ ارسال پیشنهاد",
        'insufficient': "💸 موجودی شما برای این تجارت کافی نیست.",
        'offer_sent_sender': "📨 پیشنهاد تجارت #{tid} به {dest} ارسال شد. در انتظار پذیرش لرد مقصد...",
        'btn_cancel_offer': "🚫 لغو پیشنهاد",
        'send_failed': "ارسال پیشنهاد به گروه مقصد ممکن نبود؛ همه مبالغ بازگردانده شد.",
        'offer_msg': "📦 پیشنهاد تجارت #{tid}\n\n🌍 از: {sender}\n👤 لرد: {lord}\n\n📦 کالاها:\n<blockquote>{goods}</blockquote>🧭 مسیر: {path}\n⏱ مدت سفر پس از پذیرش: {dur}\n⌛️ مهلت پذیرش: {exp} دقیقه\n\nآیا این تجارت را می‌پذیرید؟",
        'btn_accept': "✅ پذیرش",
        'btn_decline': "❌ رد",
        'offer_accepted_edit': "\n\n✅ پذیرفته شد — محموله حرکت کرد!",
        'offer_declined_edit': "\n\n❌ رد شد.",
        'offer_cancelled_edit': "\n\n🚫 توسط فرستنده لغو شد.",
        'offer_expired_edit': "\n\n⌛️ مهلت پذیرش تمام شد.",
        'declined_sender': "❌ پیشنهاد تجارت #{tid} رد شد؛ کالاها و هزینه‌ها بازگردانده شد.",
        'cancelled_sender': "🚫 پیشنهاد تجارت #{tid} لغو شد؛ مبالغ بازگردانده شد.",
        'expired_sender': "⌛️ پیشنهاد تجارت #{tid} منقضی شد؛ مبالغ بازگردانده شد.",
        'track_header': "{emoji} تجارت #{tid} | از {src_g} به {dst_g}",
        'track_moving': "🧭 در حرکت به سوی {next} (حدود {min} دقیقه)",
        'track_at': "📍 موقعیت فعلی: {cur}",
        'track_choke': "🪙 محموله از {cur} عبور کرد (عوارض پرداخت شد)",
        'track_cape': "🌊 محموله {cur} را دور زد",
        'track_done': "✅ محموله به مقصد رسید و کالاها تحویل شد!",
        'arrived_receiver': "📦 محموله تجارت #{tid} از {sender} رسید!\n<blockquote>{goods}</blockquote>",
        'depart_channel': "{emoji} محموله تجاری از {src_g} به مقصد {dst_g} حرکت کرد!\n\n🧭 مسیر: {path}\n⏱ زمان تقریبی رسیدن: {dur}",
        'arrive_channel': "{emoji} محموله تجاری از {src_g} به {dst_g} رسید و بار تحویل شد!",
        'adm_title': "🌍 مدیریت تجارت:",
        'btn_home_sea': "⚓️ تعیین موقعیت دریایی گروه‌ها",
        'btn_home_land': "🏔 تعیین موقعیت زمینی گروه‌ها",
        'btn_cfg': "⚙️ تنظیمات تجارت",
        'btn_owners': "🪙 مالکیت تنگه‌ها و گذرگاه‌ها",
        'btn_map': "🗺 ویرایش نقشه تجارت",
        'owner_only': "فقط مالک ربات می‌تواند این کار را انجام دهد.",
        'own_title': "🪙 تنگه‌ها و گذرگاه‌ها (صفحه {p}) — برای تعیین مالک روی یکی بزنید:",
        'own_unowned': "بدون مالک",
        'own_pick': "مالک {node} را انتخاب کنید:",
        'btn_no_owner': "🚫 بدون مالک",
        'own_set': "🪙 {node} از این پس در مالکیت {g} است و عوارض عبور به خزانه‌اش واریز می‌شود.",
        'own_cleared': "🪙 {node} دیگر مالکی ندارد؛ عوارض آن سوزانده می‌شود.",
        'toll_income': "🪙 خزانه شما {amount} پول عوارض دریافت کرد!\nمحموله تجارت #{tid} از {node} عبور کرد.",
        'track_choke_owned': "🪙 محموله از {cur} عبور کرد — عوارض به {owner} پرداخت شد",
        'track_pass': "🌫 محموله از {cur} عبور کرد",
        'adm_pick_group': "گروه را انتخاب کنید:",
        'adm_pick_node': "موقعیت {mode} را برای {g} انتخاب کنید:",
        'home_set': "🏠 موقعیت {mode} گروه {g} روی «{node}» تنظیم شد.",
        'cfg_home': "⚙️ تنظیمات تجارت — کدام دسته را می‌خواهید ببینید؟",
        'cfg_sec_journey': "⏱ سفر و کرایه ({n} مورد)",
        'cfg_sec_capacity': "📦 ظرفیت و هزینه وسایل حمل ({n} مورد)",
        'cfg_sec_toll': "🛣 عوارض گذرگاه‌ها ({n} مورد)",
        'cfg_sec_name_journey': "سفر و کرایه",
        'cfg_sec_name_capacity': "ظرفیت و هزینه وسایل حمل",
        'cfg_sec_name_toll': "عوارض گذرگاه‌ها",
        'cfg_sec_empty': "در این دسته چیزی برای تنظیم نیست.",
        'cfg_title': "⚙️ تنظیمات تجارت — {section} (صفحه {p} از {n})\n"
                     "برای تغییر، روی دکمه همان مورد بزنید:",
        'cfg_row': "<b>{name}</b> — الان: <code>{val}</code>\n<blockquote>{help}</blockquote>",
        'cfg_ask': "<b>{name}</b>\n<blockquote>{help}</blockquote>\n"
                   "مقدار فعلی: {val}\nمقدار جدید را بفرستید:",
        'cfg_set': "✅ {name} روی {val} تنظیم شد.",
        'cfg_toll_label': "🛣 عوارض {node}",
        'cfg_toll_help': "هر محموله‌ای که از این گذرگاه رد شود چقدر عوارض بدهد. "
                         "کشوری که مالک گذرگاه است رایگان رد می‌شود.",
        'btn_cfg_back': "🔙 دسته‌های تنظیمات",
        # RTL: the leading glyph renders on the right, so "previous" points
        # right and "next" points left — mirrored from the LTR languages.
        'btn_prev': "➡️ قبلی",
        'btn_next': "بعدی ⬅️",
        # Route separator. Persian paragraphs run right-to-left, so a route
        # reads correctly only with a left-pointing arrow between the stops.
        'path_arrow': " ← ",
        'dur_hm': "{h} ساعت و {m} دقیقه",
        'dur_m': "{m} دقیقه",
        'wizard_cancelled': "🚫 تجارت لغو شد.",
        'btn_photo': "🖼 عکس تجارت",
        'btn_ph_mode_sea': "🚢 عکس تجارت دریایی — {state}",
        'btn_ph_mode_land': "🐫 عکس تجارت زمینی — {state}",
        'btn_ph_mode_both': "🖼 عکس مشترک (پیش‌فرض) — {state}",
        'btn_ph_back': "🔙 بازگشت به عکس‌ها",
        'ph_home': "🖼 عکس تجارت — کدام را می‌خواهید تنظیم کنید؟\n"
                   "هر نوع تجارت عکس خودش را دارد؛ اگر نداشته باشد، عکس مشترک استفاده می‌شود.",
        'ph_mode_sea': "تجارت دریایی",
        'ph_mode_land': "تجارت زمینی",
        'ph_mode_both': "عکس مشترک",
        'ph_shared': "از عکس مشترک استفاده می‌کند",
        'btn_trade_modes': "🚧 باز/بسته کردن تجارت کشورها",
        'tm_title': "🚧 تجارت هر کشور (صفحه {p} از {n}) — برای تغییر روی کشور بزنید:",
        'tm_group': "🚧 <b>{g}</b>\n<blockquote>{lines}</blockquote>",
        'tm_row': "{mode}: {state}",
        'tm_on': "{mode}✅",
        'tm_off': "{mode}🚫",
        'tm_state_on': "باز",
        'tm_state_off': "بسته",
        'btn_tm_close': "🚫 بستن {mode}",
        'btn_tm_open': "✅ باز کردن {mode}",
        'btn_tm_back': "🔙 فهرست کشورها",
        'tm_toggled': "{mode} حالا {state} است.",
        'tm_closed_here': "🚫 {mode} برای کشور شما بسته است.",
        'tm_closed_there': "🚫 {mode} برای {g} بسته است.",
        'tm_all_closed': "🚫 هر دو نوع تجارت برای کشور شما بسته است. با مدیریت صحبت کنید.",
        'adm_no_groups': "هیچ کشوری ثبت نشده است.",
        'ph_title': "🖼 عکس {mode} — وضعیت فعلی: {state}\n"
                    "این عکس روی پیشنهاد تجارت، پیام رهگیری محموله و اعلان‌های کانال قرار می‌گیرد.",
        'ph_set': "تنظیم شده",
        'ph_unset': "تنظیم نشده",
        'btn_ph_set': "📷 تنظیم عکس",
        'btn_ph_clear': "🗑 حذف عکس",
        'ph_ask': "اکنون عکس {mode} را بفرستید:",
        'ph_saved': "✅ عکس {mode} ذخیره شد.",
        'ph_cleared': "🗑 عکس تجارت حذف شد؛ پیام‌ها دوباره متنی می‌شوند.",
        'ph_not_photo': "این پیام عکس نیست؛ عملیات لغو شد.",
    },
    'en': {
        'err_generic': "Something went wrong. Please try again.",
        'session_expired': "Trade session not found. Start again from the «🚢 World Trade» button.",
        'not_registered': "This group has no lord yet. Register first with /setlord.",
        'not_lord': "Only the lord of this group can do that.",
        'admin_only': "You are not the admin.",
        'already_handled': "This offer is no longer valid.",
        'menu_title': "🌍 World Trade\n\nChoose the type of trade, my lord:",
        'menu_active': "\n\n🧭 Your trades in progress: {n}",
        'btn_sea': "🚢 Sea Trade",
        'btn_land': "🐫 Land Trade",
        'mode_sea': "sea",
        'mode_land': "land",
        'need_home': "🏠 Your group's {mode} location has not been set by the admin yet.",
        'no_dest': "No destination is available for {mode} trade; other groups need a location first.",
        'choose_dest': "🎯 Choose the trade destination:",
        'btn_cancel': "❌ Cancel",
        'goods_title': "📦 Choose the goods to trade (tap an item and enter an amount):\n<blockquote>{lines}</blockquote>📊 Total cargo volume: {vol}",
        'goods_none': "no goods selected yet",
        'btn_goods_done': "✅ Continue",
        'ask_amount': "Enter the amount of {res} (you have: {bal}):",
        'bad_number': "That is not a valid number. Please enter an integer.",
        'too_much': "That is more than you have (balance: {bal}).",
        'need_goods': "Select at least one good.",
        'veh_title_sea': "⚓️ Choose your trade fleet:\n<blockquote>{fleet}</blockquote>\n🧾 Your picks:\n<blockquote>{lines}</blockquote>📦 Cargo volume: {vol}\n🚢 Fleet capacity: {cap}",
        'veh_title_land': "🐫 Prepare your caravan:\n<blockquote>{fleet}</blockquote>\n🧾 Your picks:\n<blockquote>{lines}</blockquote>📦 Cargo volume: {vol}\n🐫 Caravan capacity: {cap}\n💵 Cost per caravan for this trip: {p} money",
        'ask_vcount': "Enter the number of {v} (you own: {bal} | each carries: {cap}):",
        'veh_row': "{name}: carries {cap} each — you own {own}",
        'ask_caravans': "Enter the number of caravans (you own: {bal} | each carries: {cap} | each costs {p} money):",
        'not_enough_units': "That is more than you own (you have: {bal}).",
        'not_enough_cap': "Not enough capacity! Cargo volume is {vol} but capacity is only {cap}.",
        'btn_veh_done': "🗺 Compute routes",
        'routes_title': "🗺 Suggested routes from {src} to {dst}:",
        'route_fast': "⚡️ Fastest route",
        'route_free': "🆓 Toll-free route",
        'route_cheap': "💰 Cheapest route",
        'route_block': "{label}\n<blockquote>⏱ Duration: {dur}\n🧭 Route: {path}\n💵 Base fee: {fee}\n🪙 Tolls: {tolls}\n💰 Total cost: {total}</blockquote>",
        'tolls_none': "none",
        'no_route': "No route found between these two locations!",
        'btn_route': "Choose route {i}",
        'confirm_title': "📜 Trade summary:\n<blockquote>🎯 Destination: {dest}\n📦 Goods:\n{goods}\n🚛 Vehicles: {veh}\n🧭 Route: {path}\n⏱ Duration: {dur}\n💰 Total cost (fee + tolls): {cost} money</blockquote>\nDo you confirm, my lord?",
        'btn_send': "✅ Send offer",
        'insufficient': "💸 You do not have enough for this trade.",
        'offer_sent_sender': "📨 Trade offer #{tid} was sent to {dest}. Awaiting the destination lord's acceptance...",
        'btn_cancel_offer': "🚫 Cancel offer",
        'send_failed': "Could not deliver the offer to the destination group; everything was refunded.",
        'offer_msg': "📦 Trade offer #{tid}\n\n🌍 From: {sender}\n👤 Lord: {lord}\n\n📦 Goods:\n<blockquote>{goods}</blockquote>🧭 Route: {path}\n⏱ Travel time after acceptance: {dur}\n⌛️ Offer expires in: {exp} minutes\n\nDo you accept this trade?",
        'btn_accept': "✅ Accept",
        'btn_decline': "❌ Decline",
        'offer_accepted_edit': "\n\n✅ Accepted — the shipment is on its way!",
        'offer_declined_edit': "\n\n❌ Declined.",
        'offer_cancelled_edit': "\n\n🚫 Cancelled by the sender.",
        'offer_expired_edit': "\n\n⌛️ The offer expired.",
        'declined_sender': "❌ Trade offer #{tid} was declined; goods and fees were refunded.",
        'cancelled_sender': "🚫 Trade offer #{tid} was cancelled; everything was refunded.",
        'expired_sender': "⌛️ Trade offer #{tid} expired; everything was refunded.",
        'track_header': "{emoji} Trade #{tid} | {src_g} → {dst_g}",
        'track_moving': "🧭 Heading toward {next} (about {min} minutes)",
        'track_at': "📍 Current position: {cur}",
        'track_choke': "🪙 The shipment passed {cur} (toll paid)",
        'track_cape': "🌊 The shipment rounded {cur}",
        'track_done': "✅ The shipment arrived and the goods were delivered!",
        'arrived_receiver': "📦 The shipment of trade #{tid} from {sender} has arrived!\n<blockquote>{goods}</blockquote>",
        'depart_channel': "{emoji} A trade shipment departed from {src_g} toward {dst_g}!\n\n🧭 Route: {path}\n⏱ Estimated arrival: {dur}",
        'arrive_channel': "{emoji} The trade shipment from {src_g} arrived at {dst_g} and the cargo was delivered!",
        'adm_title': "🌍 Trade administration:",
        'btn_home_sea': "⚓️ Set groups' sea locations",
        'btn_home_land': "🏔 Set groups' land locations",
        'btn_cfg': "⚙️ Trade settings",
        'btn_owners': "🪙 Chokepoint ownership",
        'btn_map': "🗺 Edit the trade map",
        'owner_only': "Only the bot owner can do that.",
        'own_title': "🪙 Straits, canals and passes (page {p}) — tap one to set its owner:",
        'own_unowned': "unowned",
        'own_pick': "Choose the owner of {node}:",
        'btn_no_owner': "🚫 No owner",
        'own_set': "🪙 {node} is now owned by {g}; passage tolls go to their treasury.",
        'own_cleared': "🪙 {node} is now unowned; its tolls are burned.",
        'toll_income': "🪙 Your treasury collected {amount} money in tolls!\nThe shipment of trade #{tid} passed {node}.",
        'track_choke_owned': "🪙 The shipment passed {cur} — toll paid to {owner}",
        'track_pass': "🌫 The shipment passed {cur}",
        'adm_pick_group': "Choose a group:",
        'adm_pick_node': "Choose the {mode} location for {g}:",
        'home_set': "🏠 The {mode} location of {g} was set to «{node}».",
        'cfg_home': "⚙️ Trade settings — which group do you want?",
        'cfg_sec_journey': "⏱ Journeys and fees ({n})",
        'cfg_sec_capacity': "📦 Vehicle capacity and cost ({n})",
        'cfg_sec_toll': "🛣 Chokepoint tolls ({n})",
        'cfg_sec_name_journey': "journeys and fees",
        'cfg_sec_name_capacity': "vehicle capacity and cost",
        'cfg_sec_name_toll': "chokepoint tolls",
        'cfg_sec_empty': "There is nothing to set in this group.",
        'cfg_title': "⚙️ Trade settings — {section} (page {p} of {n})\n"
                     "Tap a setting's button to change it:",
        'cfg_row': "<b>{name}</b> — now: <code>{val}</code>\n<blockquote>{help}</blockquote>",
        'cfg_ask': "<b>{name}</b>\n<blockquote>{help}</blockquote>\n"
                   "Current value: {val}\nSend the new one:",
        'cfg_set': "✅ {name} was set to {val}.",
        'cfg_toll_label': "🛣 Toll at {node}",
        'cfg_toll_help': "What every convoy passing this chokepoint pays. The "
                         "country that owns it passes for free.",
        'btn_cfg_back': "🔙 Setting groups",
        'btn_prev': "⬅️ Prev",
        'btn_next': "Next ➡️",
        'path_arrow': " → ",
        'dur_hm': "{h}h {m}m",
        'dur_m': "{m} minutes",
        'wizard_cancelled': "🚫 Trade cancelled.",
        'btn_photo': "🖼 Trade photo",
        'btn_ph_mode_sea': "🚢 Sea trade photo — {state}",
        'btn_ph_mode_land': "🐫 Land trade photo — {state}",
        'btn_ph_mode_both': "🖼 Shared photo (fallback) — {state}",
        'btn_ph_back': "🔙 Back to photos",
        'ph_home': "🖼 Trade photo — which one do you want to set?\n"
                   "Each kind of trade has its own; without one it uses the shared photo.",
        'ph_mode_sea': "sea trade",
        'ph_mode_land': "land trade",
        'ph_mode_both': "the shared photo",
        'ph_shared': "using the shared photo",
        'btn_trade_modes': "🚧 Open/close a country's trade",
        'tm_title': "🚧 Trade per country (page {p} of {n}) — tap a country to change it:",
        'tm_group': "🚧 <b>{g}</b>\n<blockquote>{lines}</blockquote>",
        'tm_row': "{mode}: {state}",
        'tm_on': "{mode}✅",
        'tm_off': "{mode}🚫",
        'tm_state_on': "open",
        'tm_state_off': "closed",
        'btn_tm_close': "🚫 Close {mode}",
        'btn_tm_open': "✅ Open {mode}",
        'btn_tm_back': "🔙 Country list",
        'tm_toggled': "{mode} is now {state}.",
        'tm_closed_here': "🚫 {mode} is closed for your country.",
        'tm_closed_there': "🚫 {mode} is closed for {g}.",
        'tm_all_closed': "🚫 Both kinds of trade are closed for your country. Talk to an admin.",
        'adm_no_groups': "No country is registered yet.",
        'ph_title': "🖼 Photo for {mode} — currently: {state}\n"
                    "It is attached to the trade offer, the convoy tracking message "
                    "and the channel announcements.",
        'ph_set': "set",
        'ph_unset': "not set",
        'btn_ph_set': "📷 Set photo",
        'btn_ph_clear': "🗑 Remove photo",
        'ph_ask': "Send the photo for {mode} now:",
        'ph_saved': "✅ The photo for {mode} was saved.",
        'ph_cleared': "🗑 The trade photo was removed; messages go back to plain text.",
        'ph_not_photo': "That message is not a photo; the operation was cancelled.",
    },
    'tr': {
        'err_generic': "Bir hata oluştu. Lütfen tekrar deneyin.",
        'session_expired': "Ticaret oturumu bulunamadı. «🚢 Dünya Ticareti» düğmesinden yeniden başlayın.",
        'not_registered': "Bu grubun henüz bir lordu yok. Önce /setlord ile kayıt olun.",
        'not_lord': "Bunu yalnızca bu grubun lordu yapabilir.",
        'admin_only': "Yönetici değilsiniz.",
        'already_handled': "Bu teklif artık geçerli değil.",
        'menu_title': "🌍 Dünya Ticareti\n\nTicaret türünü seçin lordum:",
        'menu_active': "\n\n🧭 Devam eden ticaretleriniz: {n}",
        'btn_sea': "🚢 Deniz Ticareti",
        'btn_land': "🐫 Kara Ticareti",
        'mode_sea': "deniz",
        'mode_land': "kara",
        'need_home': "🏠 Grubunuzun {mode} konumu henüz yönetici tarafından belirlenmedi.",
        'no_dest': "{mode} ticareti için uygun bir hedef yok; diğer grupların önce konumu olmalı.",
        'choose_dest': "🎯 Ticaret hedefini seçin:",
        'btn_cancel': "❌ İptal",
        'goods_title': "📦 Ticaret mallarını seçin (bir mala dokunup miktar girin):\n<blockquote>{lines}</blockquote>📊 Toplam yük hacmi: {vol}",
        'goods_none': "henüz mal seçilmedi",
        'btn_goods_done': "✅ Devam",
        'ask_amount': "{res} miktarını girin (mevcut: {bal}):",
        'bad_number': "Geçersiz sayı. Lütfen bir tam sayı girin.",
        'too_much': "Sahip olduğunuzdan fazla (mevcut: {bal}).",
        'need_goods': "En az bir mal seçin.",
        'veh_title_sea': "⚓️ Ticaret filonuzu seçin:\n<blockquote>{fleet}</blockquote>\n🧾 Seçiminiz:\n<blockquote>{lines}</blockquote>📦 Yük hacmi: {vol}\n🚢 Filo kapasitesi: {cap}",
        'veh_title_land': "🐫 Kervanınızı hazırlayın:\n<blockquote>{fleet}</blockquote>\n🧾 Seçiminiz:\n<blockquote>{lines}</blockquote>📦 Yük hacmi: {vol}\n🐫 Kervan kapasitesi: {cap}\n💵 Bu sefer için kervan başına maliyet: {p} para",
        'ask_vcount': "{v} sayısını girin (sahip olduğunuz: {bal} | her biri {cap} taşır):",
        'veh_row': "{name}: her biri {cap} taşır — sahip olduğunuz {own}",
        'ask_caravans': "Kervan sayısını girin (sahip olduğunuz: {bal} | her biri {cap} taşır | her biri {p} para):",
        'not_enough_units': "Sahip olduğunuzdan fazla (mevcut: {bal}).",
        'not_enough_cap': "Kapasite yetersiz! Yük hacmi {vol} ama kapasite yalnızca {cap}.",
        'btn_veh_done': "🗺 Rotaları hesapla",
        'routes_title': "🗺 {src} → {dst} için önerilen rotalar:",
        'route_fast': "⚡️ En hızlı rota",
        'route_free': "🆓 Geçiş ücretsiz rota",
        'route_cheap': "💰 En ucuz rota",
        'route_block': "{label}\n<blockquote>⏱ Süre: {dur}\n🧭 Rota: {path}\n💵 Taban ücret: {fee}\n🪙 Geçiş ücretleri: {tolls}\n💰 Toplam maliyet: {total}</blockquote>",
        'tolls_none': "yok",
        'no_route': "Bu iki konum arasında rota bulunamadı!",
        'btn_route': "Rota {i} seç",
        'confirm_title': "📜 Ticaret özeti:\n<blockquote>🎯 Hedef: {dest}\n📦 Mallar:\n{goods}\n🚛 Araçlar: {veh}\n🧭 Rota: {path}\n⏱ Süre: {dur}\n💰 Toplam maliyet (ücret + geçişler): {cost} para</blockquote>\nOnaylıyor musunuz lordum?",
        'btn_send': "✅ Teklifi gönder",
        'insufficient': "💸 Bu ticaret için yeterli kaynağınız yok.",
        'offer_sent_sender': "📨 #{tid} ticaret teklifi {dest} grubuna gönderildi. Hedef lordun kabulü bekleniyor...",
        'btn_cancel_offer': "🚫 Teklifi iptal et",
        'send_failed': "Teklif hedef gruba iletilemedi; her şey iade edildi.",
        'offer_msg': "📦 Ticaret teklifi #{tid}\n\n🌍 Gönderen: {sender}\n👤 Lord: {lord}\n\n📦 Mallar:\n<blockquote>{goods}</blockquote>🧭 Rota: {path}\n⏱ Kabul sonrası yolculuk süresi: {dur}\n⌛️ Teklifin geçerliliği: {exp} dakika\n\nBu ticareti kabul ediyor musunuz?",
        'btn_accept': "✅ Kabul et",
        'btn_decline': "❌ Reddet",
        'offer_accepted_edit': "\n\n✅ Kabul edildi — sevkiyat yola çıktı!",
        'offer_declined_edit': "\n\n❌ Reddedildi.",
        'offer_cancelled_edit': "\n\n🚫 Gönderen tarafından iptal edildi.",
        'offer_expired_edit': "\n\n⌛️ Teklifin süresi doldu.",
        'declined_sender': "❌ #{tid} ticaret teklifi reddedildi; mallar ve ücretler iade edildi.",
        'cancelled_sender': "🚫 #{tid} ticaret teklifi iptal edildi; her şey iade edildi.",
        'expired_sender': "⌛️ #{tid} ticaret teklifinin süresi doldu; her şey iade edildi.",
        'track_header': "{emoji} Ticaret #{tid} | {src_g} → {dst_g}",
        'track_moving': "🧭 {next} yönünde ilerliyor (yaklaşık {min} dakika)",
        'track_at': "📍 Mevcut konum: {cur}",
        'track_choke': "🪙 Sevkiyat {cur} geçişini tamamladı (geçiş ücreti ödendi)",
        'track_cape': "🌊 Sevkiyat {cur} burnunu dolaştı",
        'track_done': "✅ Sevkiyat hedefe ulaştı ve mallar teslim edildi!",
        'arrived_receiver': "📦 {sender} grubundan #{tid} ticaret sevkiyatı ulaştı!\n<blockquote>{goods}</blockquote>",
        'depart_channel': "{emoji} {src_g} grubundan {dst_g} hedefine bir ticaret sevkiyatı yola çıktı!\n\n🧭 Rota: {path}\n⏱ Tahmini varış: {dur}",
        'arrive_channel': "{emoji} {src_g} grubundan gelen ticaret sevkiyatı {dst_g} hedefine ulaştı ve yük teslim edildi!",
        'adm_title': "🌍 Ticaret yönetimi:",
        'btn_home_sea': "⚓️ Grupların deniz konumlarını ayarla",
        'btn_home_land': "🏔 Grupların kara konumlarını ayarla",
        'btn_cfg': "⚙️ Ticaret ayarları",
        'btn_owners': "🪙 Boğaz ve geçit sahipliği",
        'btn_map': "🗺 Ticaret haritasını düzenle",
        'owner_only': "Bunu yalnızca bot sahibi yapabilir.",
        'own_title': "🪙 Boğazlar, kanallar ve geçitler (sayfa {p}) — sahibini ayarlamak için birine dokunun:",
        'own_unowned': "sahipsiz",
        'own_pick': "{node} sahibini seçin:",
        'btn_no_owner': "🚫 Sahipsiz",
        'own_set': "🪙 {node} artık {g} grubuna ait; geçiş ücretleri hazinesine gider.",
        'own_cleared': "🪙 {node} artık sahipsiz; geçiş ücretleri yakılır.",
        'toll_income': "🪙 Hazineniz {amount} para geçiş ücreti topladı!\n#{tid} ticaretinin sevkiyatı {node} geçişini kullandı.",
        'track_choke_owned': "🪙 Sevkiyat {cur} geçişini tamamladı — ücret {owner} grubuna ödendi",
        'track_pass': "🌫 Sevkiyat {cur} geçişini tamamladı",
        'adm_pick_group': "Bir grup seçin:",
        'adm_pick_node': "{g} için {mode} konumunu seçin:",
        'home_set': "🏠 {g} grubunun {mode} konumu «{node}» olarak ayarlandı.",
        'cfg_home': "⚙️ Ticaret ayarları — hangi grubu görmek istiyorsunuz?",
        'cfg_sec_journey': "⏱ Yolculuk ve ücretler ({n})",
        'cfg_sec_capacity': "📦 Araç kapasitesi ve maliyeti ({n})",
        'cfg_sec_toll': "🛣 Geçit ücretleri ({n})",
        'cfg_sec_name_journey': "yolculuk ve ücretler",
        'cfg_sec_name_capacity': "araç kapasitesi ve maliyeti",
        'cfg_sec_name_toll': "geçit ücretleri",
        'cfg_sec_empty': "Bu grupta ayarlanacak bir şey yok.",
        'cfg_title': "⚙️ Ticaret ayarları — {section} (sayfa {p}/{n})\n"
                     "Değiştirmek için ilgili düğmeye dokunun:",
        'cfg_row': "<b>{name}</b> — şu an: <code>{val}</code>\n<blockquote>{help}</blockquote>",
        'cfg_ask': "<b>{name}</b>\n<blockquote>{help}</blockquote>\n"
                   "Mevcut değer: {val}\nYenisini gönderin:",
        'cfg_set': "✅ {name} değeri {val} olarak ayarlandı.",
        'cfg_toll_label': "🛣 {node} geçit ücreti",
        'cfg_toll_help': "Bu geçitten geçen her konvoyun ödediği ücret. Geçidin "
                         "sahibi olan ülke bedava geçer.",
        'btn_cfg_back': "🔙 Ayar grupları",
        'btn_prev': "⬅️ Önceki",
        'btn_next': "Sonraki ➡️",
        'path_arrow': " → ",
        'dur_hm': "{h} sa {m} dk",
        'dur_m': "{m} dakika",
        'wizard_cancelled': "🚫 Ticaret iptal edildi.",
        'btn_photo': "🖼 Ticaret fotoğrafı",
        'btn_ph_mode_sea': "🚢 Deniz ticareti fotoğrafı — {state}",
        'btn_ph_mode_land': "🐫 Kara ticareti fotoğrafı — {state}",
        'btn_ph_mode_both': "🖼 Ortak fotoğraf (yedek) — {state}",
        'btn_ph_back': "🔙 Fotoğraflara dön",
        'ph_home': "🖼 Ticaret fotoğrafı — hangisini ayarlamak istiyorsunuz?\n"
                   "Her ticaret türünün kendi fotoğrafı vardır; yoksa ortak fotoğraf kullanılır.",
        'ph_mode_sea': "deniz ticareti",
        'ph_mode_land': "kara ticareti",
        'ph_mode_both': "ortak fotoğraf",
        'ph_shared': "ortak fotoğrafı kullanıyor",
        'btn_trade_modes': "🚧 Ülke ticaretini aç/kapat",
        'tm_title': "🚧 Ülke bazında ticaret (sayfa {p}/{n}) — değiştirmek için bir ülkeye dokunun:",
        'tm_group': "🚧 <b>{g}</b>\n<blockquote>{lines}</blockquote>",
        'tm_row': "{mode}: {state}",
        'tm_on': "{mode}✅",
        'tm_off': "{mode}🚫",
        'tm_state_on': "açık",
        'tm_state_off': "kapalı",
        'btn_tm_close': "🚫 {mode} kapat",
        'btn_tm_open': "✅ {mode} aç",
        'btn_tm_back': "🔙 Ülke listesi",
        'tm_toggled': "{mode} artık {state}.",
        'tm_closed_here': "🚫 Ülkeniz için {mode} kapalı.",
        'tm_closed_there': "🚫 {g} için {mode} kapalı.",
        'tm_all_closed': "🚫 Ülkeniz için her iki ticaret türü de kapalı. Bir yöneticiyle konuşun.",
        'adm_no_groups': "Henüz kayıtlı bir ülke yok.",
        'ph_title': "🖼 {mode} fotoğrafı — şu an: {state}\n"
                    "Ticaret teklifine, konvoy takip mesajına ve kanal duyurularına eklenir.",
        'ph_set': "ayarlandı",
        'ph_unset': "ayarlanmadı",
        'btn_ph_set': "📷 Fotoğrafı ayarla",
        'btn_ph_clear': "🗑 Fotoğrafı kaldır",
        'ph_ask': "{mode} için fotoğrafı şimdi gönderin:",
        'ph_saved': "✅ {mode} fotoğrafı kaydedildi.",
        'ph_cleared': "🗑 Ticaret fotoğrafı kaldırıldı; mesajlar yeniden düz metin olacak.",
        'ph_not_photo': "Bu mesaj bir fotoğraf değil; işlem iptal edildi.",
    },
}

# ---------------------------------------------------------------------------
# Init / infrastructure
# ---------------------------------------------------------------------------


def init(bot, conn, admin_id, channel_id, lang='fa', is_admin=None, audit=None,
         is_owner=None):
    """Wire the trade system into a running bot. Call once at startup."""
    global _bot, _conn, _ADMIN, _CHANNEL, _lang, _ticker_started, _is_admin, _is_owner, _audit
    assert lang in STRINGS, f"unsupported lang: {lang}"
    assert set(STRINGS['fa']) == set(STRINGS['en']) == set(STRINGS['tr']), \
        "STRINGS language key sets differ"
    _bot = bot
    _conn = conn
    _ADMIN = admin_id
    _CHANNEL = channel_id
    _lang = lang
    # admin_panel supplies this so promoted admins reach the trade screens too;
    # without it only the owner id from the config counts.
    _is_admin = is_admin if is_admin is not None else (lambda uid: uid == admin_id)
    # Deleting part of the map is owner-only; editing it is not.
    _is_owner = is_owner if is_owner is not None else (lambda uid: uid == admin_id)
    _audit = audit       # admin_panel.log, so trade admin actions reach the action log
    _migrate()
    _seed_config()
    # The world map is data. Seed it, and let it refuse to delete a node a
    # convoy is still sailing towards.
    trade_map.init(conn)
    trade_map.set_node_guard(active_route_nodes)
    trade_map_admin.init(bot, lang, _require_admin, _require_owner, _answer, _next_step, _log,
                         _toll, _set_toll, _owner_name)
    if not _ticker_started:
        _ticker_started = True
        t = threading.Thread(target=_ticker_loop, daemon=True)
        t.start()


def _migrate():
    with _lock:
        for col in ('home_sea', 'home_land'):
            try:
                _conn.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass  # column already exists
        # Which of a country's two routes an admin has closed. Absent means open,
        # so nothing has to be written for the countries that trade both ways.
        _conn.execute('''CREATE TABLE IF NOT EXISTS group_trade_modes (
            group_id INTEGER NOT NULL,
            mode     TEXT NOT NULL,
            open     INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (group_id, mode)
        )''')
        _conn.execute('''CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_group_id   INTEGER NOT NULL,
            sender_user_id    INTEGER NOT NULL,
            receiver_group_id INTEGER NOT NULL,
            receiver_user_id  INTEGER NOT NULL,
            mode        TEXT NOT NULL,
            goods       TEXT NOT NULL,
            vehicles    TEXT NOT NULL,
            route       TEXT NOT NULL,
            leg_minutes TEXT NOT NULL,
            tolls       TEXT DEFAULT '[]',
            leg         INTEGER DEFAULT 0,
            fee_paid    INTEGER DEFAULT 0,
            status      TEXT DEFAULT 'offered',
            offered_at  INTEGER,
            departed_at INTEGER,
            next_eta    INTEGER,
            offer_chat_id INTEGER, offer_msg_id INTEGER,
            track_chat_id INTEGER, track_msg_id INTEGER
        )''')
        try:
            # older databases created before chokepoint ownership existed
            _conn.execute("ALTER TABLE trades ADD COLUMN tolls TEXT DEFAULT '[]'")
        except sqlite3.OperationalError:
            pass
        # Whether the offer / tracking message was sent with a photo. Needed
        # because a photo message must be edited as a caption, and the admin
        # may change the photo while trades are already in flight.
        for col in ('offer_photo', 'track_photo'):
            try:
                _conn.execute(f"ALTER TABLE trades ADD COLUMN {col} INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
        _conn.execute('''CREATE TABLE IF NOT EXISTS trade_config (
            key TEXT PRIMARY KEY, value INTEGER NOT NULL)''')
        # trade_config only holds integers; the photo file_id needs text.
        _conn.execute('''CREATE TABLE IF NOT EXISTS trade_settings (
            key TEXT PRIMARY KEY, value TEXT NOT NULL)''')
        _conn.execute('''CREATE TABLE IF NOT EXISTS chokepoint_owners (
            node_id TEXT PRIMARY KEY, group_id INTEGER NOT NULL)''')
        _conn.commit()


def _seed_config():
    with _lock:
        for k, v in CONFIG_DEFAULTS.items():
            _conn.execute("INSERT OR IGNORE INTO trade_config (key, value) VALUES (?, ?)", (k, v))
        _conn.commit()


def cfg(key):
    with _lock:
        row = _conn.execute("SELECT value FROM trade_config WHERE key=?", (key,)).fetchone()
    return row[0] if row else CONFIG_DEFAULTS.get(key, 0)


def set_cfg(key, value):
    with _lock:
        _conn.execute("INSERT OR REPLACE INTO trade_config (key, value) VALUES (?, ?)", (key, int(value)))
        _conn.commit()


# Telegram rejects captions longer than this, so long bodies stay text-only.
CAPTION_LIMIT = 1024
# The photo a sea convoy is announced with, the one a land convoy gets, and the
# single photo that predates the split. A mode with no photo of its own falls
# back to the shared one, so an existing install keeps the picture it had until
# somebody sets a sea or land one deliberately.
PHOTO_KEY = 'trade_photo'
PHOTO_KEYS = {'sea': 'trade_photo_sea', 'land': 'trade_photo_land'}
PHOTO_MODES = ('sea', 'land')


def _setting(key):
    with _lock:
        row = _conn.execute("SELECT value FROM trade_settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else ''


def photo(mode=None):
    """file_id of the trade photo for one mode, or '' when none is set.

    With no mode — or for a mode nobody has given a photo of its own — this is
    the shared photo, which is what every announcement used before the split.
    """
    if mode in PHOTO_KEYS:
        own = _setting(PHOTO_KEYS[mode])
        if own:
            return own
    return _setting(PHOTO_KEY)


def own_photo(mode):
    """The photo set for this mode specifically, ignoring the shared fallback."""
    return _setting(PHOTO_KEYS[mode]) if mode in PHOTO_KEYS else _setting(PHOTO_KEY)


def set_photo(file_id, mode=None):
    key = PHOTO_KEYS.get(mode, PHOTO_KEY)
    with _lock:
        if file_id:
            _conn.execute("INSERT OR REPLACE INTO trade_settings (key, value) VALUES (?, ?)",
                          (key, str(file_id)))
        else:
            _conn.execute("DELETE FROM trade_settings WHERE key=?", (key,))
        _conn.commit()


def _send_rich(chat_id, text, mode=None, **kwargs):
    """Send text as a photo caption when a trade photo is set and it fits.

    Returns (message, used_photo) so the caller can record how the message was
    sent — editing it later has to match.
    """
    file_id = photo(mode)
    if file_id and len(text) <= CAPTION_LIMIT:
        try:
            return _bot.send_photo(chat_id, file_id, caption=text, **kwargs), True
        except Exception:
            pass  # stale file_id or upload problem: fall through to plain text
    return _bot.send_message(chat_id, text, **kwargs), False


def _edit_rich(chat_id, msg_id, text, used_photo, **kwargs):
    """Edit a message previously sent by _send_rich, matching its kind."""
    if used_photo:
        _bot.edit_message_caption(caption=text, chat_id=chat_id, message_id=msg_id, **kwargs)
    else:
        _bot.edit_message_text(text, chat_id, msg_id, **kwargs)


def _t(string_id, **kw):
    s = STRINGS[_lang][string_id]
    return s.format(**kw) if kw else s


def _esc(text):
    return html.escape(text, quote=False) if text else text


def _q(sql, params=()):
    """SELECT returning a list of dicts."""
    with _lock:
        cur = _conn.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _exec(sql, params=()):
    with _lock:
        cur = _conn.execute(sql, params)
        _conn.commit()
        return cur


def _title(gid):
    if gid not in _title_cache:
        try:
            _title_cache[gid] = _bot.get_chat(gid).title or str(gid)
        except Exception:
            return str(gid)
    return _title_cache[gid]


def _dur(minutes):
    h, m = divmod(int(minutes), 60)
    return _t('dur_hm', h=h, m=m) if h else _t('dur_m', m=m)


def _answer(call, text=None, alert=False):
    try:
        _bot.answer_callback_query(call.id, text, show_alert=alert)
    except Exception:
        pass


def _is_lord(group_id, user_id):
    with _lock:
        row = _conn.execute("SELECT 1 FROM users WHERE group_id=? AND user_id=?",
                            (group_id, user_id)).fetchone()
    return row is not None


def _lord_row(group_id):
    rows = _q("SELECT user_id, home_sea, home_land FROM users WHERE group_id=?", (group_id,))
    return rows[0] if rows else None


def _next_step(message, user_id, fn):
    """register_next_step_handler that ignores messages from other users."""
    def wrapper(msg):
        if msg.from_user is None or msg.from_user.id != user_id:
            _bot.register_next_step_handler(message, wrapper)
            return
        fn(msg)
    _bot.register_next_step_handler(message, wrapper)


# ---------------------------------------------------------------------------
# Graph helpers / routing
# ---------------------------------------------------------------------------


def _nodes(mode):
    return trade_map.nodes(mode)


def _node(mode, nid):
    return trade_map.node(mode, nid)


def _node_name(mode, nid):
    return trade_map.name(nid, _lang)


def _mode_name(mode):
    return _t('mode_sea' if mode == 'sea' else 'mode_land')


def _mode_emoji(mode):
    return '🚢' if mode == 'sea' else '🐫'


def _toll(nid):
    # cfg() falls back to CONFIG_DEFAULTS and then to 0, so a chokepoint an
    # admin drew on the map is simply free until someone prices it.
    return cfg('toll_' + nid)


def _owner_of(nid):
    with _lock:
        row = _conn.execute("SELECT group_id FROM chokepoint_owners WHERE node_id=?",
                            (nid,)).fetchone()
    return row[0] if row else None


def _set_owner(nid, gid):
    with _lock:
        if gid:
            _conn.execute("INSERT OR REPLACE INTO chokepoint_owners (node_id, group_id) "
                          "VALUES (?, ?)", (nid, gid))
        else:
            _conn.execute("DELETE FROM chokepoint_owners WHERE node_id=?", (nid,))
        _conn.commit()


def _set_toll(nid, amount):
    set_cfg('toll_' + nid, max(0, int(amount)))


def _owner_name(nid):
    """The title of the group that owns a chokepoint, or None."""
    gid = _owner_of(nid)
    return _title(gid) if gid else None


def _toll_for(nid, sender_gid=None):
    """Effective toll: owners pass their own chokepoints for free."""
    amt = _toll(nid)
    if amt and sender_gid is not None and _owner_of(nid) == sender_gid:
        return 0
    return amt


def _mode_of_node(nid):
    return trade_map.mode_of(nid) or 'sea'


def _adj(mode):
    return trade_map.adjacency(mode)


def _dijkstra(adj, src, dst, blocked=frozenset(), cost_fn=None):
    if src in blocked or dst in blocked or src not in adj or dst not in adj:
        return None
    dist = {src: 0}
    prev = {}
    pq = [(0, src)]
    done = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in done:
            continue
        done.add(u)
        if u == dst:
            path = [dst]
            while path[-1] != src:
                path.append(prev[path[-1]])
            return d, path[::-1]
        for v, w in adj[u]:
            if v in blocked or v in done:
                continue
            nd = d + (cost_fn(u, v, w) if cost_fn else w)
            if nd < dist.get(v, float('inf')):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    return None


def _route_info(mode, path, label, local=False, sender_gid=None):
    mpu = cfg('sea_min_per_unit' if mode == 'sea' else 'land_min_per_unit')
    if local:
        leg_units = [1]
        leg_minutes = [mpu]
    else:
        legs = [trade_map.leg(mode, path[i], path[i + 1]) or (0, 0)
                for i in range(len(path) - 1)]
        leg_units = [units for units, _minutes in legs]
        # An edge may carry an exact travel time; without one it is derived
        # from its length, exactly as it always was.
        leg_minutes = [minutes if minutes > 0 else units * mpu for units, minutes in legs]
    units = sum(leg_units)
    tolls = [(nid, _toll_for(nid, sender_gid)) for nid in path]
    tolls = [(nid, amt) for nid, amt in tolls if amt > 0]
    base_fee = units * cfg('fee_per_unit')
    toll_total = sum(a for _, a in tolls)
    return {
        'label': label, 'path': path, 'units': units,
        'minutes': sum(leg_minutes), 'leg_minutes': leg_minutes,
        'base_fee': base_fee, 'tolls': tolls, 'toll_total': toll_total,
        'money': base_fee + toll_total,
    }


def find_routes(mode, src, dst, sender_gid=None):
    """Up to 3 deduplicated route options between two home nodes.

    When sender_gid is given, chokepoints that group owns are treated as free.
    """
    if src == dst:
        return [_route_info(mode, [src, src], 'route_fast', local=True, sender_gid=sender_gid)]
    adj = _adj(mode)
    fee = cfg('fee_per_unit')
    tolled = frozenset(n for n in _nodes(mode) if _toll_for(n, sender_gid) > 0)
    candidates = []
    r = _dijkstra(adj, src, dst)
    if r:
        candidates.append((r[1], 'route_fast'))
    r = _dijkstra(adj, src, dst, blocked=tolled)
    if r:
        candidates.append((r[1], 'route_free'))
    # money cost dominates, travel units break ties (units are far below 1000)
    r = _dijkstra(adj, src, dst,
                  cost_fn=lambda u, v, w: (w * fee + _toll_for(v, sender_gid)) * 1000 + w)
    if r:
        candidates.append((r[1], 'route_cheap'))
    out, seen = [], set()
    for path, label in candidates:
        key = tuple(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(_route_info(mode, path, label, sender_gid=sender_gid))
    return out


def _path_names(mode, path):
    if len(path) == 2 and path[0] == path[1]:
        return _node_name(mode, path[0])
    return _t('path_arrow').join(_node_name(mode, nid) for nid in path)


# ---------------------------------------------------------------------------
# Economy: escrow / refund / credit (columns come only from internal whitelists)
# ---------------------------------------------------------------------------


def _escrow(group_id, goods, vehicles, fee):
    """Atomically verify and deduct goods + vehicles + fee. False if short."""
    need = dict(goods)
    need['money'] = need.get('money', 0) + fee
    for col, n in vehicles.items():
        if n:
            need[col] = need.get(col, 0) + n
    cols = list(need)
    with _lock:
        row = _conn.execute(
            f"SELECT {', '.join(cols)} FROM users WHERE group_id=?", (group_id,)).fetchone()
        if row is None or any(row[i] < need[c] for i, c in enumerate(cols)):
            return False
        sets = ', '.join(f"{c} = {c} - ?" for c in cols)
        _conn.execute(f"UPDATE users SET {sets} WHERE group_id=?",
                      [need[c] for c in cols] + [group_id])
        _conn.commit()
    return True


def _give(group_id, amounts):
    amounts = {c: n for c, n in amounts.items() if n}
    if not amounts:
        return
    cols = list(amounts)
    sets = ', '.join(f"{c} = {c} + ?" for c in cols)
    _exec(f"UPDATE users SET {sets} WHERE group_id=?",
          [amounts[c] for c in cols] + [group_id])


def _refund(trade):
    """Return goods + vehicles + the full fee to the sender."""
    back = dict(json.loads(trade['goods']))
    back['money'] = back.get('money', 0) + trade['fee_paid']
    for col, n in json.loads(trade['vehicles']).items():
        if n:
            back[col] = back.get(col, 0) + n
    _give(trade['sender_group_id'], back)


# A trade in one of these states still owes somebody a write to the users table:
# 'offered' can be refunded, 'active' will be delivered. Everything else is done.
LIVE_STATUSES = ('offered', 'active')


def active_goods_keys():
    """Asset keys a live trade is still carrying.

    _give() and _refund() build `UPDATE users SET <col> = <col> + ?` from these
    keys. Destroying such a column mid-shipment makes that write raise on a
    column that no longer exists and the cargo is simply lost, so the catalog
    asks this before it drops anything.
    """
    keys = set()
    placeholders = ', '.join('?' * len(LIVE_STATUSES))
    for row in _q(f"SELECT goods, vehicles FROM trades WHERE status IN ({placeholders})",
                  LIVE_STATUSES):
        keys.update(json.loads(row['goods']))
        keys.update(json.loads(row['vehicles']))
    keys.add('money')  # every live trade holds an escrowed fee
    return keys


def active_route_nodes():
    """Map node ids a live trade's stored route still passes through.

    Deleting one of these would strand the shipment: the ticker walks the route
    leg by leg and narrates each node by name.
    """
    nodes = set()
    placeholders = ', '.join('?' * len(LIVE_STATUSES))
    for row in _q(f"SELECT route FROM trades WHERE status IN ({placeholders})", LIVE_STATUSES):
        nodes.update(json.loads(row['route']))
    return nodes


def active_trade_groups():
    """Group ids that are either end of a live trade.

    _give() and _refund() are `UPDATE users ... WHERE group_id=?`. Against a
    deleted row that updates nothing and says nothing, so the escrowed fee and
    the cargo are simply lost. /unsetlord asks this before it removes a country.
    """
    groups = set()
    placeholders = ', '.join('?' * len(LIVE_STATUSES))
    for row in _q(f"SELECT sender_group_id, receiver_group_id FROM trades "
                  f"WHERE status IN ({placeholders})", LIVE_STATUSES):
        groups.add(row['sender_group_id'])
        groups.add(row['receiver_group_id'])
    return groups


# ---------------------------------------------------------------------------
# Callback entry point
# ---------------------------------------------------------------------------


def handle_callback(call):
    parts = call.data.split(':')
    op = parts[1] if len(parts) > 1 else ''
    try:
        if op == 'menu':
            _menu(call)
        elif op == 'm':
            _choose_mode(call, parts[2])
        elif op == 'd':
            _choose_dest(call, int(parts[2]))
        elif op == 'g':
            _ask_amount(call, parts[2])
        elif op == 'gok':
            _goods_done(call)
        elif op == 'v':
            _ask_vcount(call, parts[2])
        elif op == 'vok':
            _vehicles_done(call)
        elif op == 'r':
            _route_chosen(call, int(parts[2]))
        elif op == 'go':
            _confirm_send(call)
        elif op == 'x':
            _cancel_wizard(call)
        elif op == 'a':
            _accept(call, int(parts[2]))
        elif op == 'n':
            _decline(call, int(parts[2]))
        elif op == 'c':
            _cancel_offer(call, int(parts[2]))
        elif op == 'adm':
            _admin_menu(call)
        elif op == 'hm':
            _home_pick_group(call, parts[2])
        elif op == 'hg':
            _home_pick_node(call, parts[2], int(parts[3]))
        elif op == 'h':
            _home_set(call, parts[2], int(parts[3]), parts[4])
        elif op == 'cfgh':
            _config_home(call)
        elif op == 'cfg':
            _config_menu(call, parts[2], int(parts[3]))
        elif op == 'ck':
            _ask_cfg(call, parts[2])
        elif op == 'ow':
            _owner_list(call, int(parts[2]))
        elif op == 'on':
            _owner_pick_group(call, parts[2])
        elif op == 'og':
            _owner_set(call, parts[2], int(parts[3]))
        elif op == 'ph':
            _photo_menu(call)
        elif op == 'phm':
            _photo_mode_menu(call, parts[2])
        elif op == 'phs':
            _photo_ask(call, parts[2])
        elif op == 'phc':
            _photo_clear(call, parts[2])
        elif op == 'tm':
            _mode_list(call, int(parts[2]))
        elif op == 'tmg':
            _mode_screen(call, int(parts[2]))
        elif op == 'tmt':
            _mode_toggle(call, int(parts[2]), parts[3])
        elif op in trade_map_admin.OPS:
            trade_map_admin.handle(call, parts)
        else:
            _answer(call, _t('err_generic'))
    except Exception:
        traceback.print_exc()
        _answer(call, _t('err_generic'))


# ---------------------------------------------------------------------------
# Trade wizard
# ---------------------------------------------------------------------------


def _menu(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    lord = _lord_row(chat_id)
    if lord is None:
        _bot.send_message(chat_id, _t('not_registered'))
        _answer(call)
        return
    if not _is_lord(chat_id, user_id):
        _answer(call, _t('not_lord'), alert=True)
        return
    n = _q("SELECT COUNT(*) AS n FROM trades WHERE sender_group_id=? AND status IN ('offered','active')",
           (chat_id,))[0]['n']
    text = _t('menu_title')
    if n:
        text += _t('menu_active', n=n)
    markup = types.InlineKeyboardMarkup(row_width=2)
    # A route an admin closed for this country is not offered at all — a button
    # that always refuses reads as a bug rather than as a rule.
    buttons = [types.InlineKeyboardButton(_t('btn_' + mode), callback_data=f'trd:m:{mode}')
               for mode in PHOTO_MODES if mode_open(chat_id, mode)]
    if not buttons:
        _bot.send_message(chat_id, _t('tm_all_closed'))
        _answer(call)
        return
    markup.add(*buttons)
    _bot.send_message(chat_id, text, reply_markup=markup)
    _answer(call)


def _choose_mode(call, mode):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    if not _is_lord(chat_id, user_id):
        _answer(call, _t('not_lord'), alert=True)
        return
    if not mode_open(chat_id, mode):
        _answer(call)
        _bot.send_message(chat_id, _t('tm_closed_here', mode=_mode_name(mode)))
        return
    home_col = 'home_sea' if mode == 'sea' else 'home_land'
    lord = _lord_row(chat_id)
    if lord is None or not lord[home_col]:
        _answer(call)
        _bot.send_message(chat_id, _t('need_home', mode=_mode_name(mode)))
        return
    # A country whose route is closed cannot receive that way either, so it is
    # left off the destination list rather than refusing at the last step.
    dests = [d for d in
             _q(f"SELECT DISTINCT group_id FROM users WHERE group_id != ? AND {home_col} != ''",
                (chat_id,))
             if mode_open(d['group_id'], mode)]
    if not dests:
        _answer(call)
        _bot.send_message(chat_id, _t('no_dest', mode=_mode_name(mode)))
        return
    _ctx[user_id] = {'chat_id': chat_id, 'mode': mode, 'goods': {}, 'vehicles': {}}
    markup = types.InlineKeyboardMarkup(row_width=1)
    for d in dests:
        markup.add(types.InlineKeyboardButton(_title(d['group_id']),
                                              callback_data=f"trd:d:{d['group_id']}"))
    markup.add(types.InlineKeyboardButton(_t('btn_cancel'), callback_data='trd:x'))
    _bot.send_message(chat_id, _t('choose_dest'), reply_markup=markup)
    _answer(call)


def _get_ctx(call):
    c = _ctx.get(call.from_user.id)
    if not c:
        _answer(call, _t('session_expired'), alert=True)
        return None
    return c


def _choose_dest(call, dest_gid):
    c = _get_ctx(call)
    if not c:
        return
    c['dest'] = dest_gid
    _answer(call)
    _send_goods_menu(call.from_user.id)


def _goods_lines(goods):
    if not goods:
        return _t('goods_none')
    return '\n'.join(f"• {_res_name(col)}: {amt}" for col, amt in goods.items())


def _send_goods_menu(user_id):
    c = _ctx.get(user_id)
    if not c:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for col in resource_codes():
        amt = c['goods'].get(col, 0)
        label = _res_name(col) + (f" ({amt})" if amt else "")
        buttons.append(types.InlineKeyboardButton(label, callback_data=f'trd:g:{col}'))
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton(_t('btn_goods_done'), callback_data='trd:gok'),
               types.InlineKeyboardButton(_t('btn_cancel'), callback_data='trd:x'))
    vol = sum(c['goods'].values())
    _bot.send_message(c['chat_id'],
                      _t('goods_title', lines=_goods_lines(c['goods']), vol=vol),
                      reply_markup=markup, parse_mode='HTML')


def _balance(group_id, col):
    with _lock:
        row = _conn.execute(f"SELECT {col} FROM users WHERE group_id=?", (group_id,)).fetchone()
    return row[0] if row else 0


def _ask_amount(call, code):
    c = _get_ctx(call)
    if not c:
        return
    col = _res_column(code)
    if not col:
        _answer(call, _t('err_generic'))
        return
    user_id = call.from_user.id
    bal = _balance(c['chat_id'], col)
    _answer(call)
    _bot.send_message(c['chat_id'], _t('ask_amount', res=_res_name(col), bal=bal))

    def on_amount(msg):
        cc = _ctx.get(user_id)
        if not cc:
            return
        try:
            val = int(msg.text.strip())
        except (ValueError, AttributeError):
            _bot.send_message(cc['chat_id'], _t('bad_number'))
            _send_goods_menu(user_id)
            return
        if val < 0:
            _bot.send_message(cc['chat_id'], _t('bad_number'))
        elif val > _balance(cc['chat_id'], col):
            _bot.send_message(cc['chat_id'], _t('too_much', bal=_balance(cc['chat_id'], col)))
        elif val == 0:
            cc['goods'].pop(col, None)
        else:
            cc['goods'][col] = val
        _send_goods_menu(user_id)

    _next_step(call.message, user_id, on_amount)


def _goods_done(call):
    c = _get_ctx(call)
    if not c:
        return
    if not c['goods']:
        _answer(call, _t('need_goods'), alert=True)
        return
    _answer(call)
    _send_vehicles_menu(call.from_user.id)


def _fleet_capacity(c):
    return sum(c['vehicles'].get(col, 0) * cfg(cap_key)
               for _, col, cap_key in VEHICLES[c['mode']])


def _veh_lines(vehicles):
    lines = [f"• {_veh_name(col)}: {n} × {_veh_capacity(col)} = {n * _veh_capacity(col)}"
             for col, n in vehicles.items() if n]
    return '\n'.join(lines) if lines else '—'


def _fleet_table(group_id, mode):
    """One line per vehicle this mode can use: what it carries and how many
    the country actually has. Capacity used to be invisible until the cargo
    would not fit; now it is on the screen where the fleet is picked."""
    return '\n'.join(
        _t('veh_row', name=_veh_name(col), cap=_veh_capacity(col),
           own=_balance(group_id, col))
        for _code, col, _cap in VEHICLES[mode])


def _send_vehicles_menu(user_id):
    c = _ctx.get(user_id)
    if not c:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    vol = sum(c['goods'].values())
    cap = _fleet_capacity(c)
    buttons = []
    for code, col, _cap in VEHICLES[c['mode']]:
        n = c['vehicles'].get(col, 0)
        label = _veh_name(col) + (f" ({n})" if n else "")
        buttons.append(types.InlineKeyboardButton(label, callback_data=f'trd:v:{code}'))
    markup.add(*buttons)
    if c['mode'] == 'sea':
        text = _t('veh_title_sea', lines=_veh_lines(c['vehicles']), vol=vol, cap=cap,
                  fleet=_fleet_table(c['chat_id'], 'sea'))
    else:
        text = _t('veh_title_land', lines=_veh_lines(c['vehicles']), vol=vol, cap=cap,
                  fleet=_fleet_table(c['chat_id'], 'land'), p=cfg('caravan_cost'))
    markup.add(types.InlineKeyboardButton(_t('btn_veh_done'), callback_data='trd:vok'),
               types.InlineKeyboardButton(_t('btn_cancel'), callback_data='trd:x'))
    _bot.send_message(c['chat_id'], text, reply_markup=markup, parse_mode='HTML')


def _ask_vcount(call, code):
    c = _get_ctx(call)
    if not c:
        return
    user_id = call.from_user.id
    _answer(call)
    col = VEH_BY_CODE.get(code)
    if not col or col not in [v[1] for v in VEHICLES[c['mode']]]:
        _answer(call, _t('err_generic'))
        return
    bal = _balance(c['chat_id'], col)
    if col == 'caravans':
        _bot.send_message(c['chat_id'],
                          _t('ask_caravans', bal=bal, cap=_veh_capacity(col),
                             p=cfg('caravan_cost')))
    else:
        _bot.send_message(c['chat_id'],
                          _t('ask_vcount', v=_veh_name(col), bal=bal,
                             cap=_veh_capacity(col)))

    def on_count(msg):
        cc = _ctx.get(user_id)
        if not cc:
            return
        try:
            val = int(msg.text.strip())
        except (ValueError, AttributeError):
            _bot.send_message(cc['chat_id'], _t('bad_number'))
            _send_vehicles_menu(user_id)
            return
        if val < 0:
            _bot.send_message(cc['chat_id'], _t('bad_number'))
        elif val > _balance(cc['chat_id'], col):
            _bot.send_message(cc['chat_id'],
                              _t('not_enough_units', bal=_balance(cc['chat_id'], col)))
        elif val == 0:
            cc['vehicles'].pop(col, None)
        else:
            cc['vehicles'][col] = val
        _send_vehicles_menu(user_id)

    _next_step(call.message, user_id, on_count)


def _vehicles_done(call):
    c = _get_ctx(call)
    if not c:
        return
    vol = sum(c['goods'].values())
    cap = _fleet_capacity(c)
    if cap < vol:
        _answer(call, _t('not_enough_cap', vol=vol, cap=cap), alert=True)
        return
    mode = c['mode']
    home_col = 'home_sea' if mode == 'sea' else 'home_land'
    src_row = _lord_row(c['chat_id'])
    dst_row = _lord_row(c['dest'])
    if not src_row or not src_row[home_col] or not dst_row or not dst_row[home_col]:
        _answer(call)
        _bot.send_message(c['chat_id'], _t('need_home', mode=_mode_name(mode)))
        return
    routes = find_routes(mode, src_row[home_col], dst_row[home_col], sender_gid=c['chat_id'])
    if not routes:
        _answer(call)
        _bot.send_message(c['chat_id'], _t('no_route'))
        return
    c['routes'] = routes
    _answer(call)
    blocks = []
    markup = types.InlineKeyboardMarkup(row_width=len(routes))
    btns = []
    for i, r in enumerate(routes):
        tolls = ', '.join(f"{_node_name(mode, nid)}: {amt}" for nid, amt in r['tolls']) \
            or _t('tolls_none')
        blocks.append(_t('route_block',
                         label=f"{i + 1}️⃣ {_t(r['label'])}",
                         dur=_dur(r['minutes']),
                         path=_path_names(mode, r['path']),
                         fee=r['base_fee'], tolls=tolls, total=r['money']))
        btns.append(types.InlineKeyboardButton(_t('btn_route', i=i + 1),
                                               callback_data=f'trd:r:{i}'))
    markup.add(*btns)
    markup.add(types.InlineKeyboardButton(_t('btn_cancel'), callback_data='trd:x'))
    text = _t('routes_title',
              src=_node_name(mode, src_row[home_col]),
              dst=_node_name(mode, dst_row[home_col])) + '\n\n' + '\n'.join(blocks)
    _bot.send_message(c['chat_id'], text, reply_markup=markup, parse_mode='HTML')


def _trade_cost(c, route):
    caravan_cost = c['vehicles'].get('caravans', 0) * cfg('caravan_cost') \
        if c['mode'] == 'land' else 0
    return route['money'] + caravan_cost


def _route_chosen(call, i):
    c = _get_ctx(call)
    if not c or 'routes' not in c or not (0 <= i < len(c['routes'])):
        _answer(call, _t('session_expired'), alert=True)
        return
    c['route_i'] = i
    r = c['routes'][i]
    mode = c['mode']
    veh = ', '.join(f"{n}× {_veh_name(col)}" for col, n in c['vehicles'].items() if n)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(_t('btn_send'), callback_data='trd:go'),
               types.InlineKeyboardButton(_t('btn_cancel'), callback_data='trd:x'))
    _answer(call)
    _bot.send_message(c['chat_id'],
                      _t('confirm_title',
                         dest=_esc(_title(c['dest'])),
                         goods=_goods_lines(c['goods']),
                         veh=veh or '—',
                         path=_path_names(mode, r['path']),
                         dur=_dur(r['minutes']),
                         cost=_trade_cost(c, r)),
                      reply_markup=markup, parse_mode='HTML')


def _confirm_send(call):
    c = _get_ctx(call)
    if not c or 'route_i' not in c:
        _answer(call, _t('session_expired'), alert=True)
        return
    user_id = call.from_user.id
    r = c['routes'][c['route_i']]
    fee = _trade_cost(c, r)
    receiver = _lord_row(c['dest'])
    if receiver is None:
        _answer(call, _t('err_generic'))
        return
    # Re-checked here rather than trusted from the picker: an admin can close a
    # route while a lord is halfway through loading a convoy.
    if not mode_open(c['chat_id'], c['mode']):
        _answer(call)
        _bot.send_message(c['chat_id'], _t('tm_closed_here', mode=_mode_name(c['mode'])))
        return
    if not mode_open(c['dest'], c['mode']):
        _answer(call)
        _bot.send_message(c['chat_id'], _t('tm_closed_there', mode=_mode_name(c['mode']),
                                           g=_esc(_title(c['dest']))), parse_mode='HTML')
        return
    if not _escrow(c['chat_id'], c['goods'], c['vehicles'], fee):
        _answer(call)
        _bot.send_message(c['chat_id'], _t('insufficient'))
        return
    now = int(time.time())
    cur = _exec(
        """INSERT INTO trades (sender_group_id, sender_user_id, receiver_group_id,
                               receiver_user_id, mode, goods, vehicles, route,
                               leg_minutes, tolls, fee_paid, status, offered_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'offered', ?)""",
        (c['chat_id'], user_id, c['dest'], receiver['user_id'], c['mode'],
         json.dumps(c['goods']), json.dumps(c['vehicles']), json.dumps(r['path']),
         json.dumps(r['leg_minutes']), json.dumps(r['tolls']), fee, now))
    tid = cur.lastrowid
    trade = _q("SELECT * FROM trades WHERE id=?", (tid,))[0]

    # deliver the offer to the receiver's group; on failure refund everything
    try:
        lord_info = _bot.get_chat(user_id)
        lord_link = f"<a href='tg://user?id={user_id}'>{_esc(lord_info.first_name)}</a>"
    except Exception:
        lord_link = str(user_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(_t('btn_accept'), callback_data=f'trd:a:{tid}'),
               types.InlineKeyboardButton(_t('btn_decline'), callback_data=f'trd:n:{tid}'))
    offer_text = _t('offer_msg', tid=tid, sender=_esc(_title(c['chat_id'])), lord=lord_link,
                    goods=_goods_lines(c['goods']),
                    path=_path_names(c['mode'], r['path']),
                    dur=_dur(r['minutes']), exp=cfg('offer_expiry_min'))
    try:
        sent, with_photo = _send_rich(c['dest'], offer_text, mode=c['mode'],
                                      reply_markup=markup, parse_mode='HTML')
    except Exception:
        _refund(trade)
        _exec("UPDATE trades SET status='cancelled' WHERE id=?", (tid,))
        _answer(call)
        _bot.send_message(c['chat_id'], _t('send_failed'))
        _ctx.pop(user_id, None)
        return
    _exec("UPDATE trades SET offer_chat_id=?, offer_msg_id=?, offer_photo=? WHERE id=?",
          (sent.chat.id, sent.message_id, 1 if with_photo else 0, tid))

    markup2 = types.InlineKeyboardMarkup()
    markup2.add(types.InlineKeyboardButton(_t('btn_cancel_offer'), callback_data=f'trd:c:{tid}'))
    _bot.send_message(c['chat_id'],
                      _t('offer_sent_sender', tid=tid, dest=_esc(_title(c['dest']))),
                      reply_markup=markup2, parse_mode='HTML')
    _ctx.pop(user_id, None)
    _answer(call)


def _cancel_wizard(call):
    _ctx.pop(call.from_user.id, None)
    _answer(call)
    try:
        _bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                       reply_markup=None)
    except Exception:
        pass
    _bot.send_message(call.message.chat.id, _t('wizard_cancelled'))


# ---------------------------------------------------------------------------
# Offer lifecycle
# ---------------------------------------------------------------------------


def _get_trade(tid):
    rows = _q("SELECT * FROM trades WHERE id=?", (tid,))
    return rows[0] if rows else None


def _edit_offer_msg(trade, suffix_key):
    if not trade['offer_chat_id'] or not trade['offer_msg_id']:
        return
    try:
        _bot.edit_message_reply_markup(trade['offer_chat_id'], trade['offer_msg_id'],
                                       reply_markup=None)
    except Exception:
        pass
    try:
        _bot.send_message(trade['offer_chat_id'],
                          f"#{trade['id']}" + _t(suffix_key))
    except Exception:
        pass


def _accept(call, tid):
    with _lock:
        trade = _get_trade(tid)
        if not trade or trade['status'] != 'offered':
            _answer(call, _t('already_handled'), alert=True)
            return
        if not _is_lord(trade['receiver_group_id'], call.from_user.id):
            _answer(call, _t('not_lord'), alert=True)
            return
        now = int(time.time())
        leg_minutes = json.loads(trade['leg_minutes'])
        _exec("UPDATE trades SET status='active', departed_at=?, next_eta=? "
              "WHERE id=? AND status='offered'",
              (now, now + leg_minutes[0] * 60, tid))
    trade = _get_trade(tid)
    _answer(call)
    _edit_offer_msg(trade, 'offer_accepted_edit')
    # live tracking message in the sender's group
    try:
        sent, with_photo = _send_rich(trade['sender_group_id'], _track_text(trade),
                                      mode=trade['mode'], parse_mode='HTML')
        _exec("UPDATE trades SET track_chat_id=?, track_msg_id=?, track_photo=? WHERE id=?",
              (sent.chat.id, sent.message_id, 1 if with_photo else 0, tid))
    except Exception:
        pass
    # channel announcement
    route = json.loads(trade['route'])
    try:
        _send_rich(_CHANNEL, mode=trade['mode'], text=
                   _t('depart_channel', emoji=_mode_emoji(trade['mode']),
                      src_g=_esc(_title(trade['sender_group_id'])),
                      dst_g=_esc(_title(trade['receiver_group_id'])),
                      path=_path_names(trade['mode'], route),
                      dur=_dur(sum(json.loads(trade['leg_minutes'])))),
                   parse_mode='HTML')
    except Exception:
        pass


def _finish_offer(call, tid, require_sender, status, edit_key, sender_key):
    """Shared decline/cancel path: guard, refund, mark, notify."""
    with _lock:
        trade = _get_trade(tid)
        if not trade or trade['status'] != 'offered':
            _answer(call, _t('already_handled'), alert=True)
            return
        if require_sender:
            if not _is_lord(trade['sender_group_id'], call.from_user.id):
                _answer(call, _t('not_lord'), alert=True)
                return
        else:
            if not _is_lord(trade['receiver_group_id'], call.from_user.id):
                _answer(call, _t('not_lord'), alert=True)
                return
        _exec("UPDATE trades SET status=? WHERE id=? AND status='offered'", (status, tid))
        _refund(trade)
    _answer(call)
    _edit_offer_msg(trade, edit_key)
    try:
        _bot.send_message(trade['sender_group_id'], _t(sender_key, tid=tid))
    except Exception:
        pass


def _decline(call, tid):
    _finish_offer(call, tid, False, 'declined', 'offer_declined_edit', 'declined_sender')


def _cancel_offer(call, tid):
    _finish_offer(call, tid, True, 'cancelled', 'offer_cancelled_edit', 'cancelled_sender')


# ---------------------------------------------------------------------------
# Background ticker: expiry, movement, arrival
# ---------------------------------------------------------------------------


def _track_text(trade):
    mode = trade['mode']
    emoji = _mode_emoji(mode)
    route = json.loads(trade['route'])
    leg = trade['leg']
    parts = [_t('track_header', emoji=emoji, tid=trade['id'],
                src_g=_esc(_title(trade['sender_group_id'])),
                dst_g=_esc(_title(trade['receiver_group_id'])))]
    prog = []
    for i, nid in enumerate(route):
        icon = '✅' if i < leg else (emoji if i == leg else '▫️')
        prog.append(f"{icon} {_node_name(mode, nid)}")
    parts.append('\n'.join(prog))
    if trade['status'] == 'delivered' or leg >= len(route) - 1:
        parts.append(_t('track_done'))
    else:
        cur_nid = route[leg]
        kind = _node(mode, cur_nid)['kind']
        if kind in ('strait', 'canal', 'pass'):
            charged = dict(json.loads(trade['tolls'] or '[]'))
            owner = _owner_of(cur_nid)
            if charged.get(cur_nid) and owner:
                parts.append(_t('track_choke_owned', cur=_node_name(mode, cur_nid),
                                owner=_esc(_title(owner))))
            elif charged.get(cur_nid):
                parts.append(_t('track_choke', cur=_node_name(mode, cur_nid)))
            else:
                parts.append(_t('track_pass', cur=_node_name(mode, cur_nid)))
        elif kind == 'cape':
            parts.append(_t('track_cape', cur=_node_name(mode, cur_nid)))
        else:
            parts.append(_t('track_at', cur=_node_name(mode, cur_nid)))
        mins = max(0, (trade['next_eta'] or 0) - int(time.time())) // 60
        parts.append(_t('track_moving', next=_node_name(mode, route[leg + 1]), min=mins))
    return '\n\n'.join(parts)


def _edit_tracking(trade):
    if not trade['track_chat_id'] or not trade['track_msg_id']:
        return
    text = _track_text(trade)
    try:
        _edit_rich(trade['track_chat_id'], trade['track_msg_id'], text,
                   bool(trade.get('track_photo')), parse_mode='HTML')
    except Exception:
        # tracking message gone (deleted?) -> try a fresh one
        try:
            sent, with_photo = _send_rich(trade['track_chat_id'], text,
                                          mode=trade['mode'], parse_mode='HTML')
            _exec("UPDATE trades SET track_msg_id=?, track_photo=? WHERE id=?",
                  (sent.message_id, 1 if with_photo else 0, trade['id']))
        except Exception:
            pass


def _settle_tolls(trade, route, from_leg, to_leg):
    """Pay the snapshotted tolls for nodes passed in (from_leg, to_leg] to their
    current owners; tolls on unowned chokepoints stay burned."""
    charged = dict(json.loads(trade['tolls'] or '[]'))
    for nid in route[from_leg + 1:to_leg + 1]:
        amount = charged.get(nid)
        if not amount:
            continue
        owner = _owner_of(nid)
        if not owner:
            continue
        _give(owner, {'money': amount})
        try:
            _bot.send_message(owner,
                              _t('toll_income', amount=amount, tid=trade['id'],
                                 node=_node_name(trade['mode'], nid)))
        except Exception:
            pass


def _arrive(trade):
    """Deliver an active trade. Returns True if this call actually delivered it."""
    with _lock:
        cur = _get_trade(trade['id'])
        if not cur or cur['status'] != 'active':
            return False
        route = json.loads(cur['route'])
        _exec("UPDATE trades SET status='delivered', leg=?, next_eta=NULL WHERE id=?",
              (len(route) - 1, trade['id']))
        _give(cur['receiver_group_id'], json.loads(cur['goods']))          # goods to receiver
        _give(cur['sender_group_id'], json.loads(cur['vehicles']))         # ships come home
    trade = _get_trade(trade['id'])
    _edit_tracking(trade)
    try:
        _bot.send_message(trade['receiver_group_id'],
                          _t('arrived_receiver', tid=trade['id'],
                             sender=_esc(_title(trade['sender_group_id'])),
                             goods=_goods_lines(json.loads(trade['goods']))),
                          parse_mode='HTML')
    except Exception:
        pass
    try:
        _send_rich(_CHANNEL, mode=trade['mode'], text=
                   _t('arrive_channel', emoji=_mode_emoji(trade['mode']),
                      src_g=_esc(_title(trade['sender_group_id'])),
                      dst_g=_esc(_title(trade['receiver_group_id']))),
                   parse_mode='HTML')
    except Exception:
        pass
    return True


def _tick():
    now = int(time.time())
    # 1. expire stale offers
    expiry = cfg('offer_expiry_min') * 60
    stale = _q("SELECT * FROM trades WHERE status='offered' AND offered_at + ? <= ?",
               (expiry, now))
    for trade in stale:
        with _lock:
            cur = _get_trade(trade['id'])
            if not cur or cur['status'] != 'offered':
                continue
            _exec("UPDATE trades SET status='expired' WHERE id=? AND status='offered'",
                  (trade['id'],))
            _refund(cur)
        _edit_offer_msg(cur, 'offer_expired_edit')
        try:
            _bot.send_message(cur['sender_group_id'], _t('expired_sender', tid=cur['id']))
        except Exception:
            pass
    # 2. advance active trades (catch-up loop covers restarts in one pass)
    active = _q("SELECT * FROM trades WHERE status='active' AND next_eta IS NOT NULL "
                "AND next_eta <= ?", (now,))
    for trade in active:
        route = json.loads(trade['route'])
        legs = json.loads(trade['leg_minutes'])
        old_leg = trade['leg']
        leg = old_leg
        eta = trade['next_eta']
        arrived = False
        while eta <= now:
            leg += 1
            if leg >= len(route) - 1:
                arrived = True
                break
            eta += legs[leg] * 60
        if arrived:
            if _arrive(trade):
                _settle_tolls(trade, route, old_leg, len(route) - 1)
        else:
            cur = _exec("UPDATE trades SET leg=?, next_eta=? WHERE id=? AND status='active'",
                        (leg, eta, trade['id']))
            if cur.rowcount:
                _settle_tolls(trade, route, old_leg, leg)
            trade = _get_trade(trade['id'])
            if trade and trade['status'] == 'active':
                _edit_tracking(trade)


def _ticker_loop():
    while True:
        try:
            _tick()
        except Exception:
            traceback.print_exc()
        time.sleep(25)


# ---------------------------------------------------------------------------
# Admin panel
# ---------------------------------------------------------------------------


def _require_admin(call):
    if not _admin_check(call.from_user.id):
        _answer(call, _t('admin_only'), alert=True)
        return False
    return True


def _admin_check(user_id):
    return _is_admin(user_id) if _is_admin is not None else (user_id == _ADMIN)


def _require_owner(call):
    if not (_is_owner(call.from_user.id) if _is_owner is not None
            else call.from_user.id == _ADMIN):
        _answer(call, _t('owner_only'), alert=True)
        return False
    return True


def _log(actor_id, action, target='', detail=''):
    """Forward an admin mutation to the dashboard's action log, if wired."""
    if _audit is None:
        return
    try:
        _audit(actor_id, action, target, detail)
    except Exception:
        pass


def _admin_menu(call):
    if not _require_admin(call):
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(_t('btn_home_sea'), callback_data='trd:hm:s'),
               types.InlineKeyboardButton(_t('btn_home_land'), callback_data='trd:hm:l'),
               types.InlineKeyboardButton(_t('btn_owners'), callback_data='trd:ow:0'),
               types.InlineKeyboardButton(_t('btn_map'), callback_data='trd:map'),
               types.InlineKeyboardButton(_t('btn_cfg'), callback_data='trd:cfgh'),
               types.InlineKeyboardButton(_t('btn_trade_modes'), callback_data='trd:tm:0'),
               types.InlineKeyboardButton(_t('btn_photo'), callback_data='trd:ph'))
    _bot.send_message(call.message.chat.id, _t('adm_title'), reply_markup=markup)
    _answer(call)


def _photo_state(mode):
    """Whether this mode has its own picture, borrows the shared one, or has none."""
    if own_photo(mode):
        return _t('ph_set')
    return _t('ph_shared') if photo(mode) else _t('ph_unset')


def _photo_menu(call):
    """Sea and land are announced separately, so each picks its own picture."""
    if not _require_admin(call):
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for mode in PHOTO_MODES:
        markup.add(types.InlineKeyboardButton(
            _t('btn_ph_mode_' + mode, state=_photo_state(mode)),
            callback_data=f'trd:phm:{mode}'))
    # The shared picture is still reachable: it is what a mode with no picture
    # of its own falls back to, and an old install already has one.
    markup.add(types.InlineKeyboardButton(_t('btn_ph_mode_both', state=_photo_state('both')),
                                          callback_data='trd:phm:both'))
    _bot.send_message(call.message.chat.id, _t('ph_home'), reply_markup=markup)
    _answer(call)


def _photo_mode_menu(call, mode):
    if not _require_admin(call):
        return
    if mode not in PHOTO_MODES and mode != 'both':
        _answer(call, _t('err_generic'))
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(_t('btn_ph_set'), callback_data=f'trd:phs:{mode}'))
    if own_photo(mode if mode in PHOTO_MODES else None):
        markup.add(types.InlineKeyboardButton(_t('btn_ph_clear'),
                                              callback_data=f'trd:phc:{mode}'))
    markup.add(types.InlineKeyboardButton(_t('btn_ph_back'), callback_data='trd:ph'))
    _bot.send_message(call.message.chat.id,
                      _t('ph_title', mode=_t('ph_mode_' + mode), state=_photo_state(mode)),
                      reply_markup=markup)
    _answer(call)


def _photo_ask(call, mode):
    if not _require_admin(call):
        return
    if mode not in PHOTO_MODES and mode != 'both':
        _answer(call, _t('err_generic'))
        return
    _answer(call)
    _bot.send_message(call.message.chat.id, _t('ph_ask', mode=_t('ph_mode_' + mode)))
    _next_step(call.message, call.from_user.id,
               lambda msg: _photo_save(msg, call.from_user.id, mode))


def _photo_save(message, actor_id, mode='both'):
    if not _admin_check(actor_id):
        return
    if not getattr(message, 'photo', None):
        _bot.send_message(message.chat.id, _t('ph_not_photo'))
        return
    set_photo(message.photo[-1].file_id, mode if mode in PHOTO_MODES else None)
    _log(actor_id, 'trade_photo', mode, 'set')
    _bot.send_message(message.chat.id, _t('ph_saved', mode=_t('ph_mode_' + mode)))


def _photo_clear(call, mode):
    if not _require_admin(call):
        return
    if mode not in PHOTO_MODES and mode != 'both':
        _answer(call, _t('err_generic'))
        return
    set_photo('', mode if mode in PHOTO_MODES else None)
    _log(call.from_user.id, 'trade_photo', mode, 'cleared')
    _answer(call, _t('ph_cleared'))
    _photo_mode_menu(call, mode)


# ---------------------------------------------------------------------------
# Item 10: closing one route for one country
#
# Not every country has a coast. An admin closes a country's sea or land trade
# here, and that country neither sends nor receives that way until it is
# reopened. Trades already in flight are left alone — the cargo has to arrive.
# ---------------------------------------------------------------------------


def mode_open(group_id, mode):
    """False only when an admin has deliberately closed this route here."""
    rows = _q("SELECT open FROM group_trade_modes WHERE group_id=? AND mode=?",
              (group_id, mode))
    return bool(rows[0]['open']) if rows else True


def set_mode_open(group_id, mode, is_open):
    if mode not in PHOTO_MODES:
        return
    _exec("INSERT OR REPLACE INTO group_trade_modes (group_id, mode, open) VALUES (?, ?, ?)",
          (group_id, mode, 1 if is_open else 0))


def open_modes(group_id):
    return {mode: mode_open(group_id, mode) for mode in PHOTO_MODES}


def _mode_list(call, page):
    """Every country, with which of its two routes are open."""
    if not _require_admin(call):
        return
    groups = [g['group_id'] for g in _q("SELECT DISTINCT group_id FROM users ORDER BY group_id")]
    if not groups:
        _answer(call, _t('adm_no_groups'), alert=True)
        return
    pages = max(1, (len(groups) + OWN_PAGE_SIZE - 1) // OWN_PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    markup = types.InlineKeyboardMarkup(row_width=1)
    for gid in groups[page * OWN_PAGE_SIZE:(page + 1) * OWN_PAGE_SIZE]:
        state = open_modes(gid)
        marks = ' '.join(_t('tm_on' if state[m] else 'tm_off', mode=_t('ph_mode_' + m))
                         for m in PHOTO_MODES)
        markup.add(types.InlineKeyboardButton(f"{_title(gid)} — {marks}",
                                              callback_data=f'trd:tmg:{gid}'))
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(_t('btn_prev'), callback_data=f'trd:tm:{page - 1}'))
    if page < pages - 1:
        nav.append(types.InlineKeyboardButton(_t('btn_next'), callback_data=f'trd:tm:{page + 1}'))
    if nav:
        markup.add(*nav)
    _bot.send_message(call.message.chat.id, _t('tm_title', p=page + 1, n=pages),
                      reply_markup=markup)
    _answer(call)


def _mode_screen(call, gid):
    if not _require_admin(call):
        return
    state = open_modes(gid)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for mode in PHOTO_MODES:
        key = 'btn_tm_close' if state[mode] else 'btn_tm_open'
        markup.add(types.InlineKeyboardButton(_t(key, mode=_t('ph_mode_' + mode)),
                                              callback_data=f'trd:tmt:{gid}:{mode}'))
    markup.add(types.InlineKeyboardButton(_t('btn_tm_back'), callback_data='trd:tm:0'))
    lines = '\n'.join(_t('tm_row', mode=_t('ph_mode_' + m),
                          state=_t('tm_state_on' if state[m] else 'tm_state_off'))
                      for m in PHOTO_MODES)
    _bot.send_message(call.message.chat.id,
                      _t('tm_group', g=_esc(_title(gid)), lines=lines),
                      reply_markup=markup, parse_mode='HTML')
    _answer(call)


def _mode_toggle(call, gid, mode):
    if not _require_admin(call):
        return
    if mode not in PHOTO_MODES:
        _answer(call, _t('err_generic'))
        return
    new_state = not mode_open(gid, mode)
    set_mode_open(gid, mode, new_state)
    _log(call.from_user.id, 'trade_mode', _title(gid),
         f"{mode}={'open' if new_state else 'closed'}")
    _answer(call, _t('tm_toggled', mode=_t('ph_mode_' + mode),
                     state=_t('tm_state_on' if new_state else 'tm_state_off')))
    _mode_screen(call, gid)


def _home_pick_group(call, mcode):
    if not _require_admin(call):
        return
    mode = 'sea' if mcode == 's' else 'land'
    home_col = 'home_sea' if mode == 'sea' else 'home_land'
    groups = _q(f"SELECT DISTINCT group_id, {home_col} AS home FROM users")
    markup = types.InlineKeyboardMarkup(row_width=1)
    for g in groups:
        label = _title(g['group_id'])
        if g['home']:
            label += f" ({_node_name(mode, g['home'])})" if g['home'] in _nodes(mode) else ''
        markup.add(types.InlineKeyboardButton(label,
                                              callback_data=f"trd:hg:{mcode}:{g['group_id']}"))
    _bot.send_message(call.message.chat.id, _t('adm_pick_group'), reply_markup=markup)
    _answer(call)


def _home_pick_node(call, mcode, gid):
    if not _require_admin(call):
        return
    mode = 'sea' if mcode == 's' else 'land'
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(node['names'][_lang],
                                          callback_data=f'trd:h:{mcode}:{gid}:{nid}')
               for nid, node in _nodes(mode).items() if node['home']]
    markup.add(*buttons)
    _bot.send_message(call.message.chat.id,
                      _t('adm_pick_node', mode=_mode_name(mode), g=_esc(_title(gid))),
                      reply_markup=markup, parse_mode='HTML')
    _answer(call)


def _home_set(call, mcode, gid, nid):
    if not _require_admin(call):
        return
    mode = 'sea' if mcode == 's' else 'land'
    if nid not in _nodes(mode) or not _node(mode, nid)['home']:
        _answer(call, _t('err_generic'))
        return
    home_col = 'home_sea' if mode == 'sea' else 'home_land'
    _exec(f"UPDATE users SET {home_col}=? WHERE group_id=?", (nid, gid))
    _log(call.from_user.id, 'group_home', _title(gid), f"{mode}={nid}")
    _answer(call)
    _bot.send_message(call.message.chat.id,
                      _t('home_set', mode=_mode_name(mode), g=_esc(_title(gid)),
                         node=_node_name(mode, nid)),
                      parse_mode='HTML')


def _chokepoints():
    """All tolled chokepoint node ids, sea first then land."""
    return trade_map.chokepoints()


OWN_PAGE_SIZE = 8


def _owner_list(call, page):
    if not _require_admin(call):
        return
    nids = _chokepoints()
    pages = (len(nids) + OWN_PAGE_SIZE - 1) // OWN_PAGE_SIZE
    page = max(0, min(page, pages - 1))
    markup = types.InlineKeyboardMarkup(row_width=1)
    for nid in nids[page * OWN_PAGE_SIZE:(page + 1) * OWN_PAGE_SIZE]:
        owner = _owner_of(nid)
        owner_label = _title(owner) if owner else _t('own_unowned')
        markup.add(types.InlineKeyboardButton(
            f"{_node_name(_mode_of_node(nid), nid)} — {owner_label}",
            callback_data=f'trd:on:{nid}'))
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(_t('btn_prev'), callback_data=f'trd:ow:{page - 1}'))
    if page < pages - 1:
        nav.append(types.InlineKeyboardButton(_t('btn_next'), callback_data=f'trd:ow:{page + 1}'))
    if nav:
        markup.add(*nav)
    _bot.send_message(call.message.chat.id, _t('own_title', p=page + 1), reply_markup=markup)
    _answer(call)


def _owner_pick_group(call, nid):
    if not _require_admin(call):
        return
    if nid not in _chokepoints():
        _answer(call, _t('err_generic'))
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for g in _q("SELECT DISTINCT group_id FROM users"):
        markup.add(types.InlineKeyboardButton(_title(g['group_id']),
                                              callback_data=f"trd:og:{nid}:{g['group_id']}"))
    markup.add(types.InlineKeyboardButton(_t('btn_no_owner'), callback_data=f'trd:og:{nid}:0'))
    _bot.send_message(call.message.chat.id,
                      _t('own_pick', node=_node_name(_mode_of_node(nid), nid)),
                      reply_markup=markup)
    _answer(call)


def _owner_set(call, nid, gid):
    if not _require_admin(call):
        return
    if nid not in _chokepoints():
        _answer(call, _t('err_generic'))
        return
    _set_owner(nid, gid)
    node = _node_name(_mode_of_node(nid), nid)
    _log(call.from_user.id, 'chokepoint_owner', node, _title(gid) if gid else '-')
    _answer(call)
    if gid:
        _bot.send_message(call.message.chat.id,
                          _t('own_set', node=node, g=_esc(_title(gid))), parse_mode='HTML')
    else:
        _bot.send_message(call.message.chat.id, _t('own_cleared', node=node))


CFG_PAGE_SIZE = 8


def _config_home(call):
    """The three sections, with a count each, instead of four unlabelled pages."""
    if not _require_admin(call):
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for section, _keys in CONFIG_SECTIONS:
        markup.add(types.InlineKeyboardButton(
            _t('cfg_sec_' + section, n=len(config_keys(section))),
            callback_data=f'trd:cfg:{section}:0'))
    _bot.send_message(call.message.chat.id, _t('cfg_home'), reply_markup=markup)
    _answer(call)


def _config_menu(call, section, page):
    """One section's settings, each shown by name with its current value."""
    if not _require_admin(call):
        return
    keys = config_keys(section)
    if not keys:
        _answer(call, _t('cfg_sec_empty'), alert=True)
        return
    pages = max(1, (len(keys) + CFG_PAGE_SIZE - 1) // CFG_PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    window = keys[page * CFG_PAGE_SIZE:(page + 1) * CFG_PAGE_SIZE]
    markup = types.InlineKeyboardMarkup(row_width=1)
    for k in window:
        markup.add(types.InlineKeyboardButton(f"{config_label(k)} — {cfg(k)}",
                                              callback_data=f'trd:ck:{k}'))
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(_t('btn_prev'),
                                              callback_data=f'trd:cfg:{section}:{page - 1}'))
    if page < pages - 1:
        nav.append(types.InlineKeyboardButton(_t('btn_next'),
                                              callback_data=f'trd:cfg:{section}:{page + 1}'))
    if nav:
        markup.add(*nav)
    markup.add(types.InlineKeyboardButton(_t('btn_cfg_back'), callback_data='trd:cfgh'))
    # The list itself explains what each row does, so nobody has to tap a
    # setting to find out whether it is the one they meant.
    body = '\n'.join(_t('cfg_row', name=config_label(k), val=cfg(k), help=config_help(k))
                     for k in window)
    _bot.send_message(call.message.chat.id,
                      _t('cfg_title', section=_t('cfg_sec_name_' + section),
                         p=page + 1, n=pages) + '\n\n' + body,
                      reply_markup=markup, parse_mode='HTML')
    _answer(call)


def _known_cfg(key):
    """A setting is editable if it shipped with the game or prices a real chokepoint."""
    return key in CONFIG_DEFAULTS or key in toll_keys()


def _ask_cfg(call, key):
    if not _require_admin(call):
        return
    if not _known_cfg(key):
        _answer(call, _t('err_generic'))
        return
    chat_id = call.message.chat.id
    _answer(call)
    _bot.send_message(chat_id, _t('cfg_ask', name=config_label(key), key=key,
                                  val=cfg(key), help=config_help(key)),
                      parse_mode='HTML')

    def on_value(msg):
        try:
            val = int(msg.text.strip())
            if val < 0:
                raise ValueError
        except (ValueError, AttributeError):
            _bot.send_message(chat_id, _t('bad_number'))
            return
        set_cfg(key, val)
        _log(call.from_user.id, 'trade_config', key, str(val))
        _bot.send_message(chat_id, _t('cfg_set', name=config_label(key), val=val))

    _next_step(call.message, call.from_user.id, on_value)
