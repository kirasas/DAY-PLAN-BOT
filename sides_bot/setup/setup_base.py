import ast
import uuid
import datetime
import sqlite3
from emoji import emojize, demojize, \
    is_emoji
#
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.utils.markdown import quote_html
from aiogram.utils.exceptions import MessageNotModified, MessageToEditNotFound
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message, \
    InputFile, ParseMode, InputMediaPhoto
#
from utilis.consts_common import all_content_types, back_mes, dict_with_bold_nums, \
    emoji_work_dp_list, short_name_week_days
from utilis.main_common import get_main_id_message, save_last_state_user, \
    existing_work_message, delete_work_message, get_common_data, save_common_data, \
    save_main_id_message, get_process_dp_status, big_replacing, yes_or_no_kb, grouping_by_n_elements, \
    get_button, row_buttons
#
from sides_bot.setup.utilis.consts import common_settings_kb, sett_statistics_kb, dict_names_graphs_sett, \
    sett_compound_kb, choose_remake_week_day_kb, dict_full_name_week, dict_full_name_week_another, \
    get_new_event_time_work_kb, edit_event_sett_kb, edit_block_sett_kb, remake_work_hour_begin, remake_work_hour_end, \
    time_dp_sett_kb, work_with_timezone_kb
from sides_bot.setup.utilis.main import create_full_week_days_graph, create_average_work_time_graph, \
    values_for_remake_dp_first, values_for_remake_dp_second_and_third, \
    up_down_elements, values_for_remake_dp_second_and_third, save_sett_remakes, \
    get_data_one_block, get_data_one_event, create_days_work_block_kb, with_choosing_elements_kb
#
from sides_bot.dayplan.utilis.main import create_huge_list, get_dict_with_index_emoji
from sides_bot.dayplan.utilis.block import get_indexes_current_part_block


