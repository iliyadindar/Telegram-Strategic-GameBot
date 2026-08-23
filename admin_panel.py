# -*- coding: utf-8 -*-
"""Inline Telegram admin dashboard.

main*.py calls init() once, then:

    * routes /admin            -> open_panel(chat_id, user_id)
    * routes /setlord          -> handle_setlord(message)
    * routes /unsetlord        -> handle_unsetlord(message)
    * routes 'ap:' callbacks   -> handle_callback(call)
    * guards every feature     -> feature_enabled() / require_feature()
    * records admin mutations  -> log()

Everything the panel writes goes through log(), so the action log is a complete
record of admin-side changes. Access is checked on every callback, not only when
the panel is opened, because a panel posted in a group is visible to everyone.
"""

import html
import json
import sqlite3
import threading
import time
import traceback

from telebot import types

import asset_admin
import asset_catalog as catalog
import country_assets
from admin_strings import FEATURES, STRINGS

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------

_bot = None
_conn = None
_OWNER = 0
_CHANNEL = None
_WAR_CHANNEL = None
_lang = 'fa'
_game_menu = None          # callback into main*.py that renders the /start menu
_lock = threading.RLock()
_title_cache = {}
_name_cache = {}
_lord_guard = None         # set by main*.py; says which groups have a live trade

PAGE_SIZE = 8
LOG_PAGE_SIZE = 10
LOG_LIMIT = 200            # newest N entries are browsable in the panel
DETAIL_PREVIEW = 120       # log detail is truncated to this in the list view


def init(bot, conn, owner_id, channel_id, war_channel_id=None, lang='fa', game_menu=None):
    """Wire the panel to a bot/db. Safe to call once per process."""
    global _bot, _conn, _OWNER, _CHANNEL, _WAR_CHANNEL, _lang, _game_menu
    assert lang in STRINGS, f"unsupported lang: {lang}"
    assert all(set(STRINGS[k]) == set(STRINGS['fa']) for k in STRINGS), \
        "STRINGS language key sets differ"
    _bot = bot
    _conn = conn
    _OWNER = int(owner_id)
    _CHANNEL = channel_id
    _WAR_CHANNEL = war_channel_id or channel_id
    _lang = lang
    _game_menu = game_menu
    _migrate()
    # Resources, units and buildings are data: seed the catalog and make sure
    # `users` has a column for every type before anything reads them.
    catalog.init(conn)
    asset_admin.init(bot, lang, _require_admin, _answer, _show, log, _next_step, _back_row,
                     require_owner=_require_owner)
    # What one country has, as opposed to what the game has. Wired after the
    # catalog, because its screens list the catalog's types.
    country_assets.init(bot, conn, lang, _require_admin, _answer, _show, log, _back_row,
                        _title, _groups)


def _migrate():
    with _lock:
        _conn.execute('''CREATE TABLE IF NOT EXISTS bot_admins (
            user_id  INTEGER PRIMARY KEY,
            added_by INTEGER,
            added_at INTEGER,
            username TEXT DEFAULT ''
        )''')
        _conn.execute('''CREATE TABLE IF NOT EXISTS bot_features (
            key     TEXT PRIMARY KEY,
            enabled INTEGER NOT NULL DEFAULT 1
        )''')
        _conn.execute('''CREATE TABLE IF NOT EXISTS admin_log (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            ts       INTEGER NOT NULL,
            actor_id INTEGER NOT NULL,
            action   TEXT NOT NULL,
            target   TEXT DEFAULT '',
            detail   TEXT DEFAULT ''
        )''')
        # What a country owned when its last lord was retired. The `users` row
        # *is* the country, so removing the lord used to destroy the assets with
        # it and the next lord started from the defaults. Now the row's numbers
        # are kept here and handed to whoever takes the country on next; the
        # reset button is what zeroes a country, deliberately.
        _conn.execute('''CREATE TABLE IF NOT EXISTS country_archive (
            group_id INTEGER PRIMARY KEY,
            saved_at INTEGER NOT NULL,
            data     TEXT NOT NULL
        )''')
        # String-valued settings. trade_config only stores integers, so the
        # photo file_ids need a home of their own.
        _conn.execute('''CREATE TABLE IF NOT EXISTS bot_settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )''')
        for key in FEATURES:
            _conn.execute("INSERT OR IGNORE INTO bot_features (key, enabled) VALUES (?, 1)", (key,))
        _conn.commit()


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _t(string_id, **kw):
    text = STRINGS[_lang][string_id]
    return text.format(**kw) if kw else text


def _esc(text):
    return html.escape(str(text), quote=False)


def _col(name):
    return catalog.label(name, _lang)


def _num(value):
    return f"{int(value or 0):,}"


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
    """Group title, cached. Falls back to the raw id when the bot can't see it."""
    if gid not in _title_cache:
        try:
            _title_cache[gid] = _bot.get_chat(gid).title or str(gid)
        except Exception:
            return str(gid)
    return _title_cache[gid]


def _user_name(uid):
    if uid not in _name_cache:
        try:
            chat = _bot.get_chat(uid)
            name = (chat.first_name or '') + (' ' + chat.last_name if chat.last_name else '')
            _name_cache[uid] = name.strip() or str(uid)
        except Exception:
            return str(uid)
    return _name_cache[uid]


def _user_link(uid):
    return f"<a href='tg://user?id={uid}'>{_esc(_user_name(uid))}</a>"


def _answer(call, text=None, alert=False):
    try:
        _bot.answer_callback_query(call.id, text, show_alert=alert)
    except Exception:
        pass


