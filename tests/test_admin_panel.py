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
        # main*.py registers this after init(); a test that sets one must not
        # leave a live trade hanging over every case that follows.
        admin_panel.set_lord_guard(None)
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

    def test_group_card_survives_every_type_being_disabled(self):
        # Reachable now that builtins can be hidden; it used to be impossible.
        self.conn.execute("UPDATE asset_catalog SET hidden=1")
        self.conn.commit()
        admin_panel.handle_callback(self.call(f'ap:g:{GROUP_A}'))
        self.assertIn('Persia', self.bot.edits[-1][2])

    def test_group_card_follows_the_section_order(self):
        admin_panel.handle_callback(self.call(f'ap:g:{GROUP_A}'))
        text = self.bot.edits[-1][2]
        self.assertLess(text.index('Buildings:'), text.index('Army:'))
        catalog.move_kind('unit', 'up')
        admin_panel.handle_callback(self.call(f'ap:g:{GROUP_A}'))
        text = self.bot.edits[-1][2]
        self.assertLess(text.index('Army:'), text.index('Buildings:'))

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


class UnsetLordTest(PanelTestCase):
    """/unsetlord: one player in reply, the whole group on its own."""

    def setUp(self):
        super().setUp()
        self.conn.execute("CREATE TABLE chokepoint_owners "
                          "(node_id TEXT PRIMARY KEY, group_id INTEGER NOT NULL)")
        self.conn.commit()
        self.addCleanup(admin_panel.set_lord_guard, None)
        add_group(self.conn, PLAYER, GROUP_A)

    def promote_helper(self):
        admin_panel._admin_add_apply(Message(Chat(OWNER, 'private'), User(OWNER),
                                             text=str(HELPER)), OWNER)

    def command(self, sender_id, replied_user=None, group_id=GROUP_A):
        reply = Message(Chat(group_id), replied_user) if replied_user else None
        return Message(Chat(group_id), User(sender_id), text='/unsetlord',
                       reply_to_message=reply)

    def lords(self, group_id=GROUP_A):
        return [r[0] for r in self.conn.execute(
            "SELECT user_id FROM users WHERE group_id=?", (group_id,)).fetchall()]

    def own(self, node_id, group_id=GROUP_A):
        self.conn.execute("INSERT INTO chokepoint_owners (node_id, group_id) VALUES (?, ?)",
                          (node_id, group_id))
        self.conn.commit()

    def owners(self):
        return [r[0] for r in self.conn.execute(
            "SELECT node_id FROM chokepoint_owners").fetchall()]

    # --- the reply form -------------------------------------------------

    def test_admin_reply_removes_that_lord(self):
        admin_panel.handle_unsetlord(self.command(OWNER, User(PLAYER)))
        self.assertEqual(self.lords(), [])
        self.assertIn('no longer a lord', self.bot.replies[-1][1])

    def test_a_promoted_admin_can_remove_one_lord(self):
        self.promote_helper()
        admin_panel.handle_unsetlord(self.command(HELPER, User(PLAYER)))
        self.assertEqual(self.lords(), [])

    def test_a_stranger_cannot_remove_a_lord(self):
        admin_panel.handle_unsetlord(self.command(PLAYER, User(PLAYER)))
        self.assertEqual(self.lords(), [PLAYER])
        self.assertIn('Only a bot admin', self.bot.replies[-1][1])

    def test_removing_someone_who_is_not_a_lord_here_is_refused(self):
        admin_panel.handle_unsetlord(self.command(OWNER, User(999)))
        self.assertEqual(self.lords(), [PLAYER])
        self.assertIn('not a lord', self.bot.replies[-1][1])

    def test_private_chat_is_rejected(self):
        msg = Message(Chat(OWNER, 'private'), User(OWNER), text='/unsetlord',
                      reply_to_message=Message(Chat(OWNER, 'private'), User(PLAYER)))
        admin_panel.handle_unsetlord(msg)
        self.assertIn('only be used in groups', self.bot.replies[-1][1])
        self.assertEqual(self.lords(), [PLAYER])

    def test_disabled_setlord_feature_blocks_the_command(self):
        admin_panel._set_feature('setlord', False)
        admin_panel.handle_unsetlord(self.command(OWNER, User(PLAYER)))
        self.assertEqual(self.lords(), [PLAYER])
        self.assertIn('disabled', self.bot.replies[-1][1])

    def test_removal_is_logged(self):
        admin_panel.handle_unsetlord(self.command(OWNER, User(PLAYER)))
        entry = admin_panel.recent_log()[0]
        self.assertEqual(entry['action'], 'lord_unassign')
        self.assertEqual(entry['detail'], str(PLAYER))

    def test_only_the_named_group_loses_its_lord(self):
        add_group(self.conn, HELPER, GROUP_B)
        admin_panel.handle_unsetlord(self.command(OWNER, User(PLAYER)))
        self.assertEqual(self.lords(GROUP_B), [HELPER])

    # --- the group form -------------------------------------------------

    def test_no_reply_offers_the_group_a_confirmation_first(self):
        admin_panel.handle_unsetlord(self.command(OWNER))
        self.assertEqual(self.lords(), [PLAYER])
        self.assertIn('Retire', self.bot.replies[-1][1])
        self.assertEqual(self.bot.last_keyboard(), [f'ap:ulc:{GROUP_A}'])

    def test_a_promoted_admin_cannot_retire_a_group(self):
        self.promote_helper()
        admin_panel.handle_unsetlord(self.command(HELPER))
        self.assertEqual(self.lords(), [PLAYER])
        self.assertIn('owner', self.bot.replies[-1][1])

    def test_a_promoted_admin_cannot_confirm_a_retirement(self):
        self.promote_helper()
        admin_panel.handle_callback(self.call(f'ap:ulc:{GROUP_A}', user_id=HELPER))
        self.assertEqual(self.lords(), [PLAYER])
        _, text, alert = self.bot.last_answer()
        self.assertTrue(alert)
        self.assertIn('owner', text)

    def test_confirming_removes_every_lord_of_the_group(self):
        add_group(self.conn, HELPER, GROUP_A)
        admin_panel.handle_callback(self.call(f'ap:ulc:{GROUP_A}'))
        self.assertEqual(self.lords(), [])
        self.assertIn('retired', self.bot.edits[-1][2])

    def test_retiring_a_group_leaves_the_others_alone(self):
        add_group(self.conn, HELPER, GROUP_B)
        admin_panel.handle_callback(self.call(f'ap:ulc:{GROUP_A}'))
        self.assertEqual(self.lords(GROUP_B), [HELPER])

    def test_retirement_is_logged(self):
        admin_panel.handle_callback(self.call(f'ap:ulc:{GROUP_A}'))
        entry = admin_panel.recent_log()[0]
        self.assertEqual(entry['action'], 'group_unassign')
        self.assertEqual(entry['detail'], str(PLAYER))

    def test_a_group_with_no_lords_is_reported_not_wiped(self):
        admin_panel.handle_unsetlord(self.command(OWNER, group_id=GROUP_B))
        self.assertIn('no lord', self.bot.replies[-1][1])

    # --- the live-trade guard -------------------------------------------

    def test_a_group_with_a_trade_in_flight_keeps_its_lord(self):
        admin_panel.set_lord_guard(lambda: {GROUP_A})
        admin_panel.handle_unsetlord(self.command(OWNER, User(PLAYER)))
        self.assertEqual(self.lords(), [PLAYER])
        self.assertIn('shipment', self.bot.replies[-1][1])

    def test_the_guard_also_stops_a_confirmed_retirement(self):
        admin_panel.set_lord_guard(lambda: {GROUP_A})
        admin_panel.handle_callback(self.call(f'ap:ulc:{GROUP_A}'))
        self.assertEqual(self.lords(), [PLAYER])
        self.assertTrue(self.bot.last_answer()[2])

    def test_a_trade_elsewhere_does_not_block_this_group(self):
        admin_panel.set_lord_guard(lambda: {GROUP_B})
        admin_panel.handle_unsetlord(self.command(OWNER, User(PLAYER)))
        self.assertEqual(self.lords(), [])

    def test_an_unreadable_guard_deletes_nothing(self):
        def broken():
            raise RuntimeError('trades table is gone')
        admin_panel.set_lord_guard(broken)
        admin_panel.handle_unsetlord(self.command(OWNER, User(PLAYER)))
        self.assertEqual(self.lords(), [PLAYER])
        self.assertIn('Could not check', self.bot.replies[-1][1])

    # --- what a removal takes with it -----------------------------------

    def test_the_last_lord_leaving_releases_the_chokepoints(self):
        self.own('sue')
        admin_panel.handle_unsetlord(self.command(OWNER, User(PLAYER)))
        self.assertEqual(self.owners(), [])

    def test_a_co_lord_leaving_keeps_the_chokepoints(self):
        add_group(self.conn, HELPER, GROUP_A)
        self.own('sue')
        admin_panel.handle_unsetlord(self.command(OWNER, User(PLAYER)))
        self.assertEqual(self.lords(), [HELPER])
        self.assertEqual(self.owners(), ['sue'])

    def test_another_groups_chokepoints_survive(self):
        self.own('sue')
        self.own('hor', GROUP_B)
        admin_panel.handle_callback(self.call(f'ap:ulc:{GROUP_A}'))
        self.assertEqual(self.owners(), ['hor'])

    def test_a_removed_lord_can_be_appointed_again(self):
        admin_panel.handle_unsetlord(self.command(OWNER, User(PLAYER)))
        admin_panel.handle_setlord(Message(Chat(GROUP_A), User(OWNER), text='/setlord',
                                           reply_to_message=Message(Chat(GROUP_A), User(PLAYER))))
        self.assertEqual(self.lords(), [PLAYER])


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


