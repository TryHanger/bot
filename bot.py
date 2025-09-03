import asyncio
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InputMediaPhoto, FSInputFile, LabeledPrice, PreCheckoutQuery, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters.callback_data import CallbackData


from db import init_db, get_user, add_star_referral, add_user, is_referral_counted, mark_referral_counted, get_referrals, get_referrals_paginated, update_user_balance
from db import activate_vip, get_daily_bonus, get_autoclicker_reward
from db import game_dice, game_coin, game_rps, game_21

from config import API_TOKEN, CHANNEL_ID, ADMIN_IDS, PLAN_CONFIG_REFERRALS, BASE_REWARD_REFERRALS
from config import DB_PATH, CLICK_DELAY, CLEANUP_DELAY, ADMIN_CHAT_PAYMENTS_ID, ADMIN_CHAT_TASKS_ID

class RefCallback(CallbackData, prefix="ref"):
    action: str  # "link" или "list"
    user_id: int
    offset: int = 0

conn, cursor = init_db()

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

router = Router()
dp.include_router(router)


# photo = InputFile(path_or_bytesio="./images/menu.jpg")

async def edit_main_menu(call: types.CallbackQuery, user_id: int):
    user = get_user(call.from_user.id)
    earned, withdrawn = user[7], user[8]
    earned = float(earned)
    withdrawn = float(withdrawn)
    photo_path = r"image\main_menu.jpg"
    photo = FSInputFile(photo_path)
    text = (
        "✨ Добро пожаловать в главное меню ✨\n"
        "\n"
        f" 🌟 Всего заработано: {earned:.2f}⭐️  \n"
        f" 💱  Всего обменяли: {withdrawn:.2f}⭐️\n"
        "\n"
        " Как заработать звёзды?\n"
        "\n"
        "<blockquote>📌— Кликай, собирай ежедневные награды и вводи промокоды\n"
        "📌— Приглашай друзей и получай за них звезды 1 человек - 2 звезды 🌟\n"
        "📌— Выполняй задания\n"
        "📌— Испытай удачу в увлекательных мини-играх\n"
        "📌— Всё это доступно в главном меню</blockquote>"
    )
    
    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")
    await call.message.edit_media(media=media, reply_markup=main_menu(user_id))

async def send_main_menu_with_photo(message: types.Message, user_id: int):
    user = get_user(user_id)
    earned, withdrawn = user[7], user[8]
    earned = float(earned)
    withdrawn = float(withdrawn)
    photo_path = r"image\main_menu.jpg"
    photo = FSInputFile(photo_path)
    text = (
        "✨ Добро пожаловать в главное меню ✨\n"
        "\n"
        f" 🌟 Всего заработано: {earned:.2f}⭐️  \n"
        f" 💱  Всего обменяли: {withdrawn:.2f}⭐️\n"
        "\n"
        " Как заработать звёзды?\n"
        "\n"
        "<blockquote>📌— Кликай, собирай ежедневные награды и вводи промокоды\n"
        "📌— Приглашай друзей и получай за них звезды 1 человек - 2 звезды 🌟\n"
        "📌— Выполняй задания\n"
        "📌— Испытай удачу в увлекательных мини-играх\n"
        "📌— Всё это доступно в главном меню</blockquote>"
    )

    await message.answer_photo(photo=photo, caption=text, reply_markup=main_menu(user_id), parse_mode="HTML")

    # Если URL:
    # await message.answer_photo(
    #     photo=photo_url_or_path,
    #     caption="📌 Главное меню",
    #     reply_markup=main_menu(user_id)
    # )

def subscribe_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Подписаться на канал", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")
    kb.button(text="✅ Проверить подписку", callback_data="check_sub")
    return kb.as_markup()

def main_menu(user_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="💎 Фарм", callback_data="farm")
    kb.button(text="🖱 Автокликер", callback_data="autoclicker_claim")
    kb.button(text="🎮 Мини-игры", callback_data="mini_games")
    kb.button(text="📢 Розыгрыши", url="https://t.me/Star_Fund")
    kb.button(text="💱 Обменять звёзды", callback_data="exchange_stars")
    kb.button(text="📥 Рефералы", callback_data=RefCallback(action="link", user_id=user_id, offset=0).pack())
    kb.button(text="👑 Бустеры", callback_data="booster")
    kb.button(text="📖 Гайд", callback_data="guide")
    kb.adjust(1) 
    return kb.as_markup()

def farm_menu_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖱 Кликнуть", callback_data="clicker")],
        [InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data="daily_bonus")],
        [InlineKeyboardButton(text="🏷 Промокоды", callback_data="promo")],
        [InlineKeyboardButton(text="📋 Задания", callback_data="tasks_list")],
        [InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu")]
    ])
    return keyboard


async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False


# Старт по рефке
@dp.message(CommandStart(deep_link=True))
async def start_ref(message: types.Message, command: CommandStart):
    user_id = message.from_user.id
    inviter_id = int(command.args) if command.args.isdigit() else None
    username = message.from_user.username
    add_user(user_id, username, inviter_id)

    if await is_subscribed(user_id):
        await send_main_menu_with_photo(message, user_id)
    else:
        await message.answer(
            "❗ Подпишитесь на канал, чтобы продолжить:",
            reply_markup=subscribe_kb()
        )

