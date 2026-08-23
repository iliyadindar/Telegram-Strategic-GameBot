# -*- coding: utf-8 -*-
"""Per-country asset overrides: taking a type away from one country (item 11)
and switching one country's factories off (item 12)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import admin_panel
import asset_catalog as catalog
import asset_ui
import country_assets
from stubs import Call, Chat, Message, StubBot, User, add_group, make_db

OWNER = 100
PLAYER = 300
PERSIA = -1001
ROME = -1002


class CountryAssetTestCase(unittest.TestCase):

    def setUp(self):
        self.conn = make_db()
        self.addCleanup(self.conn.close)
        self.bot = StubBot(chats={
            OWNER: Chat(OWNER, 'private', first_name='Owner'),
            PLAYER: Chat(PLAYER, 'private', first_name='Player'),
            PERSIA: Chat(PERSIA, title='Persia'),
            ROME: Chat(ROME, title='Rome'),
        })
        admin_panel._title_cache.clear()
        admin_panel._name_cache.clear()
        admin_panel.set_lord_guard(None)
        admin_panel.init(self.bot, self.conn, OWNER, '@news', '@war', lang='en')
        asset_ui.init(self.bot, self.conn, lang='en', is_admin=admin_panel.is_admin)
        add_group(self.conn, 1, PERSIA)
        add_group(self.conn, 2, ROME)

    def tap(self, data, user_id=OWNER, chat=PERSIA):
        admin_panel.handle_callback(Call(data, User(user_id), Message(Chat(chat), User(user_id))))

    def screen(self):
        return self.bot.edits[-1][2] if self.bot.edits else self.bot.last_sent_text()


# ---------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------


class OverrideStoreTest(CountryAssetTestCase):

    def test_a_country_starts_with_the_whole_catalog(self):
        self.assertEqual(country_assets.keys_for(PERSIA), catalog.all_keys())
        self.assertEqual(country_assets.overrides(PERSIA), (0, 0))

    def test_taking_a_type_away_removes_it_from_that_country_only(self):
        country_assets.set_hidden(PERSIA, 'small_ships', True)
        self.assertNotIn('small_ships', country_assets.keys_for(PERSIA))
        self.assertIn('small_ships', country_assets.keys_for(ROME))

    def test_giving_it_back_restores_it(self):
        country_assets.set_hidden(PERSIA, 'small_ships', True)
        country_assets.set_hidden(PERSIA, 'small_ships', False)
        self.assertIn('small_ships', country_assets.keys_for(PERSIA))
        self.assertEqual(country_assets.overrides(PERSIA), (0, 0))

    def test_a_removed_type_keeps_its_stored_number(self):
        self.conn.execute("UPDATE users SET small_ships=77 WHERE group_id=?", (PERSIA,))
        self.conn.commit()
        country_assets.set_hidden(PERSIA, 'small_ships', True)
        country_assets.set_hidden(PERSIA, 'small_ships', False)
        self.assertEqual(self.conn.execute(
            "SELECT small_ships FROM users WHERE group_id=?", (PERSIA,)).fetchone()[0], 77)

    def test_hidden_and_paused_are_independent(self):
        country_assets.set_paused(PERSIA, 'bank', True)
        self.assertFalse(country_assets.is_hidden(PERSIA, 'bank'))
        self.assertIn('bank', country_assets.keys_for(PERSIA))
        self.assertEqual(country_assets.overrides(PERSIA), (0, 1))

    def test_a_removed_building_counts_as_switched_off_too(self):
        country_assets.set_hidden(PERSIA, 'bank', True)
        self.assertTrue(country_assets.is_paused(PERSIA, 'bank'))

    def test_clearing_puts_a_country_back_to_the_catalog(self):
        country_assets.set_hidden(PERSIA, 'bank', True)
        country_assets.set_paused(PERSIA, 'farm', True)
        self.assertEqual(country_assets.clear(PERSIA), 2)
        self.assertEqual(country_assets.overrides(PERSIA), (0, 0))

    def test_destroying_a_type_forgets_every_override_for_it(self):
        country_assets.set_hidden(PERSIA, 'bank', True)
        country_assets.forget('bank')
        self.assertEqual(country_assets.overrides(PERSIA), (0, 0))

    def test_production_skips_removed_and_stopped_buildings(self):
        country_assets.set_hidden(PERSIA, 'bank', True)
        country_assets.set_paused(PERSIA, 'farm', True)
        running = [b for b, _, _ in country_assets.production_for(PERSIA)]
        self.assertNotIn('bank', running)
        self.assertNotIn('farm', running)
        self.assertIn('gold_mine', running)

    def test_production_skips_a_building_whose_product_was_taken_away(self):
        country_assets.set_hidden(PERSIA, 'gold', True)
        running = [b for b, _, _ in country_assets.production_for(PERSIA)]
        self.assertNotIn('gold_mine', running)


# ---------------------------------------------------------------------------
# What a player sees
# ---------------------------------------------------------------------------


class PlayerViewTest(CountryAssetTestCase):

    def player_call(self, data, group_id=PERSIA):
        return Call(data, User(1), Message(Chat(group_id), User(1)))

    def test_a_removed_type_is_gone_from_the_assets_screen(self):
        country_assets.set_hidden(PERSIA, 'small_ships', True)
        asset_ui.show_assets(PERSIA, PERSIA)
        self.assertNotIn('Small Ships', self.bot.last_sent_text())

    def test_it_is_still_there_for_another_country(self):
        country_assets.set_hidden(PERSIA, 'small_ships', True)
        asset_ui.show_assets(ROME, ROME)
        self.assertIn('Small Ships', self.bot.last_sent_text())

    def test_a_removed_building_is_gone_from_the_upgrade_menu(self):
        country_assets.set_hidden(PERSIA, 'bank', True)
        asset_ui.upgrade_menu(PERSIA)
        self.assertNotIn('ag:upc:bank', self.bot.last_keyboard())

    def test_a_removed_building_cannot_be_upgraded_by_callback(self):
        country_assets.set_hidden(PERSIA, 'bank', True)
        asset_ui.handle_callback(self.player_call('ag:upy:bank'))
        level = self.conn.execute("SELECT bank FROM users WHERE group_id=?",
                                  (PERSIA,)).fetchone()[0]
        self.assertEqual(level, 0)

    def test_a_stopped_building_can_still_be_upgraded(self):
        country_assets.set_paused(PERSIA, 'bank', True)
        asset_ui.handle_callback(self.player_call('ag:upy:bank'))
        level = self.conn.execute("SELECT bank FROM users WHERE group_id=?",
                                  (PERSIA,)).fetchone()[0]
        self.assertEqual(level, 1)

    def test_a_stopped_building_produces_nothing(self):
        self.conn.execute("UPDATE users SET bank=3 WHERE group_id=?", (PERSIA,))
        self.conn.commit()
        country_assets.set_paused(PERSIA, 'bank', True)
        before = self.conn.execute("SELECT money FROM users WHERE group_id=?",
                                   (PERSIA,)).fetchone()[0]
        asset_ui.weekly_update(PERSIA, PERSIA)
        after = self.conn.execute("SELECT money FROM users WHERE group_id=?",
                                  (PERSIA,)).fetchone()[0]
        self.assertEqual(after, before)

    def test_its_neighbours_keep_producing(self):
        self.conn.execute("UPDATE users SET bank=3, gold_mine=2 WHERE group_id=?", (PERSIA,))
        self.conn.commit()
        country_assets.set_paused(PERSIA, 'bank', True)
        asset_ui.weekly_update(PERSIA, PERSIA)
        gold = self.conn.execute("SELECT gold FROM users WHERE group_id=?",
                                 (PERSIA,)).fetchone()[0]
        self.assertEqual(gold, catalog.defaults()['gold'] + 2 * 1500)

    def test_the_same_building_still_runs_elsewhere(self):
        self.conn.execute("UPDATE users SET bank=3")
        self.conn.commit()
        country_assets.set_paused(PERSIA, 'bank', True)
        asset_ui.weekly_update(ROME, ROME)
        money = self.conn.execute("SELECT money FROM users WHERE group_id=?",
                                  (ROME,)).fetchone()[0]
        self.assertEqual(money, catalog.defaults()['money'] + 3 * 1500)


# ---------------------------------------------------------------------------
# The panel screens
# ---------------------------------------------------------------------------


class PanelScreenTest(CountryAssetTestCase):

    def test_the_panel_offers_the_section(self):
        admin_panel.open_panel(PERSIA, OWNER)
        self.assertIn('ap:gas:0', self.bot.last_keyboard())

    def test_the_picker_lists_every_country(self):
        self.tap('ap:gas:0')
        keyboard = self.bot.last_keyboard()
        self.assertIn(f'ap:gasg:{PERSIA}', keyboard)
        self.assertIn(f'ap:gasg:{ROME}', keyboard)

    def test_the_country_screen_offers_one_button_per_kind(self):
        self.tap(f'ap:gasg:{PERSIA}')
        keyboard = self.bot.last_keyboard()
        for kind in catalog.KINDS:
            self.assertIn(f'ap:gask:{PERSIA}:{kind}:0', keyboard)

    def test_tapping_a_type_takes_it_away_and_tapping_again_gives_it_back(self):
        self.tap(f'ap:gast:{PERSIA}:small_ships')
        self.assertTrue(country_assets.is_hidden(PERSIA, 'small_ships'))
        self.tap(f'ap:gast:{PERSIA}:small_ships')
        self.assertFalse(country_assets.is_hidden(PERSIA, 'small_ships'))

    def test_a_building_row_offers_a_stop_button(self):
        self.tap(f'ap:gask:{PERSIA}:building:0')
        self.assertIn(f'ap:gasp:{PERSIA}:bank', self.bot.last_keyboard())

    def test_a_resource_row_does_not(self):
        self.tap(f'ap:gask:{PERSIA}:resource:0')
        self.assertNotIn(f'ap:gasp:{PERSIA}:gold', self.bot.last_keyboard())

    def test_stopping_and_starting_a_factory(self):
        self.tap(f'ap:gasp:{PERSIA}:bank')
        self.assertIn('bank', country_assets.paused_keys(PERSIA))
        self.tap(f'ap:gasp:{PERSIA}:bank')
        self.assertNotIn('bank', country_assets.paused_keys(PERSIA))

    def test_only_buildings_can_be_stopped(self):
        self.tap(f'ap:gasp:{PERSIA}:gold')
        self.assertEqual(country_assets.paused_keys(PERSIA), frozenset())
        self.assertTrue(self.bot.last_answer()[2])

    def test_the_country_screen_names_what_is_set(self):
        country_assets.set_hidden(PERSIA, 'small_ships', True)
        country_assets.set_paused(PERSIA, 'bank', True)
        self.tap(f'ap:gasg:{PERSIA}')
        screen = self.screen()
        self.assertIn('Small Ships', screen)
        self.assertIn('Bank', screen)

    def test_clearing_from_the_panel(self):
        country_assets.set_hidden(PERSIA, 'small_ships', True)
        self.tap(f'ap:gasrc:{PERSIA}')
        self.assertEqual(country_assets.overrides(PERSIA), (0, 0))

    def test_the_clear_button_only_appears_when_there_is_something_to_clear(self):
        self.tap(f'ap:gasg:{PERSIA}')
        self.assertNotIn(f'ap:gasr:{PERSIA}', self.bot.last_keyboard())
        country_assets.set_hidden(PERSIA, 'small_ships', True)
        self.tap(f'ap:gasg:{PERSIA}')
        self.assertIn(f'ap:gasr:{PERSIA}', self.bot.last_keyboard())

    def test_every_screen_is_admin_only(self):
        for data in (f'ap:gas:0', f'ap:gasg:{PERSIA}', f'ap:gask:{PERSIA}:unit:0',
                     f'ap:gast:{PERSIA}:small_ships', f'ap:gasp:{PERSIA}:bank',
                     f'ap:gasrc:{PERSIA}'):
            self.tap(data, user_id=PLAYER)
            self.assertTrue(self.bot.last_answer()[2], data)
        self.assertEqual(country_assets.overrides(PERSIA), (0, 0))

    def test_a_change_is_logged_against_the_country(self):
        self.tap(f'ap:gast:{PERSIA}:small_ships')
        entry = admin_panel.recent_log()[0]
        self.assertEqual(entry['action'], 'country_asset')
        self.assertEqual(entry['target'], 'Persia')

    def test_destroying_a_country_forgets_its_overrides(self):
        country_assets.set_hidden(PERSIA, 'small_ships', True)
        admin_panel._drop_lords(PERSIA)
        self.assertEqual(country_assets.overrides(PERSIA), (0, 0))

    def test_the_callbacks_fit_telegrams_budget(self):
        long_key = 'b' * 31
        catalog.add(long_key, 'building', {'en': 'Long'}, produces='gold', output=5)
        self.tap(f'ap:gask:{PERSIA}:building:4')
        for data in self.bot.last_keyboard():
            self.assertLessEqual(len(data.encode('utf-8')), 64, data)


if __name__ == '__main__':
    unittest.main()
