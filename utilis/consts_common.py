from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, \
    InlineKeyboardButton, InlineKeyboardMarkup


# BUTTONS | KB | TEXT
text_main_menu = '▫ *M A I N | M E N U* ▫️'
back_mes = '🔙НАЗАД'

def back_mes_but(callback_data): return dict(text=back_mes, callback_data=callback_data)

visiting_system_kb = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton('✈️ВОЙТИ✈️', callback_data='visiting_aut'),
    InlineKeyboardButton('🚀ЗАРЕГИСТРИРОВАТЬСЯ🚀', callback_data='visiting_reg'))

main_menu_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(
    KeyboardButton('✔️\nDAYPLAN️'),
    KeyboardButton('👤PROFILE👤'),
    KeyboardButton('SETTINGS\n🛠️️'))


# NUMBERS
special_numbers_circle = ('𝟘', '𝟙', '𝟚', '𝟛', '𝟜', '𝟝', '𝟞', '𝟟', '𝟠', '𝟡')
dict_special_numbers_circle = dict(zip((str(num) for num in range(10)),
                                       special_numbers_circle))

dict_with_bold_nums = dict(zip((str(num) for num in range(10)),
                               ('𝟬', '𝟭', '𝟮', '𝟯', '𝟰', '𝟱', '𝟲', '𝟳', '𝟴', '𝟵')))

dict_with_circle = dict(zip((str(num) for num in range(1, 21)),
                            ('➊', '➋', '➌', '➍', '➎', '➏', '➐', '➑', '➒', '❿',
                             '⓫', '⓬', '⓭', '⓮', '⓯', '⓰', '⓱', '⓲', '⓳', '⓴')))

nums_and_emoji = \
    {
    "0": '0️⃣',
    "1": '1️⃣',
    "2": '2️⃣',
    "3": '3️⃣',
    "4": '4️⃣',
    "5": '5️⃣',
    "6": '6️⃣',
    "7": '7️⃣',
    "8": '8️⃣',
    "9": '9️⃣'
}

dict_with_small_numbers = \
    {
        "0": '₀',
        "1": '₁',
        "2": '₂',
        "3": '₃',
        "4": '₄',
        "5": '₅',
        "6": '₆',
        "7": '₇',
        "8": '₈',
        "9": '₉'
    }


# EMOJI
emoji_work_dp_list = ('⭐', '❄️', '❌', '🌑')
bad_symbols_for_emoji_name = ('-', '`', '~', "'", '"', '’')


# DIFFERENT
short_name_week_days = ('ПН', 'ВТ', 'СР', "ЧТ", "ПТ", "СБ", "ВС")
all_content_types = ('text', 'sticker', 'document', 'video', 'animation', 'photo',
                     'voice', 'audio', 'contact', 'mode', 'dice', 'any', 'connected_website',
                     'delete_chat_photo', 'game', 'group_chat_created', 'invoice',
                     'left_chat_member', 'location', 'migrate_from_chat_id', 'migrate_to_chat_id',
                     'new_chat_members', 'new_chat_photo', 'new_chat_title', 'passport_data',
                     'pinned_message', 'poll', 'successful_payment', 'UNKNOWN', 'VENUE', 'VIDEO_NOTE')

use_colours = ['FFB718', '18FF34', '26D9D1', '26A9D9', 'D97926',
                   'D374EC', '95779C', 'C4AFCA', 'D1AFD9', 'F7EAFB',
                   'D947FF', '478BFF', '47FFF6', '47FF83', '58FF47',
                   'BAFF47', 'FFD347', 'FF8547', 'FF474F', 'FF476C',
                   'FF47A7', 'FF47FC', '8F8F8F', '9EB4B7', '9EB79F',
                   'B0B79E', 'B7AD9E', 'B79EA8', '37B368', '66B337',
                   '90B337', 'B38437', 'DB921F', 'CC7722', '4CBB17',
                   '0EE1DC', 'EFD334', '0BDA51', '54FF9F', '1FAEE9',
                   '7B68EE', 'DF73FF', 'FC74FD', 'ED3CCA', 'F64A8A',
                   'EFA94A', 'D1E231', '62743E', '785840', '6D3F5B']