# Обычный старт
@dp.message(CommandStart())
async def start_simple(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    add_user(user_id, username)

    if await is_subscribed(user_id):
        await send_main_menu_with_photo(message, user_id)
    else:
        await message.answer(
            "❗ Подпишитесь на канал, чтобы продолжить:",
            reply_markup=subscribe_kb()
        )




@dp.callback_query(lambda c: c.data == "check_sub")
async def check_subscription(call: types.CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)  # (user_id, stars, refs, inviter_id, ref_counted, username, created_at, earned, withdrawn)

    if await is_subscribed(user_id):
        inviter_id = user[3] if user else None  # ID пригласившего

        if inviter_id and not is_referral_counted(user_id):
            # Получаем план пригласившего
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT plan FROM subscriptions WHERE user_id = ?", (inviter_id,))
            row = cursor.fetchone()
            conn.close()

            inviter_plan = row[0] if row else "basic"
            multiplier = PLAN_CONFIG_REFERRALS.get(inviter_plan, PLAN_CONFIG_REFERRALS["basic"])["multiplier"]

            reward = BASE_REWARD_REFERRALS * multiplier

            # Начисляем звёзды пригласившему
            add_star_referral(inviter_id, reward)
            mark_referral_counted(user_id)

            await bot.send_message(inviter_id, f"✨ У вас новый реферал! +{reward:.1f}⭐")

        await edit_main_menu(call, user_id)
    else:
        await call.answer("❗ Вы ещё не подписались", show_alert=True)

# Рефералка
@dp.callback_query(RefCallback.filter(F.action == "link"))
async def show_ref_link(call: types.CallbackQuery, callback_data: RefCallback):
    user_id = callback_data.user_id
    bot_username = (await bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"

    text = (
        "<b>🎉 Приглашай друзей и получай звёзды! ⭐️</b>\n"
        "\n"
        "<b>🚀 Как использовать свою реферальную ссылку?</b>\n"
        "   <b>•</b> Отправь её друзьям в личные сообщения 📥\n"
        "   <b>•</b> Поделись ссылкой в своём Telegram-канале 📈\n"
        "   <b>•</b> Оставь её в комментариях или чатах 🗨\n"
        "   <b>•</b> Распространяй ссылку в соцсетях: TikTok, Instagram, WhatsApp и других 🌍\n"
        "\n"
        "<b>📩 Что ты получишь?</b>\n"
        "За каждого друга, который перейдет по твоей ссылке, ты получаешь +2⭐️!\n"
        "\n"
        "<blockquote><b>🛑 Правила рефералов 🛑</b>\n"
        "\n"
        "️️️️️⭕️ 1.Нельзя отписываться от спонсоров \n"
        "\n"
        "⭕️ 2.Накручивать себе рефералов , добавлять ботов или *мертвых* пользователей \n"
        "\n"
        "⭕️ 3. Администрация в праве отказать, если вы нарушили правила</blockquote>"
        "\n"
        "\n"
        "<b>🔗 Твоя реферальная ссылка:</b>\n"
        f"{ref_link}\n"
        "\n"
        "<b>Делись и зарабатывай уже сейчас! 🚀</b>"
        
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(text="👥 Мои рефералы", callback_data=RefCallback(action="list", user_id=user_id, offset=0).pack())
    kb.button(text="⬅ Главное меню", callback_data="main_menu")
    kb.adjust(1)

    # Путь к локальному файлу с фото (например, у тебя в папке image)
    photo_path = r"image\referal.jpg"
    photo = FSInputFile(photo_path)  # Используй FSInputFile для локального файла

    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")

    await call.message.edit_media(media=media, reply_markup=kb.as_markup())

@dp.callback_query(RefCallback.filter(F.action == "list"))
async def show_referrals_list(call: types.CallbackQuery, callback_data: RefCallback):
    user_id = callback_data.user_id
    offset = callback_data.offset

    referrals, total = get_referrals_paginated(user_id, offset)

    if not referrals:
        text = "😔 У вас пока нет рефералов."
    else:
        lines = []
        for uid, username, created_at in referrals:
            date_str = created_at.split(" ")[0]
            if username:
                user_link = f"[{username}](https://t.me/{username})"
            else:
                user_link = f"User ID: {uid}"
            lines.append(f"{user_link} — {date_str}")
        text = "\n".join(lines)

    caption = f"👥 Ваши рефералы:\n{text}"

    kb = InlineKeyboardBuilder()
    kb.adjust(2)

    if offset > 0:
        kb.button(
            text="⬅️ Назад",
            callback_data=RefCallback(action="list", user_id=user_id, offset=max(offset - 10, 0)).pack()
        )
    if offset + 10 < total:
        kb.button(
            text="➡️ Вперёд",
            callback_data=RefCallback(action="list", user_id=user_id, offset=offset + 10).pack()
        )

    kb.button(text="⬅ К ссылке", callback_data=RefCallback(action="link", user_id=user_id).pack())
    kb.button(text="⬅ Главное меню", callback_data="main_menu")
    kb.adjust(1)

    photo_path = r"image\referal.jpg"
    photo = FSInputFile(photo_path)

    media = InputMediaPhoto(media=photo, caption=caption, parse_mode="Markdown")

    await call.message.edit_media(media=media, reply_markup=kb.as_markup())



# @dp.callback_query(F.data == "profile")
@dp.callback_query(F.data == "farm")
async def profile(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    new_photo_path = r"image\profile.jpg"  # путь к файлу с фото

    if user:
        stars = user[1]
        refs = user[2]
    else:
        stars = 0
        refs = 0

    kb = InlineKeyboardBuilder()
    kb.button(text="⬅ Назад", callback_data="main_menu")

    text = (
        f"👤 Ваш профиль:\n"
        f"⭐ Звёзд: {stars}\n"
        f"👥 Рефералов: {refs}"
    )

    text = (
        "✨ Профиль\n"
        "──────────────\n"
        f"👤 Имя: {user[5]}\n"
        f"🆔 ID: {user[0]}\n"
        "──────────────\n"
        f"💰 Баланс: {stars:.2f}⭐️\n"
        f"👥 Рефералов: {refs}\n"
        "──────────────\n"
        # "⬇️ Используй кнопки ниже для действий.\n"
        "\n"
        # "<b>Промокоды на бесплатные звезды можно получить здесь ⬇️</b>\n"
        # "t.me/careshram"
        "<b>🎁 Промокоды на бесплатные звезды:</b>\n"
        "➡️ <a href='https://t.me/careshram'>t.me/careshram</a>"


    )


    photo = FSInputFile(new_photo_path)  # вот тут важно указать path=
    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")
    await call.message.edit_media(media=media, reply_markup=farm_menu_keyboard())






@dp.callback_query(F.data == "exchange_stars")
async def profile(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    new_photo_path = r"image\exchange_stars.jpg"

    kb = InlineKeyboardBuilder()
    kb.button(text="💸 Вывести 50⭐️", callback_data="withdraw_50")
    kb.button(text="💸 Вывести 100⭐️", callback_data="withdraw_100")
    kb.button(text="💸 Вывести 150⭐️", callback_data="withdraw_150")
    kb.button(text="💸 Вывести 200⭐️", callback_data="withdraw_200")
    kb.button(text="💸 Вывести 350⭐️", callback_data="withdraw_350")
    kb.button(text="💸 Вывести 500⭐️", callback_data="withdraw_500")
    kb.adjust(2)
    kb.row(InlineKeyboardButton(text="💸 Вывести 1000⭐️", callback_data="withdraw_1000"))
    kb.row(InlineKeyboardButton(text="⬅ Назад", callback_data="main_menu"))


    text = (
        f"🔸 У тебя на счету: {user[1]:.2f}⭐️\n\n"
        "⛔️ Важно! ⛔️\n\n"
        "❗️ Для получения выплаты (подарка) нужно быть подписанным на: <u>ВСЕХ СПОНСОРОВ</u>\n"
        "❗️ Проверьте есть ли у вас юзернейм в тг если нет то поставьте\n"
        "❗️ Не менять свой тег пока не получили свои подарки\n\n"
        "<blockquote>‼️ Если не будет подписки в момент отправки подарка или вы измените свой тег  - выплата будет удалена, звёзды не возвращаются!</blockquote>\n"
        "\n"
        "<b>Выбери количество звёзд, которое хочешь обменять, из доступных вариантов ниже:</b>\n"
    )
    
    photo = FSInputFile(new_photo_path)
    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")
    await call.message.edit_media(media=media, reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("withdraw_"))
async def withdraw_stars(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    amount = int(call.data.split("_")[1])  # извлекаем число из callback_data

    if user[1] < amount:
        await call.answer(
            f"❌ Недостаточно звёзд для вывода {amount}⭐️. У тебя только {user[1]}⭐️.",
            show_alert=True
        )
        return

    # Списываем звёзды у пользователя
    update_user_balance(call.from_user.id, amount)

    # Уведомляем пользователя
    await call.answer(f"✅ Заявка на вывод {amount}⭐️ принята!", show_alert=True)
    await call.message.answer(f"💸 Заявка на вывод {amount}⭐️ отправлена. Ожидай обработки администрацией.")

    # Отправляем уведомление в админ-группу
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{call.from_user.id}_{amount}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline_{call.from_user.id}_{amount}")]
    ])

    await bot.send_message(
        chat_id=ADMIN_CHAT_PAYMENTS_ID,
        text=(
            f"🔔 *Новая заявка на вывод!*\n\n"
            f"👤 Пользователь: [{call.from_user.full_name}](tg://user?id={call.from_user.id})\n"
            f"💰 Сумма: {amount}⭐️\n"
            f"🆔 ID: `{call.from_user.id}`"
        ),
        parse_mode="Markdown",
        reply_markup=kb
    )

@dp.callback_query(F.data.startswith("approve_"))
async def approve_withdraw(call: types.CallbackQuery):
    _, user_id, amount = call.data.split("_")
    user_id = int(user_id)
    amount = int(amount)

    await call.message.edit_text(
        f"✅ Выплата {amount}⭐️ пользователю ID {user_id} *одобрена*.",
        parse_mode="Markdown"
    )

    # Уведомляем пользователя
    await bot.send_message(
        chat_id=user_id,
        text=f"✅ Твоя заявка на вывод {amount}⭐️ одобрена! Скоро деньги поступят."
    )

@dp.callback_query(F.data.startswith("decline_"))
async def decline_withdraw(call: types.CallbackQuery):
    _, user_id, amount = call.data.split("_")
    user_id = int(user_id)
    amount = int(amount)

    await call.message.edit_text(
        f"❌ Выплата {amount}⭐️ пользователю ID {user_id} *отклонена*.",
        parse_mode="Markdown"
    )

    # Уведомляем пользователя
    await bot.send_message(
        chat_id=user_id,
        text=f"❌ Твоя заявка на вывод {amount}⭐️ была отклонена администрацией."
    )
















@dp.callback_query(F.data == "booster")
async def show_vip_menu(call: types.CallbackQuery):
    photo = FSInputFile(r"image\vip.jpg")  # Картинка для VIP меню, если есть

    text = (
        "<b>🎖 Выбери свой VIP-пакет:</b>\n\n"
        "🎖 <b>Lite Pack — 299⭐️ / 7 дней</b>\n"
        "  ⚡️ Клик ×2,5 (0,025 за тап)\n"
        "  🖱 Лимит кликов: 600/день\n"
        "  💰 Лимит звёзд: 15⭐️/день\n"
        "  👥 Рефы приносят ×2 ⭐️\n"
        "  🎁 Ежедневка: +1⭐️\n"
        "  🎲 +10% шанс в мини-играх\n"
        "  🤖 Автокликер: ~35–40% возврата\n"
        "  🎟 Доступ к VIP-конкурсам\n"
        "  🎖 VIP-иконка\n\n"
        "💎 <b>Pro Pack — 699⭐️ / 14 дней</b>\n"
        "  ⚡️ Клик ×2,5 (0,025 за тап)\n"
        "  🖱 Лимит кликов: 1000/день\n"
        "  💰 Лимит звёзд: 25⭐️/день\n"
        "  👥 Рефы приносят 2,5⭐️\n"
        "  🎁 Ежедневка: +2⭐️\n"
        "  🎲 +15% шанс в мини-играх\n"
        "  🎮 1 бесплатная мини-игра/день\n"
        "  📈 +30% к наградам за задания\n"
        "  🤖 Автокликер: ~35–40% возврата\n"
        "  💎 VIP-иконка\n\n"
        "👑 <b>Ultra Pack — 1499⭐️ / 30 дней</b>\n"
        "  ⚡️ Клик ×2,5 (0,025 за тап)\n"
        "  🖱 Лимит кликов: 1200/день\n"
        "  💰 Лимит звёзд: 30⭐️/день\n"
        "  👥 Рефы приносят 3⭐️\n"
        "  🎁 Ежедневка: +3⭐️\n"
        "  🎲 +20% шанс в мини-играх\n"
        "  🎮 2 бесплатные мини-игры/день\n"
        "  🏆 Приоритет в аукционах и конкурсах\n"
        "  💰 +50% к заданиям\n"
        "  🤖 Автокликер: ~35–40% возврата\n"
        "  👑 Ultra-иконка"
    )

    # Клавиатура выбора
    kb = InlineKeyboardBuilder()
    kb.button(text="🎖 Купить Lite Pack (299⭐️)", callback_data="buy_vip_lite")
    kb.button(text="💎 Купить Pro Pack (699⭐️)", callback_data="buy_vip_pro")
    kb.button(text="👑 Купить Ultra Pack (1499⭐️)", callback_data="buy_vip_ultra")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text="⬅ Назад", callback_data="main_menu"))

    await call.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"),
        reply_markup=kb.as_markup()
    )


# # --- Покупка Lite Pack ---
# @dp.callback_query(F.data == "buy_vip_lite")
# async def buy_lite(call: types.CallbackQuery):
#     prices = [LabeledPrice(label="Lite Pack — 7 дней", amount=299)]
#     await bot.send_invoice(
#         chat_id=call.from_user.id,
#         title="Lite Pack — 7 дней",
#         description="VIP Lite: ×2,5 клики, больше кликов и бонусы",
#         provider_token="",  # пусто для оплаты звёздами (Stars)
#         currency="XTR",     # Валюта Stars
#         prices=prices,
#         start_parameter="buy-vip-lite",
#         payload="vip_lite"
#     )


# # --- Покупка Pro Pack ---
# @dp.callback_query(F.data == "buy_vip_pro")
# async def buy_pro(call: types.CallbackQuery):
#     prices = [LabeledPrice(label="Pro Pack — 14 дней", amount=699)]
#     await bot.send_invoice(
#         chat_id=call.from_user.id,
#         title="Pro Pack — 14 дней",
#         description="VIP Pro: ×3 клики, +30% к наградам, мини-игры и бонусы",
#         provider_token="",
#         currency="XTR",
#         prices=prices,
#         start_parameter="buy-vip-pro",
#         payload="vip_pro"
#     )


# # --- Покупка Ultra Pack ---
# @dp.callback_query(F.data == "buy_vip_ultra")
# async def buy_ultra(call: types.CallbackQuery):
#     prices = [LabeledPrice(label="Ultra Pack — 30 дней", amount=1499)]
#     await bot.send_invoice(
#         chat_id=call.from_user.id,
#         title="Ultra Pack — 30 дней",
#         description="VIP Ultra: максимум бонусов, автокликер и приоритет",
#         provider_token="",
#         currency="XTR",
#         prices=prices,
#         start_parameter="buy-vip-ultra",
#         payload="vip_ultra"
#     )

# --- Покупка Lite Pack ---
# --- Покупка Lite Pack ---
@dp.callback_query(F.data == "buy_vip_lite")
async def buy_lite(call: types.CallbackQuery):
    prices = [LabeledPrice(label="Lite Pack — 7 дней", amount=299)]

    # Отправляем инвойс
    invoice_message = await bot.send_invoice(
        chat_id=call.from_user.id,
        title="Lite Pack — 7 дней",
        description="VIP Lite: ×2,5 клики, больше кликов и бонусы",
        provider_token="",  # звёзды
        currency="XTR",
        prices=prices,
        start_parameter="buy-vip-lite",
        payload="vip_lite"
    )

    # Отдельная кнопка отмены
    cancel_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_purchase_{invoice_message.message_id}")]
        ]
    )
    await call.message.answer("Если хотите отменить покупку, нажмите кнопку ниже:", reply_markup=cancel_kb)


