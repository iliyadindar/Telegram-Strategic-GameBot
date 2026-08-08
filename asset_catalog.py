# -*- coding: utf-8 -*-
"""The game's asset catalog — resources, units and buildings as data.

Everything the game can own lives in three tables instead of in Python
literals, so an admin can add "archers" (and the camp that trains them, its
weekly output and its upgrade cost) from inside Telegram.

    asset_catalog        one row per type: kind, order, default, production
    asset_labels         its display name per language
    asset_upgrade_costs  what one level of a building costs

The types that shipped with the game are seeded as `builtin` on first run, with
exactly the values the hardcoded version used, so existing saves are unchanged.
Builtins can be retuned and renamed but never removed — the trade system and the
war flow refer to them by key.

Adding a type runs ALTER TABLE ... ADD COLUMN on `users`. There are two ways to
take one away again. hide() is reversible: the column and its numbers stay, so
re-adding the same key brings the values back. remove() is not: it drops the
column and everything in it, which is why it refuses builtins and refuses any
key a trade is currently carrying.
"""

import re
import sqlite3
import threading

# Column names in `users` that are not assets and must never be claimed.
RESERVED = frozenset({'user_id', 'group_id', 'treaties', 'home_sea', 'home_land'})

KINDS = ('resource', 'unit', 'building')

# A key becomes a SQL column name, so it is held to identifier rules and always
# passed through _check_key() before it reaches a statement.
KEY_RE = re.compile(r'^[a-z][a-z0-9_]{1,30}$')

_conn = None
_lock = threading.RLock()

# Set by set_delete_guard(). Returns the keys no destructive edit may touch
# because a trade in flight is carrying them.
_delete_guard = None


# ---------------------------------------------------------------------------
# Seed data — the game exactly as it shipped
# ---------------------------------------------------------------------------

BUILTIN_RESOURCES = ('money', 'gold', 'iron', 'stones', 'wood', 'food', 'meat', 'clothes')
RESOURCE_DEFAULT = 2000

BUILTIN_UNITS = ('swordsmen', 'gunmen', 'cavalry_swordsmen', 'cavalry_gunmen', 'special_guard',
                 'medium_cannons', 'large_cannons', 'small_ships', 'medium_ships', 'large_ships')
UNIT_DEFAULT = 1500

# building key -> (what it produces, how much per level per weekly cycle)
BUILTIN_BUILDINGS = (
    ('stone_factory', 'stones', 1500),
    ('wood_factory', 'wood', 1500),
    ('iron_factory', 'iron', 1500),
    ('gold_mine', 'gold', 1500),
    ('farm', 'food', 1500),
    ('animal_farm', 'meat', 1500),
    ('clothes_factory', 'clothes', 1500),
    ('bank', 'money', 1500),
    ('swordsmen_camp', 'swordsmen', 500),
    ('gunmen_camp', 'gunmen', 500),
    ('cavalry_swordsmen_camp', 'cavalry_swordsmen', 500),
    ('cavalry_gunmen_camp', 'cavalry_gunmen', 500),
    ('special_guard_camp', 'special_guard', 500),
    ('medium_cannon_factory', 'medium_cannons', 1500),
    ('large_cannon_factory', 'large_cannons', 1500),
    ('small_shipyard', 'small_ships', 500),
    ('medium_shipyard', 'medium_ships', 500),
    ('large_shipyard', 'large_ships', 500),
)
BUILDING_DEFAULT = 0

