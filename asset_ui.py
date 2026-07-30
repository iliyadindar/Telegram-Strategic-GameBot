# -*- coding: utf-8 -*-
"""Player-facing asset screens, driven entirely by the asset catalog.

Assets, upgrades, the weekly production cycle and the admin asset editor used
to be ~300 lines of if/elif in each of main.py, main-en.py and main-tr.py, with
the cost of every building written out twice — once to test affordability and
once to deduct. The two lists disagreed for five buildings, so an upgrade could
be approved against one resource and paid for with another.

Now there is one implementation and one cost table (asset_upgrade_costs), and
whatever an admin adds to the catalog shows up here without a code change.

main*.py calls init(bot, conn, lang=...) and routes 'ag:' callbacks to
handle_callback().
"""

import html
import threading

from telebot import types

import asset_catalog as catalog

_bot = None
_conn = None
_lang = 'fa'
_audit = None
_is_admin = None
_lock = threading.RLock()

PAGE_SIZE = 10

STRINGS = {
    'fa': {
        'err_generic': "خطایی رخ داد. دوباره تلاش کنید.",
        'not_registered': "این گروه هنوز لردی ندارد. یک ادمین باید روی پیام بازیکن "
                          "ریپلای کند و /setlord بزند.",
        'not_admin': "شما ادمین نیستید.",
        'btn_back': "🔙 بازگشت",
        'assets_title': "💰 دارایی:\n<blockquote>{resources}</blockquote>\n\n"
                        "⚔️ ارتش:\n<blockquote>{units}</blockquote>\n\n"
                        "🏭 ساختمان‌ها:\n<blockquote>{buildings}</blockquote>\n\n"
                        "📜 معاهدات:\n<blockquote>{treaties}</blockquote>",
        'nothing': "ندارد",
        'upgrade_pick': "انتخاب کنید که کدام بخش را می‌خواهید ارتقا دهید:",
        'upgrade_confirm': "برای ارتقا {label} به این مقادیر نیاز دارید:\n<blockquote>{costs}</blockquote>",
        'upgrade_free': "ارتقا {label} هزینه‌ای ندارد.",
        'btn_upgrade_yes': "✅ بله، ارتقا بده",
        'upgraded': "✅ {label} ارتقا یافت (سطح {level}).",
        'insufficient': "💸 موجودی شما کافی نیست.",
        'weekly_title': "🏭 محصولات جمع‌آوری شده:\n<blockquote>{lines}</blockquote>",
        'weekly_empty': "🏭 هیچ ساختمانی برای تولید ندارید.",
        'editor_pick_kind': "کدام دسته را می‌خواهید تغییر دهید؟",
        'editor_pick_asset': "انتخاب کنید که کدام مورد را می‌خواهید تغییر دهید:",
        'editor_ask_value': "مقدار جدید برای {label} را وارد کنید (فعلی: {current}):",
        'editor_set': "✅ {label} به {value} تغییر یافت.",
        'editor_bad_number': "مقدار وارد شده معتبر نیست. لطفا یک عدد وارد کنید.",
        'editor_invalid': "دارایی نامعتبر است.",
        'kind_resource': "📦 منابع",
        'kind_unit': "⚔️ واحدها",
        'kind_building': "🏭 ساختمان‌ها",
    },
    'en': {
        'err_generic': "Something went wrong. Please try again.",
        'not_registered': "This group has no lord yet. An admin has to reply to the "
                          "player's message with /setlord.",
        'not_admin': "You are not an admin.",
        'btn_back': "🔙 Back",
        'assets_title': "💰 Resources:\n<blockquote>{resources}</blockquote>\n\n"
                        "⚔️ Army:\n<blockquote>{units}</blockquote>\n\n"
                        "🏭 Buildings:\n<blockquote>{buildings}</blockquote>\n\n"
                        "📜 Treaties:\n<blockquote>{treaties}</blockquote>",
        'nothing': "none",
        'upgrade_pick': "Choose what you want to upgrade:",
        'upgrade_confirm': "Upgrading {label} costs:\n<blockquote>{costs}</blockquote>",
        'upgrade_free': "Upgrading {label} is free.",
        'btn_upgrade_yes': "✅ Yes, upgrade it",
        'upgraded': "✅ {label} was upgraded (level {level}).",
        'insufficient': "💸 You do not have enough for that.",
        'weekly_title': "🏭 Collected output:\n<blockquote>{lines}</blockquote>",
        'weekly_empty': "🏭 You have no buildings producing anything.",
        'editor_pick_kind': "Which category do you want to change?",
        'editor_pick_asset': "Choose which entry you want to change:",
        'editor_ask_value': "Enter the new value for {label} (currently {current}):",
        'editor_set': "✅ {label} changed to {value}.",
        'editor_bad_number': "That is not a valid number. Please enter an integer.",
        'editor_invalid': "Invalid asset.",
        'kind_resource': "📦 Resources",
        'kind_unit': "⚔️ Units",
        'kind_building': "🏭 Buildings",
    },
    'tr': {
        'err_generic': "Bir hata oluştu. Lütfen tekrar deneyin.",
        'not_registered': "Bu grubun henüz bir lordu yok. Bir yöneticinin oyuncunun "
                          "mesajını yanıtlayıp /setlord göndermesi gerekir.",
        'not_admin': "Yönetici değilsiniz.",
        'btn_back': "🔙 Geri",
        'assets_title': "💰 Kaynaklar:\n<blockquote>{resources}</blockquote>\n\n"
                        "⚔️ Ordu:\n<blockquote>{units}</blockquote>\n\n"
                        "🏭 Binalar:\n<blockquote>{buildings}</blockquote>\n\n"
                        "📜 Antlaşmalar:\n<blockquote>{treaties}</blockquote>",
        'nothing': "yok",
        'upgrade_pick': "Neyi yükseltmek istediğinizi seçin:",
        'upgrade_confirm': "{label} yükseltmesi şunlara mal olur:\n<blockquote>{costs}</blockquote>",
        'upgrade_free': "{label} yükseltmesi ücretsiz.",
        'btn_upgrade_yes': "✅ Evet, yükselt",
        'upgraded': "✅ {label} yükseltildi (seviye {level}).",
        'insufficient': "💸 Bunun için yeterli kaynağınız yok.",
        'weekly_title': "🏭 Toplanan üretim:\n<blockquote>{lines}</blockquote>",
        'weekly_empty': "🏭 Üretim yapan bir binanız yok.",
        'editor_pick_kind': "Hangi kategoriyi değiştirmek istiyorsunuz?",
        'editor_pick_asset': "Hangi girdiyi değiştirmek istediğinizi seçin:",
        'editor_ask_value': "{label} için yeni değeri girin (şu an {current}):",
        'editor_set': "✅ {label} {value} olarak değiştirildi.",
        'editor_bad_number': "Girilen değer geçersiz. Lütfen bir sayı girin.",
        'editor_invalid': "Geçersiz varlık.",
        'kind_resource': "📦 Kaynaklar",
        'kind_unit': "⚔️ Birimler",
        'kind_building': "🏭 Binalar",
    },
}

