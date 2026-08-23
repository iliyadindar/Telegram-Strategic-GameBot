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
import country_assets

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
        # {sections} is one "header + <blockquote>" block per kind, joined in
        # the order asset_catalog.kind_order() gives.
        'assets_title': "{sections}\n\n📜 معاهدات:\n<blockquote>{treaties}</blockquote>",
        'sec_resource': "💰 دارایی:",
        'sec_unit': "⚔️ ارتش:",
        'sec_building': "🏭 ساختمان‌ها:",
        'nothing': "ندارد",
        'upgrade_pick': "انتخاب کنید که کدام بخش را می‌خواهید ارتقا دهید:\n(داخل پرانتز سطح فعلی و سقف آن آمده است)",
        'upgrade_confirm': "برای ارتقا {label} به سطح {level} به این مقادیر نیاز دارید:\n<blockquote>{costs}</blockquote>{cap}",
        'upgrade_free': "ارتقا {label} به سطح {level} هزینه‌ای ندارد.{cap}",
        'upgrade_cap_note': "\n🏁 سقف سطح این ساختمان: {max}",
        'upgrade_maxed': "🏁 {label} به سقف سطح خود ({max}) رسیده و بیشتر ارتقا نمی‌یابد.",
        'lvl_uncapped': "بدون سقف",
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
        # {sections} is one "header + <blockquote>" block per kind, joined in
        # the order asset_catalog.kind_order() gives.
        'assets_title': "{sections}\n\n📜 Treaties:\n<blockquote>{treaties}</blockquote>",
        'sec_resource': "💰 Resources:",
        'sec_unit': "⚔️ Army:",
        'sec_building': "🏭 Buildings:",
        'nothing': "none",
        'upgrade_pick': "Choose what you want to upgrade:\n(the brackets show the current level and its ceiling)",
        'upgrade_confirm': "Upgrading {label} to level {level} costs:\n<blockquote>{costs}</blockquote>{cap}",
        'upgrade_free': "Upgrading {label} to level {level} is free.{cap}",
        'upgrade_cap_note': "\n🏁 Level ceiling for this building: {max}",
        'upgrade_maxed': "🏁 {label} has reached its ceiling ({max}) and cannot go higher.",
        'lvl_uncapped': "no ceiling",
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
        # {sections} is one "header + <blockquote>" block per kind, joined in
        # the order asset_catalog.kind_order() gives.
        'assets_title': "{sections}\n\n📜 Antlaşmalar:\n<blockquote>{treaties}</blockquote>",
        'sec_resource': "💰 Kaynaklar:",
        'sec_unit': "⚔️ Ordu:",
        'sec_building': "🏭 Binalar:",
        'nothing': "yok",
        'upgrade_pick': "Neyi yükseltmek istediğinizi seçin:\n(parantez içinde mevcut seviye ve tavanı yazar)",
        'upgrade_confirm': "{label} seviye {level} yükseltmesi şunlara mal olur:\n<blockquote>{costs}</blockquote>{cap}",
        'upgrade_free': "{label} seviye {level} yükseltmesi ücretsiz.{cap}",
        'upgrade_cap_note': "\n🏁 Bu binanın seviye tavanı: {max}",
        'upgrade_maxed': "🏁 {label} tavanına ({max}) ulaştı, daha fazla yükseltilemez.",
        'lvl_uncapped': "tavan yok",
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
    # These screens honour what a country does and does not have, so the
    # override table has to be reachable whether or not the panel is wired.
    country_assets.attach(conn)


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


def sections(values, joiner='\n\n', group_id=None):
    """One "header + quoted list" block per kind, in the admin's chosen order.

    With a group_id, the types an admin has taken away from that country are
    left out — a landlocked nation should not be shown a fleet of zero ships.
    """
    def keys(kind):
        return (country_assets.keys_for(group_id, kind) if group_id is not None
                else catalog.keys(kind))
    return joiner.join(
        "{}\n<blockquote>{}</blockquote>".format(
            _t('sec_' + kind), _lines({k: values[k] for k in keys(kind) if k in values}))
        for kind in catalog.kind_order())


def show_assets(chat_id, group_id):
    columns = catalog.all_keys()
    values = _row(group_id, list(columns) + ['treaties'])
    if values is None:
        _bot.send_message(chat_id, _t('not_registered'))
        return
    text = _t('assets_title',
              sections=sections(values, group_id=group_id),
              treaties=_esc(values['treaties']) or _t('nothing'))
    _bot.send_message(chat_id, text, parse_mode='HTML')


# ---------------------------------------------------------------------------
# Upgrades
# ---------------------------------------------------------------------------


# Why an upgrade did not happen. _charge_and_upgrade() returns the new level as
# an int, or one of these, so "you are broke" and "this is as high as it goes"
# can be told apart in the reply.
MAXED = 'maxed'
INSUFFICIENT = 'insufficient'
NO_COUNTRY = 'no_country'


def _cap_note(key):
    """The "ceiling is N" line, or nothing at all when the building is uncapped."""
    cap = catalog.max_level(key)
    return _t('upgrade_cap_note', max=cap) if cap else ''


