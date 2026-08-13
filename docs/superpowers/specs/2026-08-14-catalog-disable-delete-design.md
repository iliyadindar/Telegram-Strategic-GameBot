# Disabling and deleting any asset type, and ordering the status sections

## The problem

Two complaints, both from an admin trying to reshape the game from inside Telegram.

**Everything that shipped with the game is frozen.** `hide()` and `remove()` both
refuse a `builtin` row, and `_entry_screen()` only draws the disable and delete
buttons when `builtin` is false. So an admin who wants a game without meat, or
without cavalry, or without a bank, can retune the numbers and rename the label
but can never take the type off the list. Only types they added themselves can
go away. The entry screen says as much — "قابل ویرایش هست اما حذف نمی‌شود" — which
is the behaviour, not a bug, but it is the wrong behaviour: the catalog exists so
the shape of the game is the admin's to decide.

**The status message has a fixed section order.** `💰 دارایی` then `⚔️ ارتش` then
`🏭 ساختمان‌ها` then `📜 معاهدات`, baked into a four-slot format string in each of
three languages, plus a hardcoded `CASE kind` in `entries()`. Cannons and ships
live in the army section, and the admin wants that section below buildings.

## What this changes

1. Every type — shipped or added — gets a disable button and a delete button.
2. Four keys the trade engine addresses by name can be disabled but not deleted.
3. A deleted builtin stays deleted across restarts.
4. The three status sections can be reordered from the panel. They ship in the
   order the admin asked for: resources → buildings → army.

## Disable versus delete

Both already exist and they are not the same thing. Keeping them distinct matters
because one is a display decision and the other destroys player data.

`hide()` takes the type out of the game — out of `/دارایی`, out of the upgrade
menu, out of the trade cargo list, out of weekly production. The `users` column
and every group's number in it survive untouched, so `unhide()` puts the game
back exactly as it was. This is what an admin wants nine times out of ten.

`remove()` drops the column. Every group's holding of that type is gone and no
reset brings the numbers back. `factory_reset()` restores the *type*, at its
shipped default, with every group starting from zero.

The panel already words these differently and that stays: `🗑 حذف از بازی` for the
reversible one, `❌ حذف کامل و همیشگی` behind a confirmation screen for the other.

## Engine keys

`trade_system` does not go through the catalog for four columns. It writes SQL
naming them:

| key | where |
|---|---|
| `money` | `trade_system.py:764` fee and toll totals, `:814` escrow, `:844` refund, `:870` every live trade holds an escrowed fee, `:1517` toll income |
| `small_ships`, `medium_ships`, `large_ships` | `trade_system.py:83-88` `SHIPS`, and the capacity config keyed off it |

Dropping any of those columns means the next refund or toll payout raises on a
column that no longer exists, and whatever cargo was in flight is lost. So:

```python
ENGINE_KEYS = frozenset({'money', 'small_ships', 'medium_ships', 'large_ships'})
```

`remove()` raises `CatalogError('engine_key')` for these. `hide()` accepts them —
hiding keeps the column, so the trade system keeps working against a currency
players no longer see. That is a strange game but not a broken one, and it is the
admin's call.

Note what is *not* on this list. The war flow (`main.py:307-366`) is announcement
text only; it never reads a unit column. No unit key needs protecting.

## Tombstones

`init()` runs `_seed()` on every start, and `_seed()` is `INSERT OR IGNORE` over
`BUILTIN_*`. Delete `meat` and the next restart hands it straight back. So
deletion of a builtin has to be recorded:

```sql
CREATE TABLE IF NOT EXISTS asset_removed (key TEXT PRIMARY KEY)
```

`remove()` writes the key there when the row was `builtin`. `_seed()` skips
tombstoned keys in all three seed tables — catalog row, labels and upgrade costs —
so nothing orphaned is left behind either.

`factory_reset()` empties the table first, then re-seeds, then calls
`ensure_columns()`. That last call does not exist today and without it a
factory reset after a builtin deletion restores the catalog row while the column
stays dropped, and the next `SELECT` in `show_assets()` raises. It is a latent
bug that only becomes reachable once builtins can be deleted.

A tombstone is not cleared by `add()`. An admin who deletes `meat` and later adds
a type keyed `meat` gets an ordinary custom type, and `_seed()` leaves it alone
because a row already exists. Only a factory reset makes it builtin again.

## Section order

```sql
CREATE TABLE IF NOT EXISTS asset_kind_order (kind TEXT PRIMARY KEY, position INTEGER NOT NULL)
```

Seeded `resource=10, building=20, unit=30` — the order asked for. `kind_order()`
returns the kinds sorted; `move_kind(kind, direction)` swaps neighbours the way
`move()` already does for types within a kind.

`entries()` builds its `ORDER BY` from `kind_order()` instead of the fixed
`CASE kind WHEN 'resource' THEN 0 …`. The values are interpolated into SQL, which
is safe only because they come from the `KINDS` constant and never from input;
`kind_order()` filters to `KINDS` before returning for exactly that reason.

The status text stops being a four-slot template. `assets_title` becomes
`{sections}` plus the treaties block, and the caller joins one block per kind in
`kind_order()`. Section headers move into their own strings — `sec_resource`,
`sec_unit`, `sec_building` — separate from the existing `kind_*` strings, which
name catalog categories (`📦 منابع`) rather than status sections (`💰 دارایی`).

Same treatment for `group_card` in the panel. `editor_menu()` and the catalog
home screen follow `kind_order()` too, so the panel and the player see one order.

## A bug found on the way

`upgrade_cost()` returns every cost row, including ones naming a hidden resource.
`_charge_and_upgrade()` then deducts a resource the group cannot see anywhere in
the game. It now filters to visible resources. The rows stay in
`asset_upgrade_costs`, so re-enabling the resource restores the cost.

## Testing

- disable and re-enable a builtin; it leaves and rejoins `all_keys()`
- delete a builtin; it is gone after a fresh `init()` on the same database
- `remove('money')` and each ship key raises `engine_key`
- `hide('money')` succeeds
- factory reset after deleting a builtin: the type is back, the column exists,
  and a `SELECT` over `all_keys()` runs
- `kind_order()` default, `move_kind()` at both ends, and `entries()` following it
- `show_assets()` renders sections in the configured order
- a hidden resource is not charged on upgrade

Two existing tests assert the old rule and get inverted:
`test_asset_catalog.py:243` (hiding a builtin raises) and `:375` (removing one
raises).

## Risks

Permanent deletion is permanent. The confirmation screen already reports how many
countries hold a non-zero amount via `holders()`; for a builtin it says so more
loudly. Nothing else guards it, by design — the admin asked for the sharp tool.
