import math
import sqlite3
import asyncio
import datetime
from num2words import num2words
from emoji import emojize, is_emoji
from collections import OrderedDict
from multiprocessing import Process, freeze_support

#
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.types import CallbackQuery, Message, ParseMode, \
    ContentTypes, InputFile, InputMedia, InputMediaPhoto, InputMediaVideo, InputMediaAnimation
from aiogram.utils.exceptions import MessageNotModified, InvalidQueryID, \
    MessageToEditNotFound
#
from utilis.consts_common import dict_with_bold_nums, back_mes, nums_and_emoji, \
    back_mes_but, all_content_types, short_name_week_days
from utilis.main_common import big_replacing, get_main_id_message, save_main_id_message, \
    delete_work_message, existing_work_message, save_last_state_user, \
    get_process_dp_status, get_datetime_from_str, \
    get_common_data, save_common_data, get_button, row_buttons, add_buttons, \
    create_stream_check_user_hour
#
from sides_bot.dayplan.utilis.consts import first_open_but, continue_work_dp_but, \
    dp_stop_tuple, active_kb, get_sett_kb, dynamic_kb, get_end_dp_kb
from sides_bot.dayplan.utilis.main import get_user_time_now, get_live_hours, \
    get_delta_time_to_str, \
    get_data_process_dp, save_data_process_dp, \
    get_dict_with_index_emoji, get_window_with_excel_dp, \
    values_for_opening_dp
from sides_bot.dayplan.utilis.dp_usual import values_for_usual_dp
from sides_bot.dayplan.utilis.block import get_full_block_values, get_time_block, \
    get_indexes_current_part_block, minus_all_freeze_block
from sides_bot.dayplan.utilis.event import get_seeing_event_values, get_first_work_index, \
    get_full_event_do_values, condition_existing_live_elem_event
from sides_bot.dayplan.utilis.dp_remaking import values_for_remake_dp_first, \
    values_for_remake_dp_second_and_third, up_down_elements, save_dp_remakes
from sides_bot.dayplan.utilis.charts import get_dynamic_dp_photo, get_dynamic_dp_anim


