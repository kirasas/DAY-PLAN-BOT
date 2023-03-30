import math
import warnings
import matplotlib.pyplot as plt
from multiprocessing import Process
import matplotlib.animation as animation
#
from utilis.main_common import get_datetime_from_str
#
from sides_bot.dayplan.utilis.main import save_data_process_dp


# GENERATION OF DATA
def get_ready_labels_and_sizes(dict_with_time, block_names_dict):
    # определяем размеры и их процентное соотношение
    sizes = list(dict_with_time.values())
    percent_sizes = [one_num * 100 / (sum(sizes) if sum(sizes) else 1)
                     for one_num in sizes]

    # создаём ярлыки с процентами
    labels = [f'{block_names_dict.get(one_emoji)} | {percent_sizes[one_ind]:.1f}%'
              for one_ind, one_emoji in enumerate(dict_with_time.keys())]

    return labels, sizes


def get_data_for_area_graph(all_time_dp, block_colours_dict, block_names_dict,
                            the_end_dp=False, first_time_dp=None):
    all_positions = [['USELESS TIME', 0, 0, 'FFFFFF', 'USELESS TIME']]
    number_event = index_before_begin_block = useful_delta = 0

    # есть хотя бы один начатый блок
    if type(all_time_dp[0]) is dict:

        # если стопа НЕ было до начала первого блока
        if tuple(all_time_dp[0].keys())[0] != '⛔':
            # получаем разницу начала ДП и начала первого блока (время до начала первого блока)
            common_delta_time = \
                round((get_datetime_from_str(tuple(all_time_dp[0].values())[0][0][1][0]) -
                       get_datetime_from_str(all_time_dp[-1][0] if the_end_dp else first_time_dp)).total_seconds()
                      / 60, 3)
            all_positions.append(['BEFORE_START_FIRST_BLOCK', number_event, common_delta_time, 'FFFFFF', 'BL---BL'])

        else:

            # время с начала ДП до начала стопа
            begin_dp_part = \
                get_datetime_from_str(all_time_dp[-1][0] if the_end_dp else first_time_dp)
            end_dp_part = \
                get_datetime_from_str(tuple(all_time_dp[0].values())[0][0])

            common_delta_time = round(
                (end_dp_part - begin_dp_part).total_seconds() / 60, 3)
            all_positions.append(['BEFORE_START_FIRST_BLOCK',
                                  number_event, common_delta_time,
                                  'FFFFFF',
                                  'BL---BL'])

            # срез со всеми стопами ДО начала первого блока
            indexes_active = \
                [one_ind for one_ind, one_elem in enumerate(all_time_dp[:-1] if the_end_dp else all_time_dp)
                 for one_emoji, _ in one_elem.items()
                 if one_emoji != '⛔']

            # то есть только одни стопы
            if not indexes_active:

                # рассматриваем каждый стоп
                for stop_ind, one_stop_before_bl in enumerate(all_time_dp[:-1] if the_end_dp else all_time_dp):

                    # рассматриваем только время стопа
                    for one_values_stop in one_stop_before_bl.values():
                        # находим дельту стопа
                        begin_time_stop = \
                            get_datetime_from_str(one_values_stop[0])
                        end_time_stop = \
                            get_datetime_from_str(one_values_stop[1])

                        common_delta_time = round(
                            (end_time_stop - begin_time_stop).total_seconds() / 60 + common_delta_time, 3)
                        all_positions.append(['STOP---STOP', number_event, common_delta_time,
                                              'C10020', 'STOP---STOP'])

                        # дельта между концом стопа и (началом нового стопа | началом блока):
                        # WAIT TIME - STOP TIME - WAIT TIME - BLOCK TIME BEGIN...
                        begin_event_part = end_time_stop
                        end_event_part = \
                            get_datetime_from_str(
                                all_time_dp[stop_ind + 1].get('⛔')[0]
                                if stop_ind < len(all_time_dp[:-1]) - 1  # begin_next_stop if not last
                                else all_time_dp[stop_ind + 1][1])  # end_time_dp

                        common_delta_time = round(
                            (end_event_part - begin_event_part).total_seconds() / 60 + common_delta_time, 3)
                        all_positions.append(['BEFORE_START_FIRST_BLOCK',
                                              number_event, common_delta_time,
                                              'FFFFFF',
                                              'BL---BL'])

                # находим дельту стопа
                begin_time_stop, end_time_stop = tuple(all_time_dp[0].values())[0]

                common_delta_time = round(
                    (get_datetime_from_str(end_time_stop) - get_datetime_from_str(begin_time_stop)).total_seconds()
                    / 60 + common_delta_time, 3)
                all_positions.append(['STOP---STOP', number_event, common_delta_time,
                                      'C10020', 'STOP---STOP'])

            else:

                # срез со всеми стопами ДО начала первого блока
                index_before_begin_block = indexes_active[0]

                # рассматриваем каждый стоп
                for stop_ind, one_stop_before_bl in enumerate(all_time_dp[:index_before_begin_block]):

                    # рассматриваем только время стопа
                    for one_values_stop in one_stop_before_bl.values():
                        # находим дельту стопа
                        begin_time_stop = \
                            get_datetime_from_str(one_values_stop[0])
                        end_time_stop = \
                            get_datetime_from_str(one_values_stop[1])

                        common_delta_time = round(
                            (end_time_stop - begin_time_stop).total_seconds() / 60 + common_delta_time, 3)
                        all_positions.append(['STOP---STOP', number_event, common_delta_time,
                                              'C10020', 'STOP---STOP'])

                        if stop_ind != len(all_time_dp)-1:

                            # дельта между концом стопа и (началом нового стопа | началом блока):
                            # WAIT TIME - STOP TIME - WAIT TIME - BLOCK TIME BEGIN...
                            begin_event_part = end_time_stop
                            end_event_part = \
                                get_datetime_from_str(
                                    all_time_dp[stop_ind + 1].get('⛔')[0]
                                    if stop_ind < len(
                                        all_time_dp[:index_before_begin_block]) - 1  # begin_next_stop if not last
                                    else tuple(all_time_dp[stop_ind + 1].values())[0][-1][0])  # begin_first_block

                            common_delta_time = round(
                                (end_event_part - begin_event_part).total_seconds() / 60 + common_delta_time, 3)
                            all_positions.append(['BEFORE_START_FIRST_BLOCK',
                                                  number_event, common_delta_time,
                                                  'FFFFFF',
                                                  'BL---BL'])

                return all_positions, 0

        # идём по всем элементам
        for index_block, values_one_block in enumerate(all_time_dp[index_before_begin_block:-1]
                                                       if the_end_dp else all_time_dp[index_before_begin_block:]):

            # получаем эмоджи одного блока и его значение
            for one_emoji, values_emoji in values_one_block.items():

                # это НЕ стоп между блоками
                if one_emoji != '⛔':

                    # просматриваем каждое значение блока
                    for index_values_event, values_event in enumerate(values_emoji):

                        # НЕ время блока - last in values_emoji: (begin_time_block, end_time_block)
                        if type(values_event) is not tuple or values_event[0] == '⛔':

                            # это НЕ стоп между эвентами
                            if values_event[0] != '⛔':

                                number_event += 1
                                # НЕТ стопов во время данного эвента
                                if len(values_event) == 2:
                                    bn_t, end_t = values_event[1][0], values_event[1][1]

                                    one_delta = round(
                                        (get_datetime_from_str(end_t) -
                                         get_datetime_from_str(bn_t)).total_seconds() / 60, 3)

                                    useful_delta += one_delta
                                    common_delta_time = round(common_delta_time + one_delta, 3)

                                    all_positions.append([values_event[0], number_event, common_delta_time,
                                                          block_colours_dict.get(one_emoji),
                                                          block_names_dict.get(one_emoji)])

                                else:

                                    # время с начала эвента до начала стопа
                                    begin_event_part = \
                                        get_datetime_from_str(values_event[-1][0])
                                    end_event_part = \
                                        get_datetime_from_str(values_event[1][1])

                                    one_delta = (end_event_part - begin_event_part).total_seconds() / 60

                                    useful_delta += one_delta
                                    common_delta_time = round(one_delta + common_delta_time, 3)

                                    all_positions.append([values_event[0], number_event, common_delta_time,
                                                          block_colours_dict.get(one_emoji),
                                                          block_names_dict.get(one_emoji)])

                                    # рассматриваем каждый стоп
                                    only_stops = values_event[1:-1]
                                    for stop_ind, one_event_stop in enumerate(only_stops):
                                        # находим дельту стопа
                                        begin_time_stop = \
                                            get_datetime_from_str(one_event_stop[1])
                                        end_time_stop = \
                                            get_datetime_from_str(one_event_stop[2])

                                        common_delta_time = round(
                                            (end_time_stop - begin_time_stop).total_seconds() / 60
                                            + common_delta_time, 3)
                                        all_positions.append(['STOP---STOP', number_event, common_delta_time,
                                                              'C10020', 'STOP---STOP'])

                                        # дельта между концом стопа и (началом нового стопа | концом эвента):
                                        # рабочее время эвента между его нерабочим временем
                                        begin_event_part = end_time_stop
                                        end_event_part = \
                                            get_datetime_from_str(
                                                only_stops[stop_ind + 1][1]
                                                if stop_ind != len(only_stops) - 1  # begin_next_stop if not last
                                                else values_event[-1][1])  # end_time_event

                                        one_delta = (end_event_part - begin_event_part).total_seconds() / 60
                                        useful_delta += one_delta
                                        common_delta_time = round(one_delta + common_delta_time, 3)

                                        all_positions.append([values_event[0], number_event, common_delta_time,
                                                              block_colours_dict.get(one_emoji),
                                                              block_names_dict.get(one_emoji)])

                            else:
                                begin_time_stop = \
                                    get_datetime_from_str(values_event[1][0])
                                end_time_stop = \
                                    get_datetime_from_str(values_event[1][1])

                                common_delta_time = round(
                                    (end_time_stop - begin_time_stop).total_seconds() / 60 + common_delta_time, 3)

                                all_positions.append(['STOP---STOP', number_event, common_delta_time,
                                                      'C10020', 'STOP---STOP'])

                        # учитываем разницу времени между началом следующего блока и концом данного
                        else:

                            # НЕ последний эвент
                            if index_block < len(all_time_dp) - (2 if the_end_dp else 1) - index_before_begin_block:

                                for future_block_emoji, future_block_values in \
                                        all_time_dp[index_block + 1 + index_before_begin_block].items():
                                    begin_time_next_block = \
                                        get_datetime_from_str(future_block_values[-1][0] if future_block_emoji != '⛔'
                                                              else future_block_values[0])
                                    end_time_this_block = \
                                        get_datetime_from_str(values_event[1])

                                    common_delta_time = round(
                                        (begin_time_next_block -
                                         end_time_this_block).total_seconds() / 60 + common_delta_time, 3)

                                    all_positions.append(['BL---BL', number_event, common_delta_time,
                                                          'FFFFFF', 'BL---BL'])

                        # учитываем разницу между эвентами
                        # НЕ последний и НЕ предпоследний элемент (НЕ последний эвент и НЕ время блока)
                        if index_values_event not in (len(values_emoji) - 1, len(values_emoji) - 2):
                            common_delta_time = round(
                                (get_datetime_from_str(values_emoji[index_values_event + 1][-1][0]) -
                                 get_datetime_from_str(values_event[-1][1])).total_seconds() / 60
                                + common_delta_time, 3)

                            all_positions.append(['EV---EV', number_event, common_delta_time,
                                                  'FFFFFF', block_names_dict.get(one_emoji)])
                else:

                    # сначала стоп
                    begin_time_stop = \
                        get_datetime_from_str(values_emoji[0])
                    end_time_stop = \
                        get_datetime_from_str(values_emoji[1])

                    common_delta_time = round(
                        (end_time_stop - begin_time_stop).total_seconds() / 60 + common_delta_time, 3)

                    all_positions.append(['STOP---STOP', number_event, common_delta_time,
                                          'C10020', 'STOP---STOP'])

                    # потом - разница между концом данного блока и началом следующего
                    if index_block < len(all_time_dp) - (2 if the_end_dp else 1) - index_before_begin_block:

                        for future_block_emoji, future_block_values in \
                                all_time_dp[index_block + 1 + index_before_begin_block].items():
                            begin_time_next_block = \
                                get_datetime_from_str(future_block_values[-1][0] if future_block_emoji != '⛔'
                                                      else future_block_values[0])
                            end_time_this_block = end_time_stop

                            common_delta_time = round(
                                (begin_time_next_block -
                                 end_time_this_block).total_seconds() / 60 + common_delta_time, 3)

                            all_positions.append(['BL---BL', number_event, common_delta_time,
                                                  'FFFFFF', 'BL---BL'])

    else:

        # получаем всё время работы
        common_delta_time = \
            round((get_datetime_from_str(all_time_dp[-1][1]) -
                   get_datetime_from_str(all_time_dp[-1][0])).total_seconds()
                  / 60, 3)
        all_positions.append(['BEFORE_START_FIRST_BLOCK', number_event, common_delta_time, 'FFFFFF', 'BL---BL'])

    return all_positions, round(useful_delta / common_delta_time * 100, 1)


