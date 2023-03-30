import math
import string
#
from utilis.consts_common import nums_and_emoji
from utilis.main_common import big_replacing, \
    get_button, row_buttons
#
from sides_bot.dayplan.utilis.consts import first_open_but
from sides_bot.dayplan.utilis.main import get_user_time_now, \
    get_data_process_dp, save_data_process_dp, \
    get_pages_with_this_elem, get_delta_time_to_str


def get_progress_dp(huge_list):
    numbers_progress = \
        math.floor(
            sum([1 for one_elem in huge_list if one_elem[1] == '⭐']) / len(huge_list) * 6)
    return numbers_progress * '█' + '▒' * (6 - numbers_progress)


def text_for_usual_dp(huge_list, events_pattern_for_putting):
    # формируем отдельные элементы расписания
    pages_with_texts = {1: "✔️<b>DAY PLAN</b>✖️\n"
                           "\t\t\t\t\t🕒 $str_clock 🕘\n"
                           " ❱◯$progress_dp◯❰\n\n"}
    pages_with_indexes = {1: []}
    pages_with_patterns = {1: []}
    only_pages = [1]

    # создаём строки ДП
    n_page = 1
    for one_ind, one_elm in enumerate(huge_list):
        name_elm, description_elm = one_elm[0]

        # номер элемента из data % 5 == 0
        maybe_even_page = (one_ind + 1) % 5 == 0
        # данный индекс - не последний индекс
        maybe_last = one_ind != len(huge_list) - 1
        # maybe_even_page = True & следующий индекс - последний индекс
        maybe_nearly_last = maybe_even_page and one_ind + 1 == len(huge_list) - 1

        message_a = f'{big_replacing(one_ind + 1, your_dict=nums_and_emoji)}\n' \
                    f'🔺 <b>{name_elm}</b>\n' \
                    f'${events_pattern_for_putting[one_ind]} {description_elm}'

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


