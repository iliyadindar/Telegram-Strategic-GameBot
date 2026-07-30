# -*- coding: utf-8 -*-
"""Load main.py / main-en.py / main-tr.py end to end against a stub bot.

This catches wiring mistakes the unit tests cannot see: a missing import, a
handler that references an undefined name, or the three language builds
drifting apart.
"""

import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import telebot

from stubs import Call, Chat, Message, StubBot, User

ENTRYPOINTS = ('main.py', 'main-en.py', 'main-tr.py')

ENV = {
    'BOT_TOKEN': '12345:ABCdef',
    'ADMIN_ID': '4242',
    'CHANNEL_ID': '@news',
    'WAR_CHANNEL_ID': '@war',
}


def load_entrypoint(filename, workdir):
    """Import a bot entrypoint with Telegram replaced by a stub."""
    bots = []

    def factory(*args, **kwargs):
        bot = StubBot()
        bots.append(bot)
        return bot

    real_teleboT = telebot.TeleBot
    old_env = {k: os.environ.get(k) for k in ENV}
    old_cwd = os.getcwd()
    module_name = filename.replace('.py', '').replace('-', '_') + '_under_test'
    telebot.TeleBot = factory
    os.environ.update(ENV)
    os.chdir(workdir)
    try:
        spec = importlib.util.spec_from_file_location(module_name,
                                                      os.path.join(ROOT, filename))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, bots[0]
    finally:
        telebot.TeleBot = real_teleboT
        os.chdir(old_cwd)
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        sys.modules.pop(module_name, None)


class EntrypointTest(unittest.TestCase):

    def setUp(self):
        # ignore_cleanup_errors: on Windows the sqlite file can still be held
        # by the daemon trade ticker when the directory is removed.
        self.dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.dir.cleanup)

    def load(self, filename):
        module, bot = load_entrypoint(filename, self.dir.name)
        self.addCleanup(module.conn.close)
        return module, bot

    def test_every_entrypoint_imports_and_starts_polling(self):
        for filename in ENTRYPOINTS:
            with self.subTest(filename):
                module, bot = self.load(filename)
                self.assertTrue(bot.polled, 'the bot never started polling')
                self.assertIsNotNone(module.WAR_CHANNEL_ID)

    def test_credentials_come_from_the_environment_not_the_source(self):
        for filename in ENTRYPOINTS:
            with self.subTest(filename):
                module, _ = self.load(filename)
                self.assertEqual(module.API_TOKEN, ENV['BOT_TOKEN'])
                self.assertEqual(module.ADMIN_ID, 4242)
                self.assertEqual(module.CHANNEL_ID, '@news')
                self.assertEqual(module.WAR_CHANNEL_ID, '@war')

    def test_no_placeholder_credentials_remain_in_the_source(self):
        for filename in ENTRYPOINTS:
            with self.subTest(filename):
                with open(os.path.join(ROOT, filename), encoding='utf-8') as fh:
                    source = fh.read()
                self.assertNotIn("API_TOKEN = 'YOUR TOKEN'", source)
                self.assertNotIn('ADMIN_ID = 000', source)

    def test_admin_and_setlord_commands_are_registered(self):
        for filename in ENTRYPOINTS:
            with self.subTest(filename):
                _, bot = self.load(filename)
                commands = set()
                for kind, kwargs, _ in bot.handlers:
                    if kind == 'message':
                        commands.update(kwargs.get('commands', []))
                self.assertIn('admin', commands)
                self.assertIn('setlord', commands)
                self.assertIn('start', commands)

    def test_menu_covers_the_same_features_in_every_language(self):
        feature_sets = {}
        for filename in ENTRYPOINTS:
            module, _ = self.load(filename)
            feature_sets[filename] = {f for _, _, f in module.MENU_BUTTONS}
        reference = feature_sets['main.py']
        for filename, features in feature_sets.items():
            self.assertEqual(features, reference, f'{filename} menu features differ')

    def test_unregistered_user_is_told_to_ask_an_admin(self):
        for filename in ENTRYPOINTS:
            with self.subTest(filename):
                module, bot = self.load(filename)
                module.send_main_menu(-1, 55)
                self.assertIn('/setlord', bot.last_sent_text())

    def test_trade_admin_ops_are_declared_identically(self):
        ops = {f: set(self.load(f)[0].TRADE_ADMIN_OPS) for f in ENTRYPOINTS}
        for filename, value in ops.items():
            self.assertEqual(value, ops['main.py'], f'{filename} differs')
        self.assertIn('ph', ops['main.py'], 'the photo screen must stay admin-reachable')


