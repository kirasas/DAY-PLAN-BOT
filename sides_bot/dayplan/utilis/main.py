from collections import OrderedDict
from num2words import num2words
import xlsxwriter
import excel2img
import datetime
import sqlite3
import random
import math
import ast
#
from aiogram.types import ParseMode, InputFile, InputMediaPhoto
#
from utilis.apies import name_main_db
from utilis.consts_common import emoji_work_dp_list, dict_with_bold_nums, back_mes, \
    use_colours
from utilis.main_common import big_replacing, get_datetime_from_str, save_main_id_message, \
    get_common_data, save_common_data, message_no_data, get_main_id_message


# WORK WITH DB
conn = sqlite3.connect(f'{name_main_db}.db', check_same_thread=False)
cursor = conn.cursor()


def create_huge_list(cursor_login, locating_elements):
    # генерируем huge_list
    cursor_login.execute("""SELECT code_element, 
                            name_dp, description_dp, 
                            its_code_block, time_of_doing 
                            FROM classification_of_events""")
    values_huge_list = cursor_login.fetchall()

    # создаём dict: {block_code: emoji}
    cursor_login.execute("""SELECT code_element, block_emoji FROM classification_of_blocks""")
    values_blocks_and_its_emoji = dict(cursor_login.fetchall())

    huge_list = \
        [
            [(name_elem, description_elem), values_blocks_and_its_emoji.get(code_block), time_work, one_elem_id]
            for one_basis_id in locating_elements
            for one_elem_id, name_elem, description_elem, code_block, time_work in values_huge_list
            if one_basis_id == one_elem_id
        ]
    return huge_list


def create_data_for_dp(user_id, username):
    # получаем логин & id пользователя
    login_user, bot_id = get_common_data(user_id, cursor,
                                         'login_user', 'bot_id')

    # подключаемся к именованной БД пользователя
    conn_login = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db')
    cursor_login = conn_login.cursor()

    # находим расположение элементов пользователя в его БД
    week_day_now = datetime.datetime.weekday(datetime.datetime.now())
    cursor_login.execute(f'SELECT week_day_{week_day_now} FROM hierarchy_day_plans')
    locating_elements = cursor_login.fetchone()

    # проверяем: есть ли у пользователя вообще какой-либо day plan
    if locating_elements:

        # проверяем: есть ли у пользователя данный день недели
        if locating_elements[0]:

            locating_elements = ast.literal_eval(locating_elements[0])
            huge_list = create_huge_list(cursor_login, locating_elements)

            # генерируем block_names_dict
            cursor_login.execute('SELECT block_emoji, name_dp FROM classification_of_blocks')
            values_for_block_names = cursor_login.fetchall()

            unique_emoji = tuple(OrderedDict.fromkeys(one_elem[1] for one_elem in huge_list if one_elem[1]))
            block_names_dict = \
                dict((one_emoji, name_emoji)
                     for one_emoji in unique_emoji
                     for (block_emoji, name_emoji) in values_for_block_names if one_emoji == block_emoji)

            # общее время выполнение
            all_time_work = sum([one_elem[2] for one_elem in huge_list if one_elem[2] is not None])

            # количество уже ранее завершённых ДП
            done_day_plans = len(cursor_login.execute('SELECT * FROM history_working').fetchall())

            # выбор цветов для блоков: {emoji: random_colour]
            block_colours_dict = dict(zip(unique_emoji, random.sample(use_colours, len(unique_emoji))))

            # получаем текст для сообщения
            text_under_photo = f'<b>Ваш план дня на сегодня, @{username}:</b>\n ' \
                               f'➖➖➖➖➖➖➖➖➖➖➖➖➖\n' \
                               f'☀️<b>Всего блоков:</b> <code>{len(unique_emoji)}</code>\n' \
                               f'🌕<b>Всего эвентов:</b> <code>{len(huge_list)}</code>\n' \
                               f'⏳<b>Время выполнения:</b> <code>{all_time_work}</code>\n' \
                               f'➖➖➖➖➖➖➖➖➖➖➖➖➖\n' \
                               f'📌<b>Это ваш {num2words(done_day_plans + 1, to="ordinal", lang="ru")} план дня</b>'

            return [huge_list, login_user, bot_id, str(get_user_time_now(user_id=user_id)), block_names_dict,
                    block_colours_dict, all_time_work, text_under_photo]