def _next_step(message, user_id, fn):
    """register_next_step_handler that ignores messages from other users."""
    def wrapper(msg):
        if msg.from_user is None or msg.from_user.id != user_id:
            _bot.register_next_step_handler(message, wrapper)
            return
        fn(msg)
    _bot.register_next_step_handler(message, wrapper)


def _show(call, text, markup=None):
    """Redraw the panel in place; fall back to a new message if the edit fails."""
    try:
        _bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                               reply_markup=markup, parse_mode='HTML')
        return
    except Exception:
        pass
    try:
        _bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='HTML')
    except Exception:
        pass


def _back_row(markup, target='ap:home'):
    markup.add(types.InlineKeyboardButton(_t('btn_back'), callback_data=target))
    return markup


def _pager(markup, page, pages, prefix):
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(_t('btn_prev'), callback_data=f'{prefix}{page - 1}'))
    if page < pages - 1:
        nav.append(types.InlineKeyboardButton(_t('btn_next'), callback_data=f'{prefix}{page + 1}'))
    if nav:
        markup.add(*nav)
    return markup


# ---------------------------------------------------------------------------
# Access control (public API)
# ---------------------------------------------------------------------------


def is_owner(user_id):
    return int(user_id) == _OWNER


def is_admin(user_id):
    if is_owner(user_id):
        return True
    return bool(_q("SELECT 1 FROM bot_admins WHERE user_id=?", (int(user_id),)))


def admin_ids():
    """Owner first, then every promoted admin."""
    ids = [_OWNER]
    ids += [r['user_id'] for r in _q("SELECT user_id FROM bot_admins ORDER BY added_at")
            if r['user_id'] != _OWNER]
    return ids


def _require_admin(call):
    if not is_admin(call.from_user.id):
        _answer(call, _t('not_admin'), alert=True)
        return False
    return True


def _require_owner(call):
    if not is_owner(call.from_user.id):
        _answer(call, _t('not_owner'), alert=True)
        return False
    return True


# ---------------------------------------------------------------------------
# Features (public API)
# ---------------------------------------------------------------------------


def feature_enabled(key):
    """Unknown keys are enabled — a typo must not silently disable a feature."""
    rows = _q("SELECT enabled FROM bot_features WHERE key=?", (key,))
    return bool(rows[0]['enabled']) if rows else True


# The master switch, above every individual feature. /off closes the game for
# players — the menu and its buttons stop working — while admins keep the panel,
# so a round can be paused and tidied up without taking the bot down.
PLAYERS_KEY = 'players_enabled'


def players_enabled():
    """False only after somebody has run /off. Absent means open."""
    return setting(PLAYERS_KEY, '1') != '0'


def set_players_enabled(value):
    set_setting(PLAYERS_KEY, '1' if value else '0')


def open_to(user_id):
    """Whether this person may use the game right now."""
    return players_enabled() or is_admin(user_id)


def closed_notice():
    """What to tell a player who opened the menu while the bot is off."""
    return _t('bot_off')


def require_feature(call, key):
    """Guard a callback branch. Answers with an alert and returns False if off."""
    if not open_to(call.from_user.id):
        _answer(call, _t('bot_off'), alert=True)
        return False
    if feature_enabled(key):
        return True
    _answer(call, _t('feature_disabled'), alert=True)
    return False


def handle_onoff(message, enable):
    """/on and /off. Admin-only, and it says so rather than staying silent."""
    if not is_admin(message.from_user.id):
        _bot.reply_to(message, _t('not_admin'))
        return
    already = players_enabled() == bool(enable)
    set_players_enabled(enable)
    if already:
        _bot.reply_to(message, _t('bot_on_already' if enable else 'bot_off_already'))
        return
    log(message.from_user.id, 'bot_switch', '', 'on' if enable else 'off')
    _bot.reply_to(message, _t('bot_turned_on' if enable else 'bot_turned_off'))


def enabled_features():
    return {key: feature_enabled(key) for key in FEATURES}


def _set_feature(key, enabled):
    _exec("INSERT OR REPLACE INTO bot_features (key, enabled) VALUES (?, ?)",
          (key, 1 if enabled else 0))


# ---------------------------------------------------------------------------
# Settings + action log (public API)
# ---------------------------------------------------------------------------


def setting(key, default=''):
    rows = _q("SELECT value FROM bot_settings WHERE key=?", (key,))
    return rows[0]['value'] if rows else default


