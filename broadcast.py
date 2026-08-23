# -*- coding: utf-8 -*-
"""Statements and military campaigns — the two things the bot posts publicly.

Both used to live three times over, once in each main*.py, and both fired the
moment the last question was answered: no preview, no way back. This module
owns them once and adds the three things that were missing.

    A confirmation step.  Nothing reaches a channel until somebody has read it
    back and pressed the button. Cancelling costs nothing.

    No length limit.      Telegram caps a message at 4096 characters and a
                          caption at 1024. A statement longer than that used to
                          fail silently; now it is split across messages, and
                          media with a long caption sends the picture first and
                          the words after it.

    A country to speak for. A statement is "from" somewhere, so a lord may only
                          issue one inside their own group's chat. Admins and
                          the owner may post from anywhere, and are asked which
                          country they are speaking for.

main*.py calls init(), routes its 'statement' / 'attack' menu buttons to
start_statement() / start_campaign(), and 'bc:' callbacks to handle_callback().
"""

import html
import threading

from telebot import types

_bot = None
_conn = None
_CHANNEL = None
_WAR_CHANNEL = None
_lang = 'fa'
_is_admin = None
_notify_admins = None
_war_photo = None
_audit = None
_lock = threading.RLock()

PREFIX = 'bc:'

# Telegram's own limits. A body longer than TEXT_LIMIT is split; a caption
# longer than CAPTION_LIMIT means the media goes out on its own and the words
# follow as text.
TEXT_LIMIT = 4096
CAPTION_LIMIT = 1024

# A draft waiting for its author to confirm it, keyed by user id. In memory
# only: nothing has been posted or charged, so losing one on a restart costs
# only the typing.
_drafts = {}

# The media kinds a statement may carry, in the order they are looked for on an
# incoming message: attribute on the message -> the bot method that sends it.
MEDIA = (
    ('photo', 'send_photo'),
    ('video', 'send_video'),
    ('document', 'send_document'),
    ('audio', 'send_audio'),
    ('voice', 'send_voice'),
    ('animation', 'send_animation'),
)