PREFIX = 'ag:'


def init(bot, conn, lang='fa', audit=None, is_admin=None):
    global _bot, _conn, _lang, _audit, _is_admin
    assert lang in STRINGS, f"unsupported lang: {lang}"
    assert set(STRINGS['fa']) == set(STRINGS['en']) == set(STRINGS['tr']), \
        "STRINGS language key sets differ"
    _bot = bot
    _conn = conn
    _lang = lang
    _audit = audit
    _is_admin = is_admin


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _t(string_id, **kw):
    text = STRINGS[_lang][string_id]
    return text.format(**kw) if kw else text


def _esc(text):
    return html.escape(str(text), quote=False)


def _label(key):
    return catalog.label(key, _lang)


def _answer(call, text=None, alert=False):
    try:
        _bot.answer_callback_query(call.id, text, show_alert=alert)
    except Exception:
        pass


def _row(group_id, columns):
    if not columns:
        return None
    with _lock:
        cur = _conn.execute(f"SELECT {', '.join(columns)} FROM users WHERE group_id=?",
                            (group_id,))
        found = cur.fetchone()
    return dict(zip(columns, found)) if found else None


def _log(actor_id, action, target='', detail=''):
    if _audit is None:
        return
    try:
        _audit(actor_id, action, target, detail)
    except Exception:
        pass