def create_dp_in_excel(huge_list, block_names_dict, block_colours_dict, bot_id, all_time_work):
    # данные для вставки в таблицу: [[name_elem, time_work], colour_block]
    need_values = \
        [
            [(one_elem[0][0], 0 if not one_elem[2] else one_elem[2]), block_colours_dict.get(one_elem[1])]
            for one_elem in huge_list
        ]

    # подключаемся к рабочей таблице
    file_name, work_sheet_name = 'curDP', 'one_see'
    user_workbook = xlsxwriter.Workbook(f'users_bot/{bot_id}_log/for_excel_dp/{file_name}.xlsx')
    user_worksheet = user_workbook.add_worksheet(work_sheet_name)

    # ширина столбцов
    user_worksheet.set_column_pixels('B:B', 215)
    user_worksheet.set_column_pixels('D:D', 320)
    # если в названии больше 15 символов, увеличиваем стандарт
    max_len_name_event = max([len(str(one_elem[0][0])) for one_elem in huge_list])
    width_column_for_events = 300 if max_len_name_event < 15 else round(20 * max_len_name_event)
    user_worksheet.set_column_pixels('C:C', width_column_for_events)

    # заглавия
    for_names_cols_format = \
        user_workbook.add_format(
            {'font_name': 'Times New Roman',
             'font_size': 18, 'font_color': 'white',
             'bold': True, 'align': 'center',
             'bg_color': 'black',
             'border': 5, 'border_color': 'black'})
    user_worksheet.write_row('B1', ('НОМЕР', 'ЭВЕНТ', 'ВРЕМЯ ВЫПОЛНЕНИЯ'), for_names_cols_format)

    # формат для отдельный эвентов
    def get_format_separate_events(bl_colour='FFFFFF',
                                   font_name='Arial Black', size=16,
                                   bool_bold=True, bool_italic=True,
                                   align='center',
                                   border_one=0, border_two=0,
                                   border_three=0, border_four=0):
        return user_workbook.add_format(
            {'font_name': f'{font_name}',
             'font_size': size, 'font_color': 'black',
             'bold': bool_bold, 'italic': bool_italic,
             'align': f'{align}', 'bg_color': f'#{bl_colour}',
             'border_color': 'black', 'bottom': border_one,
             'top': border_two, 'left': border_three, 'right': border_four})

    # заполняем таблицу эвентов
    index_cell = 0
    last_colour_block = need_values[0][1]
    for index_cell, [(name_event, time_work_event), block_colour] in enumerate(need_values, start=2):

        # если последний эвент | смена блока
        if len(need_values) == index_cell - 1:
            condition_bottom_border = 5
        elif need_values[index_cell - 1][1] != last_colour_block:
            last_colour_block = need_values[index_cell - 1][1]
            condition_bottom_border = 5
        else:
            condition_bottom_border = 0

        # НОМЕР
        user_worksheet.write(f'B{index_cell}', index_cell - 1,
                             get_format_separate_events(block_colour, font_name='Wide Latin',
                                                        size=18, bool_italic=False,
                                                        border_three=5,
                                                        border_one=condition_bottom_border))

        # ЭВЕНТ
        user_worksheet.write(f'C{index_cell}', name_event,
                             get_format_separate_events(block_colour,
                                                        border_one=condition_bottom_border))

        # ВРЕМЯ ВЫПОЛНЕНИЯ
        user_worksheet.write(f'D{index_cell}', time_work_event,
                             get_format_separate_events(block_colour, font_name='Bauhaus 93',
                                                        size=18, bool_italic=False,
                                                        bool_bold=False, border_four=5,
                                                        border_one=condition_bottom_border))

    else:
        # подсчитаем общее время с помощью формулы
        user_worksheet.write(f'C{index_cell + 1}', 'ИТОГО:',
                             get_format_separate_events(font_name='Times New Roman',
                                                        size=20, bool_italic=False,
                                                        align='right'))

        user_worksheet.write(f'D{index_cell + 1}', f'{all_time_work} MINS',
                             get_format_separate_events(font_name='Stencil',
                                                        size=22, bool_italic=False))

    # отступы потенциальной диаграммы_2 от диаграммы_1
    x_offset, y_offset = 0, 0

    # определяем широту | длину диаграм
    if len(need_values) > 15:
        # ширина постоянна, с кол-вом эвентов изменяется длина
        width_diagrams = (215 + width_column_for_events + 320) / 2 + 31
        height_diagrams = y_offset = (40 + len(need_values) * 20) / 2 \
            if all_time_work else 40 + len(need_values) * 20

        # если эвентов > 15, диаграмму вставляем справа
        insert_cell = 'E1'

        # устанавливаем зону получения фотографии
        zone_for_photo = f'B1:K{len(need_values) + 2}'
    else:
        # длина постоянна, с кол-вом эвентов изменяется ширина
        width_diagrams = x_offset = (215 + width_column_for_events + 320) / 2 \
            if all_time_work else 215 + width_column_for_events + 320
        height_diagrams = 400

        # если эвентов <= 15, диаграмму вставляем вниз
        insert_cell = f'B{index_cell + 2}'

        # устанавливаем зону получения фотографии
        zone_for_photo = f'B1:D{index_cell + 21}'

    # диаграмма_1: отношение количества эвентов блоков
    names_block_with_its_len = [[name_block, len([one_elem for one_elem in huge_list if one_elem[1] == one_emoji])]
                                for one_emoji, name_block in block_names_dict.items()]
    first_chart = user_workbook.add_chart({'type': 'pie'})
    first_chart.set_title({'name': 'ОТНОШЕНИЕ ДЛИНЫ\nБЛОКОВ'})
    first_chart.set_style(18)
    first_chart.set_size({'width': width_diagrams,
                          'height': height_diagrams})
    first_chart.set_legend({'position': 'bottom', 'font': {'bold': True,
                                                           'name': 'Arial Black'}})
    for index_diagram_column, one_elem in enumerate(names_block_with_its_len, start=1):
        user_worksheet.write_column(index_cell + 1, index_diagram_column, one_elem)
    first_chart.add_series({'categories': [work_sheet_name,
                                           index_cell + 1, 1,
                                           index_cell + 1, len(names_block_with_its_len)],
                            'values': [work_sheet_name,
                                       index_cell + 2, 1,
                                       index_cell + 2, len(names_block_with_its_len)],
                            'points': [{'fill': {'color': f'#{one_block_colour}'}}
                                       for one_block_colour in block_colours_dict.values()],
                            'data_labels': {'percentage': True,
                                            'border': {'color': 'black', 'bold': True},
                                            'font': {'bold': True, 'color': 'black'},
                                            'fill': {'color': 'white'}}})
    user_worksheet.insert_chart(insert_cell, first_chart)

    # если хотя бы одного эвента задано время
    if all_time_work:
        # диаграмма_2: соотношение времени эвентов
        index_event_with_its_time_work = [[f'EV_{one_ind}', one_elem[0][1]]
                                          for one_ind, one_elem in enumerate(need_values, start=1)
                                          if one_elem[0][1] != 0]
        second_chart = user_workbook.add_chart({'type': 'area'})
        second_chart.set_style(18)
        second_chart.set_title({'name': 'СРАВНЕНИЕ ВРЕМЕНИ ЭВЕНТОВ'})
        second_chart.set_size({'width': width_diagrams, 'height': height_diagrams})
        second_chart.set_legend({'none': True})
        for index_diagram_column, one_elem in enumerate(index_event_with_its_time_work, start=1):
            user_worksheet.write_column(index_cell + 3, index_diagram_column, one_elem)
        second_chart.add_series({'categories': [work_sheet_name,
                                                index_cell + 3, 1,
                                                index_cell + 3, len(index_event_with_its_time_work)],
                                 'values': [work_sheet_name,
                                            index_cell + 4, 1,
                                            index_cell + 4, len(index_event_with_its_time_work)],
                                 'gradient': {'colors': ['#490005', '#960018', '#B00000', '#A32000',
                                                         'red',
                                                         '#FF2B2B', '#A33400', '#E04800', '#FF5F05',
                                                         'orange'],
                                              'positions': [10, 10, 10, 10, 10, 10, 10, 10, 10, 10]}})
        second_chart.set_plotarea({'pattern': {'pattern': 'percent_40', 'fg_color': 'orange',
                                               'bg_color': 'white'},
                                   'border': {'color': 'black', 'width': 1}})
        second_chart.set_x_axis({'num_font': {'name': 'Arial Black', 'color': 'black', 'bold': True}})
        second_chart.set_y_axis({'num_font': {'name': 'Arial Black', 'color': 'black', 'bold': True}})

        user_worksheet.insert_chart(insert_cell, second_chart,
                                    {'x_offset': x_offset,
                                     'y_offset': y_offset})

    user_workbook.close()

    # формируем фото созданной таблице
    while True:
        try:
            excel2img.export_img(f'users_bot/{bot_id}_log/for_excel_dp/{file_name}.xlsx',
                             f"users_bot/{bot_id}_log/for_excel_dp/image_dp.gif", '',
                             f'{work_sheet_name}!{zone_for_photo}')
            break
        except OSError:
            pass


