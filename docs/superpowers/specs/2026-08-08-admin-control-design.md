# Admin control: real deletion, ordering, an editable map, and reset

Design doc — 2026-08-08

## Why

Six requests from AHMAD (bot co-admin), collected 2026-07-31 → 2026-08-08:

1. A type he added ("peoples") could not be removed — only disabled. He wants the key gone.
2. New types always land at the bottom of the asset list; he wants "جمعیت" above "پول".
3. Trade routes should be editable — names, owners.
4. Trade timing should be settable by hand.
5. The action-log screen (گزارش اقدامات) should be zeroable, "که اصلا این اتفاقات نیفتاده".
6. The bot should be resettable to zero, with his added sections removed.

Requests 3 and 4 collapse into one workstream: once the map is data, per-edge minutes *are*
manual timing. So six asks become five workstreams.

## Scope decisions

| Decision | Choice |
|---|---|
| Deletion depth | Custom types only, full wipe. Builtins stay protected — trade and war reference them by key. |
| Reorder UI | ⬆️/⬇️ swap with the neighbour of the same kind. |
| Map editing | Full editor: nodes, edges, weights, kinds move from code into tables. |
| Manual timing | Per-edge minutes override, inside the map editor. |
| Factory reset | Catalog back to shipped state + action log cleared. **Does not** touch countries' current numbers or the trade world. |
| Permissions | Destructive ops (delete type, log wipe, factory reset, node/edge deletion) are owner-only. Reorder, rename, retime, add-node, per-group reset stay admin-level. |

Explicitly out of scope: resetting all countries' assets in one action (the existing per-group
reset covers it), resetting the trade world, and overriding a trade already in flight.

## Architecture

Approach: extract the map into its own module. Rejected alternatives were putting map tables and
screens directly into `trade_system.py` (already 1,900 lines and the largest file in the repo) and
storing admin edits as a diff layer over the Python literals (two sources of truth; "add a node"
does not fit the model).

```
asset_catalog.py   + remove(), move(), factory_reset(), set_delete_guard()
asset_admin.py     + delete confirm screen, ⬆️/⬇️ buttons
trade_map.py       NEW — owns trade_nodes / trade_node_labels / trade_edges
trade_map_admin.py NEW — panel screens for the map (trd:map…)
trade_system.py    - the node/edge literals; reads through trade_map
admin_panel.py     + log wipe, factory reset
admin_strings.py   + fa/en/tr strings for every new screen
```

Dependency direction stays one-way, matching the existing pattern: `trade_map` knows nothing about
the bot, `trade_map_admin` receives its helpers through `init()`, and `trade_system` calls into
`trade_map` but never the reverse.

---

## Workstream 1 — Real deletion of custom types

`asset_catalog.remove(key)` replaces hiding as the terminal operation. It refuses on builtins
(`CatalogError('builtin')`) and otherwise cascades:

1. Buildings whose `produces == key` → `produces=''`, `output=0`.
2. `asset_upgrade_costs` rows where `building=key` **or** `resource=key` → deleted.
3. `asset_labels` rows for the key → deleted.
4. `asset_catalog` row → deleted.
5. `ALTER TABLE users DROP COLUMN <key>`.

Step 5 needs SQLite ≥ 3.35. The dev box runs 3.49.1, but the deploy box is unknown, so the call is
wrapped: on `OperationalError` the catalog rows are still removed (the type disappears from the
game) and the orphaned column is left in place, with the fallback reported to the caller so the
admin sees an honest message rather than a silent half-delete.

`hide()`/`unhide()` are kept. They are now a genuinely different tool — hide is a reversible
admin-level "switch this off for now", delete is an owner-level "this never existed". The entry
screen labels them so the difference is not guesswork.

### The in-flight guard

`_give()` and `_refund()` build `UPDATE users SET <col> = <col> + ?` from a trade's stored goods
keys. Dropping a column while a shipment carries it makes the refund raise `OperationalError` and
the cargo disappears. Deletion therefore refuses with `CatalogError('in_transit')` when any
non-terminal trade carries the key.

