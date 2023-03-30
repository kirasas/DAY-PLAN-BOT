import ast
import string
import sqlite3
import statistics
import matplotlib.pyplot as plt
from num2words import num2words
from collections import OrderedDict
from emoji import emojize, demojize
#
from utilis.consts_common import back_mes_but, nums_and_emoji, dict_with_small_numbers, emoji_work_dp_list, \
    short_name_week_days, dict_with_bold_nums, bad_symbols_for_emoji_name
from utilis.main_common import big_replacing, get_common_data, save_common_data, \
    get_button, row_buttons, add_buttons
#
from sides_bot.dayplan.utilis.consts import back_to_relocating_but
from sides_bot.dayplan.utilis.main import in_roman_number, \
    get_pages_with_this_elem, get_dict_with_index_emoji, \
    get_first_work_index
from sides_bot.dayplan.utilis.dp_usual import values_for_usual_dp
from sides_bot.dayplan.utilis.block import get_indexes_current_part_block, \
    get_time_block, minus_all_freeze_block
#
from sides_bot.setup.utilis.consts import week_colors


# GRAPHS
def create_full_week_days_graph(bot_id, save_path, get_full_days=True):
    first_fig, ax_first = plt.subplots()

    # подключаемся к бд пользователя
    one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db', check_same_thread=False)
    one_user_cursor = one_user_conn.cursor()

    # находим кол-во full days | not full days по дням недели
    data_history_work = \
        one_user_cursor.execute('SELECT week_day, full_dp FROM history_working').fetchall()
    everyone_week_day_sizes = \
        [sum([one_work_day[1] if get_full_days else not one_work_day[1]
              for one_work_day in data_history_work if one_work_day[0] == index_week])
         for index_week, _ in enumerate(short_name_week_days)]
    condition_not_null_sum = 1 if sum(everyone_week_day_sizes) else 0

    # определяем размеры и их процентное соотношение
    division_sum_sizes = sum(everyone_week_day_sizes) if condition_not_null_sum else 1
    percent_sizes = [one_num * 100 / division_sum_sizes for one_num in everyone_week_day_sizes]

    # создаём ярлыки с процентами + цвета
    labels = [f'{day_week} | {percent_sizes[index_week]:.1f}%'
              for index_week, day_week in enumerate(short_name_week_days)]

    title_graph = f'{"" if get_full_days else "NOT "}FULL DAYS'
    ax_first.set_title(f'{title_graph} OF DAY PLANS',
                       fontfamily='fantasy',
                       size=25,
                       color='black')

    one_cadre = \
        ax_first.pie(everyone_week_day_sizes if condition_not_null_sum else [1],
                     radius=1,
                     wedgeprops=dict(width=0.2, edgecolor='black'),
                     colors=week_colors if condition_not_null_sum else 'white')

    # находим wedges и приципляем к ним имена
    ax_first.legend(one_cadre[0], labels if condition_not_null_sum
    else [f'{title_graph} | 0.0%'],
                    title='DAYS OF THE WEEK',
                    loc="right",
                    edgecolor='black',
                    bbox_to_anchor=(0, 0, 0.03, 1.6),
                    fontsize=6)

    first_fig.savefig(f'{save_path}/graph_sett.jpg')


def create_average_work_time_graph(bot_id, save_path):
    first_fig, ax_first = plt.subplots()

    # подключаемся к бд пользователя
    one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db', check_same_thread=False)
    one_user_cursor = one_user_conn.cursor()

    # находим среднее время выполнение каждого дня
    data_history_work = \
        one_user_cursor.execute('SELECT week_day, delta_work FROM history_working').fetchall()
    if data_history_work:
        everyone_week_day_sizes = \
            [statistics.mean([one_work_day[1] if one_work_day[0] == index_week else 0
                              for one_work_day in data_history_work]) / 60
             for index_week, _ in enumerate(short_name_week_days)]
    else:
        everyone_week_day_sizes = [0] * 7

    # put title
    ax_first.set_title(f'AVERAGE DONE TIME OF DAY PLANS',
                       fontfamily='fantasy',
                       size=25,
                       color='black')

    # для x и y осей подписи
    ax_first.set_xlabel('DAYS OF THE WEEK',
                        fontfamily='monospace', size=16, fontstyle='normal')
    ax_first.set_ylabel('MINS',
                        fontfamily='monospace', size=16, fontstyle='normal')

    # устанавливаем главную сетку
    ax_first.grid(which='major',
                  color='grey',
                  linewidth=1)

    # устанавливаем побочную сетку
    ax_first.grid(which='minor',
                  color='grey',
                  linestyle=':')

    ax_first.bar(short_name_week_days, everyone_week_day_sizes,
                 linewidth=5,
                 edgecolor='black',
                 color=week_colors)

    first_fig.savefig(f'{save_path}/graph_sett.jpg')


"""FIRST WINDOW DP REMAKING"""


def text_for_remake_dp_first(remake_huge_list):
    message_a = ''
    pages_with_texts = {}
    only_pages = []
    n_page = 0

    # уникальные эмоджи с сохранением порядка, при том не в ('⭐', '❄️')
    full_emoji = OrderedDict.fromkeys((one_elem[1]
                                       for one_elem in remake_huge_list
                                       if one_elem[1] not in ('⭐', '❄️')))

    for one_ind, one_emoji in enumerate(full_emoji):
        only_name_emoji = demojize(one_emoji)[1:-1]

        # учитываем возможность появления в названии эмоджи плохих символов,
        # из-за чего ТГ не будет выделять название как команду
        exist_bad_symbol = True if sum(1 for el in only_name_emoji if el in bad_symbols_for_emoji_name) \
            else False

        # добавляем сам блок
        parse_html = 'u' if not exist_bad_symbol else 'code'
        message_a += f'\n〰{one_emoji}│<{parse_html}><b>/{only_name_emoji}BLX</b></{parse_html}>\n'

        parts_block = get_indexes_current_part_block(
            one_emoji, get_dict_with_index_emoji(remake_huge_list),
            remake_huge_list, get_full_indexes_parts=True)
        # если нет частей у блока
        if len(parts_block) == 1:

            # формируем строки с отдельными эвентами, у которых эмоджи == one_emoji
            message_a += ''.join([
                # номер эвента
                f'{big_replacing(this_ind + 1, your_dict=nums_and_emoji)}│/EVN{this_ind + 1}\n🔻'
                # название эвента
                f'<b>{one_elem[0][0]}</b>'
                # описание эвента
                f'\n{one_emoji}{one_elem[0][1]}\n\n'
                for this_ind, one_elem in enumerate(remake_huge_list)
                if one_elem[1] == one_emoji
            ])
        # при наличии у блока частей
        else:
            # учитываем возможность появления в названии эмоджи "-",
            # из-за чего ТГ не будет выделять название как команду
            parse_html = 'i' if not exist_bad_symbol else 'code'

            # создаём строки для каждой части блока
            message_a += \
                ''.join(
                    [
                        # снача даём название части блока
                        f'❣{num2words(index_part + 1, to="ordinal").upper()} | '
                        f'<{parse_html}>/PART{index_part + 1}_{only_name_emoji}</{parse_html}>\n' +
                        ''.join(
                            [
                                # номер эвента
                                f'{big_replacing(this_ind + 1, your_dict=nums_and_emoji)}│/EVN{this_ind + 1}\n🔻'
                                # название эвента
                                f'<b>{remake_huge_list[this_ind][0][0]}</b>'
                                # описание эвента
                                f'\n{one_emoji}{remake_huge_list[this_ind][0][1]}\n\n'
                                for this_ind in one_part
                                if remake_huge_list[this_ind][1] == one_emoji
                            ])
                        # прокручиваем все части блока
                        for index_part, one_part in enumerate(parts_block)
                    ])

        # отсекли вторую \n
        message_a = message_a[:-1] + '➖➖➖➖➖➖➖➖➖➖➖➖➖\n'

        # условие на добавление страницы
        if one_ind % 2 != 0:
            n_page += 1

            pages_with_texts[n_page] = message_a
            only_pages.append(n_page)

            message_a = ''
        else:
            # если это последний эмоджи и при том не второй эмоджи,
            # при котором заканчивается страница
            if one_ind == len(full_emoji) - 1:
                n_page += 1
                pages_with_texts[n_page] = message_a
                only_pages.append(n_page)

    return pages_with_texts, only_pages


