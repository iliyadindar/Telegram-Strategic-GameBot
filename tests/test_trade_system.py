# -*- coding: utf-8 -*-
"""Trade system: RTL arrow direction, photo storage and caption fallback."""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import trade_system
from admin_strings import ALL_COLS, DEFAULTS
from stubs import Chat, Message, StubBot, User, make_db

RIGHT_ARROW = '→'   # →
LEFT_ARROW = '←'    # ←


class ArrowDirectionTest(unittest.TestCase):
    """Persian renders right-to-left, so its arrows must be mirrored."""

    def test_persian_route_separator_points_left(self):
        self.assertEqual(trade_system.STRINGS['fa']['path_arrow'].strip(), LEFT_ARROW)

    def test_latin_route_separators_point_right(self):
        for lang in ('en', 'tr'):
            self.assertEqual(trade_system.STRINGS[lang]['path_arrow'].strip(), RIGHT_ARROW,
                             f'{lang} should keep the left-to-right arrow')

    def test_persian_previous_button_points_right(self):
        self.assertIn('➡', trade_system.STRINGS['fa']['btn_prev'])
        self.assertNotIn('⬅', trade_system.STRINGS['fa']['btn_prev'])

    def test_persian_next_button_points_left(self):
        self.assertIn('⬅', trade_system.STRINGS['fa']['btn_next'])
        self.assertNotIn('➡', trade_system.STRINGS['fa']['btn_next'])

    def test_latin_pagination_is_unchanged(self):
        for lang in ('en', 'tr'):
            self.assertIn('⬅', trade_system.STRINGS[lang]['btn_prev'])
            self.assertIn('➡', trade_system.STRINGS[lang]['btn_next'])

    def test_no_hardcoded_right_arrow_remains_in_persian_text(self):
        offenders = [k for k, v in trade_system.STRINGS['fa'].items()
                     if isinstance(v, str) and RIGHT_ARROW in v]
        self.assertEqual(offenders, [])

    def test_all_languages_share_the_same_keys(self):
        reference = set(trade_system.STRINGS['fa'])
        for lang, table in trade_system.STRINGS.items():
            self.assertEqual(set(table), reference, f'{lang} keys differ')


class PathRenderingTest(unittest.TestCase):

    def setUp(self):
        self.conn = make_db()
        self.bot = StubBot()
        trade_system.init(self.bot, self.conn, 1, '@news', lang='fa')

    def tearDown(self):
        trade_system._lang = 'fa'

    def path(self, lang):
        trade_system._lang = lang
        sea = list(trade_system.SEA_NODES)[:3]
        return trade_system._path_names('sea', sea)

    def test_persian_path_uses_the_left_arrow(self):
        rendered = self.path('fa')
        self.assertIn(LEFT_ARROW, rendered)
        self.assertNotIn(RIGHT_ARROW, rendered)

    def test_english_path_uses_the_right_arrow(self):
        rendered = self.path('en')
        self.assertIn(RIGHT_ARROW, rendered)
        self.assertNotIn(LEFT_ARROW, rendered)

    def test_path_lists_every_stop(self):
        trade_system._lang = 'en'
        sea = list(trade_system.SEA_NODES)[:3]
        self.assertEqual(len(self.path('en').split(RIGHT_ARROW)), 3)


