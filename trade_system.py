# -*- coding: utf-8 -*-
"""World trade system (sea + land) shared by main.py / main-en.py / main-tr.py.

All trade logic lives here once: the world-map graphs, route finding, fees and
tolls, the trade wizard (inline buttons), the offer lifecycle and the
background ticker that moves convoys in real time and live-edits the tracking
message. Player-facing strings are provided in fa/en/tr; each main*.py calls
init(bot, conn, ADMIN_ID, CHANNEL_ID, lang=...) once and forwards callback
queries whose data starts with 'trd:' to handle_callback().
"""

import heapq
import html
import json
import sqlite3
import threading
import time
import traceback

from telebot import types

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------
_bot = None
_conn = None
_ADMIN = 0
_CHANNEL = None
_lang = 'fa'
# RLock: refund/credit helpers are called from code that already holds the lock.
_lock = threading.RLock()
_ctx = {}            # per-user wizard state (in-memory; nothing escrowed before confirm)
_adj_cache = {}
_edge_w_cache = {}
_title_cache = {}
_ticker_started = False

TRADE_PREFIX = 'trd:'

# ---------------------------------------------------------------------------
# World map graphs. Straits/canals/passes are NODES so the ticker can narrate
# them ("passed the Suez Canal") and toll-free routing can simply block them.
# A node is tolled iff trade_config has a 'toll_<id>' key with value > 0.
# ---------------------------------------------------------------------------


def _N(kind, home, fa, en, tr):
    return {'kind': kind, 'home': home, 'names': {'fa': fa, 'en': en, 'tr': tr}}


SEA_NODES = {
    # oceans
    'nat': _N('ocean', True, 'اقیانوس اطلس شمالی', 'North Atlantic Ocean', 'Kuzey Atlantik Okyanusu'),
    'sat': _N('ocean', True, 'اقیانوس اطلس جنوبی', 'South Atlantic Ocean', 'Güney Atlantik Okyanusu'),
    'ind': _N('ocean', True, 'اقیانوس هند', 'Indian Ocean', 'Hint Okyanusu'),
    'npa': _N('ocean', True, 'اقیانوس آرام شمالی', 'North Pacific Ocean', 'Kuzey Pasifik Okyanusu'),
    'spa': _N('ocean', True, 'اقیانوس آرام جنوبی', 'South Pacific Ocean', 'Güney Pasifik Okyanusu'),
    'arc': _N('ocean', True, 'اقیانوس منجمد شمالی', 'Arctic Ocean', 'Arktik Okyanusu'),
    # seas & gulfs
    'nor': _N('sea', True, 'دریای شمال', 'North Sea', 'Kuzey Denizi'),
    'bal': _N('sea', True, 'دریای بالتیک', 'Baltic Sea', 'Baltık Denizi'),
    'med': _N('sea', True, 'دریای مدیترانه', 'Mediterranean Sea', 'Akdeniz'),
    'bla': _N('sea', True, 'دریای سیاه', 'Black Sea', 'Karadeniz'),
    'mar': _N('sea', True, 'دریای مرمره', 'Sea of Marmara', 'Marmara Denizi'),
    'red': _N('sea', True, 'دریای سرخ', 'Red Sea', 'Kızıldeniz'),
    'per': _N('sea', True, 'خلیج فارس', 'Persian Gulf', 'Basra Körfezi'),
    'oma': _N('sea', True, 'دریای عمان و عرب', 'Arabian Sea', 'Umman ve Arap Denizi'),
    'ade': _N('sea', True, 'دریای عدن', 'Gulf of Aden', 'Aden Körfezi'),
    'car': _N('sea', True, 'خلیج کارائیب', 'Caribbean Sea', 'Karayip Denizi'),
    'gmx': _N('sea', True, 'خلیج مکزیک', 'Gulf of Mexico', 'Meksika Körfezi'),
    'scs': _N('sea', True, 'دریای چین جنوبی', 'South China Sea', 'Güney Çin Denizi'),
    'ecs': _N('sea', True, 'دریای چین شرقی', 'East China Sea', 'Doğu Çin Denizi'),
    'yel': _N('sea', True, 'دریای زرد', 'Yellow Sea', 'Sarı Deniz'),
    'jap': _N('sea', True, 'دریای ژاپن', 'Sea of Japan', 'Japon Denizi'),
    'phi': _N('sea', True, 'دریای فیلیپین', 'Philippine Sea', 'Filipin Denizi'),
    'gui': _N('sea', True, 'خلیج گینه', 'Gulf of Guinea', 'Gine Körfezi'),
    # straits (tolled chokepoints)
    'gib': _N('strait', False, 'تنگه جبل‌الطارق', 'Strait of Gibraltar', 'Cebelitarık Boğazı'),
    'bos': _N('strait', False, 'تنگه بسفر', 'Bosphorus Strait', 'İstanbul Boğazı'),
    'dar': _N('strait', False, 'تنگه داردانل', 'Dardanelles Strait', 'Çanakkale Boğazı'),
    'dan': _N('strait', False, 'تنگه دانمارک', 'Danish Straits', 'Danimarka Boğazları'),
    'hor': _N('strait', False, 'تنگه هرمز', 'Strait of Hormuz', 'Hürmüz Boğazı'),
    'bab': _N('strait', False, 'تنگه باب‌المندب', 'Bab-el-Mandeb Strait', 'Bab-ül Mendeb Boğazı'),
    'mal': _N('strait', False, 'تنگه مالاکا', 'Strait of Malacca', 'Malakka Boğazı'),
    'tsu': _N('strait', False, 'تنگه تسوشیما', 'Tsushima Strait', 'Tsushima Boğazı'),
    'ber': _N('strait', False, 'تنگه برینگ', 'Bering Strait', 'Bering Boğazı'),
    'sun': _N('strait', False, 'تنگه سوندا', 'Sunda Strait', 'Sunda Boğazı'),
    'lom': _N('strait', False, 'تنگه لومبوک', 'Lombok Strait', 'Lombok Boğazı'),
    'mag': _N('strait', False, 'تنگه ماژلان', 'Strait of Magellan', 'Macellan Boğazı'),
    'moz': _N('strait', False, 'کانال موزامبیک', 'Mozambique Channel', 'Mozambik Kanalı'),
    # canals (tolled)
    'sue': _N('canal', False, 'کانال سوئز', 'Suez Canal', 'Süveyş Kanalı'),
    'pan': _N('canal', False, 'کانال پاناما', 'Panama Canal', 'Panama Kanalı'),
    'kie': _N('canal', False, 'کانال کیل', 'Kiel Canal', 'Kiel Kanalı'),
    # free capes (long detours)
    'cgh': _N('cape', False, 'دماغه امید نیک', 'Cape of Good Hope', 'Ümit Burnu'),
    'chn': _N('cape', False, 'دماغه هورن', 'Cape Horn', 'Horn Burnu'),
}