def _lines(values):
    if not values:
        return _t('nothing')
    return '\n'.join(f"{_label(key)}: {value}" for key, value in values.items())


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------


def show_assets(chat_id, group_id):
    columns = catalog.all_keys()
    values = _row(group_id, list(columns) + ['treaties'])
    if values is None:
        _bot.send_message(chat_id, _t('not_registered'))
        return
    text = _t('assets_title',
              resources=_lines({k: values[k] for k in catalog.keys('resource')}),
              units=_lines({k: values[k] for k in catalog.keys('unit')}),
              buildings=_lines({k: values[k] for k in catalog.keys('building')}),
              treaties=_esc(values['treaties']) or _t('nothing'))
    _bot.send_message(chat_id, text, parse_mode='HTML')


# ---------------------------------------------------------------------------
# Upgrades
# ---------------------------------------------------------------------------


def upgrade_menu(chat_id):
    buildings = catalog.keys('building')
    if not buildings:
        _bot.send_message(chat_id, _t('err_generic'))
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*[types.InlineKeyboardButton(_label(key), callback_data=f'ag:upc:{key}')
                 for key in buildings])
    _bot.send_message(chat_id, _t('upgrade_pick'), reply_markup=markup)


def _confirm_upgrade(call, key):
    row = catalog.entry(key)
    if row is None or row['kind'] != 'building' or row['hidden']:
        _answer(call, _t('err_generic'), alert=True)
        return
    costs = catalog.upgrade_cost(key)
    if costs:
        text = _t('upgrade_confirm', label=_label(key),
                  costs='\n'.join(f"{_label(res)}: {amount}" for res, amount in costs.items()))
    else:
        text = _t('upgrade_free', label=_label(key))
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(_t('btn_upgrade_yes'), callback_data=f'ag:upy:{key}'))
    _answer(call)
    _bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='HTML')


def _do_upgrade(call, key):
    row = catalog.entry(key)
    if row is None or row['kind'] != 'building' or row['hidden']:
        _answer(call, _t('err_generic'), alert=True)
        return
    group_id = call.message.chat.id
    level = _charge_and_upgrade(group_id, key)
    _answer(call)
    if level is None:
        _bot.send_message(group_id, _t('insufficient'))
        return
    _bot.send_message(group_id, _t('upgraded', label=_label(key), level=level),
                      parse_mode='HTML')


def _charge_and_upgrade(group_id, key):
    """Check, deduct and increment in one transaction. New level, or None."""
    costs = catalog.upgrade_cost(key)
    cols = list(costs)
    with _lock:
        cur = _conn.execute(f"SELECT {', '.join(cols + [key])} FROM users WHERE group_id=?",
                            (group_id,))
        found = cur.fetchone()
        if found is None:
            return None
        if any(found[i] < costs[c] for i, c in enumerate(cols)):
            return None
        sets = [f"{c} = {c} - ?" for c in cols] + [f"{key} = {key} + 1"]
        _conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE group_id=?",
                      [costs[c] for c in cols] + [group_id])
        _conn.commit()
    return found[len(cols)] + 1


# ---------------------------------------------------------------------------
# Weekly production
# ---------------------------------------------------------------------------


