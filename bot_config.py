# -*- coding: utf-8 -*-
"""Startup configuration for the bot — no secrets in the source tree.

Every value is resolved in this order:

    1. environment variable   (BOT_TOKEN, ADMIN_ID, CHANNEL_ID, WAR_CHANNEL_ID)
    2. bot_config.json        (written by a previous run, gitignored)
    3. terminal prompt        (input(), re-asks until the value is valid)

Anything typed at the prompt is written back to bot_config.json, so each value
only has to be pasted once. Environment variables always win, which makes the
bot deployable without ever creating the file.

Usage from main*.py:

    import bot_config
    conf = bot_config.load(lang='fa')
    API_TOKEN      = conf['token']
    ADMIN_ID       = conf['admin_id']
    CHANNEL_ID     = conf['channel_id']
    WAR_CHANNEL_ID = conf['war_channel_id']
"""

import json
import os
import sys

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot_config.json')

# Values shipped in the original source as placeholders. Treated as "not set"
# so an untouched checkout still walks the user through the prompts.
PLACEHOLDERS = ('', 'YOUR TOKEN', 'YOUR CHANNEL ID, EXAMPLE : @SOMETHING', '0', '000')


class ConfigError(ValueError):
    """Raised by a validator when a supplied value cannot be used."""


# ---------------------------------------------------------------------------
# Validators — each returns the cleaned value or raises ConfigError
# ---------------------------------------------------------------------------


def _clean_token(raw):
    value = str(raw).strip()
    if value in PLACEHOLDERS:
        raise ConfigError('empty')
    if ':' not in value:
        raise ConfigError('shape')
    return value


def _clean_admin_id(raw):
    value = str(raw).strip()
    if value in PLACEHOLDERS:
        raise ConfigError('empty')
    try:
        number = int(value)
    except ValueError:
        raise ConfigError('shape')
    if number == 0:
        raise ConfigError('empty')
    return number


def _clean_channel(raw):
    value = str(raw).strip()
    if value in PLACEHOLDERS:
        raise ConfigError('empty')
    if not (value.startswith('@') or value.lstrip('-').isdigit()):
        raise ConfigError('shape')
    return value


def _clean_optional_channel(raw):
    """Blank is allowed — the caller falls back to the main channel."""
    value = str(raw).strip()
    if value in PLACEHOLDERS:
        return ''
    return _clean_channel(value)


# key, environment variable, validator
FIELDS = (
    ('token', 'BOT_TOKEN', _clean_token),
    ('admin_id', 'ADMIN_ID', _clean_admin_id),
    ('channel_id', 'CHANNEL_ID', _clean_channel),
    ('war_channel_id', 'WAR_CHANNEL_ID', _clean_optional_channel),
)