# undirected edges: (a, b, weight in distance units)
SEA_EDGES = [
    # Europe / Atlantic
    ('nat', 'nor', 2), ('nor', 'dan', 2), ('dan', 'bal', 1),
    ('nor', 'kie', 1), ('kie', 'bal', 1),
    ('nat', 'gib', 2), ('gib', 'med', 1),
    # Mediterranean / Black Sea
    ('med', 'dar', 2), ('dar', 'mar', 1), ('mar', 'bos', 1), ('bos', 'bla', 1),
    # Suez corridor
    ('med', 'sue', 2), ('sue', 'red', 1), ('red', 'bab', 2), ('bab', 'ade', 1),
    ('ade', 'oma', 2), ('oma', 'hor', 1), ('hor', 'per', 1), ('oma', 'ind', 2),
    # Africa / capes
    ('nat', 'gui', 4), ('gui', 'sat', 2), ('nat', 'sat', 5),
    ('sat', 'cgh', 5), ('cgh', 'ind', 5),
    ('cgh', 'moz', 2), ('moz', 'ind', 2),
    # Americas
    ('nat', 'car', 4), ('car', 'gmx', 1), ('car', 'pan', 1), ('pan', 'spa', 2),
    ('sat', 'mag', 5), ('mag', 'spa', 3), ('sat', 'chn', 6), ('chn', 'spa', 4),
    # Indian Ocean -> East Asia
    ('ind', 'mal', 3), ('mal', 'scs', 1), ('ind', 'sun', 4), ('sun', 'scs', 2),
    ('ind', 'lom', 4), ('lom', 'phi', 3),
    # East Asia
    ('scs', 'ecs', 2), ('ecs', 'yel', 1), ('ecs', 'tsu', 1), ('tsu', 'jap', 1),
    ('jap', 'npa', 2), ('scs', 'phi', 2), ('ecs', 'phi', 2), ('phi', 'npa', 2),
    ('phi', 'spa', 3),
    # Pacific / Arctic
    ('npa', 'spa', 5), ('npa', 'ber', 4), ('ber', 'arc', 1),
    ('arc', 'nat', 5), ('arc', 'nor', 4),
]

