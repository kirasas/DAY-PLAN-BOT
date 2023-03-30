from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, \
    InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import ParseMode
#
from utilis.consts_common import visiting_system_kb


# BUTTONS&KB
deregistration_kb = \
    ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(
        KeyboardButton("⭕ОТМЕНА РЕГИСТРАЦИИ⭕"))
appeal_ques_kb = InlineKeyboardMarkup().row(
    InlineKeyboardButton("✔️ДА✔️", callback_data="appeal_yes"),
    InlineKeyboardButton("✖️НЕТ✖️", callback_data="appeal_no"))
secret_code_save_kb = InlineKeyboardMarkup().add(
    InlineKeyboardButton("✔️СЕКРЕТНЫЙ КОД СОХРАНЁН✔️", callback_data='yes_save_secret_code'))
is_all_right_reg_kb = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton("✖️️НЕТ✖️️", callback_data='control_inform_no'),
    InlineKeyboardButton("✔️ДА✔️", callback_data='control_inform_yes'))
no_ok_reg_kb = InlineKeyboardMarkup().add(
    InlineKeyboardButton("🔙ОБРАЩЕНИЕ", callback_data='reforming_appeal')).row(
    InlineKeyboardButton("🔙️️ЛОГИН", callback_data='reforming_login'),
    InlineKeyboardButton("🔙️ПАРОЛЬ️", callback_data='reforming_pass')).add(
    InlineKeyboardButton("🏴ПРОЙТИ РЕГИСТРАЦИЮ ЗАНОВО🏴", callback_data='restart_reg')).add(
    InlineKeyboardButton("НАЗАД↩️", callback_data='back_to_ask_from_reform'))
back_to_reform_menu_but = InlineKeyboardButton('НАЗАД↩️', callback_data='control_inform_no')
appeal_board_reforming = InlineKeyboardMarkup().row(
    InlineKeyboardButton("✔️ДА✔️", callback_data="ref_appeal_yes"),
    InlineKeyboardButton("✖️НЕТ✖️", callback_data="ref_appeal_no")).add(
    back_to_reform_menu_but)
back_to_reform_menu_kb = InlineKeyboardMarkup().add(back_to_reform_menu_but)
deauthorization_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(
    KeyboardButton("🔴ОТМЕНА АВТОРИЗАЦИИ🔴"))