STRINGS = {
    'fa': {
        'err_generic': "خطایی رخ داد. دوباره تلاش کنید.",
        'not_registered': "این گروه هنوز کشوری ندارد.",
        'no_groups': "هنوز هیچ کشوری ثبت نشده است.",
        'st_group_only': "🙌 بیانیه باید از داخل گروه کشور خودتان فرستاده شود، نه در چت "
                         "خصوصی با ربات.",
        'st_not_lord': "شما لرد این گروه نیستید.",
        'st_pick_country': "🙌 بیانیه از طرف کدام کشور فرستاده شود؟",
        'st_ask': "<b>بیانیه خود را بفرستید</b>\nمتن، عکس، ویدیو یا صدا — به هر طولی که "
                  "بخواهید.",
        'st_empty': "چیزی برای فرستادن پیدا نشد. دوباره تلاش کنید.",
        'st_preview': "🙌 <b>پیش‌نمایش بیانیه</b>\n<blockquote>{body}</blockquote>\n"
                      "🌍 از طرف: {g}\n\nفرستاده شود؟",
        'st_preview_media': "\n📎 به همراه یک فایل ({kind})",
        'st_preview_long': "\n\nℹ️ این بیانیه بلند است و در {n} پیام پشت سر هم فرستاده می‌شود.",
        'st_footer': "\n\n🌍 از {g}\n👤 فرمانده: {u}",
        'st_sent': "✅ بیانیه شما <b>فرستاده شد</b>.",
        'st_failed': "❌ فرستادن بیانیه ممکن نشد. با مدیریت تماس بگیرید.",
        'st_cancelled': "🚫 بیانیه لغو شد؛ چیزی فرستاده نشد.",
        'btn_send': "✅ بله، بفرست",
        'btn_cancel': "🚫 لغو",
        'at_pick_type': "نوع لشکرکشی را انتخاب کنید:",
        'at_land': "زمینی",
        'at_sea': "دریایی",
        'at_ask_details': "اطلاعات ارتش خود را وارد کنید:",
        'at_ask_origin': "مبدا لشکرکشی را وارد کنید:",
        'at_ask_dest': "مقصد لشکرکشی را وارد کنید:",
        'at_ask_time': "زمان رسیدن را وارد کنید:",
        'at_preview': "⚔️ <b>پیش‌نمایش لشکرکشی</b>\n<blockquote>{headline}</blockquote>\n"
                      "📝 جزئیات (فقط برای مدیریت): {details}\n\nفرستاده شود؟",
        'at_headline': "🔖 ارتش کشور {src} به مقصد {dst} حرکت کردند ({kind})\n\n"
                       "⚜️ فرمانده: {u}\n⌛️ زمان رسیدن: {when}",
        'at_report': "{headline}\n📝 جزئیات: {details}",
        'at_sent': "✅ اطلاعات لشکرکشی فرستاده شد.",
        'at_cancelled': "🚫 لشکرکشی لغو شد؛ چیزی فرستاده نشد.",
        'at_expired': "این لشکرکشی دیگر در جریان نیست. از اول شروع کنید.",
        'at_empty': "چیزی وارد نشد. دوباره تلاش کنید.",
    },
    'en': {
        'err_generic': "Something went wrong. Please try again.",
        'not_registered': "This group has no country yet.",
        'no_groups': "No country is registered yet.",
        'st_group_only': "🙌 A statement has to be sent from inside your own country's group "
                         "chat, not in a private chat with the bot.",
        'st_not_lord': "You are not a lord of this group.",
        'st_pick_country': "🙌 Which country is this statement from?",
        'st_ask': "<b>Send your statement</b>\nText, a photo, a video or audio — any length "
                  "you like.",
        'st_empty': "There was nothing to send. Please try again.",
        'st_preview': "🙌 <b>Statement preview</b>\n<blockquote>{body}</blockquote>\n"
                      "🌍 From: {g}\n\nSend it?",
        'st_preview_media': "\n📎 With one attachment ({kind})",
        'st_preview_long': "\n\nℹ️ This is long, and goes out as {n} messages in a row.",
        'st_footer': "\n\n🌍 From {g}\n👤 Commander: {u}",
        'st_sent': "✅ Your statement has been <b>sent</b>.",
        'st_failed': "❌ The statement could not be sent. Please tell an admin.",
        'st_cancelled': "🚫 Statement cancelled; nothing was sent.",
        'btn_send': "✅ Yes, send it",
        'btn_cancel': "🚫 Cancel",
        'at_pick_type': "Choose the type of military campaign:",
        'at_land': "Land",
        'at_sea': "Sea",
        'at_ask_details': "Please enter your army information:",
        'at_ask_origin': "Enter the origin of the campaign:",
        'at_ask_dest': "Enter the destination of the campaign:",
        'at_ask_time': "Enter the arrival time:",
        'at_preview': "⚔️ <b>Campaign preview</b>\n<blockquote>{headline}</blockquote>\n"
                      "📝 Details (admins only): {details}\n\nSend it?",
        'at_headline': "🔖 The army of {src} has set out for {dst} ({kind})\n\n"
                       "⚜️ Commander: {u}\n⌛️ Arrival time: {when}",
        'at_report': "{headline}\n📝 Details: {details}",
        'at_sent': "✅ The campaign has been announced.",
        'at_cancelled': "🚫 Campaign cancelled; nothing was sent.",
        'at_expired': "That campaign is no longer in progress. Please start again.",
        'at_empty': "Nothing was entered. Please try again.",
    },
    'tr': {
        'err_generic': "Bir hata oluştu. Lütfen tekrar deneyin.",
        'not_registered': "Bu grubun henüz bir ülkesi yok.",
        'no_groups': "Henüz kayıtlı bir ülke yok.",
        'st_group_only': "🙌 Bildiri, botla özel sohbette değil, kendi ülkenizin grup "
                         "sohbetinden gönderilmelidir.",
        'st_not_lord': "Bu grubun lordu değilsiniz.",
        'st_pick_country': "🙌 Bu bildiri hangi ülkeden?",
        'st_ask': "<b>Bildirinizi gönderin</b>\nMetin, fotoğraf, video veya ses — istediğiniz "
                  "uzunlukta.",
        'st_empty': "Gönderilecek bir şey bulunamadı. Lütfen tekrar deneyin.",
        'st_preview': "🙌 <b>Bildiri önizlemesi</b>\n<blockquote>{body}</blockquote>\n"
                      "🌍 Gönderen: {g}\n\nGönderilsin mi?",
        'st_preview_media': "\n📎 Bir ek ile ({kind})",
        'st_preview_long': "\n\nℹ️ Bu bildiri uzun; arka arkaya {n} mesaj olarak gider.",
        'st_footer': "\n\n🌍 {g} grubundan\n👤 Komutan: {u}",
        'st_sent': "✅ Bildiriniz <b>gönderildi</b>.",
        'st_failed': "❌ Bildiri gönderilemedi. Lütfen bir yöneticiye haber verin.",
        'st_cancelled': "🚫 Bildiri iptal edildi; hiçbir şey gönderilmedi.",
        'btn_send': "✅ Evet, gönder",
        'btn_cancel': "🚫 İptal",
        'at_pick_type': "Sefer türünü seçin:",
        'at_land': "Kara",
        'at_sea': "Deniz",
        'at_ask_details': "Ordu bilgilerinizi girin:",
        'at_ask_origin': "Seferin çıkış yerini girin:",
        'at_ask_dest': "Seferin hedefini girin:",
        'at_ask_time': "Varış zamanını girin:",
        'at_preview': "⚔️ <b>Sefer önizlemesi</b>\n<blockquote>{headline}</blockquote>\n"
                      "📝 Detaylar (yalnızca yöneticiler): {details}\n\nGönderilsin mi?",
        'at_headline': "🔖 {src} ordusu {dst} hedefine doğru harekete geçti ({kind})\n\n"
                       "⚜️ Komutan: {u}\n⌛️ Varış zamanı: {when}",
        'at_report': "{headline}\n📝 Detaylar: {details}",
        'at_sent': "✅ Sefer duyuruldu.",
        'at_cancelled': "🚫 Sefer iptal edildi; hiçbir şey gönderilmedi.",
        'at_expired': "O sefer artık sürmüyor. Lütfen yeniden başlayın.",
        'at_empty': "Hiçbir şey girilmedi. Lütfen tekrar deneyin.",
    },
}


