# -*- coding: utf-8 -*-
"""Panel screens for editing the trade world.

Split out of trade_system so that file stays about trading rather than about
geography. It receives its helpers through init() instead of importing
trade_system, so the dependency runs one way only, and it carries its own
strings so the trade STRINGS table does not grow another screenful.

Callback space: everything under 'trd:m…', routed here by trade_system.

Editing is admin-level. Deleting a node or an edge is owner-level: it is the
one thing here that can strand a shipment or cut a country off the map.
"""

import html

from telebot import types

import trade_map

_bot = None
_lang = 'fa'
_require_admin = None
_require_owner = None
_answer = None
_next_step = None
_log = None
_toll = None
_set_toll = None
_owner_label = None

PAGE_SIZE = 8

# The callbacks this module answers to. trade_system dispatches on membership
# rather than on a prefix, because 'm' and 'menu' are its own trade-wizard ops.
OPS = frozenset({
    'map', 'mn', 'mnd', 'mrn', 'mkd', 'mks', 'mhm', 'mtl', 'mdn', 'mdnc',
    'me', 'med', 'meu', 'mem', 'mde', 'mdec',
    'man', 'mank', 'manh', 'mae', 'mae1', 'mae2',
})

# in-progress "add a node" wizards, keyed by user id
_wizards = {}


def init(bot, lang, require_admin, require_owner, answer, next_step, log,
         toll, set_toll, owner_label):
    global _bot, _lang, _require_admin, _require_owner, _answer, _next_step, _log
    global _toll, _set_toll, _owner_label
    _bot = bot
    _lang = lang if lang in STRINGS else 'en'
    _require_admin = require_admin
    _require_owner = require_owner
    _answer = answer
    _next_step = next_step
    _log = log
    _toll = toll
    _set_toll = set_toll
    _owner_label = owner_label


def _t(string_id, **kw):
    text = STRINGS[_lang][string_id]
    return text.format(**kw) if kw else text


def _esc(text):
    return html.escape(str(text), quote=False)


def _err(exc):
    return STRINGS[_lang].get('map_err_' + str(exc), STRINGS[_lang]['map_err_generic'])


def _name(nid):
    return trade_map.name(nid, _lang)


def _send(chat_id, text, markup=None):
    _bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')


def _kind_label(kind):
    return STRINGS[_lang].get('map_kind_' + kind, kind)


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def handle(call, parts):
    """parts is call.data.split(':'); parts[1] always starts with 'm'."""
    op = parts[1]
    if op == 'map':
        _home(call)
    elif op == 'mn':
        _node_list(call, parts[2], int(parts[3]))
    elif op == 'mnd':
        _node_screen(call, parts[2])
    elif op == 'mrn':
        _ask_rename(call, parts[2])
    elif op == 'mkd':
        _pick_kind(call, parts[2])
    elif op == 'mks':
        _set_kind(call, parts[2], parts[3])
    elif op == 'mhm':
        _toggle_home(call, parts[2])
    elif op == 'mtl':
        _ask_toll(call, parts[2])
    elif op == 'mdn':
        _node_delete_confirm(call, parts[2])
    elif op == 'mdnc':
        _node_delete_apply(call, parts[2])
    elif op == 'me':
        _edge_list(call, parts[2], int(parts[3]))
    elif op == 'med':
        _edge_screen(call, parts[2], parts[3], parts[4])
    elif op == 'meu':
        _ask_units(call, parts[2], parts[3], parts[4])
    elif op == 'mem':
        _ask_minutes(call, parts[2], parts[3], parts[4])
    elif op == 'mde':
        _edge_delete_confirm(call, parts[2], parts[3], parts[4])
    elif op == 'mdec':
        _edge_delete_apply(call, parts[2], parts[3], parts[4])
    elif op == 'man':
        _add_node_start(call, parts[2])
    elif op == 'mank':
        _add_node_kind(call, parts[2])
    elif op == 'manh':
        _add_node_home(call, parts[2])
    elif op == 'mae':
        _add_edge_first(call, parts[2])
    elif op == 'mae1':
        _add_edge_second(call, parts[2], parts[3])
    elif op == 'mae2':
        _add_edge_units(call, parts[2], parts[3], parts[4])
    else:
        _answer(call, _t('map_err_generic'))


# ---------------------------------------------------------------------------
# Browsing
# ---------------------------------------------------------------------------


def _home(call):
    if not _require_admin(call):
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for mode in trade_map.MODES:
        markup.add(types.InlineKeyboardButton(
            _t('map_btn_mode_' + mode, n=len(trade_map.nodes(mode))),
            callback_data=f'trd:mn:{mode}:0'))
    _send(call.message.chat.id, _t('map_title'), markup)
    _answer(call)


def _page(items, page):
    pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    return items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE], page, pages


def _nav(markup, page, pages, prefix):
    row = []
    if page > 0:
        row.append(types.InlineKeyboardButton(_t('map_btn_prev'),
                                              callback_data=f'{prefix}{page - 1}'))
    if page < pages - 1:
        row.append(types.InlineKeyboardButton(_t('map_btn_next'),
                                              callback_data=f'{prefix}{page + 1}'))
    if row:
        markup.add(*row)