LAND_NODES = {
    # regions
    'ibe': _N('region', True, 'ایبریا', 'Iberia', 'İberya'),
    'weu': _N('region', True, 'اروپای غربی', 'Western Europe', 'Batı Avrupa'),
    'eeu': _N('region', True, 'اروپای شرقی', 'Eastern Europe', 'Doğu Avrupa'),
    'ana': _N('region', True, 'آناتولی', 'Anatolia', 'Anadolu'),
    'lev': _N('region', True, 'شام', 'Levant', 'Levant'),
    'egy': _N('region', True, 'مصر', 'Egypt', 'Mısır'),
    'naf': _N('region', True, 'شمال آفریقا', 'North Africa', 'Kuzey Afrika'),
    'waf': _N('region', True, 'غرب آفریقا', 'West Africa', 'Batı Afrika'),
    'eaf': _N('region', True, 'شرق آفریقا', 'East Africa', 'Doğu Afrika'),
    'ara': _N('region', True, 'عربستان', 'Arabia', 'Arabistan'),
    'prs': _N('region', True, 'پارس', 'Persia', 'Pers'),
    'cas': _N('region', True, 'آسیای میانه', 'Central Asia', 'Orta Asya'),
    'hnd': _N('region', True, 'هند', 'India', 'Hindistan'),
    'chi': _N('region', True, 'چین', 'China', 'Çin'),
    'sta': _N('region', True, 'آسیای جنوب شرقی', 'Southeast Asia', 'Güneydoğu Asya'),
    # tolled passes
    'sin': _N('pass', False, 'گذرگاه سینا', 'Sinai Crossing', 'Sina Geçidi'),
    'sah': _N('pass', False, 'مسیر صحرا', 'Sahara Route', 'Sahra Yolu'),
    'cau': _N('pass', False, 'دروازه قفقاز', 'Caucasus Gates', 'Kafkas Kapıları'),
    'zag': _N('pass', False, 'دروازه زاگرس', 'Zagros Gates', 'Zagros Kapıları'),
    'pam': _N('pass', False, 'گذرگاه پامیر', 'Pamir Passes', 'Pamir Geçitleri'),
    'khy': _N('pass', False, 'گذرگاه خیبر', 'Khyber Pass', 'Hayber Geçidi'),
}

LAND_EDGES = [
    ('ibe', 'weu', 2), ('weu', 'eeu', 2), ('eeu', 'ana', 2), ('ana', 'lev', 2),
    ('lev', 'sin', 1), ('sin', 'egy', 1), ('lev', 'ara', 2), ('ara', 'egy', 2),
    ('egy', 'naf', 2), ('naf', 'ibe', 2), ('naf', 'sah', 2), ('sah', 'waf', 2),
    ('egy', 'eaf', 3), ('eaf', 'ara', 2),
    ('eeu', 'cau', 1), ('cau', 'prs', 2), ('lev', 'zag', 1), ('zag', 'prs', 1),
    ('ana', 'prs', 4),
    ('prs', 'cas', 2), ('eeu', 'cas', 4),
    ('cas', 'pam', 1), ('pam', 'chi', 3), ('cas', 'chi', 6),
    ('prs', 'khy', 1), ('khy', 'hnd', 1), ('prs', 'hnd', 4),
    ('hnd', 'sta', 3), ('sta', 'chi', 3), ('hnd', 'chi', 5),
]

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

# tradeable resources: short code <-> users column
RESOURCES = (
    ('mo', 'money'), ('gd', 'gold'), ('ir', 'iron'), ('st', 'stones'),
    ('wd', 'wood'), ('fd', 'food'), ('mt', 'meat'), ('cl', 'clothes'),
)
RES_BY_CODE = dict(RESOURCES)