def init(bot, conn, channel_id, war_channel_id, lang='fa', is_admin=None,
         notify_admins=None, war_photo=None, audit=None):
    global _bot, _conn, _CHANNEL, _WAR_CHANNEL, _lang, _is_admin
    global _notify_admins, _war_photo, _audit
    assert lang in STRINGS, f"unsupported lang: {lang}"
    assert set(STRINGS['fa']) == set(STRINGS['en']) == set(STRINGS['tr']), \
        "STRINGS language key sets differ"
    _bot = bot
    _conn = conn
    _CHANNEL = channel_id
    _WAR_CHANNEL = war_channel_id or channel_id
    _lang = lang
    _is_admin = is_admin if is_admin is not None else (lambda uid: False)
    _notify_admins = notify_admins
    _war_photo = war_photo
    _audit = audit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _t(string_id, **kw):
    text = STRINGS[_lang][string_id]
    return text.format(**kw) if kw else text


def _esc(text):
    return html.escape(str(text), quote=False) if text else ''


def _answer(call, text=None, alert=False):
    try:
        _bot.answer_callback_query(call.id, text, show_alert=alert)
    except Exception:
        pass


def _log(actor_id, action, target='', detail=''):
    if _audit is None:
        return
    try:
        _audit(actor_id, action, target, detail)
    except Exception:
        pass