def _node_list(call, mode, page):
    if not _require_admin(call):
        return
    if mode not in trade_map.MODES:
        _answer(call, _t('map_err_bad_mode'), alert=True)
        return
    nids = list(trade_map.nodes(mode))
    window, page, pages = _page(nids, page)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for nid in window:
        markup.add(types.InlineKeyboardButton(f"{_name(nid)}", callback_data=f'trd:mnd:{nid}'))
    _nav(markup, page, pages, f'trd:mn:{mode}:')
    markup.add(types.InlineKeyboardButton(_t('map_btn_add_node'),
                                          callback_data=f'trd:man:{mode}'),
               types.InlineKeyboardButton(_t('map_btn_edges'),
                                          callback_data=f'trd:me:{mode}:0'))
    _send(call.message.chat.id,
          _t('map_nodes_title', mode=_t('map_mode_' + mode), p=page + 1, n=pages), markup)
    _answer(call)


def _node_screen(call, nid):
    if not _require_admin(call):
        return
    mode = trade_map.mode_of(nid)
    if mode is None:
        _answer(call, _t('map_err_unknown_node'), alert=True)
        return
    row = trade_map.node(mode, nid)
    links = trade_map.edges_of(nid)
    neighbours = ' · '.join(_name(b if a == nid else a) for a, b in
                            ((e['a'], e['b']) for e in links)) or _t('map_no_edges')
    owner = _owner_label(nid) or _t('map_no_owner')

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(_t('map_btn_rename'), callback_data=f'trd:mrn:{nid}'),
               types.InlineKeyboardButton(_t('map_btn_kind'), callback_data=f'trd:mkd:{nid}'),
               types.InlineKeyboardButton(_t('map_btn_home'), callback_data=f'trd:mhm:{nid}'),
               types.InlineKeyboardButton(_t('map_btn_toll'), callback_data=f'trd:mtl:{nid}'))
    # Only a chokepoint can be owned, and trd:on refuses anything else — so
    # offering the button elsewhere would just be a dead end.
    if row['kind'] in trade_map.CHOKEPOINT_KINDS:
        markup.add(types.InlineKeyboardButton(_t('map_btn_owner'), callback_data=f'trd:on:{nid}'))
    markup.add(types.InlineKeyboardButton(_t('map_btn_del_node'), callback_data=f'trd:mdn:{nid}'),
               types.InlineKeyboardButton(_t('map_btn_back_nodes'),
                                          callback_data=f'trd:mn:{mode}:0'))
    _send(call.message.chat.id,
          _t('map_node', name=_esc(_name(nid)), id=_esc(nid), mode=_t('map_mode_' + mode),
             kind=_kind_label(row['kind']),
             home=_t('map_yes') if row['home'] else _t('map_no'),
             toll=_toll(nid), owner=_esc(owner), neighbours=_esc(neighbours)),
          markup)
    _answer(call)


def _edge_list(call, mode, page):
    if not _require_admin(call):
        return
    if mode not in trade_map.MODES:
        _answer(call, _t('map_err_bad_mode'), alert=True)
        return
    rows = trade_map.edges(mode)
    window, page, pages = _page(rows, page)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for a, b, units, minutes in window:
        mark = ' ⏱' if minutes else ''
        markup.add(types.InlineKeyboardButton(f"{_name(a)} — {_name(b)} ({units}){mark}",
                                              callback_data=f'trd:med:{mode}:{a}:{b}'))
    _nav(markup, page, pages, f'trd:me:{mode}:')
    markup.add(types.InlineKeyboardButton(_t('map_btn_add_edge'),
                                          callback_data=f'trd:mae:{mode}'),
               types.InlineKeyboardButton(_t('map_btn_back_nodes'),
                                          callback_data=f'trd:mn:{mode}:0'))
    _send(call.message.chat.id,
          _t('map_edges_title', mode=_t('map_mode_' + mode), p=page + 1, n=pages), markup)
    _answer(call)


def _edge_screen(call, mode, a, b):
    if not _require_admin(call):
        return
    found = trade_map.leg(mode, a, b)
    if found is None:
        _answer(call, _t('map_err_no_edge'), alert=True)
        return
    units, minutes = found
    timing = (_t('map_minutes_exact', m=minutes) if minutes
              else _t('map_minutes_auto', units=units))
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(_t('map_btn_units'),
                                          callback_data=f'trd:meu:{mode}:{a}:{b}'),
               types.InlineKeyboardButton(_t('map_btn_minutes'),
                                          callback_data=f'trd:mem:{mode}:{a}:{b}'),
               types.InlineKeyboardButton(_t('map_btn_del_edge'),
                                          callback_data=f'trd:mde:{mode}:{a}:{b}'),
               types.InlineKeyboardButton(_t('map_btn_back_edges'),
                                          callback_data=f'trd:me:{mode}:0'))
    _send(call.message.chat.id,
          _t('map_edge', a=_esc(_name(a)), b=_esc(_name(b)), units=units, timing=timing),
          markup)
    _answer(call)


# ---------------------------------------------------------------------------
# Editing a node
# ---------------------------------------------------------------------------


def _ask_rename(call, nid):
    if not _require_admin(call):
        return
    if trade_map.mode_of(nid) is None:
        _answer(call, _t('map_err_unknown_node'), alert=True)
        return
    _answer(call)
    _collect_names(call.message, call.from_user.id, {},
                   lambda names: _apply_rename(call, nid, names))