PROMPTS = {
    'fa': {
        'intro': "\n=== پیکربندی ربات ===\n"
                 "مقادیر زیر یک بار پرسیده می‌شوند و در bot_config.json ذخیره می‌گردند.\n"
                 "(این فایل در .gitignore است و نباید کامیت شود.)\n",
        'saved': "✅ تنظیمات در {path} ذخیره شد.\n",
        'token': "توکن ربات (از @BotFather): ",
        'admin_id': "شناسه عددی مالک ربات (از @userinfobot): ",
        'channel_id': "شناسه کانال خبری (مثال: @mychannel یا -100…): ",
        'war_channel_id': "شناسه کانال جنگ (برای استفاده از همان کانال خبری خالی بگذارید): ",
        'err_empty': "❌ این مقدار نمی‌تواند خالی باشد.",
        'err_shape': "❌ قالب مقدار وارد شده درست نیست.",
        'err_noninteractive': "پیکربندی ناقص است و ترمینال تعاملی نیست. "
                              "متغیرهای محیطی BOT_TOKEN، ADMIN_ID و CHANNEL_ID را تنظیم کنید "
                              "یا bot_config.json را بسازید.",
    },
    'en': {
        'intro': "\n=== Bot configuration ===\n"
                 "These values are asked once and stored in bot_config.json.\n"
                 "(That file is gitignored — never commit it.)\n",
        'saved': "✅ Settings saved to {path}\n",
        'token': "Bot token (from @BotFather): ",
        'admin_id': "Owner numeric user id (from @userinfobot): ",
        'channel_id': "News channel id (e.g. @mychannel or -100…): ",
        'war_channel_id': "War channel id (leave blank to reuse the news channel): ",
        'err_empty': "❌ This value cannot be empty.",
        'err_shape': "❌ That value is not in the expected format.",
        'err_noninteractive': "Configuration is incomplete and the terminal is not interactive. "
                              "Set BOT_TOKEN, ADMIN_ID and CHANNEL_ID in the environment, "
                              "or create bot_config.json.",
    },
    'tr': {
        'intro': "\n=== Bot yapılandırması ===\n"
                 "Bu değerler bir kez sorulur ve bot_config.json içinde saklanır.\n"
                 "(Bu dosya .gitignore içindedir — asla commit etmeyin.)\n",
        'saved': "✅ Ayarlar {path} dosyasına kaydedildi.\n",
        'token': "Bot jetonu (@BotFather'dan): ",
        'admin_id': "Sahip sayısal kullanıcı kimliği (@userinfobot'tan): ",
        'channel_id': "Haber kanalı kimliği (örn. @mychannel veya -100…): ",
        'war_channel_id': "Savaş kanalı kimliği (haber kanalını kullanmak için boş bırakın): ",
        'err_empty': "❌ Bu değer boş olamaz.",
        'err_shape': "❌ Girilen değer beklenen biçimde değil.",
        'err_noninteractive': "Yapılandırma eksik ve terminal etkileşimli değil. "
                              "BOT_TOKEN, ADMIN_ID ve CHANNEL_ID ortam değişkenlerini ayarlayın "
                              "veya bot_config.json oluşturun.",
    },
}


def _read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_file(path, data):
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write('\n')
    try:  # best effort: keep the token out of other users' reach on POSIX
        os.chmod(path, 0o600)
    except OSError:
        pass


def load(lang='en', path=None, env=None, input_fn=None, out=None, interactive=None):
    """Resolve every config value and return it as a dict.

    The keyword arguments exist so the resolution logic can be tested without
    touching the real environment, the real file or a real terminal.
    """
    words = PROMPTS.get(lang, PROMPTS['en'])
    path = CONFIG_FILE if path is None else path
    env = os.environ if env is None else env
    input_fn = input if input_fn is None else input_fn
    out = (lambda text: print(text, end='')) if out is None else out
    if interactive is None:
        interactive = sys.stdin is not None and sys.stdin.isatty()

    stored = _read_file(path)
    resolved = {}
    dirty = False
    greeted = False

    for key, env_var, clean in FIELDS:
        value = None
        for candidate in (env.get(env_var), stored.get(key)):
            if candidate is None:
                continue
            try:
                value = clean(candidate)
            except ConfigError:
                continue
            break

        # A key no source mentions is still asked for, even when optional —
        # an optional validator simply accepts a blank answer.
        while value is None:
            if not interactive:
                # Headless run: an optional key quietly resolves to blank,
                # a required one is a hard error rather than a hang.
                try:
                    value = clean('')
                    break
                except ConfigError:
                    raise SystemExit(words['err_noninteractive'])
            if not greeted:
                out(words['intro'])
                greeted = True
            try:
                value = clean(input_fn(words[key]))
            except ConfigError as exc:
                out(words['err_empty' if str(exc) == 'empty' else 'err_shape'] + '\n')
                value = None
                continue
            dirty = True

        resolved[key] = value

    if dirty:
        to_store = dict(stored)
        to_store.update({k: resolved[k] for k, _, _ in FIELDS})
        _write_file(path, to_store)
        out(words['saved'].format(path=path))

    # A blank war channel simply reuses the news channel.
    if not resolved['war_channel_id']:
        resolved['war_channel_id'] = resolved['channel_id']

    return resolved