def pages_kb_for_remaking_dp_first_and_third(pages_with_texts, only_pages,
                                             message_pages, add_callback,
                                             view_number=None, reversed_kb=None):
    # если обычные цифры
    if not view_number:
        def view_number(x): return x

    if reversed_kb:
        # reverse ключей при сохранении значений на местах
        pages_with_texts = dict(zip(reversed(pages_with_texts.keys()), pages_with_texts.values()))

    # находим текст страницы и составляем КБ
    if out_come_text_mes := pages_with_texts.get(message_pages):
        # меньше 6 страниц
        if len(only_pages) < 6:

            butt_list = [get_button(f'· {view_number(n_page)} ·',
                                    callback_data=f"{n_page}_{add_callback}") if n_page is message_pages
                         else get_button(f'{view_number(n_page)}',
                                         callback_data=f"{n_page}_{add_callback}")
                         for n_page in only_pages]

        else:

            # всего больше 6 страниц, но нажата page <= 3
            butt_list = []
            if message_pages <= 3:
                for n_page in only_pages:

                    if n_page == message_pages:
                        butt_list.append(
                            get_button(f'· {n_page} ·',
                                       callback_data=f"{n_page}_{add_callback}"))
                    elif n_page in (1, 2, 3):
                        butt_list.append(
                            get_button(f'{n_page}',
                                       callback_data=f"{n_page}_{add_callback}"))
                    elif n_page == 4:
                        butt_list.append(
                            get_button(f'{n_page} ›',
                                       callback_data=f"{n_page}_{add_callback}"))
                    elif n_page == 5:
                        butt_list.append(get_button(f'{only_pages[-1]} »',
                                                    callback_data=f'{only_pages[-1]}_{add_callback}'))
                        break
            else:

                # всего больше 6 страниц, а нажата page > 3
                butt_list = \
                    [
                        get_button(f'« {only_pages[0]}', callback_data=f"{only_pages[0]}_{add_callback}"),
                        get_button(f'‹ {message_pages - 1}', callback_data=f"{message_pages - 1}_{add_callback}"),
                        get_button(f'· {message_pages} ·', callback_data=f"{message_pages}_{add_callback}")
                    ]

                if message_pages + 1 in only_pages:
                    mes_this = f'{message_pages + 1}' if message_pages + 3 not in only_pages \
                        else f'{message_pages + 1} ›'
                    butt_list.append(get_button(mes_this,
                                                callback_data=f'{message_pages + 1}_{add_callback}'))
                if message_pages + 2 in only_pages:
                    mes_this = str(only_pages[-1]) if message_pages + 3 not in only_pages \
                        else f'{only_pages[-1]} »'
                    butt_list.append(get_button(mes_this,
                                                callback_data=f'{only_pages[-1]}_{add_callback}'))

        if reversed_kb:
            # просто переворачиваем будущую КБ
            butt_list.reverse()

        # если только одна страница, то убираем её
        kb_dp = None if len(butt_list) == 1 else row_buttons(*butt_list)

        return out_come_text_mes, kb_dp


def values_for_remake_dp_first(huge_list, remake_huge_list,
                               remake_element, message_pages,
                               last_page_set_2,
                               updated_data_values_first_dp):
    # изменение расписания
    if not updated_data_values_first_dp \
            or remake_huge_list != updated_data_values_first_dp[0] \
            or huge_list != updated_data_values_first_dp[8]:

        pages_with_texts, only_pages = \
            text_for_remake_dp_first(remake_huge_list)

        out_come_text_mes, kb_dp = \
            pages_kb_for_remaking_dp_first_and_third(pages_with_texts, only_pages, message_pages, 'sett_dp_1')

        copy_elem = kb_dp.copy() if kb_dp else None
        if remake_huge_list == huge_list:
            # None обязательно - может быть нуль
            full_kb_remake_dp = row_buttons(back_mes_but('back_to_compound'), your_kb=copy_elem) \
                if remake_element is None \
                else row_buttons(back_mes_but('back_to_compound'), back_to_relocating_but(last_page_set_2),
                                 your_kb=copy_elem)
        else:
            full_kb_remake_dp = row_buttons(back_mes_but('condition_closing_sett'),
                                            back_to_relocating_but(last_page_set_2), your_kb=copy_elem)

        updated_data_values_first_dp = \
            [remake_huge_list,
             message_pages,
             only_pages, pages_with_texts,
             kb_dp,
             out_come_text_mes, full_kb_remake_dp,
             remake_element, huge_list]

    # если изменился только редактируемый элемент, но сам ДП никак не изменился
    elif remake_element != updated_data_values_first_dp[7]:

        out_come_text_mes = updated_data_values_first_dp[5]
        copy_elem = updated_data_values_first_dp[4].copy() if updated_data_values_first_dp[4] else None
        if remake_huge_list == huge_list:
            # None обязательно - может быть нуль
            full_kb_remake_dp = row_buttons(back_mes_but('back_to_compound'),
                                            your_kb=copy_elem) \
                if remake_element is None \
                else row_buttons(back_mes_but('back_to_compound'), back_to_relocating_but(last_page_set_2),
                                 your_kb=copy_elem)
        else:
            full_kb_remake_dp = row_buttons(back_mes_but('condition_closing_sett'),
                                            back_to_relocating_but(last_page_set_2),
                                            your_kb=copy_elem)
        updated_data_values_first_dp[6], updated_data_values_first_dp[7] = \
            full_kb_remake_dp, remake_element

    # если изменилась только страница, но сам ДП никак не изменился
    elif message_pages != updated_data_values_first_dp[1]:

        out_come_text_mes, kb_dp = \
            pages_kb_for_remaking_dp_first_and_third(updated_data_values_first_dp[3],
                                                     updated_data_values_first_dp[2], message_pages, 'sett_dp_1')

        # оставляем такие же дополнительные кнопки, но меняем кнопки-страницы
        if kb_dp:
            updated_data_values_first_dp[6]['inline_keyboard'][0] = kb_dp.copy()['inline_keyboard'][0]
        full_kb_remake_dp = updated_data_values_first_dp[6]

        # обновляем основной список
        updated_data_values_first_dp[1], updated_data_values_first_dp[4], \
        updated_data_values_first_dp[5] = \
            message_pages, kb_dp, \
            out_come_text_mes

    # если ничего не изменилось
    else:
        out_come_text_mes, full_kb_remake_dp = \
            updated_data_values_first_dp[5], updated_data_values_first_dp[6]

    return out_come_text_mes, full_kb_remake_dp, updated_data_values_first_dp