To keep the dependency one-way, `asset_catalog` exposes `set_delete_guard(fn)`; `main*.py` wires it
to a new `trade_system.active_goods_keys()` after both modules are initialised. Unwired, the guard
defaults to "nothing in flight", so the catalog stays independently testable.

### UI

On the entry screen, non-builtin types gain 🗑 **حذف کامل**. It opens a confirmation screen naming
the key, listing how many groups hold a non-zero value for it, and warning that the numbers are
destroyed. Confirming requires owner. Both the confirm screen and the applied delete are logged.

---

## Workstream 2 — Reordering

`asset_catalog.move(key, direction)` where direction is `'up'`/`'down'`. It loads the same-kind
entries in display order (including hidden ones, so ordering stays stable when a type is toggled),
finds the key, and swaps `position` with its neighbour. Returns `False` at either end.

Seeded positions step by 10 and custom types append at `MAX+10`, but nothing enforces uniqueness, so
`move()` first calls a private `_renumber(kind)` when it detects a collision — rewriting that kind's
positions as 10, 20, 30… before swapping. That keeps the swap a simple two-row update.

Ordering is *within kind*: `entries()` sorts resource → unit → building first. This satisfies the
actual request, since "جمعیت" and "پول" are both resources.

UI: ⬆️/⬇️ on the entry screen (`ap:catmv:<key>:u|d`), admin-level, re-rendering the entry screen
after each move. The entry text gains a rank line ("۳ از ۹") so the admin can see the effect without
navigating back to the list.

---

## Workstream 3 — The trade map editor

### Tables

```sql
trade_nodes(id TEXT PRIMARY KEY, mode TEXT, kind TEXT, home INTEGER,
            position INTEGER, builtin INTEGER)
trade_node_labels(node_id TEXT, lang TEXT, label TEXT, PRIMARY KEY (node_id, lang))
trade_edges(id INTEGER PRIMARY KEY AUTOINCREMENT, mode TEXT, a TEXT, b TEXT,
            units INTEGER NOT NULL, minutes INTEGER NOT NULL DEFAULT 0,
            UNIQUE (mode, a, b))
```

Seeded on first run from today's `SEA_NODES` / `LAND_NODES` / `SEA_EDGES` / `LAND_EDGES` with
`builtin=1`, via `INSERT OR IGNORE` so admin edits survive restarts — the same pattern
`asset_catalog._seed()` already uses. Existing databases keep working untouched: node ids continue
to match `users.home_sea`, `users.home_land`, `chokepoint_owners.node_id` and the `toll_<id>` keys
in `trade_config`.

Node ids are validated against `^[a-z][a-z0-9_]{1,15}$` because they compose into `toll_<id>` config
keys and are stored as foreign references in three places.

### The two-field edge

`units` keeps its current meaning: it drives `base_fee = units × fee_per_unit` and the
cheapest-route Dijkstra cost. `minutes` is the timing override — `0` means "derive as
`units × min_per_unit`", non-zero means "this leg takes exactly this long". So an admin can set
Suez→Red Sea to 40 minutes without moving any prices, which is the manual timing that was asked for.

`_route_info()` changes one line: `leg_minutes` reads the per-edge override where set and falls back
to the existing product. Fee computation is untouched.

### Cache invalidation

`trade_system` memoises `_adj_cache` and `_edge_w_cache`. `trade_map` exposes `on_change(fn)`;
`trade_system` registers a cache-clearing callback at init. Every mutator fires it.

### Node removal cascade

Removing a node deletes its edges, clears its `chokepoint_owners` row, blanks `home_sea`/`home_land`
for any group pointing at it, and deletes its `toll_<id>` config key. It **refuses** when any
non-terminal trade's stored route includes the node — same reasoning as the catalog guard, though
milder: `trades.leg_minutes` and `trades.route` are snapshotted at departure, so in-flight
shipments are immune to renames and retimes. Only removal can strand them.

