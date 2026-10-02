import asyncio, logging, sys, random, json, sqlite3
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, BaseFilter
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

TOKEN = "8825080659:AAFes2YH252UQarUm4txhw5fKTicv-vENaY"  
ADMIN_ID = 8034889148          

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp, DB_FILE = Dispatcher(), "bot_database.db"

def query_db(sql, params=(), fetch=False, commit=False):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute(sql, params)
        if commit: conn.commit()
        return c.fetchall() if fetch else c.fetchone()

query_db('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 1000.0, games_played INTEGER DEFAULT 0, games_won INTEGER DEFAULT 0)', commit=True)
query_db('CREATE TABLE IF NOT EXISTS active_games (user_id INTEGER PRIMARY KEY, game_type TEXT, bet REAL, mines_count INTEGER, grid TEXT, current_step INTEGER DEFAULT 0, revealed TEXT)', commit=True)

def get_user(uid, name=""):
    r = query_db("SELECT user_id, username, balance, games_played, games_won FROM users WHERE user_id = ?", (uid,))
    if not r:
        query_db("INSERT INTO users (user_id, username, balance) VALUES (?, ?, 1000.0)", (uid, name), commit=True)
        r = query_db("SELECT user_id, username, balance, games_played, games_won FROM users WHERE user_id = ?", (uid,))
    return {"user_id": r, "username": r, "balance": r, "games_played": r, "games_won": r}

class IsAdmin(BaseFilter):
    async def __call__(self, m: Message) -> bool: return m.from_user.id == ADMIN_ID

def get_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💰 Пополнить баланс")], [KeyboardButton(text="💸 Вывести")]], resize_keyboard=True)

@dp.message(CommandStart())
async def cmd_start(m: Message):
    get_user(m.from_user.id, m.from_user.username)
    await m.answer("Добро пожаловать в игровой бот!\n🎲 /chet [ставка], /nechet [ставка], /cub [ставка] [число]\n💣 /mines [мины 2 или 4] [ставка]", reply_markup=get_menu())

@dp.message(F.text == "👤 Профиль")
async def menu_profile(m: Message):
    u = get_user(m.from_user.id, m.from_user.username)
    await m.answer(f"👤 <b>Профиль:</b>\nID: <code>{u['user_id']}</code>\nБаланс: <b>{u['balance']:.2f} руб.</b>\nИгр: {u['games_played']} | Побед: {u['games_won']}")

@dp.message(F.text == "💰 Пополнить баланс")
async def menu_dep(m: Message): await m.answer("Минимум — 300 руб. Отправьте число (например, 500) для заявки.")

@dp.message(F.text == "💸 Вывести")
async def menu_wit(m: Message): await m.answer("Отправьте число суммы для вывода (например, 400) для заявки.")