"""SECOND AND THIRD WINDOWS DP REMAKING"""


def text_for_remake_dp_second_and_third(remake_huge_list, events_pattern_for_putting):
    # формируем отдельные элементы расписания
    pages_with_texts = {1: ""}
    pages_with_indexes = {1: []}
    pages_with_patterns = {1: []}
    only_pages = [1]

    # создаём строки ДП
    n_page = 1
    for one_ind in range(len(remake_huge_list)):

        # создаём булевые повторяющиеся условия
        maybe_even_page = (one_ind + 1) % 5 == 0
        maybe_last = one_ind != len(remake_huge_list) - 1
        maybe_nearly_last = maybe_even_page and one_ind + 1 == len(remake_huge_list) - 1

        message_a = f'{big_replacing(one_ind + 1, your_dict=nums_and_emoji)}\n' \
                    f'🔺 ${events_pattern_for_putting[one_ind]}'

        message_a += '\n〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️〰️\n' \
            if maybe_last and not maybe_even_page or maybe_nearly_last \
            else '\n'

        # расширяем строку данной страницы
        pages_with_texts[n_page] += message_a
        # добавляем индекс элемента к данной странице
        pages_with_indexes[n_page].append(one_ind)
        # добавляем паттерн эвента эмоджи к данной странице
        pages_with_patterns[n_page].append(events_pattern_for_putting[one_ind])

        # разбиваем по страницам
        if maybe_even_page and maybe_last and not maybe_nearly_last:
            n_page += 1

            pages_with_texts[n_page] = ''
            pages_with_indexes[n_page] = []
            pages_with_patterns[n_page] = []
            only_pages.append(n_page)

    return only_pages, pages_with_texts, pages_with_indexes, pages_with_patterns


def pages_kb_for_remaking_dp_second(updated_data_rome_kb,
                                    allow_pages,
                                    pages_with_texts, last_action_remaking,
                                    remake_element,
                                    message_pages, add_callback):
    # если нужно показать страницы блока | части блока
    if len(allow_pages) > 1:

        # если None или есть изменения
        if not updated_data_rome_kb \
                or updated_data_rome_kb[0] != pages_with_texts \
                or updated_data_rome_kb[6] != allow_pages \
                or updated_data_rome_kb[7] != remake_element:

            # берём текст только из разрешённых страниц
            message_pages = 1
            pages_with_texts_new = [text_page
                                    for number_page, text_page in pages_with_texts.items()
                                    if int(number_page) in allow_pages]

            # получаем обновлённый список чисто страниц
            only_pages_new = [one_num for one_num in range(1, len(pages_with_texts_new) + 1)]

            # в типовой дикт - {number_page: text_page}
            pages_with_texts_new = dict(zip(only_pages_new, pages_with_texts_new))

            # обычная КБ, но с обновлёнными страницами
            # если двигаем элемент вниз - переворачиваем КБ
            asked, now_kb = pages_kb_for_remaking_dp_first_and_third(pages_with_texts_new,
                                                                     only_pages_new,
                                                                     message_pages, add_callback,
                                                                     in_roman_number, reversed_kb=
                                                                     True if last_action_remaking == 'down_element'
                                                                     else False)

            updated_data_rome_kb = \
                [pages_with_texts, message_pages, only_pages_new, pages_with_texts_new,
                 asked, now_kb, allow_pages, remake_element]

        elif updated_data_rome_kb[1] != message_pages:

            # если двигаем элемент вниз - переворачиваем КБ
            asked, now_kb = pages_kb_for_remaking_dp_first_and_third(updated_data_rome_kb[3],
                                                                     updated_data_rome_kb[2],
                                                                     message_pages, add_callback,
                                                                     in_roman_number, reversed_kb=
                                                                     True if last_action_remaking == 'down_element'
                                                                     else False)

            updated_data_rome_kb[1], updated_data_rome_kb[4], updated_data_rome_kb[5] = \
                message_pages, asked, now_kb

        else:
            asked, now_kb = \
                updated_data_rome_kb[4], updated_data_rome_kb[5]

        return asked, now_kb, updated_data_rome_kb

    else:
        updated_data_rome_kb = \
            [pages_with_texts, message_pages, allow_pages, pages_with_texts,
             pages_with_texts[allow_pages[0]], None, allow_pages]

        # нет страниц у одного эвента: КБ = None
        return pages_with_texts[allow_pages[0]], None, updated_data_rome_kb


def full_kb_for_second_window(need_kb, remake_element,
                              last_page_set_1, last_page_set_3, relocating_part_block):
    if not last_page_set_3: last_page_set_3 = 1

    # изменяем число выбранного эвента на эмоджи число
    if type(remake_element) is int:
        remake_element = big_replacing(remake_element + 1, your_dict=nums_and_emoji)
    elif type(remake_element) is list:
        number_part_block = in_roman_number(relocating_part_block[-1]) \
            if type(relocating_part_block[-1]) is int \
            else relocating_part_block[-1]
        remake_element = \
            f'{number_part_block}_{relocating_part_block[0]}_{number_part_block}'

    this_el = get_button(remake_element, callback_data='NONE')
    up_but = get_button('🔺️', callback_data='up_element')
    down_but = get_button('🔻', callback_data='down_element')
    see_all_dp_but = get_button('▶️', callback_data=f'{last_page_set_3}_sett_dp_3')
    choice_elms_but = get_button('◀️️', callback_data=f'{last_page_set_1}_sett_dp_1')

    need_kb_full = add_buttons(up_but, this_el, down_but,
                               choice_elms_but, see_all_dp_but,
                               your_kb=need_kb.copy() if need_kb else None)

    return need_kb_full