class TradePhotoTest(unittest.TestCase):

    def setUp(self):
        self.conn = make_db()
        self.bot = StubBot(chats={-1: Chat(-1, title='Persia')})
        trade_system.init(self.bot, self.conn, 1, '@news', lang='en')
        trade_system.set_photo('')

    def test_no_photo_by_default(self):
        self.assertEqual(trade_system.photo(), '')

    def test_set_and_read_back(self):
        trade_system.set_photo('FILE1')
        self.assertEqual(trade_system.photo(), 'FILE1')

    def test_clearing_removes_it(self):
        trade_system.set_photo('FILE1')
        trade_system.set_photo('')
        self.assertEqual(trade_system.photo(), '')

    def test_send_falls_back_to_text_without_a_photo(self):
        message, used_photo = trade_system._send_rich(-1, 'hello')
        self.assertFalse(used_photo)
        self.assertEqual(self.bot.sent[-1], (-1, 'hello'))
        self.assertEqual(self.bot.photos, [])

    def test_send_uses_a_caption_when_a_photo_is_set(self):
        trade_system.set_photo('FILE1')
        _, used_photo = trade_system._send_rich(-1, 'hello')
        self.assertTrue(used_photo)
        self.assertEqual(self.bot.photos[-1], (-1, 'FILE1', 'hello'))

    def test_overlong_bodies_stay_text_because_captions_are_capped(self):
        trade_system.set_photo('FILE1')
        long_text = 'x' * (trade_system.CAPTION_LIMIT + 1)
        _, used_photo = trade_system._send_rich(-1, long_text)
        self.assertFalse(used_photo)
        self.assertEqual(self.bot.photos, [])

    def test_text_at_exactly_the_caption_limit_still_uses_the_photo(self):
        trade_system.set_photo('FILE1')
        _, used_photo = trade_system._send_rich(-1, 'x' * trade_system.CAPTION_LIMIT)
        self.assertTrue(used_photo)

    def test_a_broken_file_id_degrades_to_a_text_message(self):
        trade_system.set_photo('STALE')

        def boom(*args, **kwargs):
            raise RuntimeError('wrong file identifier')

        self.bot.send_photo = boom
        _, used_photo = trade_system._send_rich(-1, 'hello')
        self.assertFalse(used_photo)
        self.assertEqual(self.bot.sent[-1], (-1, 'hello'))

    def test_photo_messages_are_edited_as_captions(self):
        trade_system._edit_rich(-1, 7, 'updated', True)
        self.assertEqual(self.bot.edits[-1], (-1, 7, 'updated'))

    def test_text_messages_are_edited_as_text(self):
        trade_system._edit_rich(-1, 7, 'updated', False)
        self.assertEqual(self.bot.edits[-1], (-1, 7, 'updated'))

    def test_migration_adds_the_photo_columns(self):
        cols = [r[1] for r in self.conn.execute("PRAGMA table_info(trades)").fetchall()]
        self.assertIn('offer_photo', cols)
        self.assertIn('track_photo', cols)

    def test_admin_upload_stores_the_largest_size(self):
        photo = [type('P', (), {'file_id': 'small'})(), type('P', (), {'file_id': 'big'})()]
        trade_system._photo_save(Message(Chat(1, 'private'), User(1), photo=photo), 1)
        self.assertEqual(trade_system.photo(), 'big')

    def test_non_admin_upload_is_ignored(self):
        photo = [type('P', (), {'file_id': 'big'})()]
        trade_system._photo_save(Message(Chat(1, 'private'), User(99), photo=photo), 99)
        self.assertEqual(trade_system.photo(), '')

    def test_non_photo_message_is_rejected(self):
        trade_system._photo_save(Message(Chat(1, 'private'), User(1), text='nope'), 1)
        self.assertEqual(trade_system.photo(), '')
        self.assertIn('not a photo', self.bot.last_sent_text())


class AdminDelegationTest(unittest.TestCase):

    def setUp(self):
        self.conn = make_db()
        self.bot = StubBot()

    def test_without_a_predicate_only_the_configured_owner_passes(self):
        trade_system.init(self.bot, self.conn, 7, '@news', lang='en')
        self.assertTrue(trade_system._admin_check(7))
        self.assertFalse(trade_system._admin_check(8))

    def test_an_injected_predicate_widens_access(self):
        trade_system.init(self.bot, self.conn, 7, '@news', lang='en',
                          is_admin=lambda uid: uid in (7, 8))
        self.assertTrue(trade_system._admin_check(8))

    def test_audit_hook_receives_admin_mutations(self):
        seen = []
        trade_system.init(self.bot, self.conn, 7, '@news', lang='en',
                          audit=lambda *a: seen.append(a))
        trade_system._log(7, 'trade_config', 'fee_per_unit', '25')
        self.assertEqual(seen, [(7, 'trade_config', 'fee_per_unit', '25')])

    def test_a_failing_audit_hook_does_not_break_the_action(self):
        def boom(*args):
            raise RuntimeError('log backend down')

        trade_system.init(self.bot, self.conn, 7, '@news', lang='en', audit=boom)
        trade_system._log(7, 'trade_photo', '', 'set')   # must not raise


class SchemaAgreementTest(unittest.TestCase):
    """The reset defaults must match the schema the bots actually create."""

    def test_admin_strings_defaults_match_the_users_table_in_main(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, 'main.py'), encoding='utf-8') as fh:
            source = fh.read()
        block = source.split("CREATE TABLE IF NOT EXISTS users", 1)[1].split("'''", 1)[0]
        declared = dict((m[0], int(m[1]))
                        for m in re.findall(r"(\w+) INTEGER DEFAULT (\d+)", block))
        for col in ALL_COLS:
            self.assertIn(col, declared, f'{col} is not a column of users')
            self.assertEqual(declared[col], DEFAULTS[col],
                             f'{col} default drifted from the schema')


if __name__ == '__main__':
    unittest.main()
