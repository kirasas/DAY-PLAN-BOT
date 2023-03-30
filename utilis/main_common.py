import ast
import time
import random
import sqlite3
import asyncio
import datetime
from num2words import num2words
from multiprocessing import Process, freeze_support
from apscheduler.schedulers.asyncio import AsyncIOScheduler
#
from aiogram import Bot
from aiogram.utils.exceptions import MessageToDeleteNotFound, MessageToEditNotFound, \
    MessageCantBeEdited, BadRequest
from aiogram.types import ParseMode, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
#
from utilis.consts_common import text_main_menu, main_menu_kb, back_mes


# REG MESSAGES
def plus_to_reg_messages(cursor, conn,
                         *user_id_and_message_id: [(int, int)]) -> None:
    # добавляем айди сообщения для удаления
    cursor.executemany('INSERT INTO all_reg_message (user_id, message_id) VALUES (?, ?)',
                       user_id_and_message_id)
    conn.commit()


def minus_to_reg_messages(cursor, conn, user_id) -> None:
    # удаляем все сообщения регистрации при её завершении
    cursor.execute('DELETE FROM all_reg_message WHERE user_id = ?', (user_id,))
    conn.commit()


async def delete_messages_reg(bot, cursor, conn):
    # смотрим данные пользователей
    cursor.execute('SELECT * FROM all_reg_message')
    all_data = cursor.fetchall()

    # если имеются соощения
    if all_data:
        for (user_id, message_id) in all_data:

            # удаляем сообщения, исключая возможность ошибки
            try:
                await bot.delete_message(chat_id=user_id, message_id=message_id)
            except MessageToDeleteNotFound:
                pass

        cursor.execute('DELETE FROM all_reg_message')
        conn.commit()


# CHECK EXIT TO DP
async def reply_exit_message(user_id, id_dp):
    from sides_bot.dayplan.utilis.main import save_data_process_dp
    from menu_base import bot, cursor, conn

    # обновляем state независимо оттого, где пользователь
    save_last_state_user(user_id, 'work_dp', cursor, conn)

    # отправляем конечное сообщение
    bad_finish_kb = {'inline_keyboard': [[dict(text='⭕ВЕРНУТЬСЯ К ПЛАНУ ДНЯ⭕', callback_data='back_dp_after_end')]]}
    try:
        await bot.edit_message_text(chat_id=user_id,
                                    text='<b>🏁ВАШЕ ВРЕМЯ ВЫШЛО🏁</b>',
                                    reply_markup=bad_finish_kb,
                                    message_id=id_dp,
                                    parse_mode=ParseMode.HTML)

    # попытка изменить сообщение с фотографией
    except MessageToEditNotFound:
        new_id_dp = await update_main_menu(user_id, bot, cursor, conn,
                                           text_for='<b>🏁ВАШЕ ВРЕМЯ ВЫШЛО🏁</b>',
                                           markup_for=bad_finish_kb,
                                           parse_for=ParseMode.HTML,
                                           need_state='work_dp')

        # проверяем: начал ли выполнение пользователь, если да - обновляем айди ДП
        cursor.execute('SELECT user_id FROM all_cashDP WHERE user_id = ?', (user_id,))
        exist_work_id = cursor.fetchone()
        if exist_work_id:
            save_data_process_dp(user_id, id_dp=new_id_dp)

    # закрываем сессию
    session = await bot.get_session()
    await session.close()