@dp.message(Command("nechet", "chet"))
async def play_dice(m: Message):
    u = get_user(m.from_user.id, m.from_user.username)
    args = m.text.split()
    if len(args) < 2 or not args.replace('.', '', 1).isdigit(): return await m.answer("Формат: /chet или /nechet [ставка]")
    bet = float(args)
    if u['balance'] < bet or bet <= 0: return await m.answer("Недостаточно баланса!")
    query_db("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, m.from_user.id), commit=True)
    val = random.randint(1, 6)
    is_win = (val % 2 != 0 if "nechet" in m.text else val % 2 == 0)
    query_db("UPDATE users SET games_played = games_played + 1 WHERE user_id = ?", (m.from_user.id,), commit=True)
    if is_win: query_db("UPDATE users SET games_won = games_won + 1, balance = balance + ? WHERE user_id = ?", (bet * 1.9, m.from_user.id), commit=True)
    t = f"🎲 Выпало {val} (" + ("НЕЧЕТ" if val%2!=0 else "ЧЕТ") + ")!\n"
    await m.answer(t + (f"Поздравляем вас с победой! Выиграно {bet*1.9:.2f} руб." if is_win else "Сожалеем, повезет в следующий раз"))

@dp.message(Command("cub"))
async def play_cub(m: Message):
    u = get_user(m.from_user.id, m.from_user.username)
    args = m.text.split()
    if len(args) < 3 or not args.replace('.', '', 1).isdigit() or not args.isdigit(): return await m.answer("Формат: /cub [ставка] [1-6]")
    bet, chs = float(args), int(args)
    if chs < 1 or chs > 6 or u['balance'] < bet or bet <= 0: return await m.answer("Ошибка в ставке или числе!")
    query_db("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, m.from_user.id), commit=True)
    val = random.randint(1, 6)
    is_win = (val == chs)
    query_db("UPDATE users SET games_played = games_played + 1 WHERE user_id = ?", (m.from_user.id,), commit=True)
    if is_win: query_db("UPDATE users SET games_won = games_won + 1, balance = balance + ? WHERE user_id = ?", (bet * 6.0, m.from_user.id), commit=True)
    await m.answer(f"🎲 Выпало {val}! " + (f"Поздравляем вас с победой! Выигрыш: {bet*6.0:.2f} руб." if is_win else f"Вы загадали {chs}. Сожалеем, повезет в следующий раз"))

def get_act(uid):
    r = query_db("SELECT game_type, bet, mines_count, grid, current_step, revealed FROM active_games WHERE user_id = ?", (uid,))
    return {"game_type": r, "bet": r, "mines_count": r, "grid": json.loads(r), "current_step": r, "revealed": json.loads(r)} if r else None

@dp.message(Command("mines"))
async def start_mines(m: Message):
    u = get_user(m.from_user.id, m.from_user.username)
    if get_act(m.from_user.id): return await m.answer("Есть активная игра! Напишите /wet для восстановления.")
    args = m.text.split()
    if len(args) < 3 or not args.isdigit() or not args.replace('.', '', 1).isdigit(): return await m.answer("Формат: /mines [мины 2 или 4] [ставка]")
    mc, bet = int(args), float(args)
    if mc != 2 and mc != 4 or u['balance'] < bet or bet <= 0: return await m.answer("Ошибка ввода или баланса!")
    
    grid_str = "0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0"
    g = [int(x) for x in grid_str.split(",")]
    for i in random.sample(range(25), mc): g[i] = 1
        
    query_db("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, m.from_user.id), commit=True)
    query_db("INSERT OR REPLACE INTO active_games VALUES (?, 'mines', ?, ?, ?, 0, '[]')", (m.from_user.id, bet, mc, json.dumps(g)), commit=True)
    await send_mb(m, m.from_user.id, "Игра МИНЫ началась!")

MINES_COEFFS = {
    2: [1.0, 1.05, 1.20, 1.3, 1.4, 1.50, 1.6, 1.7, 1.9, 2.1, 2.3, 2.5, 3.5, 4.5, 5.6, 6.2, 7.9, 9.9, 13.0, 25.0, 49.0, 75.0, 130.0, 200.0],
    4: [1.11, 1.3, 1.44, 1.56, 1.66, 1.77, 2.2, 4.23, 5.6, 7.8, 9.9, 13.11, 13.11, 15.66, 17.88, 17.88, 17.88, 27.0, 75.0, 165.0, 377.0, 580.0]
}
MINES_COEFFS_4_ALT = [1.3, 1.42, 1.78, 1.99, 2.3, 4.77, 6.88, 7.56, 8.66, 12.77, 14.98, 17.75, 19.90, 21.20, 25.87, 47.99, 75.69, 122.65, 199.97, 300.0, 599.0]

async def send_mb(obj, uid, pref=""):
    g = get_act(uid)
    kb, st, mc = [], g['current_step'], g['mines_count']
    for r in range(5):
        row_btns = []
        for c in range(5):
            idx = r * 5 + c
            row_btns.append(InlineKeyboardButton(text="💎" if idx in g['revealed'] else "❓", callback_query_data=f"m_c_{idx}"))
        kb.append(row_btns)
    cfs = MINES_COEFFS if mc==2 else MINES_COEFFS_4_ALT
    cf = cfs[min(max(0, st-1), len(cfs)-1)] if st > 0 else 1.0
    if st > 0: kb.append([InlineKeyboardButton(text=f"💰 Забрать {g['bet']*cf:.2f} руб ({cf}x)", callback_query_data="m_out")])
    m = InlineKeyboardMarkup(inline_keyboard=kb)
    if isinstance(obj, CallbackQuery): await obj.message.edit_text(f"{pref}\nШаг: {st} | Коэф: {cf}x", reply_markup=m)
    else: await obj.answer(f"{pref}\nШаг: {st}", reply_markup=m)

@dp.callback_query(F.data.startswith("m_c_"))
async def click_mines(cb: CallbackQuery):
    g = get_act(cb.from_user.id)
    if not g or g['game_type'] != 'mines': return await cb.answer("Игра не найдена.")
    idx = int(cb.data.split("_"))
    if idx in g['revealed']: return await cb.answer("Уже открыто!")
    if g['grid'][idx] == 1:
        query_db("DELETE FROM active_games WHERE user_id = ?", (cb.from_user.id,), commit=True)
        query_db("UPDATE users SET games_played = games_played + 1 WHERE user_id = ?", (cb.from_user.id,), commit=True)
        return await cb.message.edit_text("💣 БУМ! Вы попали на мину!\nСожалеем, повезет в следующий раз")
    g['revealed'].append(idx)
    query_db("UPDATE active_games SET revealed = ?, current_step = current_step + 1 WHERE user_id = ?", (json.dumps(g['revealed']), cb.from_user.id), commit=True)
    await send_mb(cb, cb.from_user.id, "Отлично!")

@dp.callback_query(F.data == "m_out")
async def out_mines(cb: CallbackQuery):
    g = get_act(cb.from_user.id)
    if not g: return
    st, mc = g['current_step'], g['mines_count']
    cfs = MINES_COEFFS if mc==2 else MINES_COEFFS_4_ALT
    cf = cfs[min(max(0, st-1), len(cfs)-1)]
    query_db("DELETE FROM active_games WHERE user_id = ?", (cb.from_user.id,), commit=True)
    query_db("UPDATE users SET games_played = games_played + 1, games_won = games_won + 1, balance = balance + ? WHERE user_id = ?", (g['bet']*cf, cb.from_user.id), commit=True)
    await cb.message.edit_text(f"💎 Забрали {g['bet']*cf:.2f} руб ({cf}x)!\nПоздравляем вас с победой!")

@dp.message(F.text.regexp(r'^\d+$') | F.text.regexp(r'^\d+\.\d+$'))
async def fin_money(m: Message):
    await m.answer("Ваша заявка принята!")
    await bot.send_message(chat_id=ADMIN_ID, text=f"⚠️ ЗАЯВКА\nСумма: {m.text} руб.\nID: <code>{m.from_user.id}</code>\nЮзер: @{m.from_user.username}\n\nВыдать: <code>/выдать {m.from_user.id} {m.text}</code>")

@dp.message(Command("выдать"), IsAdmin())
async def adm_give(m: Message):
    a = m.text.split()
    if len(a) < 3: return
    query_db("UPDATE users SET balance = balance + ? WHERE user_id = ?", (float(a), int(a)), commit=True)
    await m.answer("Успешно зачислено!")
