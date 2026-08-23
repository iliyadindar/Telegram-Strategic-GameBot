# -*- coding: utf-8 -*-
"""Per-level upgrade costs, per-level yield and the level ceiling."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asset_catalog as catalog
import asset_ui
from stubs import Call, Chat, Message, StubBot, User, make_db

ADMIN = 900
GROUP = -100


class LevelTestCase(unittest.TestCase):

    def setUp(self):
        self.conn = make_db()
        self.addCleanup(self.conn.close)


# ---------------------------------------------------------------------------
# The catalog
# ---------------------------------------------------------------------------


class LevelCostTest(LevelTestCase):

    def test_an_untuned_level_costs_the_flat_price(self):
        flat = catalog.upgrade_cost('bank')
        self.assertEqual(catalog.upgrade_cost('bank', 1), flat)
        self.assertEqual(catalog.upgrade_cost('bank', 40), flat)

    def test_a_tuned_level_overrides_the_flat_price(self):
        catalog.set_level_cost('bank', 7, 'gold', 9000)
        self.assertEqual(catalog.upgrade_cost('bank', 7), {'gold': 9000})
        # every other level is untouched
        self.assertEqual(catalog.upgrade_cost('bank', 6), catalog.upgrade_cost('bank'))

    def test_seeding_a_level_copies_the_flat_price(self):
        seeded = catalog.seed_level_cost('bank', 3)
        self.assertEqual(seeded, catalog.BUILTIN_COSTS['bank'])
        self.assertTrue(catalog.level_cost_is_set('bank', 3))

    def test_zeroing_the_last_resource_returns_the_level_to_the_flat_price(self):
        catalog.set_level_cost('bank', 4, 'gold', 100)
        self.assertTrue(catalog.level_cost_is_set('bank', 4))
        catalog.set_level_cost('bank', 4, 'gold', 0)
        self.assertFalse(catalog.level_cost_is_set('bank', 4))
        self.assertEqual(catalog.upgrade_cost('bank', 4), catalog.upgrade_cost('bank'))

    def test_clearing_a_level_returns_it_to_the_flat_price(self):
        catalog.seed_level_cost('bank', 5)
        catalog.set_level_cost('bank', 5, 'gold', 12345)
        catalog.clear_level_cost('bank', 5)
        self.assertEqual(catalog.upgrade_cost('bank', 5), catalog.upgrade_cost('bank'))

    def test_a_hidden_resource_is_not_charged_at_a_tuned_level(self):
        catalog.set_level_cost('bank', 2, 'gold', 500)
        catalog.hide('gold')
        self.assertNotIn('gold', catalog.upgrade_cost('bank', 2))

    def test_tuned_levels_are_listed_in_order(self):
        for level in (9, 2, 5):
            catalog.set_level_cost('bank', level, 'gold', 10)
        self.assertEqual(catalog.tuned_cost_levels('bank'), (2, 5, 9))

    def test_a_level_outside_the_ceiling_is_refused(self):
        for bad in (0, -1, catalog.LEVEL_CEILING + 1, 'x'):
            with self.assertRaises(catalog.CatalogError):
                catalog.set_level_cost('bank', bad, 'gold', 10)

    def test_only_buildings_and_only_resources(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.set_level_cost('money', 1, 'gold', 10)
        with self.assertRaises(catalog.CatalogError):
            catalog.set_level_cost('bank', 1, 'swordsmen', 10)


class LevelOutputTest(LevelTestCase):

    def test_an_untuned_building_yields_level_times_output(self):
        # bank ships as 1500/level
        self.assertEqual(catalog.output_at_level('bank', 0), 0)
        self.assertEqual(catalog.output_at_level('bank', 1), 1500)
        self.assertEqual(catalog.output_at_level('bank', 4), 6000)

    def test_a_tuned_level_replaces_only_its_own_contribution(self):
        catalog.set_level_output('bank', 3, 10000)
        self.assertEqual(catalog.output_at_level('bank', 2), 3000)
        self.assertEqual(catalog.output_at_level('bank', 3), 1500 * 2 + 10000)
        self.assertEqual(catalog.output_at_level('bank', 4), 1500 * 3 + 10000)

    def test_a_tuned_level_can_be_worth_less(self):
        catalog.set_level_output('bank', 2, 0)
        self.assertEqual(catalog.output_at_level('bank', 2), 1500)

    def test_clearing_a_level_restores_the_flat_yield(self):
        catalog.set_level_output('bank', 2, 99)
        catalog.clear_level_output('bank', 2)
        self.assertEqual(catalog.output_at_level('bank', 2), 3000)

    def test_a_negative_yield_is_refused(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.set_level_output('bank', 2, -5)

    def test_total_yield_never_goes_below_zero(self):
        catalog.set_output('bank', 'money', 0)
        catalog.set_level_output('bank', 1, 25)
        self.assertEqual(catalog.output_at_level('bank', 3), 25)

    def test_a_building_with_no_flat_yield_still_produces_when_a_level_is_tuned(self):
        catalog.set_output('bank', 'money', 0)
        self.assertNotIn('bank', [b for b, _, _ in catalog.production()])
        catalog.set_level_output('bank', 1, 700)
        self.assertIn('bank', [b for b, _, _ in catalog.production()])


class MaxLevelTest(LevelTestCase):

    def test_buildings_ship_uncapped(self):
        self.assertEqual(catalog.max_level('bank'), 0)
        self.assertFalse(catalog.at_max_level('bank', 999))

    def test_a_cap_stops_the_next_upgrade(self):
        catalog.set_max_level('bank', 20)
        self.assertFalse(catalog.at_max_level('bank', 19))
        self.assertTrue(catalog.at_max_level('bank', 20))
        self.assertTrue(catalog.at_max_level('bank', 21))

    def test_zero_lifts_the_cap(self):
        catalog.set_max_level('bank', 20)
        catalog.set_max_level('bank', 0)
        self.assertFalse(catalog.at_max_level('bank', 500))

    def test_only_buildings_can_be_capped(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.set_max_level('money', 5)

    def test_a_cap_beyond_the_ceiling_is_refused(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.set_max_level('bank', catalog.LEVEL_CEILING + 1)

    def test_a_lowered_cap_leaves_existing_levels_alone(self):
        self.conn.execute("INSERT INTO users (user_id, group_id, bank) VALUES (1, ?, 30)",
                          (GROUP,))
        self.conn.commit()
        catalog.set_max_level('bank', 20)
        row = self.conn.execute("SELECT bank FROM users WHERE group_id=?", (GROUP,)).fetchone()
        self.assertEqual(row[0], 30)


class FactoryResetTest(LevelTestCase):

    def test_reset_clears_per_level_tuning_and_caps(self):
        catalog.set_level_cost('bank', 3, 'gold', 10)
        catalog.set_level_output('bank', 3, 10)
        catalog.set_max_level('bank', 12)
        catalog.factory_reset()
        self.assertEqual(catalog.tuned_cost_levels('bank'), ())
        self.assertEqual(catalog.tuned_output_levels('bank'), ())
        self.assertEqual(catalog.max_level('bank'), 0)

    def test_deleting_a_building_takes_its_level_rows(self):
        catalog.set_level_cost('bank', 3, 'gold', 10)
        catalog.set_level_output('bank', 3, 10)
        catalog.remove('bank')
        self.assertEqual(catalog.tuned_cost_levels('bank'), ())
        self.assertEqual(catalog.tuned_output_levels('bank'), ())

    def test_deleting_a_resource_takes_the_level_costs_naming_it(self):
        catalog.set_level_cost('bank', 3, 'gold', 10)
        catalog.remove('gold')
        self.assertEqual(catalog.level_costs('bank', 3), {})


# ---------------------------------------------------------------------------
# What a player sees
# ---------------------------------------------------------------------------


class UpgradeTest(LevelTestCase):

    def setUp(self):
        super().setUp()
        self.bot = StubBot({GROUP: Chat(GROUP, title='Iran')})
        asset_ui.init(self.bot, self.conn, lang='fa', is_admin=lambda uid: uid == ADMIN)
        self.conn.execute("INSERT INTO users (user_id, group_id) VALUES (1, ?)", (GROUP,))
        self.conn.commit()

    def call(self, data):
        message = Message(Chat(GROUP, title='Iran'), User(1))
        return Call(data, User(1), message)

    def level(self, key='bank'):
        return self.conn.execute(f"SELECT {key} FROM users WHERE group_id=?",
                                 (GROUP,)).fetchone()[0]

    def money(self):
        return self.conn.execute("SELECT gold, stones, iron FROM users WHERE group_id=?",
                                 (GROUP,)).fetchone()

    def test_an_upgrade_charges_the_flat_cost_by_default(self):
        before = self.money()
        asset_ui.handle_callback(self.call('ag:upy:bank'))
        self.assertEqual(self.level(), 1)
        # bank costs stones 500, iron 500, gold 500
        self.assertEqual(tuple(self.money()), tuple(v - 500 for v in before))

    def test_an_upgrade_charges_the_tuned_cost_for_that_level(self):
        catalog.set_level_cost('bank', 1, 'gold', 42)
        gold_before = self.money()[0]
        asset_ui.handle_callback(self.call('ag:upy:bank'))
        self.assertEqual(self.level(), 1)
        self.assertEqual(self.money()[0], gold_before - 42)
        # the tuned level replaced the flat cost outright, so stones went untouched
        self.assertEqual(self.money()[1], 2000)

    def test_each_level_can_have_its_own_price(self):
        catalog.set_level_cost('bank', 1, 'gold', 10)
        catalog.set_level_cost('bank', 2, 'gold', 700)
        gold_before = self.money()[0]
        asset_ui.handle_callback(self.call('ag:upy:bank'))
        asset_ui.handle_callback(self.call('ag:upy:bank'))
        self.assertEqual(self.level(), 2)
        self.assertEqual(self.money()[0], gold_before - 710)

    def test_the_cap_refuses_the_next_upgrade(self):
        catalog.set_max_level('bank', 2)
        for _ in range(3):
            asset_ui.handle_callback(self.call('ag:upy:bank'))
        self.assertEqual(self.level(), 2)
        self.assertIn('2', self.bot.sent[-1][1])

    def test_the_confirm_screen_quotes_the_next_level(self):
        catalog.set_level_cost('bank', 1, 'gold', 4242)
        asset_ui.handle_callback(self.call('ag:upc:bank'))
        self.assertIn('4242', self.bot.sent[-1][1])

    def test_the_confirm_screen_refuses_at_the_cap(self):
        catalog.set_max_level('bank', 0)
        self.conn.execute("UPDATE users SET bank=9 WHERE group_id=?", (GROUP,))
        self.conn.commit()
        catalog.set_max_level('bank', 9)
        asset_ui.handle_callback(self.call('ag:upc:bank'))
        self.assertIn('9', self.bot.sent[-1][1])
        # the refusal carries no "yes, upgrade" button
        self.assertEqual(self.bot.markups, [])

    def test_the_picker_shows_the_level_and_the_ceiling(self):
        catalog.set_max_level('bank', 20)
        self.conn.execute("UPDATE users SET bank=3 WHERE group_id=?", (GROUP,))
        self.conn.commit()
        asset_ui.upgrade_menu(GROUP)
        labels = [b.text for row in self.bot.markups[-1].keyboard for b in row]
        self.assertTrue(any('(3/20)' in text for text in labels), labels)

    def test_the_weekly_cycle_credits_the_tuned_yield(self):
        self.conn.execute("UPDATE users SET bank=2 WHERE group_id=?", (GROUP,))
        self.conn.commit()
        catalog.set_level_output('bank', 2, 10000)
        before = self.conn.execute("SELECT money FROM users WHERE group_id=?",
                                   (GROUP,)).fetchone()[0]
        asset_ui.weekly_update(GROUP, GROUP)
        after = self.conn.execute("SELECT money FROM users WHERE group_id=?",
                                  (GROUP,)).fetchone()[0]
        self.assertEqual(after - before, 1500 + 10000)


if __name__ == '__main__':
    unittest.main()
