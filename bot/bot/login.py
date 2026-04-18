from bot.bot import *


async def _to_the_select_lang(update: Update, context: CustomContext):
    await update_message_reply_text(
        update,
        "Bot tilini tanlang\n\nВыберите язык бота",
        reply_markup= await select_lang_keyboard()
    )
    return SELECT_LANG


async def get_lang(update: Update, context: CustomContext):
    text: str = update.effective_message.text or ""
    if "UZ" in text:
        lang = 0
    elif "RU" in text:
        lang = 1
    else:
        return await _to_the_select_lang(update, context)


    obj: Bot_user = await get_object_by_user_id(user_id=update.effective_chat.id)
    obj.lang = lang
    await obj.asave()

    return await main_menu(update, context)


async def start(update: Update, context: CustomContext):
    return await _to_the_select_lang(update, context)