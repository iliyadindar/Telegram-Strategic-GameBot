# -*- coding: utf-8 -*-
"""Per-country overrides on the asset catalog.

The catalog says what exists in the game. This says what exists *for one
country*, because the two are not always the same: a landlocked nation has no
shipyards, a demilitarised one has no army, and a country under sanctions may
have its factories standing but idle.

    country_assets   one row per (country, type) an admin has overridden

Two independent switches, because they answer different questions:

    hidden   the type is not part of this country at all. It disappears from
             that country's status message and upgrade menu, and its buildings
             stop producing. The stored number is left alone, so putting the
             type back restores the country exactly as it was.

    paused   a building this country still has, which simply does not run. It
             stays visible with its level intact and can still be upgraded; it
             just yields nothing on the weekly cycle.

Nothing is written for a country that has no overrides, so the common case
costs no rows and the absence of a row means "as the catalog says".

admin_panel routes 'ap:gas…' callbacks here.
"""

import html
import threading

from telebot import types

import asset_catalog as catalog
from admin_strings import STRINGS

_conn = None
_bot = None
_lang = 'fa'
_require_admin = None
_answer = None
_show = None
_log = None
_back_button = None
_title = None
_groups = None
_lock = threading.RLock()

PAGE_SIZE = 8

# Ops this module owns. admin_panel dispatches on exactly these, so none of them
# may start with 'cat' — that prefix belongs to the catalog screens.
OPS = frozenset({'gas', 'gasg', 'gask', 'gast', 'gasp', 'gasr', 'gasrc'})


def attach(conn):
    """Point the module at a database and make sure its table exists.

    Separate from init() because the reading half is used by asset_ui, which
    has no business knowing whether the admin panel happens to be wired up.
    Both entry points call this, and calling it twice is harmless.
    """
    global _conn
    _conn = conn
    _migrate()


def init(bot, conn, lang, require_admin, answer, show, log, back_button, title, groups):
    """Wire the panel screens. attach() alone is enough to read the overrides."""
    global _bot, _lang, _require_admin, _answer, _show, _log, _back_button
    global _title, _groups
    _bot = bot
    _lang = lang
    _require_admin = require_admin
    _answer = answer
    _show = show
    _log = log
    _back_button = back_button
    _title = title            # group id -> its title
    _groups = groups          # () -> every registered group id
    attach(conn)


def _migrate():
    with _lock:
        _conn.execute('''CREATE TABLE IF NOT EXISTS country_assets (
            group_id INTEGER NOT NULL,
            key      TEXT NOT NULL,
            hidden   INTEGER NOT NULL DEFAULT 0,
            paused   INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (group_id, key)
        )''')
        _conn.commit()


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def _q(sql, params=()):
    with _lock:
        cur = _conn.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _exec(sql, params=()):
    with _lock:
        cur = _conn.execute(sql, params)
        _conn.commit()
        return cur


def hidden_keys(group_id):
    """Types this country does not have, whatever the catalog says."""
    return frozenset(row['key'] for row in
                     _q("SELECT key FROM country_assets WHERE group_id=? AND hidden=1",
                        (group_id,)))


def paused_keys(group_id):
    """Buildings this country has but which are switched off."""
    return frozenset(row['key'] for row in
                     _q("SELECT key FROM country_assets WHERE group_id=? AND paused=1",
                        (group_id,)))


def is_hidden(group_id, key):
    return key in hidden_keys(group_id)


def is_paused(group_id, key):
    """True when this building yields nothing here — switched off, or gone."""
    row = _row(group_id, key)
    return bool(row and (row['paused'] or row['hidden']))


def _row(group_id, key):
    rows = _q("SELECT hidden, paused FROM country_assets WHERE group_id=? AND key=?",
              (group_id, key))
    return rows[0] if rows else None


def keys_for(group_id, kind=None):
    """The catalog's keys minus the ones this country does not have."""
    gone = hidden_keys(group_id)
    return tuple(key for key in catalog.keys(kind) if key not in gone)


def production_for(group_id):
    """(building, produces, flat_output) this country actually runs.

    A building that is hidden or paused here is left out, and so is one whose
    product this country does not have — crediting a resource that does not
    show up anywhere would look like the numbers were lying.
    """
    gone = hidden_keys(group_id)
    off = paused_keys(group_id)
    return [(building, produces, output)
            for building, produces, output in catalog.production()
            if building not in gone and building not in off and produces not in gone]