### Screens

`trd:map` → pick sea/land → node list (paged) and edge list.

- **Node screen**: rename per language, kind, home yes/no, toll, owner, delete. Toll and owner are
  editable elsewhere today (`trd:cfg`, `trd:ow`); surfacing them here means one screen per node
  instead of three menus. The existing screens stay.
- **Edge screen**: units, minutes, delete.
- **Add node** / **add edge** wizards, following the `_collect_labels` pattern already in
  `asset_admin`.

Everything is admin-level except node and edge *deletion*, which is owner-level. That last point is
an extrapolation from the stated "destructive ops are owner-only" rule rather than something
explicitly decided — worth a second look during review.

---

## Workstream 4 — Clearing the action log

`admin_panel.clear_log()` runs `DELETE FROM admin_log`. Owner-only, behind a confirmation screen
showing the row count. Reachable from the log screen itself.

The wipe deliberately leaves **no** entry behind — the point was "اصلا این اتفاقات نیفتاده", and a
self-documenting wipe defeats it. An audit trail that can be erased without a trace is still worth
flagging to the people it covers, so the wipe instead calls the existing `notify_admins()` to send
every admin a message naming who cleared it and how many rows went. The log reads clean; the action
is not invisible.

---

## Workstream 5 — Catalog factory reset

`asset_catalog.factory_reset()`:

1. Every non-builtin key is checked against the in-flight guard **first**, as a single pass over the
   whole set. If any key is carried by a live trade the reset aborts before touching anything and
   names the offending keys. Only once the set is clear does each key go through `remove()` — same
   cascade, same column drops.
2. Builtin rows are rewritten from `BUILTIN_*`: `position`, `default_value`, `produces`, `output`,
   `tradeable`, and `hidden=0`.
3. Builtin labels are rewritten for all three languages.
4. `asset_upgrade_costs` is emptied and re-seeded from `BUILTIN_COSTS`.

Countries' stored numbers are untouched, per the scope decision. Users keep whatever gold they had;
what resets is the *shape* of the game.

The panel screen (`ap:fac`) is owner-only, two-step, and lists exactly which custom types will be
destroyed before the confirm button appears. Confirming also clears the action log, since that was
part of the same request. The standalone log wipe stays available separately.

---

## Testing

The repo has `tests/stubs.py` plus a test file per module; these follow it.

**`test_asset_catalog.py`** — `remove()` drops the column, clears labels, costs and dependent
`produces`; refuses builtins; refuses when the guard reports the key in flight; falls back cleanly
when `DROP COLUMN` is unavailable. `move()` up, down, at both ends, and across a position collision.
`factory_reset()` restores every shipped value and drops every custom column, and aborts atomically
when a key is guarded.

**`test_trade_map.py`** — seeding is idempotent across two `init()` calls and does not overwrite
edits; id validation; node removal cascades to edges, owners, homes and the toll key; removal
refuses on an in-flight route. **Regression:** the seeded graph reproduces `SEA_EDGES`/`LAND_EDGES`
exactly, and `find_routes()` returns identical paths to the pre-change implementation for a sample
of node pairs — this is the test that proves the extraction changed nothing.

**`test_trade_system.py`** — `_route_info()` honours a per-edge minutes override, and `base_fee` is
unchanged when it does.

**`test_admin_panel.py`** — log wipe and factory reset both refuse a non-owner; the confirm flows
require the second step; `notify_admins` fires on wipe.

## Build order

1. **Reorder** — smallest, self-contained, and the thing AHMAD hit most recently.
2. **Delete + guard hook** — needs `active_goods_keys()` in `trade_system`.
3. **Factory reset** — builds on `remove()`.
4. **Log wipe** — tiny and independent.
5. **Map editor** — largest; independent of 1–4, so it can slip without blocking them.

Each step lands with its strings in `admin_strings.py` for fa, en and tr, and with its tests.