# --- Покупка Pro Pack ---
@dp.callback_query(F.data == "buy_vip_pro")
async def buy_pro(call: types.CallbackQuery):
    prices = [LabeledPrice(label="Pro Pack — 14 дней", amount=699)]

    invoice_message = await bot.send_invoice(
        chat_id=call.from_user.id,
        title="Pro Pack — 14 дней",
        description="VIP Pro: ×3 клики, +30% к наградам, мини-игры и бонусы",
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="buy-vip-pro",
        payload="vip_pro"
    )

    cancel_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_purchase_{invoice_message.message_id}")]
        ]
    )
    await call.message.answer("Если хотите отменить покупку, нажмите кнопку ниже:", reply_markup=cancel_kb)


# --- Покупка Ultra Pack ---
@dp.callback_query(F.data == "buy_vip_ultra")
async def buy_ultra(call: types.CallbackQuery):
    prices = [LabeledPrice(label="Ultra Pack — 30 дней", amount=1499)]

    invoice_message = await bot.send_invoice(
        chat_id=call.from_user.id,
        title="Ultra Pack — 30 дней",
        description="VIP Ultra: максимум бонусов, автокликер и приоритет",
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="buy-vip-ultra",
        payload="vip_ultra"
    )

    cancel_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_purchase_{invoice_message.message_id}")]
        ]
    )
    await call.message.answer("Если хотите отменить покупку, нажмите кнопку ниже:", reply_markup=cancel_kb)


# --- Отмена покупки ---
@dp.callback_query(F.data.startswith("cancel_purchase_"))
async def cancel_purchase(callback: types.CallbackQuery):
    invoice_message_id = int(callback.data.split("_")[2])

    # Удаляем сообщение с инвойсом
    try:
        await bot.delete_message(chat_id=callback.from_user.id, message_id=invoice_message_id)
    except:
        pass

    # Удаляем сообщение с кнопкой отмены
    try:
        await callback.message.delete()
    except:
        pass

    await callback.answer()

@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    payload = message.successful_payment.invoice_payload

    if payload == "vip_lite":
        activate_vip(user_id=message.from_user.id, days=7, pack="Lite")
        await message.answer("🎉 Поздравляем! Lite Pack активирован на 7 дней.")

    elif payload == "vip_pro":
        activate_vip(user_id=message.from_user.id, days=14, pack="Pro")
        await message.answer("🎉 Поздравляем! Pro Pack активирован на 14 дней.")

    elif payload == "vip_ultra":
        activate_vip(user_id=message.from_user.id, days=30, pack="Ultra")
        await message.answer("🎉 Поздравляем! Ultra Pack активирован на 30 дней.")















import sqlite3
from datetime import datetime, timedelta
import random

last_click_times = {}

PLAN_CONFIG = {
    "basic": {"multiplier": 1.0, "limit": 200},   # 10 кликов/день 2 звезды
    "lite": {"multiplier": 2.5, "limit": 600},    # 20 кликов/день 15 звезд
    "pro": {"multiplier": 2.5, "limit": 1000},     # 30 кликов/день 25 звезд
    "ultra": {"multiplier": 2.5, "limit": 1200}    # 35 кликов/день 30 звезд
}
BASE_REWARD = 0.01  # звёзд за клик

def cleanup_click_times():
    """Удаляет устаревшие записи из last_click_times"""
    now = datetime.now()
    to_delete = [uid for uid, ts in last_click_times.items()
                 if (now - ts).seconds > CLEANUP_DELAY]
    for uid in to_delete:
        del last_click_times[uid]

