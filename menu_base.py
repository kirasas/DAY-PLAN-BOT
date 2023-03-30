import sqlite3
import asyncio
#
from aiogram import Bot
from aiogram.utils import executor
from aiogram.dispatcher import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ParseMode, CallbackQuery, Message, \
    KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup
#
from utilis.apies import API_1, name_main_db
from utilis.consts_common import all_content_types, main_menu_kb, text_main_menu, \
    visiting_system_kb
from utilis.main_common import check_users_states, save_last_state_user, \
    update_main_menu, check_user_time_of_day_plans, \
    plus_to_reg_messages, delete_messages_reg
#
from sides_bot.reg_aut.reg_aut_base import reg_and_aut
from sides_bot.dayplan.dayplan_base import process_doing_dp
from sides_bot.profile.profile_base import profile_user
from sides_bot.setup.setup_base import settings_user


# бот
bot = Bot(token=API_1)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# бд
conn = sqlite3.connect(f'{name_main_db}.db', check_same_thread=False)
cursor = conn.cursor()


# state_0: стейты reg | aut
class first_actions(StatesGroup):
    waiting_command = State()
    begin_reg = State()


class process_reg(StatesGroup):
    appeal = State()
    login = State()
    password = State()
    end_reg = State()


class reforming_reg_values(StatesGroup):
    appeal = State()
    login = State()
    password = State()


class process_aut(StatesGroup):
    login = State()
    password = State()


# state_1: стейты для main_menu
class main_menu(StatesGroup):
    main_menu = State()
    profile_user = State()

    work_dp = State()
    remaking_dp = State()

    user_sett = State()
    compound_remake_sett = State()

    new_event_name = State()
    new_event_describe_dp = State()
    new_event_describe_el = State()
    edit_parameters_event = State()

    new_block_name = State()
    new_block_describe_el = State()
    new_block_emoji = State()
    edit_parameters_block = State()

# state_end: activate last users states
code_states_dict = \
    {
        'main_menu': main_menu.main_menu,
        'profile_user': main_menu.profile_user,
        'work_dp': main_menu.work_dp,
        'remaking_dp': main_menu.remaking_dp,

        'user_sett': main_menu.user_sett,
        'compound_remake_sett': main_menu.compound_remake_sett,

        'new_event_name': main_menu.new_event_name,
        'new_event_describe_dp': main_menu.new_event_describe_dp,
        'new_event_describe_el': main_menu.new_event_describe_el,
        'edit_parameters_event': main_menu.edit_parameters_event,

        'new_block_name': main_menu.new_block_name,
        'new_block_describe_el': main_menu.new_block_describe_el,
        'new_block_emoji': main_menu.new_block_emoji,
        'edit_parameters_block': main_menu.edit_parameters_block
    }

loop = asyncio.get_event_loop()
loop.run_until_complete(check_users_states(code_states_dict, dp, cursor))


# удаляем бесполезные сообщения регистрации, которые остались
loop.run_until_complete(delete_messages_reg(bot, cursor, conn))


# 0_menu: reg&aut
reg_and_aut(dp, bot, cursor, conn,
            first_actions, process_reg, reforming_reg_values, process_aut,
            main_menu, main_menu_kb, text_main_menu)


# 1_menu: назад к меню
@dp.callback_query_handler(text='back_main_menu',
                           state=(main_menu.main_menu, main_menu.profile_user,
                                  main_menu.work_dp, main_menu.user_sett))
async def back_to_main_menu(callback: CallbackQuery):
    await main_menu.main_menu.set()
    save_last_state_user(callback.from_user.id, 'main_menu', cursor, conn)
    await update_main_menu(callback.from_user.id, bot,
                           cursor, conn)


# 2_menu: DAY PLAN на сегодня
process_doing_dp(dp, bot, cursor, conn, main_menu)


# 3_menu: профиль пользователя
profile_user(dp, bot, cursor, conn,
             main_menu, update_main_menu,
             first_actions)

# 4_menu: настройки пользователя
settings_user(dp, bot, cursor, conn,
              main_menu, update_main_menu)

# LAST_menu: удаление сообщений при main_menu
@dp.message_handler(state=main_menu.main_menu, content_types=all_content_types)
async def delete_endless_in_main_menu(message: Message):
    await message.delete()

    await update_main_menu(message.from_user.id, bot,
                           cursor, conn)


# START_DP: запрос на заход в систему
@dp.message_handler(content_types=all_content_types)
async def starting_work_dp(message: Message):
    await message.delete()
    await first_actions.waiting_command.set()
    one_reg_mes = await message.answer(text='🔅*Вход в DAY PLAN*🔅\n\n'
                              '`|-|-|-|`\n\n'
                              '💠Войдите или зарегистрируйтесь, '
                              'чтобы получить доступ к услугам DAY PLAN💠',
                         parse_mode=ParseMode.MARKDOWN, reply_markup=visiting_system_kb)
    plus_to_reg_messages(cursor, conn,
                         (message.from_user.id, one_reg_mes.message_id))


if __name__ == '__main__':
    # CHECK EXIT TO DP
    check_user_time_of_day_plans(cursor)
    executor.start_polling(dp)