def full_kb_for_third_window(need_kb, remake_element,
                             history_remakes, last_page_set_2, callback_data):
    if callback_data != 'save_remakes' and history_remakes:
        # находим количество элементов в будущем
        only_future = sum([1 for one_elem_history in history_remakes if one_elem_history[-1] == 'in_future'])

        # находим элементы прошлого, к которым можем вернуться
        only_old = len(history_remakes) - only_future - 1
    else:
        only_future = only_old = 0

    # если историю перемещали или сохраняли
    callback_to_relocating = f'{last_page_set_2}_sett_dp_2'
    if callback_data in ('back_old_step', 'back_future_step', 'save_remakes'):
        callback_to_relocating = f'{remake_element}|_sett_dp_2' \
            if callback_data != 'save_remakes' and remake_element \
            else '1_sett_dp_1'

    need_kb = \
        add_buttons(
            get_button(f'↩⎛{big_replacing(only_old, your_dict=dict_with_small_numbers)}⎠',
                       callback_data='back_old_step'),
            get_button('🔹SAFE🔹', callback_data='save_remakes'),
            get_button(f'⎛{big_replacing(only_future, your_dict=dict_with_small_numbers)}⎠↪️',
                       callback_data='back_future_step'),
            get_button('⬅️', callback_data=callback_to_relocating),
            your_kb=need_kb)

    return need_kb


def values_for_remake_dp_second_and_third(remake_huge_list,
                                          this_updated_data,
                                          add_callback, remake_element,
                                          message_pages=1, history_remakes=None,
                                          last_page_set_2=None, callback_data=None,
                                          last_action_remaking=None, last_page_set_1=None,
                                          last_page_set_3=None, relocating_part_block=None) -> (str, dict, list, dict):
    if not this_updated_data:

        # лист с паттерном для каждого эвента для вставки в шаблон
        events_pattern_for_putting = [f'event_{number_emoji}'
                                      for number_emoji in range(len(remake_huge_list))]

        # формируем шаблон расписания
        only_pages, pages_with_sample_texts, pages_with_indexes, pages_with_patterns \
            = text_for_remake_dp_second_and_third(remake_huge_list, events_pattern_for_putting)

        # dict для вставки в шаблон: {pattern_event: event}
        values_putting = dict(zip(
            events_pattern_for_putting,
            [f'<b>{one_elem[0][0]}</b>\n{one_elem[1]} {one_elem[0][1]}' for one_elem in remake_huge_list]))

        # получаем конечный дикт для работы
        pages_with_texts = \
            dict(
                [
                    (one_page, string.Template(text_page).safe_substitute(values_putting))
                    for one_page, text_page in pages_with_sample_texts.items()
                ]
            )

        # находим сообщение и создаём buttons для данного page
        updated_data_rome_kb = allow_pages = None
        if add_callback == 'sett_dp_3':
            out_come_text_mes, kb_dp = \
                pages_kb_for_remaking_dp_first_and_third(pages_with_texts, only_pages, 1, add_callback)

            full_kb_remake_dp = full_kb_for_third_window(kb_dp, remake_element,
                                                         history_remakes, last_page_set_2, callback_data)
        else:
            allow_pages = get_pages_with_this_elem(remake_element,
                                                   get_dict_with_index_emoji(remake_huge_list),
                                                   pages_with_indexes)
            out_come_text_mes, kb_dp, updated_data_rome_kb = \
                pages_kb_for_remaking_dp_second(updated_data_rome_kb,
                                                allow_pages,
                                                pages_with_texts, last_action_remaking,
                                                remake_element,
                                                1, add_callback)

            # при создания расписания страница = 1
            message_pages = 1

            full_kb_remake_dp = full_kb_for_second_window(kb_dp, remake_element,
                                                          last_page_set_1, last_page_set_3, relocating_part_block)

        this_updated_data = \
            [remake_huge_list, message_pages,
             only_pages, pages_with_texts,
             kb_dp,
             out_come_text_mes, full_kb_remake_dp,
             updated_data_rome_kb,
             pages_with_sample_texts, pages_with_indexes, pages_with_patterns,
             remake_element, allow_pages]

    # при изменении в элементах
    elif remake_huge_list != this_updated_data[0]:

        # разбираемся: что за элемент был обновлён
        updated_element = [one_index for one_index, new_elem in enumerate(remake_huge_list)
                           if new_elem != this_updated_data[0][one_index]]

        # получаем страницы с изменённым элементом
        updated_pages = get_pages_with_this_elem(updated_element,
                                                 get_dict_with_index_emoji(remake_huge_list), this_updated_data[9])

        # обновляем каждую из обновлённых страниц в pages_with_texts
        for one_page in updated_pages:
            # создаём dict: {pattern: event} для этой page
            values_putting = \
                dict(
                    zip(
                        # паттерны этой страницы
                        this_updated_data[10][one_page],

                        # объединяем с обновлёнными эмоджи этой страницы
                        [f'<b>{remake_huge_list[one_ind][0][0]}</b>\n{remake_huge_list[one_ind][1]} '
                         f'{remake_huge_list[one_ind][0][1]}'
                         for one_ind in this_updated_data[9][one_page]]
                    )
                )

            # оставляем возможность вставки только для str_clock и progress_dp
            this_updated_data[3][one_page] = \
                string.Template(this_updated_data[8][one_page]).safe_substitute(values_putting)

        # находим сообщение и создаём buttons для данного page
        if add_callback == 'sett_dp_3':
            out_come_text_mes, kb_dp = \
                pages_kb_for_remaking_dp_first_and_third(this_updated_data[3], this_updated_data[2],
                                                         message_pages, add_callback)

            full_kb_remake_dp = full_kb_for_third_window(kb_dp, remake_element,
                                                         history_remakes, last_page_set_2, callback_data)
        else:
            this_updated_data[12] = get_pages_with_this_elem(str(remake_element) if type(remake_element) is int
                                                             else remake_element,
                                                             get_dict_with_index_emoji(remake_huge_list),
                                                             this_updated_data[9])

            out_come_text_mes, kb_dp, updated_data_rome_kb = \
                pages_kb_for_remaking_dp_second(this_updated_data[7],
                                                this_updated_data[12],
                                                this_updated_data[3], last_action_remaking,
                                                remake_element,
                                                message_pages, add_callback)
            this_updated_data[7] = updated_data_rome_kb

            # при любом обновлении расписания страница = 1
            message_pages = 1

            full_kb_remake_dp = full_kb_for_second_window(kb_dp, remake_element,
                                                          last_page_set_1, last_page_set_3, relocating_part_block)

        # обновляем основной список
        this_updated_data[0], this_updated_data[1], \
        this_updated_data[4], \
        this_updated_data[5], this_updated_data[6] = \
            remake_huge_list, message_pages, \
            kb_dp, \
            out_come_text_mes, full_kb_remake_dp

    # при изменении редактируемого элемента или сохранении изменений
    elif (remake_element is not None and remake_element != this_updated_data[11]) or callback_data == 'save_remakes':

        # находим сообщение и создаём buttons для данного page
        if add_callback == 'sett_dp_3':
            out_come_text_mes, kb_dp = \
                pages_kb_for_remaking_dp_first_and_third(this_updated_data[3], this_updated_data[2],
                                                         message_pages, add_callback)

            full_kb_remake_dp = full_kb_for_third_window(kb_dp, remake_element,
                                                         history_remakes, last_page_set_2, callback_data)
        else:
            allow_pages = get_pages_with_this_elem(remake_element,
                                                   get_dict_with_index_emoji(remake_huge_list),
                                                   this_updated_data[9])
            this_updated_data[12] = allow_pages

            out_come_text_mes, kb_dp, updated_data_rome_kb = \
                pages_kb_for_remaking_dp_second(None,
                                                allow_pages,
                                                this_updated_data[3], last_action_remaking,
                                                remake_element,
                                                message_pages, add_callback)
            this_updated_data[7] = updated_data_rome_kb

            # при любом обновлении remake_element message_pages = 1
            message_pages = 1

            full_kb_remake_dp = full_kb_for_second_window(kb_dp, remake_element,
                                                          last_page_set_1, last_page_set_3, relocating_part_block)

        # обновляем основной список
        this_updated_data[0], this_updated_data[1], \
        this_updated_data[4], \
        this_updated_data[5], this_updated_data[6], \
        this_updated_data[11] = \
            remake_huge_list, message_pages, \
            kb_dp, \
            out_come_text_mes, full_kb_remake_dp, \
            remake_element

    # если изменилась только страница, но сам ДП никак не изменился
    elif message_pages != this_updated_data[1]:

        # находим сообщение и создаём buttons для данного page
        if add_callback == 'sett_dp_3':
            out_come_text_mes, kb_dp = \
                pages_kb_for_remaking_dp_first_and_third(this_updated_data[3],
                                                         this_updated_data[2], message_pages, add_callback)
        else:
            out_come_text_mes, kb_dp, updated_data_rome_kb = \
                pages_kb_for_remaking_dp_second(this_updated_data[7],
                                                this_updated_data[12],
                                                this_updated_data[3], last_action_remaking,
                                                remake_element,
                                                message_pages, add_callback)
            if updated_data_rome_kb:
                message_pages = updated_data_rome_kb[1]
            this_updated_data[7] = updated_data_rome_kb

        # оставляем такие же дополнительные кнопки, но меняем кнопки-страницы
        if kb_dp:
            # если страниц нет, то kb_dp может быть None
            this_updated_data[6]['inline_keyboard'][0] = kb_dp.copy()['inline_keyboard'][0]
        full_kb_remake_dp = this_updated_data[6]

        # обновляем основной список
        this_updated_data[1], this_updated_data[4], \
        this_updated_data[5] = \
            message_pages, kb_dp, \
            out_come_text_mes

    # если ничего не изменилось
    else:
        out_come_text_mes, full_kb_remake_dp = \
            this_updated_data[5], this_updated_data[6]

    return out_come_text_mes, full_kb_remake_dp, this_updated_data