async def values_for_opening_dp(user_id, username, bot, processing_dp=0):
    # проверяем: не сгенерированы ли уже данные
    inf_for_begin_dp = get_common_data(user_id, cursor, 'inf_for_begin_dp')

    # первый запуск ДП вообще (или перезапуск ДП) | изменился день недели
    user_time_now = get_user_time_now(user_id=user_id)
    if processing_dp is None \
            or (datetime.datetime.weekday(user_time_now) !=
                datetime.datetime.weekday(get_datetime_from_str(inf_for_begin_dp[3]))
                and processing_dp == -1):

        # создаём листы для работы ДП
        inf_for_begin_dp = \
            create_data_for_dp(user_id, username)

        # проверяем: есть ли данные по этому дню
        if inf_for_begin_dp:
            new_work_mes = await bot.send_animation(chat_id=user_id,
                                                    animation=
                                                    'CgACAgQAAxkBAAIamWQXDhFLZdZSFWV'
                                                    'zhPxbCTL9yDQwAAL0AgAC2ywNU8_jyzgC4dWdLwQ')
            save_main_id_message(user_id, new_work_mes.message_id, cursor, conn)

            huge_list, login_user, bot_id, datetime_work, block_names_dict, \
            block_colours_dict, all_time_work, text_under_photo \
                = inf_for_begin_dp

            # генерируем таблицу и фото ДП
            create_dp_in_excel(huge_list, block_names_dict, block_colours_dict, bot_id, all_time_work)

            # переменная для photo_id
            inf_for_begin_dp.append(InputFile(path_or_bytesio=f'users_bot/{bot_id}_log/for_excel_dp/image_dp.gif'))

    return inf_for_begin_dp