def _apply_rename(call, nid, names):
    trade_map.set_labels(nid, names)
    _log(call.from_user.id, 'map_node_edit', nid, 'renamed')
    _send(call.message.chat.id, _t('map_renamed'))
    _node_screen(call, nid)


def _collect_names(message, user_id, store, done):
    """Ask for a display name in each language, then hand the map to `done`."""
    remaining = [lang for lang in trade_map.LANGS if lang not in store]
    if not remaining:
        done(dict(store))
        return
    lang = remaining[0]
    _bot.send_message(message.chat.id, _t('map_ask_name', lang=_t('map_lang_' + lang)))

    def on_text(msg):
        store[lang] = (msg.text or '').strip() or lang
        _collect_names(msg, user_id, store, done)

    _next_step(message, user_id, on_text)


def _pick_kind(call, nid):
    if not _require_admin(call):
        return
    mode = trade_map.mode_of(nid)
    if mode is None:
        _answer(call, _t('map_err_unknown_node'), alert=True)
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*[types.InlineKeyboardButton(_kind_label(kind),
                                            callback_data=f'trd:mks:{nid}:{kind}')
                 for kind in trade_map.KINDS[mode]])
    _send(call.message.chat.id, _t('map_pick_kind'), markup)
    _answer(call)


def _set_kind(call, nid, kind):
    if not _require_admin(call):
        return
    try:
        trade_map.set_kind(nid, kind)
    except trade_map.MapError as exc:
        _answer(call, _err(exc), alert=True)
        return
    _log(call.from_user.id, 'map_node_edit', nid, f'kind={kind}')
    _answer(call, _t('map_saved'))
    _node_screen(call, nid)


def _toggle_home(call, nid):
    if not _require_admin(call):
        return
    mode = trade_map.mode_of(nid)
    if mode is None:
        _answer(call, _t('map_err_unknown_node'), alert=True)
        return
    new_state = not trade_map.node(mode, nid)['home']
    trade_map.set_home(nid, new_state)
    _log(call.from_user.id, 'map_node_edit', nid, f'home={int(new_state)}')
    _answer(call, _t('map_home_on') if new_state else _t('map_home_off'))
    _node_screen(call, nid)


def _ask_toll(call, nid):
    if not _require_admin(call):
        return
    if trade_map.mode_of(nid) is None:
        _answer(call, _t('map_err_unknown_node'), alert=True)
        return
    _answer(call)
    _ask_number(call, _t('map_ask_toll', name=_name(nid), val=_toll(nid)),
                lambda value: _apply_toll(call, nid, value))


def _apply_toll(call, nid, value):
    _set_toll(nid, value)
    _log(call.from_user.id, 'map_node_edit', nid, f'toll={value}')
    _send(call.message.chat.id, _t('map_toll_set', name=_esc(_name(nid)), val=value))
    _node_screen(call, nid)


def _node_delete_confirm(call, nid):
    if not _require_owner(call):
        return
    mode = trade_map.mode_of(nid)
    if mode is None:
        _answer(call, _t('map_err_unknown_node'), alert=True)
        return
    links = len(trade_map.edges_of(nid))
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(_t('map_btn_del_yes'), callback_data=f'trd:mdnc:{nid}'),
               types.InlineKeyboardButton(_t('map_btn_back_node'),
                                          callback_data=f'trd:mnd:{nid}'))
    _send(call.message.chat.id,
          _t('map_del_node_confirm', name=_esc(_name(nid)), id=_esc(nid), n=links), markup)
    _answer(call)


def _node_delete_apply(call, nid):
    if not _require_owner(call):
        return
    mode = trade_map.mode_of(nid)
    label = _name(nid)
    try:
        trade_map.remove_node(nid)
    except trade_map.MapError as exc:
        _answer(call, _err(exc), alert=True)
        return
    _log(call.from_user.id, 'map_node_remove', nid, label)
    _send(call.message.chat.id, _t('map_node_deleted', name=_esc(label)))
    _node_list(call, mode or trade_map.MODES[0], 0)


# ---------------------------------------------------------------------------
# Editing an edge
# ---------------------------------------------------------------------------


def _ask_units(call, mode, a, b):
    if not _require_admin(call):
        return
    if trade_map.leg(mode, a, b) is None:
        _answer(call, _t('map_err_no_edge'), alert=True)
        return
    _answer(call)
    _ask_number(call, _t('map_ask_units'),
                lambda value: _apply_edge(call, mode, a, b, units=value), minimum=1)


def _ask_minutes(call, mode, a, b):
    if not _require_admin(call):
        return
    if trade_map.leg(mode, a, b) is None:
        _answer(call, _t('map_err_no_edge'), alert=True)
        return
    _answer(call)
    _ask_number(call, _t('map_ask_minutes'),
                lambda value: _apply_edge(call, mode, a, b, minutes=value))