"""RELOCATING ELEMENTS DP"""


def height_change_elements(general_list, to_up_indexes, to_down_indexes):
    # получаем все перемещаемые индексы и элементы
    relocate_indexes = \
        to_up_indexes + to_down_indexes
    relocate_elements = [general_list[one_index]
                         for one_index in relocate_indexes]

    # смещаем вверх по индексу перемещаемые элементы
    for one_index, general_index in enumerate(sorted(relocate_indexes)):
        general_list[general_index] = relocate_elements[one_index]
    return general_list


def delete_different_parts_block(begin_index_block, end_index_block,
                                 huge_list, our_emoji,
                                 action):
    # срез, где есть эвенты нашего эмоджи
    here_is_our_emoji = [huge_list[one_index]
                         for one_index in range(begin_index_block, end_index_block + 1)]

    # уникальные эмоджи из нашего среза, но без нашего эмоджи
    full_emoji = list(OrderedDict.fromkeys((one_elem[1]
                                            for one_elem in here_is_our_emoji
                                            if one_elem[1] != our_emoji)))
    # если нужно вниз, то добавляем в конец
    # иначе - в начало
    if action == 'down_element':
        full_emoji.append(our_emoji)
    else:
        full_emoji.insert(0, our_emoji)

    # эвенты среза в необходимой последовательности
    blocks_with_events_in_slice = \
        [one_elem
         for one_emoji in full_emoji
         for one_elem in here_is_our_emoji
         if one_elem[1] == one_emoji]

    # подставляем под индексы созданную последовательность
    new_locating_blocks = [blocks_with_events_in_slice.pop(0)
                           for _ in here_is_our_emoji]
    huge_list[begin_index_block:end_index_block + 1] = new_locating_blocks