def pages_kb_for_usual_dp(pages_with_texts, only_pages,
                          message_pages, add_callback):
    # находим текст страницы и составляем КБ
    if out_come_text_mes := pages_with_texts.get(message_pages):
        # меньше 6 страниц
        if len(only_pages) < 6:

            butt_list = [get_button(f'· {n_page} ·',
                                    callback_data=f"{n_page}_{add_callback}") if n_page is message_pages
                         else get_button(f'{n_page}',
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

        # если только одна страница, то убираем её
        kb_dp = None if len(butt_list) == 1 else row_buttons(*butt_list)

        return out_come_text_mes, kb_dp


def get_full_pages_with_text(pages_with_text_without_clock,
                             str_clock, progress_dp):
    pages_with_texts = pages_with_text_without_clock.copy()
    pages_with_texts[1] = \
        string.Template(pages_with_texts[1]).safe_substitute(str_clock=str_clock,
                                                             progress_dp=progress_dp)
    return pages_with_texts


def get_full_dp_kb(need_kb,
                   huge_list,
                   all_time_DP, delta_utc,
                   cold_event, clock_event,
                   cold_block, clock_block,
                   user_id, the_end_dp, DP_clock,
                   end_last_time_event, last_emoji):

    new_need_kb = need_kb.copy() if need_kb else None

    # проверяем: выполнены ли все элементы | завершился ли ДП
    if all([True if one_elem[1] == '⭐' else False for one_elem in huge_list]) or the_end_dp:

        # завершаем ДП
        if not the_end_dp:
            # GET_DATA_PROCESS_DP
            stb_DP, updated_data_usual_dp = \
                get_data_process_dp(user_id,
                                    'stb_DP', 'updated_data_usual_dp')

            # последний блок
            this_block_time = (clock_block, end_last_time_event)
            all_time_DP[-1][last_emoji].append(this_block_time)

            # время ДП
            all_time_DP.append((DP_clock, str(get_user_time_now(delta_utc))))

            # высчитываем крайний раз дельту дп
            updated_data_usual_dp[2] = get_delta_time_to_str(DP_clock, delta_utc, adding_time=-stb_DP)

            save_data_process_dp(user_id,
                                 the_end_dp=1, all_time_DP=all_time_DP,
                                 clock_block=None, cold_event=None,
                                 updated_data_usual_dp=updated_data_usual_dp,
                                 proof='THE_END_DP')

        return row_buttons(get_button(f'✖️ЗАКРЫТЬ✖️', callback_data='close_DP'),
                           your_kb=new_need_kb)
    else:

        butt_list = [get_button('⚙️', 'settings_DP')]
        # если есть залуненные блоки
        if cold_event and not clock_event:
            butt_list.append(get_button('🌕', callback_data='mooning'))

        # если есть замороженные блоки и clock_block is None
        elif cold_block and not clock_block:
            butt_list.append(get_button('☀', callback_data='sunning'))
        butt_list.append(get_button(f'▷▷▷', callback_data='way_bl'))

        # кнопки из butt_list в один row
        return row_buttons(*butt_list, your_kb=new_need_kb)


def values_for_usual_dp(huge_list,
                        message_pages=1,
                        str_clock='000',
                        add_callback='xDP',
                        with_index_emoji=None,
                        updated_data_usual_dp=None,
                        first_open=first_open_but,
                        all_time_DP=None, delta_utc=None,
                        cold_event=None, clock_event=None,
                        cold_block=None, clock_block=None,
                        end_last_time_event=None, last_emoji=None,
                        user_id=None, the_end_dp=None, DP_clock=None) -> (str, dict, list, dict):

    # при изменении ДП/изменении способа его сортировки
    if not updated_data_usual_dp:

        # лист с паттерном для каждого эвента для вставки в шаблон
        events_pattern_for_putting = [f'emoji{number_emoji}'
                                      for number_emoji in range(len(huge_list))]

        # формируем шаблон расписания
        only_pages, pages_with_sample_texts, pages_with_indexes, pages_with_patterns \
            = text_for_usual_dp(huge_list, events_pattern_for_putting)

        # dict для вставки в шаблон: {pattern_emoji: emoji}
        values_putting = dict(zip(events_pattern_for_putting, [one_elem[1] for one_elem in huge_list]))

        # оставляем возможность вставки только для str_clock и progress_dp
        pages_with_text_without_clock = \
            dict(
                [
                    (one_page, string.Template(text_page).safe_substitute(values_putting))
                    for one_page, text_page in pages_with_sample_texts.items()
                ]
            )

        # со вставкой str_clock и progress_dp
        progress_dp = get_progress_dp(huge_list)
        pages_with_texts = get_full_pages_with_text(pages_with_text_without_clock,
                                                    str_clock, get_progress_dp(huge_list))

        # находим сообщение и создаём buttons для данного page
        out_come_text_mes, kb_dp = \
            pages_kb_for_usual_dp(pages_with_texts, only_pages,
                                  1, add_callback)

        full_kb_dp = row_buttons(first_open, your_kb=kb_dp.copy() if kb_dp else None) if first_open \
            else get_full_dp_kb(kb_dp,
                                huge_list,
                                all_time_DP, delta_utc,
                                cold_event, clock_event,
                                cold_block, clock_block,
                                user_id, the_end_dp, DP_clock,
                                end_last_time_event=end_last_time_event, last_emoji=last_emoji)

        return out_come_text_mes, full_kb_dp, \
               [huge_list,
                add_callback, str_clock, message_pages,
                only_pages, pages_with_texts, progress_dp,
                kb_dp,
                out_come_text_mes, full_kb_dp,
                pages_with_sample_texts, pages_with_indexes,
                pages_with_patterns, pages_with_text_without_clock]

    # при изменении в элементах
    elif huge_list != updated_data_usual_dp[0]:

        # разбираемся: что за элемент был обновлён
        updated_element = [one_index for one_index, new_elem in enumerate(huge_list)
                           if new_elem != updated_data_usual_dp[0][one_index]]

        # получаем страницы с изменённым элементом
        updated_pages = get_pages_with_this_elem(updated_element,
                                                 with_index_emoji, updated_data_usual_dp[11])

        # обновляем каждую из страниц в pages_with_texts
        for one_page in updated_pages:
            # создаём dict: {pattern: new_emoji} для этой page
            values_putting = \
                dict(
                    zip(
                        # паттерны этой страницы
                        updated_data_usual_dp[12][one_page],

                        # объединяем с обновлёнными эмоджи этой страницы
                        [huge_list[one_index_emoji][1]
                         for one_index_emoji in updated_data_usual_dp[11][one_page]]
                    )
                )

            # оставляем возможность вставки только для str_clock и progress_dp
            updated_data_usual_dp[13][one_page] = \
                string.Template(updated_data_usual_dp[10][one_page]).safe_substitute(values_putting)

        # получаем конечный обновлённый словарь
        progress_dp = get_progress_dp(huge_list)
        pages_with_texts = get_full_pages_with_text(updated_data_usual_dp[13],
                                                    str_clock,
                                                    progress_dp)

        # находим сообщение и создаём buttons для данного page
        out_come_text_mes, kb_dp = \
            pages_kb_for_usual_dp(pages_with_texts, updated_data_usual_dp[4],
                                  1, add_callback)

        # добавляем не только кнопки расписания
        full_kb_dp = get_full_dp_kb(kb_dp,
                                    huge_list,
                                    all_time_DP, delta_utc,
                                    cold_event, clock_event,
                                    cold_block, clock_block,
                                    user_id, the_end_dp, DP_clock,
                                    end_last_time_event=end_last_time_event, last_emoji=last_emoji)

        # обновляем основной список
        updated_data_usual_dp[0], \
        updated_data_usual_dp[5], updated_data_usual_dp[6], \
        updated_data_usual_dp[7], \
        updated_data_usual_dp[8], updated_data_usual_dp[9] = \
            huge_list, \
            pages_with_texts, progress_dp, \
            kb_dp, \
            out_come_text_mes, full_kb_dp

    # изменение add_callback
    elif add_callback != updated_data_usual_dp[1]:

        pages_with_texts = get_full_pages_with_text(updated_data_usual_dp[13],
                                                    str_clock, updated_data_usual_dp[6])

        # находим сообщение и создаём КБ для данного page
        out_come_text_mes, kb_dp = \
            pages_kb_for_usual_dp(pages_with_texts, updated_data_usual_dp[4],
                                  message_pages, add_callback)

        # добавляем не только кнопки расписания
        full_kb_dp = get_full_dp_kb(kb_dp,
                                    huge_list,
                                    all_time_DP, delta_utc,
                                    cold_event, clock_event,
                                    cold_block, clock_block,
                                    user_id, the_end_dp, DP_clock,
                                    end_last_time_event=end_last_time_event, last_emoji=last_emoji)

        # обновляем основной список
        updated_data_usual_dp[1], updated_data_usual_dp[7], \
        updated_data_usual_dp[8], updated_data_usual_dp[9], \
        updated_data_usual_dp[5] = \
            add_callback, kb_dp, \
            out_come_text_mes, full_kb_dp, \
            pages_with_texts

    # если изменилась только страница, но сам ДП никак не изменился
    elif message_pages != updated_data_usual_dp[3]:

        # находим сообщение и создаём КБ для данного page
        out_come_text_mes, kb_dp = \
            pages_kb_for_usual_dp(updated_data_usual_dp[5], updated_data_usual_dp[4],
                                  message_pages, add_callback)

        # оставляем такие же дополнительные кнопки, но меняем кнопки-страницы
        if kb_dp:
            updated_data_usual_dp[9]['inline_keyboard'][0] = kb_dp.copy()['inline_keyboard'][0]
        full_kb_dp = updated_data_usual_dp[9]

        # обновляем основной список
        updated_data_usual_dp[3], updated_data_usual_dp[7], \
        updated_data_usual_dp[8] = \
            message_pages, kb_dp, \
            out_come_text_mes

    # изменение времени
    elif str_clock != updated_data_usual_dp[2]:

        pages_with_texts = get_full_pages_with_text(updated_data_usual_dp[13],
                                                    str_clock, updated_data_usual_dp[6])

        out_come_text_mes, full_kb_dp = \
            pages_with_texts[message_pages], updated_data_usual_dp[9]

        # обновляем основной список
        updated_data_usual_dp[2], updated_data_usual_dp[5], updated_data_usual_dp[8] = \
            str_clock, pages_with_texts, out_come_text_mes

    # если ничего не изменилось
    else:
        out_come_text_mes, full_kb_dp = \
            updated_data_usual_dp[8], updated_data_usual_dp[9]

    return out_come_text_mes, full_kb_dp, updated_data_usual_dp
