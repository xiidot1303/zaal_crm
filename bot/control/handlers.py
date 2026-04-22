from bot import *
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    InlineQueryHandler,
    TypeHandler,
    ConversationHandler
)

from bot.resources.conversationList import *

from bot.bot import (
    main, login
)

exceptions_for_filter_text = (~filters.COMMAND) & (~filters.Text(Strings.main_menu))

login_handler = ConversationHandler(
    entry_points=[CommandHandler("start", main.start)],
    states={
        SELECT_LANG: [
            MessageHandler(filters.TEXT & exceptions_for_filter_text, login.get_lang),
        ],
        MAIN_MENU: [
            MessageHandler(filters.Text(Strings.main_menu), main.main_menu),
            MessageHandler(filters.Text(Strings.create_expense), main.open_create_expense),
        ],
    },
    fallbacks=[
        CommandHandler("start", login.start)
    ],
    name="login",
    # persistent=True
)


handlers = [
    login_handler,
    MessageHandler(filters.StatusUpdate.WEB_APP_DATA, main.web_app_data_handler),
    TypeHandler(type=NewsletterUpdate, callback=main.newsletter_update)
]
