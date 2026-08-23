# -*- coding: utf-8 -*-
"""Panel screens for editing the asset catalog.

Split out of admin_panel.py so that file stays about access, statistics and
toggles. It receives the panel's helpers through init() rather than importing
admin_panel, so the dependency runs one way only.

Callback space: everything under 'ap:cat…', routed here by admin_panel.
"""

import html

from telebot import types

import asset_catalog as catalog
import country_assets
from admin_strings import STRINGS

_bot = None
_lang = 'fa'
_require_admin = None
_require_owner = None
_answer = None
_show = None
_log = None
_next_step = None
_back_button = None

PAGE_SIZE = 8

# Ops this module owns whose name does not start with 'cat'. admin_panel routes
# by prefix, so anything shorter has to be named here. The per-level screens are
# short on purpose: a building key and a resource key spelled out together
# overflow Telegram's 64-byte callback budget.
OPS = frozenset({'clv', 'clva', 'clvl', 'clvc', 'clvo', 'clvd', 'cmax'})

# in-progress "add a type" wizards, keyed by user id
_wizards = {}


def init(bot, lang, require_admin, answer, show, log, next_step, back_button,
         require_owner=None):
    global _bot, _lang, _require_admin, _require_owner, _answer, _show, _log
    global _next_step, _back_button
    _bot = bot
    _lang = lang
    _require_admin = require_admin
    # Destroying a type is owner-only. Without a checker, fall back to the
    # admin one rather than silently letting anyone through.
    _require_owner = require_owner if require_owner is not None else require_admin
    _answer = answer
    _show = show
    _log = log
    _next_step = next_step
    _back_button = back_button


def _t(string_id, **kw):
    text = STRINGS[_lang][string_id]
    return text.format(**kw) if kw else text


def _esc(text):
    return html.escape(str(text), quote=False)


def _label(key):
    return catalog.label(key, _lang)


def _err(exc):
    """Turn a CatalogError code into a sentence, falling back to the generic one."""
    return STRINGS[_lang].get('cat_err_' + str(exc), STRINGS[_lang]['err_generic'])


def _markup(*rows, back='ap:cat'):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for row in rows:
        if row:
            markup.add(*row)
    if back:
        _back_button(markup, back)
    return markup


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def handle(call, parts):
    """parts is call.data.split(':'); parts[1] always starts with 'cat'."""
    op = parts[1]
    if op == 'cat':
        _catalog_home(call)
    elif op == 'catk':
        _kind_list(call, parts[2], int(parts[3]))
    elif op == 'cate':
        _entry_screen(call, parts[2])
    elif op == 'catadd':
        _add_start(call, parts[2])
    elif op == 'catprod':
        _add_produces(call, parts[2])
    elif op == 'catren':
        _ask_rename(call, parts[2])
    elif op == 'catdef':
        _ask_default(call, parts[2])
    elif op == 'catout':
        _ask_output_target(call, parts[2])
    elif op == 'catouts':
        _ask_output_amount(call, parts[2], parts[3])
    elif op == 'cattr':
        _toggle_tradeable(call, parts[2])
    elif op == 'catcost':
        _cost_list(call, parts[2])
    elif op == 'catcosts':
        _ask_cost(call, parts[2], parts[3])
    elif op == 'clv':
        _level_list(call, parts[2])
    elif op == 'clva':
        _ask_new_level(call, parts[2])
    elif op == 'clvl':
        _level_screen(call, parts[2], int(parts[3]))
    elif op == 'clvc':
        _ask_level_cost(call, parts[2], int(parts[3]), int(parts[4]))
    elif op == 'clvo':
        _ask_level_output(call, parts[2], int(parts[3]))
    elif op == 'clvd':
        _clear_level(call, parts[2], int(parts[3]))
    elif op == 'cmax':
        _ask_max_level(call, parts[2])
    elif op == 'cathide':
        _hide(call, parts[2])
    elif op == 'catshow':
        _unhide(call, parts[2])
    elif op == 'catmv':
        _move(call, parts[2], parts[3])
    elif op == 'catord':
        _kind_order_screen(call)
    elif op == 'catordmv':
        _move_kind(call, parts[2], parts[3])
    elif op == 'catdel':
        _delete_confirm(call, parts[2])
    elif op == 'catdelc':
        _delete_apply(call, parts[2])
    else:
        _answer(call, STRINGS[_lang]['err_generic'])