def set_setting(key, value):
    if value is None or value == '':
        _exec("DELETE FROM bot_settings WHERE key=?", (key,))
    else:
        _exec("INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (key, str(value)))


def log(actor_id, action, target='', detail=''):
    _exec("INSERT INTO admin_log (ts, actor_id, action, target, detail) VALUES (?, ?, ?, ?, ?)",
          (int(time.time()), int(actor_id), action, str(target), str(detail)))


def recent_log(limit=LOG_LIMIT):
    return _q("SELECT * FROM admin_log ORDER BY id DESC LIMIT ?", (int(limit),))


def log_size():
    return _q("SELECT COUNT(*) AS n FROM admin_log")[0]['n']


def clear_log():
    """Empty the action log and return how many rows went.

    Deliberately leaves no entry of its own: the point of the feature is that
    the screen reads as though nothing ever happened. Callers announce the wipe
    to the admins instead, so an erasable audit trail is still not a silent one.
    """
    count = log_size()
    _exec("DELETE FROM admin_log")
    return count


def notify_admins(text, **kwargs):
    """Send a message to the owner and every promoted admin, ignoring failures."""
    for uid in admin_ids():
        try:
            _bot.send_message(uid, text, **kwargs)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Aggregates
# ---------------------------------------------------------------------------


def _groups():
    return [r['group_id'] for r in _q("SELECT DISTINCT group_id FROM users ORDER BY group_id")]


def _totals(columns):
    if not columns:
        return {}
    sums = ', '.join(f"COALESCE(SUM({c}), 0) AS {c}" for c in columns)
    rows = _q(f"SELECT {sums} FROM users")
    return {c: rows[0][c] for c in columns} if rows else {c: 0 for c in columns}


def _trade_counts(group_id=None):
    """Trade activity. Returns zeros when trade_system has never been initialised."""
    counts = {'active': 0, 'offered': 0, 'done': 0}
    where, params = '', ()
    if group_id is not None:
        where = " AND (sender_group_id=? OR receiver_group_id=?)"
        params = (group_id, group_id)
    try:
        for key, status in (('active', 'active'), ('offered', 'offered'), ('done', 'delivered')):
            rows = _q(f"SELECT COUNT(*) AS n FROM trades WHERE status=?{where}", (status,) + params)
            counts[key] = rows[0]['n'] if rows else 0
    except sqlite3.OperationalError:
        pass  # trades table does not exist yet
    return counts


def _top_group(columns):
    """(group_id, total) for the group with the largest sum over columns."""
    if not columns:
        return (None, 0)
    expr = ' + '.join(columns)
    rows = _q(f"SELECT group_id, ({expr}) AS total FROM users ORDER BY total DESC LIMIT 1")
    return (rows[0]['group_id'], rows[0]['total']) if rows else (None, 0)


def _lines(values):
    return '\n'.join(f"{_col(c)}: {_num(values[c])}" for c in values)


# ---------------------------------------------------------------------------
# Callback entry point
# ---------------------------------------------------------------------------


def handle_callback(call):
    """Dispatch every 'ap:' callback. Assumes main*.py already filtered by prefix."""
    try:
        parts = call.data.split(':')
        op = parts[1] if len(parts) > 1 else 'home'
        if op.startswith('cat') or op in asset_admin.OPS:
            asset_admin.handle(call, parts)
        elif op in country_assets.OPS:
            country_assets.handle(call, parts)
        elif op == 'nop':
            _answer(call)
        elif op == 'home':
            _panel(call)
        elif op == 'stats':
            _stats(call)
        elif op == 'eco':
            _economy(call)
        elif op == 'mil':
            _military(call)
        elif op == 'gl':
            _group_list(call, int(parts[2]))
        elif op == 'g':
            _group_card(call, int(parts[2]))
        elif op == 'feat':
            _feature_list(call)
        elif op == 'ft':
            _feature_toggle(call, parts[2])
        elif op == 'ftall':
            _players_toggle(call)
        elif op == 'log':
            _log_page(call, int(parts[2]))
        elif op == 'adm':
            _admin_list(call)
        elif op == 'aa':
            _admin_add_ask(call)
        elif op == 'ar':
            _admin_remove(call, int(parts[2]))
        elif op == 'rst':
            _reset_pick(call, int(parts[2]))
        elif op == 'rsg':
            _reset_confirm(call, int(parts[2]))
        elif op == 'rsc':
            _reset_apply(call, int(parts[2]))
        elif op == 'rsa':
            _reset_all_confirm(call)
        elif op == 'rsac':
            _reset_all_apply(call)
        elif op == 'ulc':
            _unset_group_apply(call, int(parts[2]))
        elif op == 'lgc':
            _log_clear_confirm(call)
        elif op == 'lgcc':
            _log_clear_apply(call)
        elif op == 'fac':
            _factory_confirm(call)
        elif op == 'facc':
            _factory_apply(call)
        elif op == 'wp':
            _war_photo_menu(call)
        elif op == 'wps':
            _war_photo_ask(call, parts[2])
        elif op == 'wpc':
            _war_photo_clear(call, parts[2])
        elif op == 'menu':
            _open_game_menu(call)
        else:
            _answer(call, _t('err_generic'))
    except Exception:
        traceback.print_exc()
        _answer(call, _t('err_generic'), alert=True)


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------


def open_panel(chat_id, user_id):
    """Entry point for /admin. Returns False when the caller is not an admin."""
    if not is_admin(user_id):
        return False
    _bot.send_message(chat_id, _panel_text(), reply_markup=_panel_markup(user_id),
                      parse_mode='HTML')
    return True


def _panel_text():
    features = enabled_features()
    text = _t('panel_title',
              owner=_user_link(_OWNER),
              admins=len(admin_ids()),
              groups=len(_groups()),
              on=sum(1 for v in features.values() if v),
              total=len(FEATURES))
    if not players_enabled():
        text += _t('panel_closed')
    return text


def _panel_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(_t('btn_stats'), callback_data='ap:stats'),
               types.InlineKeyboardButton(_t('btn_eco'), callback_data='ap:eco'))
    markup.add(types.InlineKeyboardButton(_t('btn_mil'), callback_data='ap:mil'),
               types.InlineKeyboardButton(_t('btn_features'), callback_data='ap:feat'))
    markup.add(types.InlineKeyboardButton(_t('btn_logs'), callback_data='ap:log:0'),
               types.InlineKeyboardButton(_t('btn_reset'), callback_data='ap:rst:0'))
    markup.add(types.InlineKeyboardButton(_t('btn_catalog'), callback_data='ap:cat'),
               types.InlineKeyboardButton(_t('btn_country_assets'), callback_data='ap:gas:0'))
    markup.add(types.InlineKeyboardButton(_t('btn_trade_photo'), callback_data='trd:ph'),
               types.InlineKeyboardButton(_t('btn_war_photo'), callback_data='ap:wp'))
    markup.add(types.InlineKeyboardButton(_t('btn_trade_adm'), callback_data='trd:adm'))
    if is_owner(user_id):
        markup.add(types.InlineKeyboardButton(_t('btn_admins'), callback_data='ap:adm'))
        markup.add(types.InlineKeyboardButton(_t('btn_factory'), callback_data='ap:fac'))
    if _game_menu is not None:
        markup.add(types.InlineKeyboardButton(_t('btn_game_menu'), callback_data='ap:menu'))
    return markup