def _level_suffix(key, level):
    """The "(3/20)" a picker button carries, so the ceiling is visible up front."""
    cap = catalog.max_level(key)
    return f" ({level}/{cap})" if cap else f" ({level})"


def upgrade_menu(chat_id, group_id=None):
    group_id = chat_id if group_id is None else group_id
    buildings = country_assets.keys_for(group_id, 'building')
    if not buildings:
        _bot.send_message(chat_id, _t('err_generic'))
        return
    levels = _row(group_id, list(buildings)) or {}
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*[types.InlineKeyboardButton(
        _label(key) + _level_suffix(key, levels.get(key, 0)),
        callback_data=f'ag:upc:{key}') for key in buildings])
    _bot.send_message(chat_id, _t('upgrade_pick'), reply_markup=markup)


def _confirm_upgrade(call, key):
    row = catalog.entry(key)
    if row is None or row['kind'] != 'building' or row['hidden']:
        _answer(call, _t('err_generic'), alert=True)
        return
    group_id = call.message.chat.id
    if country_assets.is_hidden(group_id, key):
        _answer(call, _t('err_generic'), alert=True)
        return
    current = _row(group_id, [key])
    if current is None:
        _answer(call, _t('not_registered'), alert=True)
        return
    level = current[key]
    if catalog.at_max_level(key, level):
        _answer(call)
        _bot.send_message(group_id, _t('upgrade_maxed', label=_label(key),
                                       max=catalog.max_level(key)))
        return
    # The price quoted is the price of the level about to be bought, which is
    # the flat one unless an admin has tuned that particular level.
    target = level + 1
    costs = catalog.upgrade_cost(key, target)
    if costs:
        text = _t('upgrade_confirm', label=_label(key), level=target, cap=_cap_note(key),
                  costs='\n'.join(f"{_label(res)}: {amount}" for res, amount in costs.items()))
    else:
        text = _t('upgrade_free', label=_label(key), level=target, cap=_cap_note(key))
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(_t('btn_upgrade_yes'), callback_data=f'ag:upy:{key}'))
    _answer(call)
    _bot.send_message(group_id, text, reply_markup=markup, parse_mode='HTML')


def _do_upgrade(call, key):
    row = catalog.entry(key)
    if row is None or row['kind'] != 'building' or row['hidden']:
        _answer(call, _t('err_generic'), alert=True)
        return
    group_id = call.message.chat.id
    if country_assets.is_hidden(group_id, key):
        _answer(call, _t('err_generic'), alert=True)
        return
    result = _charge_and_upgrade(group_id, key)
    _answer(call)
    if result == MAXED:
        _bot.send_message(group_id, _t('upgrade_maxed', label=_label(key),
                                       max=catalog.max_level(key)))
        return
    if not isinstance(result, int):
        _bot.send_message(group_id, _t('insufficient'))
        return
    _bot.send_message(group_id, _t('upgraded', label=_label(key), level=result),
                      parse_mode='HTML')


def _charge_and_upgrade(group_id, key):
    """Check the ceiling, check the price, deduct and increment atomically.

    The level is read inside the lock and the price is looked up from it, so two
    taps racing each other cannot both buy level 7 at level 7's price.
    Returns the new level, or MAXED / INSUFFICIENT / NO_COUNTRY.
    """
    with _lock:
        found = _conn.execute(f"SELECT {key} FROM users WHERE group_id=?",
                              (group_id,)).fetchone()
        if found is None:
            return NO_COUNTRY
        level = found[0] or 0
        if catalog.at_max_level(key, level):
            return MAXED
        target = level + 1
        costs = catalog.upgrade_cost(key, target)
        cols = list(costs)
        if cols:
            have = _conn.execute(f"SELECT {', '.join(cols)} FROM users WHERE group_id=?",
                                 (group_id,)).fetchone()
            if have is None:
                return NO_COUNTRY
            if any(have[i] < costs[c] for i, c in enumerate(cols)):
                return INSUFFICIENT
        sets = [f"{c} = {c} - ?" for c in cols] + [f"{key} = {key} + 1"]
        _conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE group_id=?",
                      [costs[c] for c in cols] + [group_id])
        _conn.commit()
    return target


# ---------------------------------------------------------------------------
# Weekly production
# ---------------------------------------------------------------------------


def weekly_update(chat_id, group_id):
    """Credit every building's output. Two buildings feeding one type stack.

    The plan is this country's, not the game's: a building an admin removed
    here, switched off here, or whose product this country does not have,
    simply is not in it.
    """
    plan = country_assets.production_for(group_id)
    if not plan:
        _bot.send_message(chat_id, _t('weekly_empty'))
        return
    levels = _row(group_id, [building for building, _, _ in plan])
    if levels is None:
        _bot.send_message(chat_id, _t('not_registered'))
        return

    gains = {}
    for building, produces, _flat in plan:
        # Not level x output: a level an admin has tuned contributes its own
        # number instead of the flat one.
        amount = catalog.output_at_level(building, levels[building])
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
                 for kind in catalog.kind_order()])
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
