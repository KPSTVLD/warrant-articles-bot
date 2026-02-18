import os
import random
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TOKEN")

DATA_FILE = "data/users_data.txt"

ARTICLES_GB = [
    "Статья 105. Убийство",
    "Статья 158. Кража",
    "Статья 161. Грабёж",
]

ARTICLES_UKRF = [
    "Стаття 115. Умисне вбивство",
    "Стаття 185. Крадіжка",
    "Стаття 186. Грабіж",
]


def load_users():
    users = {}
    if not os.path.exists(DATA_FILE):
        return users

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            user_id, money, articles = line.strip().split("|")
            users[int(user_id)] = {
                "money": int(money),
                "articles": int(articles)
            }
    return users


def save_users(users):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        for user_id, data in users.items():
            f.write(f"{user_id}|{data['money']}|{data['articles']}\n")


async def give_article(update: Update, context: ContextTypes.DEFAULT_TYPE, article_list):
    user_id = update.effective_user.id
    users = load_users()

    if user_id not in users:
        users[user_id] = {"money": 0, "articles": 0}

    loading = await update.message.reply_text("Загрузка...")

    article = random.choice(article_list)

    money_gain = 1 if random.random() < 0.04 else random.randint(5, 20)

    users[user_id]["money"] += money_gain
    users[user_id]["articles"] += 1

    save_users(users)

    await update.message.reply_text(
        f"{article}\n\n"
        f"Капуста: +{money_gain}\n"
        f"Всего капусты: {users[user_id]['money']}\n"
        f"Всего статьи: {users[user_id]['articles']}"
    )

    await loading.delete()


async def gb_article(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await give_article(update, context, ARTICLES_GB)


async def ukrf_article(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await give_article(update, context, ARTICLES_UKRF)


async def gb_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Команды бота:\n"
        "Гб статья\n"
        "Ук рф статья\n"
        "гб инфо\n"
        "Список разыскиваемых"
    )


async def wanted_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выбери статистику:\n"
        "Топ капуста\n"
        "Топ статьи"
    )


async def top_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    sorted_users = sorted(users.items(), key=lambda x: x[1]["money"], reverse=True)[:30]

    text = "Топ 30 по капусте:\n"
    for i, (uid, data) in enumerate(sorted_users, start=1):
        text += f"{i}. {uid} — {data['money']} капусты\n"

    await update.message.reply_text(text)


async def top_articles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    sorted_users = sorted(users.items(), key=lambda x: x[1]["articles"], reverse=True)[:30]

    text = "Топ 30 по статьи:\n"
    for i, (uid, data) in enumerate(sorted_users, start=1):
        text += f"{i}. {uid} — {data['articles']} статьи\n"

    await update.message.reply_text(text)


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.Regex("^Гб статья$"), gb_article))
    app.add_handler(MessageHandler(filters.Regex("^Ук рф статья$"), ukrf_article))
    app.add_handler(MessageHandler(filters.Regex("^гб инфо$"), gb_info))
    app.add_handler(MessageHandler(filters.Regex("^Список разыскиваемых$"), wanted_list))
    app.add_handler(MessageHandler(filters.Regex("^Топ капуста$"), top_money))
    app.add_handler(MessageHandler(filters.Regex("^Топ статьи$"), top_articles))

    app.run_polling()


if __name__ == "__main__":
    main()