def _panel(call):
    if not _require_admin(call):
        return
    _show(call, _panel_text(), _panel_markup(call.from_user.id))
    _answer(call)


def _open_game_menu(call):
    if not _require_admin(call):
        return
    _answer(call)
    if _game_menu is not None:
        _game_menu(call)


# ---------------------------------------------------------------------------
# Statistics / economy / military
# ---------------------------------------------------------------------------


def _stats(call):
    if not _require_admin(call):
        return
    groups = _groups()
    lords = _q("SELECT COUNT(*) AS n FROM users")
    resources = _totals(catalog.keys('resource'))
    units = _totals(catalog.keys('unit'))
    buildings = _totals(catalog.keys('building'))
    trades = _trade_counts()
    text = _t('stats_title',
              groups=len(groups),
              lords=lords[0]['n'] if lords else 0,
              wealth=_num(sum(resources.values())),
              troops=_num(sum(units.values())),
              buildings=_num(sum(buildings.values())),
              active=trades['active'], offered=trades['offered'], done=trades['done'])
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(_t('btn_per_group'), callback_data='ap:gl:0'))
    _show(call, text, _back_row(markup))
    _answer(call)


def _economy(call):
    if not _require_admin(call):
        return
    columns = catalog.keys('resource')
    totals = _totals(columns)
    gid, total = _top_group(columns)
    richest = f"{_esc(_title(gid))} ({_num(total)})" if gid is not None else _t('nobody')
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(_t('btn_per_group'), callback_data='ap:gl:0'))
    _show(call, _t('eco_title', lines=_lines(totals), richest=richest), _back_row(markup))
    _answer(call)


def _military(call):
    if not _require_admin(call):
        return
    columns = catalog.keys('unit')
    totals = _totals(columns)
    gid, total = _top_group(columns)
    strongest = f"{_esc(_title(gid))} ({_num(total)})" if gid is not None else _t('nobody')
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(_t('btn_per_group'), callback_data='ap:gl:0'))
    _show(call, _t('mil_title', lines=_lines(totals), strongest=strongest), _back_row(markup))
    _answer(call)


def _paged(items, page):
    pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    return items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE], page, pages


def _group_list(call, page):
    if not _require_admin(call):
        return
    groups = _groups()
    if not groups:
        _show(call, _t('no_groups'), _back_row(types.InlineKeyboardMarkup()))
        _answer(call)
        return
    window, page, pages = _paged(groups, page)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for gid in window:
        markup.add(types.InlineKeyboardButton(_title(gid), callback_data=f'ap:g:{gid}'))
    _pager(markup, page, pages, 'ap:gl:')
    _show(call, _t('group_list_title', p=page + 1, n=pages), _back_row(markup))
    _answer(call)


def _group_card(call, gid):
    if not _require_admin(call):
        return
    # An admin can disable every type, which would leave a trailing comma in the
    # SELECT below rather than an empty card.
    cols = ''.join(', ' + key for key in catalog.all_keys())
    rows = _q(f"SELECT user_id, home_sea, home_land{cols} FROM users WHERE group_id=?", (gid,))
    if not rows:
        _answer(call, _t('err_generic'), alert=True)
        return
    row = rows[0]
    trades = _trade_counts(gid)
    sections = '\n'.join(
        "{}\n<blockquote>{}</blockquote>".format(
            _t('sec_' + kind), _lines({c: row[c] for c in catalog.keys(kind)}))
        for kind in catalog.kind_order())
    text = _t('group_card',
              title=_esc(_title(gid)),
              lord=_user_link(row['user_id']),
              sections=sections,
              active=trades['active'], done=trades['done'],
              home_sea=_esc(row['home_sea'] or _t('unset')),
              home_land=_esc(row['home_land'] or _t('unset')))
    markup = types.InlineKeyboardMarkup(row_width=1)
    _back_row(markup, 'ap:gl:0')
    _show(call, text, markup)
    _answer(call)


# ---------------------------------------------------------------------------
# Feature toggles
# ---------------------------------------------------------------------------


def _feature_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    # The master switch sits above the individual features, because it
    # overrides all of them.
    markup.add(types.InlineKeyboardButton(
        _t('btn_players_on' if players_enabled() else 'btn_players_off'),
        callback_data='ap:ftall'))
    for key in FEATURES:
        state = _t('feat_on') if feature_enabled(key) else _t('feat_off')
        markup.add(types.InlineKeyboardButton(f"{state} {_t('feat_' + key)}",
                                              callback_data=f'ap:ft:{key}'))
    return _back_row(markup)


def _feature_list(call):
    if not _require_admin(call):
        return
    _show(call, _t('feat_title'), _feature_markup())
    _answer(call)


def _players_toggle(call):
    if not _require_admin(call):
        return
    new_state = not players_enabled()
    set_players_enabled(new_state)
    log(call.from_user.id, 'bot_switch', '', 'on' if new_state else 'off')
    _show(call, _t('feat_title'), _feature_markup())
    _answer(call, _t('bot_turned_on' if new_state else 'bot_turned_off'))