class LogClearTest(PanelTestCase):

    def setUp(self):
        super().setUp()
        admin_panel._admin_add_apply(Message(Chat(OWNER, 'private'), User(OWNER),
                                             text=str(HELPER)), OWNER)
        for i in range(3):
            admin_panel.log(OWNER, 'asset_edit', f'g{i}')

    def test_clearing_empties_the_log(self):
        admin_panel.handle_callback(self.call('ap:lgcc'))
        self.assertEqual(admin_panel.recent_log(), [])

    def test_clearing_reports_how_many_rows_went(self):
        admin_panel.handle_callback(self.call('ap:lgcc'))
        self.assertIn('4', self.bot.edits[-1][2])  # 3 edits + the admin_add

    def test_the_wipe_leaves_no_entry_of_its_own(self):
        admin_panel.handle_callback(self.call('ap:lgcc'))
        admin_panel.handle_callback(self.call('ap:log:0'))
        self.assertIn('No admin action', self.bot.edits[-1][2])

    def test_every_admin_is_told_who_cleared_it(self):
        self.bot.sent.clear()
        admin_panel.handle_callback(self.call('ap:lgcc'))
        told = [chat for chat, _ in self.bot.sent]
        self.assertIn(HELPER, told)
        self.assertIn('cleared the action log', self.bot.sent[-1][1])

    def test_a_plain_admin_cannot_clear_the_log(self):
        admin_panel.handle_callback(self.call('ap:lgcc', user_id=HELPER))
        self.assertNotEqual(admin_panel.recent_log(), [])

    def test_a_stranger_cannot_clear_the_log(self):
        admin_panel.handle_callback(self.call('ap:lgcc', user_id=PLAYER))
        self.assertNotEqual(admin_panel.recent_log(), [])

    def test_the_clear_button_is_offered_to_the_owner_only(self):
        admin_panel.handle_callback(self.call('ap:log:0'))
        self.assertIn('ap:lgc', self.bot.last_keyboard())
        admin_panel.handle_callback(self.call('ap:log:0', user_id=HELPER))
        self.assertNotIn('ap:lgc', self.bot.last_keyboard())

    def test_the_confirmation_names_the_row_count(self):
        admin_panel.handle_callback(self.call('ap:lgc'))
        self.assertIn('4', self.bot.edits[-1][2])
        self.assertIn('ap:lgcc', self.bot.last_keyboard())