def create_stream_check_user_hour(user_id):
    from menu_base import cursor
    from sides_bot.dayplan.utilis.main import get_data_process_dp, \
        save_data_process_dp, get_user_time_now, get_delta_time_to_str
    from sides_bot.dayplan.utilis.charts import get_dynamic_dp_photo, \
        get_dynamic_dp_anim

    while True:

        if get_process_dp_status(user_id, cursor) == 0:

            delta_utc, live_time_list, datetime_work = \
                get_data_process_dp(user_id,
                                    'delta_utc', 'live_time_list', 'datetime_work')

            user_time_now = get_user_time_now(delta_utc)
            # относится ли данный час к рабочим часам
            if int(user_time_now.strftime("%H")) not in live_time_list \
                    or datetime.datetime.weekday(get_datetime_from_str(datetime_work)) \
                    != datetime.datetime.weekday(user_time_now):

                # обновляем маркеры
                save_data_process_dp(user_id, proof='THE_END_DP', the_end_dp=2)

                all_time_DP, DP_clock, id_dp, \
                huge_list, login_user, stb_DP, \
                clock_event, clock_block, last_emoji, \
                block_colours_dict, block_names_dict, login_user, \
                stop_time_begin, updated_data_usual_dp, bot_id = \
                    get_data_process_dp(user_id,
                                        'all_time_DP', 'DP_clock', 'id_dp',
                                        'huge_list', 'login_user', 'stb_DP',
                                        'clock_event', 'clock_block', 'last_emoji',
                                        'block_colours_dict', 'block_names_dict', 'login_user',
                                        'stop_time_begin', 'updated_data_usual_dp', 'bot_id')

                # где не выполнено, там крест
                for one_elm in huge_list:
                    if one_elm[1] != '⭐':
                        one_elm[1] = '❌'

                # если время было запущено
                if DP_clock:

                    # если на момент завершения, дп был остановлен
                    if stop_time_begin:

                        # прибавляем время стопа к общему времени остановки за всё время
                        stop_delta = (user_time_now - get_datetime_from_str(stop_time_begin)).total_seconds()

                        # что делаем со временем, когда запускаем ДП
                        stb_DP += stop_delta
                        if clock_event:
                            all_time_DP[-1][last_emoji][-1].append(('⛔',
                                                                    stop_time_begin, str(user_time_now)))
                        elif clock_block:
                            all_time_DP[-1][last_emoji].append(('⛔',
                                                                (stop_time_begin, str(user_time_now))))
                        else:
                            all_time_DP.append({'⛔': (stop_time_begin, str(user_time_now))})

                    # высчитываем крайний раз дельту дп
                    updated_data_usual_dp[2] = get_delta_time_to_str(DP_clock, delta_utc, adding_time=-stb_DP)

                    # дп закончился во время эвента
                    if clock_event:
                        start_to_end_ev = (clock_event, str(user_time_now))
                        all_time_DP[-1][last_emoji][-1].append(start_to_end_ev)

                        this_block_time = (clock_block, str(user_time_now))
                        all_time_DP[-1][last_emoji].append(this_block_time)

                    # во время блока
                    elif clock_block:
                        this_block_time = (clock_block, str(user_time_now))
                        all_time_DP[-1][last_emoji].append(this_block_time)

                    # полное время дп
                    all_time_DP.append((DP_clock, str(user_time_now)))

                    # формируем графики конца заранее
                    get_dynamic_dp_anim(user_id, all_time_DP,
                                        block_colours_dict, block_names_dict,
                                        the_end_dp=True, get_area_graph=True,
                                        save_path=f'users_bot/{bot_id}_log/for_work_dp')

                    get_dynamic_dp_anim(user_id, all_time_DP,
                                        block_colours_dict, block_names_dict,
                                        the_end_dp=True, get_area_graph=False,
                                        save_path=f'users_bot/{bot_id}_log/for_work_dp')

                else:
                    save_data_process_dp(user_id,
                                         exist_circle_graph='no_data',
                                         exist_area_graph='no_data')

                save_data_process_dp(user_id,
                                     huge_list=huge_list,
                                     all_time_DP=all_time_DP,
                                     stb_DP=stb_DP, updated_data_usual_dp=updated_data_usual_dp,
                                     clock_block=None, clock_event=None,
                                     proof='THE_END_DP', the_end_dp=2)

                # нужно отправить сообщение пользователю о завершении ДП
                from menu_base import loop
                loop.run_until_complete(reply_exit_message(user_id, id_dp))

                break

            time.sleep(60)

        else:
            break