# ---------------------------------------------------------------------------
# Browsing
# ---------------------------------------------------------------------------


def _catalog_home(call):
    if not _require_admin(call):
        return
    counts = {kind: len(catalog.keys(kind)) for kind in catalog.KINDS}
    buttons = [types.InlineKeyboardButton(f"{_t('kind_' + kind)} ({counts[kind]})",
                                          callback_data=f'ap:catk:{kind}:0')
               for kind in catalog.kind_order()]
    order = [types.InlineKeyboardButton(_t('btn_cat_order'), callback_data='ap:catord')]
    _show(call, _t('cat_title', resources=counts['resource'], units=counts['unit'],
                   buildings=counts['building']),
          _markup(buttons, order, back='ap:home'))
    _answer(call)


def _kind_list(call, kind, page):
    if not _require_admin(call):
        return
    if kind not in catalog.KINDS:
        _answer(call, STRINGS[_lang]['err_generic'], alert=True)
        return
    rows = catalog.entries(kind, include_hidden=True)
    pages = max(1, (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    buttons = []
    for row in rows[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
        mark = _t('cat_hidden_mark') + ' ' if row['hidden'] else ''
        buttons.append(types.InlineKeyboardButton(f"{mark}{_label(row['key'])}",
                                                  callback_data=f"ap:cate:{row['key']}"))
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(_t('btn_prev'),
                                              callback_data=f'ap:catk:{kind}:{page - 1}'))
    if page < pages - 1:
        nav.append(types.InlineKeyboardButton(_t('btn_next'),
                                              callback_data=f'ap:catk:{kind}:{page + 1}'))
    add = [types.InlineKeyboardButton(_t('btn_cat_add'), callback_data=f'ap:catadd:{kind}')]
    _show(call, _t('cat_list_title', kind=_t('kind_' + kind), p=page + 1, n=pages),
          _markup(buttons, nav, add))
    _answer(call)


def _cost_summary(key):
    costs = catalog.upgrade_cost(key)
    if not costs:
        return _t('cat_costs_none')
    return ' · '.join(f"{_label(res)} {amount}" for res, amount in costs.items())


def _entry_screen(call, key):
    if not _require_admin(call):
        return
    row = catalog.entry(key)
    if row is None:
        _answer(call, _t('cat_err_unknown'), alert=True)
        return

    if row['kind'] == 'building':
        tuned = sorted(set(catalog.tuned_cost_levels(key)) |
                       set(catalog.tuned_output_levels(key)))
        extra = _t('cat_extra_building',
                   produces=_label(row['produces']) if row['produces'] else _t('cat_produces_none'),
                   output=row['output'], costs=_cost_summary(key),
                   max=row['max_level'] or _t('cat_max_none'),
                   tuned=', '.join(str(n) for n in tuned) if tuned else _t('cat_levels_none'))
    elif row['kind'] == 'resource':
        extra = _t('cat_extra_resource',
                   tradeable=_t('cat_yes') if row['tradeable'] else _t('cat_no'))
    else:
        extra = ''

    place, total = catalog.rank(key)
    extra = (extra + '\n' if extra else '') + _t('cat_rank', place=place, total=total)

    note = _t('cat_builtin_note') if row['builtin'] else ''
    if key in catalog.ENGINE_KEYS:
        note += _t('cat_engine_note')
    if row['hidden']:
        note += _t('cat_hidden_note')

    buttons = [types.InlineKeyboardButton(_t('btn_cat_rename'), callback_data=f'ap:catren:{key}'),
               types.InlineKeyboardButton(_t('btn_cat_default'), callback_data=f'ap:catdef:{key}')]
    if row['kind'] == 'building':
        buttons.append(types.InlineKeyboardButton(_t('btn_cat_output'),
                                                  callback_data=f'ap:catout:{key}'))
        buttons.append(types.InlineKeyboardButton(_t('btn_cat_costs'),
                                                  callback_data=f'ap:catcost:{key}'))
        buttons.append(types.InlineKeyboardButton(_t('btn_cat_levels'),
                                                  callback_data=f'ap:clv:{key}'))
        buttons.append(types.InlineKeyboardButton(_t('btn_cat_max'),
                                                  callback_data=f'ap:cmax:{key}'))
    if row['kind'] == 'resource':
        buttons.append(types.InlineKeyboardButton(_t('btn_cat_tradeable'),
                                                  callback_data=f'ap:cattr:{key}'))

    order = []
    if place > 1:
        order.append(types.InlineKeyboardButton(_t('btn_cat_up'),
                                                callback_data=f'ap:catmv:{key}:up'))
    if place < total:
        order.append(types.InlineKeyboardButton(_t('btn_cat_down'),
                                                callback_data=f'ap:catmv:{key}:down'))

    # Every type can be taken out of the game, shipped or not. Only permanent
    # deletion is withheld, and only for the keys the trade engine names in SQL.
    if row['hidden']:
        buttons.append(types.InlineKeyboardButton(_t('btn_cat_unhide'),
                                                  callback_data=f'ap:catshow:{key}'))
    else:
        buttons.append(types.InlineKeyboardButton(_t('btn_cat_hide'),
                                                  callback_data=f'ap:cathide:{key}'))
    if key not in catalog.ENGINE_KEYS:
        buttons.append(types.InlineKeyboardButton(_t('btn_cat_delete'),
                                                  callback_data=f'ap:catdel:{key}'))

    _show(call, _t('cat_entry', label=_esc(_label(key)), key=_esc(key),
                   kind=_t('kind_' + row['kind']), default=row['default_value'],
                   extra=extra, note=note),
          _markup(order, buttons, back=f"ap:catk:{row['kind']}:0"))
    _answer(call)


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def _move(call, key, direction):
    if not _require_admin(call):
        return
    try:
        moved = catalog.move(key, direction)
    except catalog.CatalogError as exc:
        _answer(call, _err(exc), alert=True)
        return
    if not moved:
        _answer(call, _t('cat_at_top' if direction == 'up' else 'cat_at_bottom'))
        return
    place, _total = catalog.rank(key)
    _log(call.from_user.id, 'asset_type_edit', key, f'moved {direction} to #{place}')
    _answer(call, _t('cat_moved'))
    _entry_screen(call, key)


def _kind_order_screen(call):
    """Which of the three sections comes first in the status message."""
    if not _require_admin(call):
        return
    order = catalog.kind_order()
    # One keyboard row per section, so each ⬆️/⬇️ sits beside the section it
    # moves. _markup() stacks everything one-per-line, which would leave three
    # identical arrow pairs with nothing saying which is which.
    markup = types.InlineKeyboardMarkup(row_width=3)
    for place, kind in enumerate(order, start=1):
        row = [types.InlineKeyboardButton(f"{place}. {_t('kind_' + kind)}",
                                          callback_data='ap:catord')]
        if place > 1:
            row.append(types.InlineKeyboardButton(_t('btn_cat_up'),
                                                  callback_data=f'ap:catordmv:{kind}:up'))
        if place < len(order):
            row.append(types.InlineKeyboardButton(_t('btn_cat_down'),
                                                  callback_data=f'ap:catordmv:{kind}:down'))
        markup.row(*row)
    _back_button(markup, 'ap:cat')
    _show(call, _t('cat_order_title',
                   order=' ← '.join(_t('kind_' + kind) for kind in order)), markup)
    _answer(call)


def _move_kind(call, kind, direction):
    if not _require_admin(call):
        return
    try:
        moved = catalog.move_kind(kind, direction)
    except catalog.CatalogError as exc:
        _answer(call, _err(exc), alert=True)
        return
    if not moved:
        _answer(call, _t('cat_at_top' if direction == 'up' else 'cat_at_bottom'))
        return
    place, _total = catalog.kind_rank(kind)
    _log(call.from_user.id, 'asset_kind_order', kind, f'moved {direction} to #{place}')
    _answer(call, _t('cat_moved'))
    _kind_order_screen(call)


# ---------------------------------------------------------------------------
# Destroying a type
# ---------------------------------------------------------------------------


def _delete_confirm(call, key):
    if not _require_owner(call):
        return
    row = catalog.entry(key)
    if row is None:
        _answer(call, _t('cat_err_unknown'), alert=True)
        return
    if key in catalog.ENGINE_KEYS:
        _answer(call, _t('cat_err_engine_key'), alert=True)
        return
    count = catalog.holders(key)
    holders = (_t('cat_delete_holders', n=count) if count
               else _t('cat_delete_holders_none'))
    # Deleting something that shipped with the game is the one delete an admin
    # cannot undo by re-adding it, so it says so before the confirm button.
    if row['builtin']:
        holders += _t('cat_delete_builtin_warning')
    confirm = types.InlineKeyboardButton(_t('btn_cat_delete_yes'),
                                         callback_data=f'ap:catdelc:{key}')
    _show(call, _t('cat_delete_confirm', label=_esc(_label(key)), key=_esc(key),
                   holders=holders),
          _markup([confirm], back=f'ap:cate:{key}'))
    _answer(call)


def _delete_apply(call, key):
    if not _require_owner(call):
        return
    label = _label(key)
    kind = (catalog.entry(key) or {}).get('kind', 'resource')
    try:
        dropped = catalog.remove(key)
    except catalog.CatalogError as exc:
        _answer(call, _err(exc), alert=True)
        return
    # Per-country overrides for a type that no longer exists would keep a
    # country marked as "does not have" something nobody has.
    country_assets.forget(key)
    _log(call.from_user.id, 'asset_remove', key, 'destroyed' if dropped else 'column kept')
    _bot.send_message(call.message.chat.id,
                      _t('cat_deleted' if dropped else 'cat_deleted_kept_column', label=label))
    _kind_list(call, kind, 0)


# ---------------------------------------------------------------------------
# Editing an existing type
# ---------------------------------------------------------------------------


def _ask_rename(call, key):
    if not _require_admin(call):
        return
    if catalog.entry(key) is None:
        _answer(call, _t('cat_err_unknown'), alert=True)
        return
    _answer(call)
    _collect_labels(call.message, call.from_user.id, {},
                    lambda labels: _apply_rename(call, key, labels))


def _apply_rename(call, key, labels):
    catalog.set_labels(key, labels)
    _log(call.from_user.id, 'asset_type_edit', key, 'renamed')
    _bot.send_message(call.message.chat.id, _t('cat_renamed'))
    _entry_screen(call, key)


def _ask_default(call, key):
    if not _require_admin(call):
        return
    if catalog.entry(key) is None:
        _answer(call, _t('cat_err_unknown'), alert=True)
        return
    _answer(call)
    _ask_number(call, _t('cat_ask_default'), lambda value: _apply_default(call, key, value))


def _apply_default(call, key, value):
    catalog.set_default(key, value)
    _log(call.from_user.id, 'asset_type_edit', key, f'default={value}')
    _bot.send_message(call.message.chat.id, _t('cat_default_set', value=value))
    _entry_screen(call, key)


def _ask_output_target(call, key):
    """Step 1 of production: which type does this building yield?"""
    if not _require_admin(call):
        return
    row = catalog.entry(key)
    if row is None or row['kind'] != 'building':
        _answer(call, _t('cat_err_not_a_building'), alert=True)
        return
    buttons = [types.InlineKeyboardButton(_label(target),
                                          callback_data=f'ap:catouts:{key}:{target}')
               for target in catalog.keys('resource') + catalog.keys('unit')]
    buttons.append(types.InlineKeyboardButton(_t('btn_produces_none'),
                                              callback_data=f'ap:catouts:{key}:-'))
    _show(call, _t('cat_pick_produces'), _markup(buttons, back=f'ap:cate:{key}'))
    _answer(call)


def _ask_output_amount(call, key, target):
    if not _require_admin(call):
        return
    if target == '-':
        catalog.set_output(key, '', 0)
        _log(call.from_user.id, 'asset_type_edit', key, 'produces nothing')
        _answer(call, _t('cat_output_set'))
        _entry_screen(call, key)
        return
    _answer(call)
    _ask_number(call, _t('cat_ask_output'),
                lambda value: _apply_output(call, key, target, value))


def _apply_output(call, key, target, value):
    catalog.set_output(key, target, value)
    _log(call.from_user.id, 'asset_type_edit', key, f'{target}+{value}/week')
    _bot.send_message(call.message.chat.id, _t('cat_output_set'))
    _entry_screen(call, key)


def _toggle_tradeable(call, key):
    if not _require_admin(call):
        return
    row = catalog.entry(key)
    if row is None or row['kind'] != 'resource':
        _answer(call, _t('cat_err_not_a_resource'), alert=True)
        return
    new_state = not row['tradeable']
    catalog.set_tradeable(key, new_state)
    _log(call.from_user.id, 'asset_type_edit', key,
         'tradeable' if new_state else 'not tradeable')
    _answer(call, _t('cat_tradeable_on') if new_state else _t('cat_tradeable_off'))
    _entry_screen(call, key)


def _cost_list(call, key):
    if not _require_admin(call):
        return
    row = catalog.entry(key)
    if row is None or row['kind'] != 'building':
        _answer(call, _t('cat_err_not_a_building'), alert=True)
        return
    costs = catalog.upgrade_cost(key)
    buttons = [types.InlineKeyboardButton(f"{_label(res)} — {costs.get(res, 0)}",
                                          callback_data=f'ap:catcosts:{key}:{res}')
               for res in catalog.keys('resource')]
    _show(call, _t('cat_costs_title', label=_esc(_label(key))),
          _markup(buttons, back=f'ap:cate:{key}'))
    _answer(call)


def _ask_cost(call, key, resource):
    if not _require_admin(call):
        return
    _answer(call)
    _ask_number(call, _t('cat_ask_cost', res=_label(resource)),
                lambda value: _apply_cost(call, key, resource, value))


def _apply_cost(call, key, resource, value):
    catalog.set_upgrade_cost(key, resource, value)
    _log(call.from_user.id, 'asset_cost', key, f'{resource}={value}')
    _bot.send_message(call.message.chat.id, _t('cat_cost_set'))
    _cost_list(call, key)


# ---------------------------------------------------------------------------
# Per-level tuning
#
# A building's price and yield are flat by default: one cost row and one output
# number that every level shares. Here an admin gives a single level numbers of
# its own — level 7 costing more than level 6, yielding less, or both — and
# every level nobody has touched keeps falling back to the flat values.
# ---------------------------------------------------------------------------


def _resource_index(i):
    """The resource a level-cost button stands for.

    The button carries the resource's position rather than its name because a
    key may be 31 characters and Telegram gives the whole callback 64: a
    building and a resource spelled out together do not fit. The list is
    rendered and read back in the same breath, so the position is stable.
    """
    resources = catalog.keys('resource')
    return resources[i] if 0 <= i < len(resources) else None


def _level_cost_line(key, level):
    """One level's price, marked as its own or inherited from the flat cost."""
    if not catalog.level_cost_is_set(key, level):
        return _t('cat_lvl_inherited')
    costs = catalog.upgrade_cost(key, level)
    if not costs:
        return _t('cat_costs_none')
    return ' · '.join(f"{_label(res)} {amount}" for res, amount in costs.items())


def _level_list(call, key):
    """Every level this building has been tuned at, plus a way to add one."""
    if not _require_admin(call):
        return
    row = catalog.entry(key)
    if row is None or row['kind'] != 'building':
        _answer(call, _t('cat_err_not_a_building'), alert=True)
        return
    levels = sorted(set(catalog.tuned_cost_levels(key)) | set(catalog.tuned_output_levels(key)))
    buttons = [types.InlineKeyboardButton(
        _t('btn_cat_level', level=level,
           cost=_level_cost_line(key, level), out=catalog.level_output(key, level)),
        callback_data=f'ap:clvl:{key}:{level}') for level in levels]
    add = [types.InlineKeyboardButton(_t('btn_cat_level_add'), callback_data=f'ap:clva:{key}')]
    _show(call, _t('cat_levels_title', label=_esc(_label(key)),
                   costs=_cost_summary(key), output=row['output'],
                   max=row['max_level'] or _t('cat_max_none'),
                   tuned=', '.join(str(n) for n in levels) if levels else _t('cat_levels_none')),
          _markup(buttons, add, back=f'ap:cate:{key}'))
    _answer(call)


def _ask_new_level(call, key):
    """Which level to tune. Its price starts as a copy of the flat one."""
    if not _require_admin(call):
        return
    row = catalog.entry(key)
    if row is None or row['kind'] != 'building':
        _answer(call, _t('cat_err_not_a_building'), alert=True)
        return
    _answer(call)
    _ask_number(call, _t('cat_ask_level', max=catalog.LEVEL_CEILING),
                lambda value: _open_new_level(call, key, value), minimum=1)


def _open_new_level(call, key, level):
    try:
        catalog.seed_level_cost(key, level)
    except catalog.CatalogError as exc:
        _bot.send_message(call.message.chat.id, _err(exc))
        return
    _log(call.from_user.id, 'asset_level', key, f'level {level} opened')
    _level_screen(call, key, level)


def _level_screen(call, key, level):
    """One level: what it costs, resource by resource, and what it yields."""
    if not _require_admin(call):
        return
    row = catalog.entry(key)
    if row is None or row['kind'] != 'building':
        _answer(call, _t('cat_err_not_a_building'), alert=True)
        return
    costs = catalog.level_costs(key, level)
    buttons = [types.InlineKeyboardButton(f"{_label(res)} — {costs.get(res, 0)}",
                                          callback_data=f'ap:clvc:{key}:{level}:{i}')
               for i, res in enumerate(catalog.keys('resource'))]
    tools = [types.InlineKeyboardButton(_t('btn_cat_level_output'),
                                        callback_data=f'ap:clvo:{key}:{level}'),
             types.InlineKeyboardButton(_t('btn_cat_level_clear'),
                                        callback_data=f'ap:clvd:{key}:{level}')]
    yields = _t('cat_lvl_output_own') if catalog.level_output_is_set(key, level) \
        else _t('cat_lvl_output_flat')
    _show(call, _t('cat_level_title', label=_esc(_label(key)), level=level,
                   cost=_level_cost_line(key, level),
                   out=catalog.level_output(key, level), source=yields,
                   total=catalog.output_at_level(key, level)),
          _markup(buttons, tools, back=f'ap:clv:{key}'))
    _answer(call)


def _ask_level_cost(call, key, level, index):
    if not _require_admin(call):
        return
    resource = _resource_index(index)
    if resource is None:
        _answer(call, _t('cat_err_bad_resource'), alert=True)
        return
    _answer(call)
    _ask_number(call, _t('cat_ask_level_cost', res=_label(resource), level=level),
                lambda value: _apply_level_cost(call, key, level, resource, value))


def _apply_level_cost(call, key, level, resource, value):
    try:
        catalog.set_level_cost(key, level, resource, value)
    except catalog.CatalogError as exc:
        _bot.send_message(call.message.chat.id, _err(exc))
        return
    _log(call.from_user.id, 'asset_level', key, f'L{level} {resource}={value}')
    _bot.send_message(call.message.chat.id, _t('cat_cost_set'))
    _level_screen(call, key, level)


def _ask_level_output(call, key, level):
    if not _require_admin(call):
        return
    _answer(call)
    _ask_number(call, _t('cat_ask_level_output', level=level),
                lambda value: _apply_level_output(call, key, level, value))


def _apply_level_output(call, key, level, value):
    try:
        catalog.set_level_output(key, level, value)
    except catalog.CatalogError as exc:
        _bot.send_message(call.message.chat.id, _err(exc))
        return
    _log(call.from_user.id, 'asset_level', key, f'L{level} yields {value}')
    _bot.send_message(call.message.chat.id, _t('cat_output_set'))
    _level_screen(call, key, level)


def _clear_level(call, key, level):
    """Hand one level back to the flat cost and the flat yield."""
    if not _require_admin(call):
        return
    try:
        catalog.clear_level_cost(key, level)
        catalog.clear_level_output(key, level)
    except catalog.CatalogError as exc:
        _answer(call, _err(exc), alert=True)
        return
    _log(call.from_user.id, 'asset_level', key, f'L{level} cleared')
    _answer(call, _t('cat_level_cleared', level=level))
    _level_list(call, key)


# ---------------------------------------------------------------------------
# The level ceiling
# ---------------------------------------------------------------------------


def _ask_max_level(call, key):
    if not _require_admin(call):
        return
    row = catalog.entry(key)
    if row is None or row['kind'] != 'building':
        _answer(call, _t('cat_err_not_a_building'), alert=True)
        return
    _answer(call)
    _ask_number(call, _t('cat_ask_max', current=row['max_level'] or _t('cat_max_none'),
                         ceiling=catalog.LEVEL_CEILING),
                lambda value: _apply_max_level(call, key, value))


def _apply_max_level(call, key, value):
    try:
        catalog.set_max_level(key, value)
    except catalog.CatalogError as exc:
        _bot.send_message(call.message.chat.id, _err(exc))
        return
    _log(call.from_user.id, 'asset_level', key, f'max level {value or "-"}')
    _bot.send_message(call.message.chat.id,
                      _t('cat_max_set', max=value) if value else _t('cat_max_lifted'))
    _entry_screen(call, key)


def _hide(call, key):
    if not _require_admin(call):
        return
    try:
        catalog.hide(key)
    except catalog.CatalogError as exc:
        _answer(call, _err(exc), alert=True)
        return
    _log(call.from_user.id, 'asset_hide', key, 'removed')
    _answer(call, _t('cat_hidden', label=_label(key)))
    _entry_screen(call, key)


def _unhide(call, key):
    if not _require_admin(call):
        return
    try:
        catalog.unhide(key)
    except catalog.CatalogError as exc:
        _answer(call, _err(exc), alert=True)
        return
    catalog.ensure_columns()
    _log(call.from_user.id, 'asset_hide', key, 'restored')
    _answer(call, _t('cat_unhidden', label=_label(key)))
    _entry_screen(call, key)


# ---------------------------------------------------------------------------
# Adding a type
# ---------------------------------------------------------------------------


def _add_start(call, kind):
    if not _require_admin(call):
        return
    if kind not in catalog.KINDS:
        _answer(call, _t('cat_err_bad_kind'), alert=True)
        return
    _wizards[call.from_user.id] = {'kind': kind, 'labels': {}}
    _answer(call)
    _bot.send_message(call.message.chat.id, _t('cat_ask_key'))
    _next_step(call.message, call.from_user.id, lambda msg: _add_key(call, msg))


def _add_key(call, message):
    key = (message.text or '').strip().lower()
    try:
        catalog.validate_new_key(key)
    except catalog.CatalogError as exc:
        _bot.send_message(message.chat.id, _err(exc))
        _next_step(message, call.from_user.id, lambda msg: _add_key(call, msg))
        return
    wizard = _wizards.get(call.from_user.id)
    if wizard is None:
        return
    wizard['key'] = key
    _collect_labels(message, call.from_user.id, wizard['labels'],
                    lambda labels: _add_after_labels(call, message))


def _collect_labels(message, user_id, store, done):
    """Ask for a display name in each language, then hand the map to `done`."""
    remaining = [lang for lang in catalog.LANGS if lang not in store]
    if not remaining:
        done(dict(store))
        return
    lang = remaining[0]
    _bot.send_message(message.chat.id, _t('cat_ask_label', lang=_t('cat_lang_' + lang)))

    def on_text(msg):
        store[lang] = (msg.text or '').strip() or lang
        _collect_labels(msg, user_id, store, done)

    _next_step(message, user_id, on_text)


def _add_after_labels(call, message):
    wizard = _wizards.get(call.from_user.id)
    if wizard is None:
        return
    _ask_number(call, _t('cat_ask_default'),
                lambda value: _add_after_default(call, message, value), chat_id=message.chat.id)


def _add_after_default(call, message, value):
    wizard = _wizards.get(call.from_user.id)
    if wizard is None:
        return
    wizard['default'] = value
    if wizard['kind'] != 'building':
        _finish_add(call, message)
        return
    buttons = [types.InlineKeyboardButton(_label(target),
                                          callback_data=f'ap:catprod:{target}')
               for target in catalog.keys('resource') + catalog.keys('unit')]
    buttons.append(types.InlineKeyboardButton(_t('btn_produces_none'),
                                              callback_data='ap:catprod:-'))
    _bot.send_message(message.chat.id, _t('cat_pick_produces'),
                      reply_markup=_markup(buttons, back=None))


def _add_produces(call, target):
    """Building wizards land here after picking what the building yields."""
    if not _require_admin(call):
        return
    wizard = _wizards.get(call.from_user.id)
    if wizard is None:
        _answer(call, STRINGS[_lang]['err_generic'], alert=True)
        return
    if target == '-':
        wizard['produces'] = ''
        wizard['output'] = 0
        _answer(call)
        _finish_add(call, call.message)
        return
    wizard['produces'] = target
    _answer(call)
    _ask_number(call, _t('cat_ask_output'),
                lambda value: _add_after_output(call, value))


def _add_after_output(call, value):
    wizard = _wizards.get(call.from_user.id)
    if wizard is None:
        return
    wizard['output'] = value
    _finish_add(call, call.message)


def _finish_add(call, message):
    wizard = _wizards.pop(call.from_user.id, None)
    if wizard is None:
        return
    try:
        catalog.add(wizard['key'], wizard['kind'], wizard['labels'],
                    default_value=wizard.get('default', 0),
                    produces=wizard.get('produces', ''),
                    output=wizard.get('output', 0),
                    tradeable=1 if wizard['kind'] == 'resource' else 0)
    except catalog.CatalogError as exc:
        _bot.send_message(message.chat.id, _err(exc))
        return
    _log(call.from_user.id, 'asset_add', wizard['key'], wizard['kind'])
    _bot.send_message(message.chat.id, _t('cat_added', label=_label(wizard['key'])))
    _entry_screen(call, wizard['key'])


# ---------------------------------------------------------------------------
# Shared input helper
# ---------------------------------------------------------------------------


def _ask_number(call, prompt, done, chat_id=None, minimum=0):
    """Ask for an integer of at least `minimum`, re-asking until one arrives."""
    chat_id = call.message.chat.id if chat_id is None else chat_id
    _bot.send_message(chat_id, prompt)

    def on_text(message):
        try:
            value = int((message.text or '').strip())
            if value < minimum:
                raise ValueError
        except ValueError:
            _bot.send_message(chat_id, STRINGS[_lang]['cat_bad_number'])
            _next_step(message, call.from_user.id, on_text)
            return
        done(value)

    _next_step(call.message, call.from_user.id, on_text)