# Seeded from what apply_upgrade() actually deducted. The old check_upgrade_cost()
# tested a different resource than the deduction for five buildings (gold_mine,
# farm, animal_farm, swordsmen_camp, special_guard_camp), which let a group's
# wood go negative. One table now drives both the check and the deduction.
BUILTIN_COSTS = {
    'stone_factory': {'wood': 500, 'money': 500},
    'wood_factory': {'stones': 500, 'money': 500},
    'iron_factory': {'stones': 500, 'money': 500},
    'gold_mine': {'wood': 500, 'stones': 500, 'money': 500},
    'farm': {'wood': 500, 'stones': 500},
    'animal_farm': {'wood': 500, 'iron': 500, 'stones': 500},
    'clothes_factory': {'gold': 500, 'money': 500, 'stones': 500},
    'bank': {'stones': 500, 'iron': 500, 'gold': 500},
    'swordsmen_camp': {'money': 500, 'stones': 500, 'wood': 500},
    'gunmen_camp': {'money': 500, 'gold': 500, 'iron': 500},
    'cavalry_swordsmen_camp': {'iron': 500, 'gold': 250, 'stones': 500, 'money': 250},
    'cavalry_gunmen_camp': {'gold': 800, 'stones': 800, 'money': 500},
    'special_guard_camp': {'money': 1000, 'stones': 1000, 'wood': 1000},
    'medium_cannon_factory': {'iron': 500, 'money': 250, 'wood': 250},
    'large_cannon_factory': {'iron': 500, 'stones': 500, 'money': 250, 'gold': 200},
    'small_shipyard': {'iron': 200, 'wood': 200, 'money': 200},
    'medium_shipyard': {'iron': 500, 'wood': 500, 'money': 500},
    'large_shipyard': {'iron': 1000, 'wood': 1000, 'money': 1000},
}

