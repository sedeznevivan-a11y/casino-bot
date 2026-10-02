import asyncio
import random
import sqlite3
import logging
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

logging.basicConfig(level=logging.INFO)
bot = Bot(token="8825080659:AAFtgFVLApTstJQW512pPHjbu3CHRS7g8EM")
dp = Dispatcher()
games = {}

# Железобетонная инициализация оригинальной базы данных
db = sqlite3.connect("casino_db.db", check_same_thread=False)
cur = db.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance REAL DEFAULT 0.0, dep_sum REAL DEFAULT 0.0, win_sum REAL DEFAULT 0.0, is_mod INTEGER DEFAULT 0)")
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
        return [0.0, 0]
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
    await m.answer("🎮 **Double Cash Bot**\n💣 `/mines`, `/lesenka`, `/cube`, `/crash`\n💳 `/balance`, `/deposit`, `/withdraw`", parse_mode="Markdown", reply_markup=kb)

@dp.message(Command("balance"))
async def cmd_bal(m: types.Message):
    bal, _ = get_u(m.from_user.id)
    await m.answer(f"💳 Баланс: {round(bal, 2)}₽")

@dp.message(Command("admin"))
async def cmd_admin(m: types.Message):
    if str(m.from_user.id) != "8034889148": return
    cur.execute("SELECT COUNT(*), SUM(balance), SUM(dep_sum), SUM(win_sum) FROM users")
    res = cur.fetchone()
    await m.answer(f"👑 **Админка**\n👤 Игроков: {res[0] or 0}\n💰 Банк: {round(res[1] or 0, 2)}₽\n📥 Депо: {round(res[2] or 0, 2)}₽\n📤 Выплаты: {round(res[3] or 0, 2)}₽\n\n/reord | /rtp [0-100] | /rtp-\n/moder [ID] — Поставить модера\n/выдать [ID] [сумма]\n/убрать [ID] [сумма]\n/spam [текст]")

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
    cur.execute("UPDATE config SET value = ? WHERE key = 'rtp_mode'", (v,))
    db.commit()
    await m.answer(f"⚙️ RTP: **{v}**")

@dp.message(Command("rtp-"))
async def cmd_rtp_m(m: types.Message):
    if str(m.from_user.id) == "8034889148":
        cur.execute("UPDATE config SET value = '15' WHERE key = 'rtp_mode'")
        db.commit()
        await m.answer("📉 Режим слива включен!")

@dp.message(Command("setcard"))
async def cmd_setcard(m: types.Message):
    if str(m.from_user.id) == "8034889148":
        card_text = m.text.replace("/setcard", "").strip()
        cur.execute("UPDATE config SET value = ? WHERE key = 'card'", (card_text,))
        db.commit()
        await m.answer("✅ Карта изменена!")

@dp.message(Command("moder"))
async def cmd_moder(m: types.Message):
    if str(m.from_user.id) != "8034889148": return
    p = m.text.split()
    if len(p) >= 2:
        cur.execute("UPDATE users SET is_mod = 1 WHERE user_id = ?", (p[1],))
        db.commit()
        await m.answer(f"✅ Игрок {p[1]} назначен Модератором!")

@dp.message(Command("выдать"))
async def cmd_give(m: types.Message):
    uid = str(m.from_user.id)
    _, is_mod = get_u(uid)
    if uid != "8034889148" and is_mod != 1: return
    p = m.text.split()
    if len(p) >= 3:
        t_id, amt = p[1], float(p[2])
        if t_id == uid and uid != "8034889148":
            return await m.answer("⚠️ Модератор не может выдавать баланс сам себе!")
        cur.execute("UPDATE users SET balance = balance + ?, dep_sum = dep_sum + ? WHERE user_id = ?", (amt, amt, t_id))
        db.commit()
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
        t_id, amt = p[1], float(p[2])
        cur.execute("UPDATE users SET balance = max(0.0, balance - ?) WHERE user_id = ?", (amt, t_id))
        db.commit()
        await m.answer(f"📉 Списано **{amt}₽** у {t_id}")

@dp.message(Command("spam"))
async def cmd_spam(m: types.Message):
    if str(m.from_user.id) == "8034889148":
        t = m.text.replace("/spam", "").strip()
        if t:
            cur.execute("SELECT user_id FROM users")
            for row in cur.fetchall():
                try: await bot.send_message(int(row[0]), t, parse_mode="Markdown")
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
        cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (am, str(m.from_user.id)))
        db.commit()
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"w_ok_{m.from_user.id}_{am}"),
            InlineKeyboardButton(text="✖️ Отклонить", callback_data=f"w_no_{m.from_user.id}_{am}")
        ]])
        await bot.send_message(8034889148, f"📥 **Заявка на вывод средств!**\n👤 Игрок: `{m.from_user.id}`\n💰 Сумма: **{am}₽**", reply_markup=kb)
        await m.answer("⚠️ **Заявка отправлена Администрации!** Ожидайте одобрения.")

@dp.message(Command("mines", "lesenka"))
async def cmd_setup_game(m: types.Message):
    uid = str(m.from_user.id)
    bal, _ = get_u(uid)
    p = m.text.split()
    is_m = m.text.startswith("/mines")
    mc = int(p[1]) if len(p) > 1 and p[1].isdigit() else (2 if is_m else 1)
    bet = float(p[2]) if len(p) > 2 else 100.0
    
    if (is_m and (mc < 2 or mc > 24)) or (not is_m and (mc < 1 or mc > 4)) or bal < bet:
        return await m.answer("⚠️ Ошибка баланса или параметров игры!")
        
    cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, uid))
    db.commit()
    
    g_id = random.randint(100, 999)
    if is_m:
        mines = set(random.sample([(r, c) for r in range(5) for c in range(5)], mc))
        games[uid] = {"id": g_id, "type": "mines", "m": mines, "o": set(), "bet": bet, "status": "play", "total_mines": mc}
        await m.answer(f"💎 Ставка: {bet}₽", reply_markup=get_mines_kb(games[uid]))
    else:
        mines = set()
        for r in range(6):
            for c in random.sample(range(5), mc): mines.add((r, c))
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
    
