import datetime
import sqlite3
import asyncio
import random
import uuid
import os
#
from aiogram import types
from aiogram.types import ParseMode
from aiogram.types import CallbackQuery
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State
from aiogram.utils.exceptions import InvalidQueryID
from aiogram.utils.exceptions import MessageNotModified, MessageToDeleteNotFound
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, \
    InlineKeyboardButton, InlineKeyboardMarkup
#
from utilis.consts_common import visiting_system_kb, \
    all_content_types, special_numbers_circle
from utilis.main_common import plus_to_reg_messages, minus_to_reg_messages
#
from sides_bot.reg_aut.utilis.consts import deregistration_kb, appeal_ques_kb, \
    secret_code_save_kb, no_ok_reg_kb, back_to_reform_menu_but, back_to_reform_menu_kb, \
    deauthorization_kb, appeal_board_reforming
from sides_bot.reg_aut.utilis.main import cancel_reg_or_aut, all_right_asking


def reg_and_aut(dp, bot, cursor, conn,
                first_actions, process_reg, reforming_reg_values, process_aut,
                main_menu, main_menu_kb, text_main_menu):

    # start: удаляет любые сообщения, присланные пользователем
    @dp.message_handler(state=first_actions.waiting_command,
                        content_types=all_content_types)
    async def delete_endless(message: types.Message):
        await message.delete()

    # reg_0: отмена регистрации
    @dp.callback_query_handler(text='restart_reg', state=process_reg.end_reg)
    async def stop_or_restart_reg_call(callback: types.CallbackQuery, state: FSMContext):
        await cancel_reg_or_aut(state, callback.from_user.id, bot, first_actions, cursor, conn,
                                restart=True)

    # reg_0.5: отмена регистрации
    @dp.message_handler(text="⭕ОТМЕНА РЕГИСТРАЦИИ⭕", state=(first_actions.begin_reg, process_reg.appeal,
                                                            process_reg.login, process_reg.password,
                                                            process_reg.end_reg))
    async def stop_or_restart_reg_mes(message: types.Message, state: FSMContext):
        await message.delete()
        await cancel_reg_or_aut(state, message.from_user.id, bot, first_actions, cursor, conn,)

    # reg_1: Если пользователь захотел зарегистрироваться
    @dp.callback_query_handler(text='visiting_reg', state=first_actions.waiting_command)
    async def appeal_1(callback: types.CallbackQuery, state: FSMContext):
        await first_actions.next()
        id_begin = \
            await callback.message.edit_text('🚀ЗАРЕГИСТРИРОВАТЬСЯ🚀')

        first_point = await bot.send_message(callback.from_user.id, "🔒➖*Р Е Г И С Т Р А Ц И Я*➖🔒",
                                             parse_mode=ParseMode.MARKDOWN, reply_markup=deregistration_kb)

        id_work = \
            await bot.send_message(callback.from_user.id,
                                   "🖱*1/4🖱*\n\n❔️|Нужно ли DAY PLAN обращаться к вам по-особому|❔",
                                   reply_markup=appeal_ques_kb, parse_mode=ParseMode.MARKDOWN)
        await state.update_data(id_begin=id_begin.message_id,
                                id_work=id_work.message_id,
                                first_point=first_point.message_id,
                                number_error=0)

        # добавляем сообщения в список для удалении при отключении бота
        plus_to_reg_messages(cursor, conn,
                             (callback.from_user.id, id_begin.message_id),
                             (callback.from_user.id, first_point.message_id),
                             (callback.from_user.id, id_work.message_id))

    # reg_2: если пользователь НЕ захотел особого обращения
    @dp.callback_query_handler(text='appeal_no', state=first_actions.begin_reg)
    async def appeal_no(callback: types.CallbackQuery):
        await process_reg.login.set()

        await callback.message.edit_text(f'🖱*2/4🖱*\n\n❕️|Сначала, '
                                         f'{callback.from_user.username}, придумайте себе логин|❕',
                                         parse_mode=ParseMode.MARKDOWN)

    # reg_3: если пользователь захотел особого обращения
    @dp.callback_query_handler(text='appeal_yes', state=first_actions.begin_reg)
    async def appeal_yes_ques_choice(callback: types.CallbackQuery, state: FSMContext):
        await process_reg.appeal.set()

        # список кнопок по всеми обращениями
        cursor.execute(f'SELECT * FROM all_appeals')
        all_appeals = cursor.fetchall()
        all_buttons_appeals = \
            [
                InlineKeyboardButton(one_appeal[0], callback_data=f'{one_appeal[0]}_choice_appeal')
                for one_appeal in all_appeals
            ]
        await state.update_data(users_buttons=all_buttons_appeals)

        # зацикливаем изменение КБ
        while True:
            async with state.proxy() as data:
                id_work = data.get('id_work')
                users_buttons = data.get('users_buttons')
                exist_appeal = data.get('appeal_user')

            if not exist_appeal:

                await bot.edit_message_text(
                    f'🖱*1/4🖱*\n\n❔️|Нужно ли DAY PLAN обращаться к вам по-особому|❔\n\n▫️И как ты, '
                    f'{callback.from_user.username}, хочешь, чтобы к тебе обращались?▫️'
                    f'\n\n📌В чат можно написать вариант своего обращения!',
                    chat_id=callback.from_user.id,
                    message_id=id_work,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup().row(*users_buttons[:3]))

                users_buttons.append(users_buttons.pop(0))
                await state.update_data(users_buttons=users_buttons)
                await asyncio.sleep(0.8)
            else:
                break

    # reg_4: при выборе обращения
    @dp.callback_query_handler(Text(endswith="_choice_appeal"), state=process_reg.appeal)
    async def appeal_yes_choice(callback: types.CallbackQuery, state: FSMContext):
        await process_reg.login.set()

        selected_appeal = callback.data[:-14]
        await state.update_data(appeal_user=selected_appeal)

        await bot.answer_callback_query(callback.id, selected_appeal)

        await callback.message.edit_text(f'🖱*2/4🖱*\n\n❕️|Сначала, '
                                         f'{callback.from_user.username}, придумайте себе логин|❕',
                                         parse_mode=ParseMode.MARKDOWN)

    # reg_5: если пользователь пишет своё обращение
    @dp.message_handler(state=process_reg.appeal, content_types='text')
    async def appeal_yes_personal_user_appeal(message: types.Message, state: FSMContext):
        await state.update_data(appeal_user=message.text)
        await message.delete()
        async with state.proxy() as data:
            id_work = data.get('id_work')

        await process_reg.login.set()
        await bot.edit_message_text(f'🖱*2/4🖱*\n\n❕️|Сначала, '
                                    f'{message.from_user.username}, придумайте себе логин|❕',
                                    chat_id=message.from_user.id,
                                    message_id=id_work,
                                    parse_mode=ParseMode.MARKDOWN)

    # reg_6: принимаем логин
    @dp.message_handler(state=process_reg.login, content_types='text')
    async def getting_login(message: types.Message, state: FSMContext):
        await message.delete()

        async with state.proxy() as data:
            id_work = data.get('id_work')

        # проверяем: нет ли такого логина уже
        cursor.execute("SELECT login FROM all_users WHERE login = ?", (message.text,))
        already_exist_login = cursor.fetchone()

        # такой логин уже есть!
        if already_exist_login:
            async with state.proxy() as data:
                number_error = data.get('number_error') + 1
            await bot.edit_message_text(f'🖱*2/4*🖱\n\n'
                                        f'❕️|Сначала, {message.from_user.username}, '
                                        f'придумайте себе логин|❕'
                                        f'\n\n▫️Логин "___{message.text}___" уже существует!▫️\n'
                                        f'❕️|*Попытка*: '
                                        f'{special_numbers_circle[number_error]} из *𝟱*|❕',
                                        chat_id=message.from_user.id,
                                        message_id=id_work,
                                        parse_mode=ParseMode.MARKDOWN)
            await state.update_data(number_error=number_error)

            # если попыток ввода логина >= 5
            if number_error >= 5: await cancel_reg_or_aut(state, message.from_user.id, bot, first_actions,
                                                          cursor, conn)
        else:
            await state.update_data(login_user=message.text)

            await process_reg.next()
            await bot.edit_message_text(f'🖱*3/4🖱*\n\n'
                                        f'❕️|А теперь, {message.from_user.username}, придумайте себе пароль|❕',
                                        chat_id=message.from_user.id,
                                        message_id=id_work,
                                        parse_mode=ParseMode.MARKDOWN)

    # reg_7: принимаем пароль
    @dp.message_handler(state=process_reg.password, content_types='text')
    async def reg_pass(message: types.Message, state: FSMContext):
        await message.delete()

        async with state.proxy() as data:
            id_work = data.get('id_work')
            login_user = data.get('login_user')

        # если с паролём всё хорошо
        if message.text != login_user and len(message.text) >= 8:
            await state.update_data(password_user=message.text)

            await process_reg.next()

            await all_right_asking(state, message.from_user.id, bot)

        else:

            # определяемся с текстом ошибки
            if message.text == login_user and len(message.text) < 8:
                text_error = 'быть длиннее семи символов и отличаться от логина'
            else:
                text_error = 'быть длиннее семи символов' if len(message.text) < 8 \
                    else 'отличаться от логина'

            async with state.proxy() as data:
                number_error = data.get('number_error') + 1
            await bot.edit_message_text(f'🖱*3/4*🖱\n\n'
                                        f'❕️|А теперь, {message.from_user.username}, придумайте себе пароль|❕\n\n'
                                        f'▫️Простите, пароль должен {text_error}▫️\n'
                                        f'❕️|*Попытка*: '
                                        f'{special_numbers_circle[number_error]} из *𝟱*|❕',
                                        chat_id=message.from_user.id,
                                        message_id=id_work,
                                        parse_mode=ParseMode.MARKDOWN)
            await state.update_data(number_error=number_error)

            # если попыток ввода логина >= 5
            if number_error >= 5: await cancel_reg_or_aut(state, message.from_user.id, bot, first_actions,
                                                          cursor, conn)

    # reg_8: секретный код
    @dp.callback_query_handler(text='back_to_ask_from_reform', state=process_reg.end_reg)
    @dp.callback_query_handler(text='ref_appeal_no', state=process_reg.end_reg)
    async def end_reg_reg(callback: types.CallbackQuery, state: FSMContext):
        # если пользователь отказался от обращения
        if callback.data == 'ref_appeal_no':
            await state.update_data(appeal_user=None)

        await all_right_asking(state, callback.from_user.id, bot)

    # reg_8: если пользователя устраивают его персональные данные
    @dp.callback_query_handler(text='control_inform_yes', state=process_reg.end_reg)
    async def all_reg_ok(callback: types.CallbackQuery, state: FSMContext):
        async with state.proxy() as data:
            id_begin = data.get('id_begin')
            id_work = data.get('id_work')
            first_point = data.get('first_point')

            # генерируем айди бота
            bot_id = str(uuid.uuid4()).replace('-', '')

            # добавляем данные в общую бд
            cursor.execute(
                'INSERT INTO all_users '
                '(appeal, login, password, date_reg, bot_id) '
                'VALUES (?, ?, ?, ?, ?)',
                (data.get("appeal_user"), data['login_user'], data['password_user'],
                 str(datetime.datetime.now()), bot_id,))
            conn.commit()

            # создаём папку на отдельного пользователя и его бд
            os.mkdir(f"users_bot/{bot_id}_log")
            for one_name in ('for_excel_dp', 'for_work_dp', 'for_sett_dp'):
                os.mkdir(f"users_bot/{bot_id}_log/{one_name}")

            one_user_conn = sqlite3.connect(f'users_bot/'
                                            f'{bot_id}_log/'
                                            f'user_db.db',
                                            check_same_thread=False)
            one_user_cursor = one_user_conn.cursor()

            one_user_cursor.execute(f'''CREATE TABLE 
                                        history_working 
                                        ([date] STRING,
                                         [week_day] STRING,
                                         [full_dp] INT,
                                         [doing_speed] STRING,
                                         [delta_work] STRING);''')

            one_user_cursor.execute(f'''CREATE TABLE 
                                        classification_of_events 
                                        ([code_element] STRING,
                                        [name_dp] STRING, 
                                        [description_dp] STRING, 
                                        [description_element] STRING,
                                        [time_of_doing] STRING DEFAULT (0), 
                                        [its_code_block] STRING);''')

            one_user_cursor.execute(f'''CREATE TABLE 
                                        classification_of_blocks 
                                        ([code_element] STRING,
                                        [block_emoji] STRING,
                                        [name_dp] STRING, 
                                        [description_element] STRING,
                                        [physics_cycle] STRING,
                                        [content] STRING);''')

            one_user_cursor.execute(f'''CREATE TABLE 
                                        hierarchy_day_plans 
                                        ([week_day_0] STRING,
                                        [week_day_1] STRING,
                                        [week_day_2] STRING,
                                        [week_day_3] STRING,
                                        [week_day_4] STRING,
                                        [week_day_5] STRING,
                                        [week_day_6] STRING);''')
            one_user_conn.commit()

        # эти сообщения-границы нужны, чтобы добавить/удалить reply keyboards
        two_point_reg_mes = await bot.send_message(callback.from_user.id,
                                                   "🔒➖*Р Е Г И С Т Р А Ц И Я*➖🔒",
                                                   parse_mode=ParseMode.MARKDOWN,
                                                   reply_markup=ReplyKeyboardRemove())
        await bot.answer_callback_query(callback.id, "✔️РЕГИСТРАЦИЯ ЗАВЕРШЕНА✖️")

        await bot.delete_message(chat_id=callback.from_user.id, message_id=first_point)
        await bot.delete_message(chat_id=callback.from_user.id, message_id=id_begin)
        await bot.delete_message(chat_id=callback.from_user.id, message_id=two_point_reg_mes.message_id)
        minus_to_reg_messages(cursor, conn, callback.from_user.id)

        await state.finish()
        await bot.edit_message_text('🔅*Вход в DAY PLAN*🔅\n\n'
                                    '`|-|-|-|`\n\n'
                                    '💠Войдите или зарегистрируйтесь, '
                                    'чтобы получить доступ к услугам DAY PLAN💠',
                                    chat_id=callback.from_user.id,
                                    message_id=id_work,
                                    parse_mode=ParseMode.MARKDOWN,
                                    reply_markup=visiting_system_kb)
        await first_actions.waiting_command.set()
        plus_to_reg_messages(cursor, conn, (callback.from_user.id, id_work))

    # reg_9: если пользователя НЕ устраивают его персональные данные
    @dp.callback_query_handler(text='control_inform_no', state=(process_reg.end_reg, reforming_reg_values.appeal,
                                                                reforming_reg_values.login,
                                                                reforming_reg_values.password))
    async def all_reg_no_ok(callback: types.CallbackQuery, state: FSMContext):
        await process_reg.end_reg.set()
        async with state.proxy() as data:
            id_work = data.get('id_work')

        await bot.edit_message_text(f'🖱*4/4*🖱\n\n'
                                    f'❔️|Вы согласны, {callback.from_user.id}, с указанными данными|❔\n\n'
                                    f'▫️И что же вас не устраивает?▫️',
                                    chat_id=callback.from_user.id, message_id=id_work,
                                    reply_markup=no_ok_reg_kb, parse_mode=ParseMode.MARKDOWN)

    # reg_10: проблемы с обращением
    @dp.callback_query_handler(text='reforming_appeal', state=process_reg.end_reg)
    async def ref_appeal(callback: types.CallbackQuery, state: FSMContext):
        async with state.proxy() as data:
            id_work = data.get('id_work')

        await bot.edit_message_text(
            "🖱*X/4🖱*\n\n"
            "❔️|Нужно ли DAY PLAN обращаться к вам по-особому|❔",
            chat_id=callback.from_user.id, message_id=id_work,
            reply_markup=appeal_board_reforming, parse_mode=ParseMode.MARKDOWN)

    # reg_11: если пользователю нужно обращение, и он это хочет изменить
    @dp.callback_query_handler(text='ref_appeal_yes', state=process_reg.end_reg)
    async def ref_appeal_yes(callback: types.CallbackQuery, state: FSMContext):
        await reforming_reg_values.appeal.set()
        async with state.proxy() as data:
            id_work = data.get('id_work')

        await bot.edit_message_text(
            f'🖱*X/🖱*\n\n❔️|Нужно ли DAY PLAN обращаться к вам по-особому|❔'
            f'\n\n▫️И как ты, {callback.from_user.username}, хочешь, чтобы к тебе обращались?▫️',
            chat_id=callback.from_user.id,
            message_id=id_work,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_to_reform_menu_kb)
        # кнопка НАЗАД

    # reg_12: проблемы с логином
    @dp.callback_query_handler(text='reforming_login', state=(process_reg.end_reg, reforming_reg_values.password))
    async def ref_login(callback: types.CallbackQuery, state: FSMContext):
        await reforming_reg_values.login.set()
        async with state.proxy() as data:
            id_work = data.get('id_work')

        await bot.edit_message_text(f'🖱*Y/4🖱*\n\n❕️|'
                                    f'{callback.from_user.username}, обновите свой логин|❕',
                                    chat_id=callback.from_user.id,
                                    message_id=id_work,
                                    parse_mode=ParseMode.MARKDOWN,
                                    reply_markup=back_to_reform_menu_kb)

    # reg_13: проблемы с паролем
    @dp.callback_query_handler(text='reforming_pass', state=(process_reg.end_reg, reforming_reg_values.login))
    async def ref_pass(callback: types.CallbackQuery, state: FSMContext):
        await reforming_reg_values.password.set()
        async with state.proxy() as data:
            id_work = data.get('id_work')

        await bot.edit_message_text(f'🖱*Z/4🖱*\n\n'
                                    f'❕️|{callback.from_user.username}, обновите свой пароль|❕',
                                    chat_id=callback.from_user.id,
                                    message_id=id_work,
                                    parse_mode=ParseMode.MARKDOWN,
                                    reply_markup=back_to_reform_menu_kb)

    # reg_14: ловим все присланные сообщения для реформ
    @dp.message_handler(state=[reforming_reg_values.appeal, reforming_reg_values.login, reforming_reg_values.password],
                        content_types='text')
    async def getting_all_messages_for_reforming(message: types.Message, state: FSMContext):
        await message.delete()
        this_state = (await state.get_state()).split(':')[1]

        if this_state == 'appeal':
            await state.update_data(appeal_user=message.text,
                                    ready_reform=1)

        elif this_state == 'login':
            # проверяем: нет ли такого логина уже
            cursor.execute("SELECT login FROM all_users WHERE login = ?", (message.text,))
            already_exist_login = cursor.fetchone()
            async with state.proxy() as data:
                password_user = data.get('password_user')

            # такой логин уже есть!
            if already_exist_login or message.text == password_user:
                async with state.proxy() as data:
                    id_work = data.get('id_work')
                    number_error = data.get('number_error') + 1

                # определяемся с текстом ошибки
                if message.text == password_user and already_exist_login:
                    text_error = f'"___{message.text}___" уже существует и не отличается от пароля'
                else:
                    text_error = f'"___{message.text}___" уже существует' if already_exist_login \
                        else 'должен отличаться от пароля'

                reforming_kb = InlineKeyboardMarkup()
                # добавляем возможность сразу изменить, если нужно
                if message.text == password_user:
                    reforming_kb.row(back_to_reform_menu_but,
                                     InlineKeyboardButton('🔙️ИЗМЕНИТЬ ПАРОЛЬ️', callback_data='reforming_pass'))
                else:
                    reforming_kb = back_to_reform_menu_kb

                await bot.edit_message_text(f'🖱*Y/4*🖱\n\n'
                                            f'❕️|{message.from_user.username}, '
                                            f'обновите свой логин|❕'
                                            f'\n\n▫️Логин {text_error}▫️\n'
                                            f'❕️|*Попытка*: '
                                            f'{special_numbers_circle[number_error]} из *𝟱*|❕',
                                            chat_id=message.from_user.id,
                                            message_id=id_work,
                                            parse_mode=ParseMode.MARKDOWN,
                                            reply_markup=reforming_kb)
                await state.update_data(number_error=number_error)

                # если попыток ввода логина >= 5
                if number_error >= 5: await cancel_reg_or_aut(state, message.from_user.id, bot, first_actions,
                                                              cursor, conn)
            else:
                await state.update_data(login_user=message.text,
                                        ready_reform=1)

        else:
            async with state.proxy() as data:
                login_user = data.get('login_user')

            if message.text == login_user or len(message.text) < 8:
                async with state.proxy() as data:
                    id_work = data.get('id_work')
                    number_error = data.get('number_error') + 1

                # определяемся с текстом ошибки
                if message.text == login_user and len(message.text) < 8:
                    text_error = 'быть длиннее семи символов и отличаться от логина'
                else:
                    text_error = 'быть длиннее семи символов' if len(message.text) < 8 \
                        else 'отличаться от логина'

                reforming_kb = InlineKeyboardMarkup()
                # добавляем возможность сразу изменить, если нужно
                if message.text == login_user:
                    reforming_kb.row(back_to_reform_menu_but,
                                     InlineKeyboardButton('🔙️ИЗМЕНИТЬ ЛОГИН', callback_data='reforming_login'))
                else:
                    reforming_kb = back_to_reform_menu_kb

                await bot.edit_message_text(f'🖱*Z/4*🖱\n\n'
                                            f'❕️|{message.from_user.username}, обновите свой пароль|❕\n\n'
                                            f'▫️Простите, пароль должен {text_error}▫️\n'
                                            f'❕️|*Попытка*: '
                                            f'{special_numbers_circle[number_error]} из *𝟱*|❕',
                                            chat_id=message.from_user.id,
                                            message_id=id_work,
                                            parse_mode=ParseMode.MARKDOWN,
                                            reply_markup=reforming_kb)
                await state.update_data(number_error=number_error)

                # если попыток ввода логина >= 5
                if number_error >= 5: await cancel_reg_or_aut(state, message.from_user.id, bot, first_actions,
                                                              cursor, conn,)
            else:
                await state.update_data(password_user=message.text,
                                        ready_reform=1)

        # если не поймано проблем
        async with state.proxy() as data:
            ready_reform = data.get('ready_reform')
        if ready_reform:
            await process_reg.end_reg.set()
            await all_right_asking(state, message.from_user.id, bot)
            await state.update_data(ready_reform=None)

    # reg_15: удаляет любые бесполезные сообщения, присланные пользователем
    @dp.message_handler(state=(first_actions.begin_reg,
                               process_reg.appeal, process_reg.login, process_reg.password, process_reg.end_reg,
                               reforming_reg_values.appeal, reforming_reg_values.login, reforming_reg_values.password),
                        content_types=all_content_types)
    async def delete_endless_v2(message: types.Message):
        await message.delete()

    # aut_0: отмена авторизации
    @dp.message_handler(text=["🔴ОТМЕНА АВТОРИЗАЦИИ🔴"], state=(process_aut.login, process_aut.password))
    async def stop_or_restart_aut(message: types.Message, state: FSMContext):
        await message.delete()
        await cancel_reg_or_aut(state, message.from_user.id, bot, first_actions,
                                cursor, conn,
                                action_reg=False)

    # aut_1: принимаем заход
    @dp.callback_query_handler(text='visiting_aut', state=first_actions.waiting_command)
    async def process_authorization(callback: types.CallbackQuery, state: FSMContext):
        await process_aut.login.set()
        id_begin = \
            await callback.message.edit_text('✈️ВОЙТИ✈️')

        first_point = await bot.send_message(callback.from_user.id, "🔑➖*А В Т О Р И З А Ц И Я*➖🔑",
                                             parse_mode=ParseMode.MARKDOWN, reply_markup=deauthorization_kb)

        id_work = \
            await bot.send_message(callback.from_user.id,
                                   "♦️*1/2♦️*\n\n"
                                   "❗|Введите свой логин|❗",
                                   parse_mode=ParseMode.MARKDOWN)
        await state.update_data(id_begin=id_begin.message_id,
                                id_work=id_work.message_id,
                                first_point=first_point.message_id,
                                number_error=0,
                                last_callback_id=callback.id)

        # добавляем сообщения в список для удалении при отключении бота
        plus_to_reg_messages(cursor, conn,
                             (callback.from_user.id, id_begin.message_id),
                             (callback.from_user.id, first_point.message_id),
                             (callback.from_user.id, id_work.message_id))

    # aut_2: ловим логин
    @dp.message_handler(state=process_aut.login, content_types='text')
    async def aut_log(message: types.Message, state: FSMContext):
        await message.delete()
        async with state.proxy() as data:
            id_work = data.get('id_work')

        # проверяем: есть ли такой логин
        cursor.execute("SELECT login FROM all_users WHERE login = ?", (message.text,))
        already_exist_login = cursor.fetchone()

        if not already_exist_login:
            async with state.proxy() as data:
                number_error = data.get('number_error') + 1

            await bot.edit_message_text(f'♦️*1/2♦️*\n\n'
                                        f'❗|Введите свой логин|❗\n\n'
                                        f'🔻*️Логин* "___{message.text}___" *не существует*🔻️\n'
                                        f'❗|*Попытка*: '
                                        f'{special_numbers_circle[number_error]} из *𝟱*|❗',
                                        chat_id=message.from_user.id,
                                        message_id=id_work,
                                        parse_mode=ParseMode.MARKDOWN)
            await state.update_data(number_error=number_error)

            # если попыток ввода логина >= 5
            if number_error >= 5: await cancel_reg_or_aut(state, message.from_user.id, bot, first_actions,
                                                          cursor, conn,
                                                          action_reg=False)

        else:
            await state.update_data(login_user=message.text)
            await process_aut.next()

            await bot.edit_message_text('♦️*2/2♦️*\n\n'
                                        '❗|Введите свой пароль|❗',
                                        chat_id=message.from_user.id,
                                        message_id=id_work,
                                        parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=None)

    # aut_3: проверяем пароль
    @dp.message_handler(state=process_aut.password, content_types='text')
    async def aut_pass(message: types.Message, state: FSMContext):
        await message.delete()
        async with state.proxy() as data:
            id_work = data.get('id_work')
            login_user = data.get('login_user')

        # смотрим: подходит ли пароль
        cursor.execute('SELECT password FROM all_users WHERE login=?', (login_user,))
        is_need_password = cursor.fetchone()[0]

        if str(is_need_password) != message.text:
            async with state.proxy() as data:
                number_error = data.get('number_error') + 1

            await bot.edit_message_text(f'♦️*2/2♦️*\n\n'
                                        f'❗|Введите свой пароль|❗\n\n'
                                        f'🔻"___{message.text}___" *- неверный пароль*🔻️️\n'
                                        f'❗|*Попытка*: '
                                        f'{special_numbers_circle[number_error]} из *𝟱*|❗',
                                        chat_id=message.from_user.id,
                                        message_id=id_work,
                                        parse_mode=ParseMode.MARKDOWN)
            await state.update_data(number_error=number_error)

            # если попыток ввода логина >= 5
            if number_error >= 5: await cancel_reg_or_aut(state, message.from_user.id, bot, first_actions,
                                                          cursor, conn,
                                                          action_reg=False)

        else:
            async with state.proxy() as data:
                last_callback_id = data.get('last_callback_id')
                first_point = data.get('first_point')
                id_begin = data.get('id_begin')
                login_user = data.get('login_user')

            # эти сообщения-границы нужны, чтобы добавить/удалить reply keyboards
            two_point_aut_mes = await bot.send_message(message.from_user.id,
                                                       "🔑➖*А В Т О Р И З А Ц И Я*➖🔑",
                                                       parse_mode=ParseMode.MARKDOWN,
                                                       reply_markup=ReplyKeyboardRemove())
            try:
                await bot.answer_callback_query(last_callback_id, "✔️ВХОД ОСУЩЕСТВЛЁН✖️")
            except InvalidQueryID:
                pass

            await bot.delete_message(chat_id=message.from_user.id, message_id=first_point)
            await bot.delete_message(chat_id=message.from_user.id, message_id=id_begin)
            await bot.delete_message(chat_id=message.from_user.id, message_id=two_point_aut_mes.message_id)
            await bot.delete_message(chat_id=message.from_user.id, message_id=id_work)
            minus_to_reg_messages(cursor, conn, message.from_user.id)
            await state.finish()

            await main_menu.main_menu.set()
            new_work_id = await bot.send_message(chat_id=message.from_user.id, text=text_main_menu,
                                                 parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_kb)

            # обновляем айди
            cursor.execute('UPDATE all_sessions SET user_id = ? WHERE user_id = ?',
                           (None, message.from_user.id,))

            # проверяем: есть ли сессия с данным логином
            cursor.execute("SELECT user_id, work_mes_id, active_session FROM all_sessions WHERE login = ?",
                           (login_user,))
            values_already_exist_login = cursor.fetchone()

            # проверяем: есть ли сессия с данным логином, если да - обновляем данные
            # иначе - добавляем в таблицу
            if values_already_exist_login:

                # active_session = 1: кто-то другой на аккаунте
                if values_already_exist_login[2]:
                    # делаем у прошлого пользователя аккаунта state на регистрацию
                    one_user_state = dp.current_state(chat=values_already_exist_login[0],
                                                      user=values_already_exist_login[0])
                    await one_user_state.set_state(first_actions.waiting_command)

                    # удаляем у прошлого пользователя аккаунта рабочее сообщение
                    try:
                        await bot.delete_message(chat_id=values_already_exist_login[0],
                                                 message_id=values_already_exist_login[1])
                    except MessageToDeleteNotFound:
                        pass

                    # отправляем сообщение входа
                    new_mes = await bot.send_message(chat_id=values_already_exist_login[0],
                                           text='🔅*Вход в DAY PLAN*🔅\n\n'
                                                '`|-|-|-|`\n\n'
                                                '💠Войдите или зарегистрируйтесь, '
                                                'чтобы получить доступ к услугам DAY PLAN💠',
                                           parse_mode=ParseMode.MARKDOWN,
                                           reply_markup=visiting_system_kb)
                    plus_to_reg_messages(cursor, conn,
                                         (values_already_exist_login[0], new_mes.message_id))

                cursor.execute("UPDATE all_sessions SET user_id = ?, state_user = ?, "
                               "work_mes_id = ?, active_session = ? WHERE login = ?",
                               (message.from_user.id, 'main_menu', new_work_id.message_id, 1, login_user,))

                # проверяем: есть ли начатый ДП у данного логина
                if cursor.execute('SELECT * FROM all_cashDP WHERE login = ?', (login_user,)).fetchone():
                    # обновляем user_id, если есть
                    cursor.execute('UPDATE all_cashDP SET user_id = ? WHERE login = ?',
                                   (message.from_user.id, login_user,))

            else:
                bot_id = cursor.execute('SELECT bot_id FROM all_users WHERE login = ?', (login_user,)).fetchone()[0]
                cursor.execute('INSERT INTO all_sessions (login, user_id, state_user, '
                               'work_mes_id, data_user, active_session) '
                               'VALUES (?, ?, ?, ?, ?, ?)',
                               (login_user, message.from_user.id, 'main_menu',
                                new_work_id.message_id,
                                str({'login_user': login_user, 'bot_id': bot_id,
                                     'data_with_media_statistics': [{}, '#']}),
                                1,))

            conn.commit()

    # aut_4: удаляет любые бесполезные сообщения, присланные пользователем
    @dp.message_handler(state=(process_aut.login, process_aut.password), content_types=all_content_types)
    async def delete_endless_v3(message: types.Message):
        await message.delete()