def weekly_update(chat_id, group_id):
    """Credit every building's output. Two buildings feeding one type stack."""
    plan = catalog.production()
    if not plan:
        _bot.send_message(chat_id, _t('weekly_empty'))
        return
    levels = _row(group_id, [building for building, _, _ in plan])
    if levels is None:
        _bot.send_message(chat_id, _t('not_registered'))
        return

    gains = {}
    for building, produces, output in plan:
        amount = levels[building] * output
        if amount:
            gains[produces] = gains.get(produces, 0) + amount
    if not gains:
        _bot.send_message(chat_id, _t('weekly_empty'))
        return

    cols = list(gains)
    sets = ', '.join(f"{c} = {c} + ?" for c in cols)
    with _lock:
        _conn.execute(f"UPDATE users SET {sets} WHERE group_id=?",
                      [gains[c] for c in cols] + [group_id])
        _conn.commit()
    _bot.send_message(chat_id, _t('weekly_title', lines=_lines(gains)), parse_mode='HTML')


# ---------------------------------------------------------------------------
# Admin asset editor
# ---------------------------------------------------------------------------


def editor_menu(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(*[types.InlineKeyboardButton(_t('kind_' + kind), callback_data=f'ag:edk:{kind}')
                 for kind in catalog.KINDS])
    _bot.send_message(chat_id, _t('editor_pick_kind'), reply_markup=markup)


def _editor_list(call, kind):
    if kind not in catalog.KINDS:
        _answer(call, _t('err_generic'), alert=True)
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*[types.InlineKeyboardButton(_label(key), callback_data=f'ag:eda:{key}')
                 for key in catalog.keys(kind)])
    _answer(call)
    _bot.send_message(call.message.chat.id, _t('editor_pick_asset'), reply_markup=markup)


def _editor_ask(call, key):
    if key not in catalog.all_keys():
        _answer(call, _t('editor_invalid'), alert=True)
        return
    group_id = call.message.chat.id
    current = _row(group_id, [key])
    if current is None:
        _answer(call, _t('not_registered'), alert=True)
        return
    actor_id = call.from_user.id
    _answer(call)
    _bot.send_message(group_id, _t('editor_ask_value', label=_label(key),
                                   current=current[key]))

    def on_value(message):
        if message.from_user is None or message.from_user.id != actor_id:
            _bot.register_next_step_handler(message, on_value)
            return
        try:
            value = int((message.text or '').strip())
        except ValueError:
            _bot.send_message(message.chat.id, _t('editor_bad_number'))
            return
        if key not in catalog.all_keys():          # re-check: it may have been removed
            _bot.send_message(message.chat.id, _t('editor_invalid'))
            return
        with _lock:
            _conn.execute(f"UPDATE users SET {key} = ? WHERE group_id = ?", (value, group_id))
            _conn.commit()
        _log(actor_id, 'asset_edit', message.chat.title or group_id, f'{key}={value}')
        _bot.send_message(message.chat.id, _t('editor_set', label=_label(key), value=value))

    _bot.register_next_step_handler(call.message, on_value)


# ---------------------------------------------------------------------------
# Callback entry point
# ---------------------------------------------------------------------------


def handle_callback(call):
    """Dispatch 'ag:' callbacks. Admin-only screens re-check the caller."""
    parts = call.data.split(':')
    op = parts[1] if len(parts) > 1 else ''
    admin_only = op in ('ed', 'edk', 'eda')
    if admin_only and not (_is_admin and _is_admin(call.from_user.id)):
        _answer(call, _t('not_admin'), alert=True)
        return
    if op == 'up':
        _answer(call)
        upgrade_menu(call.message.chat.id)
    elif op == 'upc':
        _confirm_upgrade(call, parts[2])
    elif op == 'upy':
        _do_upgrade(call, parts[2])
    elif op == 'ed':
        _answer(call)
        editor_menu(call.message.chat.id)
    elif op == 'edk':
        _editor_list(call, parts[2])
    elif op == 'eda':
        _editor_ask(call, parts[2])
    else:
        _answer(call, _t('err_generic'))