BUILTIN_LABELS = {
    'fa': {
        'money': '💵 پول', 'gold': '🏅 طلا', 'iron': '🪛 آهن', 'stones': '🪨 سنگ',
        'wood': '🌲 چوب', 'food': '🍞 غذا', 'meat': '🍖 گوشت', 'clothes': '🥋 لباس',
        'swordsmen': '🗡️ سرباز شمشیرزن', 'gunmen': '🔫 سرباز تفنگدار',
        'cavalry_swordsmen': '🗡️ سواره‌نظام شمشیرزن', 'cavalry_gunmen': '🔫 سواره‌نظام تفنگدار',
        'special_guard': '🛡️ گارد ویژه', 'medium_cannons': '🎯 توپ متوسط',
        'large_cannons': '🎯 توپ بزرگ', 'small_ships': '⛵ کشتی کوچک',
        'medium_ships': '🚢 کشتی متوسط', 'large_ships': '🛳️ کشتی بزرگ',
        'stone_factory': '🏭 کارخونه سنگ', 'wood_factory': '🏭 کارخونه چوب',
        'iron_factory': '🏭 کارخونه آهن', 'gold_mine': '⛏ معدن طلا', 'farm': '🌾 زمین کشاورزی',
        'animal_farm': '🐄 دامداری', 'clothes_factory': '🧵 کارخانه لباس', 'bank': '🏦 بانک',
        'swordsmen_camp': '⚔️ کمپ سرباز شمشیرزن', 'gunmen_camp': '⚔️ کمپ سرباز تفنگدار',
        'cavalry_swordsmen_camp': '⚔️ کمپ سواره‌نظام شمشیرزن',
        'cavalry_gunmen_camp': '⚔️ کمپ سواره‌نظام تفنگدار',
        'special_guard_camp': '⚔️ کمپ گارد ویژه',
        'medium_cannon_factory': '🔧 کارخانه توپ متوسط',
        'large_cannon_factory': '🔧 کارخانه توپ بزرگ',
        'small_shipyard': '⚓ کشتی‌سازی کوچک', 'medium_shipyard': '⚓ کشتی‌سازی متوسط',
        'large_shipyard': '⚓ کشتی‌سازی بزرگ',
    },
    'en': {
        'money': '💵 Money', 'gold': '🏅 Gold', 'iron': '🪛 Iron', 'stones': '🪨 Stone',
        'wood': '🌲 Wood', 'food': '🍞 Food', 'meat': '🍖 Meat', 'clothes': '🥋 Clothes',
        'swordsmen': '🗡️ Swordsmen', 'gunmen': '🔫 Gunmen',
        'cavalry_swordsmen': '🗡️ Cavalry Swordsmen', 'cavalry_gunmen': '🔫 Cavalry Gunmen',
        'special_guard': '🛡️ Special Guard', 'medium_cannons': '🎯 Medium Cannons',
        'large_cannons': '🎯 Large Cannons', 'small_ships': '⛵ Small Ships',
        'medium_ships': '🚢 Medium Ships', 'large_ships': '🛳️ Large Ships',
        'stone_factory': '🏭 Stone Factory', 'wood_factory': '🏭 Wood Factory',
        'iron_factory': '🏭 Iron Factory', 'gold_mine': '⛏ Gold Mine', 'farm': '🌾 Farm',
        'animal_farm': '🐄 Animal Farm', 'clothes_factory': '🧵 Clothes Factory',
        'bank': '🏦 Bank',
        'swordsmen_camp': '⚔️ Swordsman Camp', 'gunmen_camp': '⚔️ Gunman Camp',
        'cavalry_swordsmen_camp': '⚔️ Cavalry Swordsman Camp',
        'cavalry_gunmen_camp': '⚔️ Cavalry Gunman Camp',
        'special_guard_camp': '⚔️ Special Guard Camp',
        'medium_cannon_factory': '🔧 Medium Cannon Factory',
        'large_cannon_factory': '🔧 Large Cannon Factory',
        'small_shipyard': '⚓ Small Shipyard', 'medium_shipyard': '⚓ Medium Shipyard',
        'large_shipyard': '⚓ Large Shipyard',
    },
    'tr': {
        'money': '💵 Para', 'gold': '🏅 Altın', 'iron': '🪛 Demir', 'stones': '🪨 Taş',
        'wood': '🌲 Odun', 'food': '🍞 Yiyecek', 'meat': '🍖 Et', 'clothes': '🥋 Giysi',
        'swordsmen': '🗡️ Kılıçlı Asker', 'gunmen': '🔫 Tüfekçi',
        'cavalry_swordsmen': '🗡️ Atlı Kılıçlı', 'cavalry_gunmen': '🔫 Atlı Tüfekçi',
        'special_guard': '🛡️ Özel Muhafız', 'medium_cannons': '🎯 Orta Top',
        'large_cannons': '🎯 Büyük Top', 'small_ships': '⛵ Küçük Gemi',
        'medium_ships': '🚢 Orta Gemi', 'large_ships': '🛳️ Büyük Gemi',
        'stone_factory': '🏭 Taş Fabrikası', 'wood_factory': '🏭 Odun Fabrikası',
        'iron_factory': '🏭 Demir Fabrikası', 'gold_mine': '⛏ Altın Madeni',
        'farm': '🌾 Çiftlik', 'animal_farm': '🐄 Hayvan Çiftliği',
        'clothes_factory': '🧵 Giysi Fabrikası', 'bank': '🏦 Banka',
        'swordsmen_camp': '⚔️ Kılıçlı Asker Kampı', 'gunmen_camp': '⚔️ Tüfekçi Kampı',
        'cavalry_swordsmen_camp': '⚔️ Atlı Kılıçlı Kampı',
        'cavalry_gunmen_camp': '⚔️ Atlı Tüfekçi Kampı',
        'special_guard_camp': '⚔️ Özel Muhafız Kampı',
        'medium_cannon_factory': '🔧 Orta Top Fabrikası',
        'large_cannon_factory': '🔧 Büyük Top Fabrikası',
        'small_shipyard': '⚓ Küçük Tersane', 'medium_shipyard': '⚓ Orta Tersane',
        'large_shipyard': '⚓ Büyük Tersane',
    },
}

LANGS = tuple(BUILTIN_LABELS)


class CatalogError(ValueError):
    """Raised for a key or field the catalog cannot accept."""


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


