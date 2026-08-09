# -*- coding: utf-8 -*-
"""The trade world as data — nodes, the edges between them, and their names.

The map used to be four Python literals inside trade_system. It lives in three
tables now, so an admin can rename the Suez Canal, retime the leg out of it, or
draw a route that never existed, all from inside Telegram.

    trade_nodes        one row per place: mode, kind, whether a country can sit
                       there, and where it sorts in the admin list
    trade_node_labels  its display name per language
    trade_edges        an undirected leg: two nodes, its length, its timing

The map that shipped with the game is seeded on first run with `builtin=1` and
exactly the values the literals had, so existing databases keep working — node
ids still match `users.home_sea`, `users.home_land`, `chokepoint_owners.node_id`
and the `toll_<id>` keys in `trade_config`.

Deleting a seeded node or edge writes a tombstone, because otherwise the next
restart would helpfully put it back.

Two fields carry a leg's cost, and they are not the same thing:

    units    distance. Drives the fee and which route Dijkstra calls cheapest.
    minutes  travel time. 0 means "derive it from units", anything else is an
             exact override.

That split is what lets an admin say "Suez to the Red Sea takes 40 minutes"
without moving any prices.
"""

import re
import sqlite3
import threading

MODES = ('sea', 'land')

# What a node can be. Straits, canals and passes are the tolled chokepoints:
# they are nodes rather than edges so the ticker can narrate passing them and
# so a toll-free route can simply route around them.
KINDS = {
    'sea': ('ocean', 'sea', 'strait', 'canal', 'cape'),
    'land': ('region', 'pass'),
}
CHOKEPOINT_KINDS = ('strait', 'canal', 'pass')

# A node id becomes part of a `toll_<id>` config key and is stored as a plain
# reference in three other tables, so it is held to identifier rules.
NODE_ID_RE = re.compile(r'^[a-z][a-z0-9_]{1,15}$')

LANGS = ('fa', 'en', 'tr')

_conn = None
_lock = threading.RLock()
_cache = {}
_node_guard = None


class MapError(ValueError):
    """Raised for a node, edge or field the map cannot accept."""


# ---------------------------------------------------------------------------
# Seed data — the world exactly as it shipped
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

SEED = {'sea': (SEA_NODES, SEA_EDGES), 'land': (LAND_NODES, LAND_EDGES)}


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


def init(conn):
    """Create the tables, seed the shipped world, and drop any stale cache."""
    global _conn
    _conn = conn
    _migrate()
    _seed()
    _invalidate()


def _migrate():
    with _lock:
        _conn.execute('''CREATE TABLE IF NOT EXISTS trade_nodes (
            id       TEXT PRIMARY KEY,
            mode     TEXT NOT NULL,
            kind     TEXT NOT NULL,
            home     INTEGER NOT NULL DEFAULT 0,
            position INTEGER NOT NULL DEFAULT 0,
            builtin  INTEGER NOT NULL DEFAULT 0
        )''')
        _conn.execute('''CREATE TABLE IF NOT EXISTS trade_node_labels (
            node_id TEXT NOT NULL,
            lang    TEXT NOT NULL,
            label   TEXT NOT NULL,
            PRIMARY KEY (node_id, lang)
        )''')
        _conn.execute('''CREATE TABLE IF NOT EXISTS trade_edges (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            mode    TEXT NOT NULL,
            a       TEXT NOT NULL,
            b       TEXT NOT NULL,
            units   INTEGER NOT NULL,
            minutes INTEGER NOT NULL DEFAULT 0,
            UNIQUE (mode, a, b)
        )''')
        # Without this, deleting something the game shipped with would simply
        # undo itself on the next restart.
        _conn.execute('''CREATE TABLE IF NOT EXISTS trade_map_removed (
            kind TEXT NOT NULL,
            ref  TEXT NOT NULL,
            PRIMARY KEY (kind, ref)
        )''')
        _conn.commit()


