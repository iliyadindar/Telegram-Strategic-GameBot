# -*- coding: utf-8 -*-
"""bot_config resolution order: environment -> file -> prompt."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bot_config


GOOD = {
    'token': '12345:ABCdefGHIjkl',
    'admin_id': '4242',
    'channel_id': '@newsroom',
    'war_channel_id': '@warroom',
}


class Prompter:
    """Feeds canned answers to load()'s input_fn and records the questions."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.asked = []

    def __call__(self, prompt):
        self.asked.append(prompt)
        return self.answers.pop(0)


class ConfigTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, 'bot_config.json')
        self.addCleanup(self.dir.cleanup)

    def write(self, data):
        with open(self.path, 'w', encoding='utf-8') as fh:
            json.dump(data, fh)

    def load(self, env=None, answers=(), interactive=True):
        prompter = Prompter(answers)
        conf = bot_config.load(lang='en', path=self.path, env=env or {},
                               input_fn=prompter, out=lambda t: None,
                               interactive=interactive)
        return conf, prompter

    def test_environment_wins_and_nothing_is_prompted(self):
        env = {'BOT_TOKEN': GOOD['token'], 'ADMIN_ID': GOOD['admin_id'],
               'CHANNEL_ID': GOOD['channel_id'], 'WAR_CHANNEL_ID': GOOD['war_channel_id']}
        conf, prompter = self.load(env=env)
        self.assertEqual(conf['token'], GOOD['token'])
        self.assertEqual(conf['admin_id'], 4242)
        self.assertEqual(conf['war_channel_id'], '@warroom')
        self.assertEqual(prompter.asked, [])
        self.assertFalse(os.path.exists(self.path), 'env-only runs must not write a file')

    def test_environment_overrides_the_stored_file(self):
        self.write(dict(GOOD, token='99:STORED'))
        conf, _ = self.load(env={'BOT_TOKEN': '11:FROMENV'})
        self.assertEqual(conf['token'], '11:FROMENV')
        self.assertEqual(conf['admin_id'], 4242, 'other keys still come from the file')

    def test_stored_file_is_used_without_prompting(self):
        self.write(GOOD)
        conf, prompter = self.load()
        self.assertEqual(prompter.asked, [])
        self.assertEqual(conf['channel_id'], '@newsroom')

    def test_prompts_when_nothing_is_available_and_saves_the_answers(self):
        conf, prompter = self.load(answers=[GOOD['token'], GOOD['admin_id'],
                                            GOOD['channel_id'], GOOD['war_channel_id']])
        self.assertEqual(len(prompter.asked), 4)
        self.assertEqual(conf['admin_id'], 4242)
        with open(self.path, encoding='utf-8') as fh:
            saved = json.load(fh)
        self.assertEqual(saved['token'], GOOD['token'])
        self.assertEqual(saved['admin_id'], 4242)

    def test_placeholder_values_count_as_unset(self):
        self.write({'token': 'YOUR TOKEN', 'admin_id': '000',
                    'channel_id': 'YOUR CHANNEL ID, EXAMPLE : @SOMETHING'})
        conf, prompter = self.load(answers=[GOOD['token'], GOOD['admin_id'],
                                            GOOD['channel_id'], ''])
        self.assertEqual(len(prompter.asked), 4)
        self.assertEqual(conf['token'], GOOD['token'])

    def test_invalid_input_is_asked_again(self):
        answers = ['no-colon-here', GOOD['token'],      # token: rejected once
                   'not-a-number', GOOD['admin_id'],    # admin id: rejected once
                   'newsroom', GOOD['channel_id'],      # channel: rejected once
                   '']
        conf, prompter = self.load(answers=answers)
        self.assertEqual(len(prompter.asked), 7)
        self.assertEqual(conf['token'], GOOD['token'])
        self.assertEqual(conf['admin_id'], 4242)

    def test_blank_war_channel_falls_back_to_the_news_channel(self):
        conf, _ = self.load(answers=[GOOD['token'], GOOD['admin_id'],
                                     GOOD['channel_id'], ''])
        self.assertEqual(conf['war_channel_id'], GOOD['channel_id'])

    def test_numeric_channel_ids_are_accepted(self):
        conf, _ = self.load(answers=[GOOD['token'], GOOD['admin_id'], '-1001234567890', ''])
        self.assertEqual(conf['channel_id'], '-1001234567890')

    def test_non_interactive_with_missing_values_exits_instead_of_hanging(self):
        with self.assertRaises(SystemExit):
            self.load(interactive=False)

    def test_non_interactive_is_fine_when_the_environment_is_complete(self):
        env = {'BOT_TOKEN': GOOD['token'], 'ADMIN_ID': GOOD['admin_id'],
               'CHANNEL_ID': GOOD['channel_id']}
        conf, _ = self.load(env=env, interactive=False)
        self.assertEqual(conf['war_channel_id'], GOOD['channel_id'])

    def test_every_language_defines_the_same_prompt_keys(self):
        reference = set(bot_config.PROMPTS['en'])
        for lang, words in bot_config.PROMPTS.items():
            self.assertEqual(set(words), reference, f'{lang} prompt keys differ')


if __name__ == '__main__':
    unittest.main()
