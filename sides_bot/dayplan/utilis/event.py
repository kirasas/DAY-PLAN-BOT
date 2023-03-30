from utilis.consts_common import dict_with_circle, dict_with_bold_nums
from utilis.main_common import big_replacing, get_button, add_buttons
#
from sides_bot.dayplan.utilis.consts import begin_doing_event_but, eclipse_el_but, get_way_bl_but
from sides_bot.dayplan.utilis.main import get_first_work_index
from sides_bot.dayplan.utilis.block import get_indexes_current_part_block


def condition_existing_live_elem_event(huge_list, cold_event,
                                       our_part_of_block, last_emoji, work_with_index_emoji):
    existing_events = get_first_work_index(huge_list, our_part_of_block)

    # если нет НЕ выполненных | НЕ залуненных
    recast_part_block = False
    if existing_events is None:
        if cold_event:
            # устанавливаем настоящий эмоджи у первого в луне
            huge_list[cold_event.pop(0)][1] = last_emoji

            existing_events = get_first_work_index(huge_list, our_part_of_block)
        else:
            recast_part_block = True
            new_our_part_of_block = get_indexes_current_part_block(last_emoji,
                                                               work_with_index_emoji, huge_list)
            existing_events = get_first_work_index(huge_list, new_our_part_of_block)
            our_part_of_block = new_our_part_of_block if len(our_part_of_block) != 1 else our_part_of_block

    return huge_list, cold_event, our_part_of_block, existing_events, recast_part_block


def get_seeing_event_values(updated_data_seeing_event,
                            huge_list,
                            cold_event, our_part_of_block, last_emoji,
                            real_number_stars, work_with_index_emoji):
    condition_update_values_event = \
        not updated_data_seeing_event \
        or updated_data_seeing_event[0] != huge_list

    if condition_update_values_event:

        # проверяем: не все ли элементы в луне
        huge_list, cold_event, our_part_of_block, existing_events, _ = \
            condition_existing_live_elem_event(huge_list, cold_event,
                                               our_part_of_block, last_emoji, work_with_index_emoji)

        # кол-во НЕ выполненных эвентов блока
        yet_not_done = len(work_with_index_emoji.get(last_emoji))

        # ещё НЕ выполненных элементов в рамках данной части блока
        not_done_in_part_block = len(set(our_part_of_block) & set(work_with_index_emoji.get(last_emoji)))

        # СТРОКИ ЭВЕНТА
        # кол-во звёзд определяет дизайн
        real_number_stars += 1
        if real_number_stars <= 20:
            real_number_stars = f' ◄▬{dict_with_circle.get(str(real_number_stars))}▬►'
        else:
            real_number_stars = f'❁▭<b>{big_replacing(real_number_stars, dict_with_bold_nums)}</b>▭❁' \
                if real_number_stars % 10 == 0 \
                else f'●▬{big_replacing(real_number_stars, dict_with_circle)}▬●'
        asked = f'<b>⬈EVENT⬊</b>\n🕒 000 🕘\n{real_number_stars}\n\n﹄<i>{huge_list[existing_events][0][0]}</i>﹃'

        # КБ ЭВЕНТА
        # если осталось выполнить только 1 эвент | в части блока только 1 эвент,
        # то не добавляем возможность пропустить эвент
        need_kb = \
            add_buttons(get_way_bl_but('◁◁◁'), begin_doing_event_but, row_width=1) \
                if yet_not_done == 1 or len(our_part_of_block) == 1 or not_done_in_part_block == 1 \
                else add_buttons(get_way_bl_but('◁'), eclipse_el_but, begin_doing_event_but, row_width=2)
        updated_data_seeing_event = (huge_list, existing_events, asked, need_kb)

    return huge_list, cold_event, \
           updated_data_seeing_event, our_part_of_block, \
           condition_update_values_event, \
           updated_data_seeing_event[2], updated_data_seeing_event[3]


def get_full_event_do_values(updated_data_event_doing,
                             huge_list,
                             updated_data_seeing_event,
                             str_clock, needing_clock_diff, action=None):
    condition_update_value_event = not updated_data_event_doing \
                                   or updated_data_event_doing[0] != huge_list \
                                   or updated_data_event_doing[1] != str_clock \
                                   or huge_list[updated_data_seeing_event[1]][2] \
                                   or action == 'already_ready_event'

    if not updated_data_event_doing \
            or updated_data_event_doing[0] != huge_list \
            or action == 'already_ready_event' \
            or (huge_list[updated_data_seeing_event[1]][2]
                and updated_data_event_doing[1] != str_clock):  # для изменения времени на кнопке

        index_event = updated_data_seeing_event[1]
        time_work_this_event = huge_list[index_event][2]

        # СТРОКИ ЭВЕНТА
        # обновляем время
        asked = updated_data_seeing_event[2].replace('000', str_clock, 1)

        # КБ ЭВЕНТА
        finish_event_but = '✔️️END✔'
        call_finish = 'event_ready'
        if time_work_this_event:
            # если имеется время выполнения у данного эвента
            time_left = time_work_this_event - int(needing_clock_diff)

            if time_left > 0:
                finish_event_but = time_left
                call_finish = 'NONE'
            else:
                huge_list[index_event][2] = 0

        # если идёт время (finish_event_but is int), добавляем кнопку для того, чтобы закончить раньше
        ready_event_but = get_button(f'{finish_event_but}', callback_data=call_finish)
        need_kb = \
            add_buttons(
                get_button('◁', callback_data='way_bl'),
                get_button('✔️', callback_data='already_ready_event'),
                ready_event_but, row_width=2) \
                if type(finish_event_but) is int \
                else add_buttons(
                get_button('◁◁◁', callback_data='way_bl'),
                ready_event_but, row_width=1)

        updated_data_event_doing = [huge_list, str_clock, asked, need_kb]

    # изменяется только время
    elif updated_data_event_doing[1] != str_clock:
        # обновляем время
        asked, need_kb = \
            updated_data_seeing_event[2].replace('000', str_clock, 1), updated_data_event_doing[3]
        updated_data_event_doing[2] = asked

    # ничего не измеянется
    else:
        asked, need_kb = \
            updated_data_event_doing[2], updated_data_event_doing[3]

    return updated_data_event_doing, \
           huge_list, \
           asked, need_kb, \
           condition_update_value_event