def up_down_elements(remake_element, remake_huge_list,
                     relocating_part_block, history_remakes,
                     action):
    # действие вниз | только один блок
    if action == 'down_element' \
            or (len(set([one_elem[1] for one_elem in remake_huge_list])) == 1
                and type(remake_element) is str):

        if type(remake_element) is int:

            if remake_element < len(remake_huge_list) - 1:
                # меняем местами данный элемент и элемент с индексом + 1
                remake_huge_list[remake_element], remake_huge_list[remake_element + 1] = \
                    remake_huge_list[remake_element + 1], remake_huge_list[remake_element]
                remake_element += 1

            else:

                # если это последний индекс
                remake_huge_list.insert(0, remake_huge_list.pop(-1))
                remake_element = 0

        elif type(remake_element) is list:

            # получаем индексы нашей части блока
            our_indexes = relocating_part_block[1]
            last_index_emoji = our_indexes[-1]

            # меняем части друг с другом
            if last_index_emoji != len(remake_huge_list) - 1:
                # идексы n-части следующего эмоджи
                next_emoji = remake_huge_list[last_index_emoji + 1][1]
                their_indexes = get_indexes_current_part_block(next_emoji,
                                                               get_dict_with_index_emoji(remake_huge_list),
                                                               remake_huge_list,
                                                               use_this_index_as_first=last_index_emoji + 1,
                                                               action=action)
                if relocating_part_block[0] == next_emoji:
                    their_indexes = list(set(their_indexes) ^ set(our_indexes))

                # непосредственно перемещение
                remake_huge_list = height_change_elements(remake_huge_list,
                                                          to_up_indexes=their_indexes, to_down_indexes=our_indexes)
            else:
                # удаляем эвенты блока из конца и добавляем в начало
                for one_index in our_indexes:
                    remake_huge_list.insert(0, remake_huge_list.pop(one_index))

            # обновляем индексы части блока
            relocating_part_block[1] = remake_element = \
                sorted([remake_huge_list.index(one_elem) for one_elem in relocating_part_block[2]])

            # обновляем номер части данного блока
            full_indexes_parts = get_indexes_current_part_block(relocating_part_block[0],
                                                                get_dict_with_index_emoji(remake_huge_list),
                                                                remake_huge_list,
                                                                get_full_indexes_parts=True,
                                                                action=action)

            relocating_part_block[-1] = full_indexes_parts.index(relocating_part_block[1]) + 1 \
                if relocating_part_block[1] in full_indexes_parts \
                else '⌘'

        else:
            # получаем обновлённый дикт
            new_with_index_emoji = \
                get_dict_with_index_emoji(remake_huge_list)

            # получаем индексы блока
            our_indexes = new_with_index_emoji.get(remake_element)

            # получаем части блока
            full_indexes_parts = get_indexes_current_part_block(remake_element, new_with_index_emoji,
                                                                remake_huge_list,
                                                                get_full_indexes_parts=True,
                                                                action=action)

            # перемещение эвентов данного эмоджи на место другого эмоджи
            begin_index_emoji, last_index_emoji = our_indexes[0], our_indexes[-1]
            if len(full_indexes_parts) > 1:
                delete_different_parts_block(begin_index_emoji, last_index_emoji,
                                             remake_huge_list, remake_element, action)

            elif last_index_emoji != len(remake_huge_list) - 1:
                next_emoji = remake_huge_list[last_index_emoji + 1][1]

                # идексы следующего эмоджи
                their_indexes = get_indexes_current_part_block(next_emoji,
                                                               new_with_index_emoji,
                                                               remake_huge_list,
                                                               use_this_index_as_first=last_index_emoji + 1,
                                                               action=action)
                # непосредственно перемещение
                remake_huge_list = height_change_elements(remake_huge_list,
                                                          to_up_indexes=their_indexes, to_down_indexes=our_indexes)
            else:

                # удаляем эвенты блока из конца и добавляем в начало
                for one_index in our_indexes:
                    remake_huge_list.insert(0, remake_huge_list.pop(one_index))

    # действие вверх!
    else:

        if type(remake_element) is int:
            if remake_element:
                # меняем местами данный элемент и элемент с индексом - 1
                remake_huge_list[remake_element], remake_huge_list[remake_element - 1] = \
                    remake_huge_list[remake_element - 1], remake_huge_list[remake_element]
                remake_element -= 1

            else:
                # если это нулевой индекс
                remake_huge_list.append(remake_huge_list.pop(0))
                remake_element = len(remake_huge_list) - 1

        elif type(remake_element) is list:

            # получаем индексы нашей части блока
            our_indexes = relocating_part_block[1]

            # меняем части друг с другом
            begin_index_emoji = our_indexes[0]

            if begin_index_emoji:

                # идексы n-части следующего эмоджи
                next_emoji = remake_huge_list[begin_index_emoji - 1][1]
                their_indexes = get_indexes_current_part_block(next_emoji,
                                                               get_dict_with_index_emoji(remake_huge_list),
                                                               remake_huge_list,
                                                               use_this_index_as_first=begin_index_emoji - 1,
                                                               action=action)
                if relocating_part_block[0] == next_emoji:
                    their_indexes = list(set(their_indexes) ^ set(our_indexes))

                # непосредственно перемещение
                remake_huge_list = height_change_elements(remake_huge_list,
                                                          to_up_indexes=our_indexes, to_down_indexes=their_indexes)
            else:
                # удаляем эвенты блока из начала и добавляем в конец
                for _ in our_indexes:
                    remake_huge_list.append(remake_huge_list.pop(0))

            # обновляем индексы части блока
            relocating_part_block[1] = remake_element = \
                sorted([remake_huge_list.index(one_elem) for one_elem in relocating_part_block[2]])

            # обновляем номер части данного блока
            full_indexes_parts = get_indexes_current_part_block(relocating_part_block[0],
                                                                get_dict_with_index_emoji(remake_huge_list),
                                                                remake_huge_list,
                                                                get_full_indexes_parts=True,
                                                                action=action)

            relocating_part_block[-1] = full_indexes_parts.index(relocating_part_block[1]) + 1 \
                if relocating_part_block[1] in full_indexes_parts \
                else '⌘'

        else:
            # получаем обновлённый дикт
            new_with_index_emoji = \
                get_dict_with_index_emoji(remake_huge_list)

            # получаем индексы блока
            our_indexes = new_with_index_emoji.get(remake_element)

            # получаем части блока
            full_indexes_parts = get_indexes_current_part_block(remake_element, new_with_index_emoji,
                                                                remake_huge_list,
                                                                get_full_indexes_parts=True,
                                                                action=action)

            # перемещение эвентов данного эмоджи на место другого эмоджи
            begin_index_emoji, last_index_emoji = our_indexes[0], our_indexes[-1]
            if len(full_indexes_parts) > 1:
                delete_different_parts_block(begin_index_emoji, last_index_emoji,
                                             remake_huge_list, remake_element, action)

            elif begin_index_emoji:
                next_emoji = remake_huge_list[begin_index_emoji - 1][1]

                # идексы следующего эмоджи
                their_indexes = get_indexes_current_part_block(next_emoji,
                                                               new_with_index_emoji,
                                                               remake_huge_list,
                                                               use_this_index_as_first=begin_index_emoji - 1,
                                                               action=action)

                # перемещаем элементы
                remake_huge_list = height_change_elements(remake_huge_list,
                                                          to_up_indexes=our_indexes, to_down_indexes=their_indexes)
            else:
                # удаляем эвенты блока из начала и добавляем в конец
                for _ in our_indexes:
                    remake_huge_list.append(remake_huge_list.pop(0))

    # избавляемся от старого будущего
    if history_remakes[-1][-1] == 'in_future':
        history_remakes = [one_elem
                           for one_elem in history_remakes
                           if one_elem[-1] != 'in_future']
    history_remakes.append([remake_element, remake_huge_list])

    return remake_element, remake_huge_list, relocating_part_block, history_remakes