# sea vehicles: short code, users column, capacity config key
SHIPS = (
    ('s', 'small_ships', 'cap_small'),
    ('m', 'medium_ships', 'cap_medium'),
    ('l', 'large_ships', 'cap_large'),
)
SHIP_BY_CODE = {c: col for c, col, _ in SHIPS}

RES_NAMES = {
    'fa': {'money': '💵 پول', 'gold': '🏅 طلا', 'iron': '🪛 آهن', 'stones': '🪨 سنگ',
           'wood': '🌲 چوب', 'food': '🍞 غذا', 'meat': '🍖 گوشت', 'clothes': '🥋 لباس'},
    'en': {'money': '💵 Money', 'gold': '🏅 Gold', 'iron': '🪛 Iron', 'stones': '🪨 Stones',
           'wood': '🌲 Wood', 'food': '🍞 Food', 'meat': '🍖 Meat', 'clothes': '🥋 Clothes'},
    'tr': {'money': '💵 Para', 'gold': '🏅 Altın', 'iron': '🪛 Demir', 'stones': '🪨 Taş',
           'wood': '🌲 Odun', 'food': '🍞 Yiyecek', 'meat': '🍖 Et', 'clothes': '🥋 Kıyafet'},
}

VEH_NAMES = {
    'fa': {'small_ships': '⛵ کشتی کوچک', 'medium_ships': '🚢 کشتی متوسط',
           'large_ships': '🛳 کشتی بزرگ', 'caravans': '🐫 کاروان'},
    'en': {'small_ships': '⛵ Small Ship', 'medium_ships': '🚢 Medium Ship',
           'large_ships': '🛳 Large Ship', 'caravans': '🐫 Caravan'},
    'tr': {'small_ships': '⛵ Küçük Gemi', 'medium_ships': '🚢 Orta Gemi',
           'large_ships': '🛳 Büyük Gemi', 'caravans': '🐫 Kervan'},
}

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
        'veh_title_sea': "⚓️ ناوگان تجاری را انتخاب کنید:\n<blockquote>{lines}</blockquote>📦 حجم بار: {vol}\n🚢 ظرفیت ناوگان: {cap}",
        'veh_title_land': "🐫 کاروان تجاری را آماده کنید:\n<blockquote>{lines}</blockquote>📦 حجم بار: {vol}\n🐫 ظرفیت کاروان‌ها: {cap}\nظرفیت هر کاروان: {c} | هزینه هر کاروان: {p} پول",
        'ask_vcount': "تعداد {v} را وارد کنید (در اختیار: {bal}):",
        'ask_caravans': "تعداد کاروان را وارد کنید (هزینه هر کاروان {p} پول):",
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
        'adm_pick_group': "گروه را انتخاب کنید:",
        'adm_pick_node': "موقعیت {mode} را برای {g} انتخاب کنید:",
        'home_set': "🏠 موقعیت {mode} گروه {g} روی «{node}» تنظیم شد.",
        'cfg_title': "⚙️ تنظیمات تجارت (صفحه {p}) — برای تغییر روی هر مورد بزنید:",
        'cfg_ask': "مقدار جدید برای {key} را وارد کنید (فعلی: {val}):",
        'cfg_set': "✅ {key} روی {val} تنظیم شد.",
        'btn_prev': "⬅️ قبلی",
        'btn_next': "بعدی ➡️",
        'dur_hm': "{h} ساعت و {m} دقیقه",
        'dur_m': "{m} دقیقه",
        'wizard_cancelled': "🚫 تجارت لغو شد.",
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
        'veh_title_sea': "⚓️ Choose your trade fleet:\n<blockquote>{lines}</blockquote>📦 Cargo volume: {vol}\n🚢 Fleet capacity: {cap}",
        'veh_title_land': "🐫 Prepare your caravan:\n<blockquote>{lines}</blockquote>📦 Cargo volume: {vol}\n🐫 Caravan capacity: {cap}\nCapacity per caravan: {c} | Cost per caravan: {p} money",
        'ask_vcount': "Enter the number of {v} (you own: {bal}):",
        'ask_caravans': "Enter the number of caravans (each costs {p} money):",
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
        'adm_pick_group': "Choose a group:",
        'adm_pick_node': "Choose the {mode} location for {g}:",
        'home_set': "🏠 The {mode} location of {g} was set to «{node}».",
        'cfg_title': "⚙️ Trade settings (page {p}) — tap an entry to change it:",
        'cfg_ask': "Enter the new value for {key} (current: {val}):",
        'cfg_set': "✅ {key} was set to {val}.",
        'btn_prev': "⬅️ Prev",
        'btn_next': "Next ➡️",
        'dur_hm': "{h}h {m}m",
        'dur_m': "{m} minutes",
        'wizard_cancelled': "🚫 Trade cancelled.",
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
        'veh_title_sea': "⚓️ Ticaret filonuzu seçin:\n<blockquote>{lines}</blockquote>📦 Yük hacmi: {vol}\n🚢 Filo kapasitesi: {cap}",
        'veh_title_land': "🐫 Kervanınızı hazırlayın:\n<blockquote>{lines}</blockquote>📦 Yük hacmi: {vol}\n🐫 Kervan kapasitesi: {cap}\nKervan başına kapasite: {c} | Kervan başına maliyet: {p} para",
        'ask_vcount': "{v} sayısını girin (sahip olduğunuz: {bal}):",
        'ask_caravans': "Kervan sayısını girin (her biri {p} para):",
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
        'adm_pick_group': "Bir grup seçin:",
        'adm_pick_node': "{g} için {mode} konumunu seçin:",
        'home_set': "🏠 {g} grubunun {mode} konumu «{node}» olarak ayarlandı.",
        'cfg_title': "⚙️ Ticaret ayarları (sayfa {p}) — değiştirmek için bir girdiye dokunun:",
        'cfg_ask': "{key} için yeni değeri girin (mevcut: {val}):",
        'cfg_set': "✅ {key} değeri {val} olarak ayarlandı.",
        'btn_prev': "⬅️ Önceki",
        'btn_next': "Sonraki ➡️",
        'dur_hm': "{h} sa {m} dk",
        'dur_m': "{m} dakika",
        'wizard_cancelled': "🚫 Ticaret iptal edildi.",
    },
}

