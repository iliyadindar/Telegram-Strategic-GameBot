# -*- coding: utf-8 -*-
"""Inline Telegram admin dashboard.

main*.py calls init() once, then:

    * routes /admin            -> open_panel(chat_id, user_id)
    * routes /setlord          -> handle_setlord(message)
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
    asset_admin.init(bot, lang, _require_admin, _answer, _show, log, _next_step, _back_row)


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


def require_feature(call, key):
    """Guard a callback branch. Answers with an alert and returns False if off."""
    if feature_enabled(key):
        return True
    _answer(call, _t('feature_disabled'), alert=True)
    return False


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
        if op.startswith('cat'):
            asset_admin.handle(call, parts)
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
    return _t('panel_title',
              owner=_user_link(_OWNER),
              admins=len(admin_ids()),
              groups=len(_groups()),
              on=sum(1 for v in features.values() if v),
              total=len(FEATURES))


def _panel_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(_t('btn_stats'), callback_data='ap:stats'),
               types.InlineKeyboardButton(_t('btn_eco'), callback_data='ap:eco'))
    markup.add(types.InlineKeyboardButton(_t('btn_mil'), callback_data='ap:mil'),
               types.InlineKeyboardButton(_t('btn_features'), callback_data='ap:feat'))
    markup.add(types.InlineKeyboardButton(_t('btn_logs'), callback_data='ap:log:0'),
               types.InlineKeyboardButton(_t('btn_reset'), callback_data='ap:rst:0'))
    markup.add(types.InlineKeyboardButton(_t('btn_catalog'), callback_data='ap:cat'))
    markup.add(types.InlineKeyboardButton(_t('btn_trade_photo'), callback_data='trd:ph'),
               types.InlineKeyboardButton(_t('btn_war_photo'), callback_data='ap:wp'))
    markup.add(types.InlineKeyboardButton(_t('btn_trade_adm'), callback_data='trd:adm'))
    if is_owner(user_id):
        markup.add(types.InlineKeyboardButton(_t('btn_admins'), callback_data='ap:adm'))
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
    cols = ', '.join(catalog.all_keys())
    rows = _q(f"SELECT user_id, home_sea, home_land, {cols} FROM users WHERE group_id=?", (gid,))
    if not rows:
        _answer(call, _t('err_generic'), alert=True)
        return
    row = rows[0]
    trades = _trade_counts(gid)
    text = _t('group_card',
              title=_esc(_title(gid)),
              lord=_user_link(row['user_id']),
              resources=_lines({c: row[c] for c in catalog.keys('resource')}),
              units=_lines({c: row[c] for c in catalog.keys('unit')}),
              buildings=_lines({c: row[c] for c in catalog.keys('building')}),
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
    _show(call, _t('log_title', p=page + 1, n=pages) + '\n\n' + body, _back_row(markup))
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
    _show(call, _t('reset_pick', p=page + 1, n=pages), _back_row(markup))
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
    columns = catalog.all_keys()
    defaults = catalog.defaults()
    cols = ', '.join(columns)
    rows = _q(f"SELECT {cols} FROM users WHERE group_id=?", (gid,))
    if not rows:
        _answer(call, _t('err_generic'), alert=True)
        return
    before = {c: rows[0][c] for c in columns}
    # Column names come from the catalog, which validates every key as an identifier.
    assignments = ', '.join(f"{c}=?" for c in columns)
    _exec(f"UPDATE users SET {assignments} WHERE group_id=?",
          tuple(defaults[c] for c in columns) + (gid,))
    changed = {c: v for c, v in before.items() if v != defaults[c]}
    log(call.from_user.id, 'reset_country', _title(gid),
        json.dumps(changed, ensure_ascii=False, separators=(',', ':')))
    _show(call, _t('reset_done', title=_esc(_title(gid))),
          _back_row(types.InlineKeyboardMarkup()))
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
# ---------------------------------------------------------------------------


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
    _exec("INSERT OR IGNORE INTO users (user_id, group_id) VALUES (?, ?)", (target.id, group_id))
    log(message.from_user.id, 'lord_assign', _title(group_id), str(target.id))
    _bot.reply_to(message, _t('setlord_done', u=_user_link(target.id)), parse_mode='HTML')
