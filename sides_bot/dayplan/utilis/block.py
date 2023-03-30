import copy
import datetime
from collections import OrderedDict
#
from utilis.consts_common import emoji_work_dp_list, \
    dict_special_numbers_circle
from utilis.main_common import big_replacing, get_datetime_from_str, \
    row_buttons, get_button
#
from sides_bot.dayplan.utilis.main import get_first_work_index
from sides_bot.dayplan.utilis.charts import get_dynamic_dp_photo


def get_first_work_emoji(huge_list):
    for one_elem in huge_list:
        if one_elem[1] not in emoji_work_dp_list:
            return one_elem[1]


def get_indexes_elements_from_no_emoji_list(remake_huge_list,
                                            use_this_index_as_first, action) -> list:
    action_with_element = 1 if action == 'down_element' else -1
    indexes_no_emoji = []
    while True:

        if remake_huge_list[use_this_index_as_first][1] in emoji_work_dp_list:
            indexes_no_emoji.append(use_this_index_as_first)

            if not use_this_index_as_first or use_this_index_as_first == len(remake_huge_list) - 1:
                break
        else:
            break

        use_this_index_as_first += action_with_element

    return indexes_no_emoji


def get_indexes_current_part_block(last_emoji, with_index_emoji, huge_list,
                                   use_this_index_as_first=None, get_full_indexes_parts=None,
                                   action=None):
    # если last_emoji is NOT None, ищем индексы по эмоджи,
    # иначе - находим индексы первого эмоджи
    indexes_emoji = with_index_emoji.get(last_emoji) if last_emoji \
                else tuple(with_index_emoji.values())[0]

    # если следующий эмоджи или звезда, или снежинка
    if not indexes_emoji and action:
        indexes_emoji = \
            get_indexes_elements_from_no_emoji_list(huge_list, use_this_index_as_first, action)

    if indexes_emoji:

        index_el = use_this_index_as_first if use_this_index_as_first \
            else get_first_work_index(huge_list, indexes_emoji)

        if len(indexes_emoji) == 1:
            return indexes_emoji

        else:

            # находим каждые непоследовательные части блока
            every_part_of_block = [[]]
            for this_index, one_ind in enumerate(indexes_emoji):

                every_part_of_block[-1].append(one_ind)

                # если разница между двумя идущими подряд идексами > 1, то это другая часть блока
                if one_ind != indexes_emoji[-1] and indexes_emoji[this_index + 1] - one_ind > 1:

                    # если наш индекс в отработанной части блока
                    if not get_full_indexes_parts:
                        if index_el in every_part_of_block[-1]: return every_part_of_block[-1]

                    every_part_of_block.append([])

            # если return ещё не сработал, то наш индекс в последней части блока или его нет
            if not get_full_indexes_parts:
                if index_el in every_part_of_block[-1]: return every_part_of_block[-1]
            else:
                return every_part_of_block


def condition_existing_live_elem_block(huge_list, cold_block):
    # эмоджи первого НЕ выполненного эвента
    existing_emoji = get_first_work_emoji(huge_list)

    # если нет НЕ выполненных | НЕ замороженных
    if not existing_emoji:
        if cold_block:
            # определяем первый замороженный блок
            unexpected_sun_emoji = next(iter(cold_block))

            # возвращаем родное эмоджи
            for index_DP in cold_block.pop(unexpected_sun_emoji):
                huge_list[index_DP][1] = unexpected_sun_emoji

            existing_emoji = get_first_work_emoji(huge_list)

    return existing_emoji, \
           huge_list, cold_block


def run_time_block(our_part_of_block, cl_ev_for_block, index_this_elem):

    # в блоке был только 1 эвент
    if not our_part_of_block:
        our_part_of_block = [index_this_elem]

    if cl_ev_for_block:
        if indexes_emoji := our_part_of_block:
            # сначала находим значение у дикта - индексы N-емоджи, где ключ - last_emoji
            for index in indexes_emoji:
                # смотрим каждый индекс элементов c данным эмоджи в cl_ev_for_block
                if timing := cl_ev_for_block.get(index):
                    # находим значение из cl_ev_for_block, где ключ индекс из indexes
                    return timing


def get_time_all_parts_block(all_time_DP, last_emoji):
    # всё время из частей блоков плюсуем
    plus_time_work_block = 0
    for one_value_emoji in all_time_DP:
        if done_events := one_value_emoji.get(last_emoji):
            for one_done_event in done_events:
                if type(one_done_event[-1]) is dict:
                    for start_block, end_block in one_done_event[-1].items():
                        start_block = get_datetime_from_str(start_block)
                        end_block = get_datetime_from_str(end_block)
                        plus_time_work_block += (end_block - start_block).total_seconds()

    return plus_time_work_block


def minus_all_freeze_block(huge_list, cold_block, with_deep_copy=False):

    # глубоко копируем элементы
    if with_deep_copy:
        cold_block = copy.deepcopy(cold_block)
        huge_list = copy.deepcopy(huge_list)

    for value_one_block in cold_block.items():
        sun_emoji = value_one_block[0]
        for index_DP in value_one_block[1]:
            huge_list[index_DP][1] = sun_emoji

    return huge_list


