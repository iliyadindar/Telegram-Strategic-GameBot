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

    def test_builtins_cannot_be_hidden(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.hide('money')

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


if __name__ == '__main__':
    unittest.main()
