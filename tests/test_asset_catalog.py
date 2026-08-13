# -*- coding: utf-8 -*-
"""The asset catalog: seeding, adding types, costs, production and hiding."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asset_catalog as catalog
from stubs import make_db


class CatalogTestCase(unittest.TestCase):

    def setUp(self):
        self.conn = make_db()
        self.addCleanup(self.conn.close)

    def columns(self):
        return {row[1] for row in self.conn.execute("PRAGMA table_info(users)").fetchall()}


class SeedingTest(CatalogTestCase):

    def test_every_builtin_type_is_registered(self):
        keys = set(catalog.all_keys())
        for key in catalog.BUILTIN_RESOURCES + catalog.BUILTIN_UNITS:
            self.assertIn(key, keys)
        for key, _, _ in catalog.BUILTIN_BUILDINGS:
            self.assertIn(key, keys)

    def test_kinds_are_assigned_correctly(self):
        self.assertEqual(set(catalog.keys('resource')), set(catalog.BUILTIN_RESOURCES))
        self.assertEqual(set(catalog.keys('unit')), set(catalog.BUILTIN_UNITS))
        self.assertEqual(set(catalog.keys('building')),
                         {key for key, _, _ in catalog.BUILTIN_BUILDINGS})

    def test_defaults_match_the_shipped_values(self):
        defaults = catalog.defaults()
        self.assertEqual(defaults['money'], 2000)
        self.assertEqual(defaults['swordsmen'], 1500)
        self.assertEqual(defaults['bank'], 0)

    def test_builtins_are_marked_as_such(self):
        self.assertTrue(catalog.is_builtin('money'))
        self.assertFalse(catalog.is_builtin('nothing_like_this'))

    def test_every_builtin_resource_starts_tradeable(self):
        self.assertEqual(set(catalog.tradeable_resources()), set(catalog.BUILTIN_RESOURCES))

    def test_labels_come_back_per_language(self):
        self.assertIn('Money', catalog.label('money', 'en'))
        self.assertIn('پول', catalog.label('money', 'fa'))
        self.assertIn('Para', catalog.label('money', 'tr'))

    def test_unknown_key_falls_back_to_the_key_itself(self):
        self.assertEqual(catalog.label('no_such_thing', 'en'), 'no_such_thing')

    def test_seeding_twice_does_not_duplicate_or_reset(self):
        catalog.set_default('money', 999)
        catalog.init(self.conn)
        self.assertEqual(catalog.defaults()['money'], 999)
        self.assertEqual(len(catalog.keys('resource')), len(catalog.BUILTIN_RESOURCES))

    def test_production_covers_every_builtin_building(self):
        plan = {building: (produces, output) for building, produces, output in catalog.production()}
        for building, produces, output in catalog.BUILTIN_BUILDINGS:
            self.assertEqual(plan[building], (produces, output))

    def test_upgrade_costs_are_seeded(self):
        self.assertEqual(catalog.upgrade_cost('stone_factory'), {'wood': 500, 'money': 500})

    def test_gold_mine_cost_matches_what_the_old_code_deducted(self):
        # The legacy checker tested iron here while the deduction took wood.
        self.assertEqual(catalog.upgrade_cost('gold_mine'),
                         {'wood': 500, 'stones': 500, 'money': 500})


class AddTypeTest(CatalogTestCase):

    def add_archers(self):
        return catalog.add('archers', 'unit',
                           {'fa': '🏹 کماندار', 'en': '🏹 Archers', 'tr': '🏹 Okçu'},
                           default_value=750)

    def test_adding_a_unit_creates_its_column(self):
        self.add_archers()
        self.assertIn('archers', self.columns())

    def test_added_type_appears_in_its_kind(self):
        self.add_archers()
        self.assertIn('archers', catalog.keys('unit'))
        self.assertNotIn('archers', catalog.keys('resource'))

    def test_added_type_carries_its_labels(self):
        self.add_archers()
        self.assertEqual(catalog.label('archers', 'en'), '🏹 Archers')
        self.assertEqual(catalog.label('archers', 'fa'), '🏹 کماندار')

    def test_added_type_is_not_builtin(self):
        self.add_archers()
        self.assertFalse(catalog.is_builtin('archers'))

    def test_existing_groups_receive_the_starting_amount(self):
        self.conn.execute("INSERT INTO users (user_id, group_id) VALUES (1, -1)")
        self.conn.commit()
        self.add_archers()
        row = self.conn.execute("SELECT archers FROM users WHERE group_id=-1").fetchone()
        self.assertEqual(row[0], 750)

    def test_a_new_resource_can_be_made_tradeable(self):
        catalog.add('spice', 'resource', {'en': 'Spice'}, default_value=10, tradeable=1)
        self.assertIn('spice', catalog.tradeable_resources())

    def test_a_new_building_can_train_the_new_unit(self):
        self.add_archers()
        catalog.add('archery_range', 'building', {'en': 'Archery Range'},
                    default_value=0, produces='archers', output=400)
        self.assertIn(('archery_range', 'archers', 400), catalog.production())

    def test_duplicate_key_is_refused(self):
        self.add_archers()
        with self.assertRaises(catalog.CatalogError):
            self.add_archers()

    def test_reserved_key_is_refused(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.add('group_id', 'unit', {'en': 'Nope'})

    def test_key_colliding_with_an_existing_column_is_refused(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.add('treaties', 'unit', {'en': 'Nope'})

    def test_sql_injection_shaped_keys_are_refused(self):
        for bad in ('archers; DROP TABLE users', 'Archers', '1archers', 'a', '', 'arch ers',
                    'archers--', "arch'ers"):
            with self.subTest(bad):
                with self.assertRaises(catalog.CatalogError):
                    catalog.add(bad, 'unit', {'en': 'Nope'})

    def test_bad_kind_is_refused(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.add('widgets', 'gadget', {'en': 'Nope'})

    def test_a_building_cannot_produce_another_building(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.add('meta_factory', 'building', {'en': 'Nope'}, produces='bank', output=5)

    def test_a_building_cannot_produce_an_unknown_type(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.add('ghost_factory', 'building', {'en': 'Nope'},
                        produces='phantoms', output=5)


class EditTypeTest(CatalogTestCase):

    def test_renaming_a_builtin_is_allowed(self):
        catalog.set_labels('money', {'en': '💰 Coin'})
        self.assertEqual(catalog.label('money', 'en'), '💰 Coin')

    def test_renaming_one_language_leaves_the_others(self):
        catalog.set_labels('money', {'en': '💰 Coin'})
        self.assertIn('پول', catalog.label('money', 'fa'))

    def test_default_can_be_retuned(self):
        catalog.set_default('money', 5000)
        self.assertEqual(catalog.defaults()['money'], 5000)

    def test_output_can_be_retuned(self):
        catalog.set_output('bank', 'money', 3000)
        self.assertIn(('bank', 'money', 3000), catalog.production())

    def test_a_building_can_be_told_to_produce_nothing(self):
        catalog.set_output('bank', '', 0)
        self.assertNotIn('bank', [b for b, _, _ in catalog.production()])

    def test_output_on_a_non_building_is_refused(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.set_output('money', 'gold', 10)

    def test_tradeable_can_be_switched_off(self):
        catalog.set_tradeable('money', 0)
        self.assertNotIn('money', catalog.tradeable_resources())

    def test_tradeable_on_a_unit_is_refused(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.set_tradeable('swordsmen', 1)

    def test_upgrade_cost_can_be_changed(self):
        catalog.set_upgrade_cost('bank', 'gold', 1234)
        self.assertEqual(catalog.upgrade_cost('bank')['gold'], 1234)

    def test_zero_removes_a_cost_line(self):
        catalog.set_upgrade_cost('bank', 'gold', 0)
        self.assertNotIn('gold', catalog.upgrade_cost('bank'))

    def test_cost_must_name_a_resource(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.set_upgrade_cost('bank', 'swordsmen', 10)

    def test_cost_on_a_non_building_is_refused(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.set_upgrade_cost('money', 'gold', 10)

    def test_editing_an_unknown_key_is_refused(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.set_default('phantom', 1)


class HideTest(CatalogTestCase):

    def setUp(self):
        super().setUp()
        catalog.add('archers', 'unit', {'en': 'Archers'}, default_value=750)
        self.conn.execute("INSERT INTO users (user_id, group_id) VALUES (1, -1)")
        self.conn.execute("UPDATE users SET archers=42 WHERE group_id=-1")
        self.conn.commit()

    def test_hiding_removes_it_from_the_game(self):
        catalog.hide('archers')
        self.assertNotIn('archers', catalog.all_keys())
        self.assertNotIn('archers', catalog.keys('unit'))

    def test_hiding_keeps_the_column_and_the_numbers(self):
        catalog.hide('archers')
        row = self.conn.execute("SELECT archers FROM users WHERE group_id=-1").fetchone()
        self.assertEqual(row[0], 42)

    def test_restoring_brings_the_numbers_back(self):
        catalog.hide('archers')
        catalog.unhide('archers')
        self.assertIn('archers', catalog.all_keys())
        row = self.conn.execute("SELECT archers FROM users WHERE group_id=-1").fetchone()
        self.assertEqual(row[0], 42)

    def test_hidden_types_still_listed_when_asked_for(self):
        catalog.hide('archers')
        self.assertIn('archers', catalog.all_keys(include_hidden=True))

    def test_builtins_can_be_hidden_and_restored(self):
        catalog.hide('meat')
        self.assertNotIn('meat', catalog.all_keys())
        catalog.unhide('meat')
        self.assertIn('meat', catalog.all_keys())

    def test_an_engine_key_can_still_be_hidden(self):
        # Hiding keeps the column, so trade_system's direct SQL keeps working.
        catalog.hide('money')
        self.assertNotIn('money', catalog.all_keys())
        self.assertIn('money', self.columns())

    def test_hiding_a_resource_stops_it_being_charged_for_upgrades(self):
        self.assertIn('wood', catalog.upgrade_cost('stone_factory'))
        catalog.hide('wood')
        self.assertNotIn('wood', catalog.upgrade_cost('stone_factory'))
        catalog.unhide('wood')
        self.assertIn('wood', catalog.upgrade_cost('stone_factory'))

    def test_hiding_a_produced_type_drops_it_from_production(self):
        catalog.add('archery_range', 'building', {'en': 'Archery Range'},
                    produces='archers', output=400)
        self.assertIn('archery_range', [b for b, _, _ in catalog.production()])
        catalog.hide('archers')
        self.assertNotIn('archery_range', [b for b, _, _ in catalog.production()])

    def test_hiding_a_tradeable_resource_removes_it_from_trade(self):
        catalog.add('spice', 'resource', {'en': 'Spice'}, tradeable=1)
        self.assertIn('spice', catalog.tradeable_resources())
        catalog.hide('spice')
        self.assertNotIn('spice', catalog.tradeable_resources())


class OrderTest(CatalogTestCase):

    def resources(self):
        return list(catalog.keys('resource'))

    def test_a_new_resource_lands_at_the_bottom(self):
        catalog.add('peoples', 'resource', {'en': 'Peoples'})
        self.assertEqual(self.resources()[-1], 'peoples')

    def test_moving_up_swaps_with_the_neighbour(self):
        before = self.resources()
        self.assertTrue(catalog.move(before[3], 'up'))
        after = self.resources()
        self.assertEqual(after[2], before[3])
        self.assertEqual(after[3], before[2])

    def test_moving_down_swaps_the_other_way(self):
        before = self.resources()
        self.assertTrue(catalog.move(before[0], 'down'))
        self.assertEqual(self.resources()[1], before[0])

    def test_a_new_type_can_be_walked_to_the_top(self):
        # AHMAD's case: 'peoples' is added under clothes and belongs above money.
        catalog.add('peoples', 'resource', {'en': 'Peoples'})
        while catalog.move('peoples', 'up'):
            pass
        self.assertEqual(self.resources()[0], 'peoples')

    def test_moving_past_the_top_reports_no_move(self):
        self.assertFalse(catalog.move(self.resources()[0], 'up'))

    def test_moving_past_the_bottom_reports_no_move(self):
        self.assertFalse(catalog.move(self.resources()[-1], 'down'))

    def test_order_survives_a_collision_in_positions(self):
        self.conn.execute("UPDATE asset_catalog SET position=10 WHERE kind='resource'")
        self.conn.commit()
        before = self.resources()
        self.assertTrue(catalog.move(before[2], 'up'))
        after = self.resources()
        self.assertEqual(after[1], before[2])
        self.assertEqual(len(after), len(before))

    def test_moving_does_not_cross_into_another_kind(self):
        first_unit = catalog.keys('unit')[0]
        self.assertFalse(catalog.move(first_unit, 'up'))
        self.assertEqual(catalog.keys('unit')[0], first_unit)

    def test_hidden_types_still_hold_their_place(self):
        catalog.add('peoples', 'resource', {'en': 'Peoples'})
        catalog.add('spice', 'resource', {'en': 'Spice'})
        catalog.hide('peoples')
        self.assertTrue(catalog.move('spice', 'up'))
        self.assertEqual(catalog.keys('resource', include_hidden=True)[-1], 'peoples')

    def test_rank_reports_place_within_the_kind(self):
        place, total = catalog.rank(self.resources()[0])
        self.assertEqual(place, 1)
        self.assertEqual(total, len(catalog.BUILTIN_RESOURCES))

    def test_a_bad_direction_is_refused(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.move('money', 'sideways')


class RemoveTest(CatalogTestCase):

    def setUp(self):
        super().setUp()
        catalog.add('archers', 'unit', {'en': 'Archers'}, default_value=750)
        self.conn.execute("INSERT INTO users (user_id, group_id) VALUES (1, -1)")
        self.conn.execute("UPDATE users SET archers=42 WHERE group_id=-1")
        self.conn.commit()
        self.addCleanup(catalog.set_delete_guard, None)

    def test_removing_drops_the_column(self):
        self.assertTrue(catalog.remove('archers'))
        self.assertNotIn('archers', self.columns())

    def test_removing_takes_the_type_out_of_the_catalog(self):
        catalog.remove('archers')
        self.assertNotIn('archers', catalog.all_keys(include_hidden=True))
        self.assertIsNone(catalog.entry('archers'))

    def test_removing_takes_its_labels_with_it(self):
        catalog.remove('archers')
        self.assertEqual(catalog.labels('archers'), {})

    def test_a_building_that_produced_it_now_produces_nothing(self):
        catalog.add('archery_range', 'building', {'en': 'Range'},
                    produces='archers', output=400)
        catalog.remove('archers')
        self.assertEqual(catalog.entry('archery_range')['produces'], '')
        self.assertEqual(catalog.entry('archery_range')['output'], 0)

    def test_removing_a_resource_clears_costs_that_named_it(self):
        catalog.add('spice', 'resource', {'en': 'Spice'})
        catalog.set_upgrade_cost('bank', 'spice', 40)
        catalog.remove('spice')
        self.assertNotIn('spice', catalog.upgrade_cost('bank'))

    def test_removing_a_building_clears_its_own_costs(self):
        catalog.add('range', 'building', {'en': 'Range'})
        catalog.set_upgrade_cost('range', 'money', 40)
        catalog.remove('range')
        self.assertEqual(catalog.upgrade_cost('range'), {})

    def test_the_key_becomes_free_again(self):
        catalog.remove('archers')
        catalog.add('archers', 'unit', {'en': 'Archers'}, default_value=5)
        self.assertIn('archers', self.columns())
        row = self.conn.execute("SELECT archers FROM users WHERE group_id=-1").fetchone()
        self.assertEqual(row[0], 5)  # the old 42 is gone for good

    def test_a_builtin_can_be_removed(self):
        self.assertTrue(catalog.remove('meat'))
        self.assertNotIn('meat', catalog.all_keys(include_hidden=True))
        self.assertNotIn('meat', self.columns())

    def test_a_removed_builtin_stays_dead_across_a_restart(self):
        catalog.remove('meat')
        catalog.init(self.conn)          # what the next bot start does
        self.assertNotIn('meat', catalog.all_keys(include_hidden=True))
        self.assertNotIn('meat', self.columns())
        self.assertEqual(catalog.labels('meat'), {})

    def test_removing_a_builtin_clears_the_costs_that_named_it(self):
        catalog.remove('wood')
        catalog.init(self.conn)
        self.assertNotIn('wood', catalog.upgrade_cost('stone_factory'))

    def test_engine_keys_cannot_be_removed(self):
        for key in ('money', 'small_ships', 'medium_ships', 'large_ships'):
            with self.assertRaises(catalog.CatalogError, msg=key):
                catalog.remove(key)
            self.assertIn(key, self.columns())

    def test_a_hidden_type_can_still_be_removed(self):
        catalog.hide('archers')
        self.assertTrue(catalog.remove('archers'))
        self.assertNotIn('archers', self.columns())

    def test_a_key_in_flight_is_refused(self):
        catalog.set_delete_guard(lambda: {'archers'})
        with self.assertRaises(catalog.CatalogError):
            catalog.remove('archers')
        self.assertIn('archers', self.columns())

    def test_a_key_not_in_flight_is_allowed(self):
        catalog.set_delete_guard(lambda: {'spice'})
        self.assertTrue(catalog.remove('archers'))

    def test_a_guard_that_cannot_answer_blocks_the_delete(self):
        def broken():
            raise RuntimeError('trade system is down')
        catalog.set_delete_guard(broken)
        with self.assertRaises(catalog.CatalogError):
            catalog.remove('archers')
        self.assertIn('archers', self.columns())

    def test_removing_an_unknown_key_is_refused(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.remove('phantoms')


class FactoryResetTest(CatalogTestCase):

    def setUp(self):
        super().setUp()
        self.conn.execute("INSERT INTO users (user_id, group_id) VALUES (1, -1)")
        self.conn.commit()
        self.addCleanup(catalog.set_delete_guard, None)

    def test_custom_types_are_destroyed(self):
        catalog.add('archers', 'unit', {'en': 'Archers'})
        catalog.add('spice', 'resource', {'en': 'Spice'})
        removed, kept = catalog.factory_reset()
        self.assertEqual(sorted(removed), ['archers', 'spice'])
        self.assertEqual(kept, [])
        self.assertNotIn('archers', self.columns())
        self.assertNotIn('spice', self.columns())

    def test_builtin_labels_are_restored(self):
        catalog.set_labels('money', {'en': '💰 Coin'})
        catalog.factory_reset()
        self.assertEqual(catalog.label('money', 'en'), catalog.BUILTIN_LABELS['en']['money'])

    def test_builtin_defaults_are_restored(self):
        catalog.set_default('money', 999999)
        catalog.factory_reset()
        self.assertEqual(catalog.defaults()['money'], catalog.RESOURCE_DEFAULT)

    def test_builtin_production_is_restored(self):
        catalog.set_output('bank', '', 0)
        catalog.factory_reset()
        self.assertIn(('bank', 'money', 1500), catalog.production())

    def test_builtin_costs_are_restored(self):
        catalog.set_upgrade_cost('bank', 'gold', 4321)
        catalog.factory_reset()
        self.assertEqual(catalog.upgrade_cost('bank'), catalog.BUILTIN_COSTS['bank'])

    def test_a_cost_line_added_to_a_builtin_is_dropped(self):
        catalog.set_upgrade_cost('bank', 'food', 77)
        catalog.factory_reset()
        self.assertNotIn('food', catalog.upgrade_cost('bank'))

    def test_builtin_order_is_restored(self):
        catalog.move('money', 'down')
        catalog.factory_reset()
        self.assertEqual(catalog.keys('resource')[0], 'money')

    def test_a_hidden_builtin_comes_back(self):
        self.conn.execute("UPDATE asset_catalog SET hidden=1 WHERE key='money'")
        self.conn.commit()
        catalog.factory_reset()
        self.assertIn('money', catalog.all_keys())

    def test_tradeable_flags_are_restored(self):
        catalog.set_tradeable('money', 0)
        catalog.factory_reset()
        self.assertIn('money', catalog.tradeable_resources())

    def test_a_deleted_builtin_comes_back_with_its_column(self):
        catalog.remove('meat')
        catalog.factory_reset()
        self.assertIn('meat', catalog.all_keys())
        self.assertIn('meat', self.columns())
        # The whole point of restoring the column: this SELECT used to raise.
        cols = ', '.join(catalog.all_keys())
        row = self.conn.execute(f"SELECT {cols} FROM users WHERE group_id=-1").fetchone()
        self.assertIsNotNone(row)

    def test_a_deleted_builtin_stays_back_after_a_restart(self):
        catalog.remove('meat')
        catalog.factory_reset()
        catalog.init(self.conn)
        self.assertIn('meat', catalog.all_keys())

    def test_section_order_is_restored(self):
        catalog.move_kind('unit', 'up')
        catalog.factory_reset()
        self.assertEqual(catalog.kind_order(), catalog.DEFAULT_KIND_ORDER)

    def test_group_balances_are_left_alone(self):
        self.conn.execute("UPDATE users SET money=7 WHERE group_id=-1")
        self.conn.commit()
        catalog.factory_reset()
        row = self.conn.execute("SELECT money FROM users WHERE group_id=-1").fetchone()
        self.assertEqual(row[0], 7)

    def test_a_key_in_flight_aborts_the_whole_reset(self):
        catalog.add('archers', 'unit', {'en': 'Archers'})
        catalog.add('spice', 'resource', {'en': 'Spice'})
        catalog.set_delete_guard(lambda: {'spice'})
        with self.assertRaises(catalog.CatalogError):
            catalog.factory_reset()
        # nothing was destroyed, not even the key that was free to go
        self.assertIn('archers', self.columns())
        self.assertIn('spice', self.columns())

    def test_reset_with_nothing_custom_is_harmless(self):
        removed, kept = catalog.factory_reset()
        self.assertEqual(removed, [])
        self.assertEqual(set(catalog.keys('resource')), set(catalog.BUILTIN_RESOURCES))


class KindOrderTest(CatalogTestCase):
    """Which of the three sections comes first in the status message."""

    def test_sections_ship_with_buildings_above_the_army(self):
        self.assertEqual(catalog.kind_order(), ('resource', 'building', 'unit'))

    def test_moving_a_section_swaps_it_with_its_neighbour(self):
        self.assertTrue(catalog.move_kind('unit', 'up'))
        self.assertEqual(catalog.kind_order(), ('resource', 'unit', 'building'))

    def test_moving_down_swaps_the_other_way(self):
        self.assertTrue(catalog.move_kind('resource', 'down'))
        self.assertEqual(catalog.kind_order(), ('building', 'resource', 'unit'))

    def test_the_first_section_cannot_move_up(self):
        self.assertFalse(catalog.move_kind('resource', 'up'))
        self.assertEqual(catalog.kind_order(), catalog.DEFAULT_KIND_ORDER)

    def test_the_last_section_cannot_move_down(self):
        self.assertFalse(catalog.move_kind('unit', 'down'))
        self.assertEqual(catalog.kind_order(), catalog.DEFAULT_KIND_ORDER)

    def test_a_bad_direction_is_refused(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.move_kind('unit', 'sideways')

    def test_an_unknown_kind_is_refused(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.move_kind('treaties', 'up')

    def test_the_order_survives_a_restart(self):
        catalog.move_kind('unit', 'up')
        catalog.init(self.conn)
        self.assertEqual(catalog.kind_order(), ('resource', 'unit', 'building'))

    def test_entries_follow_the_section_order(self):
        def kinds_seen():
            seen = []
            for row in catalog.entries():
                if row['kind'] not in seen:
                    seen.append(row['kind'])
            return tuple(seen)

        self.assertEqual(kinds_seen(), ('resource', 'building', 'unit'))
        catalog.move_kind('unit', 'up')
        self.assertEqual(kinds_seen(), ('resource', 'unit', 'building'))

    def test_rank_reports_the_place_in_the_order(self):
        self.assertEqual(catalog.kind_rank('building'), (2, 3))
        catalog.move_kind('building', 'up')
        self.assertEqual(catalog.kind_rank('building'), (1, 3))


if __name__ == '__main__':
    unittest.main()