def overrides(group_id):
    """(hidden, paused) counts, for a screen that has to say how much is set."""
    rows = _q("SELECT hidden, paused FROM country_assets WHERE group_id=?", (group_id,))
    return (sum(1 for r in rows if r['hidden']), sum(1 for r in rows if r['paused']))


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def _set(group_id, key, field, value):
    if field not in ('hidden', 'paused'):
        raise ValueError(field)
    with _lock:
        _conn.execute(
            "INSERT INTO country_assets (group_id, key, hidden, paused) VALUES (?, ?, 0, 0) "
            "ON CONFLICT(group_id, key) DO NOTHING", (group_id, key))
        _conn.execute(f"UPDATE country_assets SET {field}=? WHERE group_id=? AND key=?",
                      (1 if value else 0, group_id, key))
        # A row saying "nothing is overridden" is the same as no row at all, and
        # keeping it would make overrides() count a country that has none.
        _conn.execute("DELETE FROM country_assets WHERE group_id=? AND key=? "
                      "AND hidden=0 AND paused=0", (group_id, key))
        _conn.commit()


def set_hidden(group_id, key, value):
    _set(group_id, key, 'hidden', value)


def set_paused(group_id, key, value):
    _set(group_id, key, 'paused', value)


def clear(group_id):
    """Give a country the catalog back exactly as it stands. Returns how many went."""
    rows = _q("SELECT COUNT(*) AS n FROM country_assets WHERE group_id=?", (group_id,))
    _exec("DELETE FROM country_assets WHERE group_id=?", (group_id,))
    return rows[0]['n'] if rows else 0


def forget(key):
    """Drop every country's override for a type that no longer exists."""
    _exec("DELETE FROM country_assets WHERE key=?", (key,))


def forget_group(group_id):
    _exec("DELETE FROM country_assets WHERE group_id=?", (group_id,))


# ---------------------------------------------------------------------------
# Panel screens
# ---------------------------------------------------------------------------


def _t(string_id, **kw):
    text = STRINGS[_lang][string_id]
    return text.format(**kw) if kw else text


def _esc(text):
    return html.escape(str(text), quote=False)


def _label(key):
    return catalog.label(key, _lang)


def _markup(*rows, back='ap:home'):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for row in rows:
        if row:
            markup.add(*row)
    if back:
        _back_button(markup, back)
    return markup


def handle(call, parts):
    """parts is call.data.split(':'); parts[1] is one of OPS."""
    op = parts[1]
    if op == 'gas':
        _country_list(call, int(parts[2]))
    elif op == 'gasg':
        _country_screen(call, int(parts[2]))
    elif op == 'gask':
        _kind_list(call, int(parts[2]), parts[3], int(parts[4]))
    elif op == 'gast':
        _toggle_hidden(call, int(parts[2]), parts[3])
    elif op == 'gasp':
        _toggle_paused(call, int(parts[2]), parts[3])
    elif op == 'gasr':
        _clear_confirm(call, int(parts[2]))
    elif op == 'gasrc':
        _clear_apply(call, int(parts[2]))
    else:
        _answer(call, STRINGS[_lang]['err_generic'])