def settings_user(dp, bot, cursor, conn,
                  main_menu, update_main_menu):
    # НАСТРОЙКИ_MES
    @dp.message_handler(text='SETTINGS\n🛠️️', state=main_menu.main_menu)
    async def sett_com_mes(message: Message):
        # обновляем state
        save_last_state_user(message.from_user.id, 'user_sett', cursor, conn)
        await main_menu.user_sett.set()

        await message.delete()
        await update_main_menu(message.from_user.id, bot, cursor, conn,
                               text_for='🛠️<i>НАСТРОЙКИ</i>🛠️️',
                               markup_for=common_settings_kb, parse_for=ParseMode.HTML,
                               need_state='user_sett')

    # НАСТРОЙКИ_CALL
    @dp.callback_query_handler(text='to_back_common_settings', state=main_menu.user_sett)
    async def set_com_call(callback: CallbackQuery):
        await bot.edit_message_text(text='🛠️<i>НАСТРОЙКИ</i>🛠️️',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    parse_mode=ParseMode.HTML,
                                    reply_markup=common_settings_kb)

    # НАСТРОЙКИ / ВРЕМЯ
    @dp.callback_query_handler(text='time_dp', state=main_menu.user_sett)
    async def time_settings(callback: CallbackQuery):
        await bot.edit_message_text(text='🛠<b>Н/</b><i>ВРЕМЯ</i>\n\n',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    parse_mode=ParseMode.HTML,
                                    reply_markup=time_dp_sett_kb)

    # НАСТРОЙКИ / ВРЕМЯ / РАБОЧИЕ ЧАСЫ / НАЧАЛЬНЫЙ ЧАС
    @dp.callback_query_handler(text='edit_work_hour', state=main_menu.user_sett)
    @dp.callback_query_handler(text=('plus_to_begin_hour', 'minus_to_begin_hour'), state=main_menu.user_sett)
    async def set_edit_work_hour_begin(callback: CallbackQuery):

        # GET_COMMON_DATA
        login_user = get_common_data(callback.from_user.id, cursor,
                                     'login_user')

        # определяем рабочие часы
        cursor.execute('SELECT begin_hour, stop_hour FROM all_users WHERE login = ?', (login_user,))
        begin_h, end_h = cursor.fetchone()

        # прибавили к начальному часу
        if callback.data == 'plus_to_begin_hour':
            begin_h += 1
            if begin_h > end_h:
                await callback.answer('Начальный час не может быть равен конечному часу!')
                begin_h -= 1

        # убавили начальный час
        elif callback.data == 'minus_to_begin_hour':
            begin_h -= 1
            if begin_h < 0:
                await callback.answer('Начальный час не может быть меньше нуля!')
                begin_h = 0

        try:
            await bot.edit_message_text(text='🛠<b>Н/В/</b><i>РАБОЧИЕ ЧАСЫ=НАЧАЛЬНЫЙ ЧАС</i>\n\n'
                                             f'★<b>️ДИАПОЗОН РАБОТЫ: от <code>{begin_h}</code> '
                                             f'до <code>{end_h+1}</code></b>★\n\n'
                                             f'️📌В часы, не входящие в диапозон работ, вы не сможете начать новый DAY '
                                             f'PLAN, а ранее открытое расписание закроется автоматически!',
                                        chat_id=callback.from_user.id,
                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                        parse_mode=ParseMode.HTML,
                                        reply_markup=remake_work_hour_begin)
        except MessageNotModified:
            pass

        # обновляем начальный час
        cursor.execute('UPDATE all_users SET begin_hour = ? WHERE login = ?', (begin_h, login_user,))
        conn.commit()

    # НАСТРОЙКИ / ВРЕМЯ РАБОЧИЕ ЧАСЫ / КОНЕЧНЫЙ ЧАС
    @dp.callback_query_handler(text='to_edit_end_hour', state=main_menu.user_sett)
    @dp.callback_query_handler(text=('plus_to_end_hour', 'minus_to_end_hour'), state=main_menu.user_sett)
    async def set_edit_work_hour_end(callback: CallbackQuery):

        # GET_COMMON_DATA
        login_user = get_common_data(callback.from_user.id, cursor,
                                     'login_user')

        # определяем рабочие часы
        cursor.execute('SELECT begin_hour, stop_hour FROM all_users WHERE login = ?', (login_user,))
        begin_h, end_h = cursor.fetchone()

        # прибавили к конечному часу
        if callback.data == 'plus_to_end_hour':
            end_h += 1
            if end_h > 23:
                await callback.answer('Конечный час не может быть больше 24 часов!')
                end_h -= 1

        # убавили конечный час
        elif callback.data == 'minus_to_end_hour':
            end_h -= 1
            if end_h < begin_h:
                await callback.answer('Конечный час не может меньше начального часа!')
                end_h += 1

        try:
            await bot.edit_message_text(text='🛠<b>Н/В/</b><i>РАБОЧИЕ ЧАСЫ=КОНЕЧНЫЙ ЧАС</i>\n\n'
                                             f'★<b>️ДИАПОЗОН РАБОТЫ: от <code>{begin_h}</code> '
                                             f'до <code>{end_h + 1}</code></b>★\n\n'
                                             f'️📌В часы, не входящие в диапозон работ, вы не сможете начать новый DAY '
                                             f'PLAN, а ранее открытое расписание закроется автоматически!',
                                        chat_id=callback.from_user.id,
                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                        parse_mode=ParseMode.HTML,
                                        reply_markup=remake_work_hour_end)
        except MessageNotModified:
            pass

        # обновляем начальный час
        cursor.execute('UPDATE all_users SET stop_hour = ? WHERE login = ?', (end_h, login_user,))
        conn.commit()

    # НАСТРОЙКИ / ВРЕМЯ / ЧАСОВОЙ ПОЯС
    @dp.callback_query_handler(text='edit_timezone', state=main_menu.user_sett)
    @dp.callback_query_handler(text=('plus_to_edit_timezone', 'minus_to_edit_timezone'), state=main_menu.user_sett)
    async def set_edit_work_hour_begin(callback: CallbackQuery):

        # GET_COMMON_DATA
        login_user = get_common_data(callback.from_user.id, cursor,
                                     'login_user')

        # определяем зону
        cursor.execute('SELECT delta_utc FROM all_users WHERE login = ?', (login_user,))
        delta_utc = cursor.fetchone()[0]

        # прибавили к дельу
        if callback.data == 'plus_to_edit_timezone':
            delta_utc += 1
            if delta_utc > 12:
                await callback.answer('Отклонение от UTC не может превышать 12 часов!')
                delta_utc -= 1

        # убавили дельту
        elif callback.data == 'minus_to_edit_timezone':
            delta_utc -= 1
            if delta_utc < -12:
                await callback.answer('Отклонение от UTC не может превышать 12 часов!')
                delta_utc = -12

        try:
            await bot.edit_message_text(text='🛠<b>Н/В/</b><i>ЧАСОВОЙ ПОЯС</i>\n\n'
                                             f'★<b>ОТКЛОНЕНИЕ ОТ UTC: <code>{delta_utc}</code></b>★\n\n'
                                             f'️📌Определите ваш часовой пояс для корректной работы времени DAY PLAN!',
                                        chat_id=callback.from_user.id,
                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                        parse_mode=ParseMode.HTML,
                                        reply_markup=work_with_timezone_kb)
        except MessageNotModified:
            pass

        # обновляем начальный час
        cursor.execute('UPDATE all_users SET delta_utc = ? WHERE login = ?', (delta_utc, login_user,))
        conn.commit()

    # НАСТРОЙКИ / СТАТИСТИКА
    @dp.callback_query_handler(text=('statistics_dp', 'back_choose_graph_sett'), state=main_menu.user_sett)
    async def exit_from_account_ask(callback: CallbackQuery):

        # возвращаемся с графиков
        if callback.data == 'back_choose_graph_sett':
            await delete_work_message(callback.from_user.id, bot, cursor)

            new_work_mes = \
                await bot.send_message(text='🛠️<b>Н/</b><i>СТАТИСТИКА</i>️️',
                                       chat_id=callback.from_user.id,
                                       parse_mode=ParseMode.HTML,
                                       reply_markup=sett_statistics_kb)
            save_main_id_message(callback.from_user.id, new_work_mes.message_id, cursor, conn)

        # в статистику зашли
        else:
            await bot.edit_message_text('🛠️<b>Н/</b><i>СТАТИСТИКА</i>',
                                        chat_id=callback.from_user.id,
                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                        parse_mode=ParseMode.HTML,
                                        reply_markup=sett_statistics_kb)

    # НАСТРОЙКИ / СТАТИСТИКА / КОНКРЕТНЫЙ ГРАФИК
    @dp.callback_query_handler(text=("get_full_days", 'get_not_full_days', 'get_average_time_work'),
                               state=main_menu.user_sett)
    async def see_statistics_graphs(callback: CallbackQuery):
        await delete_work_message(callback.from_user.id, bot, cursor)

        data_with_media_statistics, login_user, bot_id = \
            get_common_data(callback.from_user.id, cursor,
                            'data_with_media_statistics', 'login_user', 'bot_id')

        # если изменился статус, обнуляем все айди
        process_dp_status_now = get_process_dp_status(callback.from_user.id, cursor)
        if process_dp_status_now != data_with_media_statistics[1]:
            data_with_media_statistics[0] = {}

        # проверяем: есть ли уже айди
        one_photo_id = \
            data_with_media_statistics[0].get(callback.data)

        # фото ещё не сгенерировано | изменился статус
        if not one_photo_id:
            # отправляем сообщение загрузки
            new_work_mes = await bot.send_animation(chat_id=callback.from_user.id,
                                                    animation=
                                                    'CgACAgQAAxkBAAIamWQXDhFLZdZSFWVzhPxbCTL9y'
                                                    'DQwAAL0AgAC2ywNU8_jyzgC4dWdLwQ')
            save_main_id_message(callback.from_user.id, new_work_mes.message_id, cursor, conn)

            save_path = f'users_bot/{bot_id}_log/for_sett_dp'

            # фулл/не фулл
            if callback.data in ("get_full_days", 'get_not_full_days'):
                create_full_week_days_graph(bot_id, save_path, get_full_days=True
                if callback.data == 'get_full_days' else False)

            # average_time done_dp
            else:
                create_average_work_time_graph(bot_id, save_path)

            one_photo_id = InputFile(path_or_bytesio=f'{save_path}/graph_sett.jpg')

            new_work_mes = \
                await bot.edit_message_media(media=InputMediaPhoto(one_photo_id,
                                                                   caption=f'🛠️<b>Н/С/</b><i>'
                                                                        f'{dict_names_graphs_sett.get(callback.data)}'
                                                                        f'</i>️️',
                                                                   parse_mode=ParseMode.HTML),
                                             chat_id=callback.from_user.id,
                                             message_id=get_main_id_message(callback.from_user.id, cursor),
                                             reply_markup=InlineKeyboardMarkup().row(
                                                 InlineKeyboardButton(back_mes,
                                                                      callback_data='back_choose_graph_sett')))

        else:
            new_work_mes = \
                await bot.send_photo(photo=one_photo_id,
                                     caption=f'🛠️<b>Н/С/</b><i>{dict_names_graphs_sett.get(callback.data)}</i>️️',
                                     chat_id=callback.from_user.id,
                                     parse_mode=ParseMode.HTML,
                                     reply_markup=InlineKeyboardMarkup().row(
                                         InlineKeyboardButton(back_mes,
                                                              callback_data='back_choose_graph_sett')))
            save_main_id_message(callback.from_user.id, new_work_mes.message_id, cursor, conn)

        # сохраняем айди фото
        if not data_with_media_statistics[0].get(callback.data):
            data_with_media_statistics[0][callback.data] = str(new_work_mes.photo[-1].file_id)

            data_with_media_statistics = [data_with_media_statistics[0], process_dp_status_now]

            save_common_data(callback.from_user.id, cursor, conn,
                             data_with_media_statistics=data_with_media_statistics)

    # НАСТРОЙКИ / СОСТАВ
    @dp.callback_query_handler(text='compound_dp', state=main_menu.user_sett)
    async def compound_sett(callback: CallbackQuery):
        await bot.edit_message_text(text='🛠️<b>Н/</b><i>СОСТАВ</i>️️',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    parse_mode=ParseMode.HTML,
                                    reply_markup=sett_compound_kb)

    # НАСТРОЙКИ / СОСТАВ / РАСПОЛОЖЕНИЕ
    @dp.callback_query_handler(text='locating_elements_dp_sett', state=main_menu.user_sett)
    @dp.callback_query_handler(text='back_to_compound', state=main_menu.compound_remake_sett)
    @dp.callback_query_handler(text=("save_changes_sett", 'no_save_changes_sett'), state=main_menu.compound_remake_sett)
    async def locating_elements_dp_sett(callback: CallbackQuery):

        # изменения ДП | возвращение в КБ
        if callback.data in ("save_changes_sett", 'no_save_changes_sett', 'back_to_compound'):
            await main_menu.user_sett.set()
            save_last_state_user(callback.from_user.id, 'user_sett', cursor, conn)

            if callback.data == 'save_changes_sett':
                # GET_COMMON_DATA
                chosen_week_day = \
                    get_common_data(callback.from_user.id, cursor, 'chosen_week_day')
                await callback.answer(f'DAY PLAN {dict_full_name_week_another.get(chosen_week_day)} ОБНОВЛЁН!')
                save_sett_remakes(callback.from_user.id, cursor, conn)

        await bot.edit_message_text(text='🛠️<b>Н/С/</b><i>РАСПОЛОЖЕНИЕ</i>️️\n\n'
                                         '📌<b>Где вы хотите изменить расположение расписания?</b>',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    parse_mode=ParseMode.HTML,
                                    reply_markup=choose_remake_week_day_kb)

        # обнуляем всё в любом случае, дабы избежать исключений
        save_common_data(callback.from_user.id, cursor, conn,
                         remake_huge_list=None,
                         remake_element=None,
                         history_remakes=None,
                         updated_data_values_first_dp=None,
                         updated_data_rome_kb=None,
                         updated_data_steps_and_save=None,
                         updated_data_relocating_elem=None,
                         chosen_week_day=None,
                         huge_list=None, relocating_part_block=None)

    # НАСТРОЙКИ / СОСТАВ / РАСПОЛОЖЕНИЕ / ВЫБОР РЕДАКТИРУЕМОЕГО ЭЛЕМЕНТА
    @dp.callback_query_handler(Text(endswith="_choose_week_day"),
                               state=main_menu.user_sett)
    @dp.callback_query_handler(Text(endswith="_sett_dp_1"),
                               state=main_menu.compound_remake_sett)
    async def choose_remake_element(callback: CallbackQuery):

        # GET_COMMON_DATA
        remake_huge_list, remake_element, chosen_week_day, \
        last_page_set_2, updated_data_values_first_dp, history_remakes, \
        login_user, huge_list, bot_id = \
            get_common_data(callback.from_user.id, cursor,
                            'remake_huge_list', 'remake_element', 'chosen_week_day',
                            'last_page_set_2', 'updated_data_values_first_dp', 'history_remakes',
                            'login_user', 'huge_list', 'bot_id')

        # выбранный день недели ещё не зафиксировали
        if '_choose_week_day' in callback.data:
            chosen_week_day = int(callback.data[0])

            # смотрим: есть ли у данного дня недели дела
            one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                            check_same_thread=False)
            one_user_cursor = one_user_conn.cursor()
            one_user_cursor.execute(f'SELECT week_day_{chosen_week_day} FROM hierarchy_day_plans')
            exist_things = one_user_cursor.fetchone()

            if exist_things:
                if exist_things[0]:
                    huge_list = remake_huge_list = \
                        create_huge_list(one_user_cursor, ast.literal_eval(exist_things[0]))

        # если есть дела
        if huge_list:
            await main_menu.compound_remake_sett.set()
            save_last_state_user(callback.from_user.id, 'compound_remake_sett', cursor, conn)

            message_pages = int(callback.data[:-10]) if 'sett_dp_1' in callback.data \
                else 1

            # специальный деф для работы с remake_dp_1
            asked, need_kb, \
            updated_data_values_first_dp = \
                values_for_remake_dp_first(huge_list=huge_list,
                                           remake_huge_list=remake_huge_list, remake_element=remake_element,
                                           message_pages=message_pages, last_page_set_2=last_page_set_2,
                                           updated_data_values_first_dp=updated_data_values_first_dp)

            try:

                await bot.edit_message_text(f'🛠️<b>Н/С/Р/</b><i>'
                                            f'{dict_full_name_week.get(chosen_week_day)}</i>️️\n\n'
                                            f'<b>📌Выберите элемент расписания!</b>\n'
                                            f'{asked}', chat_id=callback.from_user.id,
                                            message_id=get_main_id_message(callback.from_user.id, cursor),
                                            reply_markup=need_kb,
                                            parse_mode=ParseMode.HTML)
            except MessageNotModified:
                pass

            # если remake_huge_list был None
            if not history_remakes:
                save_common_data(callback.from_user.id, cursor, conn,
                                 last_page_set_1=message_pages,
                                 remake_huge_list=remake_huge_list,
                                 history_remakes=[('1_sett_dp_1', remake_huge_list)],
                                 updated_data_steps_and_save=None,
                                 updated_data_values_first_dp=updated_data_values_first_dp,
                                 chosen_week_day=chosen_week_day,
                                 huge_list=huge_list)
            else:
                save_common_data(callback.from_user.id, cursor, conn, last_page_set_1=message_pages,
                                 updated_data_values_first_dp=updated_data_values_first_dp)

        else:
            await callback.answer('✖️DAY PLAN ОТСУТСТВУЕТ✖')

    # НАСТРОЙКИ / СОСТАВ / РАСПОЛОЖЕНИЕ / ВОПРОС: СОХРАНЯТЬ ИЗМЕНЕНИЯ?
    @dp.callback_query_handler(text="condition_closing_sett", state=main_menu.compound_remake_sett)
    async def sett_save_elem_ask(callback: CallbackQuery):

        # GET_COMMON_DATA
        chosen_week_day = \
            get_common_data(callback.from_user.id, cursor, 'chosen_week_day')

        save_remakes_kb = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton('СОХРАНИТЬ', callback_data='save_changes_sett'),
            InlineKeyboardButton('НЕ СОХРАНЯТЬ', callback_data='no_save_changes_sett'),
            InlineKeyboardButton('ОБРАТНО К ИЗМЕНЕНИЯМ', callback_data='1_sett_dp_1'))

        await bot.edit_message_text(f'🛠️<b>Н/С/Р/</b><i>'
                                    f'{dict_full_name_week.get(chosen_week_day)}</i>️️\n\n'
                                    f'<b>❓Сохранить изменения DAY PLAN❓</b>',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=save_remakes_kb,
                                    parse_mode=ParseMode.HTML)

    # НАСТРОЙКИ / СОСТАВ / РАСПОЛОЖЕНИЕ / REMAKE_ELEMENT_MES
    @dp.message_handler(Text(endswith="BLX"),
                        state=main_menu.compound_remake_sett)
    @dp.message_handler(Text(startswith="/EVN"),
                        state=main_menu.compound_remake_sett)
    @dp.message_handler(Text(startswith="/PART"),
                        state=main_menu.compound_remake_sett)
    async def work_with_remake_element_mes(message: Message):
        await message.delete()

        # GET_COMMON_DATA
        remake_huge_list, updated_data_relocating_elem, \
        last_page_set_1, last_page_set_3, chosen_week_day = \
            get_common_data(message.from_user.id, cursor,
                            'remake_huge_list', 'updated_data_relocating_elem',
                            'last_page_set_1', 'last_page_set_3', 'chosen_week_day')

        # обновляем рабочий дикт
        with_index_emoji = \
            get_dict_with_index_emoji(remake_huge_list)

        # часть блока
        if '/PART' in message.text:
            this_something = None

            # получаем лист: [number_part_block, emoji]
            number_part_and_emoji = message.text.split('_', 1)
            index_part_block = number_part_and_emoji[0][5:]
            emoji_block = emojize(f':{number_part_and_emoji[1]}:')

            all_parts_this_block = get_indexes_current_part_block(last_emoji=emoji_block,
                                                                  with_index_emoji=with_index_emoji,
                                                                  huge_list=remake_huge_list,
                                                                  get_full_indexes_parts=True)

            # проверяем: есть ли части у данного блока
            if all_parts_this_block:

                # проверяем: есть ли часть блока с данным индексом
                if index_part_block.isdigit() and int(index_part_block) - 1 < len(all_parts_this_block):
                    indexes_our_part_block = this_something = \
                        all_parts_this_block[int(index_part_block) - 1]

                    save_common_data(message.from_user.id, cursor, conn,
                                     relocating_part_block=
                                     [
                                         emoji_block, indexes_our_part_block,
                                         [remake_huge_list[one_ind] for one_ind in indexes_our_part_block],
                                         int(index_part_block)
                                     ])

        # блок или эвент
        else:
            this_something = emojize(f':{message.text[1:-3]}:')[0] \
                if 'BLX' in message.text \
                else message.text[4:]

        remake_element = message_pages = None
        # часть блока!
        if type(this_something) is list:
            remake_element = message_pages = this_something
        # нам прислали название эмоджи?
        elif is_emoji(this_something) and with_index_emoji.get(this_something):
            remake_element = message_pages = this_something
        # есть такой эвент?
        elif this_something.isdigit() and int(this_something) <= len(remake_huge_list):
            remake_element = int(this_something) - 1
            message_pages = str(remake_element)

        # если внесли корректные данные
        # remake_element может быть = 0
        if remake_element is not None:

            # наш новый DP на первой странице элемента
            asked, need_kb, updated_data_relocating_elem = \
                values_for_remake_dp_second_and_third(remake_huge_list=remake_huge_list,
                                                      this_updated_data=updated_data_relocating_elem,
                                                      add_callback='sett_dp_2', remake_element=remake_element,
                                                      message_pages=message_pages,
                                                      last_action_remaking=None,
                                                      last_page_set_1=last_page_set_1,
                                                      last_page_set_3=last_page_set_3,
                                                      relocating_part_block=
                                                      get_common_data(message.from_user.id, cursor,
                                                                      'relocating_part_block'))
            try:
                await bot.edit_message_text(f'🛠️<b>Н/С/Р/</b><i>'
                                            f'{dict_full_name_week.get(chosen_week_day)}</i>️️\n\n'
                                            f'🔺️️<b>Перемещайте выбранный элемент</b>🔻\n\n'
                                            f'{asked}', chat_id=message.from_user.id,
                                            message_id=get_main_id_message(message.from_user.id, cursor),
                                            reply_markup=need_kb,
                                            parse_mode=ParseMode.HTML)
            except MessageToEditNotFound:
                await existing_work_message(message.from_user.id, bot,
                                            cursor, conn,
                                            main_menu)

            save_common_data(message.from_user.id, cursor, conn,
                             remake_element=remake_element,
                             last_action_remaking=None,
                             last_page_set_2=1,
                             updated_data_relocating_elem=updated_data_relocating_elem)

    # НАСТРОЙКИ / СОСТАВ / РАСПОЛОЖЕНИЕ / REMAKE_ELEMENT_CALL
    @dp.callback_query_handler(text=("up_element", 'down_element'), state=main_menu.compound_remake_sett)
    @dp.callback_query_handler(Text(endswith="sett_dp_2"), state=main_menu.compound_remake_sett)
    async def work_with_remake_element_call(callback: CallbackQuery):

        # GET_COMMON_DATA
        remake_huge_list, remake_element, chosen_week_day, \
        updated_data_relocating_elem, relocating_part_block, \
        last_page_set_1, last_page_set_3, history_remakes, \
        last_action_remaking = \
            get_common_data(callback.from_user.id, cursor,
                            'remake_huge_list', 'remake_element', 'chosen_week_day',
                            'updated_data_relocating_elem', 'relocating_part_block',
                            'last_page_set_1', 'last_page_set_3', 'history_remakes',
                            'last_action_remaking')

        if 'sett_dp_2' in callback.data:

            # при X|_sett_dp_2, X - элемент расписания,
            # при X_sett_dp_2, X - страница
            message_pages = callback.data.split('|')[0] if '|' in callback.data \
                else int(callback.data[:-10])
        else:
            # непосредственно осуществляем передвижение элемента
            remake_element, remake_huge_list, \
            relocating_part_block, history_remakes = \
                up_down_elements(remake_element=remake_element, remake_huge_list=remake_huge_list,
                                 relocating_part_block=relocating_part_block, history_remakes=history_remakes,
                                 action=callback.data)
            message_pages = str(remake_element) if type(remake_element) is int \
                else remake_element
            last_action_remaking = callback.data

        # наш новый DP на первой странице элемента
        asked, need_kb, updated_data_relocating_elem = \
            values_for_remake_dp_second_and_third(remake_huge_list=remake_huge_list,
                                                  this_updated_data=updated_data_relocating_elem,
                                                  add_callback='sett_dp_2', remake_element=remake_element,
                                                  message_pages=message_pages,
                                                  last_action_remaking=last_action_remaking,
                                                  last_page_set_1=last_page_set_1,
                                                  last_page_set_3=last_page_set_3,
                                                  relocating_part_block=relocating_part_block)

        try:
            await bot.edit_message_text(f'🛠️<b>Н/С/Р/</b><i>'
                                        f'{dict_full_name_week.get(chosen_week_day)}</i>️️\n\n'
                                        f'🔺️️<b>Перемещайте выбранный элемент</b>🔻\n\n'
                                        f'{asked}', chat_id=callback.from_user.id,
                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                        reply_markup=need_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(callback.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)
        except MessageNotModified:
            pass

        # SAVE_COMMON_DATA
        if 'sett_dp_2' in callback.data:
            save_common_data(callback.from_user.id, cursor, conn,
                             last_page_set_2=message_pages if type(message_pages) is int else 1,
                             updated_data_relocating_elem=updated_data_relocating_elem)
        else:
            save_common_data(callback.from_user.id, cursor, conn,
                             remake_element=remake_element, remake_huge_list=remake_huge_list,
                             relocating_part_block=relocating_part_block, history_remakes=history_remakes,
                             last_page_set_2=message_pages if type(message_pages) is int else 1,
                             updated_data_relocating_elem=updated_data_relocating_elem,
                             last_action_remaking=last_action_remaking)

    # НАСТРОЙКИ / СОСТАВ / РАСПОЛОЖЕНИЕ / СОХРАНЕНИЕ ИЗМЕНЕНИЙ
    @dp.callback_query_handler(text=("back_old_step", 'back_future_step'), state=main_menu.compound_remake_sett)
    @dp.callback_query_handler(text="save_remakes", state=main_menu.compound_remake_sett)
    @dp.callback_query_handler(Text(endswith="_sett_dp_3"), state=main_menu.compound_remake_sett)
    async def save_remakes_sett(callback: CallbackQuery):

        # GET_COMMON_DATA
        chosen_week_day, remake_huge_list, updated_data_steps_and_save, \
        history_remakes, message_pages, remake_element, \
        last_page_set_2 = \
            get_common_data(callback.from_user.id, cursor,
                            'chosen_week_day', 'remake_huge_list', 'updated_data_steps_and_save',
                            'history_remakes', 'last_page_set_3', 'remake_element',
                            'last_page_set_2')

        if callback.data == 'back_old_step':

            # находим первый индекс не в будущем - настоящее
            # переворачиваем, чтобы быстрее обнаружить элемент
            for one_index, one_elem_history in enumerate(reversed(history_remakes)):

                if one_elem_history[-1] != 'in_future' and one_index != len(history_remakes) - 1:
                    # из индекса перевёрнутого листа в обычный индекс
                    # момент настоящего в history_remakes делаем будущим
                    history_remakes[-one_index - 1].append('in_future')

                    # объявляем новое настоящее
                    new_present_time = history_remakes[-one_index - 2]
                    remake_huge_list = new_present_time[1]

                    # если new_present_time[0] = '1_sett_dp_1', это первый элемент истории
                    remake_element = new_present_time[0] if new_present_time[0] != '1_sett_dp_1' else None

                    break

            else:
                await callback.answer('Прошлое исчерпано!')

        elif callback.data == 'back_future_step':

            # находим первый индекс in_future
            for one_index, one_elem_history in enumerate(history_remakes):

                if one_elem_history[-1] == 'in_future':
                    # даелаем будущее настоящим
                    history_remakes[one_index].remove('in_future')
                    remake_huge_list = one_elem_history[1]
                    remake_element = one_elem_history[0]

                    break
            else:
                await callback.answer('Будущее не предопределено!')

        elif '_sett_dp_3' in callback.data:
            message_pages = int(callback.data[:-10])

        asked, need_kb, \
        updated_data_steps_and_save = \
            values_for_remake_dp_second_and_third(remake_huge_list=remake_huge_list,
                                                  this_updated_data=updated_data_steps_and_save,
                                                  add_callback='sett_dp_3', remake_element=remake_element,
                                                  message_pages=message_pages,
                                                  callback_data=callback.data,
                                                  history_remakes=history_remakes,
                                                  last_page_set_2=last_page_set_2)

        try:
            await bot.edit_message_text(f'🛠️<b>Н/С/Р/</b><i>'
                                        f'{dict_full_name_week.get(chosen_week_day)}</i>️️\n\n'
                                        f'✔️<b>SIMPLE DAY PLAN</b>✖️\n\n'
                                        f'{asked}', chat_id=callback.from_user.id,
                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                        reply_markup=need_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(callback.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)

        # SAVE_COMMON_DATA
        # шагам по истории
        if callback.data in ("back_old_step", 'back_future_step'):
            save_common_data(callback.from_user.id, cursor, conn,
                             remake_element=remake_element,
                             remake_huge_list=remake_huge_list,
                             history_remakes=history_remakes,
                             updated_data_steps_and_save=updated_data_steps_and_save)

        elif callback.data == 'save_remakes':
            save_sett_remakes(callback.from_user.id, cursor, conn, updated_data_steps_and_save)
            await callback.answer(f'DAY PLAN {dict_full_name_week_another.get(chosen_week_day)} ОБНОВЛЁН!')

        # изменение страницы
        else:
            save_common_data(callback.from_user.id, cursor, conn,
                             last_page_set_3=message_pages,
                             updated_data_steps_and_save=updated_data_steps_and_save)

    # НАСТРОЙКИ / СОСТАВ / ЭВЕНТЫ
    @dp.callback_query_handler(Text(endswith='_page_to_event'),
                               state=(main_menu.user_sett, main_menu.new_event_name))
    @dp.callback_query_handler(text="events_sett", state=main_menu.user_sett)
    @dp.callback_query_handler(text=('yes_adding_this_event', 'no_adding_this_event', 'yes_delete_event'),
                               state=main_menu.user_sett)
    async def choose_events(callback: CallbackQuery):
        await main_menu.user_sett.set()
        save_last_state_user(callback.from_user.id, 'user_sett', cursor, conn)

        # GET_COMMON_DATA
        login_user, data_events_kb, last_page_choose_events, \
        new_event_name, new_event_describe_dp, new_event_describe_el, \
        new_event_time_work, work_element, bot_id = \
            get_common_data(callback.from_user.id, cursor,
                            'login_user', 'data_events_kb', 'last_page_choose_events',
                            'new_event_name', 'new_event_describe_dp', 'new_event_describe_el',
                            'new_event_time_work', 'work_element', 'bot_id')

        # добавили новый эвент!
        if callback.data == 'yes_adding_this_event':

            # подключаемся к бд пользователя
            one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                            check_same_thread=False)
            one_user_cursor = one_user_conn.cursor()

            # обновляем список эвентов
            one_user_cursor.execute(
                '''INSERT INTO classification_of_events (code_element, name_dp, description_dp, 
                        description_element, time_of_doing) VALUES (?, ?, ?, ?, ?)''',
                (str(uuid.uuid4()).replace('-', ''), new_event_name, new_event_describe_dp, new_event_describe_el,
                 new_event_time_work))
            one_user_conn.commit()

            await callback.answer('Список эвентов обновлён!')

        # удаляем эвент
        elif callback.data == 'yes_delete_event':

            code_event, event_name, text_for, one_event_kb, its_block_code = work_element

            # подключаемся к бд пользователя
            one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                            check_same_thread=False)
            one_user_cursor = one_user_conn.cursor()

            # удаляем эвент
            one_user_cursor.execute('DELETE FROM classification_of_events WHERE code_element = ?',
                                    (code_event,))

            # если эвент в блоке
            if its_block_code:
                # удаляем эвент из блока
                one_user_cursor.execute('SELECT content FROM classification_of_blocks WHERE code_element = ?',
                                        (its_block_code,))
                content_block = ast.literal_eval(one_user_cursor.fetchone()[0])
                content_block.remove(code_event)

                one_user_cursor.execute('UPDATE classification_of_blocks SET content = ? WHERE code_element = ?',
                                        (str(content_block), its_block_code,))

                # удаляем эвент из DAY PLAN
                one_user_cursor.execute('SELECT * FROM hierarchy_day_plans')
                hierarchy_day_plans = one_user_cursor.fetchone()

                if hierarchy_day_plans:
                    hierarchy_day_plans = list(hierarchy_day_plans)

                    # находим размещение эвентов на каждом дне и убираем оттуда эвент
                    for ind_week, day_week_data in enumerate(hierarchy_day_plans):

                        # если эвент есть в данном дне
                        if day_week_data:
                            day_week_list = ast.literal_eval(day_week_data)
                            if code_event in day_week_list:
                                day_week_list.remove(code_event)
                            hierarchy_day_plans[ind_week] = str(day_week_list)

                    # обновляем иерархию эвентов
                    one_user_cursor.execute('''UPDATE hierarchy_day_plans SET 
                    week_day_0 = ?, week_day_1 = ?, week_day_2 = ?, week_day_3 = ?, 
                    week_day_4 = ?, week_day_5 = ?, week_day_6 = ?''', hierarchy_day_plans)

            one_user_conn.commit()

            await callback.answer('Список эвентов обновлён!')

        # формируем КБ
        message_pages, choose_events_sett_kb = \
            with_choosing_elements_kb(callback.from_user.id,
                                      bot_id,
                                      cursor, conn,
                                      work_with_event=True,
                                      your_data_save=data_events_kb, your_save_name='data_events_kb',
                                      last_page=last_page_choose_events, with_page_call='_page_to_event',
                                      with_element_call='_choose_event', back_callback='compound_dp',
                                      list_with_first_button=[get_button('➕ДОБАВИТЬ ЭВЕНТ➕',
                                                                           callback_data='adding_event_sett')],
                                      callback_data=callback.data,
                                      sql_request='''SELECT code_element, name_dp FROM classification_of_events''')

        await bot.edit_message_text(f'🛠️<b>Н/С/</b><i>ЭВЕНТЫ</i>️️\n\n'
                                    f'<b>📌Выберите эвент или создайте новый!</b>',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=choose_events_sett_kb,
                                    parse_mode=ParseMode.HTML)

        save_common_data(callback.from_user.id, cursor, conn,
                         last_page_choose_events=message_pages,
                         new_event_name=None,
                         new_event_describe_dp=None,
                         new_event_describe_el=None,
                         new_event_time_work=0,
                         adding_event_sett_from_block=[0, ''])

    # НАСТРОЙКИ / СОСТАВ / ЭВЕНТЫ / НОВЫЙ ЭВЕНТ
    @dp.callback_query_handler(text='adding_event_sett', state=(main_menu.user_sett, main_menu.new_event_describe_dp))
    @dp.callback_query_handler(text='adding_event_sett_from_block', state=main_menu.user_sett)
    async def adding_event(callback: CallbackQuery):
        await main_menu.new_event_name.set()
        save_last_state_user(callback.from_user.id, 'new_event_name', cursor, conn)

        # GET_COMMON_DATA
        new_event_name, last_page_choose_events, adding_event_sett_from_block = \
            get_common_data(callback.from_user.id, cursor,
                            'new_event_name', 'last_page_choose_events', 'adding_event_sett_from_block')
        event_kb = InlineKeyboardMarkup()

        # если пришли из блока
        if callback.data == 'adding_event_sett_from_block':
            new_event_name = None
            adding_event_sett_from_block[0] = 1

            save_common_data(callback.from_user.id, cursor, conn,
                             adding_event_sett_from_block=adding_event_sett_from_block,
                             new_event_name=None,
                             new_event_describe_dp=None,
                             new_event_describe_el=None,
                             new_event_time_work=0)

        # name ещё не было определено
        if not new_event_name:
            text_for = '<b>❔| Как будет называться новый эвент?</b>\n\n' \
                       f'📌<b>Максимальная длина названия эвента: ' \
                       f'<code>{big_replacing(15, your_dict=dict_with_bold_nums)}</code></b>'

            event_kb.row(
                InlineKeyboardButton(back_mes,
                                     callback_data=f'{last_page_choose_events}_page_to_event'
                                     if not adding_event_sett_from_block[0]
                                     else 'back_to_block_from_adding_event'))
        else:
            text_for = f'<b>▫️НАЗВАНИЕ ЭВЕНТА:</b> \n' \
                       f'·<code>{new_event_name}</code>\n\n' \
                       f'📌<b>Вы можете изменить название, написав обновлённую версию в чат!</b>'

            event_kb.row(
                InlineKeyboardButton(back_mes, callback_data=f'{last_page_choose_events}_page_to_event'
                                     if not adding_event_sett_from_block[0]
                                     else 'back_to_block_from_adding_event'),
                InlineKeyboardButton('➡️', callback_data='to_new_event_describe_dp'))

        try:
            # НЕ пришли | пришли с блока
            text_first = f'🛠️<b>Н/С/Э/</b><i>НОВЫЙ ЭВЕНТ</i>️️\n\n' \
                if not adding_event_sett_from_block[0] else adding_event_sett_from_block[1]

            await bot.edit_message_text(f'{text_first}'
                                        f'{text_for}',
                                        chat_id=callback.from_user.id,
                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                        reply_markup=event_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(message.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)

    # НАСТРОЙКИ / СОСТАВ / ЭВЕНТЫ / НОВЫЙ ЭВЕНТ: ИМЯ
    @dp.message_handler(state=main_menu.new_event_name, content_types='text')
    async def get_new_name_event(message: Message):
        await message.delete()

        # GET_COMMON_DATA
        new_event_name, new_event_describe_dp, last_page_choose_events, \
        adding_event_sett_from_block = \
            get_common_data(message.from_user.id, cursor,
                            'new_event_name', 'new_event_describe_dp', 'last_page_choose_events',
                            'adding_event_sett_from_block')
        event_kb = InlineKeyboardMarkup()

        # ошибки
        if len(message.text) > 15 or '<' in message.text or '>' in message.text:

            if not new_event_name:
                event_kb.row(
                    InlineKeyboardButton(back_mes, callback_data=f'{last_page_choose_events}_page_to_event'))
            else:
                event_kb.row(
                    InlineKeyboardButton(back_mes, callback_data=f'{last_page_choose_events}_page_to_event'),
                    InlineKeyboardButton('➡️', callback_data='to_new_event_describe_dp'))

            # too long
            if len(message.text) > 15:
                text_for = '❗<b>Максимальная длина названия эвента: ' \
                           f'<code>{big_replacing(15, your_dict=dict_with_bold_nums)}</code></b>\n\n' \
                           f'📌<b>Пожалуйста, укротите название!</b>'

            # плохие символы
            else:
                text_for = '❗<b>В названии нельзя использовать символы: ' \
                           f'<code>{quote_html("<>")}</code></b>\n\n' \
                           f'📌<b>Пожалуйста, измените название!</b>'

        # всё отлично
        else:
            await main_menu.new_event_describe_dp.set()
            save_last_state_user(message.from_user.id, 'new_event_describe_dp', cursor, conn)

            # описание ещё не было определено
            if not new_event_describe_dp:
                text_for = f'<b>❔| Что за <i>краткое описание</i> будет у эвента?</b>\n\n' \
                           f'📌<b>Максимальная длина краткого описания эвента: ' \
                           f'<code>{big_replacing(30, your_dict=dict_with_bold_nums)}</code></b>'

                event_kb.row(
                    InlineKeyboardButton('⬅️', callback_data=f'adding_event_sett'))
            else:
                text_for = f'<b>▫️НАЗВАНИЕ ЭВЕНТА:</b> \n' \
                           f'·<code>{message.text}</code>\n' \
                           f'<b>▫КРАТКОЕ ОПИСАНИЕ ЭВЕНТА:</b> \n' \
                           f'·<code>{new_event_describe_dp}</code> \n\n' \
                           f'📌<b>Вы можете изменить краткое описание, написав обновлённую версию в чат!</b>'

                event_kb.row(
                    InlineKeyboardButton('⬅️', callback_data=f'adding_event_sett'),
                    InlineKeyboardButton('➡️', callback_data='to_new_event_describe_el'))

            save_common_data(message.from_user.id, cursor, conn,
                             new_event_name=message.text)

        try:
            # НЕ пришли | пришли с блока
            text_first = f'🛠️<b>Н/С/Э/</b><i>НОВЫЙ ЭВЕНТ</i>️️\n\n' \
                if not adding_event_sett_from_block[0] else adding_event_sett_from_block[1]

            await bot.edit_message_text(f'{text_first}'
                                        f'{text_for}',
                                        chat_id=message.from_user.id,
                                        message_id=get_main_id_message(message.from_user.id, cursor),
                                        reply_markup=event_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(message.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)

    # НАСТРОЙКИ / СОСТАВ / ЭВЕНТЫ / НОВЫЙ ЭВЕНТ: КРАТКОЕ ОПИСАНИЕ_CALL
    @dp.callback_query_handler(text='to_new_event_describe_dp',
                               state=(main_menu.new_event_name, main_menu.new_event_describe_el))
    async def get_new_event_describe_dp_call(callback: CallbackQuery):
        await main_menu.new_event_describe_dp.set()
        save_last_state_user(callback.from_user.id, 'new_event_describe_dp', cursor, conn)

        # GET_COMMON_DATA
        new_event_name, new_event_describe_dp, adding_event_sett_from_block = \
            get_common_data(callback.from_user.id, cursor,
                            'new_event_name', 'new_event_describe_dp', 'adding_event_sett_from_block')

        # описание ещё не было определено
        event_kb = InlineKeyboardMarkup()
        if not new_event_describe_dp:
            text_for = f'<b>❔| Что за <i>краткое описание</i> будет у эвента?</b>\n\n' \
                       f'📌<b>Максимальная длина краткого описания эвента: ' \
                       f'<code>{big_replacing(30, your_dict=dict_with_bold_nums)}</code></b>'

            event_kb.row(
                InlineKeyboardButton('⬅️', callback_data=f'adding_event_sett'))
        else:
            text_for = f'<b>▫️НАЗВАНИЕ ЭВЕНТА:</b> \n' \
                       f'·<code>{new_event_name}</code>\n' \
                       f'<b>▫КРАТКОЕ ОПИСАНИЕ ЭВЕНТА:</b> \n' \
                       f'·<code>{new_event_describe_dp}</code> \n\n' \
                       f'📌<b>Вы можете изменить краткое описание, написав обновлённую версию в чат!</b>'

            event_kb.row(
                InlineKeyboardButton('⬅️', callback_data=f'adding_event_sett'),
                InlineKeyboardButton('➡️', callback_data='to_new_event_describe_el'))

        try:
            # НЕ пришли | пришли с блока
            text_first = f'🛠️<b>Н/С/Э/</b><i>НОВЫЙ ЭВЕНТ</i>️️\n\n' \
                if not adding_event_sett_from_block[0] else adding_event_sett_from_block[1]

            await bot.edit_message_text(f'{text_first}'
                                        f'{text_for}',
                                        chat_id=callback.from_user.id,
                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                        reply_markup=event_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageNotModified:
            await existing_work_message(message.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)

    # НАСТРОЙКИ / СОСТАВ / ЭВЕНТЫ / НОВЫЙ ЭВЕНТ: КРАТКОЕ ОПИСАНИЕ_MES
    @dp.message_handler(state=main_menu.new_event_describe_dp, content_types='text')
    async def get_new_event_describe_dp_mes(message: Message):
        await message.delete()

        # GET_COMMON_DATA
        new_event_name, new_event_describe_dp, new_event_describe_el, \
        adding_event_sett_from_block = \
            get_common_data(message.from_user.id, cursor,
                            'new_event_name', 'new_event_describe_dp', 'new_event_describe_el',
                            'adding_event_sett_from_block')

        event_kb = InlineKeyboardMarkup()

        # ошибки
        if len(message.text) > 30 or '<' in message.text or '>' in message.text:

            # при отстутствии описания
            if not new_event_describe_dp:
                event_kb.row(
                    InlineKeyboardButton('⬅️', callback_data=f'adding_event_sett'))
            else:

                event_kb.row(
                    InlineKeyboardButton('⬅️', callback_data=f'adding_event_sett'),
                    InlineKeyboardButton('➡️', callback_data='to_new_event_describe_el'))

            # too long
            if len(message.text) > 30:
                text_for = '❗<b>Максимальная длина краткого описания эвента: ' \
                           f'<code>{big_replacing(30, your_dict=dict_with_bold_nums)}</code></b>\n\n' \
                           f'📌<b>Пожалуйста, укротите краткое описание!</b>'

            # плохие символы
            else:
                text_for = '❗<b>В кратком описании нельзя использовать символы: ' \
                           f'<code>{quote_html("<>")}</code></b>\n\n' \
                           f'📌<b>Пожалуйста, измените краткое описание!</b>'

        # всё отлично
        else:
            await main_menu.new_event_describe_el.set()
            save_last_state_user(message.from_user.id, 'new_event_describe_el', cursor, conn)

            # описание ещё не было определено
            if not new_event_describe_el:
                text_for = f'<b>❔| Что за <i>полноценное описание</i> будет у эвента?</b>\n\n' \
                           f'📌<b>Максимальная длина полноценного описания у эвента: ' \
                           f'<code>{big_replacing(150, your_dict=dict_with_bold_nums)}</code></b>'

                event_kb.row(
                    InlineKeyboardButton('⬅️', callback_data=f'to_new_event_describe_dp'))
            else:
                text_for = f'<b>▫️НАЗВАНИЕ ЭВЕНТА:</b> \n' \
                           f'·<code>{new_event_name}</code>\n' \
                           f'<b>▫КРАТКОЕ ОПИСАНИЕ ЭВЕНТА:</b> \n' \
                           f'·<code>{message.text}</code> \n' \
                           f'<b>▫ПОЛНОЦЕННОЕ ОПИСАНИЕ ЭВЕНТА:</b> \n' \
                           f'·<code>{new_event_describe_el}</code> \n\n' \
                           f'📌<b>Вы можете изменить полноценное описание, написав обновлённую версию в чат!</b>'

                event_kb.row(
                    InlineKeyboardButton('⬅️', callback_data=f'to_new_event_describe_dp'),
                    InlineKeyboardButton('➡️', callback_data='to_new_event_time_work'))

            save_common_data(message.from_user.id, cursor, conn,
                             new_event_describe_dp=message.text)

        try:
            # НЕ пришли | пришли с блока
            text_first = f'🛠️<b>Н/С/Э/</b><i>НОВЫЙ ЭВЕНТ</i>️️\n\n' \
                if not adding_event_sett_from_block[0] else adding_event_sett_from_block[1]

            await bot.edit_message_text(f'{text_first}'
                                        f'{text_for}',
                                        chat_id=message.from_user.id,
                                        message_id=get_main_id_message(message.from_user.id, cursor),
                                        reply_markup=event_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(message.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)

    # НАСТРОЙКИ / СОСТАВ / ЭВЕНТЫ / НОВЫЙ ЭВЕНТ: ПОЛНОЦЕННОЕ ОПИСАНИЕ_CALL
    @dp.callback_query_handler(text='to_new_event_describe_el',
                               state=(main_menu.new_event_describe_dp, main_menu.user_sett))
    async def get_new_event_describe_el_call(callback: CallbackQuery):
        await main_menu.new_event_describe_el.set()
        save_last_state_user(callback.from_user.id, 'new_event_describe_el', cursor, conn)

        # GET_COMMON_DATA
        new_event_name, new_event_describe_dp, new_event_describe_el, \
        adding_event_sett_from_block = \
            get_common_data(callback.from_user.id, cursor,
                            'new_event_name', 'new_event_describe_dp', 'new_event_describe_el',
                            'adding_event_sett_from_block')

        # описание ещё не было определено
        event_kb = InlineKeyboardMarkup()
        if not new_event_describe_el:
            text_for = f'<b>❔| Что за <i>полноценное описание</i> будет у эвента?</b>\n\n' \
                       f'📌<b>Максимальная длина полноценного описания у эвента: ' \
                       f'<code>{big_replacing(150, your_dict=dict_with_bold_nums)}</code></b>'

            event_kb.row(
                InlineKeyboardButton('⬅️', callback_data=f'to_new_event_describe_dp'))
        else:
            text_for = f'<b>▫️НАЗВАНИЕ ЭВЕНТА:</b> \n' \
                       f'·<code>{new_event_name}</code>\n' \
                       f'<b>▫КРАТКОЕ ОПИСАНИЕ ЭВЕНТА:</b> \n' \
                       f'·<code>{new_event_describe_dp}</code> \n' \
                       f'<b>▫ПОЛНОЦЕННОЕ ОПИСАНИЕ ЭВЕНТА:</b> \n' \
                       f'·<code>{new_event_describe_el}</code> \n\n' \
                       f'📌<b>Вы можете изменить полноценное описание, написав обновлённую версию в чат!</b>'

            event_kb.row(
                InlineKeyboardButton('⬅️', callback_data=f'to_new_event_describe_dp'),
                InlineKeyboardButton('➡️', callback_data='to_new_event_time_work'))

        try:
            # НЕ пришли | пришли с блока
            text_first = f'🛠️<b>Н/С/Э/</b><i>НОВЫЙ ЭВЕНТ</i>️️\n\n' \
                if not adding_event_sett_from_block[0] else adding_event_sett_from_block[1]

            await bot.edit_message_text(f'{text_first}'
                                        f'{text_for}',
                                        chat_id=callback.from_user.id,
                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                        reply_markup=event_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(message.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)

    # НАСТРОЙКИ / СОСТАВ / ЭВЕНТЫ / НОВЫЙ ЭВЕНТ: ПОЛНОЦЕННОЕ ОПИСАНИЕ_MES
    @dp.message_handler(state=main_menu.new_event_describe_el, content_types='text')
    async def get_new_event_describe_el_mes(message: Message):
        await message.delete()

        # GET_COMMON_DATA
        new_event_name, new_event_describe_dp, new_event_describe_el, \
        new_event_time_work, adding_event_sett_from_block = \
            get_common_data(message.from_user.id, cursor,
                            'new_event_name', 'new_event_describe_dp', 'new_event_describe_el',
                            'new_event_time_work', 'adding_event_sett_from_block')

        # ошибки
        if len(message.text) > 150 or '<' in message.text or '>' in message.text:

            event_kb = InlineKeyboardMarkup()
            # при отстутствии описания
            if not new_event_time_work:
                event_kb.row(
                    InlineKeyboardButton('⬅️', callback_data=f'to_new_event_describe_dp'))
            else:
                event_kb.row(
                    InlineKeyboardButton('⬅️', callback_data=f'to_new_event_describe_dp'),
                    InlineKeyboardButton('➡️', callback_data='to_new_event_time_work'))

            # too long
            if len(message.text) > 150:
                text_for = '❗<b>Максимальная длина полноценного описания эвента: ' \
                           f'<code>{big_replacing(150, your_dict=dict_with_bold_nums)}</code></b>\n\n' \
                           f'📌<b>Пожалуйста, укротите полноценное описание!</b>'

            # плохие символы
            else:
                text_for = '❗<b>В полноценном описании нельзя использовать символы: ' \
                           f'<code>{quote_html("<>")}</code></b>\n\n' \
                           f'📌<b>Пожалуйста, измените полноценное описание!</b>'

        # всё отлично
        else:
            await main_menu.user_sett.set()
            save_last_state_user(message.from_user.id, 'user_sett', cursor, conn)

            event_kb = \
                get_new_event_time_work_kb(new_event_time_work)

            # описание ещё не было определено
            if not new_event_time_work:
                text_for = f'<b>❔| Сколько времени будет занимать выполнение данного эвента?</b>\n'

            else:
                text_for = f'<b>▫️НАЗВАНИЕ ЭВЕНТА:</b> \n' \
                           f'·<code>{new_event_name}</code>\n' \
                           f'<b>▫КРАТКОЕ ОПИСАНИЕ ЭВЕНТА:</b> \n' \
                           f'·<code>{new_event_describe_dp}</code> \n' \
                           f'<b>▫ПОЛНОЦЕННОЕ ОПИСАНИЕ ЭВЕНТА:</b> \n' \
                           f'·<code>{message.text}</code> \n' \
                           f'<b>▫ВРЕМЯ ВЫПОЛНЕНИЯ ЭВЕНТА:</b> \n' \
                           f'·<code>{new_event_time_work}</code>\n\n' \
                           f'📌<b>Установите необходимое время выполнения!</b>'

            save_common_data(message.from_user.id, cursor, conn,
                             new_event_describe_el=message.text)

        try:
            # НЕ пришли | пришли с блока
            text_first = f'🛠️<b>Н/С/Э/</b><i>НОВЫЙ ЭВЕНТ</i>️️\n\n' \
                if not adding_event_sett_from_block[0] else adding_event_sett_from_block[1]

            await bot.edit_message_text(f'{text_first}'
                                        f'{text_for}',
                                        chat_id=message.from_user.id,
                                        message_id=get_main_id_message(message.from_user.id, cursor),
                                        reply_markup=event_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(message.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)

    # НАСТРОЙКИ / СОСТАВ / ЭВЕНТЫ / НОВЫЙ ЭВЕНТ: TIME_WORK
    @dp.callback_query_handler(text='to_new_event_time_work',
                               state=(main_menu.new_event_describe_el, main_menu.user_sett))
    @dp.callback_query_handler(Text(startswith='sett_time'), state=main_menu.user_sett)
    async def work_with_time_work(callback: CallbackQuery):

        await main_menu.user_sett.set()
        save_last_state_user(callback.from_user.id, 'user_sett', cursor, conn)

        # GET_COMMON_DATA
        new_event_name, new_event_describe_dp, new_event_describe_el, \
        new_event_time_work, adding_event_sett_from_block = \
            get_common_data(callback.from_user.id, cursor,
                            'new_event_name', 'new_event_describe_dp', 'new_event_describe_el',
                            'new_event_time_work', 'adding_event_sett_from_block')

        # если изменился time_work
        if '+' in callback.data:
            new_event_time_work += int(callback.data[10:])
        elif '-' in callback.data:
            new_event_time_work -= int(callback.data[10:])
            if new_event_time_work < 0:
                new_event_time_work = 0
                await callback.answer('Время выполнения не может быть меньше нуля!')

        try:
            # НЕ пришли | пришли с блока
            text_first = f'🛠️<b>Н/С/Э/</b><i>НОВЫЙ ЭВЕНТ</i>️️\n\n' \
                if not adding_event_sett_from_block[0] else adding_event_sett_from_block[1]

            await bot.edit_message_text(f'{text_first}'
                                        f'<b>▫️НАЗВАНИЕ ЭВЕНТА:</b> \n'
                                        f'·<code>{new_event_name}</code>\n'
                                        f'<b>▫КРАТКОЕ ОПИСАНИЕ ЭВЕНТА:</b> \n'
                                        f'·<code>{new_event_describe_dp}</code> \n'
                                        f'<b>▫ПОЛНОЦЕННОЕ ОПИСАНИЕ ЭВЕНТА:</b> \n'
                                        f'·<code>{new_event_describe_el}</code> \n'
                                        f'<b>▫ВРЕМЯ ВЫПОЛНЕНИЯ ЭВЕНТА:</b> \n'
                                        f'·<code>{new_event_time_work}</code>\n\n'
                                        f'📌<b>Установите необходимое время выполнения!</b>',
                                        chat_id=callback.from_user.id,
                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                        reply_markup=
                                        get_new_event_time_work_kb(new_event_time_work),
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(callback.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)

        except MessageNotModified:
            pass

        save_common_data(callback.from_user.id, cursor, conn,
                         new_event_time_work=new_event_time_work)

    # НАСТРОЙКИ / СОСТАВ / ЭВЕНТЫ / НОВЫЙ ЭВЕНТ: FINAL_ADDING
    @dp.callback_query_handler(text='end_process_adding_event',
                               state=main_menu.user_sett)
    async def final_adding_new_event(callback: CallbackQuery):

        # GET_COMMON_DATA
        new_event_name, new_event_describe_dp, new_event_describe_el, \
        new_event_time_work, adding_event_sett_from_block = \
            get_common_data(callback.from_user.id, cursor,
                            'new_event_name', 'new_event_describe_dp', 'new_event_describe_el',
                            'new_event_time_work', 'adding_event_sett_from_block')

        event_kb = \
            row_buttons(get_button('⬅️', callback_data='to_new_event_time_work'),
                                   your_kb=yes_or_no_kb('yes_adding_this_event' if not adding_event_sett_from_block[0]
                                                        else 'yes_adding_this_event_from_block',
                                                        'no_adding_this_event' if not adding_event_sett_from_block[0]
                                                        else 'no_adding_this_event_from_block'))

        # НЕ пришли | пришли с блока
        text_first = f'🛠️<b>Н/С/Э/</b><i>НОВЫЙ ЭВЕНТ</i>️️\n\n' \
            if not adding_event_sett_from_block[0] else adding_event_sett_from_block[1]

        await bot.edit_message_text(f'{text_first}'
                                    f'<b>▫️НАЗВАНИЕ ЭВЕНТА:</b> \n'
                                    f'·<code>{new_event_name}</code>\n'
                                    f'<b>▫КРАТКОЕ ОПИСАНИЕ ЭВЕНТА:</b> \n'
                                    f'·<code>{new_event_describe_dp}</code> \n'
                                    f'<b>▫ПОЛНОЦЕННОЕ ОПИСАНИЕ ЭВЕНТА:</b> \n'
                                    f'·<code>{new_event_describe_el}</code> \n'
                                    f'<b>▫ВРЕМЯ ВЫПОЛНЕНИЯ ЭВЕНТА:</b> \n'
                                    f'·<code>{new_event_time_work}</code>\n\n'
                                    f'❓<b>Создать эвент с данными параметрами?</b>',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=event_kb,
                                    parse_mode=ParseMode.HTML)

    # НАСТРОЙКИ / СОСТАВ / ЭВЕНТЫ / ОДИН ЭВЕНТ
    @dp.callback_query_handler(text='back_to_one_event', state=main_menu.user_sett)
    @dp.callback_query_handler(text='yes_minus_block_from_event', state=main_menu.user_sett)
    @dp.callback_query_handler(text='yes_connect_block_with_event', state=main_menu.user_sett)
    @dp.callback_query_handler(Text(endswith='_choose_event'), state=main_menu.user_sett)
    async def one_event_sett(callback: CallbackQuery):

        # GET_COMMON_DATA
        login_user, last_page_choose_events, work_element, \
        connect_code_block_now, bot_id = \
            get_common_data(callback.from_user.id, cursor,
                            'login_user', 'last_page_choose_events', 'work_element',
                            'connect_code_block_now', 'bot_id')

        # если выбираем эвент
        if '_choose_event' in callback.data \
                or callback.data in ('yes_minus_block_from_event', 'yes_connect_block_with_event'):

            # выбрали эвент
            if '_choose_event' in callback.data:

                code_event, event_name, text_for, one_event_kb, its_block_code = \
                    get_data_one_event(callback.from_user.id, cursor, conn, callback.data[:-13],
                                       bot_id,
                                       last_page_choose_events)

            # соединение блока
            elif callback.data == 'yes_connect_block_with_event':
                code_event, event_name, text_for, one_event_kb, its_block_code = work_element

                # подключаемся к бд пользователя
                one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                                check_same_thread=False)
                one_user_cursor = one_user_conn.cursor()

                # обновляем связь эвент с блоком
                one_user_cursor.execute('UPDATE classification_of_events SET its_code_block = ? '
                                        'WHERE code_element = ?',
                                        (connect_code_block_now, code_event,))

                # добавляем эвент к блоку
                one_user_cursor.execute('SELECT content, physics_cycle '
                                        'FROM classification_of_blocks WHERE code_element = ?',
                                        (connect_code_block_now,))
                content_block, physics_cycle = one_user_cursor.fetchone()
                content_block, physics_cycle = \
                    ast.literal_eval(content_block), ast.literal_eval(physics_cycle)
                content_block.append(code_event)

                one_user_cursor.execute('UPDATE classification_of_blocks SET content = ? WHERE code_element = ?',
                                        (str(content_block), connect_code_block_now,))

                # берём иерархию только тех дней, которые в physics_cycle блока
                only_active_days_block = \
                    lambda between: f"{between}".join([f"week_day_{day_week}" for day_week in physics_cycle])

                # находим активные в бд
                one_user_cursor.execute(f'''SELECT {only_active_days_block(', ')} FROM hierarchy_day_plans''')
                week_deals = one_user_cursor.fetchone()

                # если есть вообще строки в бд
                if week_deals:
                    hierarchy_day_plans = list(week_deals)
                else:
                    hierarchy_day_plans = [None for _ in physics_cycle]

                # добавляем эвент в конец иерархии каждого дня physics_cycle
                for ind_week, days_week_data in enumerate(hierarchy_day_plans):

                    # если уже были добавлены дни
                    if days_week_data:
                        days_week_list = ast.literal_eval(days_week_data)
                    else:
                        days_week_list = []
                    days_week_list.append(code_event)

                    hierarchy_day_plans[ind_week] = str(days_week_list)

                # обновляем иерархию эвентов
                if week_deals:
                    one_user_cursor.execute(f'''UPDATE hierarchy_day_plans SET 
                                                                {only_active_days_block(' = ?, ')} = ?''',
                                            hierarchy_day_plans)
                else:
                    one_user_cursor.execute(f'INSERT INTO hierarchy_day_plans ({only_active_days_block(", ")}) '
                                            f'VALUES ({", ".join("?" for _ in physics_cycle)})', hierarchy_day_plans)

                one_user_conn.commit()

                _, event_name, text_for, one_event_kb, _ = \
                    get_data_one_event(callback.from_user.id, cursor, conn, code_event,
                                       bot_id,
                                       last_page_choose_events)

                await callback.answer('Эвент соединён с блоком!')

            # лишили блока
            else:

                code_event, event_name, text_for, one_event_kb, its_block_code = work_element

                # подключаемся к бд пользователя
                one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                                check_same_thread=False)
                one_user_cursor = one_user_conn.cursor()

                # обновляем связь эвент с блоком
                one_user_cursor.execute('UPDATE classification_of_events SET its_code_block = ? '
                                        'WHERE code_element = ?',
                                        (None, code_event,))

                # если эвент в блоке
                if its_block_code:
                    # удаляем эвент из блока
                    one_user_cursor.execute('SELECT content FROM classification_of_blocks WHERE code_element = ?',
                                            (its_block_code,))
                    content_block = ast.literal_eval(one_user_cursor.fetchone()[0])
                    content_block.remove(code_event)

                    one_user_cursor.execute('UPDATE classification_of_blocks SET content = ? WHERE code_element = ?',
                                            (str(content_block), its_block_code,))

                    # удаляем эвент из DAY PLAN
                    one_user_cursor.execute('SELECT * FROM hierarchy_day_plans')
                    hierarchy_day_plans = one_user_cursor.fetchone()

                    if hierarchy_day_plans:
                        hierarchy_day_plans = list(hierarchy_day_plans)
                        # находим размещение эвентов на каждом дне и убираем оттуда эвент
                        for ind_week, day_week_data in enumerate(hierarchy_day_plans):

                            # если эвент есть в данном дне
                            if day_week_data:
                                day_week_list = ast.literal_eval(day_week_data)
                                if code_event in day_week_list:
                                    day_week_list.remove(code_event)
                                hierarchy_day_plans[ind_week] = str(day_week_list)

                        # обновляем иерархию эвентов
                        one_user_cursor.execute('''UPDATE hierarchy_day_plans SET 
                                   week_day_0 = ?, week_day_1 = ?, week_day_2 = ?, week_day_3 = ?, 
                                   week_day_4 = ?, week_day_5 = ?, week_day_6 = ?''', hierarchy_day_plans)

                    one_user_conn.commit()

                _, event_name, text_for, one_event_kb, _ = \
                    get_data_one_event(callback.from_user.id, cursor, conn, code_event,
                                       bot_id,
                                       last_page_choose_events)

                await callback.answer('Эвент лишён блока!')

        else:

            # уже выбрали из возвращаемся
            _, event_name, text_for, one_event_kb, _ = \
                work_element

        await bot.edit_message_text(f'🛠️<b>Н/С/Э/</b><i>{event_name}</i>️️\n\n'
                                    f'{text_for}',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=one_event_kb,
                                    parse_mode=ParseMode.HTML)

    # НАСТРОЙКИ / СОСТАВ / ЭВЕНТЫ / ОДИН ЭВЕНТ / УДАЛЕНИЕ
    @dp.callback_query_handler(text='delete_event', state=main_menu.user_sett)
    async def one_event_delete_sett(callback: CallbackQuery):

        # GET_COMMON_DATA
        _, event_name, text_for, *_ = \
            get_common_data(callback.from_user.id, cursor,
                            'work_element')

        await bot.edit_message_text(f'🛠️<b>Н/С/Э/{event_name[0]}.../</b><i>УДАЛЕНИЕ</i>️️\n\n'
                                    f'{text_for}\n'
                                    f'❓| <b>Вы хотите удалить этот эвент из системы DAY PLAN?</b>',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=yes_or_no_kb('yes_delete_event', 'back_to_one_event'),
                                    parse_mode=ParseMode.HTML)

    # НАСТРОЙКИ / СОСТАВ / ЭВЕНТЫ / ОДИН ЭВЕНТ / (СВЯЗАТЬ | ЛИШИТЬ) БЛОКА
    @dp.callback_query_handler(text=('add_block_from_event', 'minus_block_from_event'), state=main_menu.user_sett)
    @dp.callback_query_handler(Text(endswith='_page_block_from_event'), state=main_menu.user_sett)
    async def minus_plus_block_from_event(callback: CallbackQuery):

        # GET_COMMON_DATA
        work_element, login_user, data_blocks_from_event_kb, \
        last_page_blocks_from_event, bot_id = \
            get_common_data(callback.from_user.id, cursor,
                            'work_element', 'login_user', 'data_blocks_from_event_kb',
                            'last_page_blocks_from_event', 'bot_id')
        code_event, event_name, text_for, one_event_kb, its_block_code = work_element

        # лишаем блока
        if callback.data == 'minus_block_from_event':
            to_continue_text = 'ЛИШИТЬ БЛОКА'
            text_for += '\n❓| <b>Вы хотите лишить этот эвент блока?</b>'
            minus_or_plus_emoji_kb = yes_or_no_kb('yes_minus_block_from_event', 'back_to_one_event')

        # добавляем эмоджи
        else:
            to_continue_text = 'СВЯЗАТЬ С БЛОКОМ'
            text_for += '\n📌<b>Выберите один из блоков!</b>'
            last_page_blocks_from_event, \
            minus_or_plus_emoji_kb = \
                with_choosing_elements_kb(callback.from_user.id,
                                          bot_id,
                                          cursor, conn,
                                          work_with_event=False,
                                          your_data_save=data_blocks_from_event_kb,
                                          your_save_name='data_blocks_from_event_kb',
                                          last_page=last_page_blocks_from_event,
                                          with_page_call='_page_block_from_event',
                                          with_element_call='_to_one_block_from_event',
                                          back_callback='back_to_one_event',
                                          callback_data=callback.data,
                                          sql_request='''SELECT code_element, block_emoji, 
                                                        name_dp FROM classification_of_blocks''')

            save_common_data(callback.from_user.id, cursor, conn,
                             last_page_blocks_from_event=last_page_blocks_from_event)

        await bot.edit_message_text(f'🛠️<b>Н/С/Э/{event_name[0]}.../</b><i>{to_continue_text}</i>️️\n\n'
                                    f'{text_for}\n',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=minus_or_plus_emoji_kb,
                                    parse_mode=ParseMode.HTML)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / ОДИН БЛОК
    @dp.callback_query_handler(Text(endswith='_to_one_block_from_event'), state=main_menu.user_sett)
    async def one_block_sett(callback: CallbackQuery):

        # GET_COMMON_DATA
        login_user, work_element, \
        last_page_blocks_from_event, data_one_block_from_emoji, bot_id = \
            get_common_data(callback.from_user.id, cursor,
                            'login_user', 'work_element',
                            'last_page_blocks_from_event', 'data_one_block_from_emoji', 'bot_id')

        code_connect_block = callback.data[:-24]
        code_event, event_name, *_ = work_element

        # находим с данными выбранного блока
        one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                        check_same_thread=False)
        one_user_cursor = one_user_conn.cursor()
        one_user_cursor.execute(
            '''SELECT block_emoji, name_dp, description_element, physics_cycle, content 
            FROM classification_of_blocks WHERE code_element = ?''', (code_connect_block,))
        data_block = one_user_cursor.fetchone()

        # None | изменились данные
        if not data_one_block_from_emoji or data_one_block_from_emoji[0] != data_block:

            block_emoji, block_name, block_describe_el, block_days_work, _ = \
                data_block

            # формируем текст для запоминания
            text_another = f'<b>| ️ВЫБРАННЫЙ БЛОК | ️</b>\n' \
                       f'<b>{str(block_name).upper()}</b>' \
                       f' 【{block_emoji}】\n' \
                       f'<i>{str(block_describe_el).capitalize()}</i>\n' \
                       f'▫️<b>Рабочие дни: </b>' \
                       f'<code>' \
                       f'{", ".join([short_name_week_days[one_day] for one_day in ast.literal_eval(block_days_work)])}'\
                       f'</code>'

            # определяемся с текстом сообщения
            text_another += '\n\n❔| <b>Хотите связать этот блок с эвентом?</b>'
            one_kb = yes_or_no_kb('yes_connect_block_with_event',
                                  f'{last_page_blocks_from_event}_page_block_from_event')

            data_one_block_from_emoji = [data_block, text_another, one_kb]

        else:
            text_another, one_kb = data_one_block_from_emoji[1:]

        await bot.edit_message_text(f'🛠️<b>Н/С/Э/{event_name[0]}.../СБ/</b><i>{data_block[0]}</i>️️\n\n'
                                    f'{text_another}',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=one_kb,
                                    parse_mode=ParseMode.HTML)

        save_common_data(callback.from_user.id, cursor, conn,
                         connect_code_block_now=code_connect_block,
                         data_one_block_from_emoji=data_one_block_from_emoji)

    # НАСТРОЙКИ / СОСТАВ / ЭВЕНТЫ / ОДИН ЭВЕНТ / РЕДАКТИРОВАНИЕ
    @dp.callback_query_handler(text='edit_event',
                               state=(main_menu.user_sett, main_menu.edit_parameters_event))
    @dp.callback_query_handler(text='update_time_work', state=main_menu.user_sett)
    async def edit_event_sett(callback: CallbackQuery):
        await main_menu.user_sett.set()
        save_last_state_user(callback.from_user.id, 'user_sett', cursor, conn)

        # GET_COMMON_DATA
        work_element, login_user, edit_time_work, \
        last_page_choose_events, bot_id = \
            get_common_data(callback.from_user.id, cursor,
                            'work_element', 'login_user', 'edit_time_work',
                            'last_page_choose_events', 'bot_id')
        code_el, event_name, text_for, *_ = work_element

        # изменение time_work
        if callback.data == 'update_time_work':
            one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db', check_same_thread=False)
            one_user_cursor = one_user_conn.cursor()

            one_user_cursor.execute('''UPDATE classification_of_events SET time_of_doing = ? 
                                    WHERE code_element = ?''', (edit_time_work, code_el,))
            one_user_conn.commit()

            _, event_name, text_for, *_ = \
                get_data_one_event(callback.from_user.id, cursor, conn, code_el,
                                   bot_id, last_page_choose_events)

        await bot.edit_message_text(f'🛠️<b>Н/С/Э/{event_name[0]}.../</b><i>РЕДАКТИРОВАНИЕ</i>️️\n\n'
                                    f'{text_for}\n'
                                    f'❔| <b>Какие параметры эвента вы хотите изменить?</b>',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=edit_event_sett_kb,
                                    parse_mode=ParseMode.HTML)

    # НАСТРОЙКИ / СОСТАВ / ЭВЕНТЫ / ОДИН ЭВЕНТ / РЕДАКТИРОВАНИЕ / ACTION
    @dp.callback_query_handler(text=('edit_name_event', 'edit_short_description_event',
                                     'edit_long_description_event', 'edit_time_work'),
                               state=main_menu.user_sett)
    async def edit_event_action_sett(callback: CallbackQuery):

        # GET_COMMON_DATA
        work_element, edit_time_work, login_user, bot_id = \
            get_common_data(callback.from_user.id, cursor,
                            'work_element', 'edit_time_work', 'login_user', 'bot_id')
        code_element, event_name, *_ = work_element

        edit_event_action_kb = InlineKeyboardMarkup()
        if callback.data != 'edit_time_work':
            await main_menu.edit_parameters_event.set()
            save_last_state_user(callback.from_user.id, 'edit_parameters_event', cursor, conn)

            if callback.data == 'edit_name_event':
                to_continue = 'НАЗВАНИЕ'

                text_edit = '<b>❕| Обновите название эвента!</b>\n\n' \
                            f'📌<b>Максимальная длина названия эвента: ' \
                            f'<code>{big_replacing(15, your_dict=dict_with_bold_nums)}</code></b>'

            elif callback.data == 'edit_short_description_event':
                to_continue = 'КРАТКОЕ ОПИСАНИЕ'

                text_edit = f'<b>❕| Обновите <i>краткое описание</i> эвента!</b>\n\n' \
                            f'📌<b>Максимальная длина краткого описания эвента: ' \
                            f'<code>{big_replacing(30, your_dict=dict_with_bold_nums)}</code></b>'

            else:
                to_continue = 'ПОЛНОЦЕННОЕ ОПИСАНИЕ'

                text_edit = f'<b>❕| Обновите <i>полноценное описание</i> эвента!</b>\n\n' \
                            f'📌<b>Максимальная длина полноценного описания у эвента: ' \
                            f'<code>{big_replacing(150, your_dict=dict_with_bold_nums)}</code></b>'

        else:
            to_continue = 'ВРЕМЯ ВЫПОЛНЕНИЯ'
            text_edit = f'❕| <b>Установите необходимое время выполнения!</b>'

            # находим время выполнения эвента
            one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db', check_same_thread=False)
            one_user_cursor = one_user_conn.cursor()
            event_time_work = \
                one_user_cursor.execute('''SELECT time_of_doing FROM classification_of_events 
                                        WHERE code_element = ?''', (code_element,)).fetchone()[0]
            edit_event_action_kb = \
                get_new_event_time_work_kb(event_time_work, add_callback='process_editing_time_work')

            save_common_data(callback.from_user.id, cursor, conn,
                             edit_time_work=event_time_work,
                             old_time_work=event_time_work)

        try:
            await bot.edit_message_text(f'🛠️<b>Н/С/Э/{event_name[0]}.../Р/</b><i>{to_continue}</i>️️\n\n'
                                        f'{text_edit}\n',
                                        chat_id=callback.from_user.id,
                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                        reply_markup=edit_event_action_kb.
                                        add(InlineKeyboardButton(back_mes, callback_data='edit_event')),
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(callback.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)
        save_common_data(callback.from_user.id, cursor, conn, act_edit=callback.data)

    # НАСТРОЙКИ / СОСТАВ / ЭВЕНТЫ / ОДИН ЭВЕНТ / РЕДАКТИРОВАНИЕ / ACTION / TIME_WORK
    @dp.callback_query_handler(Text(startswith='process_editing_time_work'),
                               state=main_menu.user_sett)
    async def process_editing_time_work(callback: CallbackQuery):
        # GET_COMMON_DATA
        work_element, edit_time_work, old_time_work = \
            get_common_data(callback.from_user.id, cursor,
                            'work_element', 'edit_time_work', 'old_time_work')
        _, event_name, *_ = work_element

        # если изменился time_work
        if '+' in callback.data:
            edit_time_work += int(callback.data[26:])
        elif '-' in callback.data:
            edit_time_work -= int(callback.data[26:])
            if edit_time_work < 0:
                edit_time_work = 0
                await callback.answer('Время выполнения не может быть меньше нуля!')

        edit_time_work_kb = \
            get_new_event_time_work_kb(edit_time_work, add_callback='process_editing_time_work')

        # если пользователь изменил время
        if old_time_work != edit_time_work:
            edit_time_work_kb.add(InlineKeyboardButton(back_mes, callback_data='edit_event'),
                                  InlineKeyboardButton('✔️ОБНОВИТЬ✔️', callback_data='update_time_work'))

        else:
            edit_time_work_kb.add(InlineKeyboardButton(back_mes,
                                                       callback_data='edit_event'))

        await bot.edit_message_text(f'🛠️<b>Н/С/Э/{event_name[0]}.../Р/</b><i>ВРЕМЯ ВЫПОЛНЕНИЯ</i>️️\n\n'
                                    f'❕| <b>Установите необходимое время выполнения!</b>',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=edit_time_work_kb,
                                    parse_mode=ParseMode.HTML)

        save_common_data(callback.from_user.id, cursor, conn,
                         edit_time_work=edit_time_work)

    # НАСТРОЙКИ / СОСТАВ / ЭВЕНТЫ / ОДИН ЭВЕНТ / РЕДАКТИРОВАНИЕ / ACTION / ANOTHER
    @dp.message_handler(state=main_menu.edit_parameters_event, content_types='text')
    async def get_edit_parameters_event(message: Message):
        await message.delete()

        # GET_COMMON_DATA
        work_element, act_edit, login_user, \
        last_page_choose_events, bot_id = \
            get_common_data(message.from_user.id, cursor,
                            'work_element', 'act_edit', 'login_user',
                            'last_page_choose_events', 'bot_id')
        code_element, event_name, *_ = work_element

        max_lens_actions_edit_event = {'edit_name_event': 15,
                                       'edit_short_description_event': 30,
                                       'edit_long_description_event': 150}

        # ошибки
        if len(message.text) > max_lens_actions_edit_event.get(act_edit) \
                or '<' in message.text or '>' in message.text:

            if act_edit == 'edit_name_event':
                to_continue = 'НАЗВАНИЕ'

                if len(message.text) > 15:
                    text_for = '❗<b>Максимальная длина названия эвента: ' \
                               f'<code>{big_replacing(15, your_dict=dict_with_bold_nums)}</code></b>\n\n' \
                               f'📌<b>Пожалуйста, укротите название!</b>'

                # плохие символы
                else:
                    text_for = '❗<b>В названии нельзя использовать символы: ' \
                               f'<code>{quote_html("<>")}</code></b>\n\n' \
                               f'📌<b>Пожалуйста, измените название!</b>'

            elif act_edit == 'edit_short_description_event':
                to_continue = 'КРАТКОЕ ОПИСАНИЕ'

                if len(message.text) > 30:
                    text_for = '❗<b>Максимальная длина краткого описания эвента: ' \
                               f'<code>{big_replacing(30, your_dict=dict_with_bold_nums)}</code></b>\n\n' \
                               f'📌<b>Пожалуйста, укротите краткое описание!</b>'

                # плохие символы
                else:
                    text_for = '❗<b>В кратком описании нельзя использовать символы: ' \
                               f'<code>{quote_html("<>")}</code></b>\n\n' \
                               f'📌<b>Пожалуйста, измените краткое описание!</b>'

            else:
                to_continue = 'ПОЛНОЦЕННОЕ ОПИСАНИЕ'

                if len(message.text) > 150:
                    text_for = '❗<b>Максимальная длина полноценного описания эвента: ' \
                               f'<code>{big_replacing(150, your_dict=dict_with_bold_nums)}</code></b>\n\n' \
                               f'📌<b>Пожалуйста, укротите полноценное описание!</b>'

                # плохие символы
                else:
                    text_for = '❗<b>В полноценном описании нельзя использовать символы: ' \
                               f'<code>{quote_html("<>")}</code></b>\n\n' \
                               f'📌<b>Пожалуйста, измените полноценное описание!</b>'

            try:
                await bot.edit_message_text(f'🛠️<b>Н/С/Э/{event_name[0]}.../Р/</b><i>{to_continue}</i>️️\n\n'
                                            f'{text_for}\n',
                                            chat_id=callback.from_user.id,
                                            message_id=get_main_id_message(callback.from_user.id, cursor),
                                            reply_markup=InlineKeyboardMarkup.
                                            add(InlineKeyboardButton(back_mes, callback_data='edit_event')),
                                            parse_mode=ParseMode.HTML)
            except MessageToEditNotFound:
                await existing_work_message(message.from_user.id, bot,
                                            cursor, conn,
                                            main_menu)

        else:
            await main_menu.user_sett.set()
            save_last_state_user(message.from_user.id, 'user_sett', cursor, conn)

            # подключаемся к бд пользователя
            one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                            check_same_thread=False)
            one_user_cursor = one_user_conn.cursor()

            # понимаем, что обновили
            if act_edit == 'edit_name_event':
                update_element = 'name_dp'
            elif act_edit == 'edit_short_description_event':
                update_element = 'description_dp'
            else:
                update_element = 'description_element'

            # обновляем бд
            one_user_cursor.execute(f'''UPDATE classification_of_events SET {update_element} = ? 
                                    WHERE code_element = ?''', (message.text, code_element,))
            one_user_conn.commit()

            _, event_name, text_for, *_ = \
                get_data_one_event(message.from_user.id, cursor, conn, code_element,
                                   bot_id, last_page_choose_events)

            await bot.edit_message_text(f'🛠️<b>Н/С/Э/{event_name[0]}.../</b><i>РЕДАКТИРОВАНИЕ</i>️️\n\n'
                                        f'{text_for}\n'
                                        f'❔| <b>Какие параметры эвента вы хотите изменить?</b>',
                                        chat_id=message.from_user.id,
                                        message_id=get_main_id_message(message.from_user.id, cursor),
                                        reply_markup=edit_event_sett_kb,
                                        parse_mode=ParseMode.HTML)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ
    @dp.callback_query_handler(Text(endswith='_page_to_block'),
                               state=(main_menu.user_sett, main_menu.new_block_name))
    @dp.callback_query_handler(text="blocks_sett", state=main_menu.user_sett)
    @dp.callback_query_handler(text=('yes_adding_this_block', 'no_adding_this_block', 'yes_delete_block'),
                               state=main_menu.user_sett)
    async def choose_blocks(callback: CallbackQuery):
        await main_menu.user_sett.set()
        save_last_state_user(callback.from_user.id, 'user_sett', cursor, conn)

        # GET_COMMON_DATA
        login_user, data_blocks_kb, last_page_choose_blocks, \
        new_block_name, new_block_describe_el, \
        new_block_emoji, new_block_days_work, work_element, \
        bot_id = \
            get_common_data(callback.from_user.id, cursor,
                            'login_user', 'data_blocks_kb', 'last_page_choose_blocks',
                            'new_block_name', 'new_block_describe_el',
                            'new_block_emoji', 'new_block_days_work', 'work_element',
                            'bot_id')

        # добавили новый блок!
        if callback.data == 'yes_adding_this_block':

            # подключаемся к бд пользователя
            one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                            check_same_thread=False)
            one_user_cursor = one_user_conn.cursor()

            # обновляем список блоков
            one_user_cursor.execute(
                '''INSERT INTO classification_of_blocks (code_element, block_emoji, name_dp, 
                        description_element, physics_cycle, content) VALUES (?, ?, ?, ?, ?, ?)''',
                (str(uuid.uuid4()).replace('-', ''), new_block_emoji, new_block_name,
                 new_block_describe_el, str(new_block_days_work[0]), '[]'))
            one_user_conn.commit()

            await callback.answer('Список блоков обновлён!')

        # удаляем блок
        elif callback.data == 'yes_delete_block':

            block_code, block_emoji, block_name, text_for, \
            one_kb, block_days_work, block_content = \
                work_element

            # подключаемся к бд пользователя
            one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                            check_same_thread=False)
            one_user_cursor = one_user_conn.cursor()

            # обновляем все связи эвентов, где был этот блок
            one_query = f'''UPDATE classification_of_events SET its_code_block = ?
                                    WHERE code_element IN %s''' % \
                        f'''({", ".join(f"'{el}'" for el in block_content)})'''
            one_user_cursor.execute(one_query, (None,))

            # удаляем блок
            one_user_cursor.execute('DELETE FROM classification_of_blocks WHERE code_element = ?',
                                    (block_code,))

            # берём иерархию только тех дней, которые в block_days_work блока
            only_active_days_block = \
                lambda between: f"{between}".join([f"week_day_{day_week}" for day_week in block_days_work])

            # находим активные в бд
            one_user_cursor.execute(f'''SELECT {only_active_days_block(', ')} FROM hierarchy_day_plans''')
            week_data = one_user_cursor.fetchone()

            if week_data:
                hierarchy_day_plans = list(week_data)

                # добавляем эвент в конец иерархии каждого дня block_days_work
                for ind_week, days_week_data in enumerate(hierarchy_day_plans):
                    # только эвенты, которые НЕ эвенты данного блока
                    hierarchy_day_plans[ind_week] = \
                        str(list(set(ast.literal_eval(days_week_data)) ^ set(block_content)))

                # обновляем иерархию эвентов
                one_user_cursor.execute(f'''UPDATE hierarchy_day_plans SET {only_active_days_block(' = ?, ')} = ?''',
                                        hierarchy_day_plans)
            one_user_conn.commit()

            await callback.answer('Список блоков обновлён!')

        # формируем КБ
        message_pages, \
        choose_blocks_sett_kb = \
            with_choosing_elements_kb(callback.from_user.id,
                                      bot_id,
                                      cursor, conn,
                                      work_with_event=False,
                                      your_data_save=data_blocks_kb,
                                      your_save_name='data_blocks_kb',
                                      last_page=last_page_choose_blocks,
                                      with_page_call='_page_to_block',
                                      with_element_call='_choose_block',
                                      back_callback='compound_dp',
                                      callback_data=callback.data,
                                      list_with_first_button=
                                      [get_button('➕ДОБАВИТЬ БЛОК➕', callback_data='adding_block_sett')],
                                      sql_request='''SELECT code_element, block_emoji, 
                                                    name_dp FROM classification_of_blocks''')

        await bot.edit_message_text(f'🛠️<b>Н/С/</b><i>БЛОКИ</i>️️\n\n'
                                    f'<b>📌Выберите блок или создайте новый!</b>',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=choose_blocks_sett_kb,
                                    parse_mode=ParseMode.HTML)

        save_common_data(callback.from_user.id, cursor, conn,
                         last_page_choose_blocks=message_pages,
                         new_block_name=None,
                         new_block_describe_dp=None,
                         new_block_describe_el=None,
                         new_block_emoji=None,
                         new_block_days_work=None)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / НОВЫЙ БЛОК
    @dp.callback_query_handler(text='adding_block_sett',
                               state=(main_menu.user_sett, main_menu.new_block_describe_el))
    async def adding_block(callback: CallbackQuery):
        await main_menu.new_block_name.set()
        save_last_state_user(callback.from_user.id, 'new_block_name', cursor, conn)

        # GET_COMMON_DATA
        new_block_name, last_page_choose_blocks = \
            get_common_data(callback.from_user.id, cursor,
                            'new_block_name', 'last_page_choose_blocks')
        block_kb = InlineKeyboardMarkup()

        # name ещё не было определено
        if not new_block_name:
            text_for = '<b>❔| Как будет называться новый блок?</b>\n\n' \
                       f'📌<b>Максимальная длина названия блока: ' \
                       f'<code>{big_replacing(15, your_dict=dict_with_bold_nums)}</code></b>'

            block_kb.row(
                InlineKeyboardButton(back_mes, callback_data=f'{last_page_choose_blocks}_page_to_block'))
        else:
            text_for = f'<b>▫️НАЗВАНИЕ БЛОКА:</b> \n' \
                       f'·<code>{new_block_name}</code>\n\n' \
                       f'📌<b>Вы можете изменить название, написав обновлённую версию в чат!</b>'

            block_kb.row(
                InlineKeyboardButton(back_mes, callback_data=f'{last_page_choose_blocks}_page_to_block'),
                InlineKeyboardButton('➡️', callback_data='to_new_block_describe_el'))

        try:
            await bot.edit_message_text(f'🛠️<b>Н/С/Э/</b><i>НОВЫЙ БЛОК</i>️️\n\n'
                                        f'{text_for}',
                                        chat_id=callback.from_user.id,
                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                        reply_markup=block_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(message.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / НОВЫЙ БЛОК: ИМЯ
    @dp.message_handler(state=main_menu.new_block_name, content_types='text')
    async def get_new_name_block(message: Message):
        await message.delete()

        # GET_COMMON_DATA
        new_block_name, new_block_describe_el, last_page_choose_blocks = \
            get_common_data(message.from_user.id, cursor,
                            'new_block_name', 'new_block_describe_el', 'last_page_choose_blocks')
        block_kb = InlineKeyboardMarkup()

        # ошибки
        if len(message.text) > 15 or '<' in message.text or '>' in message.text:

            if not new_block_name:
                block_kb.row(
                    InlineKeyboardButton(back_mes, callback_data=f'{last_page_choose_blocks}_page_to_block'))
            else:
                block_kb.row(
                    InlineKeyboardButton(back_mes, callback_data=f'{last_page_choose_blocks}_page_to_block'),
                    InlineKeyboardButton('➡️', callback_data='to_new_block_describe_el'))

            # too long
            if len(message.text) > 15:
                text_for = '❗<b>Максимальная длина названия блока: ' \
                           f'<code>{big_replacing(15, your_dict=dict_with_bold_nums)}</code></b>\n\n' \
                           f'📌<b>Пожалуйста, укротите название!</b>'

            # плохие символы
            else:
                text_for = '❗<b>В названии нельзя использовать символы: ' \
                           f'<code>{quote_html("<>")}</code></b>\n\n' \
                           f'📌<b>Пожалуйста, измените название!</b>'

        # всё отлично
        else:
            await main_menu.new_block_describe_el.set()
            save_last_state_user(message.from_user.id, 'new_block_describe_el', cursor, conn)

            # описание ещё не было определено
            if not new_block_describe_el:
                text_for = f'<b>❔| Что за <i>полноценное описание</i> будет у блока?</b>\n\n' \
                           f'📌<b>Максимальная длина полноценного описания блока: ' \
                           f'<code>{big_replacing(150, your_dict=dict_with_bold_nums)}</code></b>'

                block_kb.row(
                    InlineKeyboardButton('⬅️', callback_data=f'adding_block_sett'))
            else:
                text_for = f'<b>▫️НАЗВАНИЕ БЛОКА:</b> \n' \
                           f'·<code>{message.text}</code>\n' \
                           f'<b>▫ПОЛНОЦЕННОЕ ОПИСАНИЕ БЛОКА:</b> \n' \
                           f'·<code>{new_block_describe_el}</code> \n\n' \
                           f'📌<b>Вы можете изменить полноценное описание, написав обновлённую версию в чат!</b>'

                block_kb.row(
                    InlineKeyboardButton('⬅️', callback_data=f'adding_block_sett'),
                    InlineKeyboardButton('➡️', callback_data='to_new_block_emoji'))

            save_common_data(message.from_user.id, cursor, conn,
                             new_block_name=message.text)

        try:
            await bot.edit_message_text(f'🛠️<b>Н/С/Э/</b><i>НОВЫЙ БЛОК</i>️️\n\n'
                                        f'{text_for}',
                                        chat_id=message.from_user.id,
                                        message_id=get_main_id_message(message.from_user.id, cursor),
                                        reply_markup=block_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(message.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / НОВЫЙ БЛОК:  ПОЛНОЦЕННОЕ ОПИСАНИЕ_CALL
    @dp.callback_query_handler(text='to_new_block_describe_el',
                               state=(main_menu.new_block_name, main_menu.new_block_emoji))
    async def get_new_block_describe_el_call(callback: CallbackQuery):
        await main_menu.new_block_describe_el.set()
        save_last_state_user(callback.from_user.id, 'new_block_describe_el', cursor, conn)

        # GET_COMMON_DATA
        new_block_name, new_block_describe_el = \
            get_common_data(callback.from_user.id, cursor,
                            'new_block_name', 'new_block_describe_el')

        # описание ещё не было определено
        block_kb = InlineKeyboardMarkup()
        if not new_block_describe_el:
            text_for = f'<b>❔| Что за <i>полноценное описание</i> будет у блока</b>\n\n' \
                       f'📌<b>Максимальная длина полноценного описания у блока: ' \
                       f'<code>{big_replacing(150, your_dict=dict_with_bold_nums)}</code></b>'

            block_kb.row(
                InlineKeyboardButton('⬅️', callback_data=f'to_new_block_describe_dp'))
        else:
            text_for = f'<b>▫️НАЗВАНИЕ БЛОКА:</b> \n' \
                       f'·<code>{new_block_name}</code>\n' \
                       f'<b>▫ПОЛНОЦЕННОЕ ОПИСАНИЕ БЛОКА:</b> \n' \
                       f'·<code>{new_block_describe_el}</code> \n\n' \
                       f'📌<b>Вы можете изменить полноценное описание, написав обновлённую версию в чат!</b>'

            block_kb.row(
                InlineKeyboardButton('⬅️', callback_data=f'adding_block_sett'),
                InlineKeyboardButton('➡️', callback_data='to_new_block_emoji'))

        try:
            await bot.edit_message_text(f'🛠️<b>Н/С/Э/</b><i>НОВЫЙ БЛОК</i>️️\n\n'
                                        f'{text_for}',
                                        chat_id=callback.from_user.id,
                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                        reply_markup=block_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(message.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / НОВЫЙ БЛОК: ПОЛНОЦЕННОЕ ОПИСАНИЕ_MES
    @dp.message_handler(state=main_menu.new_block_describe_el, content_types='text')
    async def get_new_block_describe_el_mes(message: Message):
        await message.delete()

        # GET_COMMON_DATA
        new_block_name, new_block_describe_el, new_block_emoji, \
        login_user, bot_id = \
            get_common_data(message.from_user.id, cursor,
                            'new_block_name', 'new_block_describe_el', 'new_block_emoji',
                            'login_user', 'bot_id')

        # ошибки
        block_kb = InlineKeyboardMarkup()
        if len(message.text) > 150 or '<' in message.text or '>' in message.text:

            # при отстутствии эмоджи
            if not new_block_emoji:
                block_kb.row(
                    InlineKeyboardButton('⬅️', callback_data=f'adding_block_sett'))
            else:
                block_kb.row(
                    InlineKeyboardButton('⬅️', callback_data=f'adding_block_sett'),
                    InlineKeyboardButton('➡️', callback_data='to_new_block_emoji'))

            # too long
            if len(message.text) > 150:
                text_for = '❗<b>Максимальная длина полноценного описания блока: ' \
                           f'<code>{big_replacing(150, your_dict=dict_with_bold_nums)}</code></b>\n\n' \
                           f'📌<b>Пожалуйста, укротите полноценное описание!</b>'

            # плохие символы
            else:
                text_for = '❗<b>В полноценном описании нельзя использовать символы: ' \
                           f'<code>{quote_html("<>")}</code></b>\n\n' \
                           f'📌<b>Пожалуйста, измените полноценное описание!</b>'

        # всё отлично
        else:
            await main_menu.new_block_emoji.set()
            save_last_state_user(message.from_user.id, 'new_block_emoji', cursor, conn)

            # описание ещё не было определено
            if not new_block_emoji:
                text_for = f'<b>❔| Что за эмоджи будет у блока?</b>\n\n' \
                           f'📌<b>Принимаются любые ранее не используемые эмоджи, за исключением следующих:\n' \
                           f'<code>⭐ | ❄️ | ❌ | 🌑</code></b>\n'

                block_kb.row(
                    InlineKeyboardButton('⬅️', callback_data=f'to_new_block_describe_el'))

            else:
                text_for = f'<b>▫️НАЗВАНИЕ БЛОКА:</b> \n' \
                           f'·<code>{new_block_name}</code>\n' \
                           f'<b>▫ПОЛНОЦЕННОЕ ОПИСАНИЕ БЛОКА:</b> \n' \
                           f'·<code>{message.text}</code> \n' \
                           f'<b>▫ЭМОДЖИ БЛОКА:</b> \n' \
                           f'·<code>{new_block_emoji}</code>\n\n' \
                           f'📌<b>Вы можете изменить эмоджи блока, написав обновлённую версию в чат!</b>'

                block_kb.row(
                    InlineKeyboardButton('⬅️', callback_data=f'to_new_block_describe_el'),
                    InlineKeyboardButton('➡️', callback_data='to_new_block_days_work'))

            # подключаемся к бд пользователя
            one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                            check_same_thread=False)
            one_user_cursor = one_user_conn.cursor()

            # создаём список уже использованных эмоджи
            already_used_emojis = \
                [one_data[0] for one_data in
                 one_user_cursor.execute('SELECT block_emoji FROM classification_of_blocks').fetchall()]

            # лист на части по 6, после - в общую строку с использованными эмоджи
            str_already_used_emojis = '\n '.join([' | '.join(one_part_emoji)
                                                  for one_part_emoji in grouping_by_n_elements(already_used_emojis, 6)])

            save_common_data(message.from_user.id, cursor, conn,
                             new_block_describe_el=message.text,
                             already_used_emojis=already_used_emojis,
                             str_already_used_emojis=str_already_used_emojis)

        try:
            await bot.edit_message_text(f'🛠️<b>Н/С/Э/</b><i>НОВЫЙ БЛОК</i>️️\n\n'
                                        f'{text_for}',
                                        chat_id=message.from_user.id,
                                        message_id=get_main_id_message(message.from_user.id, cursor),
                                        reply_markup=block_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(message.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / НОВЫЙ БЛОК: ЭМОДЖИ_CALL
    @dp.callback_query_handler(text='to_new_block_emoji',
                               state=(main_menu.new_block_describe_el, main_menu.user_sett))
    async def get_new_block_emoji_call(callback: CallbackQuery):
        await main_menu.new_block_emoji.set()
        save_last_state_user(callback.from_user.id, 'new_block_emoji', cursor, conn)

        # GET_COMMON_DATA
        new_block_name, new_block_describe_el, new_block_emoji = \
            get_common_data(callback.from_user.id, cursor,
                            'new_block_name', 'new_block_describe_el', 'new_block_emoji')

        # блок ещё не был определён
        block_kb = InlineKeyboardMarkup()
        if not new_block_emoji:
            text_for = f'<b>❔| Что за эмоджи будет у блока?</b>\n\n' \
                       f'📌<b>Принимаются любые ранее не используемые эмоджи, за исключением следующих:\n' \
                       f'<code> ⭐ | ❄️ | ❌ | 🌑</code></b>\n'

            block_kb.row(
                InlineKeyboardButton('⬅️', callback_data=f'to_new_block_describe_el'))
        else:
            text_for = f'<b>▫️НАЗВАНИЕ БЛОКА:</b> \n' \
                       f'·<code>{new_block_name}</code>\n' \
                       f'<b>▫ПОЛНОЦЕННОЕ ОПИСАНИЕ БЛОКА:</b> \n' \
                       f'·<code>{new_block_describe_el}</code> \n' \
                       f'<b>▫ЭМОДЖИ БЛОКА:</b> \n' \
                       f'·{new_block_emoji}\n\n' \
                       f'📌<b>Вы можете изменить эмоджи блока, написав обновлённую версию в чат!</b>'

            block_kb.row(
                InlineKeyboardButton('⬅️', callback_data=f'to_new_block_describe_el'),
                InlineKeyboardButton('➡️', callback_data='to_new_block_days_work'))

        try:
            await bot.edit_message_text(f'🛠️<b>Н/С/Э/</b><i>НОВЫЙ БЛОК</i>️️\n\n'
                                        f'{text_for}',
                                        chat_id=callback.from_user.id,
                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                        reply_markup=block_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(message.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / НОВЫЙ БЛОК: ЭМОДЖИ_MES
    @dp.message_handler(state=main_menu.new_block_emoji, content_types='text')
    async def get_new_block_emoji_mes(message: Message):
        await message.delete()

        # GET_COMMON_DATA
        new_block_name, new_block_describe_el, new_block_emoji, \
        new_block_days_work, already_used_emojis, str_already_used_emojis = \
            get_common_data(message.from_user.id, cursor,
                            'new_block_name', 'new_block_describe_el', 'new_block_emoji',
                            'new_block_days_work', 'already_used_emojis', 'str_already_used_emojis')

        # убираем лишние пробелы
        clear_emoji = message.text.replace(' ', '')[0]

        # ошибки
        if not is_emoji(clear_emoji) \
                or clear_emoji in emoji_work_dp_list \
                or clear_emoji in already_used_emojis:

            block_kb = InlineKeyboardMarkup()
            # при отстутствии рабочих дней
            if not new_block_days_work:
                block_kb.row(
                    InlineKeyboardButton('⬅️', callback_data=f'to_new_block_describe_el'))
            else:
                block_kb.row(
                    InlineKeyboardButton('⬅️', callback_data=f'to_new_block_describe_el'),
                    InlineKeyboardButton('➡️', callback_data='to_new_block_days_work'))

            # НЕ ЭМОДЖИ
            if not is_emoji(clear_emoji):
                text_for = '❗<b>Это не эмоджи!</b>\n\n' \
                           f'📌<b>Пожалуйста, отправьте нам эмоджи!</b>'

            # такой эмоджи уже есть
            elif clear_emoji in already_used_emojis:
                text_for = '❗<b>Этот эмоджи уже используется!</b>\n\n' \
                           f'📌<b>Пожалуйста, отправьте нам эмоджи НЕ из этого списка:\n' \
                           f'<code> {str_already_used_emojis}</code></b>'

            # неправильные эмоджи
            else:
                text_for = '❗<b>Для блока нельзя использовать следующие эмоджи:\n  ' \
                           f'<code> ⭐ | ❄️ | ❌ | 🌑</code></b>\n\n' \
                           f'📌<b>Пожалуйста, выберите другой эмоджи!</b>'

        # всё отлично
        else:
            await main_menu.user_sett.set()
            save_last_state_user(message.from_user.id, 'user_sett', cursor, conn)

            # генерируем КБ с выбыром дней
            new_block_days_work = \
                create_days_work_block_kb(new_block_days_work)

            # рабочие ещё не были определены
            if not new_block_days_work or not new_block_days_work[0]:
                text_for = f'<b>❔| Что за рабочие дни будут у блока?</b>\n\n' \
                           f'📌<b>Выберите необходимые дни недели!</b>\n'
                add_to_kb = [get_button('⬅️', callback_data=f'to_new_block_emoji')]

            else:
                text_for = f'<b>▫️НАЗВАНИЕ БЛОКА:</b> \n' \
                           f'·<code>{new_block_name}</code>\n' \
                           f'<b>▫ПОЛНОЦЕННОЕ ОПИСАНИЕ БЛОКА:</b> \n' \
                           f'·<code>{new_block_describe_el}</code> \n' \
                           f'<b>▫ЭМОДЖИ БЛОКА:</b> \n' \
                           f'·<code>{message.text}</code>\n' \
                           '<b>▫РАБОЧИЕ ДНИ БЛОКА:</b> \n' \
                           f'·<code>{new_block_days_work[2]}</code>\n\n' \
                           f'📌<b>Вы можете изменить рабочие дни блока!</b>'
                add_to_kb = \
                    [get_button('⬅️', callback_data=f'to_new_block_emoji'),
                     get_button('➡️', callback_data='end_process_adding_block')]

            save_common_data(message.from_user.id, cursor, conn,
                             new_block_emoji=message.text,
                             new_block_days_work=new_block_days_work)

            block_kb = row_buttons(*add_to_kb, your_kb=new_block_days_work[3])

        try:
            await bot.edit_message_text(f'🛠️<b>Н/С/Э/</b><i>НОВЫЙ БЛОК</i>️️\n\n'
                                        f'{text_for}',
                                        chat_id=message.from_user.id,
                                        message_id=get_main_id_message(message.from_user.id, cursor),
                                        reply_markup=block_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(message.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)
        except MessageNotModified:
            pass

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / НОВЫЙ БЛОК: РАБОЧИЕ ДНИ
    @dp.callback_query_handler(text='to_new_block_days_work', state=(main_menu.new_block_emoji, main_menu.user_sett))
    @dp.callback_query_handler(text='return_last_day_week', state=main_menu.user_sett)
    @dp.callback_query_handler(Text(startswith='week_day_'), state=main_menu.user_sett)
    async def work_with_new_block_days_work(callback: CallbackQuery):

        await main_menu.user_sett.set()
        save_last_state_user(callback.from_user.id, 'user_sett', cursor, conn)

        # GET_COMMON_DATA
        new_block_name, new_block_describe_el, new_block_emoji, \
        new_block_days_work = \
            get_common_data(callback.from_user.id, cursor,
                            'new_block_name', 'new_block_describe_el', 'new_block_emoji',
                            'new_block_days_work')

        # генерируем КБ с выбыром дней
        new_block_days_work = \
            create_days_work_block_kb(new_block_days_work, callback.data,
                                      minus_days=True if callback.data == 'return_last_day_week' else False)
        save_common_data(callback.from_user.id, cursor, conn, new_block_days_work=new_block_days_work)

        # рабочие ещё не были определены
        if not new_block_days_work or not new_block_days_work[0]:
            text_for = f'<b>❔| Что за рабочие дни будут у блока?</b>\n\n' \
                       f'📌<b>Выберите необходимые дни недели!</b>\n'
            row_buttons(get_button('⬅️', callback_data=f'to_new_block_emoji'), your_kb=new_block_days_work[3])

        else:
            text_for = f'<b>▫️НАЗВАНИЕ БЛОКА:</b> \n' \
                       f'·<code>{new_block_name}</code>\n' \
                       f'<b>▫ПОЛНОЦЕННОЕ ОПИСАНИЕ БЛОКА:</b> \n' \
                       f'·<code>{new_block_describe_el}</code> \n' \
                       f'<b>▫ЭМОДЖИ БЛОКА:</b> \n' \
                       f'·<code>{new_block_emoji}</code>\n' \
                       '<b>▫РАБОЧИЕ ДНИ БЛОКА:</b> \n' \
                       f'·<code>{new_block_days_work[2]}</code>\n\n' \
                       f'📌<b>Вы можете изменить рабочие дни блока!</b>'

            row_buttons(get_button('↪️↩️', callback_data='return_last_day_week'), your_kb=new_block_days_work[3])
            row_buttons(get_button('⬅️', callback_data=f'to_new_block_emoji'),
                        get_button('➡️', callback_data='end_process_adding_block'),
                        your_kb=new_block_days_work[3])

        try:
            await bot.edit_message_text(f'🛠️<b>Н/С/Э/</b><i>НОВЫЙ БЛОК</i>️️\n\n'
                                        f'{text_for}',
                                        chat_id=callback.from_user.id,
                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                        reply_markup=new_block_days_work[3],
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(callback.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / НОВЫЙ БЛОК: FINAL_ADDING
    @dp.callback_query_handler(text='end_process_adding_block',
                               state=main_menu.user_sett)
    async def final_adding_new_block(callback: CallbackQuery):

        # GET_COMMON_DATA
        new_block_name, new_block_describe_el, new_block_emoji, \
        new_block_days_work = \
            get_common_data(callback.from_user.id, cursor,
                            'new_block_name', 'new_block_describe_el', 'new_block_emoji',
                            'new_block_days_work')

        block_kb = \
            row_buttons(get_button('⬅️', callback_data='to_new_block_days_work'),
                        your_kb=yes_or_no_kb('yes_adding_this_block', 'no_adding_this_block'))

        await bot.edit_message_text(f'🛠️<b>Н/С/Э/</b><i>НОВЫЙ БЛОК</i>️️\n\n'
                                    f'<b>▫️НАЗВАНИЕ БЛОКА:</b> \n'
                                    f'·<code>{new_block_name}</code>\n'
                                    f'<b>▫ПОЛНОЦЕННОЕ ОПИСАНИЕ БЛОКА:</b> \n'
                                    f'·<code>{new_block_describe_el}</code> \n'
                                    f'<b>▫ЭМОДЖИ БЛОКА:</b> \n'
                                    f'·<code>{new_block_emoji}</code>\n'
                                    '<b>▫РАБОЧИЕ ДНИ БЛОКА:</b> \n'
                                    f'·<code>{new_block_days_work[2]}</code>\n\n'
                                    f'❓<b>Создать блок с данными параметрами?</b>',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=block_kb,
                                    parse_mode=ParseMode.HTML)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / ОДИН БЛОК
    @dp.callback_query_handler(text='back_to_one_block', state=main_menu.user_sett)
    @dp.callback_query_handler(Text(endswith='_choose_block'), state=main_menu.user_sett)
    async def one_block_sett(callback: CallbackQuery):

        # GET_COMMON_DATA
        login_user, last_page_choose_blocks, work_element, \
        bot_id = \
            get_common_data(callback.from_user.id, cursor,
                            'login_user', 'last_page_choose_blocks', 'work_element',
                            'bot_id')

        # если выбираем эвент
        if '_choose_block' in callback.data:
            block_code, block_emoji, block_name, text_for, \
            one_kb, block_days_work, block_content = \
                get_data_one_block(callback.from_user.id, cursor, conn, callback.data[:-13],
                                   bot_id,
                                   last_page_choose_blocks)

        else:

            # уже выбрали из возвращаемся
            _, block_emoji, _, text_for, one_kb, *_ = \
                work_element

        await bot.edit_message_text(f'🛠️<b>Н/С/Б/</b><i>{block_emoji}</i>️️\n\n'
                                    f'{text_for}',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=one_kb,
                                    parse_mode=ParseMode.HTML)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / ОДИН БЛОК / УДАЛЕНИЕ
    @dp.callback_query_handler(text='delete_block', state=main_menu.user_sett)
    async def one_block_delete_sett(callback: CallbackQuery):

        # GET_COMMON_DATA
        _, block_emoji, _, text_for, *_ = \
            get_common_data(callback.from_user.id, cursor,
                            'work_element')

        await bot.edit_message_text(f'🛠️<b>Н/С/Б/{block_emoji}/</b><i>УДАЛЕНИЕ</i>️️\n\n'
                                    f'{text_for}\n'
                                    f'\n❓| <b>Вы хотите удалить этот блок из системы DAY PLAN?</b>',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=yes_or_no_kb('yes_delete_block', 'back_to_one_block'),
                                    parse_mode=ParseMode.HTML)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / ОДИН БЛОК / СОДЕРЖАНИЕ
    @dp.callback_query_handler(text='edit_content_block', state=main_menu.user_sett)
    @dp.callback_query_handler(text='yes_delete_event_from_block', state=main_menu.user_sett)
    @dp.callback_query_handler(Text(endswith='_to_edit_content_block'), state=main_menu.user_sett)
    async def edit_content_block(callback: CallbackQuery):

        # GET_COMMON_DATA
        work_element, data_edit_content_block, last_page_edit_content_block, \
        login_user, possible_delete_event_code, last_page_choose_blocks, \
        bot_id = \
            get_common_data(callback.from_user.id, cursor,
                            'work_element', 'data_edit_content_block', 'last_page_edit_content_block',
                            'login_user', 'possible_delete_event_code', 'last_page_choose_blocks',
                            'bot_id')
        block_code, block_emoji, block_name, text_for, \
        one_kb, block_days_work, block_content = work_element

        # удалили эвент из блока
        if callback.data == 'yes_delete_event_from_block':
            # подключаемся к бд пользователя
            one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                            check_same_thread=False)
            one_user_cursor = one_user_conn.cursor()

            # обновляем связь эвент с блоком
            one_user_cursor.execute('UPDATE classification_of_events SET its_code_block = ? '
                                    'WHERE code_element = ?',
                                    (None, possible_delete_event_code,))

            # удаляем эвент из блока
            block_content.remove(possible_delete_event_code)

            one_user_cursor.execute('UPDATE classification_of_blocks SET content = ? WHERE code_element = ?',
                                    (str(block_content), block_code,))

            # удаляем эвент из DAY PLAN
            one_user_cursor.execute('SELECT * FROM hierarchy_day_plans')
            hierarchy_day_plans = one_user_cursor.fetchone()

            if hierarchy_day_plans:
                hierarchy_day_plans = list(hierarchy_day_plans)
                # находим размещение эвентов на каждом дне и убираем оттуда эвент
                for ind_week, day_week_data in enumerate(hierarchy_day_plans):

                    # если эвент есть в данном дне
                    if day_week_data:
                        day_week_list = ast.literal_eval(day_week_data)
                        if possible_delete_event_code in day_week_list:
                            day_week_list.remove(possible_delete_event_code)
                        hierarchy_day_plans[ind_week] = str(day_week_list)

                # обновляем иерархию эвентов
                one_user_cursor.execute('''UPDATE hierarchy_day_plans SET 
                                                           week_day_0 = ?, week_day_1 = ?, week_day_2 = ?, 
                                                           week_day_3 = ?, 
                                                           week_day_4 = ?, week_day_5 = ?, week_day_6 = ?''',
                                        hierarchy_day_plans)

            one_user_conn.commit()

            block_code, block_emoji, block_name, text_for, \
            one_kb, block_days_work, block_content = \
                get_data_one_block(callback.from_user.id, cursor, conn, block_code,
                                   bot_id,
                                   last_page_choose_blocks)

            await callback.answer('Блок лишён эвента!')

        # формируем КБ
        last_page_edit_content_block, \
        block_content_edit_kb = \
            with_choosing_elements_kb(callback.from_user.id,
                                      bot_id,
                                      cursor, conn,
                                      work_with_event=True,
                                      your_data_save=data_edit_content_block,
                                      your_save_name='data_edit_content_block',
                                      last_page=last_page_edit_content_block,
                                      with_page_call='_to_edit_content_block',
                                      with_element_call='_to_delete_event_from_block',
                                      back_callback='back_to_one_block',
                                      callback_data=callback.data,
                                      list_with_first_button=[get_button('👉СВЯЗАТЬ С ЭВЕНТОМ👈',
                                                                         callback_data='connect_one_block_with_event')],
                                      sql_request=f'''SELECT code_element, name_dp FROM classification_of_events 
                                                        WHERE code_element IN %s''' %
                                                  f'''({", ".join(f"'{el}'" for el in block_content)})''')

        await bot.edit_message_text(f'🛠️<b>Н/С/Б/{block_emoji}/</b><i>СОДЕРЖАНИЕ</i>️️\n\n'
                                    f'{text_for}\n'
                                    '\n📌<b>Выберите эвент или свяжите с новым!</b>',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=block_content_edit_kb,
                                    parse_mode=ParseMode.HTML)

        save_common_data(callback.from_user.id, cursor, conn,
                     last_page_edit_content_block=last_page_edit_content_block)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / ОДИН БЛОК / СОДЕРЖАНИЕ / УДАЛЕНИЕ ЭВЕНТА ИЗ БЛОКА
    @dp.callback_query_handler(Text(endswith='_to_delete_event_from_block'), state=main_menu.user_sett)
    async def one_block_delete_sett(callback: CallbackQuery):

        # GET_COMMON_DATA
        work_element, last_page_edit_content_block, data_for_delete_event_from_block, \
        login_user, bot_id = \
            get_common_data(callback.from_user.id, cursor,
                            'work_element', 'last_page_edit_content_block', 'data_for_delete_event_from_block',
                            'login_user', 'bot_id')
        _, block_emoji, *_ = work_element
        one_event_code = callback.data[:-27]

        # бд пользователя
        one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                        check_same_thread=False)
        one_user_cursor = one_user_conn.cursor()

        # получаем данные выбранного эвента
        one_user_cursor.execute(
            '''SELECT name_dp, description_dp, description_element, time_of_doing 
            FROM classification_of_events WHERE code_element = ?''', (one_event_code,))
        data_events = one_user_cursor.fetchone()
        event_name, event_describe_dp, event_describe_el, event_time_work = \
            data_events

        # None | данные эвента изменились
        if not data_for_delete_event_from_block or data_for_delete_event_from_block[0] != data_events:

            # формируем текст для запоминания
            text_for = f'<b>|ВЫБРАННЫЙ ЭВЕНТ|</b>\n' \
                       f'<b>{str(event_name).upper()}' \
                       f' 【<code>' \
                       f'{big_replacing(event_time_work, your_dict=dict_with_bold_nums)} MINS' \
                       f'</code>】</b> \n' \
                       f'<i>{str(event_describe_el).capitalize()}</i>'

            data_for_delete_event_from_block = [data_events, text_for]

        else:
            text_for = data_for_delete_event_from_block[1]

        await bot.edit_message_text(f'🛠️<b>Н/С/Б/{block_emoji}/С/</b><i>{event_name}</i>️️\n\n'
                                    f'{text_for}\n'
                                    f'\n❓| <b>Вы хотите удалить этот эвент из блока?</b>',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=yes_or_no_kb('yes_delete_event_from_block',
                                                              f'{last_page_edit_content_block}_to_edit_content_block'),
                                    parse_mode=ParseMode.HTML)

        save_common_data(callback.from_user.id, cursor, conn,
                         data_for_delete_event_from_block=data_for_delete_event_from_block,
                         possible_delete_event_code=one_event_code)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / ОДИН БЛОК / СОДЕРЖАНИЕ / СВЯЗАТЬ С ЭВЕНТОМ
    @dp.callback_query_handler(text='connect_one_block_with_event', state=main_menu.user_sett)
    @dp.callback_query_handler(text='yes_plus_event_from_block', state=main_menu.user_sett)
    @dp.callback_query_handler(text='back_to_block_from_adding_event',
                               state=(main_menu.user_sett, main_menu.new_event_name))
    @dp.callback_query_handler(text=('yes_adding_this_event_from_block', 'no_adding_this_event_from_block'),
                               state=main_menu.user_sett)
    @dp.callback_query_handler(Text(endswith='_page_plus_event_from_block'), state=main_menu.user_sett)
    async def edit_content_block_plus_event(callback: CallbackQuery):

        # пришли с добавления эвента в блок
        if callback.data == 'back_to_block_from_adding_event':
            await main_menu.user_sett.set()
            save_last_state_user(callback.from_user.id, 'user_sett', cursor, conn)

        # GET_COMMON_DATA
        work_element, data_plus_event_from_block, last_page_plus_event_from_block, \
        login_user, new_event_name, new_event_describe_dp, \
        new_event_describe_el, new_event_time_work, possible_plus_event_code, \
        last_page_choose_blocks, bot_id = \
            get_common_data(callback.from_user.id, cursor,
                            'work_element', 'data_plus_event_from_block', 'last_page_plus_event_from_block',
                            'login_user', 'new_event_name', 'new_event_describe_dp',
                            'new_event_describe_el', 'new_event_time_work', 'possible_plus_event_code',
                            'last_page_choose_blocks', 'bot_id')
        block_code, block_emoji, block_name, text_for, \
        one_kb, block_days_work, block_content = work_element

        # если создали эвент из блока
        if callback.data == 'yes_adding_this_event_from_block':
            # подключаемся к бд пользователя
            one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                            check_same_thread=False)
            one_user_cursor = one_user_conn.cursor()

            # обновляем список эвентов
            one_user_cursor.execute(
                '''INSERT INTO classification_of_events (code_element, name_dp, description_dp, 
                        description_element, time_of_doing) VALUES (?, ?, ?, ?, ?)''',
                (str(uuid.uuid4()).replace('-', ''), new_event_name, new_event_describe_dp, new_event_describe_el,
                 new_event_time_work))
            one_user_conn.commit()

            await callback.answer('Список эвентов обновлён!')

        # добавили в блок эвент
        elif callback.data == 'yes_plus_event_from_block':
            # подключаемся к бд пользователя
            one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                            check_same_thread=False)
            one_user_cursor = one_user_conn.cursor()

            # обновляем связь эвент с блоком
            one_user_cursor.execute('UPDATE classification_of_events SET its_code_block = ? '
                                    'WHERE code_element = ?',
                                    (block_code, possible_plus_event_code,))

            # добавляем эвент к блоку
            block_content.append(possible_plus_event_code)
            one_user_cursor.execute('UPDATE classification_of_blocks SET content = ? WHERE code_element = ?',
                                    (str(block_content), block_code,))

            # берём иерархию только тех дней, которые в block_days_work блока
            only_active_days_block = \
                lambda between: f"{between}".join([f"week_day_{day_week}" for day_week in block_days_work])

            # находим активные в бд
            one_user_cursor.execute(f'''SELECT {only_active_days_block(', ')} FROM hierarchy_day_plans''')
            week_deals = one_user_cursor.fetchone()

            # если есть вообще строки в бд
            if week_deals:
                hierarchy_day_plans = list(week_deals)
            else:
                hierarchy_day_plans = [None for _ in block_days_work]

            # добавляем эвент в конец иерархии каждого дня physics_cycle
            for ind_week, days_week_data in enumerate(hierarchy_day_plans):

                # если уже были добавлены дни
                if days_week_data:
                    days_week_list = ast.literal_eval(days_week_data)
                else:
                    days_week_list = []
                days_week_list.append(possible_plus_event_code)

                hierarchy_day_plans[ind_week] = str(days_week_list)

            # обновляем иерархию эвентов
            if week_deals:
                one_user_cursor.execute(f'''UPDATE hierarchy_day_plans SET 
                                                                            {only_active_days_block(' = ?, ')} = ?''',
                                        hierarchy_day_plans)
            else:
                one_user_cursor.execute(f'INSERT INTO hierarchy_day_plans ({only_active_days_block(", ")}) '
                                        f'VALUES ({", ".join("?" for _ in block_days_work)})', hierarchy_day_plans)

            one_user_conn.commit()

            block_code, block_emoji, block_name, text_for, \
            one_kb, block_days_work, block_content = \
                get_data_one_block(callback.from_user.id, cursor, conn, block_code,
                                   bot_id,
                                   last_page_choose_blocks)

            await callback.answer('Блок соединён с эвентом!')

        # формируем КБ
        last_page_plus_event_from_block, \
        plus_event_from_block_kb = \
            with_choosing_elements_kb(callback.from_user.id,
                                      bot_id,
                                      cursor, conn,
                                      work_with_event=True,
                                      your_data_save=data_plus_event_from_block,
                                      your_save_name='data_plus_event_from_block',
                                      last_page=last_page_plus_event_from_block,
                                      with_page_call='_page_plus_event_from_block',
                                      with_element_call='_choose_plus_event_from_block',
                                      back_callback='edit_content_block',
                                      callback_data=callback.data,
                                      list_with_first_button=[get_button('➕ДОБАВИТЬ ЭВЕНТ➕',
                                                                callback_data='adding_event_sett_from_block')],
                                      sql_request=f'''SELECT code_element, name_dp FROM classification_of_events 
                                                            WHERE its_code_block IS NULL''')

        await bot.edit_message_text(f'🛠️<b>Н/С/Б/{block_emoji}/С/</b><i>СВЯЗАТЬ С ЭВЕНТОМ</i>️️\n\n'
                                    f'{text_for}\n'
                                    '\n📌<b>Выберите эвент!</b>',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=plus_event_from_block_kb,
                                    parse_mode=ParseMode.HTML)

        save_common_data(callback.from_user.id, cursor, conn,
                         adding_event_sett_from_block=
                         [0, f'🛠️<b>Н/С/Б/{block_emoji}/С/СЭ/</b><i>НОВЫЙ ЭВЕНТ</i>️️\n\n'],
                         last_page_plus_event_from_block=last_page_plus_event_from_block)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / ОДИН БЛОК / СОДЕРЖАНИЕ / СВЯЗАТЬ С ЭВЕНТОМ / +ЭВЕНТ
    @dp.callback_query_handler(Text(endswith='_choose_plus_event_from_block'), state=main_menu.user_sett)
    async def choose_plus_event_from_block(callback: CallbackQuery):

        # GET_COMMON_DATA
        work_element, last_page_plus_event_from_block, data_for_plus_event_from_block, \
        login_user, bot_id = \
            get_common_data(callback.from_user.id, cursor,
                            'work_element', 'last_page_plus_event_from_block', 'data_for_plus_event_from_block',
                            'login_user', 'bot_id')
        _, block_emoji, *_ = work_element
        one_event_code = callback.data[:-29]

        # бд пользователя
        one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                        check_same_thread=False)
        one_user_cursor = one_user_conn.cursor()

        # получаем данные выбранного эвента
        one_user_cursor.execute(
            '''SELECT name_dp, description_dp, description_element, time_of_doing 
            FROM classification_of_events WHERE code_element = ?''', (one_event_code,))
        data_events = one_user_cursor.fetchone()
        event_name, event_describe_dp, event_describe_el, event_time_work = \
            data_events

        # None | данные эвента изменились
        if not data_for_plus_event_from_block or data_for_plus_event_from_block[0] != data_events:

            # формируем текст для запоминания
            text_for = f'<b>|ВЫБРАННЫЙ ЭВЕНТ|</b>\n' \
                       f'<b>{str(event_name).upper()}' \
                       f' 【<code>' \
                       f'{big_replacing(event_time_work, your_dict=dict_with_bold_nums)} MINS' \
                       f'</code>】</b> \n' \
                       f'<i>{str(event_describe_el).capitalize()}</i>'

            data_for_plus_event_from_block = [data_events, text_for]

        else:
            text_for = data_for_plus_event_from_block[1]

        await bot.edit_message_text(f'🛠️<b>Н/С/Б/{block_emoji}/С/СЭ/</b><i>{event_name}</i>️️\n\n'
                                    f'{text_for}\n'
                                    f'\n❔| <b>Вы хотите связать этот эвент с блоком?</b>',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=yes_or_no_kb('yes_plus_event_from_block',
                                                              f'{last_page_plus_event_from_block}'
                                                              f'_page_plus_event_from_block'),
                                    parse_mode=ParseMode.HTML)

        save_common_data(callback.from_user.id, cursor, conn,
                         data_for_plus_event_from_block=data_for_plus_event_from_block,
                         possible_plus_event_code=one_event_code)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / ОДИН БЛОК / РЕДАКТИРОВАНИЕ
    @dp.callback_query_handler(text='edit_block',
                               state=(main_menu.user_sett, main_menu.edit_parameters_block))
    @dp.callback_query_handler(text='update_days_work', state=main_menu.user_sett)
    async def update_work_days_block_sett(callback: CallbackQuery):
        await main_menu.user_sett.set()
        save_last_state_user(callback.from_user.id, 'user_sett', cursor, conn)

        # GET_COMMON_DATA
        work_element, login_user, update_work_days_block, \
        last_page_choose_blocks, edit_block_days_work, bot_id = \
            get_common_data(callback.from_user.id, cursor,
                            'work_element', 'login_user', 'update_work_days_block',
                            'last_page_choose_blocks', 'edit_block_days_work', 'bot_id')
        block_code, block_emoji, block_name, text_for, \
        one_kb, block_days_work, block_content = work_element

        # изменение рабочих дней
        if callback.data == 'update_days_work':

            # подключаемся к бд пользователя
            one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                            check_same_thread=False)
            one_user_cursor = one_user_conn.cursor()

            # обновляем рабочие дни у блока
            one_user_cursor.execute('UPDATE classification_of_blocks SET physics_cycle = ? WHERE code_element = ?',
                                    (str(edit_block_days_work[0]), block_code,))

            # берём иерархию только тех дней, которые изменились
            update_days = tuple(set(block_days_work) ^ set(edit_block_days_work[0]))

            only_active_days_block = \
                lambda between: f"{between}".join([f"week_day_{day_week}"
                                                   for day_week in update_days])

            # находим активные в бд
            one_user_cursor.execute(f'''SELECT {only_active_days_block(', ')} FROM hierarchy_day_plans''')
            hierarchy_day_plans = one_user_cursor.fetchone()

            if hierarchy_day_plans:
                hierarchy_day_plans = list(hierarchy_day_plans)
                # добавляем/удаляем в конец иерархии каждого дня physics_cycle
                for ind, days_week_data in enumerate(hierarchy_day_plans):

                    # удаляем эвенты из иерархии, если день убран:
                    # день из block_days_work может быть обновлён, только если убран
                    if update_days[ind] in block_days_work:

                        days_week_list = [one_event for one_event in ast.literal_eval(days_week_data)
                                          if one_event not in block_content]

                    # добавляем в конец иерархии
                    else:

                        # если уже были добавлены дни
                        if days_week_data:
                            days_week_list = ast.literal_eval(days_week_data)
                        else:
                            days_week_list = []
                        days_week_list.extend(block_content)

                    hierarchy_day_plans[ind] = str(days_week_list)

                # обновляем иерархию эвентов
                one_user_cursor.execute(f'''UPDATE hierarchy_day_plans SET {only_active_days_block(' = ?, ')} = ?''',
                                        hierarchy_day_plans)

            one_user_conn.commit()

            block_code, block_emoji, block_name, text_for, \
            one_kb, block_days_work, block_content = \
                get_data_one_block(callback.from_user.id, cursor, conn, block_code,
                                   bot_id,
                                   last_page_choose_blocks)

        await bot.edit_message_text(f'🛠️<b>Н/С/Б/{block_emoji}.../</b><i>РЕДАКТИРОВАНИЕ</i>️️\n\n'
                                    f'{text_for}\n\n'
                                    f'❔| <b>Какие параметры блока вы хотите изменить?</b>',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    reply_markup=edit_block_sett_kb,
                                    parse_mode=ParseMode.HTML)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / ОДИН БЛОК / РЕДАКТИРОВАНИЕ / ACTION
    @dp.callback_query_handler(text=('edit_name_block', 'edit_emoji_block',
                                     'edit_long_description_block', 'edit_work_days_block'),
                               state=main_menu.user_sett)
    async def edit_block_action_sett(callback: CallbackQuery):

        # GET_COMMON_DATA
        work_element, edit_work_days_block, login_user, \
        bot_id = \
            get_common_data(callback.from_user.id, cursor,
                            'work_element', 'edit_work_days_block', 'login_user',
                            'bot_id')
        block_code, block_emoji, block_name, text_for, \
        one_kb, block_days_work, block_content = work_element

        edit_block_action_kb = None
        if callback.data != 'edit_work_days_block':
            await main_menu.edit_parameters_block.set()
            save_last_state_user(callback.from_user.id, 'edit_parameters_block', cursor, conn)

            if callback.data == 'edit_name_block':
                to_continue = 'НАЗВАНИЕ'

                text_edit = '<b>❕| Обновите название блока!</b>\n\n' \
                            f'📌<b>Максимальная длина названия блока: ' \
                            f'<code>{big_replacing(15, your_dict=dict_with_bold_nums)}</code></b>'
                save_common_data(callback.from_user.id, cursor, conn, already_used_emojis=[])

            elif callback.data == 'edit_emoji_block':
                to_continue = 'ЭМОДЖИ'

                text_edit = f'<b>❕| Обновите эмоджи блока!</b>\n\n' \
                       f'📌<b>Принимаются любые ранее не используемые эмоджи, за исключением следующих:\n' \
                       f'<code> ⭐ | ❄️ | ❌ | 🌑</code></b>\n'

                # подключаемся к бд пользователя
                one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                                check_same_thread=False)
                one_user_cursor = one_user_conn.cursor()

                # создаём список уже использованных эмоджи
                already_used_emojis = \
                    [one_data[0] for one_data in
                     one_user_cursor.execute('SELECT block_emoji FROM classification_of_blocks').fetchall()]

                # лист на части по 6, после - в общую строку с использованными эмоджи
                str_already_used_emojis = '\n '.join([' | '.join(one_part_emoji)
                                                      for one_part_emoji in
                                                      grouping_by_n_elements(already_used_emojis, 6)])

                save_common_data(callback.from_user.id, cursor, conn,
                                 already_used_emojis=already_used_emojis,
                                 str_already_used_emojis=str_already_used_emojis)

            else:
                to_continue = 'ПОЛНОЦЕННОЕ ОПИСАНИЕ'

                text_edit = f'<b>❕| Обновите <i>полноценное описание</i> блока!</b>\n\n' \
                            f'📌<b>Максимальная длина полноценного описания у блока: ' \
                            f'<code>{big_replacing(150, your_dict=dict_with_bold_nums)}</code></b>'
                save_common_data(callback.from_user.id, cursor, conn, already_used_emojis=[])

        else:
            to_continue = 'РАБОЧИЕ ДНИ'

            # генерируем КБ с выбыром дней
            edit_block_days_work = create_days_work_block_kb([block_days_work, block_days_work],
                                                             just_update_data=True,
                                                             adding_callback='edit_week_day_')
            edit_block_action_kb = row_buttons(get_button('↪️↩️', callback_data='return_edit_last_day_week'),
                                               your_kb=edit_block_days_work[3])

            text_edit = f'❕| <b>Измените рабочие дни:\n</b>  <code>{edit_block_days_work[2]}</code>'
            save_common_data(callback.from_user.id, cursor, conn,
                             edit_block_days_work=edit_block_days_work,
                             old_block_days_work=edit_block_days_work,
                             already_used_emojis=[])

        try:
            await bot.edit_message_text(f'🛠️<b>Н/С/Б/{block_emoji}/Р/</b><i>{to_continue}</i>️️\n\n'
                                        f'{text_edit}\n',
                                        chat_id=callback.from_user.id,
                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                        reply_markup=row_buttons(get_button(back_mes,
                                                                                      callback_data='edit_block'),
                                                                 your_kb=edit_block_action_kb),
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(callback.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)
        save_common_data(callback.from_user.id, cursor, conn, act_edit=callback.data)

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / ОДИН БЛОК / РЕДАКТИРОВАНИЕ / ACTION / РАБОЧИЕ ДНИ
    @dp.callback_query_handler(text='return_edit_last_day_week', state=main_menu.user_sett)
    @dp.callback_query_handler(Text(startswith='edit_week_day_'), state=main_menu.user_sett)
    async def process_editing_days_work_block(callback: CallbackQuery):
        # GET_COMMON_DATA
        work_element, edit_block_days_work, old_block_days_work = \
            get_common_data(callback.from_user.id, cursor,
                            'work_element', 'edit_block_days_work', 'old_block_days_work')
        _, block_emoji, *_ = work_element

        # попытка убрать последний рабочий день
        if callback.data == 'return_edit_last_day_week' and len(edit_block_days_work[0]) == 1:
            edit_block_days_work_kb = None
            await callback.answer('Блок должен иметь как минимум один рабочий день!')

        else:
            # генерируем КБ с выбыром дней
            edit_block_days_work = \
                create_days_work_block_kb(edit_block_days_work, callback.data,
                                          minus_days=True if callback.data == 'return_edit_last_day_week' else False,
                                          adding_callback='edit_week_day_')
            save_common_data(callback.from_user.id, cursor, conn, edit_block_days_work=edit_block_days_work)
            edit_block_days_work_kb = edit_block_days_work[3]

        # если пользователь изменил дни
        if old_block_days_work[0] != edit_block_days_work[0]:
            edit_block_days_work_kb = \
                row_buttons(get_button('↪️↩️', callback_data='return_edit_last_day_week'),
                        your_kb=edit_block_days_work_kb)
            row_buttons(get_button(back_mes, callback_data='edit_block'),
                        get_button('✔️ОБНОВИТЬ✔️', callback_data='update_days_work'),
                        your_kb=edit_block_days_work_kb)

        else:
            edit_block_days_work_kb = \
                row_buttons(get_button('↪️↩️', callback_data='return_edit_last_day_week'),
                            your_kb=edit_block_days_work_kb)
            row_buttons(get_button(back_mes, callback_data='edit_block'), your_kb=edit_block_days_work_kb)

        try:
            await bot.edit_message_text(f'🛠️<b>Н/С/Б/{block_emoji}/Р/</b><i>РАБОЧИЕ ДНИ</i>️️\n\n'
                                        f'❕| <b>Измените рабочие дни:\n</b>  <code>{edit_block_days_work[2]}</code>',
                                        chat_id=callback.from_user.id,
                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                        reply_markup=edit_block_days_work_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageNotModified:
            pass

    # НАСТРОЙКИ / СОСТАВ / БЛОКИ / ОДИН БЛОК / РЕДАКТИРОВАНИЕ / ACTION / ANOTHER
    @dp.message_handler(state=main_menu.edit_parameters_block, content_types='text')
    async def get_edit_parameters_block(message: Message):
        await message.delete()

        # GET_COMMON_DATA
        work_element, act_edit, login_user, \
        last_page_choose_blocks, already_used_emojis, str_already_used_emojis, \
        bot_id = \
            get_common_data(message.from_user.id, cursor,
                            'work_element', 'act_edit', 'login_user',
                            'last_page_choose_blocks', 'already_used_emojis', 'str_already_used_emojis',
                            'bot_id')
        code_element, block_emoji, *_ = work_element

        clear_emoji = message.text.replace(' ', '')
        max_lens_actions_edit_event = {'edit_name_block': 15,
                                       'edit_long_description_block': 150}
        use_remake_kb = InlineKeyboardMarkup().add(InlineKeyboardButton(back_mes, callback_data='edit_event'))

        # ошибки
        if act_edit == 'edit_name_block' \
                and (len(message.text) > max_lens_actions_edit_event.get(act_edit)
                     or '<' in message.text or '>' in message.text):
            to_continue = 'НАЗВАНИЕ'

            if len(message.text) > 15:
                text_for = '❗<b>Максимальная длина названия блока: ' \
                           f'<code>{big_replacing(15, your_dict=dict_with_bold_nums)}</code></b>\n\n' \
                           f'📌<b>Пожалуйста, укротите название!</b>'

            # плохие символы
            else:
                text_for = '❗<b>В названии нельзя использовать символы: ' \
                           f'<code>{quote_html("<>")}</code></b>\n\n' \
                           f'📌<b>Пожалуйста, измените название!</b>'

            text_first = f'🛠️<b>Н/С/Б/{block_emoji}/Р/</b><i>{to_continue}</i>️️\n\n'

        elif act_edit == 'edit_long_description_block' \
                and (len(message.text) > max_lens_actions_edit_event.get(act_edit)
                     or '<' in message.text or '>' in message.text):
            to_continue = 'ПОЛНОЦЕННОЕ ОПИСАНИЕ'

            if len(message.text) > 150:
                text_for = '❗<b>Максимальная длина полноценного описания эвента: ' \
                           f'<code>{big_replacing(150, your_dict=dict_with_bold_nums)}</code></b>\n\n' \
                           f'📌<b>Пожалуйста, укротите полноценное описание!</b>'

            # плохие символы
            else:
                text_for = '❗<b>В полноценном описании нельзя использовать символы: ' \
                           f'<code>{quote_html("<>")}</code></b>\n\n' \
                           f'📌<b>Пожалуйста, измените полноценное описание!</b>'

            text_first = f'🛠️<b>Н/С/Б/{block_emoji}/Р/</b><i>{to_continue}</i>️️\n\n'

        elif act_edit == 'edit_emoji_block' \
                and (not is_emoji(clear_emoji)
                     or clear_emoji in emoji_work_dp_list
                     or clear_emoji in already_used_emojis):

            to_continue = 'ЭМОДЖИ'

            # НЕ ЭМОДЖИ
            if not is_emoji(clear_emoji):
                text_for = '❗<b>Это не эмоджи!</b>\n\n' \
                           f'📌<b>Пожалуйста, отправьте нам эмоджи!</b>'

            # такой эмоджи уже есть
            elif clear_emoji in already_used_emojis:
                text_for = '❗<b>Этот эмоджи уже используется!</b>\n\n' \
                           f'📌<b>Пожалуйста, отправьте нам эмоджи НЕ из этого списка:\n' \
                           f'<code> {str_already_used_emojis}</code></b>'

            # неправильные эмоджи
            else:
                text_for = '❗<b>Для блока нельзя использовать следующие эмоджи:\n  ' \
                           f'<code> ⭐ | ❄️ | ❌ | 🌑</code></b>\n\n' \
                           f'📌<b>Пожалуйста, выберите другой эмоджи!</b>'

            text_first = f'🛠️<b>Н/С/Б/{block_emoji}/Р/</b><i>{to_continue}</i>️️\n\n'

        else:
            await main_menu.user_sett.set()
            save_last_state_user(message.from_user.id, 'user_sett', cursor, conn)

            # подключаемся к бд пользователя
            one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                            check_same_thread=False)
            one_user_cursor = one_user_conn.cursor()

            # понимаем, что обновили
            if act_edit == 'edit_name_block':
                update_element = 'name_dp'
                updated_text = message.text
            elif act_edit == 'edit_long_description_block':
                update_element = 'description_element'
                updated_text = message.text
            else:
                update_element = 'block_emoji'
                updated_text = block_emoji = clear_emoji

            # обновляем бд
            one_user_cursor.execute(f'''UPDATE classification_of_blocks SET {update_element} = ? 
                                        WHERE code_element = ?''', (updated_text, code_element,))
            one_user_conn.commit()

            text_first = f'🛠️<b>Н/С/Б/{block_emoji}/</b><i>РЕДАКТИРОВАНИЕ</i>️️\n\n'

            _, _, _, text_for, *_ = \
                get_data_one_block(message.from_user.id, cursor, conn, code_element,
                                   bot_id,
                                   last_page_choose_blocks)
            text_for += f'\n\n❔| <b>Какие параметры блока вы хотите изменить?</b>'

            use_remake_kb = edit_block_sett_kb

        try:
            await bot.edit_message_text(f'{text_first}'
                                        f'{text_for}\n',
                                        chat_id=message.from_user.id,
                                        message_id=get_main_id_message(message.from_user.id, cursor),
                                        reply_markup=use_remake_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(message.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)
        except MessageNotModified:
            pass

    # УДАЛЕНИЕ ЛИШНИХ СООБЩЕНИЙ
    @dp.message_handler(state=(main_menu.user_sett, main_menu.compound_remake_sett,
                               main_menu.new_event_name, main_menu.new_event_describe_dp,
                               main_menu.new_event_describe_el, main_menu.edit_parameters_event,
                               main_menu.new_block_name, main_menu.new_block_describe_el,
                               main_menu.new_block_emoji, main_menu.edit_parameters_block),
                        content_types=all_content_types)
    async def delete_endless_in_sett(message: Message):
        await message.delete()

        await existing_work_message(message.from_user.id, bot,
                                    cursor, conn,
                                    main_menu)
