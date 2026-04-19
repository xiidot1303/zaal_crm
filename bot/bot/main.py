from bot.bot import *
import json
import logging
import traceback
import html
from django.db import close_old_connections
from telegram.error import TimedOut
import asyncio
from app.models import Staff, Expense, Income


async def start(update: Update, context: CustomContext):
    if await is_group(update):
        return

    if await Staff.objects.filter(
            bot_user__user_id=update.effective_chat.id, is_active=True
        ).aexists():
        # main menu
        return await main_menu(update, context)

    start_msg = await get_start_msg(update.message.text)
    if start_msg:
        staff: Staff | None = await Staff.objects.filter(invite_link__icontains=start_msg).afirst()
        if staff:
            bot_user, created = await Bot_user.objects.aget_or_create(
                user_id=update.effective_chat.id,
                defaults={
                    "lang": 1,
                    "name": update.effective_user.first_name,
                    "firstname": update.effective_user.first_name
                }
            )
            staff.bot_user = bot_user
            await staff.asave(update_fields=["bot_user"])

            # send message to select lang
            hello_text = Strings.hello
            await update_message_reply_text(
                update,
                hello_text,
                reply_markup= await select_lang_keyboard()
            )
            return SELECT_LANG

    # User is restricted to use bot
    text = "Вам отказано в доступе"
    await update.message.reply_text(text)
    return


async def newsletter_update(update: NewsletterUpdate, context: CustomContext):
    bot = context.bot
    while True:
        try:
            if not (update.photo or update.video or update.document or update.location):
                # send text message
                message = await bot.send_message(
                    chat_id=update.user_id,
                    text=update.text,
                    reply_markup=update.reply_markup,
                    parse_mode=ParseMode.HTML
                )

            if update.photo:
                # send photo
                message = await bot.send_photo(
                    update.user_id,
                    update.photo,
                    caption=update.text,
                    reply_markup=update.reply_markup,
                    parse_mode=ParseMode.HTML,
                )
            if update.video:
                # send video
                message = await bot.send_video(
                    update.user_id,
                    update.video,
                    caption=update.text,
                    reply_markup=update.reply_markup,
                    parse_mode=ParseMode.HTML,
                )
            if update.document:
                # send document
                message = await bot.send_document(
                    update.user_id,
                    update.document,
                    caption=update.text,
                    reply_markup=update.reply_markup,
                    parse_mode=ParseMode.HTML,
                )
            if update.location:
                # send location
                message = await bot.send_location(
                    chat_id=update.user_id,
                    latitude=update.location.get('latitude'),
                    longitude=update.location.get('longitude')
                )
            if update.pin_message:
                await bot.pin_chat_message(chat_id=update.user_id, message_id=message.message_id)

            break
        except TimedOut:
            await asyncio.sleep(0.5)
            continue


async def open_create_expense(update: Update, context: CustomContext):
    return await main_menu(update, context)


async def web_app_data_handler(update: Update, context: CustomContext):
    web_app_data = getattr(update.effective_message, 'web_app_data', None)
    if not web_app_data:
        return

    try:
        payload = json.loads(web_app_data.data)
    except Exception:
        return

    # Handle expense creation
    if payload.get('action') == 'expense_created':
        expense_id = payload.get('expense_id')
        if expense_id:
            try:
                expense = await Expense.objects.select_related('account').aget(pk=expense_id)
                text = (
                    f"{context.words.expense_created_info}\n"
                    f"{context.words.expense_title}: {expense.title}\n"
                    f"{context.words.expense_account}: {expense.account.title}\n"
                    f"{context.words.expense_amount}: {expense.amount}\n"
                    f"{context.words.expense_description}: {expense.description or '-'}"
                )
            except Expense.DoesNotExist:
                text = payload.get('message', context.words.expense_created_default)
        else:
            text = payload.get('message', context.words.expense_created_default)

    # Handle income creation
    elif payload.get('action') == 'income_created':
        income_id = payload.get('income_id')
        if income_id:
            try:
                income = await Income.objects.select_related('account', 'accommondation').aget(pk=income_id)
                type_display = dict(Income.TYPE_CHOICES).get(income.type, income.type)
                text = (
                    f"{context.words.income_created_info}\n"
                    f"{context.words.income_type}: {type_display}\n"
                    f"{context.words.income_account}: {income.account.title}\n"
                    f"{context.words.income_amount}: {income.amount}\n"
                    f"{context.words.income_description}: {income.description or '-'}"
                )
            except Income.DoesNotExist:
                text = payload.get('message', context.words.income_created_default)
        else:
            text = payload.get('message', context.words.income_created_default)

    # Handle room status update
    elif payload.get('action') == 'room_status_updated':
        room_id = payload.get('room_id')
        is_free = payload.get('is_free')
        if room_id is not None:
            try:
                from app.models import Room
                room = await Room.objects.aget(pk=room_id)
                status_text = context.words.room_free if is_free else context.words.room_occupied
                text = f"{context.words.room_status_updated}\n{context.words.room_number}: {room.number}\n{context.words.room_status}: {status_text}"
            except Room.DoesNotExist:
                text = payload.get('message', 'Room status updated')
        else:
            text = payload.get('message', 'Room status updated')
    else:
        return

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
    )


###############################################################################################
###############################################################################################
###############################################################################################
logger = logging.getLogger(__name__)


async def error_handler(update: Update, context: CustomContext):
    # restart db connection if error is "connection already closed"
    if "connection already closed" in str(context.error):
        await sync_to_async(close_old_connections)()
        return


    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error("Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
    )
    error_message = f"{html.escape(tb_string)}"

    # Finally, send the message
    try:
        await context.bot.send_message(
            chat_id=206261493, text=message, parse_mode=ParseMode.HTML
        )
        for i in range(0, len(error_message), 4000):
            await context.bot.send_message(
                chat_id=206261493, text=f"<pre>{error_message[i:i+4000]}</pre>", parse_mode=ParseMode.HTML
            )
    except Exception as ex:
        print(ex)