def get_data_for_circle_graph(all_time_dp, block_colours_dict, block_names_dict,
                              the_end_dp=False, first_time_dp=None):
    dict_with_time = {}
    all_positions = []
    index_before_begin_block = 0

    block_names_dict['USELESS_TIME'] = 'USELESS_TIME'
    block_colours_dict['USELESS_TIME'] = 'FFFFFF'
    block_names_dict['⛔'] = 'STOP---STOP'
    block_colours_dict['⛔'] = 'C10020'

    # есть хотя бы один начатый блок
    if type(all_time_dp[0]) is dict:

        # если стопа НЕ было до начала первого блока
        if tuple(all_time_dp[0].keys())[0] != '⛔':
            # получаем разницу начала ДП и начала первого блока (время до начала первого блока)
            common_delta_time = \
                round((get_datetime_from_str(tuple(all_time_dp[0].values())[0][0][1][0]) -
                       get_datetime_from_str(all_time_dp[-1][0] if the_end_dp else first_time_dp)).total_seconds()
                      / 60, 3)
            dict_with_time.update(USELESS_TIME=common_delta_time)
            all_positions.append([['USELESS_TIME | 100%'], [common_delta_time], ['#FFFFFF'],
                                  'USELESS_TIME', 'BEFORE_START_FIRST_BLOCK'])

        else:

            # время с начала ДП до начала стопа
            begin_dp_part = \
                get_datetime_from_str(all_time_dp[-1][0] if the_end_dp else first_time_dp)
            end_dp_part = \
                get_datetime_from_str(tuple(all_time_dp[0].values())[0][0])

            common_delta_time = round(
                (end_dp_part - begin_dp_part).total_seconds() / 60, 3)
            dict_with_time.update(USELESS_TIME=common_delta_time)
            all_positions.append([['USELESS_TIME | 100%'], [common_delta_time], ['#FFFFFF'],
                                  'USELESS_TIME', 'BEFORE_START_FIRST_BLOCK'])

            # срез со всеми стопами ДО начала первого блока
            indexes_active = \
                [one_ind for one_ind, one_elem in enumerate(all_time_dp[:-1] if the_end_dp else all_time_dp)
                 for one_emoji, _ in one_elem.items()
                 if one_emoji != '⛔']

            # то есть только одни стопы
            if not indexes_active:

                # рассматриваем каждый стоп
                for stop_ind, one_stop_before_bl in enumerate(all_time_dp[:-1] if the_end_dp else all_time_dp):

                    # рассматриваем только время стопа
                    for one_values_stop in one_stop_before_bl.values():
                        # находим дельту стопа
                        begin_time_stop = \
                            get_datetime_from_str(one_values_stop[0])
                        end_time_stop = \
                            get_datetime_from_str(one_values_stop[1])

                        # обновляем время работы
                        common_delta_time = round(
                            (end_time_stop - begin_time_stop).total_seconds() / 60, 3)
                        dict_with_time['⛔'] = round(dict_with_time.get('⛔', 0) + common_delta_time, 3)

                        # получаем имена и размеры
                        labels, sizes = \
                            get_ready_labels_and_sizes(dict_with_time, block_names_dict)

                        all_positions.append([labels, sizes,
                                              [f'#{block_colours_dict.get(one_emoji)}'
                                               for one_emoji in dict_with_time.keys()],
                                              'STOP---STOP', 'STOP---STOP'])

                        if stop_ind < len(all_time_dp)-1:

                            # дельта между концом стопа и (началом нового стопа | началом блока):
                            # WAIT TIME - STOP TIME - WAIT TIME - BLOCK TIME BEGIN...
                            begin_event_part = end_time_stop
                            end_event_part = \
                                get_datetime_from_str(
                                    all_time_dp[stop_ind + 1].get('⛔')[0]
                                    if stop_ind < len(all_time_dp[:-1]) - 1  # begin_next_stop if not last
                                    else all_time_dp[stop_ind + 1][1])  # end_time_dp

                            common_delta_time = round(
                                (end_event_part - begin_event_part).total_seconds() / 60, 3)

                            dict_with_time['USELESS_TIME'] = \
                                round(dict_with_time.get('USELESS_TIME', 0) + common_delta_time, 3)

                            # получаем имена и размеры
                            labels, sizes = \
                                get_ready_labels_and_sizes(dict_with_time, block_names_dict)

                            all_positions.append([labels, sizes,
                                                  [f'#{block_colours_dict.get(one_emoji)}'
                                                   for one_emoji in dict_with_time.keys()],
                                                  'USELESS_TIME', 'BEFORE_START_FIRST_BLOCK'])

                return all_positions, 0

            else:

                # срез со всеми стопами ДО начала первого блока
                index_before_begin_block = indexes_active[0]

                # рассматриваем каждый стоп
                for stop_ind, one_stop_before_bl in enumerate(all_time_dp[:index_before_begin_block]):

                    # рассматриваем только время стопа
                    for one_values_stop in one_stop_before_bl.values():
                        # находим дельту стопа
                        begin_time_stop = \
                            get_datetime_from_str(one_values_stop[0])
                        end_time_stop = \
                            get_datetime_from_str(one_values_stop[1])

                        # обновляем время работы
                        common_delta_time = round(
                            (end_time_stop - begin_time_stop).total_seconds() / 60, 3)
                        dict_with_time['⛔'] = round(dict_with_time.get('⛔', 0) + common_delta_time, 3)

                        # получаем имена и размеры
                        labels, sizes = \
                            get_ready_labels_and_sizes(dict_with_time, block_names_dict)

                        all_positions.append([labels, sizes,
                                              [f'#{block_colours_dict.get(one_emoji)}'
                                               for one_emoji in dict_with_time.keys()],
                                              'STOP---STOP', 'STOP---STOP'])

                        # дельта между концом стопа и (началом нового стопа | началом блока):
                        # WAIT TIME - STOP TIME - WAIT TIME - BLOCK TIME BEGIN...
                        begin_event_part = end_time_stop
                        end_event_part = \
                            get_datetime_from_str(all_time_dp[stop_ind + 1].get('⛔')[0]
                                                  if stop_ind < len(
                                all_time_dp[:index_before_begin_block]) - 1  # begin_next_stop if not last
                                                  else list(all_time_dp[stop_ind + 1].values())[0][-1][
                                0])  # begin_first_block

                        common_delta_time = round(
                            (end_event_part - begin_event_part).total_seconds() / 60, 3)

                        dict_with_time['USELESS_TIME'] = \
                            round(dict_with_time.get('USELESS_TIME', 0) + common_delta_time, 3)

                        # получаем имена и размеры
                        labels, sizes = \
                            get_ready_labels_and_sizes(dict_with_time, block_names_dict)

                        all_positions.append([labels, sizes,
                                              [f'#{block_colours_dict.get(one_emoji)}'
                                               for one_emoji in dict_with_time.keys()],
                                              'USELESS_TIME', 'BEFORE_START_FIRST_BLOCK'])

        # идём по всем элементам
        for index_block, values_one_block in enumerate(all_time_dp[index_before_begin_block:-1]
                                                       if the_end_dp else all_time_dp[index_before_begin_block:]):

            # получаем эмоджи одного блока и его значение
            for one_emoji, values_emoji in values_one_block.items():

                # это НЕ стоп между блоками
                if one_emoji != '⛔':

                    # просматриваем каждое значение блока
                    for index_values_event, values_event in enumerate(values_emoji):

                        # НЕ время блока - last in values_emoji: (begin_time_block, end_time_block)
                        if type(values_event) is not tuple or values_event[0] == '⛔':

                            # это НЕ стоп между эвентами
                            if values_event[0] != '⛔':

                                # НЕТ стопов во время данного эвента
                                if len(values_event) == 2:
                                    bn_t, end_t = values_event[1][0], values_event[1][1]

                                    common_delta_time = round(
                                        (get_datetime_from_str(end_t) -
                                         get_datetime_from_str(bn_t)).total_seconds() / 60, 3)

                                    dict_with_time[one_emoji] = \
                                        round(dict_with_time.get(one_emoji, 0) + common_delta_time, 3)

                                    # получаем имена и размеры
                                    labels, sizes = \
                                        get_ready_labels_and_sizes(dict_with_time, block_names_dict)

                                    all_positions.append([labels, sizes,
                                                          [f'#{block_colours_dict.get(one_emoji)}' for one_emoji in
                                                           dict_with_time.keys()],
                                                          block_names_dict.get(one_emoji),
                                                          values_event[0]])

                                else:

                                    # время с начала эвента до начала стопа
                                    begin_event_part = \
                                        get_datetime_from_str(values_event[-1][0])
                                    end_event_part = \
                                        get_datetime_from_str(values_event[1][1])

                                    common_delta_time = round(
                                        (end_event_part - begin_event_part).total_seconds() / 60, 3)

                                    dict_with_time[one_emoji] = \
                                        round(dict_with_time.get(one_emoji, 0) + common_delta_time, 3)

                                    # получаем имена и размеры
                                    labels, sizes = \
                                        get_ready_labels_and_sizes(dict_with_time, block_names_dict)

                                    all_positions.append([labels, sizes,
                                                          [f'#{block_colours_dict.get(one_emoji)}' for one_emoji in
                                                           dict_with_time.keys()],
                                                          block_names_dict.get(one_emoji),
                                                          values_event[0]])

                                    # рассматриваем каждый стоп
                                    only_stops = values_event[1:-1]
                                    for stop_ind, one_event_stop in enumerate(only_stops):
                                        # находим дельту стопа
                                        begin_time_stop = \
                                            get_datetime_from_str(one_event_stop[1])
                                        end_time_stop = \
                                            get_datetime_from_str(one_event_stop[2])

                                        common_delta_time = round(
                                            (end_time_stop - begin_time_stop).total_seconds() / 60, 3)

                                        dict_with_time['⛔'] = \
                                            round(dict_with_time.get('⛔', 0) + common_delta_time, 3)

                                        # получаем имена и размеры
                                        labels, sizes = \
                                            get_ready_labels_and_sizes(dict_with_time, block_names_dict)

                                        all_positions.append([labels, sizes,
                                                              [f'#{block_colours_dict.get(one_emoji)}' for one_emoji in
                                                               dict_with_time.keys()],
                                                              'STOP---STOP', 'STOP---STOP'])

                                        # дельта между концом стопа и (началом нового стопа | концом эвента):
                                        # рабочее время эвента между его нерабочим временем
                                        begin_event_part = end_time_stop
                                        end_event_part = \
                                            get_datetime_from_str(
                                                only_stops[stop_ind + 1][1]
                                                if stop_ind < len(only_stops) - 1  # begin_next_stop if not last
                                                else values_event[-1][1])  # end_time_event

                                        common_delta_time = round(
                                            (end_event_part - begin_event_part).total_seconds() / 60, 3)

                                        dict_with_time[one_emoji] = \
                                            round(dict_with_time.get(one_emoji, 0) + common_delta_time, 3)

                                        # получаем имена и размеры
                                        labels, sizes = \
                                            get_ready_labels_and_sizes(dict_with_time, block_names_dict)

                                        all_positions.append([labels, sizes,
                                                              [f'#{block_colours_dict.get(one_emoji)}' for one_emoji in
                                                               dict_with_time.keys()],
                                                              block_names_dict.get(one_emoji),
                                                              values_event[0]])

                            else:
                                begin_time_stop = \
                                    get_datetime_from_str(values_event[1][0])
                                end_time_stop = \
                                    get_datetime_from_str(values_event[1][1])

                                common_delta_time = round(
                                    (end_time_stop - begin_time_stop).total_seconds() / 60, 3)

                                dict_with_time['⛔'] = \
                                    round(dict_with_time.get('⛔', 0) + common_delta_time, 3)

                                # получаем имена и размеры
                                labels, sizes = \
                                    get_ready_labels_and_sizes(dict_with_time, block_names_dict)

                                all_positions.append([labels, sizes,
                                                      [f'#{block_colours_dict.get(one_emoji)}' for one_emoji in
                                                       dict_with_time.keys()],
                                                      'STOP---STOP', 'STOP---STOP'])

                        # учитываем разницу времени между началом следующего блока и концом данного
                        else:

                            # НЕ последний эвент
                            if index_block < len(all_time_dp) - (2 if the_end_dp else 1) - index_before_begin_block:

                                for future_block_emoji, future_block_values in \
                                        all_time_dp[index_block + 1 + index_before_begin_block].items():
                                    begin_time_next_block = \
                                        get_datetime_from_str(future_block_values[-1][0] if future_block_emoji != '⛔'
                                                              else future_block_values[0])
                                    end_time_this_block = \
                                        get_datetime_from_str(values_event[1])

                                    common_delta_time = round(
                                        (begin_time_next_block -
                                         end_time_this_block).total_seconds() / 60, 3)

                                    dict_with_time['USELESS_TIME'] = \
                                        round(dict_with_time.get('USELESS_TIME', 0) + common_delta_time, 3)

                                    # получаем имена и размеры
                                    labels, sizes = \
                                        get_ready_labels_and_sizes(dict_with_time, block_names_dict)

                                    all_positions.append([labels, sizes,
                                                          [f'#{block_colours_dict.get(one_emoji)}' for one_emoji in
                                                           dict_with_time.keys()],
                                                          'USELESS_TIME', 'BL---BL'])

                        # учитываем разницу между эвентами
                        # НЕ последний и НЕ предпоследний элемент (НЕ последний эвент и НЕ время блока)
                        if index_values_event not in (len(values_emoji) - 1, len(values_emoji) - 2):
                            common_delta_time = round(
                                (get_datetime_from_str(values_emoji[index_values_event + 1][-1][0]) -
                                 get_datetime_from_str(values_event[-1][1])).total_seconds() / 60, 3)

                            dict_with_time['USELESS_TIME'] = \
                                round(dict_with_time.get('USELESS_TIME', 0) + common_delta_time, 3)

                            # получаем имена и размеры
                            labels, sizes = \
                                get_ready_labels_and_sizes(dict_with_time, block_names_dict)

                            all_positions.append([labels, sizes,
                                                  [f'#{block_colours_dict.get(one_emoji)}' for one_emoji in
                                                   dict_with_time.keys()],
                                                  'USELESS_TIME', 'EV---EV'])
                else:

                    # сначала стоп
                    begin_time_stop = \
                        get_datetime_from_str(values_emoji[0])
                    end_time_stop = \
                        get_datetime_from_str(values_emoji[1])

                    common_delta_time = round(
                        (end_time_stop - begin_time_stop).total_seconds() / 60, 3)

                    dict_with_time['⛔'] = round(dict_with_time.get('⛔', 0) + common_delta_time, 3)

                    # получаем имена и размеры
                    labels, sizes = \
                        get_ready_labels_and_sizes(dict_with_time, block_names_dict)

                    all_positions.append([labels, sizes,
                                          [f'#{block_colours_dict.get(one_emoji)}'
                                           for one_emoji in dict_with_time.keys()],
                                          'STOP---STOP', 'STOP---STOP'])

                    # потом - разница между концом данного блока и началом следующего
                    if index_block < len(all_time_dp) - (2 if the_end_dp else 1) - index_before_begin_block:

                        for future_block_emoji, future_block_values in \
                                all_time_dp[index_block + 1 + index_before_begin_block].items():
                            begin_time_next_block = \
                                get_datetime_from_str(future_block_values[-1][0] if future_block_emoji != '⛔'
                                                      else future_block_values[0])
                            end_time_this_block = end_time_stop

                            common_delta_time = round(
                                (begin_time_next_block -
                                 end_time_this_block).total_seconds() / 60, 3)

                            dict_with_time['USELESS_TIME'] = \
                                round(dict_with_time.get('USELESS_TIME', 0) + common_delta_time, 3)

                            # получаем имена и размеры
                            labels, sizes = \
                                get_ready_labels_and_sizes(dict_with_time, block_names_dict)

                            all_positions.append([labels, sizes,
                                                  [f'#{block_colours_dict.get(one_emoji)}' for one_emoji in
                                                   dict_with_time.keys()],
                                                  'USELESS_TIME', 'BL---BL'])

        useful_delta = round(
            sum(one_time for block, one_time in dict_with_time.items()
                if block not in ('USELESS_TIME', 'STOP---STOP')) /
            sum(one_time for one_time in dict_with_time.values()) * 100, 1)

    else:
        # получаем всё время работы
        common_delta_time = \
            round((get_datetime_from_str(all_time_dp[-1][1]) -
                   get_datetime_from_str(all_time_dp[-1][0])).total_seconds()
                  / 60, 3)
        dict_with_time.update(USELESS_TIME=common_delta_time)
        all_positions.append([['USELESS_TIME | 100%'], [common_delta_time], ['#FFFFFF'], 'USELESS_TIME',
                              'BEFORE_START_FIRST_BLOCK'])
        useful_delta = 0

    return all_positions, useful_delta