def _q(sql, params=()):
    with _lock:
        cur = _conn.execute(sql, params)
        return cur.fetchall()


def _groups():
    return [row[0] for row in _q("SELECT DISTINCT group_id FROM users ORDER BY group_id")]


def _is_lord(group_id, user_id):
    return bool(_q("SELECT 1 FROM users WHERE group_id=? AND user_id=?", (group_id, user_id)))


def _title(group_id):
    try:
        chat = _bot.get_chat(group_id)
        return chat.title or str(group_id)
    except Exception:
        return str(group_id)


def _user_link(user_id):
    try:
        info = _bot.get_chat(user_id)
        return f"<a href='tg://user?id={user_id}'>{_esc(info.first_name)}</a>"
    except Exception:
        return str(user_id)


def _confirm_markup(ok, cancel):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(_t('btn_send'), callback_data=ok),
               types.InlineKeyboardButton(_t('btn_cancel'), callback_data=cancel))
    return markup


def chunks(text, limit=TEXT_LIMIT):
    """Split a body into pieces Telegram will accept, breaking at newlines.

    A statement is prose, so it is cut between lines wherever that is possible
    and only mid-line when a single line is itself over the limit. The pieces
    are sent in order, which is why the attribution rides on the last one.
    """
    text = text or ''
    if len(text) <= limit:
        return [text] if text else []
    out, current = [], ''
    for line in text.split('\n'):
        while len(line) > limit:                # one enormous line: hard-cut it
            if current:
                out.append(current)
                current = ''
            out.append(line[:limit])
            line = line[limit:]
        candidate = line if not current else current + '\n' + line
        if len(candidate) > limit:
            out.append(current)
            current = line
        else:
            current = candidate
    if current:
        out.append(current)
    return out


def _media_of(message):
    """(kind, file_id) of whatever the message carries, or (None, None)."""
    for kind, _method in MEDIA:
        found = getattr(message, kind, None)
        if found:
            # photo arrives as a list of sizes; the last one is the largest
            item = found[-1] if isinstance(found, (list, tuple)) else found
            return kind, getattr(item, 'file_id', None)
    return None, None


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------


def start_statement(message, user_id):
    """The 🙌 button. Where it is allowed from depends on who pressed it.

    A lord speaks for their group, so they have to be in it. An admin or the
    owner may speak for any country, and is asked which one.
    """
    chat_id = message.chat.id
    in_group = message.chat.type in ('group', 'supergroup')
    if in_group:
        if not _q("SELECT 1 FROM users WHERE group_id=?", (chat_id,)):
            _bot.send_message(chat_id, _t('not_registered'))
            return
        if not (_is_lord(chat_id, user_id) or _is_admin(user_id)):
            _bot.send_message(chat_id, _t('st_not_lord'))
            return
        _ask_statement(chat_id, user_id, chat_id)
        return
    # Private chat: this is where lords were bypassing their own group.
    if not _is_admin(user_id):
        _bot.send_message(chat_id, _t('st_group_only'))
        return
    groups = _groups()
    if not groups:
        _bot.send_message(chat_id, _t('no_groups'))
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for gid in groups:
        markup.add(types.InlineKeyboardButton(_title(gid), callback_data=f'bc:sg:{gid}'))
    _bot.send_message(chat_id, _t('st_pick_country'), reply_markup=markup)


def _pick_country(call, gid):
    if not _is_admin(call.from_user.id):
        _answer(call, _t('st_group_only'), alert=True)
        return
    _answer(call)
    _ask_statement(call.message.chat.id, call.from_user.id, gid)