@dp.callback_query(F.data == "clicker")
async def handle_click(call: types.CallbackQuery):
    user_id = call.from_user.id
    now = datetime.now()
    
    if random.random() < 0.1:
        cleanup_click_times()
    
    if user_id in last_click_times:
        elapsed = (now - last_click_times[user_id]).seconds
        if elapsed < CLICK_DELAY:
            await call.answer(f"⏳ Подожди ещё {CLICK_DELAY - elapsed} сек.", show_alert=True)
            return
    
    last_click_times[user_id] = now
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Получаем текущий план пользователя
    cursor.execute("SELECT plan, end_date FROM subscriptions WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    plan = "basic"
    if row:
        plan, end_date = row
        if end_date and datetime.now() > datetime.fromisoformat(end_date):
            plan = "basic"
            cursor.execute("UPDATE subscriptions SET plan = ?, end_date = NULL WHERE user_id = ?", ("basic", user_id))

    config = PLAN_CONFIG.get(plan, PLAN_CONFIG["basic"])
    multiplier = config["multiplier"]
    limit = config["limit"]

    today = datetime.now().date()

    # Проверяем запись для кликов
    cursor.execute("SELECT clicks, date FROM clicks WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row:
        clicks, last_date = row
        last_date = datetime.fromisoformat(last_date).date() if last_date else None

        # Если новый день — сбрасываем клики
        if last_date != today:
            clicks = 0
    else:
        clicks = 0

    if clicks >= limit:
        await call.answer("❌ Лимит кликов на сегодня исчерпан!", show_alert=True)
        conn.close()
        return

    # Начисляем звёзды
    reward = BASE_REWARD * multiplier
    cursor.execute("UPDATE users SET stars = stars + ?, earned = earned + ? WHERE user_id = ?", (reward, reward, user_id))

    # Обновляем таблицу clicks
    cursor.execute("""
        INSERT INTO clicks (user_id, date, clicks)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, date)
        DO UPDATE SET clicks = ?
    """, (user_id, today.isoformat(), clicks + 1, clicks + 1))

    conn.commit()
    conn.close()

    await call.answer(f"⭐ +{reward:.3f} звёзд!", show_alert=False)






PLAN_CONFIG_DAILY_BONUS = {
    "basic": {"amount": 0.5},
    "lite": {"amount": 1},
    "pro": {"amount": 2},
    "ultra": {"amount": 3}
}

@dp.callback_query(lambda c: c.data == "daily_bonus")
async def daily_bonus_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    success, amount = get_daily_bonus(user_id,)

    if success:
        await call.answer(f"🎁 Ежедневный бонус получен! +{amount}⭐", show_alert=True)
    else:
        await call.answer("⏳ Вы уже получили бонус сегодня. Попробуйте завтра!", show_alert=True)

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

class SubmitTask(StatesGroup):
    waiting_for_text = State()
    waiting_for_photo = State()

@router.callback_query(F.data == "tasks_list")
async def show_active_tasks(callback: CallbackQuery):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description, reward FROM tasks WHERE status='active'")
    tasks = cursor.fetchall()
    conn.close()

    kb = InlineKeyboardBuilder()
    text = "📋 <b>Доступные задания:</b>\n\n"

    if not tasks:
        await callback.message.edit_text(
            "❌ Сейчас нет активных заданий.",
            parse_mode="HTML"
        )
        return

    for task_id, title, description, reward in tasks:
        text += (
            f"📝 <b>{title}</b>\n"
            f"📄 <i>{description}</i>\n"
            f"💰 Награда: <b>{reward}⭐</b>\n\n"
        )
        kb.row(InlineKeyboardButton(text=f"✅ Сдать «{title}»", callback_data=f"submit_task_{task_id}"))

    # Кнопки навигации
    kb.row(InlineKeyboardButton(text="⬅ Назад", callback_data="farm"))
    kb.row(InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu"))

    # Фоновая картинка
    photo = FSInputFile("image/profile.jpg")

    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")
    await callback.message.edit_media(
        media=media,
        reply_markup=kb.as_markup()
    )

@router.callback_query(F.data.startswith("submit_task_"))
async def start_task_submission(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    task_id = int(callback.data.split("_")[-1])

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Проверяем статус
    cursor.execute(
        "SELECT status FROM task_submissions WHERE user_id=? AND task_id=?",
        (user_id, task_id)
    )
    row = cursor.fetchone()

    if row and row[0] in ("pending", "approved"):
        await callback.answer("❗ Вы уже отправили это задание. Дождитесь проверки админом.", show_alert=True)
        conn.close()
        return

    # Если отклонено — обновляем
    if row and row[0] == "rejected":
        cursor.execute(
            "UPDATE task_submissions SET status='pending' WHERE user_id=? AND task_id=?",
            (user_id, task_id)
        )
    else:
        cursor.execute(
            "INSERT INTO task_submissions (user_id, task_id, status) VALUES (?, ?, 'pending')",
            (user_id, task_id)
        )

    conn.commit()
    conn.close()

    await state.update_data(task_id=task_id, photos=[])

    msg = await callback.message.answer("📝 Напиши комментарий или описание выполнения задания.")
    await state.update_data(last_bot_message=msg.message_id)
    await state.set_state(SubmitTask.waiting_for_text)


# Получаем комментарий
@router.message(SubmitTask.waiting_for_text)
async def get_submission_text(message: Message, state: FSMContext):
    await message.delete()
    data = await state.get_data()

    # Удаляем предыдущее сообщение бота
    if "last_bot_message" in data:
        try:
            await message.bot.delete_message(message.chat.id, data["last_bot_message"])
        except:
            pass

    await state.update_data(comment=message.text)

    msg = await message.answer("📸 Отправьте фото-доказательства. Когда всё будет готово — нажмите «📤 Отправить задание».")
    await state.update_data(last_bot_message=msg.message_id)

    await state.set_state(SubmitTask.waiting_for_photo)
    
from collections import defaultdict

media_groups = defaultdict(list)     # media_group_id -> [photo_file_id]
message_groups = defaultdict(list)   # media_group_id -> [message_id]

@router.message(SubmitTask.waiting_for_photo, F.photo)
async def collect_photos(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])

    if message.media_group_id:
        # Запоминаем фото и ID сообщений для группы
        media_groups[message.media_group_id].append(message.photo[-1].file_id)
        message_groups[message.media_group_id].append(message.message_id)

        # Ждём прихода всего альбома
        await asyncio.sleep(1)

        # Если группа ещё в списке — значит собрали все фото
        if media_groups.get(message.media_group_id):
            # Добавляем все фото в state
            photos.extend(media_groups.pop(message.media_group_id))
            await state.update_data(photos=photos)

            # Удаляем все сообщения пользователя из альбома
            for msg_id in message_groups.pop(message.media_group_id, []):
                try:
                    await message.bot.delete_message(message.chat.id, msg_id)
                except:
                    pass

            # Удаляем старое сообщение бота, если есть
            if "last_bot_message" in data:
                try:
                    await message.bot.delete_message(message.chat.id, data["last_bot_message"])
                except:
                    pass

            # Показываем обновлённый статус
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📤 Отправить задание", callback_data="finish_task_submission")]
                ]
            )
            msg = await message.answer(
                f"📸 Добавлено фото: {len(photos)} шт. Можете отправить ещё или нажмите «📤 Отправить задание».",
                reply_markup=kb
            )
            await state.update_data(last_bot_message=msg.message_id)

    else:
        # Обычное одиночное фото
        photos.append(message.photo[-1].file_id)
        await state.update_data(photos=photos)

        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass

        # Удаляем предыдущее сообщение бота, если было
        if "last_bot_message" in data:
            try:
                await message.bot.delete_message(message.chat.id, data["last_bot_message"])
            except:
                pass

        # Сообщаем пользователю
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📤 Отправить задание", callback_data="finish_task_submission")]
            ]
        )
        msg = await message.answer(
            f"📸 Добавлено фото: {len(photos)} шт. Можете отправить ещё или нажмите «📤 Отправить задание».",
            reply_markup=kb
        )
        await state.update_data(last_bot_message=msg.message_id)