def _seed():
    """Insert the shipped world, skipping anything an admin already deleted."""
    with _lock:
        gone = {(row[0], row[1]) for row in
                _conn.execute("SELECT kind, ref FROM trade_map_removed").fetchall()}
        nodes, labels, edges = [], [], []
        for mode, (seed_nodes, seed_edges) in SEED.items():
            for position, (nid, node) in enumerate(seed_nodes.items(), start=1):
                if ('node', nid) in gone:
                    continue
                nodes.append((nid, mode, node['kind'], 1 if node['home'] else 0, position * 10, 1))
                labels.extend((nid, lang, text) for lang, text in node['names'].items())
            for a, b, units in seed_edges:
                if ('edge', _edge_ref(mode, a, b)) in gone:
                    continue
                if ('node', a) in gone or ('node', b) in gone:
                    continue
                edges.append((mode,) + _pair(a, b) + (units, 0))
        _conn.executemany(
            "INSERT OR IGNORE INTO trade_nodes (id, mode, kind, home, position, builtin) "
            "VALUES (?, ?, ?, ?, ?, ?)", nodes)
        _conn.executemany(
            "INSERT OR IGNORE INTO trade_node_labels (node_id, lang, label) VALUES (?, ?, ?)",
            labels)
        _conn.executemany(
            "INSERT OR IGNORE INTO trade_edges (mode, a, b, units, minutes) VALUES (?, ?, ?, ?, ?)",
            edges)
        _conn.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _q(sql, params=()):
    with _lock:
        cur = _conn.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def _exec(sql, params=()):
    with _lock:
        cur = _conn.execute(sql, params)
        _conn.commit()
        return cur


def _pair(a, b):
    """Edges are undirected, so they are always stored in one canonical order."""
    return (a, b) if a <= b else (b, a)


def _edge_ref(mode, a, b):
    return '%s:%s:%s' % ((mode,) + _pair(a, b))


def _tombstone(kind, ref):
    _exec("INSERT OR IGNORE INTO trade_map_removed (kind, ref) VALUES (?, ?)", (kind, ref))


def _invalidate():
    """Drop the derived lookups. Every mutator ends with this.

    Readers go through nodes()/edges()/adjacency(), which memoise here rather
    than in their callers, so this is the only place a stale map can hide.
    """
    with _lock:
        _cache.clear()


def _cached(key, build):
    """Memoise one derived lookup, holding the lock across build and store.

    trade_system's ticker thread reads the map while an admin edits it. The
    dangerous interleaving is not a torn read — it is a reader that builds a
    value, has _invalidate() run underneath it, and then writes its now-stale
    value into the cache, where it would stay until the next edit. Building
    under the same lock the mutators take makes that impossible. The lock is
    reentrant and _q() already takes it, so `build` may query freely.
    """
    with _lock:
        if key not in _cache:
            _cache[key] = build()
        return _cache[key]


def set_node_guard(fn):
    """Register what decides a node is too busy to delete.

    `fn` returns node ids that a trade in flight still has to travel through.
    Deleting one would strand that shipment mid-route.
    """
    global _node_guard
    _node_guard = fn


def nodes_in_transit():
    if _node_guard is None:
        return frozenset()
    try:
        return frozenset(_node_guard())
    except Exception:
        raise MapError('guard_unavailable')


def _check_id(nid):
    if not NODE_ID_RE.match(nid or ''):
        raise MapError('bad_id')
    return nid


def check_new_id(nid):
    """Raise MapError unless `nid` is a usable id for a brand-new node."""
    _check_id(nid)
    if _q("SELECT 1 FROM trade_nodes WHERE id=?", (nid,)):
        raise MapError('exists')
    return nid


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def nodes(mode):
    """{node id: {'kind', 'home', 'names'}} for one mode, in admin list order.

    Shaped exactly like the literal that used to live in trade_system, so the
    routing code reads it the same way it always did.
    """
    if mode not in MODES:
        raise MapError('bad_mode')

    def build():
        labels = {}
        for row in _q("SELECT node_id, lang, label FROM trade_node_labels"):
            labels.setdefault(row['node_id'], {})[row['lang']] = row['label']
        out = {}
        for row in _q("SELECT id, kind, home FROM trade_nodes WHERE mode=? ORDER BY position, id",
                      (mode,)):
            out[row['id']] = {'kind': row['kind'], 'home': bool(row['home']),
                              'names': labels.get(row['id'], {})}
        return out

    return _cached(('nodes', mode), build)


def node(mode, nid):
    return nodes(mode).get(nid)


def mode_of(nid):
    rows = _q("SELECT mode FROM trade_nodes WHERE id=?", (nid,))
    return rows[0]['mode'] if rows else None