def init(conn):
    """Create the catalog tables, seed the builtins and sync the users columns."""
    global _conn
    _conn = conn
    _migrate()
    _seed()
    ensure_columns()


def _migrate():
    with _lock:
        _conn.execute('''CREATE TABLE IF NOT EXISTS asset_catalog (
            key           TEXT PRIMARY KEY,
            kind          TEXT NOT NULL,
            position      INTEGER NOT NULL DEFAULT 0,
            default_value INTEGER NOT NULL DEFAULT 0,
            builtin       INTEGER NOT NULL DEFAULT 0,
            hidden        INTEGER NOT NULL DEFAULT 0,
            produces      TEXT NOT NULL DEFAULT '',
            output        INTEGER NOT NULL DEFAULT 0,
            tradeable     INTEGER NOT NULL DEFAULT 0
        )''')
        _conn.execute('''CREATE TABLE IF NOT EXISTS asset_labels (
            key   TEXT NOT NULL,
            lang  TEXT NOT NULL,
            label TEXT NOT NULL,
            PRIMARY KEY (key, lang)
        )''')
        _conn.execute('''CREATE TABLE IF NOT EXISTS asset_upgrade_costs (
            building TEXT NOT NULL,
            resource TEXT NOT NULL,
            amount   INTEGER NOT NULL,
            PRIMARY KEY (building, resource)
        )''')
        _conn.commit()


_CATALOG_COLUMNS = ("(key, kind, position, default_value, builtin, hidden, produces, output, "
                    "tradeable) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")


def _builtin_rows():
    """The shipped catalog as insertable rows, positions stepping by 10 per kind."""
    rows = []
    for keys, kind, default, tradeable in (
            (BUILTIN_RESOURCES, 'resource', RESOURCE_DEFAULT, 1),
            (BUILTIN_UNITS, 'unit', UNIT_DEFAULT, 0)):
        for index, key in enumerate(keys, start=1):
            rows.append((key, kind, index * 10, default, 1, 0, '', 0, tradeable))
    for index, (key, produces, output) in enumerate(BUILTIN_BUILDINGS, start=1):
        rows.append((key, 'building', index * 10, BUILDING_DEFAULT, 1, 0, produces, output, 0))
    return rows


def _builtin_label_rows():
    return [(key, lang, label)
            for lang, table in BUILTIN_LABELS.items()
            for key, label in table.items()]


def _builtin_cost_rows():
    return [(building, resource, amount)
            for building, table in BUILTIN_COSTS.items()
            for resource, amount in table.items()]


def _seed():
    """Insert the shipped types. INSERT OR IGNORE, so admin edits are never undone."""
    with _lock:
        _conn.executemany("INSERT OR IGNORE INTO asset_catalog " + _CATALOG_COLUMNS,
                          _builtin_rows())
        _conn.executemany("INSERT OR IGNORE INTO asset_labels (key, lang, label) VALUES (?, ?, ?)",
                          _builtin_label_rows())
        _conn.executemany(
            "INSERT OR IGNORE INTO asset_upgrade_costs (building, resource, amount) "
            "VALUES (?, ?, ?)", _builtin_cost_rows())
        _conn.commit()


def ensure_columns():
    """Add a `users` column for every catalog key that lacks one."""
    with _lock:
        existing = {r[1] for r in _conn.execute("PRAGMA table_info(users)").fetchall()}
        for row in _q("SELECT key, default_value FROM asset_catalog"):
            if row['key'] in existing:
                continue
            _check_key(row['key'])
            _conn.execute(
                f"ALTER TABLE users ADD COLUMN {row['key']} INTEGER DEFAULT {int(row['default_value'])}")
            # ALTER TABLE fills existing rows with the default already, but be
            # explicit so a re-added (previously hidden) column is reset too.
            _conn.execute(f"UPDATE users SET {row['key']}=? WHERE {row['key']} IS NULL",
                          (int(row['default_value']),))
        _conn.commit()


