import datetime
import sqlite3
#
from aiogram.utils.markdown import quote_html
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, \
    Message, ParseMode
#
from utilis.consts_common import all_content_types, back_mes, \
    dict_special_numbers_circle, visiting_system_kb, dict_with_bold_nums
from utilis.main_common import get_main_id_message, save_last_state_user, \
    yes_or_no_kb, to_right_russian_word_day, big_replacing, existing_work_message, big_replacing


# CONST
profile_kb = InlineKeyboardMarkup().add(
    InlineKeyboardButton(back_mes, callback_data='back_main_menu'),
    InlineKeyboardButton('❌ВЫЙТИ❌', callback_data='sign_out'))


def profile_user(dp, bot, cursor, conn,
                 main_menu, update_main_menu,
                 first_actions):

    def getting_profile_user(user_id, tg_username):
        # находим логин в данной сессии по айди
        cursor.execute('SELECT login FROM all_sessions WHERE user_id = ?', (user_id,))
        login_user = cursor.fetchone()[0]

        # обращение, дата регистрации
        cursor.execute('SELECT appeal, date_reg, bot_id FROM all_users WHERE login = ?', (login_user,))
        appeal_user, date_reg_user, bot_id = cursor.fetchone()
        if appeal_user is None:
            appeal_user = f'{tg_username}'

        # дельта дат
        date_reg_datetime = datetime.datetime.strptime(date_reg_user, '%Y-%m-%d %H:%M:%S.%f')
        delta_days_user = abs((datetime.datetime.now() - date_reg_datetime).days)
        delta_in_emoji = big_replacing(delta_days_user, your_dict=dict_special_numbers_circle)

        # кол-во успешных ДП
        one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                        check_same_thread=False)
        one_user_cursor = one_user_conn.cursor()

        one_user_cursor.execute('SELECT full_dp FROM history_working WHERE full_dp = ?', (1,))
        done_dp = one_user_cursor.fetchall()
        number_successful_dp = big_replacing(len(done_dp) if done_dp else 0, your_dict=dict_with_bold_nums)

        return '<b>Ваш профиль в @day_plans_getting_bot:</b>' \
               '\n➖➖➖➖➖➖➖➖➖➖➖➖➖\n' \
               f'🔊<b>Вы мой -</b> <i>{quote_html(appeal_user)}</i>\n' \
               f'👤<b>Ваш логин:</b> <u>{quote_html(login_user)}</u>\n' \
               f'⭐<b>Успешных DAY PLANS:</b> <code>{number_successful_dp}</code>' \
               f'\n➖➖➖➖➖➖➖➖➖➖➖➖➖\n' \
               f'♥️<b>Вы с нами уже: {delta_in_emoji} ' \
               f'{to_right_russian_word_day(delta_days_user)}</b>♥️'

    @dp.message_handler(text='👤PROFILE👤', state=main_menu.main_menu)
    async def profile_mes(message: Message):
        # обновляем state
        save_last_state_user(message.from_user.id, 'profile_user', cursor, conn)
        await main_menu.profile_user.set()

        await message.delete()
        await update_main_menu(message.from_user.id, bot, cursor, conn,
                               text_for=getting_profile_user(message.from_user.id,
                                                             message.from_user.username),
                               markup_for=profile_kb, parse_for=ParseMode.HTML,
                               need_state='profile_user')

    @dp.callback_query_handler(text='to_back_profile', state=main_menu.profile_user)
    async def profile_call(callback: CallbackQuery):
        await bot.edit_message_text(text=getting_profile_user(callback.from_user.id,
                                                              callback.from_user.username),
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    parse_mode=ParseMode.HTML,
                                    reply_markup=profile_kb)

    @dp.callback_query_handler(text='sign_out', state=main_menu.profile_user)
    async def exit_from_account_ask(callback: CallbackQuery):
        await bot.edit_message_text('*👤PROFILE👤*\n\n'
                                    '❓ *Вы уверены, что хотите выйти из своего аккаунта DAY PLAN* ❓',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    parse_mode=ParseMode.MARKDOWN,
                                    reply_markup=yes_or_no_kb('yes_sign_out',
                                                              'to_back_profile'))

    @dp.callback_query_handler(text='yes_sign_out', state=main_menu.profile_user)
    async def yes_sign_out(callback: CallbackQuery, state: FSMContext):
        await state.finish()
        await bot.answer_callback_query(callback.id, '✔️ВЫХОД ОСУЩЕСТВЛЁН✖')

        await first_actions.waiting_command.set()
        await bot.edit_message_text('🔅*Вход в DAY PLAN*🔅\n\n'
                                    '`|-|-|-|`\n\n'
                                    '💠Войдите или зарегистрируйтесь, '
                                    'чтобы получить доступ к услугам DAY PLAN💠',
                                    chat_id=callback.from_user.id,
                                    message_id=get_main_id_message(callback.from_user.id, cursor),
                                    parse_mode=ParseMode.MARKDOWN,
                                    reply_markup=visiting_system_kb)
        cursor.execute('UPDATE all_sessions SET state_user = ?, active_session = ? WHERE user_id = ?',
                       (None, 0, callback.from_user.id,))
        conn.commit()

    @dp.message_handler(state=main_menu.profile_user, content_types=all_content_types)
    async def delete_endless_in_profile(message: Message):
        await message.delete()

        await existing_work_message(message.from_user.id, bot,
                                    cursor, conn,
                                    main_menu)
