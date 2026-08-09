# -*- coding: utf-8 -*-
"""Minimal stand-ins for telebot objects, so panel logic can be tested offline."""

import sqlite3

import asset_catalog


class Chat:
    def __init__(self, chat_id, chat_type='supergroup', title=None,
                 first_name=None, last_name=None):
        self.id = chat_id
        self.type = chat_type
        self.title = title
        self.first_name = first_name
        self.last_name = last_name


class User:
    def __init__(self, user_id, first_name='User', is_bot=False):
        self.id = user_id
        self.first_name = first_name
        self.last_name = None
        self.is_bot = is_bot


class Message:
    def __init__(self, chat, from_user, text=None, reply_to_message=None,
                 photo=None, forward_from=None, message_id=1):
        self.chat = chat
        self.from_user = from_user
        self.text = text
        self.reply_to_message = reply_to_message
        self.photo = photo
        self.forward_from = forward_from
        self.message_id = message_id


class Call:
    def __init__(self, data, from_user, message, call_id='c1'):
        self.data = data
        self.from_user = from_user
        self.message = message
        self.id = call_id


class StubBot:
    """Records every outgoing call instead of talking to Telegram."""

    def __init__(self, chats=None):
        self.sent = []          # (chat_id, text)
        self.answers = []       # (call_id, text, show_alert)
        self.edits = []         # (chat_id, message_id, text)
        self.photos = []        # (chat_id, file_id, caption)
        self.replies = []       # (message, text)
        self.next_steps = []    # (message, callback)
        self.handlers = []      # ('message'|'callback', kwargs, fn)
        self.markups = []       # every reply_markup handed to the bot, in order
        self.polled = False
        self._chats = chats or {}

    # --- outgoing -------------------------------------------------------
    def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text))
        self._record_markup(kwargs)
        return Message(Chat(chat_id), User(0), message_id=len(self.sent))

    def send_photo(self, chat_id, file_id, caption=None, **kwargs):
        self.photos.append((chat_id, file_id, caption))
        return Message(Chat(chat_id), User(0), message_id=len(self.photos))

    def reply_to(self, message, text, **kwargs):
        self.replies.append((message, text))
        self._record_markup(kwargs)

    def edit_message_text(self, text, chat_id, message_id, **kwargs):
        self.edits.append((chat_id, message_id, text))
        self._record_markup(kwargs)

    def edit_message_caption(self, caption=None, chat_id=None, message_id=None, **kwargs):
        self.edits.append((chat_id, message_id, caption))

    def answer_callback_query(self, call_id, text=None, show_alert=False):
        self.answers.append((call_id, text, show_alert))

    def register_next_step_handler(self, message, callback):
        self.next_steps.append((message, callback))

    # --- handler registration (used by the entrypoint smoke test) --------
    def message_handler(self, **kwargs):
        def decorator(fn):
            self.handlers.append(('message', kwargs, fn))
            return fn
        return decorator

    def callback_query_handler(self, **kwargs):
        def decorator(fn):
            self.handlers.append(('callback', kwargs, fn))
            return fn
        return decorator

    def infinity_polling(self, *args, **kwargs):
        self.polled = True

    # --- lookups --------------------------------------------------------
    def get_chat(self, chat_id):
        if chat_id in self._chats:
            return self._chats[chat_id]
        raise RuntimeError(f'unknown chat {chat_id}')

    # --- assertions helpers ---------------------------------------------
    def _record_markup(self, kwargs):
        markup = kwargs.get('reply_markup')
        if markup is not None:
            self.markups.append(markup)

    def last_sent_text(self):
        return self.sent[-1][1] if self.sent else None

    def last_answer(self):
        return self.answers[-1] if self.answers else None

    def last_keyboard(self):
        """callback_data of every button in the most recent keyboard."""
        if not self.markups:
            return []
        return [button.callback_data
                for row in self.markups[-1].keyboard for button in row]

    def last_button_labels(self):
        if not self.markups:
            return []
        return [button.text for row in self.markups[-1].keyboard for button in row]


# The builtin columns, exactly as main*.py declares them. asset_catalog.init()
# adds anything else the catalog knows about.
BUILTIN_COLUMNS = (
    [(key, asset_catalog.RESOURCE_DEFAULT) for key in asset_catalog.BUILTIN_RESOURCES]
    + [(key, asset_catalog.UNIT_DEFAULT) for key in asset_catalog.BUILTIN_UNITS]
    + [(key, asset_catalog.BUILDING_DEFAULT) for key, _, _ in asset_catalog.BUILTIN_BUILDINGS]
)

USERS_SCHEMA = (
    "CREATE TABLE users (user_id INTEGER PRIMARY KEY, group_id INTEGER, "
    + ', '.join(f"{key} INTEGER DEFAULT {default}" for key, default in BUILTIN_COLUMNS)
    + ", treaties TEXT DEFAULT '', home_sea TEXT DEFAULT '', home_land TEXT DEFAULT '')"
)


def make_db(with_catalog=True):
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    conn.execute(USERS_SCHEMA)
    conn.commit()
    if with_catalog:
        asset_catalog.init(conn)
    return conn


def add_group(conn, user_id, group_id, **overrides):
    cols = ['user_id', 'group_id'] + list(overrides)
    values = [user_id, group_id] + list(overrides.values())
    placeholders = ', '.join('?' * len(cols))
    conn.execute(f"INSERT INTO users ({', '.join(cols)}) VALUES ({placeholders})", values)
    conn.commit()
