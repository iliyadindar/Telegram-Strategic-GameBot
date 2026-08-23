# -*- coding: utf-8 -*-
"""A separate photo per trade kind, and closing one route for one country."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import trade_map
import trade_system
from stubs import Call, Chat, Message, StubBot, User, make_db

ADMIN = 7
PLAYER = 1
PERSIA = -100
ROME = -200


class TradeScreenTest(unittest.TestCase):

    def setUp(self):
        self.conn = make_db()
        self.addCleanup(self.conn.close)
        self.bot = StubBot({PERSIA: Chat(PERSIA, title='Persia'),
                            ROME: Chat(ROME, title='Rome')})
        trade_system._title_cache.clear()
        trade_system._ctx.clear()
        trade_system.init(self.bot, self.conn, ADMIN, '@news', lang='en')
        sea = list(trade_map.home_nodes('sea'))[0]
        land = list(trade_map.home_nodes('land'))[0]
        for gid, uid in ((PERSIA, PLAYER), (ROME, 2)):
            self.conn.execute(
                "INSERT INTO users (user_id, group_id, home_sea, home_land) VALUES (?,?,?,?)",
                (uid, gid, sea, land))
        self.conn.commit()

    def tap(self, data, user_id=ADMIN, chat=PERSIA):
        trade_system.handle_callback(
            Call(data, User(user_id), Message(Chat(chat), User(user_id))))

    def text(self):
        return self.bot.sent[-1][1] if self.bot.sent else ''


# ---------------------------------------------------------------------------
# Item 9 — a sea trade and a land trade get their own photo
# ---------------------------------------------------------------------------


class PhotoPerModeTest(TradeScreenTest):

    def test_each_mode_starts_with_no_photo(self):
        self.assertEqual(trade_system.photo('sea'), '')
        self.assertEqual(trade_system.photo('land'), '')

    def test_a_mode_photo_is_kept_apart_from_the_other(self):
        trade_system.set_photo('SEA_ID', 'sea')
        self.assertEqual(trade_system.photo('sea'), 'SEA_ID')
        self.assertEqual(trade_system.photo('land'), '')

    def test_a_mode_without_its_own_falls_back_to_the_shared_photo(self):
        trade_system.set_photo('SHARED')
        self.assertEqual(trade_system.photo('sea'), 'SHARED')
        self.assertEqual(trade_system.photo('land'), 'SHARED')

    def test_a_mode_photo_wins_over_the_shared_one(self):
        trade_system.set_photo('SHARED')
        trade_system.set_photo('LAND_ID', 'land')
        self.assertEqual(trade_system.photo('land'), 'LAND_ID')
        self.assertEqual(trade_system.photo('sea'), 'SHARED')

    def test_own_photo_ignores_the_fallback(self):
        trade_system.set_photo('SHARED')
        self.assertEqual(trade_system.own_photo('sea'), '')

    def test_clearing_a_mode_photo_returns_it_to_the_shared_one(self):
        trade_system.set_photo('SHARED')
        trade_system.set_photo('SEA_ID', 'sea')
        trade_system.set_photo('', 'sea')
        self.assertEqual(trade_system.photo('sea'), 'SHARED')

    def test_the_menu_offers_one_entry_per_mode_plus_the_shared_one(self):
        self.tap('trd:ph')
        self.assertEqual(self.bot.last_keyboard(),
                         ['trd:phm:sea', 'trd:phm:land', 'trd:phm:both'])

    def test_a_mode_screen_offers_set_but_not_clear_while_empty(self):
        self.tap('trd:phm:sea')
        self.assertIn('trd:phs:sea', self.bot.last_keyboard())
        self.assertNotIn('trd:phc:sea', self.bot.last_keyboard())

    def test_a_mode_screen_offers_clear_once_it_has_one(self):
        trade_system.set_photo('SEA_ID', 'sea')
        self.tap('trd:phm:sea')
        self.assertIn('trd:phc:sea', self.bot.last_keyboard())

    def test_uploading_stores_it_against_that_mode(self):
        self.tap('trd:phs:land')
        handler = self.bot.next_steps[-1][1]
        message = Message(Chat(PERSIA), User(ADMIN))
        message.photo = [type('P', (), {'file_id': 'LAND_ID'})()]
        handler(message)
        self.assertEqual(trade_system.own_photo('land'), 'LAND_ID')
        self.assertEqual(trade_system.own_photo('sea'), '')

    def test_a_sea_announcement_uses_the_sea_photo(self):
        trade_system.set_photo('SEA_ID', 'sea')
        trade_system.set_photo('LAND_ID', 'land')
        trade_system._send_rich(PERSIA, 'off we go', mode='sea')
        self.assertEqual(self.bot.photos[-1][1], 'SEA_ID')

    def test_a_land_announcement_uses_the_land_photo(self):
        trade_system.set_photo('SEA_ID', 'sea')
        trade_system.set_photo('LAND_ID', 'land')
        trade_system._send_rich(PERSIA, 'off we go', mode='land')
        self.assertEqual(self.bot.photos[-1][1], 'LAND_ID')

    def test_the_screens_are_admin_only(self):
        self.tap('trd:phm:sea', user_id=PLAYER)
        self.assertTrue(self.bot.last_answer()[2])


# ---------------------------------------------------------------------------
# Item 10 — closing one route for one country
# ---------------------------------------------------------------------------


class TradeClosureTest(TradeScreenTest):

    def test_both_routes_start_open(self):
        self.assertEqual(trade_system.open_modes(PERSIA), {'sea': True, 'land': True})

    def test_closing_one_route_leaves_the_other_alone(self):
        trade_system.set_mode_open(PERSIA, 'sea', False)
        self.assertFalse(trade_system.mode_open(PERSIA, 'sea'))
        self.assertTrue(trade_system.mode_open(PERSIA, 'land'))

    def test_closing_one_country_leaves_the_others_alone(self):
        trade_system.set_mode_open(PERSIA, 'sea', False)
        self.assertTrue(trade_system.mode_open(ROME, 'sea'))

    def test_the_toggle_flips_and_logs(self):
        seen = []
        trade_system._audit = lambda *a: seen.append(a)
        self.addCleanup(setattr, trade_system, '_audit', None)
        self.tap(f'trd:tmt:{ROME}:sea')
        self.assertFalse(trade_system.mode_open(ROME, 'sea'))
        self.assertEqual(seen[-1][1], 'trade_mode')
        self.tap(f'trd:tmt:{ROME}:sea')
        self.assertTrue(trade_system.mode_open(ROME, 'sea'))

    def test_a_closed_route_is_not_offered_in_the_menu(self):
        trade_system.set_mode_open(PERSIA, 'sea', False)
        self.tap('trd:menu', user_id=PLAYER)
        self.assertEqual(self.bot.last_keyboard(), ['trd:m:land'])

    def test_closing_both_leaves_no_menu_at_all(self):
        trade_system.set_mode_open(PERSIA, 'sea', False)
        trade_system.set_mode_open(PERSIA, 'land', False)
        self.tap('trd:menu', user_id=PLAYER)
        self.assertIn('closed', self.text())

    def test_picking_a_closed_route_directly_is_refused(self):
        trade_system.set_mode_open(PERSIA, 'sea', False)
        self.tap('trd:m:sea', user_id=PLAYER)
        self.assertIn('closed for your country', self.text())
        self.assertNotIn(PLAYER, trade_system._ctx)

    def test_a_country_with_that_route_closed_is_not_a_destination(self):
        trade_system.set_mode_open(ROME, 'sea', False)
        self.tap('trd:m:sea', user_id=PLAYER)
        # Rome was the only other country, so there is nowhere to sail
        self.assertNotIn(f'trd:d:{ROME}', self.bot.last_keyboard())

    def test_it_is_still_a_destination_by_land(self):
        trade_system.set_mode_open(ROME, 'sea', False)
        self.tap('trd:m:land', user_id=PLAYER)
        self.assertIn(f'trd:d:{ROME}', self.bot.last_keyboard())

    def test_a_route_closed_mid_wizard_stops_the_despatch(self):
        self.tap('trd:m:land', user_id=PLAYER)
        ctx = trade_system._ctx[PLAYER]
        ctx.update({'dest': ROME, 'goods': {'wood': 10}, 'vehicles': {'caravans': 1},
                    'route_i': 0,
                    'routes': [{'money': 0, 'path': [ctx['chat_id']], 'leg_minutes': [1],
                                'tolls': [], 'base_fee': 0, 'minutes': 1}]})
        trade_system.set_mode_open(ROME, 'land', False)
        self.tap('trd:go', user_id=PLAYER)
        self.assertIn('closed for Rome', self.text())
        # nothing was escrowed
        wood = self.conn.execute("SELECT wood FROM users WHERE group_id=?",
                                 (PERSIA,)).fetchone()[0]
        self.assertEqual(wood, 2000)

    def test_the_admin_list_shows_each_country_and_its_two_routes(self):
        self.tap('trd:tm:0')
        labels = self.bot.last_button_labels()
        self.assertTrue(any('Persia' in label for label in labels), labels)
        self.assertTrue(any('Rome' in label for label in labels), labels)

    def test_the_screens_are_admin_only(self):
        self.tap('trd:tm:0', user_id=PLAYER)
        self.assertTrue(self.bot.last_answer()[2])
        self.tap(f'trd:tmt:{ROME}:sea', user_id=PLAYER)
        self.assertTrue(trade_system.mode_open(ROME, 'sea'))


if __name__ == '__main__':
    unittest.main()