# ---------------------------------------------------------------------------
# Helpers
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


def _check_key(key):
    """Guard every value that reaches a statement as an identifier."""
    if not KEY_RE.match(key or ''):
        raise CatalogError('bad_key')
    if key in RESERVED:
        raise CatalogError('reserved')
    return key


def validate_new_key(key):
    """Raise CatalogError unless `key` is a usable name for a brand-new type."""
    _check_key(key)
    if _q("SELECT 1 FROM asset_catalog WHERE key=?", (key,)):
        raise CatalogError('exists')
    with _lock:
        existing = {row[1] for row in _conn.execute("PRAGMA table_info(users)").fetchall()}
    if key in existing:
        raise CatalogError('column_exists')
    return key


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def entries(kind=None, include_hidden=False):
    """Catalog rows, ordered by kind then position."""
    sql = "SELECT * FROM asset_catalog"
    where, params = [], []
    if kind:
        where.append("kind=?")
        params.append(kind)
    if not include_hidden:
        where.append("hidden=0")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY CASE kind WHEN 'resource' THEN 0 WHEN 'unit' THEN 1 ELSE 2 END, position, key"
    return _q(sql, tuple(params))


def entry(key):
    rows = _q("SELECT * FROM asset_catalog WHERE key=?", (key,))
    return rows[0] if rows else None


def keys(kind=None, include_hidden=False):
    return tuple(row['key'] for row in entries(kind, include_hidden))


def all_keys(include_hidden=False):
    return keys(None, include_hidden)


def defaults(include_hidden=True):
    return {row['key']: row['default_value'] for row in entries(None, include_hidden)}


def is_builtin(key):
    row = entry(key)
    return bool(row and row['builtin'])


def label(key, lang):
    rows = _q("SELECT label FROM asset_labels WHERE key=? AND lang=?", (key, lang))
    if rows:
        return rows[0]['label']
    rows = _q("SELECT label FROM asset_labels WHERE key=? LIMIT 1", (key,))
    return rows[0]['label'] if rows else key


def labels(key):
    return {row['lang']: row['label']
            for row in _q("SELECT lang, label FROM asset_labels WHERE key=?", (key,))}


def tradeable_resources():
    return tuple(row['key'] for row in entries('resource') if row['tradeable'])


def production():
    """(building, produces, output) for visible buildings that actually produce."""
    out = []
    visible = set(all_keys())
    for row in entries('building'):
        if row['produces'] and row['output'] and row['produces'] in visible:
            out.append((row['key'], row['produces'], row['output']))
    return out


def upgrade_cost(building):
    return {row['resource']: row['amount']
            for row in _q("SELECT resource, amount FROM asset_upgrade_costs WHERE building=?",
                          (building,))
            if row['amount'] > 0}


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def add(key, kind, label_map, default_value=0, produces='', output=0, tradeable=0):
    """Register a new type and give `users` a column for it."""
    validate_new_key(key)
    if kind not in KINDS:
        raise CatalogError('bad_kind')
    if produces:
        target = entry(produces)
        if target is None or target['kind'] == 'building':
            raise CatalogError('bad_produces')
    with _lock:
        rows = _q("SELECT COALESCE(MAX(position), 0) AS p FROM asset_catalog WHERE kind=?",
                  (kind,))
        position = (rows[0]['p'] if rows else 0) + 10
        _conn.execute(
            "INSERT INTO asset_catalog "
            "(key, kind, position, default_value, builtin, hidden, produces, output, tradeable) "
            "VALUES (?, ?, ?, ?, 0, 0, ?, ?, ?)",
            (key, kind, position, int(default_value), produces if kind == 'building' else '',
             int(output) if kind == 'building' else 0,
             1 if (kind == 'resource' and tradeable) else 0))
        _conn.commit()
    set_labels(key, label_map)
    ensure_columns()
    return key