def _apply_edge(call, mode, a, b, units=None, minutes=None):
    try:
        trade_map.set_edge(mode, a, b, units=units, minutes=minutes)
    except trade_map.MapError as exc:
        _send(call.message.chat.id, _err(exc))
        return
    detail = f'units={units}' if units is not None else f'minutes={minutes}'
    _log(call.from_user.id, 'map_edge_edit', f'{a}-{b}', detail)
    _send(call.message.chat.id, _t('map_saved'))
    _edge_screen(call, mode, a, b)


def _edge_delete_confirm(call, mode, a, b):
    if not _require_owner(call):
        return
    if trade_map.leg(mode, a, b) is None:
        _answer(call, _t('map_err_no_edge'), alert=True)
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(_t('map_btn_del_yes'),
                                          callback_data=f'trd:mdec:{mode}:{a}:{b}'),
               types.InlineKeyboardButton(_t('map_btn_back_edges'),
                                          callback_data=f'trd:me:{mode}:0'))
    _send(call.message.chat.id,
          _t('map_del_edge_confirm', a=_esc(_name(a)), b=_esc(_name(b))), markup)
    _answer(call)


def _edge_delete_apply(call, mode, a, b):
    if not _require_owner(call):
        return
    names = (_name(a), _name(b))
    try:
        trade_map.remove_edge(mode, a, b)
    except trade_map.MapError as exc:
        _answer(call, _err(exc), alert=True)
        return
    _log(call.from_user.id, 'map_edge_remove', f'{a}-{b}', ' — '.join(names))
    _send(call.message.chat.id, _t('map_edge_deleted', a=_esc(names[0]), b=_esc(names[1])))
    _edge_list(call, mode, 0)


# ---------------------------------------------------------------------------
# Adding a node
# ---------------------------------------------------------------------------


def _add_node_start(call, mode):
    if not _require_admin(call):
        return
    if mode not in trade_map.MODES:
        _answer(call, _t('map_err_bad_mode'), alert=True)
        return
    _wizards[call.from_user.id] = {'mode': mode, 'names': {}}
    _answer(call)
    _bot.send_message(call.message.chat.id, _t('map_ask_id'))
    _next_step(call.message, call.from_user.id, lambda msg: _add_node_id(call, msg))


def _add_node_id(call, message):
    nid = (message.text or '').strip().lower()
    wizard = _wizards.get(call.from_user.id)
    if wizard is None:
        return
    try:
        trade_map.check_new_id(nid)
    except trade_map.MapError as exc:
        _bot.send_message(message.chat.id, _err(exc))
        _next_step(message, call.from_user.id, lambda msg: _add_node_id(call, msg))
        return
    wizard['id'] = nid
    _collect_names(message, call.from_user.id, wizard['names'],
                   lambda names: _add_node_after_names(call, message))


def _add_node_after_names(call, message):
    wizard = _wizards.get(call.from_user.id)
    if wizard is None:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*[types.InlineKeyboardButton(_kind_label(kind), callback_data=f'trd:mank:{kind}')
                 for kind in trade_map.KINDS[wizard['mode']]])
    _send(message.chat.id, _t('map_pick_kind'), markup)


def _add_node_kind(call, kind):
    if not _require_admin(call):
        return
    wizard = _wizards.get(call.from_user.id)
    if wizard is None:
        _answer(call, _t('map_err_generic'), alert=True)
        return
    if kind not in trade_map.KINDS[wizard['mode']]:
        _answer(call, _t('map_err_bad_kind'), alert=True)
        return
    wizard['kind'] = kind
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(_t('map_yes'), callback_data='trd:manh:1'),
               types.InlineKeyboardButton(_t('map_no'), callback_data='trd:manh:0'))
    _answer(call)
    _send(call.message.chat.id, _t('map_ask_home'), markup)


def _add_node_home(call, flag):
    if not _require_admin(call):
        return
    wizard = _wizards.pop(call.from_user.id, None)
    if wizard is None:
        _answer(call, _t('map_err_generic'), alert=True)
        return
    try:
        trade_map.add_node(wizard['mode'], wizard['id'], wizard['kind'],
                           flag == '1', wizard['names'])
    except trade_map.MapError as exc:
        _answer(call, _err(exc), alert=True)
        return
    _log(call.from_user.id, 'map_node_add', wizard['id'], wizard['kind'])
    _answer(call)
    _send(call.message.chat.id, _t('map_node_added', name=_esc(_name(wizard['id']))))
    _node_screen(call, wizard['id'])


# ---------------------------------------------------------------------------
# Adding an edge
# ---------------------------------------------------------------------------


def _add_edge_first(call, mode):
    if not _require_admin(call):
        return
    if mode not in trade_map.MODES:
        _answer(call, _t('map_err_bad_mode'), alert=True)
        return
    _pick_node(call, mode, _t('map_pick_first'), lambda nid: f'trd:mae1:{mode}:{nid}')


def _add_edge_second(call, mode, a):
    if not _require_admin(call):
        return
    _pick_node(call, mode, _t('map_pick_second', a=_name(a)),
               lambda nid: f'trd:mae2:{mode}:{a}:{nid}', skip=a)


def _pick_node(call, mode, prompt, target, skip=None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*[types.InlineKeyboardButton(_name(nid), callback_data=target(nid))
                 for nid in trade_map.nodes(mode) if nid != skip])
    _send(call.message.chat.id, prompt, markup)
    _answer(call)


