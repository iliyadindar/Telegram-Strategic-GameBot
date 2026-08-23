# -*- coding: utf-8 -*-
"""Statements and campaigns: the confirmation step (13), unlimited length (14),
who may speak and from where (15), and the master on/off switch (16)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import admin_panel
import broadcast
from stubs import Call, Chat, Message, StubBot, User, add_group, make_db

OWNER = 100
LORD = 300
STRANGER = 400
PERSIA = -1001
ROME = -1002


class Photo:
    def __init__(self, file_id):
        self.file_id = file_id


class BroadcastTestCase(unittest.TestCase):

    def setUp(self):
        self.conn = make_db()
        self.addCleanup(self.conn.close)
        self.bot = StubBot(chats={
            OWNER: Chat(OWNER, 'private', first_name='Owner'),
            LORD: Chat(LORD, 'private', first_name='Cyrus'),
            STRANGER: Chat(STRANGER, 'private', first_name='Nobody'),
            PERSIA: Chat(PERSIA, title='Persia'),
            ROME: Chat(ROME, title='Rome'),
        })
        admin_panel._title_cache.clear()
        admin_panel._name_cache.clear()
        admin_panel.set_lord_guard(None)
        admin_panel.init(self.bot, self.conn, OWNER, '@news', '@war', lang='en')
        broadcast._drafts.clear()
        self.addCleanup(broadcast._drafts.clear)
        broadcast.init(self.bot, self.conn, '@news', '@war', lang='en',
                       is_admin=admin_panel.is_admin,
                       notify_admins=admin_panel.notify_admins,
                       war_photo=admin_panel.war_photo, audit=admin_panel.log)
        add_group(self.conn, LORD, PERSIA)
        add_group(self.conn, 2, ROME)

    # --- helpers --------------------------------------------------------
    def tap(self, data, user_id=LORD, chat=PERSIA):
        broadcast.handle_callback(
            Call(data, User(user_id), Message(Chat(chat), User(user_id))))

    def feed(self, message):
        self.bot.next_steps[-1][1](message)

    def posts(self, channel='@news'):
        return [text for chat, text in self.bot.sent if chat == channel]

    def group_chat(self, group_id=PERSIA):
        return Chat(group_id, 'supergroup', title=self.bot._chats[group_id].title)


# ---------------------------------------------------------------------------
# Item 15 — who may issue a statement, and from where
# ---------------------------------------------------------------------------


class StatementAccessTest(BroadcastTestCase):

    def test_a_lord_may_speak_inside_their_group(self):
        broadcast.start_statement(Message(self.group_chat(), User(LORD)), LORD)
        self.assertTrue(self.bot.next_steps)

    def test_a_lord_may_not_speak_in_private(self):
        broadcast.start_statement(Message(Chat(LORD, 'private'), User(LORD)), LORD)
        self.assertIn('private chat', self.bot.last_sent_text())
        self.assertEqual(self.bot.next_steps, [])

    def test_a_stranger_may_not_speak_for_a_group_they_do_not_lead(self):
        broadcast.start_statement(Message(self.group_chat(), User(STRANGER)), STRANGER)
        self.assertIn('not a lord', self.bot.last_sent_text())
        self.assertEqual(self.bot.next_steps, [])

    def test_a_group_with_no_country_cannot_speak(self):
        empty = Chat(-9999, 'supergroup', title='Nowhere')
        broadcast.start_statement(Message(empty, User(LORD)), LORD)
        self.assertIn('no country', self.bot.last_sent_text())

    def test_an_admin_in_private_is_asked_which_country(self):
        broadcast.start_statement(Message(Chat(OWNER, 'private'), User(OWNER)), OWNER)
        self.assertEqual(sorted(self.bot.last_keyboard()),
                         sorted([f'bc:sg:{PERSIA}', f'bc:sg:{ROME}']))

    def test_picking_a_country_starts_the_draft(self):
        broadcast.start_statement(Message(Chat(OWNER, 'private'), User(OWNER)), OWNER)
        self.tap(f'bc:sg:{ROME}', user_id=OWNER, chat=OWNER)
        self.assertEqual(broadcast._drafts[OWNER]['group_id'], ROME)

    def test_a_player_cannot_pick_a_country_by_callback(self):
        self.tap(f'bc:sg:{ROME}', user_id=LORD, chat=LORD)
        self.assertNotIn(LORD, broadcast._drafts)

    def test_an_admin_may_still_speak_from_a_group(self):
        broadcast.start_statement(Message(self.group_chat(), User(OWNER)), OWNER)
        self.assertTrue(self.bot.next_steps)


# ---------------------------------------------------------------------------
# Item 13 — nothing is posted until it is confirmed
# ---------------------------------------------------------------------------


class StatementConfirmTest(BroadcastTestCase):

    def draft(self, text='We march at dawn.'):
        broadcast.start_statement(Message(self.group_chat(), User(LORD)), LORD)
        self.feed(Message(self.group_chat(), User(LORD), text=text))

    def test_writing_one_posts_nothing_yet(self):
        self.draft()
        self.assertEqual(self.posts(), [])

    def test_the_preview_offers_both_buttons(self):
        self.draft()
        self.assertEqual(self.bot.last_keyboard(), ['bc:sok', 'bc:sx'])

    def test_the_preview_shows_the_text_and_the_country(self):
        self.draft()
        preview = self.bot.last_sent_text()
        self.assertIn('We march at dawn.', preview)
        self.assertIn('Persia', preview)

    def test_confirming_posts_it(self):
        self.draft()
        self.tap('bc:sok')
        self.assertEqual(len(self.posts()), 1)
        self.assertIn('We march at dawn.', self.posts()[0])

    def test_the_post_carries_the_country_and_the_commander(self):
        self.draft()
        self.tap('bc:sok')
        self.assertIn('Persia', self.posts()[0])
        self.assertIn('Cyrus', self.posts()[0])

    def test_cancelling_posts_nothing(self):
        self.draft()
        self.tap('bc:sx')
        self.assertEqual(self.posts(), [])
        self.assertNotIn(LORD, broadcast._drafts)

    def test_confirming_twice_posts_once(self):
        self.draft()
        self.tap('bc:sok')
        self.tap('bc:sok')
        self.assertEqual(len(self.posts()), 1)

    def test_an_empty_statement_is_refused(self):
        broadcast.start_statement(Message(self.group_chat(), User(LORD)), LORD)
        self.feed(Message(self.group_chat(), User(LORD), text=''))
        self.assertIn('nothing to send', self.bot.last_sent_text())
        self.assertNotIn(LORD, broadcast._drafts)

    def test_it_is_logged_once_sent(self):
        self.draft()
        self.tap('bc:sok')
        self.assertEqual(admin_panel.recent_log()[0]['action'], 'statement')

    def test_a_failure_to_post_is_reported_rather_than_swallowed(self):
        self.draft()
        original = self.bot.send_message

        def explode(chat_id, text, **kwargs):
            if chat_id == '@news':
                raise RuntimeError('channel is gone')
            return original(chat_id, text, **kwargs)

        self.bot.send_message = explode
        self.tap('bc:sok')
        self.assertIn('could not be sent', self.bot.last_sent_text())


# ---------------------------------------------------------------------------
# Item 14 — a statement may be as long as it likes
# ---------------------------------------------------------------------------


class StatementLengthTest(BroadcastTestCase):

    def test_a_short_body_is_one_piece(self):
        self.assertEqual(broadcast.chunks('hello'), ['hello'])

    def test_an_empty_body_is_no_pieces(self):
        self.assertEqual(broadcast.chunks(''), [])

    def test_a_long_body_is_split_below_the_limit(self):
        body = '\n'.join('line %d' % i for i in range(3000))
        pieces = broadcast.chunks(body)
        self.assertGreater(len(pieces), 1)
        for piece in pieces:
            self.assertLessEqual(len(piece), broadcast.TEXT_LIMIT)

    def test_splitting_loses_nothing(self):
        body = '\n'.join('line %d' % i for i in range(3000))
        self.assertEqual('\n'.join(broadcast.chunks(body)), body)

    def test_it_breaks_between_lines_where_it_can(self):
        body = '\n'.join('x' * 100 for _ in range(200))
        for piece in broadcast.chunks(body):
            self.assertFalse(piece.startswith('\n'))
            self.assertEqual(set(piece.replace('\n', '')), {'x'})

    def test_a_single_enormous_line_is_still_split(self):
        body = 'y' * 10000
        pieces = broadcast.chunks(body)
        self.assertEqual(''.join(pieces), body)
        for piece in pieces:
            self.assertLessEqual(len(piece), broadcast.TEXT_LIMIT)

    def test_a_very_long_statement_goes_out_in_several_messages(self):
        body = '\n'.join('Paragraph %d of the declaration.' % i for i in range(500))
        broadcast.start_statement(Message(self.group_chat(), User(LORD)), LORD)
        self.feed(Message(self.group_chat(), User(LORD), text=body))
        self.tap('bc:sok')
        posts = self.posts()
        self.assertGreater(len(posts), 1)
        for post in posts:
            self.assertLessEqual(len(post), broadcast.TEXT_LIMIT)

    def test_the_attribution_rides_on_the_last_message(self):
        body = '\n'.join('Paragraph %d of the declaration.' % i for i in range(500))
        broadcast.start_statement(Message(self.group_chat(), User(LORD)), LORD)
        self.feed(Message(self.group_chat(), User(LORD), text=body))
        self.tap('bc:sok')
        self.assertIn('Cyrus', self.posts()[-1])

    def test_the_preview_warns_how_many_messages_it_will_take(self):
        body = '\n'.join('Paragraph %d of the declaration.' % i for i in range(500))
        broadcast.start_statement(Message(self.group_chat(), User(LORD)), LORD)
        self.feed(Message(self.group_chat(), User(LORD), text=body))
        self.assertIn('messages in a row', self.bot.last_sent_text())


class StatementMediaTest(BroadcastTestCase):

    def send_photo_statement(self, caption):
        broadcast.start_statement(Message(self.group_chat(), User(LORD)), LORD)
        message = Message(self.group_chat(), User(LORD))
        message.caption = caption
        message.photo = [Photo('PIC')]
        self.feed(message)
        self.tap('bc:sok')

    def test_a_short_caption_rides_on_the_photo(self):
        self.send_photo_statement('Behold')
        self.assertEqual(self.bot.photos[-1][1], 'PIC')
        self.assertIn('Behold', self.bot.photos[-1][2])
        self.assertEqual(self.posts(), [])

    def test_a_long_caption_sends_the_photo_then_the_words(self):
        self.send_photo_statement('word ' * 500)
        self.assertEqual(self.bot.photos[-1][1], 'PIC')
        self.assertTrue(self.posts(), 'the text should follow as its own message')
        self.assertIn('word', self.posts()[0])

    def test_a_photo_with_no_caption_still_goes(self):
        self.send_photo_statement(None)
        self.assertEqual(self.bot.photos[-1][1], 'PIC')

    def test_the_preview_says_there_is_an_attachment(self):
        broadcast.start_statement(Message(self.group_chat(), User(LORD)), LORD)
        message = Message(self.group_chat(), User(LORD))
        message.caption = 'Behold'
        message.photo = [Photo('PIC')]
        self.feed(message)
        self.assertIn('attachment', self.bot.last_sent_text())


# ---------------------------------------------------------------------------
# Item 13 again — campaigns
# ---------------------------------------------------------------------------


class CampaignTest(BroadcastTestCase):

    def run_wizard(self):
        broadcast.start_campaign(Message(self.group_chat(), User(LORD)), LORD)
        self.tap('bc:at:land')
        for answer in ('9000 swordsmen', 'Persepolis', 'Athens', 'dawn'):
            self.feed(Message(self.group_chat(), User(LORD), text=answer))

    def test_the_wizard_ends_in_a_preview_not_a_post(self):
        self.run_wizard()
        self.assertEqual(self.posts('@war'), [])
        self.assertEqual(self.bot.last_keyboard(), ['bc:aok', 'bc:ax'])

    def test_confirming_announces_it(self):
        self.run_wizard()
        self.tap('bc:aok')
        self.assertEqual(len(self.posts('@war')), 1)
        self.assertIn('Persepolis', self.posts('@war')[0])

    def test_the_public_post_still_hides_the_troop_counts(self):
        self.run_wizard()
        self.tap('bc:aok')
        self.assertNotIn('9000 swordsmen', self.posts('@war')[0])

    def test_the_owner_still_gets_the_full_report(self):
        self.run_wizard()
        self.tap('bc:aok')
        private = [text for chat, text in self.bot.sent if chat == OWNER]
        self.assertTrue(any('9000 swordsmen' in text for text in private))

    def test_cancelling_announces_nothing(self):
        self.run_wizard()
        self.tap('bc:ax')
        self.assertEqual(self.posts('@war'), [])
        self.assertNotIn(LORD, broadcast._drafts)

    def test_a_blank_answer_is_re_asked(self):
        broadcast.start_campaign(Message(self.group_chat(), User(LORD)), LORD)
        self.tap('bc:at:land')
        self.feed(Message(self.group_chat(), User(LORD), text='   '))
        # it complains, then asks the same question again
        self.assertTrue(any('Nothing was entered' in text for _, text in self.bot.sent))
        self.assertIn('army information', self.bot.last_sent_text())
        self.feed(Message(self.group_chat(), User(LORD), text='9000 swordsmen'))
        self.assertEqual(broadcast._drafts[LORD]['details'], '9000 swordsmen')

    def test_two_commanders_do_not_mix(self):
        add_group(self.conn, STRANGER, ROME)
        self.run_wizard()
        broadcast.start_campaign(Message(self.group_chat(ROME), User(STRANGER)), STRANGER)
        broadcast.handle_callback(
            Call('bc:at:sea', User(STRANGER), Message(self.group_chat(ROME), User(STRANGER))))
        self.assertEqual(broadcast._drafts[LORD]['type'], 'land')
        self.assertEqual(broadcast._drafts[STRANGER]['type'], 'sea')

    def test_a_confirm_with_no_draft_says_so(self):
        self.tap('bc:aok')
        self.assertTrue(self.bot.last_answer()[2])

    def test_an_unknown_campaign_type_is_refused(self):
        self.tap('bc:at:air')
        self.assertNotIn(LORD, broadcast._drafts)


# ---------------------------------------------------------------------------
# Item 16 — /on and /off
# ---------------------------------------------------------------------------


class MasterSwitchTest(BroadcastTestCase):

    def command(self, user_id, text='/off'):
        return Message(self.group_chat(), User(user_id), text=text)

    def player_call(self, data='assets'):
        return Call(data, User(LORD), Message(self.group_chat(), User(LORD)))

    def test_the_bot_starts_open(self):
        self.assertTrue(admin_panel.players_enabled())
        self.assertTrue(admin_panel.open_to(LORD))

    def test_off_closes_it_for_players(self):
        admin_panel.handle_onoff(self.command(OWNER), False)
        self.assertFalse(admin_panel.players_enabled())
        self.assertFalse(admin_panel.open_to(LORD))

    def test_admins_are_never_locked_out(self):
        admin_panel.handle_onoff(self.command(OWNER), False)
        self.assertTrue(admin_panel.open_to(OWNER))

    def test_a_player_callback_is_refused_while_closed(self):
        admin_panel.handle_onoff(self.command(OWNER), False)
        self.assertFalse(admin_panel.require_feature(self.player_call(), 'assets'))
        self.assertTrue(self.bot.last_answer()[2])

    def test_an_admin_callback_still_works_while_closed(self):
        admin_panel.handle_onoff(self.command(OWNER), False)
        call = Call('assets', User(OWNER), Message(self.group_chat(), User(OWNER)))
        self.assertTrue(admin_panel.require_feature(call, 'assets'))

    def test_on_opens_it_again(self):
        admin_panel.handle_onoff(self.command(OWNER), False)
        admin_panel.handle_onoff(self.command(OWNER, '/on'), True)
        self.assertTrue(admin_panel.players_enabled())

    def test_a_player_cannot_flip_it(self):
        admin_panel.handle_onoff(self.command(LORD), False)
        self.assertTrue(admin_panel.players_enabled())
        self.assertIn('not an admin', self.bot.replies[-1][1])

    def test_flipping_it_twice_says_it_was_already_that_way(self):
        admin_panel.handle_onoff(self.command(OWNER), False)
        admin_panel.handle_onoff(self.command(OWNER), False)
        self.assertIn('already closed', self.bot.replies[-1][1])

    def test_it_is_logged(self):
        admin_panel.handle_onoff(self.command(OWNER), False)
        self.assertEqual(admin_panel.recent_log()[0]['action'], 'bot_switch')

    def test_the_feature_screen_carries_the_switch(self):
        admin_panel.handle_callback(
            Call('ap:feat', User(OWNER), Message(self.group_chat(), User(OWNER))))
        self.assertIn('ap:ftall', self.bot.last_keyboard())

    def test_the_panel_button_flips_it(self):
        admin_panel.handle_callback(
            Call('ap:ftall', User(OWNER), Message(self.group_chat(), User(OWNER))))
        self.assertFalse(admin_panel.players_enabled())

    def test_the_panel_header_says_when_the_game_is_closed(self):
        admin_panel.handle_onoff(self.command(OWNER), False)
        admin_panel.open_panel(PERSIA, OWNER)
        self.assertIn('closed to players', self.bot.last_sent_text())


if __name__ == '__main__':
    unittest.main()