# Завершение отправки
@router.callback_query(F.data == "finish_task_submission")
async def finish_task_submission(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    task_id = data["task_id"]
    comment = data["comment"]

    if not photos:
        await callback.answer("❗ Нужно прикрепить хотя бы одно фото!", show_alert=True)
        return

    # Удаляем сообщение бота
    if "last_bot_message" in data:
        try:
            await callback.bot.delete_message(callback.message.chat.id, data["last_bot_message"])
        except:
            pass

    # Получаем информацию о задании
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT title, description FROM tasks WHERE id = ?", (task_id,))
    task_data = cursor.fetchone()
    conn.close()
    task_title, task_description = task_data if task_data else ("Неизвестно", "Описание недоступно")

    # Уведомление пользователю
    success_msg = await callback.message.answer("✅ Доказательства отправлены на проверку. Ждите ответа администратора.")

    # Отправляем фото админу альбомом
    media_group = [InputMediaPhoto(media=p) for p in photos]
    await callback.bot.send_media_group(chat_id=ADMIN_CHAT_TASKS_ID, media=media_group)

    # Сообщение админу с кнопками
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"taskapprove_{task_id}_{callback.from_user.id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"taskreject_{task_id}_{callback.from_user.id}")
            ]
        ]
    )
    await callback.bot.send_message(
        chat_id=ADMIN_CHAT_TASKS_ID,
        text=(
            f"📢 <b>Новое выполнение задания</b>\n\n"
            f"👤 Пользователь: <a href='tg://user?id={callback.from_user.id}'>{callback.from_user.first_name}</a>\n"
            f"🆔 ID: <code>{callback.from_user.id}</code>\n\n"
            f"📝 Комментарий: {comment}\n\n"
            f"📌 Задание: <b>{task_title}</b>\n"
            f"📄 <i>{task_description}</i>\n"
            f"🆔 Task ID: {task_id}"
        ),
        parse_mode="HTML",
        reply_markup=kb
    )

    await state.clear()

    # Удаляем уведомление об успехе через 15 секунд
    await asyncio.sleep(15)
    try:
        await callback.bot.delete_message(callback.message.chat.id, success_msg.message_id)
    except:
        pass

@router.callback_query(F.data.startswith("taskapprove_"))
async def approve_task(callback: CallbackQuery):
    _, task_id, user_id = callback.data.split("_")
    task_id, user_id = int(task_id), int(user_id)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Проверяем выполнение задания
    cursor.execute(
        "SELECT status FROM task_submissions WHERE task_id=? AND user_id=?",
        (task_id, user_id)
    )
    submission = cursor.fetchone()

    if not submission or submission[0] == "approved":
        await callback.answer("⚠ Задание уже одобрено или не найдено.", show_alert=True)
        conn.close()
        return

    # Проверяем, есть ли задание в базе
    cursor.execute("SELECT reward FROM tasks WHERE id=?", (task_id,))
    row = cursor.fetchone()

    # Если задания уже нет, просто удаляем сообщение и выходим
    if row is None:
        await callback.answer("⚠ Задание уже удалено, операция отменена.", show_alert=True)
        try:
            await callback.message.delete()
        except:
            pass
        conn.close()
        return

    reward = row[0]

    # Начисляем звёзды пользователю
    cursor.execute(
        "UPDATE users SET stars=stars+?, earned=earned+? WHERE user_id=?",
        (reward, reward, user_id)
    )

    # Обновляем статус выполнения
    cursor.execute(
        "UPDATE task_submissions SET status='approved' WHERE task_id=? AND user_id=?",
        (task_id, user_id)
    )

    conn.commit()
    conn.close()

    # Уведомляем пользователя
    await callback.bot.send_message(
        chat_id=user_id,
        text=(
            f"🎉 Ваше выполнение задания #{task_id} одобрено!\n"
            f"💰 Начислено: <b>{reward}⭐</b>"
        ),
        parse_mode="HTML"
    )

    try:
        caption = callback.message.caption or callback.message.text or ""
        updated_caption = caption + f"\n\n✅ Одобрено\n💰 Начислено: {reward}⭐"

        if callback.message.caption:
            await callback.message.edit_caption(updated_caption, reply_markup=None)
        else:
            await callback.message.edit_text(updated_caption, reply_markup=None)
    except:
        pass

@router.callback_query(F.data.startswith("taskreject_"))
async def reject_task(callback: CallbackQuery):
    _, task_id, user_id = callback.data.split("_")
    task_id, user_id = int(task_id), int(user_id)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Обновляем статус выполнения на "отклонено"
    cursor.execute(
        "UPDATE task_submissions SET status='rejected' WHERE task_id=? AND user_id=?",
        (task_id, user_id)
    )
    conn.commit()
    conn.close()

    # Уведомляем пользователя
    await callback.bot.send_message(
        chat_id=user_id,
        text=f"❌ Ваше выполнение задания #{task_id} отклонено. Попробуйте снова."
    )

    # Обновляем сообщение у админа:
    # - убираем кнопки
    # - добавляем отметку "Отклонено"
    caption = callback.message.caption or callback.message.text or ""
    updated_caption = caption + "\n\n❌ Отклонено"

    try:
        if callback.message.caption:
            await callback.message.edit_caption(updated_caption, reply_markup=None)
        else:
            await callback.message.edit_text(updated_caption, reply_markup=None)
    except:
        # Игнорируем, если сообщение уже изменено
        pass

    await callback.answer("Задание отклонено ❌")