def _feature_toggle(call, key):
    if not _require_admin(call):
        return
    if key not in FEATURES:
        _answer(call, _t('err_generic'), alert=True)
        return
    new_state = not feature_enabled(key)
    _set_feature(key, new_state)
    log(call.from_user.id, 'feature_toggle', key, 'on' if new_state else 'off')
    _show(call, _t('feat_title'), _feature_markup())
    _answer(call, _t('feat_toggled', name=_t('feat_' + key),
                     state=_t('feat_on') if new_state else _t('feat_off')))


# ---------------------------------------------------------------------------
# Action log
# ---------------------------------------------------------------------------


def _log_page(call, page):
    if not _require_admin(call):
        return
    entries = recent_log()
    if not entries:
        _show(call, _t('log_empty'), _back_row(types.InlineKeyboardMarkup()))
        _answer(call)
        return
    pages = max(1, (len(entries) + LOG_PAGE_SIZE - 1) // LOG_PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    window = entries[page * LOG_PAGE_SIZE:(page + 1) * LOG_PAGE_SIZE]
    body = '\n\n'.join(_log_row(e) for e in window)
    markup = types.InlineKeyboardMarkup(row_width=2)
    _pager(markup, page, pages, 'ap:log:')
    if is_owner(call.from_user.id):
        markup.add(types.InlineKeyboardButton(_t('btn_log_clear'), callback_data='ap:lgc'))
    _show(call, _t('log_title', p=page + 1, n=pages) + '\n\n' + body, _back_row(markup))
    _answer(call)


def _log_clear_confirm(call):
    if not _require_owner(call):
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(_t('btn_confirm_log_clear'), callback_data='ap:lgcc'))
    _back_row(markup, 'ap:log:0')
    _show(call, _t('log_clear_confirm', n=log_size()), markup)
    _answer(call)


def _log_clear_apply(call):
    if not _require_owner(call):
        return
    count = clear_log()
    # The log cannot record its own erasure, so tell the admins directly.
    notify_admins(_t('log_clear_notice', u=_user_name(call.from_user.id), n=count))
    _show(call, _t('log_clear_done', n=count), _back_row(types.InlineKeyboardMarkup()))
    _answer(call)


def _log_row(entry):
    action = STRINGS[_lang].get('act_' + entry['action'], entry['action'])
    detail = entry['detail'] or ''
    if len(detail) > DETAIL_PREVIEW:
        detail = detail[:DETAIL_PREVIEW] + '…'
    return _t('log_row',
              action=_esc(action),
              actor=_user_link(entry['actor_id']),
              target=_esc(entry['target']),
              detail=f" — {_esc(detail)}" if detail else '',
              ts=time.strftime('%Y-%m-%d %H:%M', time.localtime(entry['ts'])))


# ---------------------------------------------------------------------------
# Admin management (owner only)
# ---------------------------------------------------------------------------


def _admin_list(call):
    if not _require_owner(call):
        return
    rows = _q("SELECT user_id FROM bot_admins ORDER BY added_at")
    extra = [r['user_id'] for r in rows if r['user_id'] != _OWNER]
    markup = types.InlineKeyboardMarkup(row_width=1)
    for uid in extra:
        markup.add(types.InlineKeyboardButton(f"🗑 {_user_name(uid)}", callback_data=f'ap:ar:{uid}'))
    markup.add(types.InlineKeyboardButton(_t('btn_add_admin'), callback_data='ap:aa'))
    text = _t('adm_title', owner=_user_link(_OWNER))
    if not extra:
        text += '\n' + _t('adm_none')
    _show(call, text, _back_row(markup))
    _answer(call)


def _admin_add_ask(call):
    if not _require_owner(call):
        return
    _answer(call)
    _bot.send_message(call.message.chat.id, _t('adm_add_ask'))
    _next_step(call.message, call.from_user.id,
               lambda msg: _admin_add_apply(msg, call.from_user.id))


def _admin_add_apply(message, actor_id):
    if not is_owner(actor_id):
        return
    uid = None
    forwarded = getattr(message, 'forward_from', None)
    if forwarded is not None:
        uid = forwarded.id
    elif message.text:
        try:
            uid = int(message.text.strip())
        except ValueError:
            uid = None
    if uid is None:
        _bot.send_message(message.chat.id, _t('adm_bad_id'))
        return
    if is_owner(uid):
        _bot.send_message(message.chat.id, _t('adm_is_owner'))
        return
    if _q("SELECT 1 FROM bot_admins WHERE user_id=?", (uid,)):
        _bot.send_message(message.chat.id, _t('adm_exists'))
        return
    _exec("INSERT INTO bot_admins (user_id, added_by, added_at, username) VALUES (?, ?, ?, ?)",
          (uid, actor_id, int(time.time()), _user_name(uid)))
    log(actor_id, 'admin_add', uid, _user_name(uid))
    _bot.send_message(message.chat.id, _t('adm_added', u=_user_link(uid)), parse_mode='HTML')


def _admin_remove(call, uid):
    if not _require_owner(call):
        return
    if is_owner(uid):
        _answer(call, _t('adm_is_owner'), alert=True)
        return
    _exec("DELETE FROM bot_admins WHERE user_id=?", (uid,))
    log(call.from_user.id, 'admin_remove', uid, _user_name(uid))
    _answer(call, _t('adm_removed', u=_user_name(uid)))
    _admin_list(call)


# ---------------------------------------------------------------------------
# Reset a country to its initial assets
# ---------------------------------------------------------------------------


