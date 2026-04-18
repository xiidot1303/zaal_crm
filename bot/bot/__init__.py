from bot import *
from telegram import Update
from telegram.ext import ContextTypes, CallbackContext, ExtBot, Application
from dataclasses import dataclass
from asgiref.sync import sync_to_async
from bot.utils import *
from bot.utils.bot_functions import *
from bot.utils.keyboards import *
from bot.services import *
from bot.resources.conversationList import *
from app.resources.classes import *
from bot.services.string_service import *
from config import WEBAPP_URL
from telegram import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo


async def is_message_back(update: Update):
    if update.effective_message.text == Strings(update.effective_user.id).back:
        return True
    else:
        return False


async def main_menu(update: Update, context: CustomContext):
    bot = context.bot
    expense_url = f"{WEBAPP_URL.rstrip('/')}/expense/create" if WEBAPP_URL else None
    income_url = f"{WEBAPP_URL.rstrip('/')}/income/create" if WEBAPP_URL else None
    room_management_url = f"{WEBAPP_URL.rstrip('/')}/room/management" if WEBAPP_URL else None
    print(  f"Expense URL: {expense_url}")  # Debug print to check the URL
    print(  f"Income URL: {income_url}")  # Debug print to check the URL
    print(  f"Room Management URL: {room_management_url}")  # Debug print to check the URL
    buttons = [[context.words.create_expense], [context.words.create_income], [context.words.room_management]]

    if expense_url and income_url and room_management_url:
        buttons = [
            [KeyboardButton(text=context.words.create_expense, web_app=WebAppInfo(url=expense_url))],
            [KeyboardButton(text=context.words.create_income, web_app=WebAppInfo(url=income_url))],
            [KeyboardButton(text=context.words.room_management, web_app=WebAppInfo(url=room_management_url))]
        ]

    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    await bot.send_message(
        update.effective_message.chat_id,
        context.words.main_menu,
        reply_markup=reply_markup,
    )
    context.application.create_task(check_username(update))

    return ConversationHandler.END