# PHOTO DP
def create_area_dp_photo(data_time_dp, save_path, name_photo):

    first_fig, ax_first = plt.subplots()

    # цвета фонов
    first_fig.set(facecolor='white')
    ax_first.set(facecolor='black')

    # заголовок
    ax_first.set_title('ДИНАМИКА РАБОТЫ',
                       fontfamily='fantasy',
                       size=25,
                       color='black')

    # для x и y осей подписи
    ax_first.set_xlabel('МИНУТЫ',
                        fontfamily='monospace', size=16, fontstyle='normal')
    ax_first.set_ylabel('ЭВЕНТЫ',
                        fontfamily='monospace', size=16, fontstyle='normal')

    # устанавливаем главную сетку
    ax_first.grid(which='major',
                  color='grey',
                  linewidth=1)

    # устанавливаем побочную сетку
    ax_first.grid(which='minor',
                  color='grey',
                  linestyle=':')

    # first string to legend
    ax_first.fill_between((0, 0.01), (0, 0.01),
                          color=f'#{data_time_dp[0][3]}',
                          linewidth=2,
                          label=data_time_dp[0][4])

    not_in_list = ['EV---EV', 'BL---BL']
    for index_frame, one_data in enumerate(data_time_dp):
        if index_frame:
            ax_first.fill_between(
                (data_time_dp[index_frame - 1][2], one_data[2]),
                (str(data_time_dp[index_frame - 1][1]), str(one_data[1])),
                color=f'#{one_data[3]}', linestyle='-',
                linewidth=2,
                label=one_data[4] if one_data[4] not in not_in_list else None)
            not_in_list.append(one_data[4])

    # устанавливаем легенду
    ax_first.legend(fontsize=7 - math.floor(len(ax_first.get_legend_handles_labels()[1])/10),
                    ncol=2,
                    loc='upper left')

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        first_fig.savefig(f'{save_path}/{name_photo}.jpg')


