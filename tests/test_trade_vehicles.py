# -*- coding: utf-8 -*-
"""Caravans are stock, like ships: owned, escrowed, and brought home again."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asset_catalog as catalog
import trade_system
from stubs import Chat, StubBot, make_db

OWNER = 7
SENDER = -100
RECEIVER = -200


class VehicleTestCase(unittest.TestCase):

    def setUp(self):
        self.conn = make_db()
        self.addCleanup(self.conn.close)
        self.bot = StubBot({SENDER: Chat(SENDER, title='Persia'),
                            RECEIVER: Chat(RECEIVER, title='Rome')})
        trade_system._title_cache.clear()
        trade_system.init(self.bot, self.conn, OWNER, '@news', lang='fa')
        for gid, uid in ((SENDER, 1), (RECEIVER, 2)):
            self.conn.execute("INSERT INTO users (user_id, group_id) VALUES (?, ?)", (uid, gid))
        self.conn.commit()

    def stock(self, column, group_id=SENDER):
        return self.conn.execute(f"SELECT {column} FROM users WHERE group_id=?",
                                 (group_id,)).fetchone()[0]


class CaravanIsAnAssetTest(VehicleTestCase):

    def test_a_caravan_is_a_catalog_unit(self):
        self.assertIn('caravans', catalog.keys('unit'))

    def test_every_country_starts_with_a_stock_of_them(self):
        self.assertEqual(self.stock('caravans'), catalog.UNIT_DEFAULT)

    def test_it_shows_up_in_the_assets_screen_columns(self):
        self.assertIn('caravans', catalog.all_keys())

    def test_the_trade_engine_will_not_let_it_be_deleted(self):
        self.assertIn('caravans', catalog.ENGINE_KEYS)
        with self.assertRaises(catalog.CatalogError):
            catalog.remove('caravans')

    def test_it_can_still_be_taken_out_of_the_game(self):
        catalog.hide('caravans')
        self.assertNotIn('caravans', catalog.all_keys())
        # the column survives, so the trade system keeps working
        self.assertEqual(self.stock('caravans'), catalog.UNIT_DEFAULT)


class EscrowTest(VehicleTestCase):

    def test_despatching_a_caravan_takes_it_out_of_stock(self):
        before = self.stock('caravans')
        ok = trade_system._escrow(SENDER, {'wood': 100}, {'caravans': 4}, fee=0)
        self.assertTrue(ok)
        self.assertEqual(self.stock('caravans'), before - 4)

    def test_a_country_cannot_send_caravans_it_does_not_own(self):
        self.conn.execute("UPDATE users SET caravans=3 WHERE group_id=?", (SENDER,))
        self.conn.commit()
        self.assertFalse(trade_system._escrow(SENDER, {'wood': 1}, {'caravans': 4}, fee=0))
        self.assertEqual(self.stock('caravans'), 3)   # nothing was taken

    def test_a_refund_brings_the_caravans_back(self):
        before = self.stock('caravans')
        trade_system._escrow(SENDER, {'wood': 100}, {'caravans': 4}, fee=50)
        trade_system._refund({'sender_group_id': SENDER, 'fee_paid': 50,
                              'goods': json.dumps({'wood': 100}),
                              'vehicles': json.dumps({'caravans': 4})})
        self.assertEqual(self.stock('caravans'), before)

    def test_a_delivered_convoy_sends_its_caravans_home(self):
        before = self.stock('caravans')
        trade_system._escrow(SENDER, {'wood': 100}, {'caravans': 4}, fee=0)
        trade_system._give(SENDER, {'caravans': 4})
        self.assertEqual(self.stock('caravans'), before)

    def test_ships_still_behave_the_same_way(self):
        before = self.stock('small_ships')
        trade_system._escrow(SENDER, {'wood': 10}, {'small_ships': 2}, fee=0)
        self.assertEqual(self.stock('small_ships'), before - 2)
        trade_system._give(SENDER, {'small_ships': 2})
        self.assertEqual(self.stock('small_ships'), before)


class CapacityTest(VehicleTestCase):

    def test_land_capacity_is_caravans_times_their_capacity(self):
        ctx = {'mode': 'land', 'vehicles': {'caravans': 3}}
        self.assertEqual(trade_system._fleet_capacity(ctx),
                         3 * trade_system.cfg('cap_caravan'))

    def test_sea_capacity_adds_every_ship_class(self):
        ctx = {'mode': 'sea',
               'vehicles': {'small_ships': 1, 'medium_ships': 2, 'large_ships': 3}}
        expected = (trade_system.cfg('cap_small')
                    + 2 * trade_system.cfg('cap_medium')
                    + 3 * trade_system.cfg('cap_large'))
        self.assertEqual(trade_system._fleet_capacity(ctx), expected)

    def test_capacity_follows_the_config(self):
        trade_system.set_cfg('cap_caravan', 999)
        ctx = {'mode': 'land', 'vehicles': {'caravans': 2}}
        self.assertEqual(trade_system._fleet_capacity(ctx), 1998)

    def test_each_vehicle_reports_its_own_capacity(self):
        self.assertEqual(trade_system._veh_capacity('caravans'),
                         trade_system.cfg('cap_caravan'))
        self.assertEqual(trade_system._veh_capacity('large_ships'),
                         trade_system.cfg('cap_large'))

    def test_the_fleet_table_names_capacity_and_stock_for_every_vehicle(self):
        self.conn.execute("UPDATE users SET caravans=17 WHERE group_id=?", (SENDER,))
        self.conn.commit()
        table = trade_system._fleet_table(SENDER, 'land')
        self.assertIn('17', table)
        self.assertIn(str(trade_system.cfg('cap_caravan')), table)

    def test_the_sea_fleet_table_lists_all_three_ship_classes(self):
        table = trade_system._fleet_table(SENDER, 'sea')
        self.assertEqual(len(table.splitlines()), 3)


class InTransitGuardTest(VehicleTestCase):

    def test_caravans_in_flight_are_reported_as_busy(self):
        self.conn.execute(
            "INSERT INTO trades (sender_group_id, sender_user_id, receiver_group_id, "
            "receiver_user_id, mode, goods, vehicles, route, leg_minutes, tolls, fee_paid, "
            "status, offered_at) VALUES (?, 1, ?, 2, 'land', ?, ?, '[]', '[]', '[]', 0, "
            "'active', 0)",
            (SENDER, RECEIVER, json.dumps({'wood': 5}), json.dumps({'caravans': 2})))
        self.conn.commit()
        self.assertIn('caravans', trade_system.active_goods_keys())


class VehicleNameTest(VehicleTestCase):

    def test_a_vehicle_name_comes_from_the_catalog(self):
        catalog.set_labels('caravans', {'fa': '🐫 شترهای من'})
        self.assertEqual(trade_system._veh_name('caravans'), '🐫 شترهای من')

    def test_it_falls_back_when_the_catalog_has_no_label(self):
        self.conn.execute("DELETE FROM asset_labels WHERE key='caravans'")
        self.conn.commit()
        self.assertEqual(trade_system._veh_name('caravans'),
                         trade_system.VEH_NAMES['fa']['caravans'])


if __name__ == '__main__':
    unittest.main()