def save_sett_remakes(user_id, cursor, conn, updated_data_steps_and_save=None):
    remake_huge_list, chosen_week_day, login_user, \
    bot_id = \
        get_common_data(user_id, cursor,
                        'remake_huge_list', 'chosen_week_day', 'login_user',
                        'bot_id')

    # обновляем расположение элементов данного дня в БД
    one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db', check_same_thread=False)
    one_user_cursor = one_user_conn.cursor()
    one_user_cursor.execute(f'UPDATE hierarchy_day_plans SET week_day_{chosen_week_day} = ?',
                            (str([one_el[3] for one_el in remake_huge_list]),))
    one_user_conn.commit()

    # обновляем данные в кэше
    save_common_data(user_id, cursor, conn,
                     huge_list=remake_huge_list,
                     remake_huge_list=remake_huge_list,
                     updated_data_rome_kb=None,
                     updated_data_relocating_elem=None,
                     updated_data_values_first_dp=None,
                     updated_data_steps_and_save=updated_data_steps_and_save,
                     remake_element=None, history_remakes=[])


# KB FOR ELEMENTS
func_create_but_event = \
    lambda index, one_data, with_element_call: \
            get_button(f'{big_replacing(index + 1, your_dict=dict_with_bold_nums)} | {one_data[1]}',
                       callback_data=f'{one_data[0]}{with_element_call}')


func_create_but_block = \
    lambda index, one_data, with_element_call: \
            get_button(f'{big_replacing(index + 1, your_dict=dict_with_bold_nums)} | '
                       f'{one_data[2]} 【{one_data[1]}】',
                       callback_data=f'{one_data[0]}{with_element_call}')


def get_inline_pages_kb(new_inf,
                        func_create_button,
                        back_callback: str,
                        with_page_call: str,
                        with_element_call: str,
                        list_with_first_button=None) -> dict:
    # если не задана первая страница
    if list_with_first_button is None:
        list_with_first_button = []

    # формируем отдельные элементы расписания
    pages_with_data = {1: list_with_first_button}
    only_pages = [1]
    n_page = 1

    # save_page = 1, если сохраняем страницу, иначе - 0
    save_page = 0
    if new_inf:

        for one_ind, one_data in enumerate(new_inf):
            save_page = 0

            one_button = \
                func_create_button(one_ind, one_data, with_element_call)

            # номер элемента из data % 5 == 0
            maybe_even_page = (one_ind + 1) % 5 == 0
            # данный индекс - не последний индекс
            maybe_last = one_ind != len(new_inf) - 1
            # maybe_even_page = True & следующий индекс - последний индекс
            maybe_nearly_last = maybe_even_page and one_ind + 1 == len(new_inf) - 1

            # добавляем кнопку к данной странице
            pages_with_data[n_page].append(one_button)

            # разбиваем по страницам
            if maybe_even_page and maybe_last and not maybe_nearly_last:
                save_page = 1

                # смотрим: кнопки перемещения
                if n_page == 1:

                    # страница 1: кнопка назад
                    from_data_kb = add_buttons(*pages_with_data[1], row_width=1)
                    row_buttons(back_mes_but(back_callback),
                                get_button('➡️', callback_data=f'2{with_page_call}'),
                                your_kb=from_data_kb)
                    pages_with_data[1] = from_data_kb
                else:

                    # иные страницы: кнопки обратно-вперёд
                    from_data_kb = add_buttons(*pages_with_data[n_page], row_width=1)
                    row_buttons(get_button('⬅️️', callback_data=f'{n_page - 1}{with_page_call}'),
                                get_button('➡️', callback_data=f'{n_page + 1}{with_page_call}'),
                                your_kb=from_data_kb)
                    pages_with_data[n_page] = from_data_kb

                n_page += 1

                pages_with_data[n_page] = []
                only_pages.append(n_page)

    # значит, только одна страница
    if n_page == 1:
        pages_with_data[1].append(back_mes_but(back_callback))
        pages_with_data[1] = add_buttons(*pages_with_data[1], row_width=1)

    # если последнее действие в цикле != сохранению страницы ->
    # остались кнопки, которые не в КБ
    else:
        if not save_page:
            pages_with_data[n_page].append(get_button('⬅️️', callback_data=f'{n_page - 1}{with_page_call}'))
            pages_with_data[n_page] = add_buttons(*pages_with_data[n_page], row_width=1)

    return pages_with_data


def get_page_inline_kb(user_id, cursor, conn,
                       last_page, callback_data,
                       save_data_list, save_name,
                       sql_request, back_callback,
                       with_page_call, with_element_call,
                       func_create_but, bot_id,
                       use_first_button_condition,
                       list_with_first_button=None):

    # определяем страницу
    if with_page_call in callback_data:
        message_pages = int(callback_data[:-len(with_page_call)])
    else:
        message_pages = last_page if last_page else 1

    # смотрим: есть ли эвенты
    one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                    check_same_thread=False)
    one_user_cursor = one_user_conn.cursor()
    one_user_cursor.execute(sql_request)
    new_inf = one_user_cursor.fetchall()

    # если условие использования не подходит
    if not use_first_button_condition(new_inf):
        list_with_first_button = None

    # None | изменение данных
    if not save_data_list or save_data_list[0] != new_inf:

        # генерируем страницы
        pages_with_data = \
            get_inline_pages_kb(new_inf,
                                func_create_but,
                                back_callback=back_callback,
                                with_page_call=with_page_call,
                                with_element_call=with_element_call,
                                list_with_first_button=list_with_first_button)

        save_data_list = [new_inf, pages_with_data]
        save_common_data(user_id, cursor, conn, dict_save={save_name: save_data_list})

    # проверяем: не изменилась ли страница
    return [message_pages, save_data_list[1][message_pages]] \
               if save_data_list[1].get(message_pages) \
               else [message_pages-1, save_data_list[1].get(message_pages-1)]


def with_choosing_elements_kb(user_id,
                            bot_id,
                            cursor, conn,
                            work_with_event,
                            your_data_save, your_save_name,
                            last_page, with_page_call, with_element_call,
                            back_callback, list_with_first_button=None, callback_data='',
                            use_first_button_condition=lambda x: True,
                            sql_request=''):

    # получаем страницу КБ
    message_pages, one_kb = \
        get_page_inline_kb(user_id, cursor, conn,
                           last_page=last_page,
                           callback_data=callback_data,
                           save_data_list=your_data_save,
                           save_name=your_save_name,
                           sql_request=sql_request,
                           back_callback=back_callback,
                           with_page_call=with_page_call,
                           func_create_but=
                           func_create_but_event if work_with_event else func_create_but_block,
                           bot_id=bot_id,
                           use_first_button_condition=use_first_button_condition,
                           with_element_call=with_element_call,
                           list_with_first_button=list_with_first_button)

    return message_pages, one_kb