def create_circle_dp_photo(data_time_dp, save_path, name_photo):

    first_fig, ax_first = plt.subplots()
    first_fig.set(facecolor='black')
    ax_first.set_aspect('equal')

    labels, sizes, colors, *_ = \
        data_time_dp[-1]
    last_index = len(data_time_dp) - 1

    ax_first.set_title(f'ДИНАМИКА РАБОТЫ',
                       fontfamily='fantasy',
                       size=25,
                       color='white')

    one_cadre = \
        ax_first.pie(sizes,
                     radius=1 + last_index / 5000 if last_index < 100 else 1.02,
                     wedgeprops=dict(width=1 - last_index / 100 if last_index < 100 else 0.2,
                                     edgecolor='w'), colors=colors)

    # находим wedges и приципляем к ним имена
    ax_first.legend(one_cadre[0], labels,
                    title='BLOCKS',
                    loc="right",
                    bbox_to_anchor=(0, 0, 0.0505, 1.7-0.025*len(labels)),
                    fontsize=5.5)

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        first_fig.savefig(f'{save_path}/{name_photo}.jpg')


def get_dynamic_dp_photo(all_time_dp,
                         block_colours_dict, block_names_dict,
                         the_end_dp=False, first_time_dp=None,
                         get_area_graph=True, use_stream=False,
                         save_path='', name_photo='dp_dynamic_photo') -> int:
    # требуется график линии
    if get_area_graph:

        data_for_photo, useful_delta = get_data_for_area_graph(all_time_dp,
                                                               block_colours_dict, block_names_dict,
                                                               the_end_dp=the_end_dp, first_time_dp=first_time_dp)

        if use_stream:
            stream_photo = Process(target=create_area_dp_photo,
                                   args=(data_for_photo, save_path, name_photo, useful_delta))
            stream_photo.start()
        else:
            create_area_dp_photo(data_for_photo, save_path, name_photo)

    # круговой график
    else:

        data_for_photo, useful_delta = get_data_for_circle_graph(all_time_dp,
                                                                 block_colours_dict, block_names_dict,
                                                                 the_end_dp=the_end_dp, first_time_dp=first_time_dp)

        if use_stream:
            stream_photo = Process(target=create_circle_dp_photo,
                                   args=(data_for_photo, save_path, name_photo, useful_delta))
            stream_photo.start()
        else:
            create_circle_dp_photo(data_for_photo, save_path, name_photo)

    return useful_delta


