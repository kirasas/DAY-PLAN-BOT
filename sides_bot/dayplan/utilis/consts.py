import datetime
#
from utilis.consts_common import back_mes
from utilis.main_common import get_datetime_from_str
#
from sides_bot.dayplan.utilis.main import get_user_time_now, values_for_opening_dp

# BUTTS | KB
first_open_but = dict(text='❕ОТКРЫТЬ❕', callback_data="1_xDP")
def continue_work_dp_but(call): return dict(text='⏩ПРОДОЛЖИТЬ⏩', callback_data=f'{call}')
begin_doing_event_but = dict(text='✖️START✖️', callback_data='in_doing_event')
eclipse_el_but = dict(text='🌑', callback_data='eclipse_el')


def get_way_bl_but(text_button):
    return dict(text=f'{text_button}', callback_data='way_bl')


def get_sett_kb(last_page):
    return \
        {
            'inline_keyboard':
            [
                [dict(text='⛔ПРИОСТАНОВИТЬ DAY PLAN⛔', callback_data='stop_dp')],
                [dict(text='📈ДИНАМИКА РАБОТЫ📉', callback_data='dynamic_work'),
                 dict(text='📁ПОРЯДОК ПЛАНА📂', callback_data='coordinate_elements')],
                [dict(text=back_mes, callback_data=f'{last_page}_xDP')]
            ]
        }

active_kb = {'inline_keyboard': [[dict(text='️❇️RESTART DAYPLAN RIGHT NOW❇️', callback_data='active_DP')],
                                  [dict(text='▫ M A I N | M E N U ▫️', callback_data='back_main_menu')]]}

dynamic_kb = \
    {'inline_keyboard':
         [[dict(text='⚪БЛОКИ⚪️', callback_data='circle_graph'),
           dict(text='🖋ЭВЕНТЫ✒️', callback_data='area_graph')],
          [dict(text=back_mes, callback_data='settings_DP')]]}


def back_to_relocating_but(last_page_set_2):
    return dict(text='➡️', callback_data=f'{last_page_set_2}_sett_dp_2')


async def get_end_dp_kb(user_id, username, bot):
    inf_for_begin_dp = \
        await values_for_opening_dp(user_id, username, bot)
    work_last_week_day = datetime.datetime.weekday(get_datetime_from_str(inf_for_begin_dp[3]))

    end_dp_kb = \
        {'inline_keyboard':
             [[dict(text='⚪БЛОКИ⚪️', callback_data='circle_graph_with_end'),
               dict(text='🖋ЭВЕНТЫ✒️', callback_data='area_graph_with_end')],
              [dict(text=back_mes, callback_data='back_main_menu')]]}

    # вставляем кнопку в начало КБ при изменении дня
    user_time_now = get_user_time_now(user_id=user_id)
    if work_last_week_day != datetime.datetime.weekday(user_time_now):
        end_dp_kb['inline_keyboard'].insert(0, [dict(text='🔚NEXT DAY PLAN🔜', callback_data='get_next_dp')])

    return end_dp_kb


# STOP_DP
dp_stop_str_1 = '\n╔══╗╔══╗╔═╦╗╔═╗╔╗─╔══╗╔═╦╗\n' \
                '╚╗╗║║╔╗║╚╗║║║╬║║║─║╔╗║║║║║\n' \
                '╔╩╝║║╠╣║╔╩╗║║╔╝║╚╗║╠╣║║║║║\n' \
                '╚══╝╚╝╚╝╚══╝╚╝─╚═╝╚╝╚╝╚╩═╝\n\n'
dp_stop_str_2 = '  ╔══╗╔══╗╔═╗╔═╗╔═╗╔═╗╔══╗\n' \
                '  ║══╣╚╗╔╝║║║║╬║║╬║║╦╝╚╗╗║\n' \
                '  ╠══║─║║─║║║║╔╝║╔╝║╩╗╔╩╝║\n' \
                '  ╚══╝─╚╝─╚═╝╚╝─╚╝─╚═╝╚══╝'
dp_stop_tuple = (dp_stop_str_1, dp_stop_str_2)