def _add_edge_units(call, mode, a, b):
    if not _require_admin(call):
        return
    _answer(call)
    _ask_number(call, _t('map_ask_units'),
                lambda value: _finish_add_edge(call, mode, a, b, value), minimum=1)


def _finish_add_edge(call, mode, a, b, units):
    try:
        trade_map.add_edge(mode, a, b, units)
    except trade_map.MapError as exc:
        _send(call.message.chat.id, _err(exc))
        return
    _log(call.from_user.id, 'map_edge_add', f'{a}-{b}', f'units={units}')
    _send(call.message.chat.id, _t('map_edge_added', a=_esc(_name(a)), b=_esc(_name(b))))
    _edge_screen(call, mode, a, b)


# ---------------------------------------------------------------------------
# Shared input helper
# ---------------------------------------------------------------------------


def _ask_number(call, prompt, done, minimum=0):
    """Ask for an integer no smaller than `minimum`, re-asking until one arrives."""
    chat_id = call.message.chat.id
    _bot.send_message(chat_id, prompt)

    def on_text(message):
        try:
            value = int((message.text or '').strip())
            if value < minimum:
                raise ValueError
        except ValueError:
            _bot.send_message(chat_id, _t('map_bad_number', min=minimum))
            _next_step(message, call.from_user.id, on_text)
            return
        done(value)

    _next_step(call.message, call.from_user.id, on_text)


# ---------------------------------------------------------------------------
# Strings
# ---------------------------------------------------------------------------

