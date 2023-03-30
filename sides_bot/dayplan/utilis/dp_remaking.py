from collections import OrderedDict
from emoji import emojize, demojize
from num2words import num2words
import string
#
from utilis.consts_common import back_mes_but, nums_and_emoji, dict_with_small_numbers, emoji_work_dp_list, \
    bad_symbols_for_emoji_name
from utilis.main_common import big_replacing, get_button, row_buttons, add_buttons
#
from sides_bot.dayplan.utilis.consts import back_to_relocating_but
from sides_bot.dayplan.utilis.main import in_roman_number, \
    get_pages_with_this_elem, get_dict_with_index_emoji, get_data_process_dp, save_data_process_dp, \
    get_first_work_index
from sides_bot.dayplan.utilis.dp_usual import values_for_usual_dp
from sides_bot.dayplan.utilis.block import get_indexes_current_part_block, \
    get_time_block, minus_all_freeze_block

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
            full_kb_remake_dp = row_buttons(back_mes_but('settings_DP'), your_kb=copy_elem) \
                if remake_element is None \
                else row_buttons(back_mes_but('settings_DP'), back_to_relocating_but(last_page_set_2),
                                 your_kb=copy_elem)
        else:
            full_kb_remake_dp = row_buttons(back_mes_but('condition_closing'),
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
            full_kb_remake_dp = row_buttons(back_mes_but('settings_DP'),
                                            your_kb=copy_elem) \
                if remake_element is None \
                else row_buttons(back_mes_but('settings_DP'), back_to_relocating_but(last_page_set_2),
                                 your_kb=copy_elem)
        else:
            full_kb_remake_dp = row_buttons(back_mes_but('condition_closing'),
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


def save_dp_remakes(user_id, updated_data_steps_and_save=None):
    remake_huge_list, cold_block, all_time_DP, \
    delta_utc, the_end_dp, DP_clock, \
    recast_time_DP, huge_list, = \
        get_data_process_dp(user_id,
                            'remake_huge_list', 'cold_block', 'all_time_DP',
                            'delta_utc', 'the_end_dp', 'DP_clock',
                            'recast_time_DP', 'huge_list')

    # индексы cold_block должны быть обновлены
    if cold_block:
        cold_block = dict(
            [
                # dict формата: {emoji: [its_new_index_in_remake_huge_list]}
                (one_emoji,
                 [
                     # проверяем каждый элемент remake_huge_list,
                     new_index for new_index, new_elem in enumerate(remake_huge_list)
                     # не элемент ли это с айди (new_elem[3]), который был у данного эмоджи в cold_block
                     if new_elem[3] in [huge_list[old_index][3] for old_index in old_indexes_elements]
                 ])
                # запускаем цикл со старыми индексами эмоджи из cold_block
                for one_emoji, old_indexes_elements in cold_block.items()
            ])

    # обновляем значение рабочих переменных
    cl_ev_for_block = {}
    full_remake_huge_list = \
        minus_all_freeze_block(remake_huge_list, cold_block, with_deep_copy=True)
    with_index_emoji = work_with_index_emoji = \
        get_dict_with_index_emoji(full_remake_huge_list)

    # время блока и смена эмоджи
    updated_data_get_time_block, \
    clock_block, cold_block, \
    remake_huge_list, \
    progress_block, last_emoji, \
    our_part_of_block, \
    plus_time_work_block, all_time_DP, cold_event, \
    stb_block \
        = get_time_block(updated_data_get_time_block=None,
                         huge_list=remake_huge_list, clock_event=None,
                         clock_block=None, last_emoji=None,
                         our_part_of_block=[], cold_block=cold_block,
                         cl_ev_for_block=cl_ev_for_block, with_index_emoji=with_index_emoji,
                         end_last_time_event=None, all_time_DP=all_time_DP,
                         work_with_index_emoji=work_with_index_emoji, cold_event=[],
                         progress_block=None, plus_time_work_block=None,
                         index_this_elem=get_first_work_index(remake_huge_list, check_all_list=True), stb_block=0)

    # обновляем ДП
    out_come_text_mes, full_kb_dp, updated_data_usual_dp = \
        values_for_usual_dp(remake_huge_list,
                            all_time_DP=all_time_DP, delta_utc=delta_utc,
                            cold_event=None, clock_event=None,
                            cold_block=cold_block, clock_block=clock_block,
                            user_id=user_id, the_end_dp=the_end_dp,
                            DP_clock=DP_clock, str_clock=recast_time_DP,
                            first_open=False)

    save_data_process_dp(user_id, huge_list=remake_huge_list,
                         remake_huge_list=remake_huge_list,
                         cl_ev_for_block=cl_ev_for_block,
                         with_index_emoji=with_index_emoji, work_with_index_emoji=work_with_index_emoji,
                         updated_data_get_time_block=updated_data_get_time_block, clock_block=clock_block,
                         cold_block=cold_block, progress_block=progress_block, last_emoji=last_emoji,
                         our_part_of_block=our_part_of_block, plus_time_work_block=plus_time_work_block,
                         all_time_DP=all_time_DP, cold_event=cold_event, updated_data_rome_kb=None,
                         updated_data_relocating_elem=None,
                         updated_data_values_first_dp=None,
                         updated_data_usual_dp=updated_data_usual_dp,
                         remake_element=None, history_remakes=[],
                         updated_data_steps_and_save=updated_data_steps_and_save,
                         stb_block=0)