async def get_window_with_excel_dp(user_id, username, processing_dp, bot):

    # excel таблица ДП, её фотография, рабочие листы
    inf_for_begin_dp = \
        await values_for_opening_dp(user_id, username, bot,
                              processing_dp=processing_dp)

    # есть ли данные по настоящему дню
    if inf_for_begin_dp:
        huge_list, login_user, bot_id, datetime_work, \
        block_names_dict, block_colours_dict, all_time_work, \
        text_under_photo, photo_id \
            = inf_for_begin_dp

        # только что обновили расписание
        if type(inf_for_begin_dp[8]) is not str:

            new_work_mes = \
                await bot.edit_message_media(media=InputMediaPhoto(photo_id,
                                                               caption=text_under_photo,
                                                               parse_mode=ParseMode.HTML),
                                         chat_id=user_id,
                                         message_id=get_main_id_message(user_id, cursor),
                                         reply_markup={'inline_keyboard':
                                                                  [[dict(text=back_mes, callback_data='back_main_menu'),
                                                          dict(text='⏩', callback_data='way_to_DP')]]})

            # сохраняем айди фотографии, чтобы быстрее присылать
            inf_for_begin_dp[8] = str(new_work_mes.photo[-1].file_id)

            # сохраняем сформированный ДП
            save_common_data(user_id, cursor, conn, inf_for_begin_dp=inf_for_begin_dp)
            cursor.execute('UPDATE all_sessions SET processing_dp = ? WHERE user_id = ?', (-1, user_id))
            cursor.execute('DELETE FROM all_cashDP WHERE login = ? or user_id = ?',
                           (login_user, user_id,))
            conn.commit()

        # повторные заходы
        else:
            new_work_mes = await bot.send_photo(chat_id=user_id,
                                                photo=photo_id,
                                                caption=text_under_photo,
                                                parse_mode=ParseMode.HTML,
                                                reply_markup={'inline_keyboard':
                                                                  [[dict(text=back_mes, callback_data='back_main_menu'),
                                                          dict(text='⏩', callback_data='way_to_DP')]]})
            save_main_id_message(user_id, new_work_mes.message_id, cursor, conn)

    else:

        # сообщает: данного дня нет!
        await message_no_data(user_id, cursor, conn, bot, call_back='back_main_menu')