# ANIMATION DP
def create_area_dp_anim(data_time_dp, save_path, user_id):
    first_fig, ax_first = plt.subplots()

    def init_graph():

        # цвета фона
        ax_first.set(facecolor='black')

        # заголовок
        ax_first.set_title('ДИНАМИКА РАБОТЫ',
                           fontfamily='fantasy',
                           size=25,
                           color='black')

        # для x и y осей подписи
        ax_first.set_xlabel('МИНУТЫ',
                            fontfamily='monospace', size=16, fontstyle='normal')
        ax_first.set_ylabel('ЭВЕНТЫ',
                            fontfamily='monospace', size=16, fontstyle='normal')

        # устанавливаем главную сетку
        ax_first.grid(which='major',
                      color='grey',
                      linewidth=1)

        # устанавливаем побочную сетку
        ax_first.grid(which='minor',
                      color='grey',
                      linestyle=':')

        return []

    # функция анимации
    def animate_dp(index_frame):

        # последний кадр
        if index_frame == len(data_time_dp):
            # обновляем данный блок, эвент
            ax_first.set_title(f'ДИНАМИКА РАБОТЫ',
                               fontfamily='fantasy',
                               size=25,
                               color='black')

        # ну нулевой кадр
        elif index_frame:

            # обновляем данный блок, эвент
            ax_first.set_title(f'BLOCK {data_time_dp[index_frame][4]}'
                               f'\nEVENT {data_time_dp[index_frame][0]}',
                               fontfamily='fantasy',
                               size=16,
                               color='black')

            # area на график
            add_element = \
                (ax_first.fill_between(
                    (data_time_dp[index_frame - 1][2], data_time_dp[index_frame][2]),
                    (str(data_time_dp[index_frame - 1][1]), str(data_time_dp[index_frame][1])),
                    color=f'#{data_time_dp[index_frame][3]}', linestyle='-',
                    label=data_time_dp[index_frame][4]
                    if str(data_time_dp[index_frame][4]) not in
                       ax_first.get_legend_handles_labels()[1] + ['EV---EV', 'BL---BL']
                    else None),)

            # устанавливаем легенду
            ax_first.legend(fontsize=6,
                            ncol=2,
                            loc='upper left')

            return add_element

        # нулевой элемент
        else:
            add_element = \
                (ax_first.fill_between(
                    (data_time_dp[index_frame][2], data_time_dp[index_frame + 1][2]),
                    (str(data_time_dp[index_frame][1]), str(data_time_dp[index_frame + 1][1])),
                    color=f'#{data_time_dp[index_frame][3]}', linestyle='-',
                    linewidth=5,
                    label=data_time_dp[index_frame][4]),)

            # устанавливаем легенду
            ax_first.legend(fontsize=7 - math.floor(len(ax_first.get_legend_handles_labels()[1])/10),
                            ncol=2,
                            loc='upper left')

            return add_element

        return []

    # animation object
    dp_graph = animation.FuncAnimation(first_fig,
                                       animate_dp,
                                       init_func=init_graph,
                                       frames=len(data_time_dp) + 1,
                                       blit=True, repeat=False)

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        dp_graph.save(f'{save_path}/dp_dynamic_anim_area.mp4',
                  writer=animation.FFMpegWriter(fps=math.ceil(len(data_time_dp) / 5)
                  if len(data_time_dp) >= 15 else math.ceil(len(data_time_dp) / 2)))

    save_data_process_dp(user_id, exist_area_graph=1)