def set_labels(key, label_map):
    if entry(key) is None:
        raise CatalogError('unknown')
    rows = [(key, lang, text) for lang, text in label_map.items() if text]
    with _lock:
        _conn.executemany(
            "INSERT OR REPLACE INTO asset_labels (key, lang, label) VALUES (?, ?, ?)", rows)
        _conn.commit()


def set_default(key, value):
    _require_known(key)
    _exec("UPDATE asset_catalog SET default_value=? WHERE key=?", (int(value), key))


def set_output(key, produces, output):
    row = _require_known(key)
    if row['kind'] != 'building':
        raise CatalogError('not_a_building')
    if produces:
        target = entry(produces)
        if target is None or target['kind'] == 'building':
            raise CatalogError('bad_produces')
    _exec("UPDATE asset_catalog SET produces=?, output=? WHERE key=?",
          (produces, int(output), key))


def set_tradeable(key, tradeable):
    row = _require_known(key)
    if row['kind'] != 'resource':
        raise CatalogError('not_a_resource')
    _exec("UPDATE asset_catalog SET tradeable=? WHERE key=?", (1 if tradeable else 0, key))


def set_upgrade_cost(building, resource, amount):
    row = _require_known(building)
    if row['kind'] != 'building':
        raise CatalogError('not_a_building')
    target = entry(resource)
    if target is None or target['kind'] != 'resource':
        raise CatalogError('bad_resource')
    if int(amount) <= 0:
        _exec("DELETE FROM asset_upgrade_costs WHERE building=? AND resource=?",
              (building, resource))
    else:
        _exec("INSERT OR REPLACE INTO asset_upgrade_costs (building, resource, amount) "
              "VALUES (?, ?, ?)", (building, resource, int(amount)))


def hide(key):
    """Remove a custom type from the game without touching its stored numbers."""
    row = _require_known(key)
    if row['builtin']:
        raise CatalogError('builtin')
    _exec("UPDATE asset_catalog SET hidden=1 WHERE key=?", (key,))


def unhide(key):
    _require_known(key)
    _exec("UPDATE asset_catalog SET hidden=0 WHERE key=?", (key,))


def _require_known(key):
    row = entry(key)
    if row is None:
        raise CatalogError('unknown')
    return row


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def _ordered(kind):
    """Every key of one kind in display order, hidden ones included."""
    return _q("SELECT key, position FROM asset_catalog WHERE kind=? ORDER BY position, key",
              (kind,))


def _renumber(kind):
    """Rewrite one kind's positions as 10, 20, 30… keeping the current order.

    Seeded positions step by 10 and add() appends at MAX+10, but nothing
    enforces uniqueness, and a swap between two rows sharing a position would
    be a no-op. Spacing them out first makes the swap meaningful.
    """
    with _lock:
        _conn.executemany("UPDATE asset_catalog SET position=? WHERE key=?",
                          [((i + 1) * 10, row['key']) for i, row in enumerate(_ordered(kind))])
        _conn.commit()


def move(key, direction):
    """Swap a type with its neighbour of the same kind.

    Returns False when it is already at that end of its kind. Ordering is
    within a kind only — entries() always groups resource, unit, building.
    """
    if direction not in ('up', 'down'):
        raise CatalogError('bad_direction')
    kind = _require_known(key)['kind']
    with _lock:
        ordered = _ordered(kind)
        if len({row['position'] for row in ordered}) != len(ordered):
            _renumber(kind)
            ordered = _ordered(kind)
        index = next(i for i, row in enumerate(ordered) if row['key'] == key)
        other = index - 1 if direction == 'up' else index + 1
        if not 0 <= other < len(ordered):
            return False
        here, there = ordered[index], ordered[other]
        _conn.execute("UPDATE asset_catalog SET position=? WHERE key=?",
                      (there['position'], here['key']))
        _conn.execute("UPDATE asset_catalog SET position=? WHERE key=?",
                      (here['position'], there['key']))
        _conn.commit()
    return True