def get_time_block(updated_data_get_time_block,
                   huge_list, clock_event,
                   clock_block, last_emoji, our_part_of_block,
                   cold_block, cl_ev_for_block, with_index_emoji,
                   end_last_time_event, all_time_DP, work_with_index_emoji,
                   cold_event, progress_block, plus_time_work_block, index_this_elem,
                   stb_block, recast_part_block=False):

    # None | изменение huge_list | изменение времени эвента
    if not updated_data_get_time_block \
            or updated_data_get_time_block[0] != huge_list \
            or updated_data_get_time_block[1] != clock_event:

        # проверка на живой элемент + время блока
        existing_emoji, huge_list, cold_block = \
            condition_existing_live_elem_block(huge_list, cold_block)

        # запуск времени блока
        if not clock_block:
            # если time данного блока уже есть, иначе - None
            clock_block = run_time_block(our_part_of_block, cl_ev_for_block, index_this_elem)

        # конец времени блока и обновление эмоджи
        if existing_emoji:

            if existing_emoji != last_emoji \
                    or recast_part_block:

                # если время блока уже идёт
                if clock_block:
                    if end_last_time_event:
                        this_block_time = (clock_block, end_last_time_event)
                        all_time_DP[-1][last_emoji].append(this_block_time)
                        clock_block = None
                        cold_event = []

                last_emoji = existing_emoji
                progress_block = len(with_index_emoji.get(last_emoji))
                plus_time_work_block = get_time_all_parts_block(all_time_DP, last_emoji)
                our_part_of_block = get_indexes_current_part_block(last_emoji,
                                                                   with_index_emoji, huge_list)
                stb_block = 0

        # yet_done - разность всех эвентов данного эмоджи (в том числе выполненных) и НЕ выполненных элементов эмоджи
        yet_done = len(with_index_emoji.get(last_emoji)) - len(work_with_index_emoji.get(last_emoji))
        updated_data_get_time_block = (huge_list, clock_event,
                                       existing_emoji, yet_done)

    return updated_data_get_time_block, \
           clock_block, cold_block, \
           huge_list, \
           progress_block, last_emoji, \
           our_part_of_block, \
           plus_time_work_block, all_time_DP, \
           cold_event, stb_block


def get_full_block_values(updated_data_block_values,
                          huge_list, last_page,
                          last_emoji, cold_event,
                          clock_event, clock_block,
                          str_clock, yet_done,
                          progress_block):
    # условие изменения текста и кб
    condition_update_text_or_kb = not updated_data_block_values \
                                  or updated_data_block_values[0] != huge_list \
                                  or updated_data_block_values[1] != str_clock \
                                  or updated_data_block_values[3] != last_page \
                                  or updated_data_block_values[4] != clock_event

    # условия изменения строк
    if not updated_data_block_values \
            or updated_data_block_values[0] != huge_list:

        # определяем начальное сообщение и отступы
        elements_block = f"<b>THE BLOCK</b>\n\t🕒{str_clock}🕘\n" \
                         f"❮➖<b>{yet_done}/{progress_block}</b>➖❯\n\n"

        # получаем из huge_list только те имена элементов с индексами,
        # где emoji == last_emoji
        name_events_this_emoji = [one_elem[0][0] for one_elem in huge_list if one_elem[1] == last_emoji]

        # объединяем начальное сообщение и отдельные имена эвентов блока
        elements_block += "".join([
            f'\t{big_replacing(one_ind+1, your_dict=dict_special_numbers_circle)} | {name_elem}\n{last_emoji}\n'
            for one_ind, name_elem in enumerate(name_events_this_emoji)])

    # изменилось только время
    elif updated_data_block_values[1] != str_clock:
        elements_block = updated_data_block_values[2] = \
            updated_data_block_values[2].replace(updated_data_block_values[1], str_clock, 1)

    else:
        elements_block = updated_data_block_values[2]

    # условия изменения КБ
    if not updated_data_block_values \
            or updated_data_block_values[0] != huge_list \
            or updated_data_block_values[3] != last_page \
            or updated_data_block_values[4] != clock_event:

        # разбираемся с callbacks кнопок
        last_page = last_page if last_page \
            else 1
        callback_for_event = 'in_doing_event' if clock_event \
            else 'seeing_one_element'

        # кнопка заморозки
        need_kb = None
        # clock_block is None, cold_event is None, данный эмоджи - не последний эмоджи
        if not clock_block and not cold_event \
                and len(OrderedDict.fromkeys([one_elem[1] for one_elem in huge_list if one_elem[1] != '⭐'])) != 1:
            need_kb = row_buttons(get_button('❄️', callback_data='block_snow'))

        need_kb = row_buttons(
            get_button('◁', callback_data=f'{last_page}_xDP'),
            get_button('▷', callback_data=f'{callback_for_event}'), your_kb=need_kb)

    else:
        need_kb = updated_data_block_values[5]

    updated_data_block_values = \
        [huge_list, str_clock, elements_block, last_page, clock_event, need_kb]

    return updated_data_block_values, elements_block, need_kb, \
           condition_update_text_or_kb