def _reset_pick(call, page):
    if not _require_admin(call):
        return
    groups = _groups()
    if not groups:
        _show(call, _t('no_groups'), _back_row(types.InlineKeyboardMarkup()))
        _answer(call)
        return
    window, page, pages = _paged(groups, page)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for gid in window:
        markup.add(types.InlineKeyboardButton(_title(gid), callback_data=f'ap:rsg:{gid}'))
    _pager(markup, page, pages, 'ap:rst:')
    # Resetting every country one tap at a time is the same decision made N
    # times. This is that decision made once — and it is only the countries'
    # numbers, never the catalog, which is what the factory reset is for.
    markup.add(types.InlineKeyboardButton(_t('btn_reset_all', n=len(groups)),
                                          callback_data='ap:rsa'))
    _show(call, _t('reset_pick', p=page + 1, n=pages), _back_row(markup))
    _answer(call)


def _reset_country(gid):
    """Put one country back to the catalog defaults. Returns what changed."""
    columns = catalog.all_keys()
    defaults = catalog.defaults()
    if not columns:
        return None
    rows = _q(f"SELECT {', '.join(columns)} FROM users WHERE group_id=?", (gid,))
    if not rows:
        return None
    before = {c: rows[0][c] for c in columns}
    # Column names come from the catalog, which validates every key as an identifier.
    assignments = ', '.join(f"{c}=?" for c in columns)
    _exec(f"UPDATE users SET {assignments} WHERE group_id=?",
          tuple(defaults[c] for c in columns) + (gid,))
    return {c: v for c, v in before.items() if v != defaults[c]}


def _reset_all_confirm(call):
    if not _require_admin(call):
        return
    groups = _groups()
    if not groups:
        _show(call, _t('no_groups'), _back_row(types.InlineKeyboardMarkup()))
        _answer(call)
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(_t('btn_confirm_reset_all'), callback_data='ap:rsac'))
    _back_row(markup, 'ap:rst:0')
    _show(call, _t('reset_all_confirm', n=len(groups),
                   names=_esc('، '.join(_title(gid) for gid in groups))), markup)
    _answer(call)


def _reset_all_apply(call):
    if not _require_admin(call):
        return
    groups = _groups()
    done = [gid for gid in groups if _reset_country(gid) is not None]
    if not done:
        _answer(call, _t('err_generic'), alert=True)
        return
    log(call.from_user.id, 'reset_all', str(len(done)),
        ', '.join(_title(gid) for gid in done))
    _show(call, _t('reset_all_done', n=len(done)), _back_row(types.InlineKeyboardMarkup()))
    _answer(call)


def _reset_confirm(call, gid):
    if not _require_admin(call):
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(_t('btn_confirm_reset'), callback_data=f'ap:rsc:{gid}'))
    _back_row(markup, 'ap:rst:0')
    _show(call, _t('reset_confirm', title=_esc(_title(gid))), markup)
    _answer(call)


def _reset_apply(call, gid):
    if not _require_admin(call):
        return
    changed = _reset_country(gid)
    if changed is None:                   # no such country, or every type disabled
        _answer(call, _t('err_generic'), alert=True)
        return
    log(call.from_user.id, 'reset_country', _title(gid),
        json.dumps(changed, ensure_ascii=False, separators=(',', ':')))
    _show(call, _t('reset_done', title=_esc(_title(gid))),
          _back_row(types.InlineKeyboardMarkup()))
    _answer(call)


# ---------------------------------------------------------------------------
# Factory reset: the catalog back to the shape the game shipped with
# ---------------------------------------------------------------------------


def _factory_confirm(call):
    if not _require_owner(call):
        return
    custom = [row['key'] for row in catalog.entries(include_hidden=True) if not row['builtin']]
    customs = (_t('factory_customs', keys=_esc(', '.join(custom))) if custom
               else _t('factory_customs_none'))
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(_t('btn_confirm_factory'), callback_data='ap:facc'))
    _back_row(markup, 'ap:home')
    _show(call, _t('factory_confirm', customs=customs), markup)
    _answer(call)


def _factory_apply(call):
    if not _require_owner(call):
        return
    try:
        _removed, kept = catalog.factory_reset()
    except catalog.CatalogError as exc:
        _answer(call, STRINGS[_lang].get('cat_err_' + str(exc), _t('err_generic')), alert=True)
        return
    # The reset is only complete once the log of the edits it undid is gone too.
    count = clear_log()
    notify_admins(_t('factory_notice', u=_user_name(call.from_user.id), n=count))
    text = _t('factory_done')
    if kept:
        text += _t('factory_kept', keys=_esc(', '.join(kept)))
    _show(call, text, _back_row(types.InlineKeyboardMarkup()))
    _answer(call)


# ---------------------------------------------------------------------------
# Campaign photos
# ---------------------------------------------------------------------------

WAR_PHOTO_KEYS = {'land': 'war_photo_land', 'sea': 'war_photo_sea'}


def war_photo(mode):
    """file_id of the campaign photo for 'land'/'sea', or '' when unset."""
    return setting(WAR_PHOTO_KEYS.get(mode, ''), '')


def _war_photo_menu(call):
    if not _require_admin(call):
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for mode in ('land', 'sea'):
        state = _t('wp_set') if war_photo(mode) else _t('wp_unset')
        markup.add(types.InlineKeyboardButton(f"{_t('wp_' + mode)} — {state}",
                                              callback_data=f'ap:wps:{mode}'))
        if war_photo(mode):
            markup.add(types.InlineKeyboardButton(f"{_t('btn_wp_clear')} · {_t('wp_' + mode)}",
                                                  callback_data=f'ap:wpc:{mode}'))
    _show(call, _t('war_photo_title'), _back_row(markup))
    _answer(call)