def get_data_one_event(user_id, cursor, conn, event_code,
                       bot_id, last_page_choose_events) -> tuple:
    # бд пользователя
    one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                    check_same_thread=False)
    one_user_cursor = one_user_conn.cursor()

    # получаем данные выбранного эвента
    one_user_cursor.execute(
        '''SELECT name_dp, description_dp, description_element, time_of_doing, its_code_block 
        FROM classification_of_events WHERE code_element = ?''', (event_code,))
    data_events = one_user_cursor.fetchone()
    event_name, event_describe_dp, event_describe_el, event_time_work, its_code_block = \
        data_events

    # формируем текст для запоминания
    text_for = f'<b>◾️️THE EVENT◾️️</b> \n' \
               f'<b>{str(event_name).upper()}</b>' \
               f' 【<code>' \
               f'{big_replacing(event_time_work, your_dict=dict_with_bold_nums)} MINS' \
               f'</code>】\n' \
               f'<i>{str(event_describe_el).capitalize()}</i>\n'

    # добавляем возможноть разорвать связь с блоком
    if its_code_block:
        one_user_cursor.execute(
            '''SELECT block_emoji, name_dp FROM classification_of_blocks 
            WHERE code_element = ?''', (its_code_block,))
        emoji_block, name_block = \
            one_user_cursor.fetchone()

        text_for += f'▫️<b>Имеет связь с блоком: </b>' \
                    f'<b><code>{name_block}</code> 【{emoji_block}】</b>\n'

        one_event_sett_kb = add_buttons(
            get_button('📝РЕДАКТИРОВАНИЕ📝', callback_data='edit_event'),
            get_button('⚔️ЛИШИТЬ БЛОКА⚔️️', callback_data='minus_block_from_event'),
            row_width=1)
    else:
        # находим блоки
        one_user_cursor.execute('SELECT * FROM classification_of_blocks')
        all_blocks = one_user_cursor.fetchall()

        # есть как минимум 1 блока
        if all_blocks:
            one_event_sett_kb = add_buttons(
                get_button('📝РЕДАКТИРОВАНИЕ📝', callback_data='edit_event'),
                get_button('👉СВЯЗАТЬ С БЛОКОМ👈 ️', callback_data='add_block_from_event'),
                row_width=1)

        else:
            one_event_sett_kb = add_buttons(
                get_button('📝РЕДАКТИРОВАНИЕ📝', callback_data='edit_event'))

    one_event_sett_kb = row_buttons(
        back_mes_but(f'{last_page_choose_events}_page_to_event'),
        get_button('❌', callback_data='delete_event'), your_kb=one_event_sett_kb)

    save_common_data(user_id, cursor, conn,
                     work_element=(event_code, str(event_name), text_for, one_event_sett_kb, its_code_block))

    return event_code, str(event_name), text_for, one_event_sett_kb, its_code_block


def create_days_work_block_kb(block_days_work,
                              callback_data='',
                              minus_days=False,
                              adding_callback='week_day_',
                              just_update_data=False) -> dict:
    # None | изменились дни
    if not block_days_work \
            or adding_callback in callback_data \
            or minus_days \
            or just_update_data:

        # ещё ничего не выбрали | последний список выбранных дней
        list_with_days = \
            [] if not block_days_work else block_days_work[0]
        list_with_not_sort_days = \
            [] if not block_days_work else block_days_work[1]

        # удаление дней
        if minus_days:
            list_with_days.remove(list_with_not_sort_days.pop(-1))

        # добавление дней
        elif callback_data:
            # определяем день недели
            one_day = int(callback_data[-1])

            # обновляем список используемых
            list_with_days.append(one_day)
            list_with_not_sort_days.append(one_day)

            list_with_days.sort()

        # обновляем строку со всеми днями
        all_use_day_str = '-'.join([short_name_week_days[day_week]
                                    for day_week in list_with_days])

        # дни, которые ещё можно использовать
        not_use_day = set(list_with_days) ^ {0, 1, 2, 3, 4, 5, 6}

        # создаём КБ с неиспользованными днями
        with_not_use_kb = \
            row_buttons(
                *[get_button(short_name_week_days[day_week],
                             callback_data=f'{adding_callback}{day_week}')
                  for day_week in not_use_day])

        block_days_work = [list_with_days, list_with_not_sort_days,
                               all_use_day_str, with_not_use_kb]

    return block_days_work


def get_data_one_block(user_id, cursor, conn, block_code,
                       bot_id, last_page_choose_blocks) -> tuple:
    # бд пользователя
    one_user_conn = sqlite3.connect(f'users_bot/{bot_id}_log/user_db.db',
                                    check_same_thread=False)
    one_user_cursor = one_user_conn.cursor()

    # получаем данные выбранного блока
    one_user_cursor.execute(
        '''SELECT block_emoji, name_dp, description_element, physics_cycle, content 
        FROM classification_of_blocks WHERE code_element = ?''', (block_code,))
    data_block = one_user_cursor.fetchone()
    block_emoji, block_name, block_describe_el, block_days_work, block_content = \
        data_block

    # переводим в листы
    block_days_work, block_content = \
        ast.literal_eval(block_days_work), ast.literal_eval(block_content)

    # формируем текст для запоминания
    text_for = f'<b>◾️THE BLOCK◾️️</b> \n' \
               f'<b>{str(block_name).upper()}</b>' \
               f' <i>【{block_emoji}】</i> \n' \
               f'<i>{str(block_describe_el).capitalize()}</i>\n' \
               f'▫️<b>Работаем в дни: </b>' \
               f'<code>' \
               f'{", ".join([short_name_week_days[one_day] for one_day in block_days_work])}' \
               f'</code>'

    one_block_sett_kb = \
        add_buttons(
            get_button('📝РЕДАКТИРОВАНИЕ📝', callback_data='edit_block'),
            get_button('🗂СОДЕРЖАНИЕ🗂 ️', callback_data='edit_content_block'),
            row_width=1)
    row_buttons(back_mes_but(f'{last_page_choose_blocks}_page_to_block'),
                get_button('❌', callback_data='delete_block'), your_kb=one_block_sett_kb)

    save_common_data(user_id, cursor, conn,
                     work_element=(block_code, block_emoji, str(block_name), text_for,
                                   one_block_sett_kb, block_days_work, block_content))

    return block_code, block_emoji, str(block_name), text_for, \
           one_block_sett_kb, block_days_work, block_content
