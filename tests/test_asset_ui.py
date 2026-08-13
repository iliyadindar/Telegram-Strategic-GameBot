# -*- coding: utf-8 -*-
"""Player screens: assets, upgrades, weekly production and the asset editor."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asset_catalog as catalog
import asset_ui
from stubs import Call, Chat, Message, StubBot, User, add_group, make_db

GROUP = -1001
LORD = 500
ADMIN = 100


class UiTestCase(unittest.TestCase):

    def setUp(self):
        self.conn = make_db()
        self.addCleanup(self.conn.close)
        self.bot = StubBot(chats={GROUP: Chat(GROUP, title='Persia')})
        self.audit = []
        asset_ui.init(self.bot, self.conn, lang='en',
                      audit=lambda *a: self.audit.append(a),
                      is_admin=lambda uid: uid == ADMIN)
        add_group(self.conn, LORD, GROUP)

    def call(self, data, user_id=LORD):
        return Call(data, User(user_id), Message(Chat(GROUP), User(user_id)))

    def value(self, column):
        row = self.conn.execute(f"SELECT {column} FROM users WHERE group_id=?",
                                (GROUP,)).fetchone()
        return row[0]

    def set_values(self, **columns):
        sets = ', '.join(f"{c}=?" for c in columns)
        self.conn.execute(f"UPDATE users SET {sets} WHERE group_id=?",
                          list(columns.values()) + [GROUP])
        self.conn.commit()

    def keyboard(self):
        """callback_data of the last keyboard the bot was handed."""
        return self._last_keyboard

    def capture_keyboards(self):
        self._last_keyboard = []
        original = self.bot.send_message

        def capture(chat_id, text, **kwargs):
            markup = kwargs.get('reply_markup')
            if markup is not None:
                self._last_keyboard = [b.callback_data for row in markup.keyboard for b in row]
            return original(chat_id, text, **kwargs)

        self.bot.send_message = capture


class ShowAssetsTest(UiTestCase):

    def test_every_builtin_appears(self):
        asset_ui.show_assets(GROUP, GROUP)
        text = self.bot.last_sent_text()
        self.assertIn('Money', text)
        self.assertIn('Swordsmen', text)
        self.assertIn('Bank', text)

    def test_a_newly_added_type_appears_without_a_code_change(self):
        catalog.add('archers', 'unit', {'en': '🏹 Archers'}, default_value=750)
        asset_ui.show_assets(GROUP, GROUP)
        self.assertIn('🏹 Archers', self.bot.last_sent_text())

    def test_a_hidden_type_disappears(self):
        catalog.add('archers', 'unit', {'en': '🏹 Archers'}, default_value=750)
        catalog.hide('archers')
        asset_ui.show_assets(GROUP, GROUP)
        self.assertNotIn('Archers', self.bot.last_sent_text())

    def test_a_renamed_type_shows_its_new_name(self):
        catalog.set_labels('money', {'en': '💰 Coin'})
        asset_ui.show_assets(GROUP, GROUP)
        self.assertIn('💰 Coin', self.bot.last_sent_text())

    def test_unknown_group_is_told_to_register(self):
        asset_ui.show_assets(GROUP, -9999)
        self.assertIn('/setlord', self.bot.last_sent_text())


class UpgradeTest(UiTestCase):

    def test_menu_lists_every_building(self):
        self.capture_keyboards()
        asset_ui.upgrade_menu(GROUP)
        self.assertIn('ag:upc:bank', self.keyboard())
        self.assertIn('ag:upc:stone_factory', self.keyboard())

    def test_menu_includes_a_newly_added_building(self):
        catalog.add('archery_range', 'building', {'en': 'Archery Range'})
        self.capture_keyboards()
        asset_ui.upgrade_menu(GROUP)
        self.assertIn('ag:upc:archery_range', self.keyboard())

    def test_confirmation_lists_the_cost(self):
        asset_ui.handle_callback(self.call('ag:upc:stone_factory'))
        text = self.bot.last_sent_text()
        self.assertIn('Wood', text)
        self.assertIn('500', text)

    def test_upgrade_deducts_exactly_what_was_quoted(self):
        self.set_values(wood=1000, money=1000, stones=1000)
        asset_ui.handle_callback(self.call('ag:upy:stone_factory'))
        self.assertEqual(self.value('wood'), 500)
        self.assertEqual(self.value('money'), 500)
        self.assertEqual(self.value('stones'), 1000)
        self.assertEqual(self.value('stone_factory'), 1)

    def test_gold_mine_charges_wood_not_iron(self):
        # The legacy code checked iron but deducted wood, so wood could go negative.
        self.set_values(wood=100, iron=5000, stones=5000, money=5000)
        asset_ui.handle_callback(self.call('ag:upy:gold_mine'))
        self.assertEqual(self.value('gold_mine'), 0, 'the upgrade should have been refused')
        self.assertEqual(self.value('wood'), 100)

    def test_special_guard_camp_charges_wood_not_iron(self):
        self.set_values(money=5000, stones=5000, wood=100, iron=5000)
        asset_ui.handle_callback(self.call('ag:upy:special_guard_camp'))
        self.assertEqual(self.value('special_guard_camp'), 0)

    def test_no_resource_can_be_driven_negative(self):
        self.set_values(wood=0, money=0, stones=0, iron=0, gold=0)
        for building in catalog.keys('building'):
            asset_ui.handle_callback(self.call(f'ag:upy:{building}'))
        for resource in catalog.keys('resource'):
            self.assertGreaterEqual(self.value(resource), 0, resource)

    def test_insufficient_funds_are_reported(self):
        self.set_values(wood=0, money=0)
        asset_ui.handle_callback(self.call('ag:upy:stone_factory'))
        self.assertIn('not have enough', self.bot.last_sent_text())

    def test_a_free_building_can_always_be_upgraded(self):
        catalog.add('watchtower', 'building', {'en': 'Watchtower'})
        self.set_values(money=0, wood=0)
        asset_ui.handle_callback(self.call('ag:upy:watchtower'))
        self.assertEqual(self.value('watchtower'), 1)

    def test_admin_defined_cost_is_enforced(self):
        catalog.add('archery_range', 'building', {'en': 'Archery Range'})
        catalog.set_upgrade_cost('archery_range', 'gold', 300)
        self.set_values(gold=200)
        asset_ui.handle_callback(self.call('ag:upy:archery_range'))
        self.assertEqual(self.value('archery_range'), 0)
        self.set_values(gold=300)
        asset_ui.handle_callback(self.call('ag:upy:archery_range'))
        self.assertEqual(self.value('archery_range'), 1)
        self.assertEqual(self.value('gold'), 0)

    def test_a_hidden_building_cannot_be_upgraded(self):
        catalog.add('watchtower', 'building', {'en': 'Watchtower'})
        catalog.hide('watchtower')
        asset_ui.handle_callback(self.call('ag:upy:watchtower'))
        self.assertEqual(self.value('watchtower'), 0)

    def test_upgrading_something_that_is_not_a_building_is_refused(self):
        asset_ui.handle_callback(self.call('ag:upy:money'))
        _, _, alert = self.bot.last_answer()
        self.assertTrue(alert)


class WeeklyUpdateTest(UiTestCase):

    def test_output_scales_with_the_building_level(self):
        self.set_values(stone_factory=2, stones=0)
        asset_ui.weekly_update(GROUP, GROUP)
        self.assertEqual(self.value('stones'), 3000)

    def test_a_group_with_no_buildings_gets_nothing(self):
        asset_ui.weekly_update(GROUP, GROUP)
        self.assertIn('no buildings', self.bot.last_sent_text())

    def test_two_buildings_feeding_one_type_stack(self):
        catalog.add('quarry', 'building', {'en': 'Quarry'}, produces='stones', output=100)
        self.set_values(stone_factory=1, quarry=2, stones=0)
        asset_ui.weekly_update(GROUP, GROUP)
        self.assertEqual(self.value('stones'), 1500 + 200)

    def test_a_new_building_produces_its_new_unit(self):
        catalog.add('archers', 'unit', {'en': 'Archers'}, default_value=0)
        catalog.add('archery_range', 'building', {'en': 'Archery Range'},
                    produces='archers', output=400)
        self.set_values(archery_range=3)
        asset_ui.weekly_update(GROUP, GROUP)
        self.assertEqual(self.value('archers'), 1200)

    def test_retuned_output_takes_effect(self):
        catalog.set_output('bank', 'money', 10)
        self.set_values(bank=1, money=0)
        asset_ui.weekly_update(GROUP, GROUP)
        self.assertEqual(self.value('money'), 10)

    def test_a_building_producing_nothing_is_skipped(self):
        catalog.set_output('bank', '', 0)
        self.set_values(bank=5, money=0)
        asset_ui.weekly_update(GROUP, GROUP)
        self.assertEqual(self.value('money'), 0)


class EditorTest(UiTestCase):

    def test_editor_is_admin_only(self):
        asset_ui.handle_callback(self.call('ag:edk:resource', user_id=LORD))
        _, text, alert = self.bot.last_answer()
        self.assertTrue(alert)
        self.assertIn('not an admin', text)

    def test_admin_sees_the_kind_picker_in_section_order(self):
        self.capture_keyboards()
        asset_ui.editor_menu(GROUP)
        self.assertEqual(self.keyboard(), ['ag:edk:resource', 'ag:edk:building', 'ag:edk:unit'])
        catalog.move_kind('unit', 'up')
        self.capture_keyboards()
        asset_ui.editor_menu(GROUP)
        self.assertEqual(self.keyboard(), ['ag:edk:resource', 'ag:edk:unit', 'ag:edk:building'])

    def test_kind_list_offers_every_entry(self):
        self.capture_keyboards()
        asset_ui.handle_callback(self.call('ag:edk:resource', user_id=ADMIN))
        self.assertIn('ag:eda:money', self.keyboard())
        self.assertNotIn('ag:eda:swordsmen', self.keyboard())

    def test_setting_a_value_writes_it_and_logs(self):
        asset_ui.handle_callback(self.call('ag:eda:money', user_id=ADMIN))
        handler = self.bot.next_steps[-1][1]
        handler(Message(Chat(GROUP, title='Persia'), User(ADMIN), text='777'))
        self.assertEqual(self.value('money'), 777)
        self.assertIn(('asset_edit', 'Persia', 'money=777'),
                      [(a[1], a[2], a[3]) for a in self.audit])

    def test_a_non_number_is_rejected(self):
        asset_ui.handle_callback(self.call('ag:eda:money', user_id=ADMIN))
        handler = self.bot.next_steps[-1][1]
        handler(Message(Chat(GROUP), User(ADMIN), text='lots'))
        self.assertEqual(self.value('money'), 2000)
        self.assertIn('valid number', self.bot.last_sent_text())

    def test_another_user_cannot_hijack_the_prompt(self):
        asset_ui.handle_callback(self.call('ag:eda:money', user_id=ADMIN))
        handler = self.bot.next_steps[-1][1]
        handler(Message(Chat(GROUP), User(LORD), text='999999'))
        self.assertEqual(self.value('money'), 2000)

    def test_an_admin_added_type_can_be_edited(self):
        catalog.add('archers', 'unit', {'en': 'Archers'}, default_value=0)
        asset_ui.handle_callback(self.call('ag:eda:archers', user_id=ADMIN))
        handler = self.bot.next_steps[-1][1]
        handler(Message(Chat(GROUP), User(ADMIN), text='40'))
        self.assertEqual(self.value('archers'), 40)

    def test_an_unknown_column_is_refused(self):
        asset_ui.handle_callback(self.call('ag:eda:treaties', user_id=ADMIN))
        _, text, alert = self.bot.last_answer()
        self.assertTrue(alert)
        self.assertIn('Invalid asset', text)


class StringsTest(unittest.TestCase):

    def test_all_languages_share_the_same_keys(self):
        reference = set(asset_ui.STRINGS['en'])
        for lang, table in asset_ui.STRINGS.items():
            self.assertEqual(set(table), reference, f'{lang} keys differ')


if __name__ == '__main__':
    unittest.main()
