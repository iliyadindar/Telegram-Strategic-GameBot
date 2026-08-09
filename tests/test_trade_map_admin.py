# -*- coding: utf-8 -*-
"""The panel screens that edit the trade world."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import trade_map
import trade_map_admin
import trade_system
from stubs import Call, Chat, Message, StubBot, User, add_group, make_db

OWNER = 100
HELPER = 200
PLAYER = 300
GROUP = -1001

ADMINS = {OWNER, HELPER}


class MapScreenTest(unittest.TestCase):

    def setUp(self):
        self.conn = make_db()
        self.addCleanup(self.conn.close)
        self.bot = StubBot(chats={GROUP: Chat(GROUP, title='Persia')})
        self.logged = []
        trade_system.init(self.bot, self.conn, OWNER, '@news', lang='en',
                          is_admin=lambda uid: uid in ADMINS,
                          is_owner=lambda uid: uid == OWNER,
                          audit=lambda *a: self.logged.append(a))
        self.addCleanup(trade_map.set_node_guard, None)
        trade_map_admin._wizards.clear()

    def tap(self, data, user_id=OWNER):
        trade_system.handle_callback(
            Call(data, User(user_id), Message(Chat(GROUP), User(user_id))))

    def feed(self, text, user_id=OWNER):
        handler = self.bot.next_steps[-1][1]
        handler(Message(Chat(GROUP), User(user_id), text=text))

    def screen(self):
        return self.bot.last_sent_text()


class BrowsingTest(MapScreenTest):

    def test_the_editor_offers_both_maps(self):
        self.tap('trd:map')
        self.assertEqual(self.bot.last_keyboard(), ['trd:mn:sea:0', 'trd:mn:land:0'])

    def test_the_admin_menu_links_to_the_editor(self):
        self.tap('trd:adm')
        self.assertIn('trd:map', self.bot.last_keyboard())

    def test_the_node_list_links_to_each_node(self):
        self.tap('trd:mn:sea:0')
        first = list(trade_map.nodes('sea'))[0]
        self.assertIn(f'trd:mnd:{first}', self.bot.last_keyboard())

    def test_the_node_list_paginates(self):
        self.tap('trd:mn:sea:0')
        self.assertIn('trd:mn:sea:1', self.bot.last_keyboard())

    def test_the_node_screen_shows_the_facts(self):
        self.tap('trd:mnd:sue')
        text = self.screen()
        self.assertIn('sue', text)
        self.assertIn('Suez Canal', text)
        self.assertIn('Canal', text)

    def test_the_node_screen_names_its_neighbours(self):
        self.tap('trd:mnd:sue')
        self.assertIn('Red Sea', self.screen())

    def test_the_node_screen_shows_the_toll(self):
        trade_system.set_cfg('toll_sue', 777)
        self.tap('trd:mnd:sue')
        self.assertIn('777', self.screen())

    def test_the_node_screen_shows_the_owner(self):
        add_group(self.conn, PLAYER, GROUP)
        trade_system._set_owner('sue', GROUP)
        self.tap('trd:mnd:sue')
        self.assertIn('Persia', self.screen())

    def test_the_edge_list_links_to_each_edge(self):
        self.tap('trd:me:sea:0')
        self.assertTrue(any(k.startswith('trd:med:sea:') for k in self.bot.last_keyboard()))

    def test_the_edge_screen_explains_automatic_timing(self):
        self.tap('trd:med:sea:red:sue')
        self.assertIn('automatic', self.screen())

    def test_an_unknown_node_is_refused(self):
        self.tap('trd:mnd:atlantis')
        self.assertTrue(self.bot.last_answer()[2])

    def test_a_stranger_sees_nothing(self):
        self.tap('trd:mn:sea:0', user_id=PLAYER)
        self.assertEqual(self.bot.sent, [])


class NodeEditScreenTest(MapScreenTest):

    def test_a_node_can_be_renamed_through_the_wizard(self):
        self.tap('trd:mrn:sue')
        for lang in trade_map.LANGS:
            self.feed(f'Ditch-{lang}')
        self.assertEqual(trade_map.name('sue', 'en'), 'Ditch-en')
        self.assertEqual(trade_map.name('sue', 'fa'), 'Ditch-fa')

    def test_renaming_is_logged(self):
        self.tap('trd:mrn:sue')
        for _lang in trade_map.LANGS:
            self.feed('Ditch')
        self.assertIn('map_node_edit', [entry[1] for entry in self.logged])

    def test_a_blank_reply_keeps_the_name_the_node_already_has(self):
        self.tap('trd:mrn:sue')
        for _lang in trade_map.LANGS:
            self.feed('   ')
        self.assertEqual(trade_map.name('sue', 'en'), 'Suez Canal')
        self.assertEqual(trade_map.name('sue', 'fa'), trade_map.SEA_NODES['sue']['names']['fa'])

    def test_one_language_can_be_renamed_while_the_others_are_skipped(self):
        self.tap('trd:mrn:sue')
        self.feed('')            # fa — keep
        self.feed('The Ditch')   # en
        self.feed('')            # tr — keep
        self.assertEqual(trade_map.name('sue', 'en'), 'The Ditch')
        self.assertEqual(trade_map.name('sue', 'tr'), trade_map.SEA_NODES['sue']['names']['tr'])

    def test_the_rename_prompt_shows_the_current_name(self):
        self.tap('trd:mrn:sue')
        self.feed('')
        self.assertIn('Suez Canal', self.screen())

    def test_the_new_name_reaches_the_route_text(self):
        self.tap('trd:mrn:sue')
        for _lang in trade_map.LANGS:
            self.feed('The Ditch')
        self.assertIn('The Ditch', trade_system._path_names('sea', ['med', 'sue']))

    def test_kind_can_be_changed(self):
        self.tap('trd:mks:med:strait')
        self.assertEqual(trade_map.node('sea', 'med')['kind'], 'strait')
        self.assertIn('med', trade_map.chokepoints())

    def test_a_kind_from_the_other_map_is_refused(self):
        self.tap('trd:mks:med:region')
        self.assertEqual(trade_map.node('sea', 'med')['kind'], 'sea')

    def test_home_can_be_toggled_off_and_on(self):
        self.tap('trd:mhm:med')
        self.assertFalse(trade_map.node('sea', 'med')['home'])
        self.tap('trd:mhm:med')
        self.assertTrue(trade_map.node('sea', 'med')['home'])

    def test_a_toll_can_be_set(self):
        self.tap('trd:mtl:sue')
        self.feed('450')
        self.assertEqual(trade_system.cfg('toll_sue'), 450)

    def test_a_toll_can_be_set_on_a_node_that_never_had_one(self):
        trade_map.add_node('sea', 'azo', 'strait', False, {'en': 'Azov Strait'})
        self.tap('trd:mtl:azo')
        self.feed('120')
        self.assertEqual(trade_system._toll('azo'), 120)

    def test_a_bad_toll_is_re_asked(self):
        self.tap('trd:mtl:sue')
        before = trade_system.cfg('toll_sue')
        self.feed('lots')
        self.assertEqual(trade_system.cfg('toll_sue'), before)
        self.feed('60')
        self.assertEqual(trade_system.cfg('toll_sue'), 60)

    def test_editing_is_open_to_any_admin(self):
        self.tap('trd:mhm:med', user_id=HELPER)
        self.assertFalse(trade_map.node('sea', 'med')['home'])


class EdgeEditScreenTest(MapScreenTest):

    def test_length_can_be_changed(self):
        self.tap('trd:meu:sea:red:sue')
        self.feed('9')
        self.assertEqual(trade_map.leg('sea', 'sue', 'red')[0], 9)

    def test_minutes_can_be_set_and_shown(self):
        self.tap('trd:mem:sea:red:sue')
        self.feed('40')
        self.assertEqual(trade_map.leg('sea', 'sue', 'red')[1], 40)
        self.tap('trd:med:sea:red:sue')
        self.assertIn('40 minutes', self.screen())

    def test_zero_minutes_returns_the_leg_to_automatic(self):
        trade_map.set_edge('sea', 'red', 'sue', minutes=40)
        self.tap('trd:mem:sea:red:sue')
        self.feed('0')
        self.assertEqual(trade_map.leg('sea', 'sue', 'red')[1], 0)

    def test_a_zero_length_is_re_asked(self):
        self.tap('trd:meu:sea:red:sue')
        before = trade_map.leg('sea', 'red', 'sue')[0]
        self.feed('0')
        self.assertEqual(trade_map.leg('sea', 'red', 'sue')[0], before)
        self.feed('4')
        self.assertEqual(trade_map.leg('sea', 'red', 'sue')[0], 4)

    def test_an_unknown_edge_is_refused(self):
        self.tap('trd:med:sea:med:jap')
        self.assertTrue(self.bot.last_answer()[2])


class AddNodeTest(MapScreenTest):

    def add_azov(self, user_id=OWNER):
        self.tap('trd:man:sea', user_id=user_id)
        self.feed('azo', user_id=user_id)
        for lang in trade_map.LANGS:
            self.feed(f'Azov-{lang}', user_id=user_id)
        self.tap('trd:mank:sea', user_id=user_id)
        self.tap('trd:manh:1', user_id=user_id)

    def test_a_node_can_be_added_end_to_end(self):
        self.add_azov()
        self.assertIn('azo', trade_map.nodes('sea'))
        self.assertEqual(trade_map.name('azo', 'en'), 'Azov-en')
        self.assertTrue(trade_map.node('sea', 'azo')['home'])

    def test_a_node_added_as_not_home_stays_that_way(self):
        self.tap('trd:man:sea')
        self.feed('azo')
        for _lang in trade_map.LANGS:
            self.feed('Azov')
        self.tap('trd:mank:sea')
        self.tap('trd:manh:0')
        self.assertFalse(trade_map.node('sea', 'azo')['home'])

    def test_a_duplicate_id_is_re_asked(self):
        self.tap('trd:man:sea')
        self.feed('med')
        self.assertIn('already exists', self.screen())
        self.feed('azo')
        self.assertIn('display name', self.screen())

    def test_a_malformed_id_is_re_asked(self):
        self.tap('trd:man:sea')
        self.feed('Azov Sea!')
        self.assertIn('Invalid id', self.screen())

    def test_a_blank_name_is_re_asked_when_there_is_none_to_keep(self):
        self.tap('trd:man:sea')
        self.feed('azo')
        self.feed('   ')
        self.assertIn('cannot be empty', self.screen())
        for lang in trade_map.LANGS:
            self.feed(f'Azov-{lang}')
        self.tap('trd:mank:sea')
        self.tap('trd:manh:1')
        self.assertEqual(trade_map.name('azo', 'fa'), 'Azov-fa')

    def test_adding_is_logged(self):
        self.add_azov()
        self.assertIn('map_node_add', [entry[1] for entry in self.logged])


class AddEdgeTest(MapScreenTest):

    def test_an_edge_can_be_added_end_to_end(self):
        self.tap('trd:mae:sea')
        self.tap('trd:mae1:sea:med')
        self.tap('trd:mae2:sea:med:bla')
        self.feed('7')
        self.assertEqual(trade_map.leg('sea', 'med', 'bla')[0], 7)

    def test_the_second_picker_excludes_the_first_node(self):
        self.tap('trd:mae1:sea:med')
        self.assertNotIn('trd:mae2:sea:med:med', self.bot.last_keyboard())

    def test_the_first_picker_pages_instead_of_one_huge_keyboard(self):
        self.tap('trd:mae:sea')
        keyboard = self.bot.last_keyboard()
        self.assertIn('trd:maep:sea:1', keyboard)
        self.assertLessEqual(len(keyboard), trade_map_admin.PAGE_SIZE + 2)

    def test_a_later_page_of_the_first_picker_offers_later_nodes(self):
        nids = list(trade_map.nodes('sea'))
        self.tap('trd:maep:sea:1')
        self.assertIn(f'trd:mae1:sea:{nids[trade_map_admin.PAGE_SIZE]}', self.bot.last_keyboard())
        self.assertNotIn(f'trd:mae1:sea:{nids[0]}', self.bot.last_keyboard())

    def test_the_second_picker_pages_too(self):
        self.tap('trd:mae1:sea:med')
        self.assertIn('trd:mae1p:sea:med:1', self.bot.last_keyboard())
        self.tap('trd:mae1p:sea:med:1')
        self.assertTrue(any(d.startswith('trd:mae2:sea:med:') for d in self.bot.last_keyboard()))

    def test_a_node_reached_through_a_later_page_still_makes_an_edge(self):
        nids = [nid for nid in trade_map.nodes('sea') if nid != 'med']
        far = nids[trade_map_admin.PAGE_SIZE + 1]
        self.tap('trd:mae1p:sea:med:1')
        self.tap(f'trd:mae2:sea:med:{far}')
        self.feed('4')
        self.assertEqual(trade_map.leg('sea', 'med', far)[0], 4)

    def test_a_duplicate_edge_is_reported(self):
        self.tap('trd:mae2:sea:red:sue')
        self.feed('3')
        self.assertIn('already connected', self.screen())

    def test_a_new_edge_changes_routing(self):
        before = trade_system._dijkstra(trade_map.adjacency('sea'), 'med', 'bla')
        self.tap('trd:mae2:sea:med:bla')
        self.feed('1')
        after = trade_system._dijkstra(trade_map.adjacency('sea'), 'med', 'bla')
        self.assertLess(after[0], before[0])


class DeletionTest(MapScreenTest):

    def test_deleting_a_node_needs_the_owner(self):
        self.tap('trd:mdnc:sue', user_id=HELPER)
        self.assertIn('sue', trade_map.nodes('sea'))

    def test_the_confirmation_needs_the_owner_too(self):
        self.tap('trd:mdn:sue', user_id=HELPER)
        self.assertNotIn('trd:mdnc:sue', self.bot.last_keyboard())

    def test_the_confirmation_counts_the_routes_at_risk(self):
        self.tap('trd:mdn:sue')
        self.assertIn('2 routes', self.screen())
        self.assertIn('trd:mdnc:sue', self.bot.last_keyboard())

    def test_the_owner_can_delete_a_node(self):
        self.tap('trd:mdnc:sue')
        self.assertNotIn('sue', trade_map.nodes('sea'))
        self.assertIsNone(trade_map.leg('sea', 'med', 'sue'))

    def test_a_node_a_convoy_needs_is_refused_with_an_alert(self):
        trade_map.set_node_guard(lambda: {'sue'})
        self.tap('trd:mdnc:sue')
        _id, text, alert = self.bot.last_answer()
        self.assertTrue(alert)
        self.assertIn('shipment is passing', text)
        self.assertIn('sue', trade_map.nodes('sea'))

    def test_deleting_an_edge_needs_the_owner(self):
        self.tap('trd:mdec:sea:red:sue', user_id=HELPER)
        self.assertIsNotNone(trade_map.leg('sea', 'red', 'sue'))

    def test_the_owner_can_delete_an_edge(self):
        self.tap('trd:mdec:sea:red:sue')
        self.assertIsNone(trade_map.leg('sea', 'red', 'sue'))

    def test_deleting_is_logged(self):
        self.tap('trd:mdnc:sue')
        self.assertIn('map_node_remove', [entry[1] for entry in self.logged])


class StringsIntegrityTest(unittest.TestCase):

    def test_all_languages_define_the_same_keys(self):
        reference = set(trade_map_admin.STRINGS['en'])
        for lang, table in trade_map_admin.STRINGS.items():
            self.assertEqual(set(table), reference, f'{lang} keys differ')

    def test_every_map_error_has_a_message(self):
        codes = ('bad_id', 'bad_kind', 'bad_mode', 'exists', 'unknown_node', 'in_transit',
                 'guard_unavailable', 'self_edge', 'mode_mismatch', 'bad_units',
                 'edge_exists', 'no_edge')
        for lang, table in trade_map_admin.STRINGS.items():
            for code in codes:
                self.assertIn('map_err_' + code, table, f'{lang} lacks a message for {code}')

    def test_every_node_kind_has_a_label(self):
        for lang, table in trade_map_admin.STRINGS.items():
            for kinds in trade_map.KINDS.values():
                for kind in kinds:
                    self.assertIn('map_kind_' + kind, table, f'{lang} lacks {kind}')

    def test_the_routed_ops_are_the_ones_the_handler_knows(self):
        # Every op the module advertises must reach a branch rather than the
        # generic error, or a button would silently do nothing.
        self.assertIn('map', trade_map_admin.OPS)
        self.assertNotIn('m', trade_map_admin.OPS, "'m' belongs to the trade wizard")
        self.assertNotIn('menu', trade_map_admin.OPS)


if __name__ == '__main__':
    unittest.main()