@dp.callback_query(lambda c: c.data == "mini_games")
async def show_mini_games(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()  # используем билдeр
    kb.button(text="🎲 Кубик", callback_data="game_dice")
    kb.button(text="🪙 Монетка", callback_data="game_coin")
    kb.button(text="✊✋✌ КНБ", callback_data="game_rps")
    kb.button(text="🃏 21 (Blackjack)", callback_data="game_21")
    kb.button(text="⬅ Главное меню", callback_data="main_menu")
    
    kb.adjust(1)  # 1 кнопка в ряд

    text = "🎮 Выберите мини-игру:"

    photo_path = r"image\games.jpg"  # локальный путь к фото
    photo = FSInputFile(photo_path)  # используем FSInputFile для локального файла

    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")
    
    await call.message.edit_media(media=media, reply_markup=kb.as_markup())


@dp.callback_query(lambda c: c.data == "game_dice")
async def open_dice_menu(call: types.CallbackQuery):
    # Путь к фото для меню игры
    photo_path = r"image\games.jpg"
    photo = FSInputFile(photo_path)

    # Текст описания игры
    text = (
        "🎲 Игра 'Кубик'\n\n"
        "Выберите ставку, чтобы бросить кубик и выиграть звезды!\n"
        "Правила: если выпадет 6 — выигрыш x2, иначе ставка сгорает."
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="1⭐️", callback_data="dice_bet_1")
    kb.button(text="2⭐️", callback_data="dice_bet_2")
    kb.button(text="3⭐️", callback_data="dice_bet_3")
    kb.button(text="4⭐️", callback_data="dice_bet_4")
    kb.button(text="5⭐️", callback_data="dice_bet_5")
    kb.button(text="10⭐️", callback_data="dice_bet_10")
    kb.adjust(2)
    
    kb.row(
        InlineKeyboardButton(text="⬅ Назад", callback_data="mini_games"),
    )
    
    kb.row(
        InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu")
    )

    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")
    
    await call.message.edit_media(media=media, reply_markup=kb.as_markup())

@dp.callback_query(lambda c: c.data.startswith("dice_bet_"))
async def play_dice(call: types.CallbackQuery):
    bet = int(call.data.split("_")[-1])
    balance = get_user(call.from_user.id)[1]
    if balance < bet:
        await call.answer("❌ У вас недостаточно звёзд для этой ставки!", show_alert=True)
        return
    dice = random.randint(1, 6)
    if dice == 6:
        winnings = bet * 2
        result_text = f"🎲 Выпало {dice}! Поздравляем, вы выиграли {winnings}⭐️!"
        game_dice(call.from_user.id, winnings)
    else:
        winnings = -bet
        result_text = f"🎲 Выпало {dice}. Вы проиграли {bet}⭐️."
        game_dice(call.from_user.id, winnings)
    await call.answer(result_text, show_alert=True)


temp_bets = {}

@dp.callback_query(lambda c: c.data == "game_coin")
async def open_coin_menu(call: types.CallbackQuery):
    photo_path = r"image\games.jpg"
    photo = FSInputFile(photo_path)

    text = (
        "🪙 Игра 'Монетка'\n\n"
        "Выберите ставку, а затем угадайте: Орёл или Решка.\n"
        "Если угадаете — выигрыш x2, иначе ставка сгорает."
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="1⭐️", callback_data="coin_bet_1")
    kb.button(text="2⭐️", callback_data="coin_bet_2")
    kb.button(text="3⭐️", callback_data="coin_bet_3")
    kb.button(text="4⭐️", callback_data="coin_bet_4")
    kb.button(text="5⭐️", callback_data="coin_bet_5")
    kb.button(text="10⭐️", callback_data="coin_bet_10")
    kb.adjust(2)
    
    kb.row(
        InlineKeyboardButton(text="⬅ Назад", callback_data="mini_games"),
    )
    
    kb.row(
        InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu")
    )

    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")
    
    await call.message.edit_media(media=media, reply_markup=kb.as_markup())

# Выбор ставки
@dp.callback_query(lambda c: c.data.startswith("coin_bet_"))
async def choose_coin_side(call: types.CallbackQuery):
    user_id = call.from_user.id
    bet = int(call.data.split("_")[-1])  # извлекаем сумму ставки
    temp_bets[user_id] = bet  # сохраняем ставку

    # Путь к картинке
    photo_path = r"image\games.jpg"
    photo = FSInputFile(photo_path)

    # Текст для нового сообщения
    text = f"Ставка: <b>{bet}⭐️</b>\nВыберите сторону монетки:"

    # Клавиатура выбора стороны
    kb = InlineKeyboardBuilder()
    kb.row(
        types.InlineKeyboardButton(text="🦅 Орёл", callback_data="coin_flip_heads"),
        types.InlineKeyboardButton(text="⚖️ Решка", callback_data="coin_flip_tails")
    )
    kb.row(
        types.InlineKeyboardButton(text="⬅ Назад", callback_data="game_coin"),
        types.InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu")
    )

    # Формируем объект медиа с новым текстом
    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")

    # Редактируем текущее сообщение (обновляем фото и подпись)
    await call.message.edit_media(media=media, reply_markup=kb.as_markup())

    await call.answer()


@dp.callback_query(lambda c: c.data in ["coin_flip_heads", "coin_flip_tails"])
async def flip_coin(call: types.CallbackQuery):
    user_id = call.from_user.id

    if user_id not in temp_bets:
        await call.answer("❗ Сначала выберите ставку!", show_alert=True)
        return

    bet = temp_bets[user_id]
    user_choice = "Орёл" if call.data == "coin_flip_heads" else "Решка"

    win_chance = 0.20
    if random.random() < win_chance:
        result = user_choice
    else:
        result = "Орёл" if user_choice == "Решка" else "Решка"

    if result == user_choice:
        winnings = bet * 2
        text = f"🪙 Монетка: <b>{result}</b>\nВы выиграли <b>{winnings}⭐️</b>!"
    else:
        winnings = -bet
        text = f"🪙 Монетка: <b>{result}</b>\nВы проиграли <b>{bet}⭐️</b>."
    
    game_coin(call.from_user.id, winnings)

    del temp_bets[user_id]

    photo_path = r"image\\games.jpg"
    photo = FSInputFile(photo_path)
    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")

    kb = InlineKeyboardBuilder()
    kb.row(
        types.InlineKeyboardButton(text="🎮 Играть снова", callback_data="game_coin"),
        types.InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu")
    )

    await call.message.edit_media(media=media, reply_markup=kb.as_markup())
    await call.answer()





@dp.callback_query(lambda c: c.data == "game_rps")
async def open_rps_menu(call: types.CallbackQuery):
    photo_path = r"image\games.jpg"
    photo = FSInputFile(photo_path)

    text = (
        "✊✋✌ <b>Камень, Ножницы, Бумага</b>\n\n"
        "Правила:\n"
        "• Камень бьёт ножницы\n"
        "• Ножницы режут бумагу\n"
        "• Бумага кроет камень\n\n"
        "Выплата: победа = x2 от ставки, ничья = возврат ставки."
    )

    kb = InlineKeyboardBuilder()
    for bet in (1, 2, 3, 4, 5, 10):
        kb.button(text=f"{bet}⭐️", callback_data=f"rps_bet_{bet}")
    kb.adjust(2)
    kb.row(
        types.InlineKeyboardButton(text="⬅ Назад", callback_data="mini_games"),
        types.InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu"),
    )

    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")
    await call.message.edit_media(media=media, reply_markup=kb.as_markup())


# -------- После выбора ставки — выбор хода --------
@dp.callback_query(lambda c: c.data.startswith("rps_bet_"))
async def rps_choose_move(call: types.CallbackQuery):
    user_id = call.from_user.id
    bet = int(call.data.split("_")[-1])

    # проверка баланса
    balance = get_user(user_id)[1]
    if balance < bet:
        await call.answer("❗ Недостаточно звёзд для этой ставки.", show_alert=True)
        return

    # сохраняем ставку
    temp_bets[user_id] = bet

    photo_path = r"image\games.jpg"
    photo = FSInputFile(photo_path)

    text = (
        f"✊✋✌ <b>КНБ</b>\n"
        f"Ставка: <b>{bet}⭐️</b>\n\n"
        "Выберите ваш ход:"
    )

    kb = InlineKeyboardBuilder()
    kb.row(
        types.InlineKeyboardButton(text="✊ Камень", callback_data="rps_move_rock"),
        types.InlineKeyboardButton(text="✌ Ножницы", callback_data="rps_move_scissors"),
    )
    kb.row(
        types.InlineKeyboardButton(text="✋ Бумага", callback_data="rps_move_paper"),
    )
    kb.row(
        types.InlineKeyboardButton(text="⬅ Назад", callback_data="game_rps"),
        types.InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu"),
    )

    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")
    await call.message.edit_media(media=media, reply_markup=kb.as_markup())
    await call.answer()


# -------- Розыгрыш КНБ --------
@dp.callback_query(lambda c: c.data in ["rps_move_rock", "rps_move_paper", "rps_move_scissors"])
async def rps_play(call: types.CallbackQuery):
    user_id = call.from_user.id

    if user_id not in temp_bets:
        await call.answer("❗ Сначала выберите ставку в меню КНБ.", show_alert=True)
        return

    bet = temp_bets[user_id]
    user_move = call.data.split("_")[-1]  # rock / paper / scissors

    # Маппинг для удобства
    beats = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
    loses_to = {v: k for k, v in beats.items()}

    # 20% шанс победы
    if random.random() < 0.1:
        bot_move = beats[user_move]  # бот ставит проигрышный для себя ход
        result = "win"
    else:
        # иногда бот ставит ничью
        if random.random() < 0.1:
            bot_move = user_move
            result = "draw"
        else:
            bot_move = loses_to[user_move]  # бот ставит выигрышный ход
            result = "lose"

    winnings = 0
    if result == "win":
        winnings = bet
        delta_text = f"+{bet}⭐️"
    elif result == "lose":
        winnings = -bet
        delta_text = f"-{bet}⭐️"
    else:
        delta_text = "0⭐️"

    game_rps(user_id, winnings)
    balance = get_user(user_id)[1]

    names = {"rock": "✊ Камень", "paper": "✋ Бумага", "scissors": "✌ Ножницы"}
    result_text = {
        "win": "✅ <b>Победа!</b>",
        "lose": "❌ <b>Поражение.</b>",
        "draw": "➖ <b>Ничья.</b>"
    }[result]

    text = (
        "✊✋✌ <b>КНБ — результат</b>\n\n"
        f"Вы: {names[user_move]}\n"
        f"Бот: {names[bot_move]}\n"
        f"{result_text}\n\n"
        f"Изменение баланса: <b>{delta_text}</b>\n"
        f"Текущий баланс: <b>{balance:.2f}⭐️</b>"
    )

    temp_bets.pop(user_id, None)

    photo_path = r"image\\games.jpg"
    photo = FSInputFile(photo_path)
    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")

    kb = InlineKeyboardBuilder()
    kb.row(
        types.InlineKeyboardButton(text="🔁 Играть снова", callback_data="game_rps"),
        types.InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu"),
    )

    await call.message.edit_media(media=media, reply_markup=kb.as_markup())
    await call.answer()


@dp.callback_query(lambda c: c.data in ["rps_move_rock", "rps_move_paper", "rps_move_scissors"])
async def rps_play(call: types.CallbackQuery):
    user_id = call.from_user.id

    if user_id not in temp_bets:
        await call.answer("❗ Сначала выберите ставку в меню КНБ.", show_alert=True)
        return

    bet = temp_bets[user_id]
    user_move = call.data.split("_")[-1]  # rock / paper / scissors

    # Маппинг для удобства
    beats = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
    loses_to = {v: k for k, v in beats.items()}

    # 20% шанс победы
    if random.random() < 0.2:
        bot_move = beats[user_move]  # бот ставит проигрышный для себя ход
        result = "win"
    else:
        # иногда бот ставит ничью
        if random.random() < 0.2:
            bot_move = user_move
            result = "draw"
        else:
            bot_move = loses_to[user_move]  # бот ставит выигрышный ход
            result = "lose"

    winnings = 0
    if result == "win":
        winnings = bet
        delta_text = f"+{bet}⭐️"
    elif result == "lose":
        winnings = -bet
        delta_text = f"-{bet}⭐️"
    else:
        delta_text = "0⭐️"

    game_rps(user_id, winnings)
    balance = get_user(user_id)[1]

    names = {"rock": "✊ Камень", "paper": "✋ Бумага", "scissors": "✌ Ножницы"}
    result_text = {
        "win": "✅ <b>Победа!</b>",
        "lose": "❌ <b>Поражение.</b>",
        "draw": "➖ <b>Ничья.</b>"
    }[result]

    text = (
        "✊✋✌ <b>КНБ — результат</b>\n\n"
        f"Вы: {names[user_move]}\n"
        f"Бот: {names[bot_move]}\n"
        f"{result_text}\n\n"
        f"Изменение баланса: <b>{delta_text}</b>\n"
        f"Текущий баланс: <b>{balance:.2f}⭐️</b>"
    )

    temp_bets.pop(user_id, None)

    photo_path = r"image\\games.jpg"
    photo = FSInputFile(photo_path)
    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")

    kb = InlineKeyboardBuilder()
    kb.row(
        types.InlineKeyboardButton(text="🔁 Играть снова", callback_data="game_rps"),
        types.InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu"),
    )

    await call.message.edit_media(media=media, reply_markup=kb.as_markup())
    await call.answer()












active_games = {}
temp_bets = {}

def create_deck():
    """Создает колоду: 4 масти * (2-10,J,Q,K=10,A=11)"""
    cards = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
    random.shuffle(cards)
    return cards


def calculate_score(hand):
    """Считает очки, туз может быть 1 или 11"""
    score = sum(hand)
    while score > 21 and 11 in hand:
        hand[hand.index(11)] = 1
        score = sum(hand)
    return score


def dealer_draw(deck, dealer_hand):
    """Дилер добирает карты по стандартным правилам"""
    while calculate_score(dealer_hand) < 17:
        dealer_hand.append(deck.pop())
    return dealer_hand


def finalize_result(player_hand, dealer_hand):
    player_score = calculate_score(player_hand)
    dealer_score = calculate_score(dealer_hand)

    if player_score > 21:
        result = "lose"
    elif dealer_score > 21:
        result = "win"
    elif player_score > dealer_score:
        result = "win"
    elif player_score < dealer_score:
        result = "lose"
    else:
        result = "draw"

    return result

@dp.callback_query(lambda c: c.data == "game_21")
async def start_21(call: types.CallbackQuery):
    photo = FSInputFile("image/games.jpg")
    text = "🃏 <b>Игра 21</b>\n\nВыберите ставку для начала игры."

    kb = InlineKeyboardBuilder()
    for bet in (1, 2, 3, 4, 5, 10):
        kb.button(text=f"{bet}⭐️", callback_data=f"blackjack_bet_{bet}")
    kb.adjust(2)
    kb.row(
        types.InlineKeyboardButton(text="⬅ Назад", callback_data="mini_games"),
        types.InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu"),
    )

    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")
    await call.message.edit_media(media=media, reply_markup=kb.as_markup())
    
@dp.callback_query(lambda c: c.data.startswith("blackjack_bet_"))
async def deal_cards(call: types.CallbackQuery):
    user_id = call.from_user.id
    bet = int(call.data.split("_")[-1])
    balance = get_user(user_id)[1]

    if balance < bet:
        await call.answer("❗ Недостаточно звёзд.", show_alert=True)
        return

    temp_bets[user_id] = bet
    deck = create_deck()
    player = [deck.pop(), deck.pop()]
    dealer = [deck.pop()]

    active_games[user_id] = {"deck": deck, "player": player, "dealer": dealer}

    await update_blackjack_message(call, user_id, "Начало игры! Ваш ход.")
    
async def update_blackjack_message(call, user_id, title):
    game = active_games[user_id]
    player = game["player"]
    dealer = game["dealer"]

    player_score = calculate_score(player)
    dealer_score = calculate_score(dealer)

    photo = FSInputFile("image/games.jpg")
    text = (
        f"🃏 <b>Игра 21</b>\n"
        f"{title}\n\n"
        f"Ваши карты: {player} (Очки: {player_score})\n"
        f"Карты дилера: {dealer} (Очки: {dealer_score}?)"
    )

    kb = InlineKeyboardBuilder()
    kb.row(
        types.InlineKeyboardButton(text="➕ Добрать", callback_data="blackjack_hit"),
        types.InlineKeyboardButton(text="✋ Хватит", callback_data="blackjack_stand"),
    )
    kb.row(
        types.InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu")
    )

    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")
    await call.message.edit_media(media=media, reply_markup=kb.as_markup())

@dp.callback_query(lambda c: c.data == "blackjack_hit")
async def blackjack_hit(call: types.CallbackQuery):
    user_id = call.from_user.id

    if user_id not in active_games:
            await call.answer("❗ Игра не найдена. Начните заново.", show_alert=True)
            return

    game = active_games[user_id]
    game["player"].append(game["deck"].pop())

    if calculate_score(game["player"]) > 21:
        await finalize_blackjack(call, user_id, "Перебор! Вы проиграли.")
    else:
        await update_blackjack_message(call, user_id, "Вы взяли карту.")

@dp.callback_query(lambda c: c.data == "blackjack_stand")
async def blackjack_stand(call: types.CallbackQuery):
    user_id = call.from_user.id
    game = active_games[user_id]
    game["dealer"] = dealer_draw(game["deck"], game["dealer"])

    await finalize_blackjack(call, user_id, "Результаты игры:")

async def finalize_blackjack(call, user_id, title):
    game = active_games.pop(user_id)
    player = game["player"]
    dealer = game["dealer"]

    result = finalize_result(player, dealer)
    bet = temp_bets.pop(user_id)
    delta = 0

    if result == "win":
        delta = bet
        text_delta = f"+{bet}⭐️"
    elif result == "lose":
        delta = -bet
        text_delta = f"-{bet}⭐️"
    else:
        text_delta = "0⭐️"

    game_21(user_id, delta)  # обновление баланса

    photo = FSInputFile("image/games.jpg")
    text = (
        f"🃏 <b>Игра 21</b>\n{title}\n\n"
        f"Ваши карты: {player} (Очки: {calculate_score(player)})\n"
        f"Карты дилера: {dealer} (Очки: {calculate_score(dealer)})\n\n"
        f"Изменение баланса: <b>{text_delta}</b>"
    )

    kb = InlineKeyboardBuilder()
    kb.row(
        types.InlineKeyboardButton(text="🔁 Играть снова", callback_data="game_21"),
        types.InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu"),
    )

    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")
    await call.message.edit_media(media=media, reply_markup=kb.as_markup())
    await call.answer()





from aiogram import Router, types


@router.callback_query(F.data == "autoclicker_claim")
async def claim_autoclicker_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    success, result_message = get_autoclicker_reward(user_id)

    if not success and "подписк" in result_message.lower():
        # Показываем в alert, что нужна подписка
        await callback.answer(
            text=(
                "Автокликер доступен только по подписке. Оформите её, чтобы пользоваться этой функцией.\n\n"
                "Ежедневно копит бесплатные звезды.\n\n"
                "Важно: каждый день происходит сброс накопленных звезд."
            ),
            show_alert=True
        )
        # Автоматически открываем раздел бустеров
        await show_vip_menu(callback)
    else:
        await callback.answer(result_message, show_alert=True)












    """
    
    
                    АДМИН
    
    
    """
    
@dp.message(Command("admin"))
async def show_admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа.")
        return

    await edit_admin_panel(message)

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from contextlib import suppress


class AddTaskStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_reward = State()

@router.callback_query(F.data == "admin_list_tasks")
async def admin_list_tasks(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, reward, status FROM tasks ORDER BY id ASC")
    tasks = cursor.fetchall()
    conn.close()

    # Создаём клавиатуру сразу, чтобы использовать в любом случае
    kb = InlineKeyboardBuilder()

    if not tasks:
        # Если заданий нет, показываем кнопку "Назад"
        kb.row(InlineKeyboardButton(text="⬅ Назад", callback_data="admin_menu_back"))
        await callback.message.edit_text(
            "❌ Заданий пока нет.",
            reply_markup=kb.as_markup()
        )
        return

    # Если задания есть
    text = "📋 <b>Список заданий</b>\n\n"
    for task_id, title, reward, status in tasks:
        text += (
            f"🆔 {task_id}\n"
            f"📝 <b>{title}</b>\n"
            f"💰 Награда: {reward}⭐\n"
            f"📌 Статус: <i>{status}</i>\n\n"
        )
        kb.row(
            InlineKeyboardButton(
                text=f"❌ Удалить «{title}»",
                callback_data=f"admin_delete_task_{task_id}"
            )
        )

    # Кнопка "Назад"
    kb.row(InlineKeyboardButton(text="⬅ Назад", callback_data="admin_menu_back"))

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )

# --- Шаг 1. Запрос названия задания ---
@router.callback_query(F.data == "admin_add_task")
async def admin_add_task(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return

    msg = await callback.message.answer("Введите название задания:")
    await state.update_data(bot_message=msg.message_id)  # Сохраняем ID последнего сообщения
    await state.set_state(AddTaskStates.waiting_for_title)


# --- Шаг 2. Получение названия ---
@router.message(AddTaskStates.waiting_for_title)
async def task_title_step(message: types.Message, state: FSMContext):
    with suppress(Exception):
        await message.delete()

    data = await state.get_data()
    last_bot_msg = data.get("bot_message")
    if last_bot_msg:
        with suppress(Exception):
            await message.bot.delete_message(chat_id=message.chat.id, message_id=last_bot_msg)

    await state.update_data(title=message.text)
    msg = await message.answer("Теперь введите описание задания:")
    await state.update_data(bot_message=msg.message_id)

    await state.set_state(AddTaskStates.waiting_for_description)


# --- Шаг 3. Получение описания ---
@router.message(AddTaskStates.waiting_for_description)
async def task_description_step(message: types.Message, state: FSMContext):
    with suppress(Exception):
        await message.delete()

    data = await state.get_data()
    last_bot_msg = data.get("bot_message")
    if last_bot_msg:
        with suppress(Exception):
            await message.bot.delete_message(chat_id=message.chat.id, message_id=last_bot_msg)

    await state.update_data(description=message.text)
    msg = await message.answer("Введите награду (можно дробное число, например 0.5):")
    await state.update_data(bot_message=msg.message_id)

    await state.set_state(AddTaskStates.waiting_for_reward)


# --- Шаг 4. Получение награды ---
@router.message(AddTaskStates.waiting_for_reward)
async def task_reward_step(message: types.Message, state: FSMContext):
    with suppress(Exception):
        await message.delete()

    data = await state.get_data()
    last_bot_msg = data.get("bot_message")
    if last_bot_msg:
        with suppress(Exception):
            await message.bot.delete_message(chat_id=message.chat.id, message_id=last_bot_msg)

    try:
        reward = float(message.text)
    except ValueError:
        msg = await message.answer("⚠ Введите корректное число (например: 1, 0.5, 2.75)")
        await state.update_data(bot_message=msg.message_id)
        return

    title = data["title"]
    description = data["description"]

    # Сохраняем в БД
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (title, description, reward) VALUES (?, ?, ?)",
        (title, description, reward)
    )
    conn.commit()
    conn.close()

    confirm_msg = await message.answer(
        f"✅ Задание *{title}* добавлено!\n"
        f"Описание: {description}\n"
        f"Награда: {reward:.2f}⭐️",
        parse_mode="Markdown"
    )

    await state.clear()
    
    await asyncio.sleep(10)
    try:
        await confirm_msg.delete()
    except:
        # Если сообщение уже удалено вручную — игнорируем
        pass
    
@router.callback_query(F.data.startswith("admin_delete_task_"))
async def admin_delete_task(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return

    task_id = int(callback.data.split("_")[-1])

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Проверяем, существует ли задание
    cursor.execute("SELECT title FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()

    if not task:
        await callback.answer("❌ Задание не найдено.", show_alert=True)
        conn.close()
        return

    title = task[0]

    # Удаляем задание
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

    await callback.answer(f"🗑 Задание «{title}» удалено.", show_alert=True)

    # Обновляем список заданий
    await admin_list_tasks(callback)

async def edit_admin_panel(call_or_message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить задание", callback_data="admin_add_task")],
        [InlineKeyboardButton(text="📋 Список заданий", callback_data="admin_list_tasks")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast_start")]
    ])

    text = "🛠 *Админ-панель*:"
    
    if isinstance(call_or_message, types.CallbackQuery):
        # Если это callback, редактируем сообщение
        await call_or_message.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        # Если это сообщение, отправляем новое
        await call_or_message.answer(text, reply_markup=kb, parse_mode="Markdown")









class Broadcast(StatesGroup):
    waiting_for_message = State()
    waiting_for_photo = State()

# =========================
# Запуск рассылки с кнопки
# =========================
@router.callback_query(F.data == "broadcast_start")
async def broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return await callback.answer("⛔ У вас нет доступа.", show_alert=True)

    msg = await callback.message.edit_text(
        "✍ Введите текст рассылки.\nЕсли хотите фото — отправьте его после текста.\n\nЧтобы отменить — введите /cancel."
    )
    await state.update_data(temp_msgs=[msg.message_id])
    await state.set_state(Broadcast.waiting_for_message)

# Получение текста
@router.message(Broadcast.waiting_for_message)
async def get_broadcast_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    temp_msgs = data.get("temp_msgs", [])
    temp_msgs.append(message.message_id)
    await state.update_data(text=message.text, temp_msgs=temp_msgs)

    msg = await message.answer(
        "📸 Теперь, если хотите, отправьте фото для рассылки.\nИли напишите `/skip`, чтобы пропустить."
    )
    temp_msgs.append(msg.message_id)
    await state.update_data(temp_msgs=temp_msgs)
    await state.set_state(Broadcast.waiting_for_photo)

# Пропуск фото
@router.message(Broadcast.waiting_for_photo, Command("skip"))
async def skip_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = data["text"]
    temp_msgs = data.get("temp_msgs", [])

    # добавим /skip в список и попробуем удалить сразу
    temp_msgs.append(message.message_id)
    try:
        await message.delete()
    except:
        pass

    status_msg = await message.answer("🚀 Начинаю рассылку без фото...")
    temp_msgs.append(status_msg.message_id)
    await state.update_data(temp_msgs=temp_msgs)

    await send_broadcast(text=text)

    # подчистим все временные сообщения и вернём админ-меню
    await clear_temp_messages(message.chat.id, temp_msgs)
    await state.clear()
    await edit_admin_panel(message)

# Получение фото
@router.message(Broadcast.waiting_for_photo, F.photo)
async def get_broadcast_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = data["text"]
    temp_msgs = data.get("temp_msgs", [])
    temp_msgs.append(message.message_id)

    photo_id = message.photo[-1].file_id
    status_msg = await message.answer("🚀 Начинаю рассылку с фото...")
    temp_msgs.append(status_msg.message_id)

    await send_broadcast(text=text, photo=photo_id)
    await clear_temp_messages(message.chat.id, temp_msgs)
    await state.clear()
    await edit_admin_panel(message)

# =========================
# Отправка рассылки
# =========================
async def send_broadcast(text: str, photo: str = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()

    sent, failed = 0, 0
    status_msg = await bot.send_message(
        ADMIN_CHAT_TASKS_ID,
        f"🚀 Начинаю рассылку...\nОтправлено: 0/{len(users)}"
    )

    for idx, user_id in enumerate(users, start=1):
        try:
            if photo:
                await bot.send_photo(chat_id=user_id, photo=photo, caption=text, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1

        if idx % 20 == 0:  # обновление статуса каждые 20 пользователей
            try:
                await status_msg.edit_text(
                    f"🚀 Рассылка в процессе...\nОтправлено: {sent}/{len(users)}\nОшибок: {failed}"
                )
            except:
                pass
        await asyncio.sleep(0.05)

    try:
        await status_msg.edit_text(
            f"✅ Рассылка завершена!\nОтправлено: {sent}/{len(users)}\nОшибок: {failed}"
        )
    except:
        await bot.send_message(
            ADMIN_CHAT_TASKS_ID,
            f"✅ Рассылка завершена!\nОтправлено: {sent}/{len(users)}\nОшибок: {failed}"
        )

# =========================
# Удаление временных сообщений
# =========================
async def clear_temp_messages(chat_id: int, msg_ids: list):
    for msg_id in msg_ids:
        try:
            await bot.delete_message(chat_id, msg_id)
        except:
            pass
        
        


@dp.callback_query(F.data == "admin_menu_back")
async def back_to_admin_panel(callback: types.CallbackQuery):
    await edit_admin_panel(callback)


@dp.callback_query(lambda c: c.data == "main_menu")
async def back_to_main(call: types.CallbackQuery):
    user_id = call.from_user.id
    await edit_main_menu(call, user_id)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())