"""Telegram command and callback handlers.

Handlers never manage storage, translation lookups, or platform-detection
logic directly - they go through services/language_service.py,
services/translations.py, and downloader/manager.py.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from typing import Awaitable, Callable

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.keyboards import (
    LANGUAGE_CALLBACK_PREFIX,
    YOUTUBE_QUALITY_CALLBACK_PREFIX,
    language_selection_keyboard,
    youtube_quality_keyboard,
)
from downloader.instagram import download_instagram_video
from downloader.manager import Platform, detect_platform
from downloader.youtube import (
    QualityOption,
    YouTubeExtractionError,
    download_youtube_video,
    get_available_qualities,
)
from services.language_service import get_language, has_saved_language, set_language
from services.translations import translate
from services.video_service import DeliveryOutcome, deliver_video

logger = logging.getLogger(__name__)

_DEFAULT_LANGUAGE = "en"

# context.user_data key holding at most one pending YouTube quality
# selection per user. "Pending" means: a menu was shown and hasn't been
# resolved (tapped, superseded by a newer URL, or consumed) yet.
_PENDING_YOUTUBE_KEY = "pending_youtube_selection"

# PTB's default write timeout is far too short for a video upload, so
# these are passed explicitly on the send_video call (per-call, not
# global, so nothing else in the bot is affected).
_UPLOAD_TIMEOUTS = {"write_timeout": 300, "read_timeout": 60, "connect_timeout": 30}

SendMessage = Callable[[str], Awaitable[None]]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start.

    Returning users (a saved language already exists) get a single
    "Welcome back!" message in their saved language.

    First-time users get two separate messages: a plain welcome (no
    keyboard), followed by the language-selection prompt with the
    inline keyboard attached. Before any choice is saved, this is
    always rendered in English.
    """
    user_id = update.effective_user.id

    if has_saved_language(user_id):
        lang = get_language(user_id)
        await update.message.reply_text(translate("welcome_back", lang))
        return

    await update.message.reply_text(translate("welcome", _DEFAULT_LANGUAGE))
    await update.message.reply_text(
        translate("choose_language", _DEFAULT_LANGUAGE),
        reply_markup=language_selection_keyboard(),
    )


async def handle_language_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle a tap on one of the language-selection buttons.

    Saves the choice first, then sends the confirmation in the
    newly-selected language (never in whatever language was active
    before).
    """
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = query.data.removeprefix(LANGUAGE_CALLBACK_PREFIX)

    set_language(user_id, lang)

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=translate("language_set", lang),
    )


async def handle_url_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle a plain text message, treating it as a possible video URL.

    Detects the platform via downloader.manager.detect_platform() and
    replies in the user's saved language. YouTube URLs are handed off to
    _handle_youtube_url() for the quality-selection flow; Instagram URLs
    to _handle_instagram_url() for download + delivery. Anything else
    gets the "unsupported link" reply.
    """
    user_id = update.effective_user.id
    lang = get_language(user_id)

    url_text = update.message.text
    platform = detect_platform(url_text)

    if platform == Platform.YOUTUBE:
        await _handle_youtube_url(update, context, url_text, lang)
        return

    if platform == Platform.INSTAGRAM:
        await _handle_instagram_url(update, context, url_text, lang)
        return

    await update.message.reply_text(translate("url.unsupported", lang))