def name(nid, lang):
    """A node's display name, falling back to another language then to its id."""
    rows = _q("SELECT label FROM trade_node_labels WHERE node_id=? AND lang=?", (nid, lang))
    if rows:
        return rows[0]['label']
    rows = _q("SELECT label FROM trade_node_labels WHERE node_id=? LIMIT 1", (nid,))
    return rows[0]['label'] if rows else nid


def labels(nid):
    return {row['lang']: row['label']
            for row in _q("SELECT lang, label FROM trade_node_labels WHERE node_id=?", (nid,))}


def edges(mode):
    """[(a, b, units, minutes)] for one mode."""
    if mode not in MODES:
        raise MapError('bad_mode')
    return _cached(('edges', mode), lambda: [
        (row['a'], row['b'], row['units'], row['minutes'])
        for row in _q("SELECT a, b, units, minutes FROM trade_edges WHERE mode=? "
                      "ORDER BY a, b", (mode,))])


def edge(mode, a, b):
    a, b = _pair(a, b)
    rows = _q("SELECT a, b, units, minutes FROM trade_edges WHERE mode=? AND a=? AND b=?",
              (mode, a, b))
    return rows[0] if rows else None


def edges_of(nid):
    """Every edge touching a node, whichever end it sits on."""
    return _q("SELECT mode, a, b, units, minutes FROM trade_edges WHERE a=? OR b=? ORDER BY a, b",
              (nid, nid))


def adjacency(mode):
    """{node id: [(neighbour, units)]}, every node present even with no edges."""
    def build():
        out = {nid: [] for nid in nodes(mode)}
        for a, b, units, _minutes in edges(mode):
            if a in out and b in out:
                out[a].append((b, units))
                out[b].append((a, units))
        return out

    return _cached(('adj', mode), build)


def leg(mode, a, b):
    """(units, minutes) for one leg, or None when the two are not connected."""
    legs = _cached(('legs', mode), lambda: {frozenset((x, y)): (units, minutes)
                                            for x, y, units, minutes in edges(mode)})
    return legs.get(frozenset((a, b)))


def leg_minutes(mode, a, b, per_unit):
    """How long one leg takes: the override when set, else units x per_unit."""
    found = leg(mode, a, b)
    if found is None:
        return 0
    units, minutes = found
    return minutes if minutes > 0 else units * per_unit


def chokepoints():
    """Every node a toll can be charged at, sea first then land."""
    out = []
    for mode in MODES:
        out += [nid for nid, n in nodes(mode).items() if n['kind'] in CHOKEPOINT_KINDS]
    return out


def home_nodes(mode):
    return [nid for nid, n in nodes(mode).items() if n['home']]


# ---------------------------------------------------------------------------
# Writing — nodes
# ---------------------------------------------------------------------------


def add_node(mode, nid, kind, home, label_map):
    if mode not in MODES:
        raise MapError('bad_mode')
    _check_id(nid)
    if kind not in KINDS[mode]:
        raise MapError('bad_kind')
    if _q("SELECT 1 FROM trade_nodes WHERE id=?", (nid,)):
        raise MapError('exists')
    with _lock:
        rows = _q("SELECT COALESCE(MAX(position), 0) AS p FROM trade_nodes WHERE mode=?", (mode,))
        position = (rows[0]['p'] if rows else 0) + 10
        _conn.execute("INSERT INTO trade_nodes (id, mode, kind, home, position, builtin) "
                      "VALUES (?, ?, ?, ?, ?, 0)",
                      (nid, mode, kind, 1 if home else 0, position))
        # A node deleted once and added back should stay this time.
        _conn.execute("DELETE FROM trade_map_removed WHERE kind='node' AND ref=?", (nid,))
        _conn.commit()
    set_labels(nid, label_map)
    _invalidate()
    return nid


def set_labels(nid, label_map):
    _require_node(nid)
    rows = [(nid, lang, text) for lang, text in label_map.items() if text]
    if not rows:
        return
    with _lock:
        _conn.executemany(
            "INSERT OR REPLACE INTO trade_node_labels (node_id, lang, label) VALUES (?, ?, ?)",
            rows)
        _conn.commit()
    _invalidate()