def create_circle_dp_anim(data_time_dp, save_path, user_id):
    first_fig, ax_first = plt.subplots()

    # перед началом графика
    def init_graph():
        first_fig.set(facecolor='black')
        return []

    # функция анимации
    def animate_dp(index_frame):

        if index_frame == len(data_time_dp):
            # обновляем данный блок, эвент
            ax_first.set_title(f'ДИНАМИКА РАБОТЫ',
                               fontfamily='fantasy',
                               size=25,
                               color='white')
        else:
            ax_first.clear()
            ax_first.set_aspect('equal')

            labels, sizes, colors, block, event = \
                data_time_dp[index_frame]

            if not index_frame:
                ax_first.set_title(f'ДИНАМИКА РАБОТЫ',
                                   fontfamily='fantasy',
                                   size=25,
                                   color='white')
            else:
                # обновляем данный блок, эвент
                ax_first.set_title(f'BLOCK {block}'
                                   f'\nEVENT {event}',
                                   fontfamily='fantasy',
                                   size=16,
                                   color='white')

            # строим диаграмму
            one_cadre = ax_first.pie(sizes,
                                     radius=1 + index_frame / 5000 if index_frame < 100 else 1,
                                     wedgeprops=dict(width=1 - index_frame / 100 if index_frame < 100 else 0.2,
                                                     edgecolor='w'), colors=colors),

            # находим wedges и приципляем к ним имена
            ax_first.legend(one_cadre[0][0], labels,
                            title='BLOCKS',
                            loc="right",
                            bbox_to_anchor=(0, 0, 0.0505, 1.7-0.025*len(ax_first.get_legend_handles_labels()[1])),
                            fontsize=6)

            return one_cadre

    # animation object
    dp_graph = animation.FuncAnimation(first_fig,
                                       animate_dp,
                                       init_func=init_graph,
                                       frames=len(data_time_dp) + 1,
                                       blit=False, repeat=False)

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        dp_graph.save(f'{save_path}/dp_dynamic_anim_circle.mp4',
                  writer=animation.FFMpegWriter(fps=math.ceil(len(data_time_dp) / 5)
                  if len(data_time_dp) >= 15 else math.ceil(len(data_time_dp) / 2)))

    save_data_process_dp(user_id, exist_circle_graph=1)


def get_dynamic_dp_anim(user_id, all_time_dp,
                        block_colours_dict, block_names_dict,
                        the_end_dp=False, first_time_dp=None,
                        get_area_graph=True, save_path='') -> int:
    # требуется график линии
    if get_area_graph:

        data_for_anim, useful_delta = \
            get_data_for_area_graph(all_time_dp,
                                    block_colours_dict, block_names_dict,
                                    the_end_dp=the_end_dp, first_time_dp=first_time_dp)

        stream_anim = Process(target=create_area_dp_anim, args=(data_for_anim, save_path, user_id))
        stream_anim.start()

    # круговой график
    else:

        data_for_anim, useful_delta = \
            get_data_for_circle_graph(all_time_dp, block_colours_dict, block_names_dict,
                                      the_end_dp=the_end_dp, first_time_dp=first_time_dp)

        stream_anim = Process(target=create_circle_dp_anim, args=(data_for_anim, save_path, user_id))
        stream_anim.start()

    return useful_delta
