from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
#
from utilis.consts_common import back_mes, short_name_week_days, dict_with_bold_nums
from utilis.main_common import big_replacing


# BASIS
week_colors = ['#FF476C', '#4CBB17', '#DB921F', '#9EB4B7', '#0EE1DC', '#FC74FD', '#EFD334']


# KB
common_settings_kb = InlineKeyboardMarkup().\
    add(
    InlineKeyboardButton('🕒ВРЕМЯ🕘', callback_data='time_dp')).\
    row(
    InlineKeyboardButton('📋СОСТАВ📋', callback_data='compound_dp'),
    InlineKeyboardButton('🗂СТАТИСТИКА🗂', callback_data='statistics_dp')).add(
    InlineKeyboardButton(back_mes, callback_data='back_main_menu'))

time_dp_sett_kb = InlineKeyboardMarkup().\
    row(
    InlineKeyboardButton('⌚РАБОЧИЕ ЧАСЫ⌚', callback_data='edit_work_hour'),
    InlineKeyboardButton('🌐ЧАСОВОЙ ПОЯС🌐', callback_data='edit_timezone')).\
    add(
    InlineKeyboardButton(back_mes, callback_data='to_back_common_settings'))

work_with_timezone_kb = \
    InlineKeyboardMarkup(row_width=2).add(
                                        InlineKeyboardButton('➕', callback_data='plus_to_edit_timezone'),
                                        InlineKeyboardButton('➖', callback_data='minus_to_edit_timezone'),
                                        InlineKeyboardButton(back_mes, callback_data='time_dp'))

remake_work_hour_begin = \
    InlineKeyboardMarkup(row_width=2).add(
                                        InlineKeyboardButton('➕', callback_data='plus_to_begin_hour'),
                                        InlineKeyboardButton('➖', callback_data='minus_to_begin_hour'),
                                        InlineKeyboardButton(back_mes, callback_data='time_dp'),
                                        InlineKeyboardButton('➡️', callback_data='to_edit_end_hour'))

remake_work_hour_end = \
    InlineKeyboardMarkup(row_width=2).add(
                                        InlineKeyboardButton('➕', callback_data='plus_to_end_hour'),
                                        InlineKeyboardButton('➖', callback_data='minus_to_end_hour'),
                                        InlineKeyboardButton('⬅️️', callback_data='edit_work_hour'))


sett_statistics_kb = InlineKeyboardMarkup().add(
    InlineKeyboardButton('⌛ВРЕМЯ ВЫПОЛНЕНИЯ⌛', callback_data='get_average_time_work')).row(
    InlineKeyboardButton('✔️ПОЛНЫЕ ДНИ✔️', callback_data='get_full_days'),
    InlineKeyboardButton('✖️НЕПОЛНЫЕ ДНИ✖️', callback_data='get_not_full_days'),).add(
    InlineKeyboardButton(back_mes, callback_data='to_back_common_settings'))

dict_names_graphs_sett = \
    {'get_full_days': 'ПОЛНЫЕ ДНИ',
     'get_not_full_days': 'НЕПОЛНЫЕ ДНИ',
     'get_average_time_work': 'ВРЕМЯ ВЫПОЛНЕНИЯ'}

sett_compound_kb = InlineKeyboardMarkup().add(
    InlineKeyboardButton('⬆️РАСПОЛОЖЕНИЕ⬇️', callback_data='locating_elements_dp_sett')).row(
    InlineKeyboardButton('🌕ЭВЕНТЫ🌑️', callback_data='events_sett'),
    InlineKeyboardButton('☀️БЛОКИ❄️', callback_data='blocks_sett'),).add(
    InlineKeyboardButton(back_mes, callback_data='to_back_common_settings'))

choose_remake_week_day_kb = InlineKeyboardMarkup().row(
    *[InlineKeyboardButton(f'{one_week_day}', callback_data=f'{index_week}_choose_week_day')
      for index_week, one_week_day in enumerate(short_name_week_days)]).add(
    InlineKeyboardButton(back_mes, callback_data='compound_dp'))

dict_full_name_week = \
    {0: 'ПОНЕДЕЛЬНИК',
     1: "ВТОРНИК",
     2: "СРЕДА",
     3: "ЧЕТВЕРГ",
     4: "ПЯТНИЦА",
     5: "СУББОТА",
     6: "ВОСКРЕСЕНЬЕ"}

dict_full_name_week_another = \
    {0: 'ПОНЕДЕЛЬНИКА',
     1: "ВТОРНИКА",
     2: "СРЕДЫ",
     3: "ЧЕТВЕРГА",
     4: "ПЯТНИЦЫ",
     5: "СУББОТЫ",
     6: "ВОСКРЕСЕНЬЯ"}

def get_new_event_time_work_kb(time_work, add_callback='sett_time'):

    time_work_kb = \
        InlineKeyboardMarkup().row(
            InlineKeyboardButton('↓25', callback_data=f'{add_callback}-25'),
            InlineKeyboardButton('↓5', callback_data=f'{add_callback}-5'),
            InlineKeyboardButton(big_replacing(time_work, your_dict=dict_with_bold_nums),
                                 callback_data='NONE'),
            InlineKeyboardButton('5↑', callback_data=f'{add_callback}+5'),
            InlineKeyboardButton('25↑', callback_data=f'{add_callback}+25'))

    # у нового эвента задаём time_work
    if add_callback == 'sett_time':
        time_work_kb.add(
            InlineKeyboardButton('⬅️', callback_data=f'to_new_event_describe_el'),
            InlineKeyboardButton('➡️', callback_data='end_process_adding_event'))

    return time_work_kb


edit_event_sett_kb = \
    InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton('НАЗВАНИЕ', callback_data='edit_name_event'),
        InlineKeyboardButton('КРАТКОЕ ОПИСАНИЕ', callback_data='edit_short_description_event'),
        InlineKeyboardButton('ПОЛНОЦЕННОЕ ОПИСАНИЕ', callback_data='edit_long_description_event'),
        InlineKeyboardButton('ВРЕМЯ ВЫПОЛНЕНИЯ', callback_data='edit_time_work'),
        InlineKeyboardButton(back_mes, callback_data='back_to_one_event'))

edit_block_sett_kb = \
    InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton('НАЗВАНИЕ', callback_data='edit_name_block'),
        InlineKeyboardButton('ЭМОДЖИ', callback_data='edit_emoji_block'),
        InlineKeyboardButton('ПОЛНОЦЕННОЕ ОПИСАНИЕ', callback_data='edit_long_description_block'),
        InlineKeyboardButton('РАБОЧИЕ ДНИ', callback_data='edit_work_days_block'),
        InlineKeyboardButton(back_mes, callback_data='back_to_one_block'))