def _ask_statement(chat_id, user_id, group_id):
    _drafts[user_id] = {'kind': 'statement', 'chat_id': chat_id, 'group_id': group_id}
    sent = _bot.send_message(chat_id, _t('st_ask'), parse_mode='HTML')
    _bot.register_next_step_handler(sent, lambda msg: _collect_statement(msg, user_id))


def _collect_statement(message, user_id):
    draft = _drafts.get(user_id)
    if not draft or draft.get('kind') != 'statement':
        return
    kind, file_id = _media_of(message)
    # A media message carries its words in `caption`, a plain one in `text`.
    body = getattr(message, 'text', None) or getattr(message, 'caption', None) or ''
    if not body and not file_id:
        _bot.send_message(draft['chat_id'], _t('st_empty'))
        _drafts.pop(user_id, None)
        return
    draft.update({'body': body, 'media': kind, 'file_id': file_id})
    _preview_statement(user_id)


def _statement_text(draft, user_id):
    """The full body as it will be posted, attribution included."""
    return _esc(draft.get('body')) + _t('st_footer', g=_esc(_title(draft['group_id'])),
                                        u=_user_link(user_id))


def _preview_statement(user_id):
    draft = _drafts.get(user_id)
    if not draft:
        return
    full = _statement_text(draft, user_id)
    pieces = chunks(full)
    # The preview itself is a Telegram message, so a very long statement is
    # shown trimmed. What gets posted is the whole thing.
    shown = draft.get('body') or ''
    if len(shown) > 1500:
        shown = shown[:1500] + '…'
    text = _t('st_preview', body=_esc(shown) or '—',
              g=_esc(_title(draft['group_id'])))
    if draft.get('file_id'):
        text += _t('st_preview_media', kind=draft['media'])
    if len(pieces) > 1:
        text += _t('st_preview_long', n=len(pieces))
    _bot.send_message(draft['chat_id'], text, parse_mode='HTML',
                      reply_markup=_confirm_markup('bc:sok', 'bc:sx'))


def _send_statement(call):
    user_id = call.from_user.id
    draft = _drafts.pop(user_id, None)
    if not draft or draft.get('kind') != 'statement':
        _answer(call, _t('err_generic'), alert=True)
        return
    _answer(call)
    full = _statement_text(draft, user_id)
    pieces = chunks(full)
    try:
        _post(pieces, draft)
    except Exception:
        _bot.send_message(draft['chat_id'], _t('st_failed'))
        return
    _log(user_id, 'statement', _title(draft['group_id']), f'{len(full)} chars')
    _bot.send_message(draft['chat_id'], _t('st_sent'), parse_mode='HTML')


def _post(pieces, draft):
    """Put a statement on the channel, however long it is.

    Media with a caption that fits goes out as one message, which is what a
    short statement with a picture has always looked like. Past that the media
    leads and the words follow, because a caption cannot hold them.
    """
    file_id = draft.get('file_id')
    if file_id:
        method = dict(MEDIA)[draft['media']]
        send = getattr(_bot, method)
        if len(pieces) == 1 and len(pieces[0]) <= CAPTION_LIMIT:
            send(_CHANNEL, file_id, caption=pieces[0], parse_mode='HTML')
            return
        send(_CHANNEL, file_id)
    for piece in pieces:
        _bot.send_message(_CHANNEL, piece, parse_mode='HTML')


def _cancel_statement(call):
    _drafts.pop(call.from_user.id, None)
    _answer(call)
    _bot.send_message(call.message.chat.id, _t('st_cancelled'))


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------


def start_campaign(message, user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(_t('at_land'), callback_data='bc:at:land'),
               types.InlineKeyboardButton(_t('at_sea'), callback_data='bc:at:sea'))
    _bot.send_message(message.chat.id, _t('at_pick_type'), reply_markup=markup)