def get_data_process_dp(user_id: int, *name_keys) -> list:
    cursor.execute(f'SELECT work_dict from all_cashDP WHERE user_id = ?', (user_id,))
    work_dict = ast.literal_eval(cursor.fetchone()[0])

    got_values = [work_dict.get(one_key) for one_key in name_keys]

    return got_values if len(got_values) > 1 else got_values[0]

def save_data_process_dp(user_id: int, **keys_and_values):
    cursor.execute(f'SELECT work_dict from all_cashDP WHERE user_id = ?', (user_id,))
    work_dict = ast.literal_eval(cursor.fetchone()[0])
    work_dict.update(keys_and_values)

    cursor.execute(f"UPDATE all_cashDP set work_dict = ? "
                   f"WHERE user_id = ?",
                   (str(work_dict), user_id,))
    conn.commit()


# GETTING
def get_user_time_now(delta_utc=None, user_id=None):

    if delta_utc is None:
        login_user = get_common_data(user_id, cursor, 'login_user')
        delta_utc = cursor.execute('SELECT delta_utc FROM all_users WHERE login = ?', (login_user,)).fetchone()[0]

    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=delta_utc)

def get_live_hours(begin_clock: int, end_clock: int) -> iter:
    # формируем лист с часами работы DP
    for range_hour in range(24):
        now_hour = begin_clock + range_hour if begin_clock + range_hour < 25 \
            else begin_clock + range_hour - 24

        yield now_hour

        if now_hour is end_clock: break


def get_delta_time_to_str(one_time, delta_utc,
                          adding_time=0, needing_clock_diff=None):
    if one_time:
        # формируем настоящее время для пользователя
        diff_in_time = get_user_time_now(delta_utc) - get_datetime_from_str(one_time)
        clock_diff = str(math.floor((diff_in_time.total_seconds() + adding_time) / 60))
        str_clock = '𝟬' * (3 - len(clock_diff)) + big_replacing(clock_diff, dict_with_bold_nums)

        return str_clock if not needing_clock_diff \
            else (str_clock, clock_diff)
 
    return '𝟬𝟬𝟬' if not needing_clock_diff \
        else ('𝟬𝟬𝟬', 0)

def get_dict_with_index_emoji(huge_list, full_emoji_tuple=None):
    if not full_emoji_tuple:
        full_emoji_tuple = tuple(OrderedDict.fromkeys((one_elem[1]
                                                       for one_elem in huge_list
                                                       if one_elem[1] not in emoji_work_dp_list)))
    # получаем лист с индексами эвентов данного эмоджи
    return \
        dict(
            zip(
                full_emoji_tuple,
                [
                    [this_index for this_index, this_elm in enumerate(huge_list)
                     if one_emoji == this_elm[1]]
                    for one_emoji in full_emoji_tuple
                ]
            )
        )

def get_first_work_index(huge_list, indexes_list=None, check_all_list=False):

    if check_all_list:
        indexes_list = [one_ind for one_ind in range(len(huge_list))]

    if indexes_list:
        for one_index in indexes_list:
            if huge_list[one_index][1] not in emoji_work_dp_list:
                return one_index

def get_pages_with_this_elem(element,
                             with_index_emoji, pages_with_indexes):

    # находим разрешённую страницу для element
    allow_pages = []

    # эвент
    if (type(element) is str and element.isdigit()) or type(element) is int:
        for one_page, one_value in pages_with_indexes.items():

            if int(element) in one_value:
                allow_pages = [one_page]
                break

    # несколько блоков | блок | часть блока
    else:
        updated_elements_emoji = \
            with_index_emoji.get(element) if type(element) is str else element

        # добавляем только те страницы,
        # с индексами которых есть пересечение с updated_elements_emoji
        allow_pages = [one_page
                       for one_page, one_value in pages_with_indexes.items()
                       if set(updated_elements_emoji) & set(one_value)]

    return allow_pages


# TRANSFORM ELEMENTS
def in_roman_number(number: int):
    result = ''
    for arabic, roman in zip((1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1),
                             'M     CM   D    CD   C    XC  L   XL  X   IX V  IV I'.split()):
        result += number // arabic * roman
        number %= arabic
    return result
