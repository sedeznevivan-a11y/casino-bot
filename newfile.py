import asyncio, random, sqlite3, logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)
bot = Bot(token="8825080659:AAERBPHmb-fVyBJvP69bRbDepK5BlR2Vhhk")
dp = Dispatcher()
games = {}

db = sqlite3.connect("casino_db.db", check_same_thread=False)
cur = db.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance REAL DEFAULT 1000.0, dep_sum REAL DEFAULT 0.0, win_sum REAL DEFAULT 0.0, is_mod INTEGER DEFAULT 0)")
db.commit()

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    await m.answer("🎮 **Double Cash Bot** на Aiogram!\n💣 `/mines`, `/crash` [ставка]\n💳 `/balance` | `/admin`", parse_mode="Markdown")

@dp.message(Command("balance"))
async def cmd_bal(m: types.Message):
    cur.execute("SELECT balance FROM users WHERE user_id = ?", (str(m.from_user.id),))
    r = cur.fetchone()
    bal = r[0] if r else 1000.0
    if not r:
        cur.execute("INSERT INTO users (user_id) VALUES (?)", (str(m.from_user.id),))
        db.commit()
    await m.answer(f"💳 Баланс: {round(bal, 2)}₽")

@dp.message(Command("admin"))
async def cmd_admin(m: types.Message):
    if str(m.from_user.id) != "8034889148": return
    await m.answer("👑 **Панель Владельца Казино**\n\nБот успешно запущен на сервере Render!")

@dp.message(Command("crash"))
async def cmd_crash(m: types.Message):
    p = m.text.split()
    if len(p) < 2:
        return await m.answer("⚠️ Укажите ставку: `/crash 100`")
    bet = float(p[1])
    msg = await m.answer("🚀 **Ракета взлетает...**\n📈 Множитель: **x1.00**")
    crash_point = round(random.uniform(1.1, 3.5), 2)
    current_x = 1.0
    for _ in range(5):
        await asyncio.sleep(0.8)
        current_x += round(random.uniform(0.1, 0.4), 2)
        if current_x >= crash_point:
            return await msg.edit_text(f"💥 **РАКЕТА КРАШНУЛАСЬ!**\n📈 Множитель взрыва: **x{round(crash_point, 2)}**\n💸 Ставка {bet}₽ сгорела.")
        await msg.edit_text(f"🚀 **Ракета летит!**\n📈 Текущий множитель: **x{round(current_x, 2)}**")
    win = round(bet * crash_point, 2)
    await m.answer(f"👑 **Успешный вывод!**\n🚀 Ракета долетела до: **x{round(crash_point, 2)}**\n💰 Выигрыш: **+{win}₽**")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