def check_user_time_of_day_plans(cursor):
    # получаем все строки с процессом выполнением
    cursor.execute('SELECT * FROM all_cashDP')
    all_data = cursor.fetchall()

    # если кто-то выполняет дела
    if all_data:

        # получаем данные всех пользователей
        for (login, user_id, work_dict) in all_data:

            # 0, если DAY PLAN идёт
            if not ast.literal_eval(work_dict).get('the_end_dp'):
                check_bad_hours = Process(target=create_stream_check_user_hour,
                                          args=(user_id,))
                check_bad_hours.start()
                freeze_support()


# WORK WITH KBS
def get_button(text, callback_data) -> dict:
    return {'text': str(text), 'callback_data': str(callback_data)}


def add_buttons(*buttons, your_kb=None, row_width=3):
    # распределяем кнопки в ряды с длиной row_width
    new_butts = [buttons[i:i + row_width] for i in range(0, len(buttons), row_width)]

    if your_kb:
        your_kb['inline_keyboard'] = your_kb.get('inline_keyboard') + new_butts
        return your_kb
    else:
        return {'inline_keyboard': new_butts}


def row_buttons(*buttons, your_kb=None):
    # или создём новую кб, или добавляем кнопки к уже сушествуюшим
    if your_kb:
        your_kb['inline_keyboard'] = your_kb.get('inline_keyboard') + [buttons]
        return your_kb
    else:
        return {'inline_keyboard': [buttons]}


def get_datetime_from_str(your_str: str, style_with_z=True) -> datetime:
    return datetime.datetime.strptime(your_str, '%Y-%m-%d %H:%M:%S.%f%z') if style_with_z \
        else datetime.datetime.strptime(your_str, '%Y-%m-%d %H:%M:%S.%f')


def get_common_data(user_id: int, cursor, *name_keys) -> list:
    cursor.execute(f'SELECT data_user from all_sessions WHERE user_id = ?', (user_id,))
    data_user = ast.literal_eval(cursor.fetchone()[0])

    got_values = [data_user.get(one_key) for one_key in name_keys]

    return got_values if len(got_values) > 1 else got_values[0]


def save_common_data(user_id: int,
                     cursor, conn,
                     dict_save=None,
                     **keys_and_values):
    cursor.execute(f'SELECT data_user from all_sessions WHERE user_id = ?', (user_id,))
    data_user = ast.literal_eval(cursor.fetchone()[0])

    # обычный способ сохранения
    if not dict_save:
        data_user.update(keys_and_values)

    # задаём дикт
    else:
        data_user.update(dict_save)

    cursor.execute(f"UPDATE all_sessions set data_user = ? "
                   f"WHERE user_id = ?",
                   (str(data_user), user_id,))
    conn.commit()


async def check_users_states(code_states_dict,
                             dp, cursor):
    cursor.execute('SELECT user_id, state_user FROM all_sessions')
    users_id_and_their_states = cursor.fetchall()
    for one_value_user in users_id_and_their_states:

        # user_id is not None
        if one_value_user and one_value_user[0]:
            one_user_state = dp.current_state(chat=one_value_user[0],
                                              user=one_value_user[0])
            await one_user_state.set_state(code_states_dict.get(one_value_user[1]))


def get_main_id_message(user_id: int, cursor):
    cursor.execute(f'SELECT work_mes_id from all_sessions WHERE user_id = ?', (user_id,))
    return cursor.fetchone()[0]


def save_main_id_message(user_id: int, new_work_id: int,
                         cursor, conn):
    cursor.execute("UPDATE all_sessions SET work_mes_id = ? WHERE user_id = ?",
                   (new_work_id, user_id,))
    conn.commit()


def get_last_state_user(user_id: int, cursor):
    cursor.execute(f'SELECT state_user from all_sessions WHERE user_id = ?', (user_id,))
    return cursor.fetchone()[0]


def save_last_state_user(user_id: int, new_state: str,
                         cursor, conn):
    cursor.execute('UPDATE all_sessions SET state_user=? WHERE user_id=?',
                   (new_state, user_id,))
    conn.commit()


