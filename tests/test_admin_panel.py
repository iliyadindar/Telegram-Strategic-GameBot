# -*- coding: utf-8 -*-
"""Admin dashboard: access control, feature toggles, log, stats and reset."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import admin_panel
import asset_catalog as catalog
from admin_strings import FEATURES
from stubs import Call, Chat, Message, StubBot, User, add_group, make_db

OWNER = 100
HELPER = 200
PLAYER = 300
GROUP_A = -1001
GROUP_B = -1002


def _builtin_keys():
    return (list(catalog.BUILTIN_RESOURCES) + list(catalog.BUILTIN_UNITS)
            + [key for key, _, _ in catalog.BUILTIN_BUILDINGS])


class PanelTestCase(unittest.TestCase):
    """Fresh in-memory db + stub bot wired into the panel for every test."""

    def setUp(self):
        self.conn = make_db()
        self.bot = StubBot(chats={
            OWNER: Chat(OWNER, 'private', first_name='Owner'),
            HELPER: Chat(HELPER, 'private', first_name='Helper'),
            PLAYER: Chat(PLAYER, 'private', first_name='Player'),
            GROUP_A: Chat(GROUP_A, title='Persia'),
            GROUP_B: Chat(GROUP_B, title='Rome'),
        })
        admin_panel._title_cache.clear()
        admin_panel._name_cache.clear()
        admin_panel.init(self.bot, self.conn, OWNER, '@news', '@war', lang='en')

    def call(self, data, user_id=OWNER, chat_id=GROUP_A):
        return Call(data, User(user_id), Message(Chat(chat_id), User(user_id)))


class AccessControlTest(PanelTestCase):

    def test_owner_is_admin_without_a_row(self):
        self.assertTrue(admin_panel.is_owner(OWNER))
        self.assertTrue(admin_panel.is_admin(OWNER))

    def test_stranger_is_not_admin(self):
        self.assertFalse(admin_panel.is_admin(PLAYER))
        self.assertFalse(admin_panel.is_owner(PLAYER))

    def test_promoted_user_becomes_admin_but_not_owner(self):
        admin_panel._admin_add_apply(Message(Chat(OWNER, 'private'), User(OWNER),
                                             text=str(HELPER)), OWNER)
        self.assertTrue(admin_panel.is_admin(HELPER))
        self.assertFalse(admin_panel.is_owner(HELPER))
        self.assertEqual(admin_panel.admin_ids(), [OWNER, HELPER])

    def test_only_the_owner_can_promote(self):
        admin_panel._admin_add_apply(Message(Chat(GROUP_A), User(PLAYER), text=str(HELPER)),
                                     PLAYER)
        self.assertFalse(admin_panel.is_admin(HELPER))

    def test_forwarded_message_identifies_the_new_admin(self):
        msg = Message(Chat(OWNER, 'private'), User(OWNER), forward_from=User(HELPER))
        admin_panel._admin_add_apply(msg, OWNER)
        self.assertTrue(admin_panel.is_admin(HELPER))

    def test_garbage_id_is_rejected(self):
        admin_panel._admin_add_apply(Message(Chat(OWNER, 'private'), User(OWNER),
                                             text='not-an-id'), OWNER)
        self.assertEqual(admin_panel.admin_ids(), [OWNER])

    def test_owner_cannot_be_demoted(self):
        admin_panel._admin_remove(self.call(f'ap:ar:{OWNER}'), OWNER)
        self.assertTrue(admin_panel.is_admin(OWNER))

    def test_promoted_admin_can_be_removed(self):
        admin_panel._admin_add_apply(Message(Chat(OWNER, 'private'), User(OWNER),
                                             text=str(HELPER)), OWNER)
        admin_panel._admin_remove(self.call(f'ap:ar:{HELPER}'), HELPER)
        self.assertFalse(admin_panel.is_admin(HELPER))

    def test_non_admin_callback_gets_an_alert_and_no_screen(self):
        admin_panel.handle_callback(self.call('ap:stats', user_id=PLAYER))
        call_id, text, alert = self.bot.last_answer()
        self.assertTrue(alert)
        self.assertIn('not an admin', text)
        self.assertEqual(self.bot.edits, [])

    def test_open_panel_refuses_non_admins(self):
        self.assertFalse(admin_panel.open_panel(GROUP_A, PLAYER))
        self.assertEqual(self.bot.sent, [])

    def test_open_panel_works_for_the_owner(self):
        self.assertTrue(admin_panel.open_panel(GROUP_A, OWNER))
        self.assertIn('Admin Panel', self.bot.last_sent_text())

    def test_admin_screen_is_owner_only(self):
        admin_panel._admin_add_apply(Message(Chat(OWNER, 'private'), User(OWNER),
                                             text=str(HELPER)), OWNER)
        admin_panel.handle_callback(self.call('ap:adm', user_id=HELPER))
        _, text, alert = self.bot.last_answer()
        self.assertTrue(alert)
        self.assertIn('owner', text)


class FeatureToggleTest(PanelTestCase):

    def test_every_feature_starts_enabled(self):
        for key in FEATURES:
            self.assertTrue(admin_panel.feature_enabled(key), key)

    def test_unknown_keys_default_to_enabled(self):
        self.assertTrue(admin_panel.feature_enabled('not_a_feature'))

    def test_toggle_flips_and_persists(self):
        admin_panel.handle_callback(self.call('ap:ft:trade'))
        self.assertFalse(admin_panel.feature_enabled('trade'))
        admin_panel.handle_callback(self.call('ap:ft:trade'))
        self.assertTrue(admin_panel.feature_enabled('trade'))

    def test_toggling_one_feature_leaves_the_others_alone(self):
        admin_panel.handle_callback(self.call('ap:ft:attack'))
        self.assertFalse(admin_panel.feature_enabled('attack'))
        self.assertTrue(admin_panel.feature_enabled('trade'))

    def test_require_feature_blocks_and_alerts_when_disabled(self):
        admin_panel._set_feature('assets', False)
        call = self.call('assets', user_id=PLAYER)
        self.assertFalse(admin_panel.require_feature(call, 'assets'))
        _, text, alert = self.bot.last_answer()
        self.assertTrue(alert)
        self.assertIn('disabled', text)

    def test_require_feature_passes_silently_when_enabled(self):
        call = self.call('assets', user_id=PLAYER)
        self.assertTrue(admin_panel.require_feature(call, 'assets'))
        self.assertEqual(self.bot.answers, [])

    def test_toggle_is_recorded_in_the_log(self):
        admin_panel.handle_callback(self.call('ap:ft:treaty'))
        entry = admin_panel.recent_log()[0]
        self.assertEqual(entry['action'], 'feature_toggle')
        self.assertEqual(entry['target'], 'treaty')
        self.assertEqual(entry['detail'], 'off')

    def test_unknown_feature_key_is_not_written(self):
        admin_panel.handle_callback(self.call('ap:ft:bogus'))
        self.assertEqual(admin_panel.recent_log(), [])


class ActionLogTest(PanelTestCase):

    def test_entries_come_back_newest_first(self):
        admin_panel.log(OWNER, 'asset_edit', 'Persia', 'gold=1')
        admin_panel.log(OWNER, 'asset_edit', 'Rome', 'gold=2')
        entries = admin_panel.recent_log()
        self.assertEqual(entries[0]['target'], 'Rome')
        self.assertEqual(entries[1]['target'], 'Persia')

    def test_limit_keeps_only_the_newest(self):
        for i in range(5):
            admin_panel.log(OWNER, 'asset_edit', f'g{i}')
        entries = admin_panel.recent_log(limit=2)
        self.assertEqual([e['target'] for e in entries], ['g4', 'g3'])

    def test_empty_log_renders_a_placeholder(self):
        admin_panel.handle_callback(self.call('ap:log:0'))
        self.assertIn('No admin action', self.bot.edits[-1][2])

    def test_long_details_are_truncated_in_the_list(self):
        admin_panel.log(OWNER, 'reset_country', 'Persia', 'x' * 400)
        admin_panel.handle_callback(self.call('ap:log:0'))
        rendered = self.bot.edits[-1][2]
        self.assertIn('…', rendered)
        self.assertNotIn('x' * 200, rendered)


class StatsTest(PanelTestCase):

    def setUp(self):
        super().setUp()
        add_group(self.conn, PLAYER, GROUP_A, money=1000, gold=500, swordsmen=10)
        add_group(self.conn, PLAYER + 1, GROUP_B, money=3000, gold=100, swordsmen=40)

    def test_totals_sum_across_groups(self):
        totals = admin_panel._totals(('money', 'gold'))
        self.assertEqual(totals['money'], 4000)
        self.assertEqual(totals['gold'], 600)

    def test_top_group_by_resources(self):
        gid, total = admin_panel._top_group(('money', 'gold'))
        self.assertEqual(gid, GROUP_B)
        self.assertEqual(total, 3100)

    def test_top_group_by_units(self):
        gid, _ = admin_panel._top_group(('swordsmen',))
        self.assertEqual(gid, GROUP_B)

    def test_groups_are_listed_once_each(self):
        self.assertEqual(sorted(admin_panel._groups()), sorted([GROUP_A, GROUP_B]))

    def test_stats_screen_names_both_groups_count(self):
        admin_panel.handle_callback(self.call('ap:stats'))
        text = self.bot.edits[-1][2]
        self.assertIn('Groups: 2', text)

    def test_trade_counts_are_zero_without_a_trades_table(self):
        self.assertEqual(admin_panel._trade_counts(), {'active': 0, 'offered': 0, 'done': 0})

    def test_trade_counts_read_the_trades_table_when_present(self):
        self.conn.execute("CREATE TABLE trades (id INTEGER PRIMARY KEY, status TEXT, "
                          "sender_group_id INTEGER, receiver_group_id INTEGER)")
        self.conn.executemany("INSERT INTO trades (status, sender_group_id, receiver_group_id) "
                              "VALUES (?, ?, ?)",
                              [('active', GROUP_A, GROUP_B),
                               ('delivered', GROUP_A, GROUP_B),
                               ('offered', GROUP_B, GROUP_A)])
        self.conn.commit()
        self.assertEqual(admin_panel._trade_counts(),
                         {'active': 1, 'offered': 1, 'done': 1})

    def test_group_card_shows_the_title_and_a_resource(self):
        admin_panel.handle_callback(self.call(f'ap:g:{GROUP_A}'))
        text = self.bot.edits[-1][2]
        self.assertIn('Persia', text)
        self.assertIn('1,000', text)

    def test_group_card_for_an_unknown_group_alerts(self):
        admin_panel.handle_callback(self.call('ap:g:-9999'))
        _, _, alert = self.bot.last_answer()
        self.assertTrue(alert)

    def test_empty_world_reports_no_groups(self):
        self.conn.execute("DELETE FROM users")
        self.conn.commit()
        admin_panel.handle_callback(self.call('ap:gl:0'))
        self.assertIn('No group', self.bot.edits[-1][2])


class ResetTest(PanelTestCase):

    def setUp(self):
        super().setUp()
        add_group(self.conn, PLAYER, GROUP_A, money=7, swordsmen=3, bank=9)

    def current(self):
        cur = self.conn.execute(
            f"SELECT {', '.join(catalog.all_keys())} FROM users WHERE group_id=?", (GROUP_A,))
        return dict(zip(catalog.all_keys(), cur.fetchone()))

    def test_reset_restores_every_column_to_its_default(self):
        admin_panel.handle_callback(self.call(f'ap:rsc:{GROUP_A}'))
        self.assertEqual(self.current(), catalog.defaults())

    def test_reset_leaves_other_groups_untouched(self):
        add_group(self.conn, PLAYER + 1, GROUP_B, money=55)
        admin_panel.handle_callback(self.call(f'ap:rsc:{GROUP_A}'))
        row = self.conn.execute("SELECT money FROM users WHERE group_id=?", (GROUP_B,)).fetchone()
        self.assertEqual(row[0], 55)

    def test_reset_records_the_previous_values(self):
        admin_panel.handle_callback(self.call(f'ap:rsc:{GROUP_A}'))
        entry = admin_panel.recent_log()[0]
        self.assertEqual(entry['action'], 'reset_country')
        before = json.loads(entry['detail'])
        self.assertEqual(before['money'], 7)
        self.assertEqual(before['bank'], 9)
        self.assertNotIn('gold', before, 'columns already at default are not recorded')

    def test_reset_needs_admin_rights(self):
        admin_panel.handle_callback(self.call(f'ap:rsc:{GROUP_A}', user_id=PLAYER))
        self.assertEqual(self.current()['money'], 7)

    def test_reset_preserves_treaties_and_trade_locations(self):
        self.conn.execute("UPDATE users SET treaties='pact', home_sea='per' WHERE group_id=?",
                          (GROUP_A,))
        self.conn.commit()
        admin_panel.handle_callback(self.call(f'ap:rsc:{GROUP_A}'))
        row = self.conn.execute("SELECT treaties, home_sea FROM users WHERE group_id=?",
                                (GROUP_A,)).fetchone()
        self.assertEqual(row, ('pact', 'per'))


class SettingsTest(PanelTestCase):

    def test_missing_setting_returns_the_default(self):
        self.assertEqual(admin_panel.setting('nope', 'fallback'), 'fallback')

    def test_set_then_read(self):
        admin_panel.set_setting('war_photo_land', 'FILE123')
        self.assertEqual(admin_panel.war_photo('land'), 'FILE123')

    def test_clearing_removes_the_value(self):
        admin_panel.set_setting('war_photo_sea', 'FILE456')
        admin_panel.set_setting('war_photo_sea', '')
        self.assertEqual(admin_panel.war_photo('sea'), '')

    def test_war_photo_of_an_unknown_mode_is_empty(self):
        self.assertEqual(admin_panel.war_photo('air'), '')

    def test_photo_upload_stores_the_largest_size(self):
        photo = [type('P', (), {'file_id': 'small'})(), type('P', (), {'file_id': 'big'})()]
        msg = Message(Chat(OWNER, 'private'), User(OWNER), photo=photo)
        admin_panel._war_photo_save(msg, 'land', OWNER)
        self.assertEqual(admin_panel.war_photo('land'), 'big')

    def test_non_photo_message_is_rejected(self):
        msg = Message(Chat(OWNER, 'private'), User(OWNER), text='here you go')
        admin_panel._war_photo_save(msg, 'land', OWNER)
        self.assertEqual(admin_panel.war_photo('land'), '')
        self.assertIn('not a photo', self.bot.last_sent_text())


class SetLordTest(PanelTestCase):

    def group_message(self, sender_id, replied_user=None):
        reply = Message(Chat(GROUP_A), replied_user) if replied_user else None
        return Message(Chat(GROUP_A), User(sender_id), text='/setlord', reply_to_message=reply)

    def lords(self):
        return [r[0] for r in self.conn.execute(
            "SELECT user_id FROM users WHERE group_id=?", (GROUP_A,)).fetchall()]

    def test_admin_reply_registers_the_replied_user(self):
        admin_panel.handle_setlord(self.group_message(OWNER, User(PLAYER)))
        self.assertEqual(self.lords(), [PLAYER])

    def test_player_cannot_appoint_themselves(self):
        admin_panel.handle_setlord(self.group_message(PLAYER, User(PLAYER)))
        self.assertEqual(self.lords(), [])
        self.assertIn('Only a bot admin', self.bot.replies[-1][1])

    def test_admin_without_a_reply_is_told_to_reply(self):
        admin_panel.handle_setlord(self.group_message(OWNER))
        self.assertEqual(self.lords(), [])
        self.assertIn('Reply to the message', self.bot.replies[-1][1])

    def test_bots_cannot_be_made_lords(self):
        admin_panel.handle_setlord(self.group_message(OWNER, User(999, is_bot=True)))
        self.assertEqual(self.lords(), [])

    def test_private_chat_is_rejected(self):
        msg = Message(Chat(OWNER, 'private'), User(OWNER), text='/setlord',
                      reply_to_message=Message(Chat(OWNER, 'private'), User(PLAYER)))
        admin_panel.handle_setlord(msg)
        self.assertIn('only be used in groups', self.bot.replies[-1][1])

    def test_repeat_assignment_is_reported_not_duplicated(self):
        admin_panel.handle_setlord(self.group_message(OWNER, User(PLAYER)))
        admin_panel.handle_setlord(self.group_message(OWNER, User(PLAYER)))
        self.assertEqual(self.lords(), [PLAYER])
        self.assertIn('already the lord', self.bot.replies[-1][1])

    def test_disabled_setlord_feature_blocks_the_command(self):
        admin_panel._set_feature('setlord', False)
        admin_panel.handle_setlord(self.group_message(OWNER, User(PLAYER)))
        self.assertEqual(self.lords(), [])
        self.assertIn('disabled', self.bot.replies[-1][1])

    def test_assignment_is_logged(self):
        admin_panel.handle_setlord(self.group_message(OWNER, User(PLAYER)))
        entry = admin_panel.recent_log()[0]
        self.assertEqual(entry['action'], 'lord_assign')
        self.assertEqual(entry['detail'], str(PLAYER))


class NotifyAdminsTest(PanelTestCase):

    def test_message_reaches_owner_and_every_admin(self):
        admin_panel._admin_add_apply(Message(Chat(OWNER, 'private'), User(OWNER),
                                             text=str(HELPER)), OWNER)
        self.bot.sent.clear()
        admin_panel.notify_admins('army report')
        self.assertEqual(sorted(c for c, _ in self.bot.sent), sorted([OWNER, HELPER]))

    def test_one_failing_recipient_does_not_stop_the_rest(self):
        admin_panel._admin_add_apply(Message(Chat(OWNER, 'private'), User(OWNER),
                                             text=str(HELPER)), OWNER)
        original = self.bot.send_message

        def flaky(chat_id, text, **kwargs):
            if chat_id == OWNER:
                raise RuntimeError('blocked the bot')
            return original(chat_id, text, **kwargs)

        self.bot.send_message = flaky
        self.bot.sent.clear()
        admin_panel.notify_admins('army report')
        self.assertEqual([c for c, _ in self.bot.sent], [HELPER])


class StringsIntegrityTest(unittest.TestCase):

    def test_all_languages_define_the_same_keys(self):
        from admin_strings import STRINGS
        reference = set(STRINGS['en'])
        for lang, table in STRINGS.items():
            self.assertEqual(set(table), reference, f'{lang} keys differ')

    def test_every_builtin_has_a_name_in_every_language(self):
        for lang, names in catalog.BUILTIN_LABELS.items():
            missing = [key for key in _builtin_keys() if key not in names]
            self.assertEqual(missing, [], f'{lang} is missing labels')

    def test_every_catalog_error_has_a_message(self):
        from admin_strings import CATALOG_ERRORS, STRINGS
        for lang, table in STRINGS.items():
            for code in CATALOG_ERRORS:
                self.assertIn('cat_err_' + code, table, f'{lang} lacks a message for {code}')

    def test_every_feature_has_a_label_in_every_language(self):
        from admin_strings import STRINGS
        for lang, table in STRINGS.items():
            for key in FEATURES:
                self.assertIn('feat_' + key, table, f'{lang} lacks a label for {key}')

    def test_every_action_has_a_label_in_every_language(self):
        from admin_strings import ACTIONS, STRINGS
        for lang, table in STRINGS.items():
            for action in ACTIONS:
                self.assertIn('act_' + action, table, f'{lang} lacks a label for {action}')

    def test_builtin_keys_are_unique_across_the_kinds(self):
        keys = _builtin_keys()
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_builtin_building_produces_a_known_type(self):
        stock = set(catalog.BUILTIN_RESOURCES) | set(catalog.BUILTIN_UNITS)
        for building, produces, output in catalog.BUILTIN_BUILDINGS:
            self.assertIn(produces, stock, f'{building} produces something unknown')
            self.assertGreater(output, 0, building)

    def test_every_builtin_cost_names_a_real_resource(self):
        for building, costs in catalog.BUILTIN_COSTS.items():
            self.assertIn(building, [b for b, _, _ in catalog.BUILTIN_BUILDINGS])
            for resource in costs:
                self.assertIn(resource, catalog.BUILTIN_RESOURCES,
                              f'{building} costs an unknown resource')


if __name__ == '__main__':
    unittest.main()
