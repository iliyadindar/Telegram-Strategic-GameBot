# -*- coding: utf-8 -*-
"""The panel screens that add and retune catalog types."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import admin_panel
import asset_catalog as catalog
from stubs import Call, Chat, Message, StubBot, User, make_db

OWNER = 100
PLAYER = 300
GROUP = -1001


class CatalogScreenTest(unittest.TestCase):

    def setUp(self):
        self.conn = make_db()
        self.addCleanup(self.conn.close)
        self.bot = StubBot(chats={
            OWNER: Chat(OWNER, 'private', first_name='Owner'),
            PLAYER: Chat(PLAYER, 'private', first_name='Player'),
            GROUP: Chat(GROUP, title='Persia'),
        })
        admin_panel._title_cache.clear()
        admin_panel._name_cache.clear()
        admin_panel.init(self.bot, self.conn, OWNER, '@news', '@war', lang='en')

    # --- helpers --------------------------------------------------------
    def tap(self, data, user_id=OWNER):
        admin_panel.handle_callback(
            Call(data, User(user_id), Message(Chat(GROUP), User(user_id))))

    def feed(self, text, user_id=OWNER):
        """Deliver `text` to whatever prompt is currently waiting."""
        handler = self.bot.next_steps[-1][1]
        handler(Message(Chat(GROUP), User(user_id), text=text))

    def screen(self):
        return self.bot.edits[-1][2] if self.bot.edits else self.bot.last_sent_text()


class AccessTest(CatalogScreenTest):

    def test_catalog_home_is_admin_only(self):
        self.tap('ap:cat', user_id=PLAYER)
        _, text, alert = self.bot.last_answer()
        self.assertTrue(alert)
        self.assertIn('not an admin', text)

    def test_adding_a_type_is_admin_only(self):
        self.tap('ap:catadd:unit', user_id=PLAYER)
        self.assertEqual(self.bot.next_steps, [])

    def test_panel_offers_the_catalog(self):
        admin_panel.open_panel(GROUP, OWNER)
        self.assertIn('ap:cat', self.bot.last_keyboard())


class BrowsingTest(CatalogScreenTest):

    def test_home_counts_each_kind(self):
        self.tap('ap:cat')
        text = self.screen()
        self.assertIn(f"Resources: {len(catalog.BUILTIN_RESOURCES)}", text)
        self.assertIn(f"Units: {len(catalog.BUILTIN_UNITS)}", text)

    def test_kind_list_paginates(self):
        self.tap('ap:catk:building:0')
        self.assertIn('page 1 of', self.screen())

    def test_entry_screen_shows_key_and_cost(self):
        self.tap('ap:cate:stone_factory')
        text = self.screen()
        self.assertIn('stone_factory', text)
        self.assertIn('500', text)

    def test_builtin_entry_is_marked_as_undeletable(self):
        self.tap('ap:cate:money')
        self.assertIn('but not removed', self.screen())
        self.assertNotIn('ap:cathide:money', self.bot.last_keyboard())

    def test_unknown_entry_alerts(self):
        self.tap('ap:cate:phantom')
        _, text, alert = self.bot.last_answer()
        self.assertTrue(alert)
        self.assertIn('No such type', text)


class AddUnitTest(CatalogScreenTest):

    def add_archers(self):
        self.tap('ap:catadd:unit')
        self.feed('archers')       # key
        self.feed('🏹 کماندار')     # fa
        self.feed('🏹 Archers')     # en
        self.feed('🏹 Okçu')        # tr
        self.feed('750')           # starting amount

    def test_wizard_registers_the_type(self):
        self.add_archers()
        self.assertIn('archers', catalog.keys('unit'))
        self.assertEqual(catalog.label('archers', 'en'), '🏹 Archers')
        self.assertEqual(catalog.defaults()['archers'], 750)

    def test_wizard_creates_the_column(self):
        self.add_archers()
        columns = {r[1] for r in self.conn.execute("PRAGMA table_info(users)").fetchall()}
        self.assertIn('archers', columns)

    def test_addition_is_logged(self):
        self.add_archers()
        entry = admin_panel.recent_log()[0]
        self.assertEqual(entry['action'], 'asset_add')
        self.assertEqual(entry['target'], 'archers')

    def test_a_bad_key_is_rejected_and_re_asked(self):
        self.tap('ap:catadd:unit')
        self.feed('Archers!!')
        self.assertIn('Invalid key', self.bot.last_sent_text())
        self.feed('archers')
        self.feed('a'); self.feed('b'); self.feed('c')
        self.feed('10')
        self.assertIn('archers', catalog.keys('unit'))

    def test_a_duplicate_key_is_rejected(self):
        self.tap('ap:catadd:unit')
        self.feed('money')
        self.assertIn('already exists', self.bot.last_sent_text())

    def test_a_reserved_key_is_rejected(self):
        self.tap('ap:catadd:unit')
        self.feed('group_id')
        self.assertIn('reserved', self.bot.last_sent_text())

    def test_a_non_numeric_starting_amount_is_re_asked(self):
        self.tap('ap:catadd:unit')
        self.feed('archers')
        self.feed('a'); self.feed('b'); self.feed('c')
        self.feed('plenty')
        self.assertIn('valid amount', self.bot.last_sent_text())
        self.feed('12')
        self.assertEqual(catalog.defaults()['archers'], 12)


class AddBuildingTest(CatalogScreenTest):

    def setUp(self):
        super().setUp()
        catalog.add('archers', 'unit', {'en': 'Archers'}, default_value=0)

    def test_building_wizard_wires_production(self):
        self.tap('ap:catadd:building')
        self.feed('archery_range')
        self.feed('میدان تیر'); self.feed('Archery Range'); self.feed('Okçu Alanı')
        self.feed('0')                       # starting level
        self.tap('ap:catprod:archers')       # what it produces
        self.feed('400')                     # output per level per week
        self.assertIn(('archery_range', 'archers', 400), catalog.production())

    def test_building_can_produce_nothing(self):
        self.tap('ap:catadd:building')
        self.feed('watchtower')
        self.feed('برج'); self.feed('Watchtower'); self.feed('Kule')
        self.feed('0')
        self.tap('ap:catprod:-')
        self.assertIn('watchtower', catalog.keys('building'))
        self.assertNotIn('watchtower', [b for b, _, _ in catalog.production()])


class RetuneTest(CatalogScreenTest):

    def test_rename_updates_every_language(self):
        self.tap('ap:catren:money')
        self.feed('پول نو'); self.feed('New Money'); self.feed('Yeni Para')
        self.assertEqual(catalog.label('money', 'en'), 'New Money')
        self.assertEqual(catalog.label('money', 'tr'), 'Yeni Para')

    def test_default_can_be_changed(self):
        self.tap('ap:catdef:money')
        self.feed('12345')
        self.assertEqual(catalog.defaults()['money'], 12345)

    def test_upgrade_cost_can_be_changed(self):
        self.tap('ap:catcosts:bank:gold')
        self.feed('4200')
        self.assertEqual(catalog.upgrade_cost('bank')['gold'], 4200)

    def test_cost_change_is_logged(self):
        self.tap('ap:catcosts:bank:gold')
        self.feed('4200')
        entry = admin_panel.recent_log()[0]
        self.assertEqual(entry['action'], 'asset_cost')
        self.assertEqual(entry['detail'], 'gold=4200')

    def test_output_can_be_retargeted(self):
        self.tap('ap:catouts:bank:gold')
        self.feed('99')
        self.assertIn(('bank', 'gold', 99), catalog.production())

    def test_tradeable_toggles(self):
        self.tap('ap:cattr:money')
        self.assertNotIn('money', catalog.tradeable_resources())
        self.tap('ap:cattr:money')
        self.assertIn('money', catalog.tradeable_resources())

    def test_tradeable_on_a_unit_alerts(self):
        self.tap('ap:cattr:swordsmen')
        _, text, alert = self.bot.last_answer()
        self.assertTrue(alert)
        self.assertIn('not a resource', text)


class HideScreenTest(CatalogScreenTest):

    def setUp(self):
        super().setUp()
        catalog.add('archers', 'unit', {'en': 'Archers'}, default_value=750)

    def test_custom_type_can_be_hidden_and_restored(self):
        self.tap('ap:cathide:archers')
        self.assertNotIn('archers', catalog.all_keys())
        self.tap('ap:catshow:archers')
        self.assertIn('archers', catalog.all_keys())

    def test_hiding_is_logged(self):
        self.tap('ap:cathide:archers')
        entry = admin_panel.recent_log()[0]
        self.assertEqual(entry['action'], 'asset_hide')

    def test_builtin_cannot_be_hidden_from_the_screen(self):
        self.tap('ap:cathide:money')
        _, text, alert = self.bot.last_answer()
        self.assertTrue(alert)
        self.assertIn('cannot be removed', text)
        self.assertIn('money', catalog.all_keys())


if __name__ == '__main__':
    unittest.main()