def process_doing_dp(dp, bot, cursor, conn, main_menu):
    # 0/реакция на заход из главного меню
    @dp.message_handler(text='✔️\nDAYPLAN️', state=main_menu.main_menu)
    async def dp_begin_mes(message: Message):

        # обновляем state
        save_last_state_user(message.from_user.id, 'work_dp', cursor, conn)
        await main_menu.work_dp.set()

        await message.delete()
        await delete_work_message(message.from_user.id, bot, cursor)

        processing_dp = get_process_dp_status(message.from_user.id, cursor)
        # None (first_dp) | 0 (yet_in_process_work_with_dp) | -1 (only_see_excel_dp)
        if not processing_dp or processing_dp == -1:

            await get_window_with_excel_dp(message.from_user.id, message.from_user.username,
                                           processing_dp=processing_dp, bot=bot)
        # 1 (done_dp)
        else:
            data_end_dp = get_common_data(message.from_user.id, cursor, 'data_end_dp')
            new_work_mes = await bot.send_photo(photo=data_end_dp[1],
                                 caption=data_end_dp[0], chat_id=message.from_user.id,
                                 parse_mode=ParseMode.HTML,
                                 reply_markup=await get_end_dp_kb(message.from_user.id,
                                                                  message.from_user.username, bot))
            save_main_id_message(message.from_user.id, new_work_mes.message_id, cursor, conn)

    # 1/Запуск ДП, проверка рабочего времени
    @dp.callback_query_handler(text='way_to_DP', state=main_menu.work_dp)
    async def starting_work(callback: CallbackQuery):

        await delete_work_message(callback.from_user.id, bot, cursor)
        inf_for_begin_dp = \
            get_common_data(callback.from_user.id, cursor, 'inf_for_begin_dp')
        huge_list, login_user, bot_id, datetime_work, \
        block_names_dict, block_colours_dict, *_ = \
            inf_for_begin_dp

        # берём обращение, отклонение от UTC пользователя, default = 3 (МСК)
        cursor.execute("SELECT appeal, delta_utc, stop_hour, begin_hour FROM all_users WHERE login = ?",
                       (login_user,))
        its_appeal, delta_utc, stop_h, beg_h = cursor.fetchall()[0]
        user_time_now = get_user_time_now(int(delta_utc))

        live_time_list = list(get_live_hours(beg_h, stop_h)) if stop_h is not None and beg_h is not None \
            else None

        # проверяем, относится ли данный час к рабочим часам
        if live_time_list \
                and int(user_time_now.strftime("%H")) not in live_time_list:

            new_work_mes = await bot.send_message(chat_id=callback.from_user.id,
                                                  text=f'😵<b>Ваше время вышло, '
                                                       f'<i>'
                                                       f'{its_appeal if its_appeal else callback.from_user.username}'
                                                       f'</i>!</b>😵',
                                                  reply_markup=row_buttons(back_mes_but('back_main_menu')),
                                                  parse_mode=ParseMode.HTML)
            save_main_id_message(callback.from_user.id, new_work_mes.message_id, cursor, conn)
        else:

            # проверяем: идёт ли уже дп у данного логина
            cursor.execute("SELECT login FROM all_cashDP WHERE login = ?", (login_user,))
            already_exist_login = cursor.fetchone()
            if already_exist_login:
                cursor.execute("UPDATE all_cashDP SET user_id = ? WHERE login = ?",
                               (callback.from_user.id, login_user,))
                conn.commit()

                updated_data_usual_dp, recast_time_DP, proof, DP_clock = \
                    get_data_process_dp(callback.from_user.id,
                                        'updated_data_usual_dp', 'recast_time_DP', 'proof',
                                        'DP_clock')

                # останавливал ли пользователь ДП, иначе - зашёл через другой аккаунт
                call_for_continue_but = 'active_DP' if proof == 'stop_dp_check' else '1_xDP'

                # если не обнулился при найстройках
                if updated_data_usual_dp:

                    # находим текст первой страницы
                    asked = updated_data_usual_dp[5][1]
                    need_kb = row_buttons(continue_work_dp_but(call_for_continue_but)) if DP_clock \
                        else updated_data_usual_dp[9]

                else:
                    # только если дп ещё не был запущен | ДП is None
                    asked, _, \
                    updated_data_usual_dp = \
                        values_for_usual_dp(huge_list,
                                            str_clock=recast_time_DP,
                                            first_open=continue_work_dp_but(call_for_continue_but) if DP_clock
                                            else first_open_but)

                    need_kb = row_buttons(continue_work_dp_but(call_for_continue_but) if DP_clock
                                          else first_open_but)

                    save_data_process_dp(callback.from_user.id, updated_data_usual_dp=updated_data_usual_dp)
            else:

                # обновляем процесс в бд
                cursor.execute("UPDATE all_sessions SET processing_dp = ? WHERE user_id = ?",
                               (0, callback.from_user.id,))
                conn.commit()

                # получаем словарь: {emoji: [their_indexes]}
                with_index_emoji = work_with_index_emoji = \
                    get_dict_with_index_emoji(huge_list, OrderedDict.fromkeys([one_elem[1] for one_elem in huge_list]))

                # только если дп ещё не был запущен
                asked, need_kb, \
                updated_data_usual_dp = values_for_usual_dp(huge_list,
                                                            add_callback='oneDP')

                # создаём строку в таблице, где будет кэш
                cursor.execute(f'INSERT INTO all_cashDP (login, user_id, work_dict) '
                               f'VALUES (?, ?, ?)',
                               (login_user, callback.from_user.id, str(
                                   {'login_user': login_user,
                                    'bot_id': bot_id,
                                    'datetime_work': datetime_work,
                                    'huge_list': huge_list,
                                    'block_names_dict': block_names_dict,
                                    'block_colours_dict': block_colours_dict,
                                    'with_index_emoji': with_index_emoji,
                                    'work_with_index_emoji': work_with_index_emoji,
                                    'user_appeal': its_appeal, 'all_time_DP': [], 'real_number_stars': 0,
                                    'stb_DP': 0, 'stb_block': 0, 'stb_event': 0,
                                    'delta_utc': int(delta_utc),
                                    'live_time_list': live_time_list,
                                    'the_end_dp': 0, 'dict_with_media_data': {},
                                    'cold_block': {}, 'cold_event': [], 'cl_ev_for_block': {},
                                    'our_part_of_block': [], 'updated_data_graphs': {},
                                    'plus_time_work_block': 0,
                                    'updated_data_usual_dp': updated_data_usual_dp}),))
                conn.commit()

            new_work_mes = await bot.send_message(chat_id=callback.from_user.id,
                                                  text=asked, parse_mode=ParseMode.HTML,
                                                  reply_markup=need_kb)
            save_main_id_message(callback.from_user.id, new_work_mes.message_id, cursor, conn)
            save_data_process_dp(callback.from_user.id, id_dp=new_work_mes.message_id)
            save_common_data(callback.from_user.id, cursor, conn, data_end_dp=None)

            # зацикливаем проверку времени каждую минуту
            check_bad_hours = Process(target=create_stream_check_user_hour,
                                      args=(callback.from_user.id,))
            check_bad_hours.start()
            freeze_support()

    # 2/ДП до запуска: листание страниц
    @dp.callback_query_handler(Text(endswith="_oneDP"), state=main_menu.work_dp)
    async def first_reading_pages(callback: CallbackQuery):
        # GET_DATA
        huge_list, id_dp, updated_data_usual_dp = \
            get_data_process_dp(callback.from_user.id, 'huge_list', 'id_dp', 'updated_data_usual_dp')

        # для получения страниц из калбека
        message_pages = int(callback.data[:-6])

        # создаёт DP: возвращает текст сообщений и КБ
        asked, need_kb, *_ = \
            values_for_usual_dp(huge_list,
                                message_pages=message_pages,
                                add_callback='oneDP',
                                updated_data_usual_dp=updated_data_usual_dp)

        try:
            await bot.edit_message_text(chat_id=callback.from_user.id, text=asked,
                                        message_id=id_dp, parse_mode=ParseMode.HTML,
                                        reply_markup=need_kb)
        except MessageNotModified:
            pass

    # 3/ДП непосредственно ДП
    @dp.callback_query_handler(text='back_dp_after_end', state='*')
    @dp.callback_query_handler(text='event_ready', state=main_menu.work_dp)
    @dp.callback_query_handler(text='active_DP', state=main_menu.work_dp)
    @dp.callback_query_handler(Text(endswith="_xDP"), state=main_menu.work_dp)
    async def body_dp(callback: CallbackQuery):
        # получаем данный номер страницы
        save_data_process_dp(callback.from_user.id, proof='usual_dp_check',
                             last_page=int(callback.data[:-4]) if callback.data[-4:] == '_xDP'
                             else 1)

        # GET_DATA_PROCESS_DP
        DP_clock, delta_utc, updated_data_usual_dp, \
        the_end_dp, stb_DP, last_page, \
        with_index_emoji, all_time_DP, cold_event, \
        clock_event, cold_block, clock_block, \
        id_dp, huge_list, updated_data_block_values, \
        updated_data_seeing_event, \
 \
        end_last_time_event, for_work_event, \
        last_emoji, work_with_index_emoji, updated_data_get_time_block, \
        our_part_of_block, cl_ev_for_block, progress_block, \
        plus_time_work_block, real_number_stars, \
 \
        stop_time_begin, stb_event, stb_block, \
        recast_last_emoji, block_colours_dict, block_names_dict, \
        login_user, bot_id, exist_area_graph, exist_circle_graph = \
            get_data_process_dp(callback.from_user.id,
                                'DP_clock', 'delta_utc', 'updated_data_usual_dp',
                                'the_end_dp', 'stb_DP', 'last_page',
                                'with_index_emoji', 'all_time_DP', 'cold_event',
                                'clock_event', 'cold_block', 'clock_block',
                                'id_dp', 'huge_list', 'updated_data_block_values',
                                'updated_data_seeing_event',
                                'end_last_time_event', 'for_work_event',
                                'last_emoji', 'work_with_index_emoji', 'updated_data_get_time_block',
                                'our_part_of_block', 'cl_ev_for_block', 'progress_block',
                                'plus_time_work_block', 'real_number_stars',
                                'stop_time_begin', 'stb_event', 'stb_block',
                                'recast_last_emoji', 'block_colours_dict', 'block_names_dict',
                                'login_user', 'bot_id', 'exist_area_graph', 'exist_circle_graph')

        # после невольного завершения дп
        if callback.data == 'back_dp_after_end':
            await main_menu.work_dp.set()
            save_last_state_user(callback.from_user.id, 'work_dp', cursor, conn)

        # при выполнении элемента
        elif callback.data == 'event_ready':

            # делаем защиту от двойного нажатия на кнопку выполнить
            user_time_now = get_user_time_now(delta_utc)
            if not end_last_time_event or (user_time_now - get_datetime_from_str(end_last_time_event)).seconds > 1:
                index_this_elem = updated_data_seeing_event[1]

                # обновляем huge_list
                huge_list[index_this_elem][1] = '⭐'

                # чтобы не выполнялось во время завершения дп

                # добавляем время выполнения данного элемента в список
                start_to_end_ev = (clock_event, str(user_time_now))
                all_time_DP[-1][last_emoji][-1].append(start_to_end_ev)

                # обновляем живые эвенты у эмоджи
                try:
                    work_with_index_emoji[last_emoji].remove(index_this_elem)
                except ValueError:
                    pass

                # время последнего выполнения
                end_last_time_event = str(user_time_now)

                # обновляем данные эвентов
                huge_list, cold_event, \
                our_part_of_block, _, recast_part_block = \
                    condition_existing_live_elem_event(huge_list, cold_event,
                                                       our_part_of_block, last_emoji, work_with_index_emoji)

                # получаем обновлённые данные по блокам
                updated_data_get_time_block, \
                clock_block, cold_block, \
                huge_list, \
                progress_block, last_emoji, \
                our_part_of_block, \
                plus_time_work_block, all_time_DP, \
                cold_event, stb_block = \
                    get_time_block(updated_data_get_time_block=updated_data_get_time_block,
                                   huge_list=huge_list, clock_event=None,
                                   clock_block=clock_block, last_emoji=last_emoji,
                                   our_part_of_block=our_part_of_block, cold_block=cold_block,
                                   cl_ev_for_block=cl_ev_for_block, with_index_emoji=with_index_emoji,
                                   end_last_time_event=end_last_time_event, all_time_DP=all_time_DP,
                                   work_with_index_emoji=work_with_index_emoji, cold_event=cold_event,
                                   progress_block=progress_block, plus_time_work_block=plus_time_work_block,
                                   index_this_elem=index_this_elem, stb_block=stb_block,
                                   recast_part_block=recast_part_block)

            # прибавляем звёзды
            real_number_stars += 1

        # включение плана дня после стопа
        if callback.data == 'active_DP':

            # прибавляем время стопа к общему времени остановки за всё время
            user_time_now = get_user_time_now(delta_utc)
            stop_delta = (user_time_now - get_datetime_from_str(stop_time_begin)).total_seconds()

            # что делаем со временем, когда запускаем ДП
            stb_DP += stop_delta
            if clock_event:
                stb_event += stop_delta
                stb_block += stop_delta
                all_time_DP[-1][last_emoji][-1].append(['⛔',
                                                        stop_time_begin, str(user_time_now)])
            elif clock_block:
                stb_block += stop_delta
                all_time_DP[-1][last_emoji].append(['⛔',
                                                    (stop_time_begin, str(user_time_now))])
            else:
                all_time_DP.append({'⛔': (stop_time_begin, str(user_time_now))})

        # разбираемся со временем
        if not DP_clock:
            # настоящее время для пользователя
            DP_clock = str(get_user_time_now(delta_utc))
            save_data_process_dp(callback.from_user.id, DP_clock=DP_clock)

        # смотрим: нужно ли высчитывать дельту времени
        str_clock = updated_data_usual_dp[2] if the_end_dp \
            else get_delta_time_to_str(DP_clock, delta_utc, adding_time=-stb_DP)

        # создаёт DP: возвращает текст сообщений и КБ
        asked, need_kb, \
        updated_data_usual_dp = values_for_usual_dp(huge_list,
                                                    str_clock=str_clock,
                                                    message_pages=last_page,
                                                    updated_data_usual_dp=updated_data_usual_dp,
                                                    with_index_emoji=with_index_emoji,
                                                    all_time_DP=all_time_DP, delta_utc=delta_utc,
                                                    cold_event=cold_event, clock_event=clock_event,
                                                    user_id=callback.from_user.id, the_end_dp=the_end_dp,
                                                    DP_clock=DP_clock,
                                                    cold_block=cold_block, clock_block=clock_block,
                                                    end_last_time_event=end_last_time_event, last_emoji=last_emoji)

        try:
            if get_data_process_dp(callback.from_user.id, 'proof') in ('usual_dp_check', 'THE_END_DP'):
                await bot.edit_message_text(
                    text=asked, chat_id=callback.from_user.id, message_id=id_dp,
                    parse_mode=ParseMode.HTML, reply_markup=need_kb)

            if callback.data == 'event_ready':
                numbers_stars = \
                    big_replacing(real_number_stars, dict_with_bold_nums)
                await callback.answer(f'⭐{numbers_stars}⭐')

        except MessageNotModified:
            pass
        except InvalidQueryID:
            pass

        # не продолжаем, если ДП всё
        if get_data_process_dp(callback.from_user.id, 'proof') != 'THE_END_DP':
            # SAVE_DATA_PROCESS_DP

            # при выполнении эвента
            if callback.data == 'event_ready':

                # сгенерируем блок, чтобы открытие было быстрее
                str_clock_block = get_delta_time_to_str(clock_block, delta_utc,
                                                        adding_time=plus_time_work_block - stb_block)

                updated_data_block_values, *_ \
                    = get_full_block_values(updated_data_block_values=updated_data_block_values,
                                            huge_list=huge_list, last_page=last_page,
                                            last_emoji=last_emoji, cold_event=cold_event,
                                            clock_event=None, clock_block=clock_block,
                                            str_clock=str_clock_block,
                                            yet_done=updated_data_get_time_block[3] if updated_data_get_time_block
                                            else 0,
                                            progress_block=progress_block)

                save_data_process_dp(callback.from_user.id,
                                     clock_event=None,
                                     stb_event=0, stb_block=stb_block,
                                     real_number_stars=real_number_stars,
                                     work_with_index_emoji=work_with_index_emoji,
                                     end_last_time_event=end_last_time_event,
                                     huge_list=huge_list,
                                     updated_data_get_time_block=updated_data_get_time_block,
                                     clock_block=clock_block, cold_block=cold_block,
                                     progress_block=progress_block, last_emoji=last_emoji,
                                     our_part_of_block=our_part_of_block,
                                     plus_time_work_block=plus_time_work_block,
                                     all_time_DP=all_time_DP, cold_event=cold_event,
                                     updated_data_usual_dp=updated_data_usual_dp,
                                     recast_time_DP=str_clock,
                                     updated_data_block_values=updated_data_block_values,
                                     exist_photo_area=0, exist_photo_circle=0)

            # при активации ДП после остановки
            elif callback.data == 'active_DP':
                save_data_process_dp(callback.from_user.id,
                                     stb_event=stb_event, stb_block=stb_block, stb_DP=stb_DP,
                                     all_time_DP=all_time_DP,
                                     updated_data_usual_dp=updated_data_usual_dp,
                                     recast_time_DP=str_clock, stop_time_begin=None)

            # при переключении страниц
            else:
                save_data_process_dp(callback.from_user.id,
                                     updated_data_usual_dp=updated_data_usual_dp,
                                     recast_time_DP=str_clock)

            # изменение времени
            the_end_dp = \
                get_data_process_dp(callback.from_user.id, 'the_end_dp')
            while not int(the_end_dp) and last_page == 1:
                await asyncio.sleep(60)

                # не завершён ли ДП
                if get_process_dp_status(callback.from_user.id, cursor) != 0:
                    break
                else:

                    # GET_DATA_PROCESS_DP
                    DP_clock, delta_utc, stb_DP, \
                    updated_data_usual_dp, last_page, \
                    the_end_dp, id_dp, huge_list, \
                    recast_time_DP = \
                        get_data_process_dp(callback.from_user.id,
                                            'DP_clock', 'delta_utc', 'stb_DP',
                                            'updated_data_usual_dp', 'last_page',
                                            'the_end_dp', 'id_dp', 'huge_list', 'recast_time_DP')

                    # если ДП активен
                    if id_dp:

                        # обновляем время каждые 60 секунд
                        str_clock = get_delta_time_to_str(DP_clock, delta_utc, adding_time=-stb_DP)

                        asked, need_kb, \
                        updated_data_usual_dp = \
                            values_for_usual_dp(huge_list,
                                                str_clock=str_clock,
                                                updated_data_usual_dp=updated_data_usual_dp)

                        if get_data_process_dp(callback.from_user.id, 'proof') == 'usual_dp_check' \
                                and last_page == 1 \
                                and not the_end_dp \
                                and str_clock != recast_time_DP:

                            try:
                                await bot.edit_message_text(
                                    text=asked, chat_id=callback.from_user.id, message_id=id_dp,
                                    parse_mode=ParseMode.HTML, reply_markup=need_kb)
                            except MessageNotModified:
                                pass

                            save_data_process_dp(callback.from_user.id,
                                                 updated_data_usual_dp=updated_data_usual_dp,
                                                 recast_time_DP=str_clock)
                        else:
                            break

        else:
            if exist_circle_graph is None and exist_area_graph is None:
                save_data_process_dp(callback.from_user.id, exist_circle_graph=0, exist_area_graph=0)
                all_time_DP = get_data_process_dp(callback.from_user.id, 'all_time_DP')

                # формируем графики конца заранее
                # AREA_ANIM
                get_dynamic_dp_anim(callback.from_user.id, all_time_DP,
                                    block_colours_dict, block_names_dict,
                                    the_end_dp=True, get_area_graph=True,
                                    save_path=f'users_bot/{bot_id}_log/for_work_dp')

                # CIRCLE_ANIM
                get_dynamic_dp_anim(callback.from_user.id, all_time_DP,
                                    block_colours_dict, block_names_dict,
                                    the_end_dp=True, get_area_graph=False,
                                    save_path=f'users_bot/{bot_id}_log/for_work_dp')

    # 4/блок
    @dp.callback_query_handler(text="way_bl", state=main_menu.work_dp)
    @dp.callback_query_handler(text="block_snow", state=main_menu.work_dp)
    @dp.callback_query_handler(Text(endswith="_SUNbl"), state=main_menu.work_dp)
    async def body_block(callback: CallbackQuery):
        save_data_process_dp(callback.from_user.id, proof='usual_block_check')

        # GET_DATA_PROCESS_DP
        updated_data_get_time_block, clock_event, \
        clock_block, last_emoji, our_part_of_block, \
        cold_block, cl_ev_for_block, with_index_emoji, \
        end_last_time_event, all_time_DP, work_with_index_emoji, \
        cold_event, progress_block, plus_time_work_block, \
 \
        delta_utc, stb_block, \
 \
        updated_data_block_values, last_page, real_number_stars, \
        huge_list, \
 \
        id_dp, updated_data_seeing_event, recast_index, \
        stb_block, \
 \
        login_user, block_colours_dict, block_names_dict, \
        DP_clock, bot_id = \
            get_data_process_dp(callback.from_user.id,
                                'updated_data_get_time_block', 'clock_event',
                                'clock_block', 'last_emoji', 'our_part_of_block',
                                'cold_block', 'cl_ev_for_block', 'with_index_emoji',
                                'end_last_time_event', 'all_time_DP', 'work_with_index_emoji',
                                'cold_event', 'progress_block', 'plus_time_work_block',
                                'delta_utc', 'stb_block',
                                'updated_data_block_values', 'last_page', 'real_number_stars',
                                'huge_list',
                                'id_dp', 'updated_data_seeing_event', 'recast_index',
                                'stb_block',
                                'login_user', 'block_colours_dict', 'block_names_dict',
                                'DP_clock', 'bot_id')

        # заморозка блока
        if callback.data == 'block_snow':

            # находим индексы блока
            indexes_freeze_emoji = \
                work_with_index_emoji.get(last_emoji)

            # замораживаем эвенты
            for one_ind in indexes_freeze_emoji:
                huge_list[one_ind][1] = '❄️'

            # добавляем в лист-заморозки
            cold_block[last_emoji] = indexes_freeze_emoji

        # разморозка блоков
        elif '_SUNbl' in callback.data:

            # один блок
            if 'all_return' not in callback.data:
                sun_emoji = callback.data[0]
                # получаем индексы элементов данного эмоджи, удаляя эмоджи из cold_block
                for index_DP in cold_block.pop(sun_emoji):
                    huge_list[index_DP][1] = sun_emoji
            # все блоки
            else:
                huge_list = minus_all_freeze_block(huge_list, cold_block)
                cold_block = {}

        # получаем обновлённое время блока
        updated_data_get_time_block, \
        clock_block, cold_block, \
        huge_list, \
        progress_block, last_emoji, \
        our_part_of_block, \
        plus_time_work_block, all_time_DP, \
        cold_event, stb_block = \
            get_time_block(updated_data_get_time_block=updated_data_get_time_block,
                           huge_list=huge_list, clock_event=clock_event,
                           clock_block=clock_block, last_emoji=last_emoji,
                           our_part_of_block=our_part_of_block, cold_block=cold_block,
                           cl_ev_for_block=cl_ev_for_block, with_index_emoji=with_index_emoji,
                           end_last_time_event=end_last_time_event, all_time_DP=all_time_DP,
                           work_with_index_emoji=work_with_index_emoji, cold_event=cold_event,
                           progress_block=progress_block, plus_time_work_block=plus_time_work_block,
                           index_this_elem=updated_data_seeing_event[1] if updated_data_seeing_event else None,
                           stb_block=stb_block)

        # время работы в 000
        str_clock = get_delta_time_to_str(clock_block, delta_utc,
                                          adding_time=plus_time_work_block - stb_block)

        # строки+КБ блока
        updated_data_block_values, asked, need_kb, \
        condition_update_text_or_kb \
            = get_full_block_values(updated_data_block_values=updated_data_block_values,
                                    huge_list=huge_list, last_page=last_page,
                                    last_emoji=last_emoji, cold_event=cold_event,
                                    clock_event=clock_event, clock_block=clock_block,
                                    str_clock=str_clock, yet_done=updated_data_get_time_block[3],
                                    progress_block=progress_block)

        if get_data_process_dp(callback.from_user.id, 'proof') == 'usual_block_check':
            try:
                await bot.edit_message_text(
                    text=asked, chat_id=callback.from_user.id, message_id=id_dp,
                    parse_mode=ParseMode.HTML, reply_markup=need_kb)

                # отправляем уведомление о разморозке | заморозке
                if callback.data == 'block_snow':
                    await bot.answer_callback_query(callback.id, "❄️")
                elif '_SUNbl' in callback.data:
                    await bot.answer_callback_query(callback.id, "☀️")

            except MessageNotModified or InvalidQueryID:
                pass

        # получаем строки и КБ эвента заранее
        new_recast_index = get_first_work_index(huge_list, our_part_of_block)
        if new_recast_index != recast_index:
            recast_index = new_recast_index
            huge_list, cold_event, \
            updated_data_seeing_event, our_part_of_block, *_ = \
                get_seeing_event_values(updated_data_seeing_event=updated_data_seeing_event,
                                        huge_list=huge_list,
                                        cold_event=cold_event, our_part_of_block=our_part_of_block,
                                        last_emoji=last_emoji, real_number_stars=real_number_stars,
                                        work_with_index_emoji=work_with_index_emoji)

        # не продолжаем, если ДП всё
        if get_data_process_dp(callback.from_user.id, 'proof') != 'THE_END_DP':
            # SAVE_DATA_PROCESS_DP

            # разморозка | заморозка | изменения текста&КБ
            if condition_update_text_or_kb \
                    or callback.data == 'block_snow' \
                    or '_SUNbl' in callback.data:

                save_data_process_dp(callback.from_user.id,
                                     updated_data_get_time_block=updated_data_get_time_block,
                                     clock_block=clock_block, cold_block=cold_block,
                                     huge_list=huge_list,
                                     progress_block=progress_block, last_emoji=last_emoji,
                                     our_part_of_block=our_part_of_block,
                                     plus_time_work_block=plus_time_work_block,
                                     all_time_DP=all_time_DP, cold_event=cold_event,
                                     updated_data_block_values=updated_data_block_values,
                                     recast_time_block=str_clock,
                                     recast_last_emoji=last_emoji,
                                     updated_data_seeing_event=updated_data_seeing_event,
                                     recast_index=recast_index,
                                     stb_block=stb_block)

            # стандартное сохранение
            else:
                save_data_process_dp(callback.from_user.id,
                                     recast_time_block=str_clock,
                                     our_part_of_block=our_part_of_block,
                                     recast_last_emoji=last_emoji,
                                     huge_list=huge_list,
                                     cold_event=cold_event,
                                     updated_data_seeing_event=updated_data_seeing_event,
                                     recast_index=recast_index)

            # изменение времени
            while not int(get_data_process_dp(callback.from_user.id, 'the_end_dp')):
                await asyncio.sleep(60)

                # не завершён ли ДП
                if get_process_dp_status(callback.from_user.id, cursor) != 0:
                    break
                else:

                    # GET_DATA_PROCESS_DP
                    clock_block, delta_utc, plus_time_work_block, \
                    stb_block, updated_data_block_values, \
                    last_page, last_emoji, cold_event, \
                    clock_event, progress_block, \
                    recast_last_emoji, recast_time_block, id_dp, \
                    huge_list = \
                        get_data_process_dp(callback.from_user.id,
                                            'clock_block', 'delta_utc', 'plus_time_work_block',
                                            'stb_block', 'updated_data_block_values',
                                            'last_page', 'last_emoji', 'cold_event',
                                            'clock_block', 'progress_block',
                                            'recast_last_emoji', 'recast_time_block', 'id_dp',
                                            'huge_list')

                    # если ДП активен
                    if id_dp:

                        # обновляем время каждые 60 секунд
                        str_clock = get_delta_time_to_str(clock_block, delta_utc,
                                                          adding_time=plus_time_work_block - stb_block)

                        updated_data_block_values, \
                        asked, need, _ \
                            = get_full_block_values(updated_data_block_values=updated_data_block_values,
                                                    huge_list=huge_list, last_page=last_page,
                                                    last_emoji=last_emoji, cold_event=cold_event,
                                                    clock_event=clock_event, clock_block=clock_block,
                                                    str_clock=str_clock, yet_done=updated_data_block_values[3],
                                                    progress_block=progress_block)

                        if get_data_process_dp(callback.from_user.id, 'proof') == 'usual_block_check' \
                                and last_emoji == recast_last_emoji \
                                and str_clock != recast_time_block:

                            try:
                                await bot.edit_message_text(
                                    text=asked, chat_id=callback.from_user.id, message_id=id_dp,
                                    parse_mode=ParseMode.HTML, reply_markup=need_kb)
                            except MessageNotModified:
                                pass

                            save_data_process_dp(callback.from_user.id,
                                                 updated_data_block_values=updated_data_block_values,
                                                 recast_time_block=str_clock)
                        else:
                            break

    # 5/освещение блока - убрать заморозку
    @dp.callback_query_handler(text="sunning", state=main_menu.work_dp)
    async def sun_to_block(callback: CallbackQuery):
        save_data_process_dp(callback.from_user.id, proof='sunning_block_check')

        # GET_DATA_PROCESS_DP
        user_appeal, id_dp, cold_block, last_page = \
            get_data_process_dp(callback.from_user.id, 'user_appeal', 'id_dp',
                                'cold_block', 'last_page')

        # создаём КБ
        sun_kb = row_buttons(get_button(back_mes,
                                        callback_data=f'{last_page}_xDP'))

        # создаём лист со всеми замороженными блоками-эмоджи
        butt_list = [get_button(f'{one_emoji}',
                                callback_data=f'{one_emoji}_SUNbl')
                     for one_emoji in tuple(cold_block)]

        add_buttons(*butt_list, your_kb=sun_kb, row_width=4)
        # возможность разлунить сразу все
        if len(butt_list) > 1:
            row_buttons(get_button('❄️УБРАТЬ ЗАМОРОЗКУ У ВСЕХ❄️',
                                   callback_data='all_return_SUNbl'), your_kb=sun_kb)

        # создём клавиатуру с помощью to_big_kb и отправляем
        try:
            if get_data_process_dp(callback.from_user.id, 'proof') == 'sunning_block_check':
                await bot.edit_message_text(f'<b>❄️{user_appeal if user_appeal else callback.from_user.username}</b>, '
                                            f'что ты хочешь разморозить?',
                                            chat_id=callback.from_user.id,
                                            message_id=id_dp,
                                            reply_markup=sun_kb, parse_mode=ParseMode.HTML)
        except MessageNotModified:
            pass

    # 6/работа с конкретным элементом
    @dp.callback_query_handler(text="seeing_one_element", state=main_menu.work_dp)
    @dp.callback_query_handler(text="eclipse_el", state=main_menu.work_dp)
    @dp.callback_query_handler(Text(endswith="_disappearMOON"), state=main_menu.work_dp)
    async def body_element_see(callback: CallbackQuery):
        save_data_process_dp(callback.from_user.id, proof='see_event_check')

        # GET_DATA_PROCESS_DP
        updated_data_seeing_event, cold_event, \
        our_part_of_block, last_emoji, real_number_stars, \
        huge_list, id_dp, recast_index, \
        work_with_index_emoji, updated_data_event_doing = \
            get_data_process_dp(callback.from_user.id,
                                'updated_data_seeing_event', 'cold_event',
                                'our_part_of_block', 'last_emoji', 'real_number_stars',
                                'huge_list', 'id_dp', 'recast_index',
                                'work_with_index_emoji', 'updated_data_event_doing')

        # полнолуние элементов
        if callback.data == 'eclipse_el':
            cold_event.append(recast_index)
            huge_list[recast_index][1] = '🌑'

        # снятие луны у элементов
        elif '_disappearMOON' in callback.data:

            # убираем луну у одного элемента
            if 'all_return' not in callback.data:
                no_moon_event_index = int(callback.data[:-14])
                cold_event.remove(no_moon_event_index)
                huge_list[no_moon_event_index][1] = last_emoji

            # убираем луну у всех возможных
            else:
                for no_moon_event_index in cold_event:
                    huge_list[no_moon_event_index][1] = last_emoji
                cold_event = []

        # получаем строки и КБ эвента
        huge_list, cold_event, \
        updated_data_seeing_event, our_part_of_block, \
        condition_update_values_event, \
        asked, need_kb = \
            get_seeing_event_values(updated_data_seeing_event=updated_data_seeing_event,
                                    huge_list=huge_list, cold_event=cold_event,
                                    our_part_of_block=our_part_of_block, last_emoji=last_emoji,
                                    real_number_stars=real_number_stars, work_with_index_emoji=work_with_index_emoji)

        try:
            await bot.edit_message_text(asked, chat_id=callback.from_user.id,
                                        message_id=id_dp, parse_mode=ParseMode.HTML,
                                        reply_markup=need_kb)

            if callback.data == 'eclipse_el':
                await bot.answer_callback_query(callback.id, "🌑")

        except MessageNotModified or InvalidQueryID:
            pass

        # не продолжаем, если ДП всё
        if get_data_process_dp(callback.from_user.id, 'proof') != 'THE_END_DP':
            # SAVE_DATA_PROCESS_DP

            # затмнение | убрать затмение (updated_data_seeing_event меняется) | изменение updated_data_seeing_event
            if condition_update_values_event \
                    or (not updated_data_event_doing or updated_data_event_doing[0] != huge_list):
                # заранее генерируем рабочий эвент
                updated_data_event_doing, huge_list, *_ = \
                    get_full_event_do_values(updated_data_event_doing=updated_data_event_doing,
                                             huge_list=huge_list,
                                             updated_data_seeing_event=updated_data_seeing_event,
                                             str_clock='𝟬𝟬𝟬', needing_clock_diff=0)

                save_data_process_dp(callback.from_user.id,
                                     huge_list=huge_list, cold_event=cold_event,
                                     updated_data_seeing_event=updated_data_seeing_event,
                                     recast_index=updated_data_seeing_event[1],
                                     our_part_of_block=our_part_of_block,
                                     updated_data_event_doing=updated_data_event_doing)

    # 7/исчезновение луны - убрать луну у элемента
    @dp.callback_query_handler(text="mooning", state=main_menu.work_dp)
    async def not_moon_to_event(callback: CallbackQuery):
        save_data_process_dp(callback.from_user.id, proof='mooning_event_check')

        # GET_DATA_PROCESS_DP
        user_appeal, id_dp, last_page, cold_event = \
            get_data_process_dp(callback.from_user.id, 'user_appeal', 'id_dp',
                                'last_page', 'cold_event')

        not_moon_kb = row_buttons(get_button(back_mes,
                                             callback_data=f'{last_page}_xDP'))
        # стандартно сортируем лист по возврастанию
        cold_event.sort()

        # с помощью big_replacing переводим число в emoji
        butt_list = [get_button(f'{big_replacing(one_elem + 1, your_dict=nums_and_emoji)}',
                                callback_data=f'{one_elem}_disappearMOON')
                     for one_elem in cold_event]

        add_buttons(*butt_list, your_kb=not_moon_kb, row_width=4)
        # возможность разлунить сразу все
        if len(butt_list) > 1:
            row_buttons(get_button('🌑УБРАТЬ ЗАТМЕНЕНИЕ У ВСЕХ🌑',
                                   callback_data='all_return_disappearMOON'), your_kb=not_moon_kb)

        try:
            if get_data_process_dp(callback.from_user.id, 'proof') == 'mooning_event_check':
                await bot.edit_message_text(f'🌑<b>{user_appeal if user_appeal else callback.from_user.username}</b>, '
                                            f'где должно пройти затмение?',
                                            chat_id=callback.from_user.id,
                                            message_id=id_dp,
                                            reply_markup=not_moon_kb, parse_mode=ParseMode.HTML)
        except MessageNotModified:
            pass

    # 8/непосредственно выполнение данного элемента
    @dp.callback_query_handler(text="in_doing_event", state=main_menu.work_dp)
    @dp.callback_query_handler(text="already_ready_event", state=main_menu.work_dp)
    async def body__element_do(callback: CallbackQuery):
        save_data_process_dp(callback.from_user.id, proof='doing_event_check')

        # GET_DATA_PROCESS_DP
        clock_event, updated_data_seeing_event, clock_block, \
        all_time_DP, last_emoji, delta_utc, \
        cl_ev_for_block, stb_event, updated_data_event_doing, \
        huge_list, id_dp = \
            get_data_process_dp(callback.from_user.id,
                                'clock_event', 'updated_data_seeing_event', 'clock_block',
                                'all_time_DP', 'last_emoji', 'delta_utc',
                                'cl_ev_for_block', 'stb_event', 'updated_data_event_doing',
                                'huge_list', 'id_dp')

        # если пользователь закончил дело раньше
        if callback.data == 'already_ready_event':
            huge_list[updated_data_seeing_event[1]][2] = 0

        # запускаем часы эвента
        if not clock_event:
            index_el = updated_data_seeing_event[1]

            # добавляем в список со временем ярлык блока, если нет его
            if not clock_block or not all_time_DP[-1].get(last_emoji):
                all_time_DP.append({last_emoji: []})

            # добавляем ярлык на эвент
            all_time_DP[-1][last_emoji].append([huge_list[index_el][0][0]])
            # фиксируем время
            clock_event = str(get_user_time_now(delta_utc))

            # для времени блока
            cl_ev_for_block[index_el] = clock_event

        # время в 000
        str_clock, needing_clock_diff = get_delta_time_to_str(clock_event, delta_utc,
                                                              adding_time=-stb_event,
                                                              needing_clock_diff=True)

        # текст&КБ эвента
        updated_data_event_doing, \
        huge_list, \
        asked, need_kb, \
        condition_update_value_event = \
            get_full_event_do_values(updated_data_event_doing=updated_data_event_doing,
                                     huge_list=huge_list,
                                     updated_data_seeing_event=updated_data_seeing_event,
                                     str_clock=str_clock, needing_clock_diff=needing_clock_diff,
                                     action=callback.data)

        try:
            if get_data_process_dp(callback.from_user.id, 'proof') == 'doing_event_check':
                await bot.edit_message_text(asked, chat_id=callback.from_user.id,
                                            message_id=id_dp, parse_mode=ParseMode.HTML,
                                            reply_markup=need_kb)

            if callback.data == 'already_ready_event':
                await callback.answer('➕STRONG➕')

        except MessageNotModified or InvalidQueryID:
            pass

        # не продолжаем, если ДП всё
        if get_data_process_dp(callback.from_user.id, 'proof') != 'THE_END_DP':
            # SAVE_DATA_PROCESS_DP

            # при изменении КБ
            if condition_update_value_event:
                save_data_process_dp(callback.from_user.id,
                                     updated_data_event_doing=updated_data_event_doing,
                                     huge_list=huge_list,
                                     recast_time_event=str_clock,
                                     clock_event=clock_event, all_time_DP=all_time_DP, cl_ev_for_block=cl_ev_for_block)
            else:
                save_data_process_dp(callback.from_user.id,
                                     recast_time_event=str_clock,
                                     clock_event=clock_event, all_time_DP=all_time_DP, cl_ev_for_block=cl_ev_for_block)

            # изменение времени
            while not int(get_data_process_dp(callback.from_user.id, 'the_end_dp')):
                await asyncio.sleep(60)

                # не завершён ли ДП
                if get_process_dp_status(callback.from_user.id, cursor) != 0:
                    break
                else:

                    # GET_DATA_PROCESS_DP
                    clock_event, delta_utc, stb_event, \
                    updated_data_event_doing, huge_list, updated_data_seeing_event, \
                    huge_list, recast_time_event, id_dp = \
                        get_data_process_dp(callback.from_user.id,
                                            'clock_event', 'delta_utc', 'stb_event',
                                            'updated_data_event_doing', 'huge_list', 'updated_data_seeing_event',
                                            'huge_list', 'recast_time_event', 'id_dp')

                    # если ДП активен
                    if id_dp:

                        # обновляем время
                        str_clock, needing_clock_diff = get_delta_time_to_str(clock_event, delta_utc,
                                                                              adding_time=-stb_event,
                                                                              needing_clock_diff=True)

                        # текст&КБ эвента
                        updated_data_event_doing, \
                        huge_list, \
                        asked, need_kb, *_ = \
                            get_full_event_do_values(updated_data_event_doing=updated_data_event_doing,
                                                     huge_list=huge_list,
                                                     updated_data_seeing_event=updated_data_seeing_event,
                                                     str_clock=str_clock, needing_clock_diff=needing_clock_diff)

                        if get_data_process_dp(callback.from_user.id, 'proof') == 'doing_event_check' \
                                and str_clock != recast_time_event:

                            try:
                                await bot.edit_message_text(
                                    text=asked, chat_id=callback.from_user.id, message_id=id_dp,
                                    parse_mode=ParseMode.HTML, reply_markup=need_kb)
                            except MessageNotModified:
                                pass

                            save_data_process_dp(callback.from_user.id,
                                                 updated_data_event_doing=updated_data_event_doing,
                                                 recast_time_event=str_clock)

    # 9/sett_DP
    @dp.callback_query_handler(text="settings_DP",
                               state=(main_menu.work_dp, main_menu.remaking_dp))
    @dp.callback_query_handler(text=("save_changes", 'no_save_changes'),
                               state=main_menu.remaking_dp)
    async def body_settings_dp(callback: CallbackQuery):
        await main_menu.work_dp.set()
        save_last_state_user(callback.from_user.id, 'work_dp', cursor, conn)
        save_data_process_dp(callback.from_user.id, proof='settings_check')

        id_dp, last_page = \
            get_data_process_dp(callback.from_user.id, 'id_dp', 'last_page')

        await bot.edit_message_text(f'⚙️<i>НАСТРОЙКИ</i>⚙️', chat_id=callback.from_user.id,
                                    message_id=id_dp,
                                    reply_markup=get_sett_kb(last_page),
                                    parse_mode=ParseMode.HTML)

        # разбираемся с разными callbacks
        if callback.data == 'save_changes':
            save_dp_remakes(callback.from_user.id)
            await callback.answer(f'DAY PLAN сохранён!')

        save_data_process_dp(callback.from_user.id,
                             remake_huge_list=None,
                             remake_element=None,
                             history_remakes=None,
                             updated_data_steps_and_save=None)

    # 10/sett_DP/STOP_DP
    @dp.callback_query_handler(text="stop_dp", state=main_menu.work_dp)
    async def sett_stop_dp(callback: CallbackQuery):
        save_data_process_dp(callback.from_user.id, proof='stop_dp_check')

        # сохраняем время стопа
        delta_utc, huge_list, id_dp = \
            get_data_process_dp(callback.from_user.id, 'delta_utc', 'huge_list', 'id_dp')
        save_data_process_dp(callback.from_user.id,
                             stop_time_begin=str(get_user_time_now(delta_utc)))

        # сообщение стопа из двух частей
        for index_part, one_part_stop in enumerate(dp_stop_tuple):

            # когда второй индекс, используем active_kb
            if get_data_process_dp(callback.from_user.id, 'proof') == 'stop_dp_check':
                await bot.edit_message_text(f'⊙{"".join(dp_stop_tuple) if index_part else one_part_stop}',
                                            chat_id=callback.from_user.id,
                                            message_id=id_dp,
                                            reply_markup=
                                            active_kb if index_part
                                            else None)

    # 11/sett_DP/dynamic_dp
    @dp.callback_query_handler(text=("dynamic_work", 'back_to_choose_graph'), state=main_menu.work_dp)
    async def sett_dynamic_work(callback: CallbackQuery):
        # GET_DATA_PROCESS_DP
        clock_event, clock_block, id_dp, = \
            get_data_process_dp(callback.from_user.id,
                                'clock_event', 'clock_block', 'id_dp')

        # только если clock_block is None and clock_event is None
        if not clock_block and not clock_event:

            # возвращаемся к выбору графиков из конкретного графика
            if callback.data == 'back_to_choose_graph':
                await delete_work_message(callback.from_user.id, bot, cursor)

                # отправляем новое сообщение обнолвяем айди
                new_work_mes = \
                    await bot.send_message(text=f'⚙️<b>Н/</b><i>ДИНАМИКА РАБОТЫ</i>⚙️',
                                           chat_id=callback.from_user.id,
                                           reply_markup=dynamic_kb,
                                           parse_mode=ParseMode.HTML)
                save_main_id_message(callback.from_user.id, new_work_mes.message_id, cursor, conn)
                save_data_process_dp(callback.from_user.id, id_dp=new_work_mes.message_id)

            else:
                await bot.edit_message_text(f'⚙️<b>Н/</b><i>ДИНАМИКА РАБОТЫ</i>⚙️',
                                            chat_id=callback.from_user.id,
                                            message_id=id_dp,
                                            reply_markup=dynamic_kb,
                                            parse_mode=ParseMode.HTML)

        else:
            await callback.answer('БЛОК ДОЛЖЕН БЫТЬ ЗАКРЫТ')

    # 12/sett_DP/dynamic_dp/get_graph
    @dp.callback_query_handler(text=('area_graph', 'circle_graph'), state=main_menu.work_dp)
    async def sett_get_graph(callback: CallbackQuery):

        updated_data_graphs, \
        all_time_DP, block_names_dict, block_colours_dict, \
        DP_clock, huge_list, real_number_stars, \
        work_with_index_emoji, bot_id = \
            get_data_process_dp(callback.from_user.id, 'updated_data_graphs',
                                'all_time_DP', 'block_names_dict', 'block_colours_dict',
                                'DP_clock', 'huge_list', 'real_number_stars',
                                'work_with_index_emoji', 'bot_id')

        if all_time_DP:
            await delete_work_message(callback.from_user.id, bot, cursor)

            # None | изменение времени
            condition_remaking_graph = \
                not updated_data_graphs.get(callback.data) \
                or updated_data_graphs.get(callback.data)[0] != all_time_DP
            if condition_remaking_graph:

                # отправляем сообщение загрузки
                new_work_mes = await bot.send_animation(chat_id=callback.from_user.id,
                                         animation=
                                         'CgACAgQAAxkBAAIamWQXDhFLZdZSFWVzhPxbCTL9yDQwAAL0AgAC2ywNU8_jyzgC4dWdLwQ')
                save_main_id_message(callback.from_user.id, new_work_mes.message_id, cursor, conn)

                useful_delta = get_dynamic_dp_photo(all_time_DP,
                                     block_colours_dict, block_names_dict,
                                     the_end_dp=False, first_time_dp=DP_clock,
                                     get_area_graph=True if callback.data == 'area_graph' else False,
                                     save_path=f'users_bot/{bot_id}_log/for_work_dp',
                                     name_photo=f'dp_dynamic_photo_{callback.data}')

                photo_id = \
                    InputFile(path_or_bytesio=f'users_bot/{bot_id}_log/'
                                              f'for_work_dp/dp_dynamic_photo_{callback.data}.jpg')
                text_under_photo = \
                    f'⚙️<b>Н/ДР/</b>' \
                    f'<i>{"ЭВЕНТЫ" if callback.data == "area_graph" else "БЛОКИ"}</i>⚙️\n\n' \
                    f'<b>ДИНАМИКА РАБОТЫ</b>\n' \
                    f'◾️ОСТАЛОСЬ ЭВЕНТОВ: ' \
                    f'<code>{len(huge_list) - real_number_stars}</code>\n' \
                    f'◾️ОСТАЛОСЬ БЛОКОВ: ' \
                    f'<code>{sum(bool(block) for block in work_with_index_emoji.values())}</code>\n'\
                    f'◾️КПД: ' \
                    f'<code>' \
                    f'{useful_delta}%' \
                    f'</code>'

                updated_data_graphs[callback.data] = [all_time_DP, photo_id, text_under_photo]

            else:
                photo_id, text_under_photo = \
                    updated_data_graphs.get(callback.data)[1:]

            if condition_remaking_graph:
                new_work_mes = \
                    await bot.edit_message_media(media=InputMediaPhoto(photo_id,
                                                                       caption=text_under_photo,
                                                                       parse_mode=ParseMode.HTML),
                                                 chat_id=callback.from_user.id,
                                                 message_id=get_main_id_message(callback.from_user.id, cursor),
                                                 reply_markup=row_buttons(back_mes_but('back_to_choose_graph')))

                # сохраняем айди фотографии, чтобы быстрее присылать
                updated_data_graphs[callback.data][1] = new_work_mes.photo[-1].file_id
                save_data_process_dp(callback.from_user.id, updated_data_graphs=updated_data_graphs)

            else:
                new_work_mes = await bot.send_photo(chat_id=callback.from_user.id,
                                                    photo=photo_id,
                                                    caption=text_under_photo,
                                                    parse_mode=ParseMode.HTML,
                                                    reply_markup=row_buttons(back_mes_but('back_to_choose_graph')))
                save_main_id_message(callback.from_user.id, new_work_mes.message_id, cursor, conn)

        else:
            await callback.answer('DAY PLAN ДОЛЖЕН БЫТЬ НАЧАТ')

    # 13/sett_DP/element_order
    @dp.callback_query_handler(text="coordinate_elements",
                               state=main_menu.work_dp)
    @dp.callback_query_handler(Text(endswith="_sett_dp_1"),
                               state=main_menu.remaking_dp)
    async def sett_elem_order(callback: CallbackQuery):
        # GET_DATA_PROCESS_DP
        huge_list, clock_event, clock_block, \
        id_dp, remake_huge_list, remake_element, \
        last_page_set_2, updated_data_values_first_dp, history_remakes = \
            get_data_process_dp(callback.from_user.id,
                                'huge_list', 'clock_event', 'clock_block',
                                'id_dp', 'remake_huge_list', 'remake_element',
                                'last_page_set_2', 'updated_data_values_first_dp', 'history_remakes')

        # только если clock_block is None and clock_event is None
        if not clock_block and not clock_event:
            await main_menu.remaking_dp.set()
            save_last_state_user(callback.from_user.id, 'remaking_dp', cursor, conn)

            message_pages = int(callback.data[:-10]) if 'sett_dp_1' in callback.data \
                else 1

            if not remake_huge_list:
                remake_huge_list = huge_list

            # специальный деф для работы с remake_dp_1
            asked, need_kb, \
            updated_data_values_first_dp = \
                values_for_remake_dp_first(huge_list=huge_list,
                                           remake_huge_list=remake_huge_list, remake_element=remake_element,
                                           message_pages=message_pages, last_page_set_2=last_page_set_2,
                                           updated_data_values_first_dp=updated_data_values_first_dp)

            try:
                await bot.edit_message_text(f'⚙️<b>Н/</b><i>ПОРЯДОК ПЛАНА</i>⚙️\n\n'
                                            f'<b>📌Выберите элемент расписания!</b>\n'
                                            f'{asked}', chat_id=callback.from_user.id,
                                            message_id=id_dp,
                                            reply_markup=need_kb,
                                            parse_mode=ParseMode.HTML)
            except MessageNotModified:
                pass

            # если remake_huge_list был None
            if not history_remakes:
                save_data_process_dp(callback.from_user.id, last_page_set_1=message_pages,
                                     remake_huge_list=remake_huge_list,
                                     history_remakes=[('1_sett_dp_1', remake_huge_list)],
                                     updated_data_steps_and_save=None,
                                     updated_data_values_first_dp=updated_data_values_first_dp)
            else:
                save_data_process_dp(callback.from_user.id, last_page_set_1=message_pages,
                                     updated_data_values_first_dp=updated_data_values_first_dp)

        else:
            await callback.answer('БЛОК ДОЛЖЕН БЫТЬ ЗАКРЫТ')

    # 14/sett_DP/element_order/ask: are you right?
    @dp.callback_query_handler(text="condition_closing", state=main_menu.remaking_dp)
    async def sett_elem_ask(callback: CallbackQuery):
        # GET_DATA_PROCESS_DP
        id_dp = \
            get_data_process_dp(callback.from_user.id, 'id_dp')

        save_remakes_kb = add_buttons(get_button('СОХРАНИТЬ', callback_data='save_changes'),
                                      get_button('НЕ СОХРАНЯТЬ', callback_data='no_save_changes'),
                                      get_button('ОБРАТНО К ИЗМЕНЕНИЯМ', callback_data='1_sett_dp_1'),
                                      row_width=2)

        await bot.edit_message_text(f'⚙️<b>Н/</b><i>ПОРЯДОК ПЛАНА</i>⚙️\n\n'
                                    f'<b>❓Сохранить изменения DAY PLAN❓</b>', chat_id=callback.from_user.id,
                                    message_id=id_dp,
                                    reply_markup=save_remakes_kb,
                                    parse_mode=ParseMode.HTML)

    # 15/sett_DP/element_order/seeking_remake_el
    @dp.message_handler(Text(endswith="BLX"),
                        state=main_menu.remaking_dp)
    @dp.message_handler(Text(startswith="/EVN"),
                        state=main_menu.remaking_dp)
    @dp.message_handler(Text(startswith="/PART"),
                        state=main_menu.remaking_dp)
    async def sett_seeking_els(message: Message):
        await message.delete()

        # GET_DATA_PROCESS_DP
        id_dp, remake_huge_list, updated_data_relocating_elem, \
        last_page_set_1, last_page_set_3 = \
            get_data_process_dp(message.from_user.id,
                                'id_dp', 'remake_huge_list', 'updated_data_relocating_elem',
                                'last_page_set_1', 'last_page_set_3')

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

                    save_data_process_dp(message.from_user.id,
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
                                                      get_data_process_dp(message.from_user.id,
                                                                          'relocating_part_block'))
            try:
                await bot.edit_message_text(f'⚙️<b>Н/</b><i>ПОРЯДОК ПЛАНА</i>⚙️\n\n'
                                            f'🔺️️<b>Перемещайте выбранный элемент</b>🔻\n\n'
                                            f'{asked}', chat_id=message.from_user.id,
                                            message_id=id_dp,
                                            reply_markup=need_kb,
                                            parse_mode=ParseMode.HTML)
            except MessageToEditNotFound:
                await existing_work_message(message.from_user.id, bot,
                                            cursor, conn,
                                            main_menu)
            except MessageNotModified:
                pass

            save_data_process_dp(message.from_user.id,
                                 remake_element=remake_element,
                                 last_action_remaking=None,
                                 last_page_set_2=1,
                                 updated_data_relocating_elem=updated_data_relocating_elem)

    # 16/sett_DP/element_order/seeking_remake_el/to_pages
    @dp.callback_query_handler(text=("up_element", 'down_element'), state=main_menu.remaking_dp)
    @dp.callback_query_handler(Text(endswith="sett_dp_2"), state=main_menu.remaking_dp)
    async def sett_to_remake_pages(callback: CallbackQuery):

        # GET_DATA_PROCESS_DP
        id_dp, remake_huge_list, remake_element, \
        updated_data_relocating_elem, relocating_part_block, \
        last_page_set_1, last_page_set_3, history_remakes, \
        last_action_remaking = \
            get_data_process_dp(callback.from_user.id, 'id_dp', 'remake_huge_list', 'remake_element',
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
            await bot.edit_message_text(f'⚙️<b>Н/</b><I>ПОРЯДОК ПЛАНА</i>⚙️\n\n'
                                        f'🔺️️<b>Перемещайте выбранный элемент</b>🔻\n\n'
                                        f'{asked}', chat_id=callback.from_user.id,
                                        message_id=id_dp,
                                        reply_markup=need_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(callback.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)
        except MessageNotModified:
            pass

        # SAVE_DATA_PROCESS_DP
        if 'sett_dp_2' in callback.data:
            save_data_process_dp(callback.from_user.id,
                                 last_page_set_2=message_pages if type(message_pages) is int else 1,
                                 updated_data_relocating_elem=updated_data_relocating_elem)
        else:
            save_data_process_dp(callback.from_user.id,
                                 remake_element=remake_element, remake_huge_list=remake_huge_list,
                                 relocating_part_block=relocating_part_block, history_remakes=history_remakes,
                                 last_page_set_2=message_pages if type(message_pages) is int else 1,
                                 updated_data_relocating_elem=updated_data_relocating_elem,
                                 last_action_remaking=last_action_remaking)

    # 17/sett_DP/element_order/seeking_remake_el/to_pages/to_remakes
    @dp.callback_query_handler(text=("back_old_step", 'back_future_step'), state=main_menu.remaking_dp)
    @dp.callback_query_handler(text="save_remakes", state=main_menu.remaking_dp)
    @dp.callback_query_handler(Text(endswith="_sett_dp_3"), state=main_menu.remaking_dp)
    async def sett_to_remakes(callback: CallbackQuery):

        # GET_DATA_PROCESS_DP
        id_dp, remake_huge_list, updated_data_steps_and_save, \
        history_remakes, message_pages, remake_element, \
        last_page_set_2 = \
            get_data_process_dp(callback.from_user.id,
                                'id_dp', 'remake_huge_list', 'updated_data_steps_and_save',
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
            await bot.edit_message_text(f'⚙️<b>Н/</b><i>ПОРЯДОК ПЛАНА</i>⚙️\n\n'
                                        f'✔️<b>SIMPLE DAY PLAN</b>✖️\n\n'
                                        f'{asked}', chat_id=callback.from_user.id,
                                        message_id=id_dp,
                                        reply_markup=need_kb,
                                        parse_mode=ParseMode.HTML)
        except MessageToEditNotFound:
            await existing_work_message(callback.from_user.id, bot,
                                        cursor, conn,
                                        main_menu)

        # SAVE_DATA_PROCESS_DP
        # шагам по истории
        if callback.data in ("back_old_step", 'back_future_step'):
            save_data_process_dp(callback.from_user.id, remake_element=remake_element,
                                 remake_huge_list=remake_huge_list,
                                 history_remakes=history_remakes,
                                 updated_data_steps_and_save=updated_data_steps_and_save)

        elif callback.data == 'save_remakes':
            save_dp_remakes(callback.from_user.id, updated_data_steps_and_save)
            await callback.answer(f'DAY PLAN сохранён!')

        # изменение страницы
        else:
            save_data_process_dp(callback.from_user.id, last_page_set_3=message_pages,
                                 updated_data_steps_and_save=updated_data_steps_and_save)

    # 18/(close_DP | get_next_dp)
    @dp.callback_query_handler(text=("close_DP", 'get_next_dp'), state=main_menu.work_dp)
    async def all_work_done(callback: CallbackQuery):

        if callback.data == 'close_DP':

            # GET_DATA_PROCESS_DP
            huge_list, all_time_DP, \
            datetime_work, the_end_dp, \
            block_names_dict, block_colours_dict, bot_id = \
                get_data_process_dp(callback.from_user.id,
                                    'huge_list', 'all_time_DP',
                                    'datetime_work', 'the_end_dp',
                                    'block_names_dict', 'block_colours_dict', 'bot_id')

            # GET_COMMON_DATA
            data_end_dp = get_common_data(callback.from_user.id, cursor, 'data_end_dp')

            # в момент сразу после закрытия
            if not data_end_dp:
                await delete_work_message(callback.from_user.id, bot, cursor)

                # подключаемся к именованной БД пользователя
                conn_login = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db')
                cursor_login = conn_login.cursor()

                # дата ДП
                datetime_work_in_datetime_type = \
                    get_datetime_from_str(datetime_work)
                day_week_dp = datetime.datetime.weekday(datetime_work_in_datetime_type)
                date_dp = datetime.datetime.date(datetime_work_in_datetime_type)

                # время работы ДП
                delta_secs_dp = \
                    (get_datetime_from_str(all_time_DP[-1][1]) -
                     get_datetime_from_str(all_time_DP[-1][0])).total_seconds() if all_time_DP else 0
                delta_mins_dp = \
                    big_replacing(math.floor(delta_secs_dp / 60), your_dict=dict_with_bold_nums)

                # количество (успешных | провальных) ДП
                all_dp_values = cursor_login.execute('SELECT full_dp FROM history_working WHERE full_dp = ?',
                                                     (1 if the_end_dp == 1 else 0,)).fetchall()
                done_day_plans = len(all_dp_values) if all_dp_values else 0

                # кол-во done elements
                all_events = big_replacing(len(huge_list) if huge_list else 0, your_dict=dict_with_bold_nums)
                all_blocks = big_replacing(len(tuple(block_names_dict)) if block_names_dict else 0,
                                           your_dict=dict_with_bold_nums)

                # формируем текст для сообщения
                text_end_dp = f'📋<b>{date_dp} | {short_name_week_days[day_week_dp]}</b>\n' \
                              '➖➖➖➖➖➖➖➖➖➖➖➖➖\n' \
                              f'☀️<b>Выполнено эвентов:</b> <code>{all_events}</code>\n' \
                              f'🌕<b>Выполнено блоков:</b> <code>{all_blocks}</code>\n' \
                              f'⏳<b>Всего затрачено минут:</b> <code>{delta_mins_dp}</code>\n' \
                              '➖➖➖➖➖➖➖➖➖➖➖➖➖\n' \
                              f'<b>{"⭐УСПЕХ" if the_end_dp == 1 else "❌КРАХ"} ' \
                              f'{num2words(done_day_plans + 1, to="ordinal", lang="ru").upper()}</b>️'

                # обновляем историю выполнений ДП
                cursor.execute("UPDATE all_sessions SET processing_dp = ? WHERE user_id = ?",
                               (1, callback.from_user.id,))
                conn.commit()

                cursor_login.execute('INSERT INTO history_working (date, week_day, full_dp, doing_speed, delta_work) '
                                     'VALUES (?, ?, ?, ?, ?)',
                                     (str(date_dp),
                                      str(day_week_dp),
                                      1 if the_end_dp == 1 else 0,
                                      str(all_time_DP) if all_time_DP else None,
                                      str((get_datetime_from_str(all_time_DP[-1][1]) -
                                           get_datetime_from_str(all_time_DP[-1][0])).total_seconds()
                                          if all_time_DP else 0)), )
                conn_login.commit()

                data_end_dp = [text_end_dp,
                               get_common_data(callback.from_user.id, cursor, 'inf_for_begin_dp')[8]]
                save_common_data(callback.from_user.id, cursor, conn, data_end_dp=data_end_dp)

                new_work_mes = \
                    await bot.send_photo(photo=data_end_dp[1],
                                     caption=data_end_dp[0], chat_id=callback.from_user.id,
                                     parse_mode=ParseMode.HTML,
                                     reply_markup=await get_end_dp_kb(callback.from_user.id,
                                                                      callback.from_user.username, bot))
                save_main_id_message(callback.from_user.id, new_work_mes.message_id, cursor, conn)

            # при возвращении к странице end_dp
            else:
                await bot.edit_message_media(media=InputMediaPhoto(data_end_dp[1],
                                                                   caption=data_end_dp[0], parse_mode=ParseMode.HTML),
                                             chat_id=callback.from_user.id,
                                             message_id=get_main_id_message(callback.from_user.id, cursor),
                                             reply_markup=
                                             await get_end_dp_kb(callback.from_user.id,
                                                                 callback.from_user.username, bot))

        else:
            await delete_work_message(callback.from_user.id, bot, cursor)
            await get_window_with_excel_dp(callback.from_user.id, callback.from_user.username,
                                           processing_dp=None, bot=bot)

    # 19/close_DP/(BLOCKS | EVENTS) GRAPHS
    @dp.callback_query_handler(text=("area_graph_with_end", 'circle_graph_with_end'), state=main_menu.work_dp)
    @dp.callback_query_handler(text=("area_animate_get", 'circle_animate_get'), state=main_menu.work_dp)
    async def see_end_graphs(callback: CallbackQuery):

        # GET_DATA_PROCESS_DP
        login_user, \
        all_time_DP, block_colours_dict, block_names_dict, \
        dict_with_media_data, exist_area_graph, exist_circle_graph, \
        bot_id = \
            get_data_process_dp(callback.from_user.id,
                                'login_user', 'all_time_DP', 'block_colours_dict', 'block_names_dict',
                                'dict_with_media_data', 'exist_area_graph', 'exist_circle_graph',
                                'bot_id')
        type_graph = "area" if callback.data[:4] == "area" else "circle"

        # если ещё не сохранено такое фото/видео,
        if not dict_with_media_data.get(callback.data):
            # отправляем сообщение загрузки
            await bot.edit_message_media(media=InputMediaAnimation('CgACAgQAAxkBAAIamWQXDhFLZdZSFWVzhPxb'
                                                                   'CTL9yDQwAAL0AgAC2ywNU8_jyzgC4dWdLwQ'),
                                         chat_id=callback.from_user.id,
                                         message_id=get_main_id_message(callback.from_user.id, cursor))

        # если фото
        if callback.data in ("area_graph_with_end", 'circle_graph_with_end'):

            # создаём общую КБ
            reply_markup = \
                row_buttons(back_mes_but('close_DP'),
                            get_button('▶️', callback_data='area_animate_get' if type_graph == 'area'
                            else 'circle_animate_get'))

            # если айди фото ещё не сохранён | нет данных для фото
            one_photo_id = dict_with_media_data.get(callback.data)
            if not one_photo_id \
                    and exist_circle_graph != 'no_data' and exist_area_graph != 'no_data':
                get_dynamic_dp_photo(all_time_DP,
                                     block_colours_dict, block_names_dict,
                                     the_end_dp=True,
                                     get_area_graph=True if type_graph == 'area' else False,
                                     save_path=f'users_bot/{bot_id}_log/for_work_dp',
                                     name_photo=f'dp_dynamic_photo_{type_graph}')

                one_photo_id = \
                    InputFile(path_or_bytesio=f'users_bot/{bot_id}_log/for_work_dp/'
                                              f'dp_dynamic_photo_{type_graph}.jpg')

            # данные для фото отсутствуют
            if exist_circle_graph == 'no_data' and exist_area_graph == 'no_data':

                reply_markup = row_buttons(back_mes_but('close_DP'))

                # no time photo
                one_photo_id = 'AgACAgIAAxkBAAIlZmQhW1zbmG-lr3KjsUlqc2OXiJw-AAI0yjEbUfAISQbUgoVUCyv3AQADAgADbQADLwQ'

            new_work_mes = await bot.edit_message_media(media=InputMediaPhoto(one_photo_id),
                                                        chat_id=callback.from_user.id,
                                                        message_id=get_main_id_message(callback.from_user.id, cursor),
                                                        reply_markup=reply_markup)

            if not dict_with_media_data.get(callback.data):
                dict_with_media_data[callback.data] = str(new_work_mes.photo[-1].file_id)
                save_data_process_dp(callback.from_user.id, dict_with_media_data=dict_with_media_data)

        # если видео
        else:

            reply_markup = \
                row_buttons(get_button('⏸', callback_data='area_graph_with_end' if type_graph == 'area'
                else 'circle_graph_with_end'))

            # если айди видео ещё не сохранено
            one_video_id = dict_with_media_data.get(callback.data)
            if not one_video_id:

                # проверяем: успели ли создаться видео
                one_condition = exist_area_graph if type_graph == 'area' else exist_circle_graph
                if one_condition:
                    one_video_id = \
                        InputFile(path_or_bytesio=f'users_bot/{bot_id}_log/for_work_dp/'
                                                  f'dp_dynamic_anim_{type_graph}.mp4')
                else:

                    # зацикливаем проверку создания + уведомление загрузки
                    while True:

                        exist_area_graph, exist_circle_graph = \
                            get_data_process_dp(callback.from_user.id, 'exist_area_graph', 'exist_circle_graph')

                        one_condition = exist_area_graph if type_graph == 'area' else exist_circle_graph
                        if one_condition:
                            one_video_id = \
                                InputFile(
                                    path_or_bytesio=f'users_bot/{bot_id}_log/for_work_dp/'
                                                    f'dp_dynamic_anim_{type_graph}.mp4')
                            break

                        # проверяем: существует ли ещё сообщение ожидания
                        if not await existing_work_message(callback.from_user.id, bot, cursor, conn, main_menu):
                            break

                        await asyncio.sleep(0.05)

            if one_video_id:
                new_work_mes = await bot.edit_message_media(media=InputMediaVideo(one_video_id),
                                                            chat_id=callback.from_user.id,
                                                            message_id=
                                                            get_main_id_message(callback.from_user.id, cursor),
                                                            reply_markup=reply_markup)

                if not dict_with_media_data.get(callback.data):
                    dict_with_media_data[callback.data] = str(new_work_mes.video.file_id)
                    save_data_process_dp(callback.from_user.id, dict_with_media_data=dict_with_media_data)

    # --/удаление лишних сообщений
    @dp.message_handler(state=(main_menu.work_dp, main_menu.remaking_dp), content_types=all_content_types)
    async def delete_endless_in_profile(message: Message):
        await message.delete()

        await existing_work_message(message.from_user.id, bot,
                                    cursor, conn,
                                    main_menu)
