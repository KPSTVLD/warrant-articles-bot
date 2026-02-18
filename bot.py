import random
import time
import os
from collections import deque
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("TOKEN")

# ====== ФАЙЛЫ ======
UK_FILE = "data/uk_rf.txt"
GB_FILE = "data/gb.txt"
TITLES_FILE = "data/titles.txt"
DATA_FILE = "data/users_data.txt"

# ====== НАГРАДЫ ======
NORMAL_REWARD = 100
RARE_REWARD = 1
RARE_CHANCE = 0.04  # 4%

# ====== ПАМЯТЬ ======
uk_queue = deque()
gb_queue = deque()
users = {}

# ====== ЗАГРУЗКА ======
def load_articles():
    global uk_queue, gb_queue
    with open(UK_FILE, encoding="utf-8") as f:
        uk = [line.strip() for line in f if line.strip()]
    with open(GB_FILE, encoding="utf-8") as f:
        gb = [line.strip() for line in f if line.strip()]
    random.shuffle(uk)
    random.shuffle(gb)
    uk_queue = deque(uk)
    gb_queue = deque(gb)

def load_users():
    if not os.path.exists(DATA_FILE):
        return
    with open(DATA_FILE, encoding="utf-8") as f:
        for line in f:
            uid, cap, arts, title = line.strip().split("|")
            users[int(uid)] = {
                "cap": int(cap),
                "arts": int(arts),
                "title": title
            }

def save_users():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        for uid, d in users.items():
            f.write(f"{uid}|{d['cap']}|{d['arts']}|{d['title']}\n")

# ====== ВСПОМОГ ======
def get_reward():
    if random.random() < RARE_CHANCE:
        return RARE_REWARD
    return NORMAL_REWARD

def cap_text(n):
    return "Капуста" if n == 1 else "Капусты"

# ====== ВЫДАЧА СТАТЕЙ ======
async def give_article(update: Update, context: ContextTypes.DEFAULT_TYPE, kind: str):
    uid = update.effective_user.id
    name = update.effective_user.first_name

    if uid not in users:
        users[uid] = {"cap": 0, "arts": 0, "title": "Без титула"}

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Проверяю наличие преступника..."
    )

    time.sleep(1.5)

    queue = uk_queue if kind == "uk" else gb_queue
    source = UK_FILE if kind == "uk" else GB_FILE

    if not queue:
        load_articles()
        queue = uk_queue if kind == "uk" else gb_queue

    article = queue.popleft()
    reward = get_reward()

    users[uid]["cap"] += reward
    users[uid]["arts"] += 1
    save_users()

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f"{article}\n\n"
            f"Получено: {reward} {cap_text(reward)}\n"
            f"Всего статей: {users[uid]['arts']}"
        )
    )

# ====== КОМАНДЫ ======
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()

    if text == "ук рф статьи":
        await give_article(update, context, "uk")

    elif text == "гб статьи":
        await give_article(update, context, "gb")

    elif text == "профиль разыскиваемого":
        uid = update.effective_user.id
        if uid not in users:
            users[uid] = {"cap": 0, "arts": 0, "title": "Без титула"}
        u = users[uid]
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"Профиль:\n"
                f"Титул: {u['title']}\n"
                f"Статей: {u['arts']}\n"
                f"Капуста: {u['cap']} {cap_text(u['cap'])}"
            )
        )

    elif text == "магаз титулов":
        if not os.path.exists(TITLES_FILE):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Магазин пуст."
            )
            return
        msg = "Магаз титулов:\n"
        with open(TITLES_FILE, encoding="utf-8") as f:
            for line in f:
                name, price = line.strip().split("|")
                msg += f"{name} — {price} Капусты\n"
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=msg
        )

    elif text == "гб инфо":
        total_users = len(users)
        total_arts = sum(u["arts"] for u in users.values())
        total_cap = sum(u["cap"] for u in users.values())
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"ГБ Инфо:\n"
                f"Пользователей: {total_users}\n"
                f"Всего статей: {total_arts}\n"
                f"Всего капусты: {total_cap}"
            )
        )

# ====== ЗАПУСК ======
def main():
    load_articles()
    load_users()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    app.run_polling()

if __name__ == "__main__":
    main()
