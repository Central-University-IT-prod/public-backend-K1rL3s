import time
from typing import Any, Awaitable, Callable, cast

from aiogram import BaseMiddleware
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.types import TelegramObject, Update
from structlog.typing import FilteringBoundLogger

HANDLED_STR = ["Handled", "Unhandled"]


class StructLoggingMiddleware(BaseMiddleware):
    def __init__(self, logger: FilteringBoundLogger):
        self.logger = logger

    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        event = cast(Update, event)
        _started_processing_at = time.time()
        logger = self.logger.bind(update_id=event.update_id)
        if event.message:
            message = event.message
            logger = logger.bind(
                message_id=message.message_id,
                chat_type=message.chat.type,
                chat_id=message.chat.id,
            )
            if message.from_user is not None:
                logger = logger.bind(user_id=message.from_user.id)
            if message.text:
                logger = logger.bind(text=message.text, entities=message.entities)
            if message.video:
                logger = logger.bind(
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    video_id=message.video.file_id,
                    video_unique_id=message.video.file_unique_id,
                )
            if message.photo:
                logger = logger.bind(
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    photo_id=message.photo[-1].file_id,
                    photo_unique_id=message.photo[-1].file_unique_id,
                )
            logger.debug("Received message")
        elif event.callback_query:
            c = event.callback_query
            logger = logger.bind(
                callback_query_id=c.id,
                callback_data=c.data,
                user_id=c.from_user.id,
                inline_message_id=c.inline_message_id,
                chat_instance=c.chat_instance,
            )
            if c.message is not None:
                logger = logger.bind(
                    message_id=c.message.message_id,
                    chat_type=c.message.chat.type,
                    chat_id=c.message.chat.id,
                )
            logger.debug("Received callback query")
        elif event.inline_query:
            query = event.inline_query
            logger = logger.bind(
                query_id=query.id,
                user_id=query.from_user.id,
                query=query.query,
                offset=query.offset,
                chat_type=query.chat_type,
                location=query.location,
            )
            logger.debug("Received inline query")
        elif event.my_chat_member:
            upd = event.my_chat_member
            logger = self.logger.bind(
                user_id=upd.from_user.id,
                chat_id=upd.chat.id,
                old_state=upd.old_chat_member,
                new_state=upd.new_chat_member,
            )
            logger.debug("Received my chat member update")
        elif event.chat_member:
            upd = event.chat_member
            logger = logger.bind(
                user_id=upd.from_user.id,
                chat_id=upd.chat.id,
                old_state=upd.old_chat_member,
                new_state=upd.new_chat_member,
            )
            logger.debug("Received chat member update")

        response = await handler(event, data)
        handled = HANDLED_STR[response is UNHANDLED]

        logger = logger.bind(
            process_result=True,
            spent_time_ms=round((time.time() - _started_processing_at) * 10000) / 10,
        )
        if event.message:
            logger.info("%s message", handled)
        elif event.callback_query:
            logger.info("%s callback query", handled)
        elif event.inline_query:
            logger.info("%s inline query", handled)
        elif event.my_chat_member:
            logger.info("%s my chat member update", handled)
        elif event.chat_member:
            logger.info("%s chat member update", handled)

        return response