def _campaign_type(call, kind):
    if kind not in ('land', 'sea'):
        _answer(call, _t('err_generic'))
        return
    user_id = call.from_user.id
    # Per-user, not a module global: two campaigns can be in flight at once.
    _drafts[user_id] = {'kind': 'campaign', 'chat_id': call.message.chat.id, 'type': kind}
    _answer(call)
    _ask_campaign(user_id, 'at_ask_details', 'details', 'at_ask_origin')


# The campaign questions in order: which prompt, where the answer is stored,
# and which prompt comes next. The last one has no next and shows the preview.
CAMPAIGN_STEPS = {
    'at_ask_details': ('details', 'at_ask_origin'),
    'at_ask_origin': ('origin', 'at_ask_dest'),
    'at_ask_dest': ('destination', 'at_ask_time'),
    'at_ask_time': ('when', None),
}


def _ask_campaign(user_id, prompt, field, nxt):
    draft = _drafts.get(user_id)
    if not draft:
        return
    sent = _bot.send_message(draft['chat_id'], _t(prompt))

    def on_answer(message):
        current = _drafts.get(user_id)
        if not current or current.get('kind') != 'campaign':
            return
        text = (message.text or '').strip()
        if not text:
            _bot.send_message(current['chat_id'], _t('at_empty'))
            _ask_campaign(user_id, prompt, field, nxt)
            return
        current[field] = _esc(text)
        if nxt is None:
            _preview_campaign(user_id)
        else:
            _ask_campaign(user_id, nxt, *CAMPAIGN_STEPS[nxt])

    _bot.register_next_step_handler(sent, on_answer)


def _headline(draft, user_id):
    return _t('at_headline', src=draft.get('origin', ''), dst=draft.get('destination', ''),
              kind=_t('at_' + draft['type']), u=_user_link(user_id),
              when=draft.get('when', ''))


def _preview_campaign(user_id):
    draft = _drafts.get(user_id)
    if not draft:
        return
    _bot.send_message(draft['chat_id'],
                      _t('at_preview', headline=_headline(draft, user_id),
                         details=draft.get('details', '')),
                      parse_mode='HTML',
                      reply_markup=_confirm_markup('bc:aok', 'bc:ax'))


def _send_campaign(call):
    user_id = call.from_user.id
    draft = _drafts.pop(user_id, None)
    if not draft or draft.get('kind') != 'campaign':
        _answer(call, _t('at_expired'), alert=True)
        return
    _answer(call)
    headline = _headline(draft, user_id)
    # Troop numbers stay private: the owner and every bot admin get the full
    # report, the public post below carries none of it.
    if _notify_admins is not None:
        _notify_admins(_t('at_report', headline=headline, details=draft.get('details', '')),
                       parse_mode='HTML')
    photo = _war_photo(draft['type']) if _war_photo is not None else ''
    if photo:
        _bot.send_photo(_WAR_CHANNEL, photo, caption=headline, parse_mode='HTML')
    else:
        _bot.send_message(_WAR_CHANNEL, headline, parse_mode='HTML')
    _log(user_id, 'campaign', draft.get('destination', ''), draft['type'])
    _bot.send_message(draft['chat_id'], _t('at_sent'))


def _cancel_campaign(call):
    _drafts.pop(call.from_user.id, None)
    _answer(call)
    _bot.send_message(call.message.chat.id, _t('at_cancelled'))


# ---------------------------------------------------------------------------
# Callback entry point
# ---------------------------------------------------------------------------


def handle_callback(call):
    """Dispatch 'bc:' callbacks. main*.py has already filtered by prefix."""
    parts = call.data.split(':')
    op = parts[1] if len(parts) > 1 else ''
    if op == 'sg':
        _pick_country(call, int(parts[2]))
    elif op == 'sok':
        _send_statement(call)
    elif op == 'sx':
        _cancel_statement(call)
    elif op == 'at':
        _campaign_type(call, parts[2])
    elif op == 'aok':
        _send_campaign(call)
    elif op == 'ax':
        _cancel_campaign(call)
    else:
        _answer(call, _t('err_generic'))
