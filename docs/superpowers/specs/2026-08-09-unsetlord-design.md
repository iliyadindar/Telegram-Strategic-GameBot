# /unsetlord — taking a lordship back

Design doc — 2026-08-09

## Why

`/setlord` is one-way. An admin who replies to the wrong message, or a group that leaves the
game, leaves a `users` row nobody can remove from inside Telegram. The only escape today is
editing `game_bot.db` by hand.

Two shapes are wanted, and they are not the same operation:

* **a user** — the wrong person was made lord; take it off them.
* **a group** (گپ) — the whole country is finished; remove every lord it has.

This doc also settles three review comments left on PR #8, all in the map editor.

## What a lordship actually is

There is no registration table. `users` *is* the country: one row holds the group id, every
asset column, and `home_sea` / `home_land`. So unsetting a lord deletes their assets with them.
That is the honest reading of the feature, not a side effect to be engineered away — but it
means every path to it needs a confirmation and a guard.

## Scope decisions

| Decision | Choice |
|---|---|
| Reply form | `/unsetlord` in reply to a player removes that player's row. |
| No-reply form | `/unsetlord` alone in a group offers a confirm button that removes **every** lord of that group. |
| Permissions | Removing one player is admin-level, like `/setlord`. Wiping a whole group is owner-only, like node deletion and factory reset. |
| Live trades | Refuse. A group with an `offered` or `active` trade cannot be unset until it lands. |
| Chokepoints | A removed group's `chokepoint_owners` rows are cleared in the same transaction. |
| Feature flag | The existing `setlord` toggle gates both. Lord registration is one feature. |
| Confirmation | The reply form acts immediately (it names one visible person and is already an explicit reply). The group form requires a button press. |
| Out of scope | Un-setting from the `/admin` panel's group list, and moving a lordship between users (that is `/unsetlord` then `/setlord`). |

### Why refuse rather than refund

`trade_system._give()` and `_refund()` are `UPDATE users SET <col> = <col> + ? WHERE group_id=?`.
Against a deleted row that updates nothing and reports nothing: the escrowed fee and the cargo
are simply gone, and the counterparty is left tracking a convoy that will never be credited.
Refunding first does not help — the refund lands in a row that is about to be deleted. So the
group is refused while anything is in flight, in the same words the map editor already uses for
a node a convoy is sailing towards.

## Architecture

```
trade_system.py  + active_trade_groups()      group ids with a live trade
admin_panel.py   + handle_unsetlord(message)  /unsetlord
                 + set_lord_guard()           receives active_trade_groups
                 + _unset_group_ask/_apply    the confirm, and the ap:ulc: tap
                 + _drop_lords()              the one place a users row dies
admin_strings.py + fa/en/tr strings, + lord_unassign / group_unassign actions
main*.py         + the /unsetlord handler, three entrypoints
```

The guard is injected, not imported: `admin_panel` must not learn about `trade_system`, because
`trade_system.init()` already depends on `admin_panel.is_admin`. `main*.py` wires it after both
are up, exactly as it already wires `asset_catalog.set_delete_guard`. With no guard registered
— `admin_panel` used on its own, in tests — nothing is in flight and the removal proceeds.

`_drop_lords(group_id, user_id=None)` is the single deletion path. It checks the guard, deletes
the matching `users` rows, clears `chokepoint_owners` for the group when no lord is left, and
returns the ids it removed. Both entry points go through it, so there is one place where a
country can die.

## Flow

```
/unsetlord (reply)   admin? -> feature on? -> target is a lord here? -> guard clear?
                     -> delete row -> log lord_unassign -> reply naming the ex-lord

/unsetlord (alone)   admin? -> feature on? -> owner? -> group has lords?
                     -> confirm keyboard carrying ap:ulc:<gid>
                     -> tap -> owner? -> guard clear? -> delete every row
                     -> log group_unassign -> report the count
```

The guard is re-checked inside `ap:ulc:` rather than trusted from the confirm screen: a trade
can be offered between the two taps.

## Errors

| Case | Answer |
|---|---|
| Not a group chat | `setlord_group_only` — reused, the command has the same constraint. |
| Feature off | `feature_disabled`. |
| Not admin / not owner | `unsetlord_not_admin` / `unsetlord_not_owner`. |
| Replied-to user is not a lord here | `unsetlord_err_not_lord`. |
| No lords in the group | `unsetlord_no_lords`. |
| Live trade | `unsetlord_err_in_trade` — wait for the shipment to arrive. |
| Guard raised | `unsetlord_err_guard_unavailable` — nothing is deleted. |

The last four are `LordError` codes raised by `_drop_lords()` and looked up as
`unsetlord_err_<code>`, the same shape `trade_map`'s `MapError` codes already use.

## Review comments from PR #8

**1. Blank name stores the language code.** `_collect_names()` fell back to `lang` when the
admin sent whitespace, so a node could end up called "en". It now keeps the node's current
label for that language if it has one, and re-asks when it does not — a rename should never be
able to make a name worse than it was.

**2. The node picker is one unbounded keyboard.** `_pick_node()` drew a button per node. The
seeded map is 38 sea nodes and Telegram's practical limit is near, so an admin who adds a few
more gets a failed send. It paginates through the same `_page()`/`_nav()` helpers the node and
edge lists already use, under two new ops (`maep`, `mae1p`) that carry the page.

**3. `trade_map._cache` is read and written without the lock.** The ticker thread reads the map
while an admin edits it. The dangerous interleaving is not a torn read — it is a reader that
computes a value, has `_invalidate()` run underneath it, and then writes its now-stale value
into the cache, where it stays until the next edit. Every cache read, fill and clear moves
inside `_lock`, which is reentrant and already held by `_q`, so the compute-and-store is atomic
against mutators.

## Testing

* Reply form removes the row; a non-lord target is refused; a non-admin is refused.
* Group form is refused for a promoted admin and accepted for the owner.
* A group with a live trade is refused, and its row survives.
* The guard raising leaves everything in place.
* `chokepoint_owners` is cleared for the removed group.
* Blank rename input keeps the existing label.
* The picker pages when the map is larger than one page.
* `trade_map` reads stay correct under a mutation from another thread.
