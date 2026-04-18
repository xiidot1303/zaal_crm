import asyncio
from dataclasses import dataclass
from telegram.ext import (
    Application,
    CallbackContext,
    CommandHandler,
    ContextTypes,
    ExtBot,
    TypeHandler,
    PicklePersistence
)
from telegram.request import HTTPXRequest
from telegram import Update
from config import BOT_API_TOKEN, WEBHOOK_URL
from bot.control.handlers import handlers
from bot.bot.main import error_handler
from bot import *
from asgiref.sync import async_to_sync

request = HTTPXRequest(
    connect_timeout=30,
    read_timeout=30,
    write_timeout=30,
    connection_pool_size=20,
    pool_timeout=30
)
# persistence = PicklePersistence(filepath="persistencebot")
persistence = RedisPersistence()
context_types = ContextTypes(context=CustomContext)
application = Application.builder().token(
    BOT_API_TOKEN).persistence(persistence).context_types(context_types).request(request).build()

# add handlers
for handler in handlers[::-1]:
    application.add_handler(handler)

application.add_error_handler(error_handler)


# webhook functions

async def set_webhook():
    await application.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


async def delete_webhook():
    await application.bot.delete_webhook()
