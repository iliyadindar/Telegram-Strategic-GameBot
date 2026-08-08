# -*- coding: utf-8 -*-
"""The trade world as data: seeding, editing, and the guards around deletion."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import trade_map
import trade_system
from stubs import StubBot, make_db


class MapTestCase(unittest.TestCase):

    def setUp(self):
        self.conn = make_db()
        self.addCleanup(self.conn.close)
        trade_map.init(self.conn)
        self.addCleanup(trade_map.set_node_guard, None)


class SeedingTest(MapTestCase):
    """The seeded map must be exactly the world the literals describe."""

    def test_every_sea_node_is_present(self):
        self.assertEqual(set(trade_map.nodes('sea')), set(trade_map.SEA_NODES))

    def test_every_land_node_is_present(self):
        self.assertEqual(set(trade_map.nodes('land')), set(trade_map.LAND_NODES))

    def test_node_kinds_and_homes_match_the_literals(self):
        for mode, seed in (('sea', trade_map.SEA_NODES), ('land', trade_map.LAND_NODES)):
            for nid, node in seed.items():
                with self.subTest(nid):
                    stored = trade_map.node(mode, nid)
                    self.assertEqual(stored['kind'], node['kind'])
                    self.assertEqual(stored['home'], node['home'])

    def test_names_match_the_literals_in_every_language(self):
        for mode, seed in (('sea', trade_map.SEA_NODES), ('land', trade_map.LAND_NODES)):
            for nid, node in seed.items():
                for lang, text in node['names'].items():
                    with self.subTest(nid=nid, lang=lang):
                        self.assertEqual(trade_map.name(nid, lang), text)

    def test_node_order_follows_the_literals(self):
        self.assertEqual(list(trade_map.nodes('sea')), list(trade_map.SEA_NODES))
        self.assertEqual(list(trade_map.nodes('land')), list(trade_map.LAND_NODES))

    def test_edges_match_the_literals(self):
        for mode, seed in (('sea', trade_map.SEA_EDGES), ('land', trade_map.LAND_EDGES)):
            with self.subTest(mode):
                stored = {frozenset((a, b)): units for a, b, units, _m in trade_map.edges(mode)}
                declared = {frozenset((a, b)): w for a, b, w in seed}
                self.assertEqual(stored, declared)

    def test_no_edge_starts_with_a_timing_override(self):
        for mode in trade_map.MODES:
            for _a, _b, _units, minutes in trade_map.edges(mode):
                self.assertEqual(minutes, 0)

    def test_chokepoints_are_the_tolled_kinds(self):
        expected = [nid for nid, n in trade_map.SEA_NODES.items()
                    if n['kind'] in ('strait', 'canal')]
        expected += [nid for nid, n in trade_map.LAND_NODES.items() if n['kind'] == 'pass']
        self.assertEqual(trade_map.chokepoints(), expected)

    def test_seeding_twice_changes_nothing(self):
        trade_map.set_labels('sue', {'en': 'The Ditch'})
        trade_map.set_edge('sea', 'sue', 'red', minutes=40)
        trade_map.init(self.conn)
        self.assertEqual(trade_map.name('sue', 'en'), 'The Ditch')
        self.assertEqual(trade_map.leg('sea', 'sue', 'red')[1], 40)
        self.assertEqual(len(trade_map.nodes('sea')), len(trade_map.SEA_NODES))


class GraphEquivalenceTest(MapTestCase):
    """Routing over the seeded map must match routing over the old literals."""

    def literal_adjacency(self, mode):
        seed = trade_map.SEA_EDGES if mode == 'sea' else trade_map.LAND_EDGES
        nodes = trade_map.SEA_NODES if mode == 'sea' else trade_map.LAND_NODES
        adj = {nid: [] for nid in nodes}
        for a, b, w in seed:
            adj[a].append((b, w))
            adj[b].append((a, w))
        return adj

    def test_adjacency_matches_the_literals(self):
        for mode in trade_map.MODES:
            with self.subTest(mode):
                stored = {n: sorted(v) for n, v in trade_map.adjacency(mode).items()}
                literal = {n: sorted(v) for n, v in self.literal_adjacency(mode).items()}
                self.assertEqual(stored, literal)

    def test_shortest_paths_are_unchanged_everywhere(self):
        """Every pair of home nodes routes exactly as it did before the move."""
        for mode in trade_map.MODES:
            stored = trade_map.adjacency(mode)
            literal = self.literal_adjacency(mode)
            homes = trade_map.home_nodes(mode)
            for src in homes:
                for dst in homes:
                    if src == dst:
                        continue
                    with self.subTest(mode=mode, src=src, dst=dst):
                        self.assertEqual(trade_system._dijkstra(stored, src, dst),
                                         trade_system._dijkstra(literal, src, dst))


class NodeEditTest(MapTestCase):

    def test_a_node_can_be_renamed_in_one_language_only(self):
        trade_map.set_labels('sue', {'en': 'The Ditch'})
        self.assertEqual(trade_map.name('sue', 'en'), 'The Ditch')
        self.assertEqual(trade_map.name('sue', 'fa'), trade_map.SEA_NODES['sue']['names']['fa'])

    def test_a_node_can_be_made_a_home(self):
        trade_map.set_home('sue', True)
        self.assertIn('sue', trade_map.home_nodes('sea'))

    def test_a_node_can_stop_being_a_home(self):
        trade_map.set_home('med', False)
        self.assertNotIn('med', trade_map.home_nodes('sea'))

    def test_changing_kind_changes_whether_it_is_a_chokepoint(self):
        trade_map.set_kind('med', 'strait')
        self.assertIn('med', trade_map.chokepoints())

    def test_a_kind_from_the_other_mode_is_refused(self):
        with self.assertRaises(trade_map.MapError):
            trade_map.set_kind('med', 'region')

    def test_a_new_node_can_be_added_and_linked(self):
        trade_map.add_node('sea', 'azo', 'sea', True, {'en': 'Sea of Azov', 'fa': 'آزوف'})
        trade_map.add_edge('sea', 'bla', 'azo', 2)
        self.assertIn('azo', trade_map.nodes('sea'))
        self.assertIn(('azo', 2), trade_map.adjacency('sea')['bla'])

    def test_a_new_node_is_reachable_by_routing(self):
        trade_map.add_node('sea', 'azo', 'sea', True, {'en': 'Sea of Azov'})
        trade_map.add_edge('sea', 'bla', 'azo', 2)
        found = trade_system._dijkstra(trade_map.adjacency('sea'), 'med', 'azo')
        self.assertIsNotNone(found)
        self.assertEqual(found[1][-1], 'azo')

    def test_a_duplicate_id_is_refused(self):
        with self.assertRaises(trade_map.MapError):
            trade_map.add_node('sea', 'med', 'sea', True, {'en': 'Again'})

    def test_sql_injection_shaped_ids_are_refused(self):
        for bad in ('med; DROP TABLE trade_nodes', 'MED', '1med', 'a', '', 'me d', "m'ed"):
            with self.subTest(bad):
                with self.assertRaises(trade_map.MapError):
                    trade_map.add_node('sea', bad, 'sea', True, {'en': 'Nope'})

    def test_a_bad_kind_is_refused(self):
        with self.assertRaises(trade_map.MapError):
            trade_map.add_node('sea', 'azo', 'region', True, {'en': 'Nope'})

    def test_a_bad_mode_is_refused(self):
        with self.assertRaises(trade_map.MapError):
            trade_map.add_node('air', 'azo', 'sea', True, {'en': 'Nope'})


class EdgeEditTest(MapTestCase):

    def test_units_can_be_retuned(self):
        trade_map.set_edge('sea', 'sue', 'red', units=9)
        self.assertEqual(trade_map.leg('sea', 'sue', 'red')[0], 9)

    def test_minutes_override_can_be_set_and_cleared(self):
        trade_map.set_edge('sea', 'sue', 'red', minutes=40)
        self.assertEqual(trade_map.leg_minutes('sea', 'sue', 'red', per_unit=30), 40)
        trade_map.set_edge('sea', 'sue', 'red', minutes=0)
        self.assertEqual(trade_map.leg_minutes('sea', 'sue', 'red', per_unit=30), 30)

    def test_timing_falls_back_to_length_times_the_rate(self):
        units = trade_map.leg('sea', 'med', 'sue')[0]
        self.assertEqual(trade_map.leg_minutes('sea', 'med', 'sue', per_unit=30), units * 30)

    def test_edges_are_undirected_however_they_are_named(self):
        trade_map.set_edge('sea', 'red', 'sue', minutes=40)
        self.assertEqual(trade_map.leg('sea', 'sue', 'red')[1], 40)

    def test_an_edge_can_be_added_between_existing_nodes(self):
        trade_map.add_edge('sea', 'med', 'bla', 7)
        self.assertIn(('bla', 7), trade_map.adjacency('sea')['med'])

    def test_a_duplicate_edge_is_refused(self):
        with self.assertRaises(trade_map.MapError):
            trade_map.add_edge('sea', 'sue', 'red', 3)

    def test_an_edge_across_two_modes_is_refused(self):
        with self.assertRaises(trade_map.MapError):
            trade_map.add_edge('sea', 'med', 'prs', 3)

    def test_an_edge_to_itself_is_refused(self):
        with self.assertRaises(trade_map.MapError):
            trade_map.add_edge('sea', 'med', 'med', 3)

    def test_zero_length_is_refused(self):
        with self.assertRaises(trade_map.MapError):
            trade_map.add_edge('sea', 'med', 'bla', 0)

    def test_removing_an_edge_cuts_the_connection(self):
        trade_map.remove_edge('sea', 'sue', 'red')
        self.assertIsNone(trade_map.leg('sea', 'sue', 'red'))
        self.assertNotIn('red', [n for n, _ in trade_map.adjacency('sea')['sue']])

    def test_removing_an_edge_reroutes_traffic(self):
        before = trade_system._dijkstra(trade_map.adjacency('sea'), 'med', 'ind')
        trade_map.remove_edge('sea', 'med', 'sue')
        after = trade_system._dijkstra(trade_map.adjacency('sea'), 'med', 'ind')
        self.assertNotEqual(before[1], after[1], 'closing Suez should change the route')

    def test_retuning_an_unknown_edge_is_refused(self):
        with self.assertRaises(trade_map.MapError):
            trade_map.set_edge('sea', 'med', 'jap', units=1)


class NodeRemovalTest(MapTestCase):

    def test_removing_a_node_takes_its_edges(self):
        trade_map.remove_node('sue')
        self.assertNotIn('sue', trade_map.nodes('sea'))
        self.assertIsNone(trade_map.leg('sea', 'med', 'sue'))
        self.assertNotIn('sue', [n for n, _ in trade_map.adjacency('sea')['med']])

    def test_removing_a_node_takes_its_names(self):
        trade_map.remove_node('sue')
        self.assertEqual(trade_map.labels('sue'), {})

    def test_a_removed_node_does_not_come_back_on_restart(self):
        trade_map.remove_node('sue')
        trade_map.init(self.conn)
        self.assertNotIn('sue', trade_map.nodes('sea'))
        self.assertIsNone(trade_map.leg('sea', 'med', 'sue'))

    def test_a_removed_edge_does_not_come_back_on_restart(self):
        trade_map.remove_edge('sea', 'med', 'sue')
        trade_map.init(self.conn)
        self.assertIsNone(trade_map.leg('sea', 'med', 'sue'))

    def test_a_node_added_back_after_removal_stays(self):
        trade_map.remove_node('sue')
        trade_map.add_node('sea', 'sue', 'canal', False, {'en': 'Suez Canal'})
        trade_map.init(self.conn)
        self.assertIn('sue', trade_map.nodes('sea'))

    def test_a_node_a_convoy_needs_cannot_be_removed(self):
        trade_map.set_node_guard(lambda: {'sue'})
        with self.assertRaises(trade_map.MapError):
            trade_map.remove_node('sue')
        self.assertIn('sue', trade_map.nodes('sea'))

    def test_a_node_no_convoy_needs_can_be_removed(self):
        trade_map.set_node_guard(lambda: {'pan'})
        trade_map.remove_node('sue')
        self.assertNotIn('sue', trade_map.nodes('sea'))

    def test_a_guard_that_cannot_answer_blocks_removal(self):
        def broken():
            raise RuntimeError('trades table is locked')
        trade_map.set_node_guard(broken)
        with self.assertRaises(trade_map.MapError):
            trade_map.remove_node('sue')
        self.assertIn('sue', trade_map.nodes('sea'))

    def test_removing_an_unknown_node_is_refused(self):
        with self.assertRaises(trade_map.MapError):
            trade_map.remove_node('atlantis')

    def test_removal_works_without_the_trade_system_tables(self):
        # The map is usable on its own; the cascade must not need those tables.
        trade_map.remove_node('sue')
        self.assertNotIn('sue', trade_map.nodes('sea'))


class RemovalCascadeTest(unittest.TestCase):
    """A deleted node must leave no dangling reference behind."""

    def setUp(self):
        self.conn = make_db()
        self.addCleanup(self.conn.close)
        trade_system.init(StubBot(), self.conn, 1, '@news', lang='en')
        self.conn.execute("INSERT INTO users (user_id, group_id, home_sea, home_land) "
                          "VALUES (1, -1, 'sue', 'sin')")
        self.conn.commit()

    def test_a_country_based_there_loses_its_home(self):
        trade_map.remove_node('sue')
        row = self.conn.execute("SELECT home_sea FROM users WHERE group_id=-1").fetchone()
        self.assertEqual(row[0], '')

    def test_the_other_home_is_left_alone(self):
        trade_map.remove_node('sue')
        row = self.conn.execute("SELECT home_land FROM users WHERE group_id=-1").fetchone()
        self.assertEqual(row[0], 'sin')

    def test_its_owner_row_goes(self):
        trade_system._set_owner('sue', -1)
        trade_map.remove_node('sue')
        self.assertIsNone(trade_system._owner_of('sue'))

    def test_its_toll_goes(self):
        trade_system.set_cfg('toll_sue', 900)
        trade_map.remove_node('sue')
        self.assertEqual(trade_system._toll('sue'), 0)

    def test_a_rebuilt_node_does_not_inherit_the_old_toll(self):
        trade_system.set_cfg('toll_sue', 900)
        trade_map.remove_node('sue')
        trade_map.add_node('sea', 'sue', 'canal', False, {'en': 'Suez Canal'})
        self.assertEqual(trade_system._toll('sue'), 0)


class LiveTradeGuardTest(unittest.TestCase):
    """The guards read from real trades rather than a hand-written set."""

    def setUp(self):
        self.conn = make_db()
        self.addCleanup(self.conn.close)
        trade_system.init(StubBot(), self.conn, 1, '@news', lang='en')

    def insert_trade(self, status, route, goods):
        self.conn.execute(
            "INSERT INTO trades (sender_group_id, sender_user_id, receiver_group_id, "
            "receiver_user_id, mode, goods, vehicles, route, leg_minutes, status) "
            "VALUES (1, 1, 2, 2, 'sea', ?, '{}', ?, '[]', ?)",
            (goods, route, status))
        self.conn.commit()

    def test_a_live_trade_protects_its_goods(self):
        self.insert_trade('active', '["med","sue"]', '{"gold": 50}')
        self.assertIn('gold', trade_system.active_goods_keys())

    def test_a_live_trade_protects_its_route(self):
        self.insert_trade('active', '["med","sue"]', '{"gold": 50}')
        self.assertEqual(trade_system.active_route_nodes(), {'med', 'sue'})

    def test_an_offered_trade_still_counts(self):
        self.insert_trade('offered', '["med","sue"]', '{"gold": 50}')
        self.assertIn('gold', trade_system.active_goods_keys())

    def test_a_delivered_trade_no_longer_counts(self):
        self.insert_trade('delivered', '["med","sue"]', '{"gold": 50}')
        self.assertNotIn('gold', trade_system.active_goods_keys())
        self.assertEqual(trade_system.active_route_nodes(), set())

    def test_a_cancelled_trade_no_longer_counts(self):
        self.insert_trade('cancelled', '["med","sue"]', '{"gold": 50}')
        self.assertEqual(trade_system.active_route_nodes(), set())

    def test_the_escrowed_fee_always_protects_money(self):
        self.insert_trade('active', '["med","sue"]', '{"gold": 50}')
        self.assertIn('money', trade_system.active_goods_keys())

    def test_the_map_refuses_a_node_a_real_convoy_is_using(self):
        self.insert_trade('active', '["med","sue"]', '{"gold": 50}')
        with self.assertRaises(trade_map.MapError):
            trade_map.remove_node('sue')


if __name__ == '__main__':
    unittest.main()