# ---------------------------------------------------------------------------
# Init / infrastructure
# ---------------------------------------------------------------------------


def init(bot, conn, admin_id, channel_id, lang='fa'):
    """Wire the trade system into a running bot. Call once at startup."""
    global _bot, _conn, _ADMIN, _CHANNEL, _lang, _ticker_started
    assert lang in STRINGS, f"unsupported lang: {lang}"
    assert set(STRINGS['fa']) == set(STRINGS['en']) == set(STRINGS['tr']), \
        "STRINGS language key sets differ"
    _bot = bot
    _conn = conn
    _ADMIN = admin_id
    _CHANNEL = channel_id
    _lang = lang
    _migrate()
    _seed_config()
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
            leg         INTEGER DEFAULT 0,
            fee_paid    INTEGER DEFAULT 0,
            status      TEXT DEFAULT 'offered',
            offered_at  INTEGER,
            departed_at INTEGER,
            next_eta    INTEGER,
            offer_chat_id INTEGER, offer_msg_id INTEGER,
            track_chat_id INTEGER, track_msg_id INTEGER
        )''')
        _conn.execute('''CREATE TABLE IF NOT EXISTS trade_config (
            key TEXT PRIMARY KEY, value INTEGER NOT NULL)''')
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
    return SEA_NODES if mode == 'sea' else LAND_NODES


def _node(mode, nid):
    return _nodes(mode)[nid]


def _node_name(mode, nid):
    return _node(mode, nid)['names'][_lang]


def _mode_name(mode):
    return _t('mode_sea' if mode == 'sea' else 'mode_land')


def _mode_emoji(mode):
    return '🚢' if mode == 'sea' else '🐫'


def _toll(nid):
    key = 'toll_' + nid
    return cfg(key) if key in CONFIG_DEFAULTS else 0


def _adj(mode):
    if mode not in _adj_cache:
        adj = {n: [] for n in _nodes(mode)}
        for a, b, w in (SEA_EDGES if mode == 'sea' else LAND_EDGES):
            adj[a].append((b, w))
            adj[b].append((a, w))
        _adj_cache[mode] = adj
    return _adj_cache[mode]


def _edge_w(mode):
    if mode not in _edge_w_cache:
        _edge_w_cache[mode] = {frozenset((a, b)): w
                               for a, b, w in (SEA_EDGES if mode == 'sea' else LAND_EDGES)}
    return _edge_w_cache[mode]


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


def _route_info(mode, path, label, local=False):
    mpu = cfg('sea_min_per_unit' if mode == 'sea' else 'land_min_per_unit')
    if local:
        leg_units = [1]
    else:
        w = _edge_w(mode)
        leg_units = [w[frozenset((path[i], path[i + 1]))] for i in range(len(path) - 1)]
    units = sum(leg_units)
    leg_minutes = [u * mpu for u in leg_units]
    tolls = [(nid, _toll(nid)) for nid in path if _toll(nid) > 0]
    base_fee = units * cfg('fee_per_unit')
    toll_total = sum(a for _, a in tolls)
    return {
        'label': label, 'path': path, 'units': units,
        'minutes': sum(leg_minutes), 'leg_minutes': leg_minutes,
        'base_fee': base_fee, 'tolls': tolls, 'toll_total': toll_total,
        'money': base_fee + toll_total,
    }


def find_routes(mode, src, dst):
    """Up to 3 deduplicated route options between two home nodes."""
    if src == dst:
        return [_route_info(mode, [src, src], 'route_fast', local=True)]
    adj = _adj(mode)
    fee = cfg('fee_per_unit')
    tolled = frozenset(n for n in _nodes(mode) if _toll(n) > 0)
    candidates = []
    r = _dijkstra(adj, src, dst)
    if r:
        candidates.append((r[1], 'route_fast'))
    r = _dijkstra(adj, src, dst, blocked=tolled)
    if r:
        candidates.append((r[1], 'route_free'))
    # money cost dominates, travel units break ties (units are far below 1000)
    r = _dijkstra(adj, src, dst, cost_fn=lambda u, v, w: (w * fee + _toll(v)) * 1000 + w)
    if r:
        candidates.append((r[1], 'route_cheap'))
    out, seen = [], set()
    for path, label in candidates:
        key = tuple(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(_route_info(mode, path, label))
    return out


def _path_names(mode, path):
    if len(path) == 2 and path[0] == path[1]:
        return _node_name(mode, path[0])
    return ' → '.join(_node_name(mode, nid) for nid in path)


# ---------------------------------------------------------------------------
# Economy: escrow / refund / credit (columns come only from internal whitelists)
# ---------------------------------------------------------------------------


def _escrow(group_id, goods, vehicles, fee):
    """Atomically verify and deduct goods + vehicles + fee. False if short."""
    need = dict(goods)
    need['money'] = need.get('money', 0) + fee
    for col, n in vehicles.items():
        if col != 'caravans' and n:
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
    amounts = {c: n for c, n in amounts.items() if c != 'caravans' and n}
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
        if col != 'caravans' and n:
            back[col] = back.get(col, 0) + n
    _give(trade['sender_group_id'], back)


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
        elif op == 'cfg':
            _config_menu(call, int(parts[2]))
        elif op == 'ck':
            _ask_cfg(call, parts[2])
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
    markup.add(types.InlineKeyboardButton(_t('btn_sea'), callback_data='trd:m:sea'),
               types.InlineKeyboardButton(_t('btn_land'), callback_data='trd:m:land'))
    _bot.send_message(chat_id, text, reply_markup=markup)
    _answer(call)


def _choose_mode(call, mode):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    if not _is_lord(chat_id, user_id):
        _answer(call, _t('not_lord'), alert=True)
        return
    home_col = 'home_sea' if mode == 'sea' else 'home_land'
    lord = _lord_row(chat_id)
    if lord is None or not lord[home_col]:
        _answer(call)
        _bot.send_message(chat_id, _t('need_home', mode=_mode_name(mode)))
        return
    dests = _q(f"SELECT DISTINCT group_id FROM users WHERE group_id != ? AND {home_col} != ''",
               (chat_id,))
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
    return '\n'.join(f"• {RES_NAMES[_lang][col]}: {amt}" for col, amt in goods.items())


def _send_goods_menu(user_id):
    c = _ctx.get(user_id)
    if not c:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for code, col in RESOURCES:
        amt = c['goods'].get(col, 0)
        label = RES_NAMES[_lang][col] + (f" ({amt})" if amt else "")
        buttons.append(types.InlineKeyboardButton(label, callback_data=f'trd:g:{code}'))
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
    col = RES_BY_CODE.get(code)
    if not col:
        _answer(call, _t('err_generic'))
        return
    user_id = call.from_user.id
    bal = _balance(c['chat_id'], col)
    _answer(call)
    _bot.send_message(c['chat_id'], _t('ask_amount', res=RES_NAMES[_lang][col], bal=bal))

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
    if c['mode'] == 'sea':
        return sum(c['vehicles'].get(col, 0) * cfg(cap_key) for _, col, cap_key in SHIPS)
    return c['vehicles'].get('caravans', 0) * cfg('cap_caravan')


def _veh_lines(vehicles):
    lines = [f"• {VEH_NAMES[_lang][col]}: {n}" for col, n in vehicles.items() if n]
    return '\n'.join(lines) if lines else '—'


def _send_vehicles_menu(user_id):
    c = _ctx.get(user_id)
    if not c:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    vol = sum(c['goods'].values())
    cap = _fleet_capacity(c)
    if c['mode'] == 'sea':
        buttons = []
        for code, col, _cap in SHIPS:
            n = c['vehicles'].get(col, 0)
            label = VEH_NAMES[_lang][col] + (f" ({n})" if n else "")
            buttons.append(types.InlineKeyboardButton(label, callback_data=f'trd:v:{code}'))
        markup.add(*buttons)
        text = _t('veh_title_sea', lines=_veh_lines(c['vehicles']), vol=vol, cap=cap)
    else:
        n = c['vehicles'].get('caravans', 0)
        label = VEH_NAMES[_lang]['caravans'] + (f" ({n})" if n else "")
        markup.add(types.InlineKeyboardButton(label, callback_data='trd:v:c'))
        text = _t('veh_title_land', lines=_veh_lines(c['vehicles']), vol=vol, cap=cap,
                  c=cfg('cap_caravan'), p=cfg('caravan_cost'))
    markup.add(types.InlineKeyboardButton(_t('btn_veh_done'), callback_data='trd:vok'),
               types.InlineKeyboardButton(_t('btn_cancel'), callback_data='trd:x'))
    _bot.send_message(c['chat_id'], text, reply_markup=markup, parse_mode='HTML')


def _ask_vcount(call, code):
    c = _get_ctx(call)
    if not c:
        return
    user_id = call.from_user.id
    _answer(call)
    if code == 'c':
        col = 'caravans'
        _bot.send_message(c['chat_id'], _t('ask_caravans', p=cfg('caravan_cost')))
    else:
        col = SHIP_BY_CODE.get(code)
        if not col:
            _answer(call, _t('err_generic'))
            return
        bal = _balance(c['chat_id'], col)
        _bot.send_message(c['chat_id'],
                          _t('ask_vcount', v=VEH_NAMES[_lang][col], bal=bal))

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
        elif col != 'caravans' and val > _balance(cc['chat_id'], col):
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
    routes = find_routes(mode, src_row[home_col], dst_row[home_col])
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
    veh = ', '.join(f"{n}× {VEH_NAMES[_lang][col]}" for col, n in c['vehicles'].items() if n)
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
    if not _escrow(c['chat_id'], c['goods'], c['vehicles'], fee):
        _answer(call)
        _bot.send_message(c['chat_id'], _t('insufficient'))
        return
    now = int(time.time())
    cur = _exec(
        """INSERT INTO trades (sender_group_id, sender_user_id, receiver_group_id,
                               receiver_user_id, mode, goods, vehicles, route,
                               leg_minutes, fee_paid, status, offered_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'offered', ?)""",
        (c['chat_id'], user_id, c['dest'], receiver['user_id'], c['mode'],
         json.dumps(c['goods']), json.dumps(c['vehicles']), json.dumps(r['path']),
         json.dumps(r['leg_minutes']), fee, now))
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
        sent = _bot.send_message(c['dest'], offer_text, reply_markup=markup, parse_mode='HTML')
    except Exception:
        _refund(trade)
        _exec("UPDATE trades SET status='cancelled' WHERE id=?", (tid,))
        _answer(call)
        _bot.send_message(c['chat_id'], _t('send_failed'))
        _ctx.pop(user_id, None)
        return
    _exec("UPDATE trades SET offer_chat_id=?, offer_msg_id=? WHERE id=?",
          (sent.chat.id, sent.message_id, tid))

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
        sent = _bot.send_message(trade['sender_group_id'], _track_text(trade),
                                 parse_mode='HTML')
        _exec("UPDATE trades SET track_chat_id=?, track_msg_id=? WHERE id=?",
              (sent.chat.id, sent.message_id, tid))
    except Exception:
        pass
    # channel announcement
    route = json.loads(trade['route'])
    try:
        _bot.send_message(_CHANNEL,
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
            parts.append(_t('track_choke', cur=_node_name(mode, cur_nid)))
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
        _bot.edit_message_text(text, trade['track_chat_id'], trade['track_msg_id'],
                               parse_mode='HTML')
    except Exception:
        # tracking message gone (deleted?) -> try a fresh one
        try:
            sent = _bot.send_message(trade['track_chat_id'], text, parse_mode='HTML')
            _exec("UPDATE trades SET track_msg_id=? WHERE id=?",
                  (sent.message_id, trade['id']))
        except Exception:
            pass


def _arrive(trade):
    with _lock:
        cur = _get_trade(trade['id'])
        if not cur or cur['status'] != 'active':
            return
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
        _bot.send_message(_CHANNEL,
                          _t('arrive_channel', emoji=_mode_emoji(trade['mode']),
                             src_g=_esc(_title(trade['sender_group_id'])),
                             dst_g=_esc(_title(trade['receiver_group_id']))),
                          parse_mode='HTML')
    except Exception:
        pass


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
        leg = trade['leg']
        eta = trade['next_eta']
        arrived = False
        while eta <= now:
            leg += 1
            if leg >= len(route) - 1:
                arrived = True
                break
            eta += legs[leg] * 60
        if arrived:
            _arrive(trade)
        else:
            _exec("UPDATE trades SET leg=?, next_eta=? WHERE id=? AND status='active'",
                  (leg, eta, trade['id']))
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
    if call.from_user.id != _ADMIN:
        _answer(call, _t('admin_only'), alert=True)
        return False
    return True


def _admin_menu(call):
    if not _require_admin(call):
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(_t('btn_home_sea'), callback_data='trd:hm:s'),
               types.InlineKeyboardButton(_t('btn_home_land'), callback_data='trd:hm:l'),
               types.InlineKeyboardButton(_t('btn_cfg'), callback_data='trd:cfg:0'))
    _bot.send_message(call.message.chat.id, _t('adm_title'), reply_markup=markup)
    _answer(call)


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
    _answer(call)
    _bot.send_message(call.message.chat.id,
                      _t('home_set', mode=_mode_name(mode), g=_esc(_title(gid)),
                         node=_node_name(mode, nid)),
                      parse_mode='HTML')


CFG_PAGE_SIZE = 10


def _config_menu(call, page):
    if not _require_admin(call):
        return
    keys = list(CONFIG_DEFAULTS)
    pages = (len(keys) + CFG_PAGE_SIZE - 1) // CFG_PAGE_SIZE
    page = max(0, min(page, pages - 1))
    markup = types.InlineKeyboardMarkup(row_width=1)
    for k in keys[page * CFG_PAGE_SIZE:(page + 1) * CFG_PAGE_SIZE]:
        markup.add(types.InlineKeyboardButton(f"{k} = {cfg(k)}", callback_data=f'trd:ck:{k}'))
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(_t('btn_prev'), callback_data=f'trd:cfg:{page - 1}'))
    if page < pages - 1:
        nav.append(types.InlineKeyboardButton(_t('btn_next'), callback_data=f'trd:cfg:{page + 1}'))
    if nav:
        markup.add(*nav)
    _bot.send_message(call.message.chat.id, _t('cfg_title', p=page + 1), reply_markup=markup)
    _answer(call)


def _ask_cfg(call, key):
    if not _require_admin(call):
        return
    if key not in CONFIG_DEFAULTS:
        _answer(call, _t('err_generic'))
        return
    chat_id = call.message.chat.id
    _answer(call)
    _bot.send_message(chat_id, _t('cfg_ask', key=key, val=cfg(key)))

    def on_value(msg):
        try:
            val = int(msg.text.strip())
            if val < 0:
                raise ValueError
        except (ValueError, AttributeError):
            _bot.send_message(chat_id, _t('bad_number'))
            return
        set_cfg(key, val)
        _bot.send_message(chat_id, _t('cfg_set', key=key, val=val))

    _next_step(call.message, _ADMIN, on_value)