def _video_sender(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> Callable[[str], Awaitable[None]]:
    """Build the `send_fn` deliver_video() expects: upload the file at
    `path` to `chat_id` as a streamable video.

    Platform-agnostic, so the YouTube flow can reuse it. The file is
    closed (the `with` block exits) before deliver_video() cleans up -
    this matters on Windows, where an open file can't be deleted.
    """

    async def send(path: str) -> None:
        with open(path, "rb") as video_file:
            await context.bot.send_video(
                chat_id=chat_id,
                video=video_file,
                supports_streaming=True,
                **_UPLOAD_TIMEOUTS,
            )

    return send


async def _handle_instagram_url(
    update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, lang: str
) -> None:
    """Download an Instagram video and send it back, then clean up.

    The download/send/cleanup sequence lives in
    services.video_service.deliver_video(); this handler only supplies
    the two callables and maps the returned outcome to a translated
    message. On success the video itself is the reply - no extra
    confirmation text is sent.
    """
    await update.message.reply_text(translate("instagram.downloading", lang))

    outcome = await deliver_video(
        lambda request_dir: download_instagram_video(url, request_dir),
        _video_sender(context, update.message.chat_id),
    )

    if outcome is DeliveryOutcome.DOWNLOAD_FAILED:
        await update.message.reply_text(translate("instagram.download_failed", lang))
    elif outcome is DeliveryOutcome.SEND_FAILED:
        await update.message.reply_text(translate("delivery.send_failed", lang))


async def _handle_youtube_url(
    update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, lang: str
) -> None:
    """Inspect a YouTube URL's real qualities and act on what's found.

    - Any previously pending selection for this user is dropped first,
      so a stale menu from an earlier URL can never be honored once a
      new URL has been sent (see handle_youtube_quality_selection's
      token check for the other half of this).
    - Extraction failure -> a translated error, nothing pending is set.
    - Exactly one usable quality -> auto-download it and say so
      explicitly (Rule 5's single-quality exception - never a one-item
      menu).
    - Multiple qualities -> store them under a fresh token in
      context.user_data and show a keyboard built from the real
      options.
    """
    context.user_data.pop(_PENDING_YOUTUBE_KEY, None)

    try:
        options = await asyncio.to_thread(get_available_qualities, url)
    except YouTubeExtractionError:
        logger.warning("YouTube extraction failed for %r", url, exc_info=True)
        await update.message.reply_text(translate("youtube.extraction_failed", lang))
        return

    if not options:
        logger.warning("YouTube URL %r had no usable video formats", url)
        await update.message.reply_text(translate("youtube.extraction_failed", lang))
        return

    if len(options) == 1:
        await _download_youtube_and_report(
            update.message.reply_text,
            context,
            update.message.chat_id,
            url,
            options[0],
            lang,
            single_quality=True,
        )
        return

    token = secrets.token_urlsafe(8)
    context.user_data[_PENDING_YOUTUBE_KEY] = {
        "token": token,
        "url": url,
        "options": options,
    }
    await update.message.reply_text(
        translate("youtube.choose_quality", lang),
        reply_markup=youtube_quality_keyboard(token, options),
    )


async def handle_youtube_quality_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle a tap on one of the YouTube quality-selection buttons.

    callback_data carries only the pending selection's token and the
    tapped option's index (see bot/keyboards.py) - never the URL or a
    raw yt-dlp format id. The token is validated against whatever is
    currently stored in context.user_data before anything is trusted:

    - No pending entry at all (bot restarted, or nothing was ever
      pending for this user) -> expired-selection message.
    - Pending entry exists but its token doesn't match (a newer URL
      superseded it, or this is a stale button from an old menu) ->
      expired-selection message.
    - Token matches -> the pending entry is removed immediately, before
      the download starts, so a double tap on the same button (the
      second update arriving before or after the first download
      finishes) always finds nothing pending and gets the expired
      message instead of starting a second download.
    """
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = get_language(user_id)

    async def send(text: str) -> None:
        await context.bot.send_message(chat_id=query.message.chat_id, text=text)

    payload = query.data.removeprefix(YOUTUBE_QUALITY_CALLBACK_PREFIX)
    token, _, index_text = payload.partition(":")

    pending = context.user_data.get(_PENDING_YOUTUBE_KEY)
    if pending is None or pending["token"] != token:
        await send(translate("youtube.selection_expired", lang))
        return

    options = pending["options"]
    try:
        index = int(index_text)
        option = options[index]
    except (ValueError, IndexError):
        # Malformed or out-of-range index shouldn't happen from our own
        # keyboard, but a stale/tampered callback_data is still just an
        # invalid selection, not a crash.
        del context.user_data[_PENDING_YOUTUBE_KEY]
        await send(translate("youtube.selection_expired", lang))
        return

    # Consume before downloading (see docstring) so a double tap can
    # never reach this point twice.
    del context.user_data[_PENDING_YOUTUBE_KEY]

    await _download_youtube_and_report(
        send,
        context,
        query.message.chat_id,
        pending["url"],
        option,
        lang,
        single_quality=False,
    )


async def _download_youtube_and_report(
    send: SendMessage,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    url: str,
    option: QualityOption,
    lang: str,
    *,
    single_quality: bool,
) -> None:
    """Download `option` for `url`, send the video, and report the outcome.

    Shared by the auto-download (single-quality) and user-selected
    (multi-quality) paths so the "announce -> download + send + clean up
    -> confirm or report failure" sequence is defined in exactly one
    place. `send` posts text messages (reply_text on the message path, a
    send_message wrapper on the callback path); the video itself is sent
    to `chat_id` via the same _video_sender() Instagram uses. The
    download/send/cleanup mechanics live in
    services.video_service.deliver_video().
    """
    if single_quality:
        await send(translate("youtube.single_quality_auto", lang, quality=option.label))
    else:
        await send(translate("youtube.download_started", lang, quality=option.label))

    outcome = await deliver_video(
        lambda request_dir: download_youtube_video(url, option, request_dir),
        _video_sender(context, chat_id),
    )

    if outcome is DeliveryOutcome.DOWNLOAD_FAILED:
        await send(translate("youtube.download_failed", lang))
    elif outcome is DeliveryOutcome.SEND_FAILED:
        await send(translate("delivery.send_failed", lang))
    else:
        await send(translate("youtube.download_complete", lang, quality=option.label))


def register_handlers(application: Application) -> None:
    """Register all handlers defined in this module on `application`."""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        CallbackQueryHandler(
            handle_language_selection, pattern=f"^{LANGUAGE_CALLBACK_PREFIX}"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_youtube_quality_selection,
            pattern=f"^{YOUTUBE_QUALITY_CALLBACK_PREFIX}",
        )
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url_message)
    )