async def delete_work_message(user_id, bot, cursor):
    # находим рабочее сообщение и удаляем
    try:
        await bot.delete_message(chat_id=user_id,
                                 message_id=get_main_id_message(user_id, cursor))
    except MessageToDeleteNotFound:
        pass


async def update_main_menu(chat_id, bot,
                           cursor, conn,
                           text_for=text_main_menu, markup_for=main_menu_kb,
                           parse_for=ParseMode.MARKDOWN,
                           need_state='main_menu') -> int:
    await delete_work_message(chat_id, bot, cursor)

    # проверяем: не изменилось ли состояние
    if need_state == get_last_state_user(chat_id, cursor):
        # обновляем айди сообщения в бд
        new_work_mes = await bot.send_message(chat_id=chat_id,
                                              text=text_for, parse_mode=parse_for,
                                              reply_markup=markup_for)

        save_main_id_message(chat_id, new_work_mes.message_id, cursor, conn)
        return new_work_mes.message_id


def big_replacing(thing,
                  your_dict: dict): return ''.join([your_dict.get(one_elm)
                                                    for one_elm in str(thing)])


def to_right_russian_word_day(number_days: int):
    division_by_10 = number_days % 10
    if number_days == 0 or division_by_10 == 0 \
            or division_by_10 >= 5 \
            or number_days in range(11, 19):
        return 'дней'
    elif division_by_10 == 1:
        return 'день'
    else:
        return 'дня'


def yes_or_no_kb(callback_yes, callback_no, your_kb=None):
    return row_buttons(
        get_button('Да', callback_data=callback_yes),
        get_button('Нет', callback_data=callback_no),
        your_kb=your_kb)


async def check_message_exists(chat_id, message_id, bot):
    try:
        await bot.edit_message_media(chat_id=chat_id, message_id=message_id,
                                     media=InputMediaPhoto('EXISTING_THIS_MESSAGE'))
    except MessageCantBeEdited:
        return True
    except MessageToEditNotFound:
        return False
    except BadRequest:
        return True


async def existing_work_message(chat_id, bot,
                                cursor, conn,
                                main_menu) -> bool:
    # находим рабочее сообщение и проверяем его существование
    if not await check_message_exists(chat_id, get_main_id_message(chat_id, cursor), bot):
        # обновляем айди сообщения в бд
        new_work_mes = await bot.send_message(chat_id=chat_id,
                                              text=text_main_menu, parse_mode=ParseMode.MARKDOWN,
                                              reply_markup=main_menu_kb)

        await main_menu.main_menu.set()
        save_last_state_user(chat_id, 'main_menu', cursor, conn)
        save_main_id_message(chat_id, new_work_mes.message_id, cursor, conn)

        return False

    return True


def get_process_dp_status(user_id, cursor):
    return cursor.execute(f'SELECT processing_dp from all_sessions WHERE user_id = ?', (user_id,)).fetchone()[0]


async def message_no_data(user_id, cursor, conn, bot, call_back):
    new_work_mes = await bot.send_photo(photo='AgACAgIAAxkBAAIc6GQYRioK-'
                                              'yDFxw6eWY0PIqgvti5KAAIkyjEb'
                                              'IRXASBvXZsFB0lJBAQADAgADeAADLwQ',
                                        caption='✖️*DAY PLAN ОТСУТСТВУЕТ*✖️\n\n'
                                                '📌*Расписание дня должно содержать как минимум один блок!*',
                                        chat_id=user_id, parse_mode=ParseMode.MARKDOWN,
                                        reply_markup={'inline_keyboard':
                                                          [[dict(text=back_mes, callback_data=f'{call_back}')]]})
    save_main_id_message(user_id, new_work_mes.message_id, cursor, conn)


def grouping_by_n_elements(one_list: list, n_element: int):
    return [one_list[i:i + n_element] for i in range(0, len(one_list), n_element)]