def set_kind(nid, kind):
    row = _require_node(nid)
    if kind not in KINDS[row['mode']]:
        raise MapError('bad_kind')
    _exec("UPDATE trade_nodes SET kind=? WHERE id=?", (kind, nid))
    _invalidate()


def set_home(nid, home):
    _require_node(nid)
    _exec("UPDATE trade_nodes SET home=? WHERE id=?", (1 if home else 0, nid))
    _invalidate()


def remove_node(nid):
    """Delete a node, its labels, its edges and every reference to it.

    Refuses while a trade in flight still has to pass through it — the ticker
    walks that stored route leg by leg and names each node as it goes.

    A node id is referenced from three places outside this module's own tables,
    and a dangling reference is worse than a missing node: a country whose
    home_sea points at nothing simply cannot trade, with no error to explain
    why. So they are cleared here, in the same transaction as the delete.
    """
    _require_node(nid)
    if nid in nodes_in_transit():
        raise MapError('in_transit')
    with _lock:
        _conn.execute("DELETE FROM trade_edges WHERE a=? OR b=?", (nid, nid))
        _conn.execute("DELETE FROM trade_node_labels WHERE node_id=?", (nid,))
        _conn.execute("DELETE FROM trade_nodes WHERE id=?", (nid,))
        for statement, params in (
                ("UPDATE users SET home_sea='' WHERE home_sea=?", (nid,)),
                ("UPDATE users SET home_land='' WHERE home_land=?", (nid,)),
                ("DELETE FROM chokepoint_owners WHERE node_id=?", (nid,)),
                # Zeroed rather than deleted: trade_config falls back to the
                # shipped CONFIG_DEFAULTS, so a deleted row would restore the
                # old toll — and re-seed it on the next restart.
                ("INSERT OR REPLACE INTO trade_config (key, value) VALUES (?, 0)",
                 ('toll_' + nid,))):
            try:
                _conn.execute(statement, params)
            except sqlite3.OperationalError:
                # Those tables belong to trade_system. When the map is used on
                # its own they are simply absent, and there is nothing to clear.
                pass
        _conn.commit()
    _tombstone('node', nid)
    _invalidate()


# ---------------------------------------------------------------------------
# Writing — edges
# ---------------------------------------------------------------------------


def add_edge(mode, a, b, units, minutes=0):
    if mode not in MODES:
        raise MapError('bad_mode')
    if a == b:
        raise MapError('self_edge')
    for nid in (a, b):
        row = _require_node(nid)
        if row['mode'] != mode:
            raise MapError('mode_mismatch')
    if int(units) <= 0:
        raise MapError('bad_units')
    a, b = _pair(a, b)
    if edge(mode, a, b):
        raise MapError('edge_exists')
    _exec("INSERT INTO trade_edges (mode, a, b, units, minutes) VALUES (?, ?, ?, ?, ?)",
          (mode, a, b, int(units), max(0, int(minutes))))
    _exec("DELETE FROM trade_map_removed WHERE kind='edge' AND ref=?", (_edge_ref(mode, a, b),))
    _invalidate()


def set_edge(mode, a, b, units=None, minutes=None):
    """Retune a leg. units drives fee and routing, minutes overrides its timing."""
    a, b = _pair(a, b)
    row = edge(mode, a, b)
    if row is None:
        raise MapError('no_edge')
    if units is not None:
        if int(units) <= 0:
            raise MapError('bad_units')
        _exec("UPDATE trade_edges SET units=? WHERE mode=? AND a=? AND b=?",
              (int(units), mode, a, b))
    if minutes is not None:
        _exec("UPDATE trade_edges SET minutes=? WHERE mode=? AND a=? AND b=?",
              (max(0, int(minutes)), mode, a, b))
    _invalidate()


def remove_edge(mode, a, b):
    a, b = _pair(a, b)
    if edge(mode, a, b) is None:
        raise MapError('no_edge')
    _exec("DELETE FROM trade_edges WHERE mode=? AND a=? AND b=?", (mode, a, b))
    _tombstone('edge', _edge_ref(mode, a, b))
    _invalidate()


def _require_node(nid):
    rows = _q("SELECT id, mode, kind, home, builtin FROM trade_nodes WHERE id=?", (nid,))
    if not rows:
        raise MapError('unknown_node')
    return rows[0]