class FactoryResetTest(PanelTestCase):

    def setUp(self):
        super().setUp()
        add_group(self.conn, PLAYER, GROUP_A, money=7)
        catalog.add('archers', 'unit', {'en': 'Archers'}, default_value=750)
        self.addCleanup(catalog.set_delete_guard, None)

    def columns(self):
        return {row[1] for row in self.conn.execute("PRAGMA table_info(users)").fetchall()}

    def test_reset_destroys_custom_types(self):
        admin_panel.handle_callback(self.call('ap:facc'))
        self.assertNotIn('archers', self.columns())

    def test_reset_restores_builtin_tuning(self):
        catalog.set_default('money', 999999)
        admin_panel.handle_callback(self.call('ap:facc'))
        self.assertEqual(catalog.defaults()['money'], catalog.RESOURCE_DEFAULT)

    def test_reset_leaves_group_balances_alone(self):
        admin_panel.handle_callback(self.call('ap:facc'))
        row = self.conn.execute("SELECT money FROM users WHERE group_id=?", (GROUP_A,)).fetchone()
        self.assertEqual(row[0], 7)

    def test_reset_also_empties_the_log(self):
        admin_panel.log(OWNER, 'asset_edit', 'something')
        admin_panel.handle_callback(self.call('ap:facc'))
        self.assertEqual(admin_panel.recent_log(), [])

    def test_a_plain_admin_cannot_factory_reset(self):
        admin_panel._admin_add_apply(Message(Chat(OWNER, 'private'), User(OWNER),
                                             text=str(HELPER)), OWNER)
        admin_panel.handle_callback(self.call('ap:facc', user_id=HELPER))
        self.assertIn('archers', self.columns())

    def test_a_key_in_flight_blocks_the_reset(self):
        catalog.set_delete_guard(lambda: {'archers'})
        admin_panel.handle_callback(self.call('ap:facc'))
        self.assertIn('archers', self.columns())
        self.assertTrue(self.bot.last_answer()[2], 'the refusal should be an alert')

    def test_the_confirmation_names_what_will_be_destroyed(self):
        admin_panel.handle_callback(self.call('ap:fac'))
        self.assertIn('archers', self.bot.edits[-1][2])
        self.assertIn('ap:facc', self.bot.last_keyboard())

    def test_the_confirmation_copes_with_nothing_to_destroy(self):
        catalog.remove('archers')
        admin_panel.handle_callback(self.call('ap:fac'))
        self.assertIn('ap:facc', self.bot.last_keyboard())

    def test_the_panel_offers_it_to_the_owner_only(self):
        admin_panel._admin_add_apply(Message(Chat(OWNER, 'private'), User(OWNER),
                                             text=str(HELPER)), OWNER)
        admin_panel.handle_callback(self.call('ap:home'))
        self.assertIn('ap:fac', self.bot.last_keyboard())
        admin_panel.handle_callback(self.call('ap:home', user_id=HELPER))
        self.assertNotIn('ap:fac', self.bot.last_keyboard())


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