class PanelEntryTest(unittest.TestCase):
    """/start opens the menu everywhere, and the bare word "panel" is its alias."""

    # One build per language for the whole class: every extra load leaves a
    # trade ticker running against the same sqlite file.
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.builds = {}
        for filename in ENTRYPOINTS:
            module, bot = load_entrypoint(filename, cls.dir.name)
            # The three builds share one sqlite file, so the lord is inserted once.
            module.cursor.execute("INSERT OR IGNORE INTO users (user_id, group_id) VALUES (?, ?)",
                                  (7, -1))
            module.conn.commit()
            cls.builds[filename] = (module, bot)

    @classmethod
    def tearDownClass(cls):
        for module, _ in cls.builds.values():
            module.conn.close()
        cls.dir.cleanup()

    def load(self, filename):
        module, bot = self.builds[filename]
        for record in (bot.sent, bot.replies, bot.markups):
            record.clear()
        return module, bot

    @staticmethod
    def menu_buttons(bot):
        return [button.callback_data for row in bot.markups[-1].keyboard for button in row]

    def test_start_in_private_opens_the_menu(self):
        for filename in ENTRYPOINTS:
            with self.subTest(filename):
                module, bot = self.load(filename)
                module.start(Message(Chat(7, chat_type='private'), User(7), text='/start'))
                self.assertEqual([chat for chat, _ in bot.sent], [7])
                self.assertIn('assets', self.menu_buttons(bot))
                self.assertEqual(bot.replies, [], 'no "groups only" brush-off any more')

    def test_start_in_a_group_still_shows_the_menu(self):
        for filename in ENTRYPOINTS:
            with self.subTest(filename):
                module, bot = self.load(filename)
                module.start(Message(Chat(-1), User(7), text='/start'))
                self.assertEqual([chat for chat, _ in bot.sent], [-1])
                self.assertIn('assets', self.menu_buttons(bot))

    def test_the_word_panel_does_exactly_what_start_does(self):
        for filename in ENTRYPOINTS:
            with self.subTest(filename):
                module, bot = self.load(filename)
                for word in module.PANEL_WORDS:
                    message = Message(Chat(-1), User(7), text=f'  {word.upper()} ')
                    self.assertTrue(module.is_panel_word(message), word)
                    module.panel_word(message)
                    self.assertIn('assets', self.menu_buttons(bot))
                self.assertEqual(len(bot.sent), len(module.PANEL_WORDS))

    def test_the_word_works_for_an_admin_too(self):
        module, bot = self.load('main.py')
        module.cursor.execute("INSERT OR IGNORE INTO users (user_id, group_id) VALUES (?, ?)",
                              (4242, -1))
        module.conn.commit()
        module.panel_word(Message(Chat(-1), User(4242), text='panel'))
        self.assertIn('ap:home', self.menu_buttons(bot), 'admins still get the panel button')

    def test_ordinary_chatter_is_not_a_panel_word(self):
        for filename in ENTRYPOINTS:
            with self.subTest(filename):
                module, _ = self.load(filename)
                for text in ('panel of judges', '/start', 'panels', '', None):
                    message = Message(Chat(-1), User(7), text=text)
                    self.assertFalse(module.is_panel_word(message), repr(text))