def _war_photo_ask(call, mode):
    if not _require_admin(call):
        return
    if mode not in WAR_PHOTO_KEYS:
        _answer(call, _t('err_generic'), alert=True)
        return
    _answer(call)
    _bot.send_message(call.message.chat.id, _t('wp_ask'))
    _next_step(call.message, call.from_user.id,
               lambda msg: _war_photo_save(msg, mode, call.from_user.id))


def _war_photo_save(message, mode, actor_id):
    if not is_admin(actor_id):
        return
    if not getattr(message, 'photo', None):
        _bot.send_message(message.chat.id, _t('wp_not_photo'))
        return
    file_id = message.photo[-1].file_id
    set_setting(WAR_PHOTO_KEYS[mode], file_id)
    log(actor_id, 'war_photo', mode, 'set')
    _bot.send_message(message.chat.id, _t('wp_saved', kind=_t('wp_' + mode)))


def _war_photo_clear(call, mode):
    if not _require_admin(call):
        return
    if mode not in WAR_PHOTO_KEYS:
        _answer(call, _t('err_generic'), alert=True)
        return
    set_setting(WAR_PHOTO_KEYS[mode], '')
    log(call.from_user.id, 'war_photo', mode, 'cleared')
    _answer(call, _t('wp_cleared', kind=_t('wp_' + mode)))
    _war_photo_menu(call)


# ---------------------------------------------------------------------------
# Lord assignment — an admin replies to the player's message with /setlord
#
# There is no registration table: the `users` row *is* the country, assets and
# home nodes included. So taking a lordship back destroys those numbers, which
# is why /unsetlord below guards, confirms and logs rather than just deleting.
# ---------------------------------------------------------------------------


class LordError(ValueError):
    """Raised when a lordship cannot be taken back right now."""


def set_lord_guard(fn):
    """Register what decides a group is too busy to lose its lord.

    `fn` returns the group ids that still have a trade in flight. Their refunds
    and deliveries are `UPDATE users ... WHERE group_id=?`: against a deleted
    row that writes nothing and reports nothing, so the escrowed fee and the
    cargo are simply lost. With no guard registered nothing is in flight.
    """
    global _lord_guard
    _lord_guard = fn


def _groups_in_trade():
    if _lord_guard is None:
        return frozenset()
    try:
        return frozenset(_lord_guard())
    except Exception:
        raise LordError('guard_unavailable')


def _lord_err(exc):
    return STRINGS[_lang].get('unsetlord_err_' + str(exc), _t('err_generic'))


# Columns of `users` that are not the country's own numbers and must not be
# carried across to the next lord.
_ARCHIVE_SKIP = frozenset({'user_id', 'group_id'})


def _country_columns():
    """Everything about a country worth keeping: assets, treaties, home nodes."""
    with _lock:
        return [row[1] for row in _conn.execute("PRAGMA table_info(users)").fetchall()
                if row[1] not in _ARCHIVE_SKIP]


def archive_country(group_id):
    """Snapshot a country's numbers before its row goes, and return them.

    Called from the one place a country dies. The snapshot replaces any older
    one: what the next lord should inherit is what the last lord actually left,
    not the state from two lords ago.
    """
    columns = _country_columns()
    if not columns:
        return {}
    rows = _q(f"SELECT {', '.join(columns)} FROM users WHERE group_id=? LIMIT 1", (group_id,))
    if not rows:
        return {}
    data = dict(rows[0])
    owned = []
    try:
        owned = [r['node_id'] for r in
                 _q("SELECT node_id FROM chokepoint_owners WHERE group_id=?", (group_id,))]
    except sqlite3.OperationalError:
        pass  # trade_system's table; absent when the panel runs alone
    data['__chokepoints__'] = owned
    _exec("INSERT OR REPLACE INTO country_archive (group_id, saved_at, data) VALUES (?, ?, ?)",
          (group_id, int(time.time()),
           json.dumps(data, ensure_ascii=False, separators=(',', ':'))))
    return data


def archived_country(group_id):
    """The snapshot waiting for this group's next lord, or None."""
    rows = _q("SELECT data FROM country_archive WHERE group_id=?", (group_id,))
    if not rows:
        return None
    try:
        return json.loads(rows[0]['data'])
    except ValueError:
        return None


def restore_country(group_id):
    """Give a freshly-appointed lord what the last one left behind.

    Consumed on use: a country is inherited once. A column the catalog has
    dropped since the snapshot is skipped rather than restored, because there is
    nowhere left to put it.
    """
    data = archived_country(group_id)
    _exec("DELETE FROM country_archive WHERE group_id=?", (group_id,))
    if not data:
        return {}
    chokepoints = data.pop('__chokepoints__', [])
    live = set(_country_columns())
    restored = {c: v for c, v in data.items() if c in live}
    if restored:
        columns = list(restored)
        assignments = ', '.join(f"{c}=?" for c in columns)
        _exec(f"UPDATE users SET {assignments} WHERE group_id=?",
              tuple(restored[c] for c in columns) + (group_id,))
    # Only straits nobody has been given in the meantime: handing back one that
    # now belongs to another country would take it off them without a word.
    for nid in chokepoints:
        try:
            _exec("INSERT OR IGNORE INTO chokepoint_owners (node_id, group_id) VALUES (?, ?)",
                  (nid, group_id))
        except sqlite3.OperationalError:
            break
    return restored