def _country_list(call, page):
    if not _require_admin(call):
        return
    groups = _groups()
    if not groups:
        _show(call, _t('no_groups'), _markup())
        _answer(call)
        return
    pages = max(1, (len(groups) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    buttons = []
    for gid in groups[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
        off, paused = overrides(gid)
        mark = _t('gas_marks', off=off, paused=paused) if (off or paused) else ''
        buttons.append(types.InlineKeyboardButton(f"{_title(gid)}{mark}",
                                                  callback_data=f'ap:gasg:{gid}'))
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(_t('btn_prev'), callback_data=f'ap:gas:{page - 1}'))
    if page < pages - 1:
        nav.append(types.InlineKeyboardButton(_t('btn_next'), callback_data=f'ap:gas:{page + 1}'))
    _show(call, _t('gas_pick', p=page + 1, n=pages), _markup(buttons, nav))
    _answer(call)


def _country_screen(call, gid):
    if not _require_admin(call):
        return
    off, paused = overrides(gid)
    gone = hidden_keys(gid)
    stopped = paused_keys(gid)
    buttons = [types.InlineKeyboardButton(
        _t('gas_kind_btn', kind=_t('kind_' + kind),
           n=len(keys_for(gid, kind)), total=len(catalog.keys(kind))),
        callback_data=f'ap:gask:{gid}:{kind}:0') for kind in catalog.kind_order()]
    tools = []
    if off or paused:
        tools.append(types.InlineKeyboardButton(_t('btn_gas_clear'),
                                                callback_data=f'ap:gasr:{gid}'))
    _show(call, _t('gas_country', g=_esc(_title(gid)),
                   off=_esc(', '.join(_label(k) for k in sorted(gone))) or _t('gas_none'),
                   paused=_esc(', '.join(_label(k) for k in sorted(stopped)))
                   or _t('gas_none')),
          _markup(buttons, tools, back='ap:gas:0'))
    _answer(call)


def _kind_list(call, gid, kind, page):
    """One kind's types for one country, each with what it can be switched to."""
    if not _require_admin(call):
        return
    if kind not in catalog.KINDS:
        _answer(call, STRINGS[_lang]['err_generic'], alert=True)
        return
    keys = catalog.keys(kind)
    pages = max(1, (len(keys) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    gone = hidden_keys(gid)
    stopped = paused_keys(gid)
    rows = []
    for key in keys[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
        mark = _t('gas_off') if key in gone else _t('gas_on')
        row = [types.InlineKeyboardButton(f"{mark} {_label(key)}",
                                          callback_data=f'ap:gast:{gid}:{key}')]
        # Pausing only means anything for something that produces: a resource
        # cannot be switched off, only taken away.
        if kind == 'building' and key not in gone:
            row.append(types.InlineKeyboardButton(
                _t('btn_gas_run') if key in stopped else _t('btn_gas_stop'),
                callback_data=f'ap:gasp:{gid}:{key}'))
        rows.append(row)
    markup = types.InlineKeyboardMarkup(row_width=2)
    for row in rows:
        markup.row(*row)
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(
            _t('btn_prev'), callback_data=f'ap:gask:{gid}:{kind}:{page - 1}'))
    if page < pages - 1:
        nav.append(types.InlineKeyboardButton(
            _t('btn_next'), callback_data=f'ap:gask:{gid}:{kind}:{page + 1}'))
    if nav:
        markup.add(*nav)
    _back_button(markup, f'ap:gasg:{gid}')
    _show(call, _t('gas_kind', g=_esc(_title(gid)), kind=_t('kind_' + kind),
                   p=page + 1, n=pages), markup)
    _answer(call)


def _toggle_hidden(call, gid, key):
    if not _require_admin(call):
        return
    if catalog.entry(key) is None:
        _answer(call, _t('cat_err_unknown'), alert=True)
        return
    new_state = not is_hidden(gid, key)
    set_hidden(gid, key, new_state)
    _log(call.from_user.id, 'country_asset', _title(gid),
         f"{key}={'removed' if new_state else 'restored'}")
    _answer(call, _t('gas_removed' if new_state else 'gas_restored', label=_label(key)))
    _kind_list(call, gid, catalog.entry(key)['kind'], 0)


def _toggle_paused(call, gid, key):
    if not _require_admin(call):
        return
    row = catalog.entry(key)
    if row is None or row['kind'] != 'building':
        _answer(call, _t('cat_err_not_a_building'), alert=True)
        return
    new_state = key not in paused_keys(gid)
    set_paused(gid, key, new_state)
    _log(call.from_user.id, 'country_asset', _title(gid),
         f"{key}={'stopped' if new_state else 'running'}")
    _answer(call, _t('gas_stopped' if new_state else 'gas_running', label=_label(key)))
    _kind_list(call, gid, 'building', 0)


def _clear_confirm(call, gid):
    if not _require_admin(call):
        return
    off, paused = overrides(gid)
    confirm = types.InlineKeyboardButton(_t('btn_gas_clear_yes'),
                                         callback_data=f'ap:gasrc:{gid}')
    _show(call, _t('gas_clear_confirm', g=_esc(_title(gid)), off=off, paused=paused),
          _markup([confirm], back=f'ap:gasg:{gid}'))
    _answer(call)


def _clear_apply(call, gid):
    if not _require_admin(call):
        return
    count = clear(gid)
    _log(call.from_user.id, 'country_asset', _title(gid), f'{count} overrides cleared')
    _answer(call, _t('gas_cleared', n=count))
    _country_screen(call, gid)