def holders(key):
    """How many groups hold a non-zero amount of this type.

    What a delete confirmation screen needs in order to say how much is about
    to be destroyed rather than asking the admin to take it on faith.
    """
    _require_known(key)
    _check_key(key)
    rows = _q(f"SELECT COUNT(DISTINCT group_id) AS n FROM users WHERE {key} != 0")
    return rows[0]['n'] if rows else 0


def rank(key):
    """(place, total) of a key within its kind, 1-based, for display."""
    kind = _require_known(key)['kind']
    ordered = [row['key'] for row in _ordered(kind)]
    return ordered.index(key) + 1, len(ordered)


# ---------------------------------------------------------------------------
# Destroying a type
# ---------------------------------------------------------------------------


def set_delete_guard(fn):
    """Register what decides a key is too busy to destroy.

    `fn` returns an iterable of keys some trade in flight is carrying. Dropping
    such a column would make that trade's refund raise on a column that no
    longer exists, and the cargo would be gone. main*.py wires this to
    trade_system after both modules are up; unwired, nothing is ever busy.
    """
    global _delete_guard
    _delete_guard = fn


def keys_in_transit():
    """Keys no destructive edit may touch right now."""
    if _delete_guard is None:
        return frozenset()
    try:
        return frozenset(_delete_guard())
    except Exception:
        # A guard that cannot answer is not permission to proceed.
        raise CatalogError('guard_unavailable')


def remove(key):
    """Destroy a custom type: its row, labels, costs, and its `users` column.

    Returns True when the column went too, False when the database is too old
    for ALTER TABLE ... DROP COLUMN (SQLite < 3.35). In that case the type is
    still gone from the game and only an orphaned column survives, so the
    caller can say so rather than reporting a clean delete.
    """
    row = _require_known(key)
    if row['builtin']:
        raise CatalogError('builtin')
    if key in keys_in_transit():
        raise CatalogError('in_transit')
    _check_key(key)
    with _lock:
        # Buildings that produced it now produce nothing, rather than pointing
        # at a key production() would silently drop anyway.
        _conn.execute("UPDATE asset_catalog SET produces='', output=0 WHERE produces=?", (key,))
        _conn.execute("DELETE FROM asset_upgrade_costs WHERE building=? OR resource=?", (key, key))
        _conn.execute("DELETE FROM asset_labels WHERE key=?", (key,))
        _conn.execute("DELETE FROM asset_catalog WHERE key=?", (key,))
        dropped = True
        try:
            _conn.execute(f"ALTER TABLE users DROP COLUMN {key}")
        except sqlite3.OperationalError:
            dropped = False
        _conn.commit()
    return dropped


def factory_reset():
    """Restore the shipped catalog. Group balances are deliberately untouched.

    Every custom type is destroyed and every builtin is retuned to the values
    in BUILTIN_*. What resets is the shape of the game, not what anyone owns.

    Returns the (removed, kept_columns) key lists, where kept_columns names the
    types whose column outlived them on an old SQLite.
    """
    custom = [row['key'] for row in
              _q("SELECT key FROM asset_catalog WHERE builtin=0 ORDER BY key")]
    if set(custom) & keys_in_transit():
        raise CatalogError('in_transit')
    removed, kept = [], []
    for key in custom:
        if not remove(key):
            kept.append(key)
        removed.append(key)
    with _lock:
        _conn.executemany("INSERT OR REPLACE INTO asset_catalog " + _CATALOG_COLUMNS,
                          _builtin_rows())
        _conn.executemany("INSERT OR REPLACE INTO asset_labels (key, lang, label) "
                          "VALUES (?, ?, ?)", _builtin_label_rows())
        _conn.execute("DELETE FROM asset_upgrade_costs")
        _conn.executemany("INSERT INTO asset_upgrade_costs (building, resource, amount) "
                          "VALUES (?, ?, ?)", _builtin_cost_rows())
        _conn.commit()
    return removed, kept