class MenuKeyboardTest(unittest.TestCase):
    """send_main_menu builds its keyboard from the feature toggles."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.dir.cleanup)
        self.module, self.bot = load_entrypoint('main.py', self.dir.name)
        self.addCleanup(self.module.conn.close)
        self.captured = []
        original = self.bot.send_message

        def capture(chat_id, text, **kwargs):
            markup = kwargs.get('reply_markup')
            data = []
            if markup is not None:
                for row in markup.keyboard:
                    data.extend(button.callback_data for button in row)
            self.captured.append(data)
            return original(chat_id, text, **kwargs)

        self.bot.send_message = capture
        self.module.cursor.execute("INSERT INTO users (user_id, group_id) VALUES (?, ?)", (7, -1))
        self.module.cursor.execute("INSERT INTO users (user_id, group_id) VALUES (?, ?)",
                                   (4242, -2))
        self.module.conn.commit()
        for key in self.module.admin_panel.enabled_features():
            self.module.admin_panel._set_feature(key, True)

    def menu_for(self, user_id):
        self.captured.clear()
        self.module.send_main_menu(-1, user_id)
        return self.captured[-1] if self.captured else []

    def test_player_menu_lists_every_enabled_feature(self):
        data = self.menu_for(7)
        self.assertIn('assets', data)
        self.assertIn('trd:menu', data)
        self.assertNotIn('ap:home', data)

    def test_disabled_feature_disappears(self):
        self.module.admin_panel._set_feature('trade', False)
        self.assertNotIn('trd:menu', self.menu_for(7))

    def test_admin_menu_adds_the_panel_and_admin_tools(self):
        data = self.menu_for(4242)
        self.assertIn('ap:home', data)
        self.assertIn('change_assets', data)
        self.assertIn('trd:adm', data)

    def test_disabled_weekly_update_hides_the_button_from_admins(self):
        self.module.admin_panel._set_feature('weekly_update', False)
        data = self.menu_for(4242)
        self.assertNotIn('weekly_update', data)
        self.assertIn('ap:home', data, 'the panel itself is never hidden')


class AddArchersEndToEndTest(unittest.TestCase):
    """The Phase 2 headline: add a unit and its camp from Telegram, no code change."""

    OWNER = 4242
    LORD = 55
    GROUP = -10

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.dir.cleanup)
        self.module, self.bot = load_entrypoint('main.py', self.dir.name)
        self.addCleanup(self.module.conn.close)
        self.bot._chats = {
            self.OWNER: Chat(self.OWNER, 'private', first_name='Owner'),
            self.GROUP: Chat(self.GROUP, title='Persia'),
        }
        self.module.cursor.execute("INSERT INTO users (user_id, group_id) VALUES (?, ?)",
                                   (self.LORD, self.GROUP))
        self.module.conn.commit()

    def tap(self, data, user_id=None):
        user_id = self.OWNER if user_id is None else user_id
        self.module.callback_query(
            Call(data, User(user_id), Message(Chat(self.GROUP), User(user_id))))

    def feed(self, text, user_id=None):
        user_id = self.OWNER if user_id is None else user_id
        self.bot.next_steps[-1][1](Message(Chat(self.GROUP), User(user_id), text=text))

    def value(self, column):
        row = self.module.conn.execute(
            f"SELECT {column} FROM users WHERE group_id=?", (self.GROUP,)).fetchone()
        return row[0]

    def add_archers_and_range(self):
        self.tap('ap:catadd:unit')
        self.feed('archers')
        self.feed('🏹 کماندار'); self.feed('🏹 Archers'); self.feed('🏹 Okçu')
        self.feed('0')
        self.tap('ap:catadd:building')
        self.feed('archery_range')
        self.feed('میدان تیر'); self.feed('🏹 Archery Range'); self.feed('Okçu Alanı')
        self.feed('0')
        self.tap('ap:catprod:archers')
        self.feed('400')
        self.tap('ap:catcosts:archery_range:wood')
        self.feed('300')

    def test_the_new_unit_reaches_the_player_assets_screen(self):
        self.add_archers_and_range()
        self.bot.sent.clear()
        self.tap('assets', user_id=self.LORD)
        text = self.bot.last_sent_text()
        # main.py is the Persian build, so the Persian label is what players see.
        self.assertIn('🏹 کماندار', text)
        self.assertIn('میدان تیر', text)

    def test_the_new_camp_appears_in_the_upgrade_menu(self):
        self.add_archers_and_range()
        self.tap('upgrade', user_id=self.LORD)
        self.assertIn('ag:upc:archery_range', self.bot.last_keyboard())

    def test_the_new_camp_charges_the_cost_the_admin_set(self):
        self.add_archers_and_range()
        self.module.conn.execute("UPDATE users SET wood=500 WHERE group_id=?", (self.GROUP,))
        self.module.conn.commit()
        self.tap('ag:upy:archery_range', user_id=self.LORD)
        self.assertEqual(self.value('archery_range'), 1)
        self.assertEqual(self.value('wood'), 200)

    def test_the_new_camp_trains_the_new_unit_on_the_weekly_update(self):
        self.add_archers_and_range()
        self.module.conn.execute("UPDATE users SET archery_range=2 WHERE group_id=?",
                                 (self.GROUP,))
        self.module.conn.commit()
        self.tap('weekly_update')
        self.assertEqual(self.value('archers'), 800)

    def test_the_new_unit_shows_in_the_admin_military_screen(self):
        self.add_archers_and_range()
        self.tap('ap:mil')
        self.assertIn('🏹 کماندار', self.bot.edits[-1][2])

    def test_a_player_cannot_add_a_type(self):
        self.tap('ap:catadd:unit', user_id=self.LORD)
        self.assertNotIn('archers', self.module.asset_ui.catalog.all_keys())


class WarFlowTest(unittest.TestCase):
    """Public campaign posts carry no troop counts; admins get the full report."""

    COMMANDER = 77
    GROUP = -10

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.dir.cleanup)
        self.module, self.bot = load_entrypoint('main.py', self.dir.name)
        self.addCleanup(self.module.conn.close)
        self.bot._chats = {
            self.COMMANDER: Chat(self.COMMANDER, 'private', first_name='Cyrus'),
            self.GROUP: Chat(self.GROUP, title='Persia'),
        }
        self.module.user_context[self.COMMANDER] = {
            'attack_type': 'land',
            'attack_details': '9000 swordsmen and 12 cannons',
            'attack_origin': 'Persepolis',
            'attack_destination': 'Athens',
        }

    def run_flow(self):
        message = Message(Chat(self.GROUP), User(self.COMMANDER), text='dawn')
        self.module.send_attack_details(message, self.COMMANDER)

    def channel_posts(self):
        return [(chat, text) for chat, text in self.bot.sent if str(chat).startswith('@')]

    def test_public_post_goes_to_the_war_channel(self):
        self.run_flow()
        targets = [chat for chat, _ in self.channel_posts()]
        self.assertIn('@war', targets)
        self.assertNotIn('@news', targets)

    def test_public_post_hides_the_army_details(self):
        self.run_flow()
        public = dict(self.channel_posts())['@war']
        self.assertNotIn('9000 swordsmen', public)
        self.assertIn('Persepolis', public)
        self.assertIn('Athens', public)

    def test_admins_receive_the_full_report(self):
        self.run_flow()
        private = [text for chat, text in self.bot.sent if chat == self.module.ADMIN_ID]
        self.assertEqual(len(private), 1)
        self.assertIn('9000 swordsmen', private[0])

    def test_a_configured_photo_is_used_for_the_public_post(self):
        self.module.admin_panel.set_setting('war_photo_land', 'LANDPIC')
        self.run_flow()
        self.assertEqual(self.bot.photos[-1][0], '@war')
        self.assertEqual(self.bot.photos[-1][1], 'LANDPIC')
        self.assertNotIn('9000 swordsmen', self.bot.photos[-1][2])

    def test_the_sea_photo_is_not_used_for_a_land_campaign(self):
        self.module.admin_panel.set_setting('war_photo_sea', 'SEAPIC')
        self.run_flow()
        self.assertEqual(self.bot.photos, [], 'no land photo is set, so it stays text')

    def test_context_is_cleared_so_two_campaigns_do_not_mix(self):
        self.run_flow()
        self.assertNotIn(self.COMMANDER, self.module.user_context)


if __name__ == '__main__':
    unittest.main()
