from bot.utils.bot_functions import *

async def get_callback_query_data(update):
    data = await update.data
    *args, result = str(data).split('_')
    return result

async def get_location_coordinates(l):
    return l['latitude'], l['longitude']

async def split_text_and_text_id(msg):
    return msg.split('<>?')

async def get_last_msg_and_markup(context):
    return await context.user_data['last_msg'], await context.user_data['last_markup'] if 'last_markup' in context.user_data else None

async def remove_inline_keyboards_from_last_msg(update, context):
    try:
        last_msg, markup = await get_last_msg_and_markup(context)
        await bot_edit_message_reply_markup(update, context, last_msg.message_id)
        return True
    except:
        return None

async def is_group(update):
    if update.message.chat.type == 'group' or update.message.chat.type == 'supergroup':
        return True
    return False

async def save_and_get_photo(update, context):
    bot = context.bot
    photo_id = await bot.getFile(update.message.photo[-1].file_id)
    *args, file_name = str(photo_id.file_path).split('/')
    d_photo = await photo_id.download('files/photos/{}'.format(file_name))
    return str(d_photo).replace('files/', '')

async def set_last_msg_and_markup(context, msg, markup=None):
    context.user_data['last_msg'] = msg
    context.user_data['last_markup'] = markup


async def get_start_msg(msg):
    if msg != '/start':
        r = msg.split(' ')[1]
    else:
        r = None
    return r

def format_amount(value) -> str:
    """Format a money amount with space thousand separators: 6120000.00 -> '6 120 000'.
    Keeps two decimals only when they are non-zero: 1500.5 -> '1 500.50'."""
    from decimal import Decimal
    value = Decimal(str(value))
    if value == value.to_integral_value():
        return f"{int(value):,}".replace(",", " ")
    return f"{value:,.2f}".replace(",", " ")