def _drop_lords(group_id, user_id=None):
    """Delete a group's lord row(s) and return the user ids that went.

    The single path by which a country dies. `user_id` narrows it to one
    player; without it the whole group goes. Raises LordError rather than
    deleting anything when the group has a trade in flight.

    Losing the last lord no longer loses the country: the row's numbers are
    archived on the way out and handed to the next lord. Zeroing a country is
    the reset button's job, and stays a separate, deliberate act.
    """
    where, params = "group_id=?", (group_id,)
    if user_id is not None:
        where, params = "group_id=? AND user_id=?", (group_id, user_id)
    rows = _q(f"SELECT user_id FROM users WHERE {where}", params)
    if not rows:
        raise LordError('not_lord' if user_id is not None else 'no_lords')
    if group_id in _groups_in_trade():
        raise LordError('in_trade')
    with _lock:
        remaining = _conn.execute(
            f"SELECT COUNT(*) FROM users WHERE group_id=? AND user_id NOT IN "
            f"({', '.join('?' * len(rows))})",
            (group_id,) + tuple(r['user_id'] for r in rows)).fetchone()[0]
        # Only the last lord leaving ends the country, and only then is there
        # anything to keep: with a co-lord still in place the row survives.
        if not remaining:
            archive_country(group_id)
        _conn.execute(f"DELETE FROM users WHERE {where}", params)
        # A chokepoint whose owner no longer exists would keep charging tolls
        # on behalf of a country that is gone. The archive remembers which ones
        # they were, so the next lord gets them back.
        if not remaining:
            try:
                _conn.execute("DELETE FROM chokepoint_owners WHERE group_id=?", (group_id,))
            except sqlite3.OperationalError:
                pass  # trade_system's table; absent when the panel runs alone
            _conn.execute("DELETE FROM country_assets WHERE group_id=?", (group_id,))
        _conn.commit()
    return [row['user_id'] for row in rows]


def handle_setlord(message):
    """Register the replied-to user as the lord of this group. Admin only."""
    if message.chat.type not in ('group', 'supergroup'):
        _bot.reply_to(message, _t('setlord_group_only'))
        return
    if not feature_enabled('setlord'):
        _bot.reply_to(message, _t('feature_disabled'))
        return
    if not is_admin(message.from_user.id):
        _bot.reply_to(message, _t('setlord_not_admin'))
        return
    reply = getattr(message, 'reply_to_message', None)
    if reply is None or reply.from_user is None:
        _bot.reply_to(message, _t('setlord_need_reply'))
        return
    target = reply.from_user
    if getattr(target, 'is_bot', False):
        _bot.reply_to(message, _t('setlord_bot_target'))
        return

    group_id = message.chat.id
    if _q("SELECT 1 FROM users WHERE user_id=? AND group_id=?", (target.id, group_id)):
        _bot.reply_to(message, _t('setlord_already', u=_user_link(target.id)), parse_mode='HTML')
        return
    # A country with no lord left keeps its numbers in the archive. Whoever is
    # appointed next inherits them, rather than starting the country over.
    first_lord = not _q("SELECT 1 FROM users WHERE group_id=?", (group_id,))
    _exec("INSERT OR IGNORE INTO users (user_id, group_id) VALUES (?, ?)", (target.id, group_id))
    restored = restore_country(group_id) if first_lord else {}
    log(message.from_user.id, 'lord_assign', _title(group_id), str(target.id))
    text = _t('setlord_done', u=_user_link(target.id))
    if restored:
        log(message.from_user.id, 'country_restore', _title(group_id), str(len(restored)))
        text += _t('setlord_restored')
    _bot.reply_to(message, text, parse_mode='HTML')


def handle_unsetlord(message):
    """Take a lordship back. In reply: that player. On its own: the group.

    Removing one player is admin-level, the mirror of /setlord. Retiring a
    whole group deletes every country row it has, so it is owner-only and
    goes through a confirmation button.
    """
    if message.chat.type not in ('group', 'supergroup'):
        _bot.reply_to(message, _t('setlord_group_only'))
        return
    if not feature_enabled('setlord'):
        _bot.reply_to(message, _t('feature_disabled'))
        return
    if not is_admin(message.from_user.id):
        _bot.reply_to(message, _t('unsetlord_not_admin'))
        return
    reply = getattr(message, 'reply_to_message', None)
    if reply is None or reply.from_user is None:
        _unset_group_ask(message)
        return

    group_id = message.chat.id
    target = reply.from_user
    try:
        _drop_lords(group_id, target.id)
    except LordError as exc:
        _bot.reply_to(message, _lord_err(exc))
        return
    log(message.from_user.id, 'lord_unassign', _title(group_id), str(target.id))
    _bot.reply_to(message, _t('unsetlord_done', u=_user_link(target.id)), parse_mode='HTML')


def _unset_group_ask(message):
    """/unsetlord with nothing to reply to: offer to retire the whole group."""
    if not is_owner(message.from_user.id):
        _bot.reply_to(message, _t('unsetlord_not_owner'))
        return
    group_id = message.chat.id
    lords = _q("SELECT user_id FROM users WHERE group_id=?", (group_id,))
    if not lords:
        _bot.reply_to(message, _t('unsetlord_no_lords'))
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(_t('btn_unset_group'),
                                          callback_data=f'ap:ulc:{group_id}'))
    _bot.reply_to(message, _t('unsetlord_group_confirm', title=_esc(_title(group_id)),
                              n=len(lords)),
                  reply_markup=markup, parse_mode='HTML')


def _unset_group_apply(call, gid):
    # The guard is checked again inside _drop_lords rather than trusted from
    # the confirm screen: a trade can be offered between the two taps.
    if not _require_owner(call):
        return
    title = _title(gid)
    try:
        removed = _drop_lords(gid)
    except LordError as exc:
        _answer(call, _lord_err(exc), alert=True)
        return
    log(call.from_user.id, 'group_unassign', title, ', '.join(str(uid) for uid in removed))
    _show(call, _t('unsetlord_group_done', title=_esc(title), n=len(removed)))
    _answer(call)