STRINGS = {
    'fa': {
        'map_title': "🗺 ویرایش نقشه تجارت — کدام نقشه؟",
        'map_btn_mode_sea': "🚢 نقشه دریایی ({n} جا)",
        'map_btn_mode_land': "🐫 نقشه زمینی ({n} جا)",
        'map_mode_sea': "دریایی",
        'map_mode_land': "زمینی",
        'map_nodes_title': "🗺 جاهای نقشه {mode} (صفحه {p} از {n}) — برای ویرایش روی یکی بزنید:",
        'map_edges_title': "🛣 مسیرهای نقشه {mode} (صفحه {p} از {n}) — برای ویرایش روی یکی بزنید:",
        'map_node': "📍 <b>{name}</b>\n<blockquote>🔑 شناسه: <code>{id}</code>\n"
                    "🗺 نقشه: {mode}\n📁 نوع: {kind}\n🏠 محل استقرار کشور: {home}\n"
                    "🪙 عوارض: {toll}\n👑 مالک: {owner}\n🛣 مسیرها: {neighbours}</blockquote>",
        'map_edge': "🛣 <b>{a} — {b}</b>\n<blockquote>📏 طول: {units}\n⏱ زمان: {timing}"
                    "</blockquote>\n\nطول، هزینه و انتخاب مسیر را تعیین می‌کند؛ زمان فقط "
                    "مدت سفر را عوض می‌کند.",
        'map_minutes_auto': "خودکار ({units} × نرخ هر واحد)",
        'map_minutes_exact': "{m} دقیقه (دستی)",
        'map_no_edges': "به جایی وصل نیست",
        'map_no_owner': "بدون مالک",
        'map_yes': "بله",
        'map_no': "خیر",
        'map_btn_prev': "➡️ قبلی",
        'map_btn_next': "بعدی ⬅️",
        'map_btn_rename': "✏️ تغییر نام",
        'map_btn_kind': "📁 نوع",
        'map_btn_home': "🏠 محل استقرار",
        'map_btn_toll': "🪙 عوارض",
        'map_btn_owner': "👑 مالک",
        'map_btn_del_node': "❌ حذف این جا",
        'map_btn_units': "📏 طول",
        'map_btn_minutes': "⏱ زمان سفر",
        'map_btn_del_edge': "❌ حذف این مسیر",
        'map_btn_del_yes': "🔥 بله، حذف کن",
        'map_btn_add_node': "➕ افزودن جای جدید",
        'map_btn_add_edge': "➕ افزودن مسیر جدید",
        'map_btn_edges': "🛣 مسیرها",
        'map_btn_back_nodes': "🔙 فهرست جاها",
        'map_btn_back_edges': "🔙 فهرست مسیرها",
        'map_btn_back_node': "🔙 بازگشت",
        'map_pick_kind': "نوع این جا را انتخاب کنید:",
        'map_ask_home': "آیا کشورها می‌توانند اینجا مستقر شوند؟",
        'map_ask_id': "شناسه انگلیسی جای جدید را بفرستید (حروف کوچک، مثل azov):",
        'map_ask_name': "نام نمایشی به {lang} را بفرستید:",
        'map_ask_toll': "عوارض عبور از {name} چقدر باشد؟ (فعلی: {val}، صفر یعنی رایگان)",
        'map_ask_units': "طول این مسیر چند واحد باشد؟ (هزینه از روی همین حساب می‌شود)",
        'map_ask_minutes': "زمان سفر این مسیر چند دقیقه باشد؟ (صفر یعنی خودکار از روی طول)",
        'map_pick_first': "مسیر از کجا شروع شود؟",
        'map_pick_second': "مسیر از {a} به کجا برود؟",
        'map_bad_number': "مقدار معتبر نیست. عددی صحیح و حداقل {min} بفرستید.",
        'map_lang_fa': "فارسی",
        'map_lang_en': "انگلیسی",
        'map_lang_tr': "ترکی",
        'map_kind_ocean': "🌊 اقیانوس",
        'map_kind_sea': "🌊 دریا",
        'map_kind_strait': "⚓️ تنگه",
        'map_kind_canal': "🚧 کانال",
        'map_kind_cape': "🏔 دماغه",
        'map_kind_region': "🗺 منطقه",
        'map_kind_pass': "🏔 گذرگاه",
        'map_saved': "✅ ذخیره شد.",
        'map_renamed': "✅ نام‌ها به‌روزرسانی شد.",
        'map_home_on': "🏠 کشورها می‌توانند اینجا مستقر شوند.",
        'map_home_off': "🚫 دیگر نمی‌توان اینجا مستقر شد.",
        'map_toll_set': "🪙 عوارض {name} روی {val} تنظیم شد.",
        'map_node_added': "✅ «{name}» به نقشه اضافه شد. حالا با «افزودن مسیر» وصلش کنید.",
        'map_edge_added': "✅ مسیر {a} — {b} اضافه شد.",
        'map_node_deleted': "🔥 «{name}» از نقشه حذف شد.",
        'map_edge_deleted': "🔥 مسیر {a} — {b} حذف شد.",
        'map_del_node_confirm': "🔥 <b>حذف «{name}»</b>\n<blockquote>شناسه <code>{id}</code> و "
                                "{n} مسیری که به آن وصل است حذف می‌شوند.\n\n"
                                "⚠️ اگر کشوری اینجا مستقر باشد، باید محل جدیدی برایش تعیین "
                                "کنید.</blockquote>",
        'map_del_edge_confirm': "🔥 مسیر <b>{a} — {b}</b> حذف شود؟ محموله‌ها باید راه دیگری "
                                "پیدا کنند.",
        'map_err_generic': "❌ خطایی رخ داد.",
        'map_err_bad_id': "❌ شناسه نامعتبر است. فقط حروف کوچک انگلیسی، عدد و زیرخط؛ "
                          "با حرف شروع شود و بین ۲ تا ۱۶ کاراکتر باشد.",
        'map_err_bad_kind': "❌ این نوع برای این نقشه معتبر نیست.",
        'map_err_bad_mode': "❌ نقشه نامعتبر است.",
        'map_err_exists': "❌ جایی با این شناسه از قبل هست.",
        'map_err_unknown_node': "❌ چنین جایی روی نقشه نیست.",
        'map_err_in_transit': "❌ همین حالا محموله‌ای از اینجا عبور می‌کند. تا رسیدن آن "
                              "نمی‌توان حذفش کرد.",
        'map_err_guard_unavailable': "❌ وضعیت محموله‌های در راه مشخص نشد، پس حذف انجام نشد.",
        'map_err_self_edge': "❌ یک جا را نمی‌توان به خودش وصل کرد.",
        'map_err_mode_mismatch': "❌ نمی‌توان نقشه دریایی و زمینی را به هم وصل کرد.",
        'map_err_bad_units': "❌ طول مسیر باید حداقل ۱ باشد.",
        'map_err_edge_exists': "❌ این دو از قبل به هم وصل‌اند.",
        'map_err_no_edge': "❌ چنین مسیری وجود ندارد.",
    },
    'en': {
        'map_title': "🗺 Edit the trade map — which one?",
        'map_btn_mode_sea': "🚢 Sea map ({n} places)",
        'map_btn_mode_land': "🐫 Land map ({n} places)",
        'map_mode_sea': "sea",
        'map_mode_land': "land",
        'map_nodes_title': "🗺 Places on the {mode} map (page {p} of {n}) — tap one to edit:",
        'map_edges_title': "🛣 Routes on the {mode} map (page {p} of {n}) — tap one to edit:",
        'map_node': "📍 <b>{name}</b>\n<blockquote>🔑 Id: <code>{id}</code>\n"
                    "🗺 Map: {mode}\n📁 Kind: {kind}\n🏠 Countries can be based here: {home}\n"
                    "🪙 Toll: {toll}\n👑 Owner: {owner}\n🛣 Routes: {neighbours}</blockquote>",
        'map_edge': "🛣 <b>{a} — {b}</b>\n<blockquote>📏 Length: {units}\n⏱ Time: {timing}"
                    "</blockquote>\n\nLength sets the fee and which route is cheapest; time "
                    "only changes how long the journey takes.",
        'map_minutes_auto': "automatic ({units} × the per-unit rate)",
        'map_minutes_exact': "{m} minutes (set by hand)",
        'map_no_edges': "connected to nothing",
        'map_no_owner': "nobody",
        'map_yes': "Yes",
        'map_no': "No",
        'map_btn_prev': "⬅️ Previous",
        'map_btn_next': "Next ➡️",
        'map_btn_rename': "✏️ Rename",
        'map_btn_kind': "📁 Kind",
        'map_btn_home': "🏠 Can be based here",
        'map_btn_toll': "🪙 Toll",
        'map_btn_owner': "👑 Owner",
        'map_btn_del_node': "❌ Delete this place",
        'map_btn_units': "📏 Length",
        'map_btn_minutes': "⏱ Travel time",
        'map_btn_del_edge': "❌ Delete this route",
        'map_btn_del_yes': "🔥 Yes, delete it",
        'map_btn_add_node': "➕ Add a place",
        'map_btn_add_edge': "➕ Add a route",
        'map_btn_edges': "🛣 Routes",
        'map_btn_back_nodes': "🔙 Places",
        'map_btn_back_edges': "🔙 Routes",
        'map_btn_back_node': "🔙 Back",
        'map_pick_kind': "What kind of place is it?",
        'map_ask_home': "Can countries be based here?",
        'map_ask_id': "Send the new place's id (lowercase letters, e.g. azov):",
        'map_ask_name': "Send its display name in {lang}:",
        'map_ask_toll': "What should passing {name} cost? (currently {val}, 0 means free)",
        'map_ask_units': "How long is this route, in units? (the fee is worked out from this)",
        'map_ask_minutes': "How many minutes should this route take? (0 derives it from length)",
        'map_pick_first': "Where does the route start?",
        'map_pick_second': "Where does the route go from {a}?",
        'map_bad_number': "That is not a valid value. Send a whole number of at least {min}.",
        'map_lang_fa': "Persian",
        'map_lang_en': "English",
        'map_lang_tr': "Turkish",
        'map_kind_ocean': "🌊 Ocean",
        'map_kind_sea': "🌊 Sea",
        'map_kind_strait': "⚓️ Strait",
        'map_kind_canal': "🚧 Canal",
        'map_kind_cape': "🏔 Cape",
        'map_kind_region': "🗺 Region",
        'map_kind_pass': "🏔 Pass",
        'map_saved': "✅ Saved.",
        'map_renamed': "✅ Names updated.",
        'map_home_on': "🏠 Countries can be based here now.",
        'map_home_off': "🚫 Countries can no longer be based here.",
        'map_toll_set': "🪙 Passing {name} now costs {val}.",
        'map_node_added': "✅ “{name}” is on the map. Connect it with “Add a route”.",
        'map_edge_added': "✅ Route {a} — {b} added.",
        'map_node_deleted': "🔥 “{name}” was removed from the map.",
        'map_edge_deleted': "🔥 Route {a} — {b} was removed.",
        'map_del_node_confirm': "🔥 <b>Delete “{name}”</b>\n<blockquote>The id <code>{id}</code> "
                                "and the {n} routes touching it will be removed.\n\n"
                                "⚠️ Any country based here will need a new home.</blockquote>",
        'map_del_edge_confirm': "🔥 Delete the route <b>{a} — {b}</b>? Shipments will have to "
                                "find another way round.",
        'map_err_generic': "❌ Something went wrong.",
        'map_err_bad_id': "❌ Invalid id. Lowercase letters, digits and underscores only; "
                          "it must start with a letter and be 2 to 16 characters.",
        'map_err_bad_kind': "❌ That kind does not belong on this map.",
        'map_err_bad_mode': "❌ No such map.",
        'map_err_exists': "❌ A place with that id already exists.",
        'map_err_unknown_node': "❌ There is no such place on the map.",
        'map_err_in_transit': "❌ A shipment is passing through here right now. It cannot be "
                              "deleted until that trade arrives.",
        'map_err_guard_unavailable': "❌ Could not check what is in transit, so nothing was "
                                     "deleted.",
        'map_err_self_edge': "❌ A place cannot connect to itself.",
        'map_err_mode_mismatch': "❌ The sea map and the land map cannot be joined.",
        'map_err_bad_units': "❌ A route must be at least 1 unit long.",
        'map_err_edge_exists': "❌ Those two are already connected.",
        'map_err_no_edge': "❌ There is no such route.",
    },
    'tr': {
        'map_title': "🗺 Ticaret haritasını düzenle — hangisi?",
        'map_btn_mode_sea': "🚢 Deniz haritası ({n} yer)",
        'map_btn_mode_land': "🐫 Kara haritası ({n} yer)",
        'map_mode_sea': "deniz",
        'map_mode_land': "kara",
        'map_nodes_title': "🗺 {mode} haritasındaki yerler ({p}/{n}. sayfa) — düzenlemek için "
                           "birine dokunun:",
        'map_edges_title': "🛣 {mode} haritasındaki yollar ({p}/{n}. sayfa) — düzenlemek için "
                           "birine dokunun:",
        'map_node': "📍 <b>{name}</b>\n<blockquote>🔑 Kimlik: <code>{id}</code>\n"
                    "🗺 Harita: {mode}\n📁 Tür: {kind}\n🏠 Ülkeler burada konuşlanabilir: {home}\n"
                    "🪙 Geçiş ücreti: {toll}\n👑 Sahip: {owner}\n🛣 Yollar: {neighbours}"
                    "</blockquote>",
        'map_edge': "🛣 <b>{a} — {b}</b>\n<blockquote>📏 Uzunluk: {units}\n⏱ Süre: {timing}"
                    "</blockquote>\n\nUzunluk ücreti ve en ucuz yolu belirler; süre yalnızca "
                    "yolculuğun ne kadar süreceğini değiştirir.",
        'map_minutes_auto': "otomatik ({units} × birim oranı)",
        'map_minutes_exact': "{m} dakika (elle ayarlandı)",
        'map_no_edges': "hiçbir yere bağlı değil",
        'map_no_owner': "yok",
        'map_yes': "Evet",
        'map_no': "Hayır",
        'map_btn_prev': "⬅️ Önceki",
        'map_btn_next': "Sonraki ➡️",
        'map_btn_rename': "✏️ Yeniden adlandır",
        'map_btn_kind': "📁 Tür",
        'map_btn_home': "🏠 Burada konuşlanılabilir",
        'map_btn_toll': "🪙 Geçiş ücreti",
        'map_btn_owner': "👑 Sahip",
        'map_btn_del_node': "❌ Bu yeri sil",
        'map_btn_units': "📏 Uzunluk",
        'map_btn_minutes': "⏱ Yolculuk süresi",
        'map_btn_del_edge': "❌ Bu yolu sil",
        'map_btn_del_yes': "🔥 Evet, sil",
        'map_btn_add_node': "➕ Yer ekle",
        'map_btn_add_edge': "➕ Yol ekle",
        'map_btn_edges': "🛣 Yollar",
        'map_btn_back_nodes': "🔙 Yerler",
        'map_btn_back_edges': "🔙 Yollar",
        'map_btn_back_node': "🔙 Geri",
        'map_pick_kind': "Burası ne tür bir yer?",
        'map_ask_home': "Ülkeler burada konuşlanabilir mi?",
        'map_ask_id': "Yeni yerin kimliğini gönderin (küçük harfler, örn. azov):",
        'map_ask_name': "{lang} dilindeki görünen adını gönderin:",
        'map_ask_toll': "{name} geçişi ne kadar olsun? (şu an {val}, 0 ücretsiz demektir)",
        'map_ask_units': "Bu yol kaç birim uzunlukta? (ücret bundan hesaplanır)",
        'map_ask_minutes': "Bu yol kaç dakika sürsün? (0 uzunluktan hesaplar)",
        'map_pick_first': "Yol nereden başlıyor?",
        'map_pick_second': "{a} noktasından nereye gidiyor?",
        'map_bad_number': "Geçerli bir değer değil. En az {min} olan bir tam sayı gönderin.",
        'map_lang_fa': "Farsça",
        'map_lang_en': "İngilizce",
        'map_lang_tr': "Türkçe",
        'map_kind_ocean': "🌊 Okyanus",
        'map_kind_sea': "🌊 Deniz",
        'map_kind_strait': "⚓️ Boğaz",
        'map_kind_canal': "🚧 Kanal",
        'map_kind_cape': "🏔 Burun",
        'map_kind_region': "🗺 Bölge",
        'map_kind_pass': "🏔 Geçit",
        'map_saved': "✅ Kaydedildi.",
        'map_renamed': "✅ Adlar güncellendi.",
        'map_home_on': "🏠 Ülkeler artık burada konuşlanabilir.",
        'map_home_off': "🚫 Ülkeler artık burada konuşlanamaz.",
        'map_toll_set': "🪙 {name} geçişi artık {val}.",
        'map_node_added': "✅ “{name}” haritada. “Yol ekle” ile bağlayın.",
        'map_edge_added': "✅ {a} — {b} yolu eklendi.",
        'map_node_deleted': "🔥 “{name}” haritadan kaldırıldı.",
        'map_edge_deleted': "🔥 {a} — {b} yolu kaldırıldı.",
        'map_del_node_confirm': "🔥 <b>“{name}” silinsin mi?</b>\n<blockquote><code>{id}</code> "
                                "kimliği ve ona değen {n} yol kaldırılacak.\n\n"
                                "⚠️ Burada konuşlanmış bir ülke varsa yeni bir yer "
                                "gerekecek.</blockquote>",
        'map_del_edge_confirm': "🔥 <b>{a} — {b}</b> yolu silinsin mi? Sevkiyatlar başka bir "
                                "yol bulmak zorunda kalacak.",
        'map_err_generic': "❌ Bir şeyler ters gitti.",
        'map_err_bad_id': "❌ Geçersiz kimlik. Yalnızca küçük harf, rakam ve alt çizgi; "
                          "harfle başlamalı ve 2 ila 16 karakter olmalı.",
        'map_err_bad_kind': "❌ Bu tür bu haritaya ait değil.",
        'map_err_bad_mode': "❌ Böyle bir harita yok.",
        'map_err_exists': "❌ Bu kimlikte bir yer zaten var.",
        'map_err_unknown_node': "❌ Haritada böyle bir yer yok.",
        'map_err_in_transit': "❌ Şu anda buradan bir sevkiyat geçiyor. O ticaret varana kadar "
                              "silinemez.",
        'map_err_guard_unavailable': "❌ Yolda ne olduğu kontrol edilemedi, bu yüzden hiçbir şey "
                                     "silinmedi.",
        'map_err_self_edge': "❌ Bir yer kendisine bağlanamaz.",
        'map_err_mode_mismatch': "❌ Deniz haritası ile kara haritası birleştirilemez.",
        'map_err_bad_units': "❌ Bir yol en az 1 birim uzunlukta olmalı.",
        'map_err_edge_exists': "❌ Bu ikisi zaten bağlı.",
        'map_err_no_edge': "❌ Böyle bir yol yok.",
    },
}
