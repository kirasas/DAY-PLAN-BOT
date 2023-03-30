from aiogram.types import ParseMode
from aiogram.utils.markdown import quote_html
#
from utilis.main_common import plus_to_reg_messages, minus_to_reg_messages
#
from sides_bot.reg_aut.utilis.consts import visiting_system_kb, is_all_right_reg_kb


async def cancel_reg_or_aut(state, chat_id, bot, first_actions,
                            cursor, conn,
                            action_reg=True, restart=False):
    async with state.proxy() as data:
        id_work = data.get('id_work')
        id_begin = data.get('id_begin')
        first_point = data.get('first_point')

    await bot.delete_message(chat_id=chat_id, message_id=id_work)
    await bot.delete_message(chat_id=chat_id, message_id=first_point)
    await bot.edit_message_text(f'{"🚀ЗАРЕГИСТРИРОВАТЬСЯ🚀" if action_reg else "✈️ВОЙТИ✈"}\n\n'
                                f'{"❌*ОТМЕНЕНО*❌" if not restart else "♻*️ПЕРЕЗАПУЩЕНО*♻️"}',
                                chat_id=chat_id,
                                message_id=id_begin,
                                parse_mode=ParseMode.MARKDOWN)
    await state.finish()
    minus_to_reg_messages(cursor, conn, chat_id)

    await first_actions.waiting_command.set()
    await bot.edit_message_text('🔅*Вход в DAY PLAN*🔅\n\n'
                                '`|-|-|-|`\n\n'
                                '💠Войдите или зарегистрируйтесь, '
                                'чтобы получить доступ к услугам DAY PLAN💠',
                                chat_id=chat_id,
                                message_id=id_begin,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=visiting_system_kb)
    plus_to_reg_messages(cursor, conn,
                         (chat_id, id_begin))


async def all_right_asking(state, chat_id, bot):
    # проверяем: есть ли обращение у пользователя
    async with state.proxy() as data:
        is_appeal_existing = \
            f"<b>️️▫Ваше обращение:</b> <code>{quote_html(data['appeal_user'])}</code>️\n" if data.get('appeal_user') \
            else ""

        await bot.edit_message_text(f'🖱<b>4/4🖱</b>\n\n'
                                    f'❔️|Вы согласны, {chat_id}, с указанными данными|❔\n\n'
                                    f'️{is_appeal_existing}'
                                    f'▫<b>Ваш логин:</b> <code>{quote_html(data["login_user"])}</code>\n'
                                    f'▫<b>Ваш пароль:</b> <code>{quote_html(data["password_user"])}</code>\n\n',
                                    chat_id=chat_id,
                                    message_id=data['id_work'],
                                    parse_mode=ParseMode.HTML,
                                    reply_markup=is_all_right_reg_kb)
