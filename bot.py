import re
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

import os
import random

TOKEN = os.getenv("TOKEN")

USERS_FILE = "data/users_data.txt"
TITLES_FILE = "data/titles.txt"


# ---------- ДАННЫЕ ----------

def load_users():
    users = {}
    if not os.path.exists(USERS_FILE):
        return users

    with open(USERS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            uid, money, articles, title = line.strip().split("|")
            users[int(uid)] = {
                "money": int(money),
                "articles": int(articles),
                "title": title
            }
    return users


def save_users(users):
    os.makedirs("data", exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        for uid, data in users.items():
            f.write(f"{uid}|{data['money']}|{data['articles']}|{data['title']}\n")


def load_articles(path):
    articles = []
    if not os.path.exists(path):
        return articles

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            articles.append(line)

    return articles


def load_titles():
    titles = {}
    if not os.path.exists(TITLES_FILE):
        return titles

    with open(TITLES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            name, price = line.strip().split("|")
            titles[name] = int(price)

    return titles

ARTICLES_GB = load_articles("data/gb.txt")
ARTICLES_UKRF = load_articles("data/uk_rf.txt")


def get_user(users, user_id):
    if user_id not in users:
        users[user_id] = {
            "money": 0,
            "articles": 0,
            "title": "Нет"
            "used_articles": []   # ← ВАЖНО
        }
    return users[user_id]


async def give_article(update, context, pool):
    users = load_users()
    user = get_user(users, update.effective_user.id)

    used = set(user.get("used_articles", []))
    available = [a for a in pool if a not in used]

    # если всё выбито — сбрасываем
    if not available:
        user["used_articles"] = []
        available = pool.copy()

    loading = await update.message.reply_text("Загрузка...")

    article = random.choice(available)

    user["used_articles"].append(article)
    user["articles"] += 1

    money = 1 if random.random() < 0.04 else random.randint(5, 20)
    user["money"] += money

    save_users(users)

    await update.message.reply_text(
        f"{article}\n\n"
        f"Капуста: +{money}\n"
        f"Всего капусты: {user['money']}\n"
        f"Всего статей: {user['articles']}"
    )

    await loading.delete()


# ---------- КОМАНДЫ ----------

async def gb_article(update, context):
    await give_article(update, context, ARTICLES_GB)

async def ukrf_article(update, context):
    await give_article(update, context, ARTICLES_UKRF)


async def gb_info(update, context):
    await update.message.reply_text(
        "Команды бота:\n"
        "Гб статья\n"
        "Ук рф статья\n"
        "Профиль разыскиваемого\n"
        "Список разыскиваемых\n"
        "Магаз титулов\n"
        "Купить титул НАЗВАНИЕ"
    )


async def profile(update, context):
    users = load_users()
    user = get_user(users, update.effective_user.id)

    await update.message.reply_text(
        f"Профиль разыскиваемого\n\n"
        f"Капуста: {user['money']}\n"
        f"Статьи: {user['articles']}\n"
        f"Титул: {user['title']}"
    )


async def wanted_list(update, context):
    await update.message.reply_text(
        "Статистика:\n"
        "Топ капуста\n"
        "Топ статьи"
    )


async def top_money(update, context):
    users = load_users()
    top = sorted(users.items(), key=lambda x: x[1]["money"], reverse=True)[:30]

    text = "Топ 30 по капусте:\n"
    for i, (uid, data) in enumerate(top, 1):
        text += f"{i}. {uid} — {data['money']}\n"

    await update.message.reply_text(text)


async def top_articles(update, context):
    users = load_users()
    top = sorted(users.items(), key=lambda x: x[1]["articles"], reverse=True)[:30]

    text = "Топ 30 по статьи:\n"
    for i, (uid, data) in enumerate(top, 1):
        text += f"{i}. {uid} — {data['articles']}\n"

    await update.message.reply_text(text)


async def shop_titles(update, context):
    titles = load_titles()
    if not titles:
        await update.message.reply_text("Титулы отсутствуют")
        return

    text = "Магаз титулов:\n"
    for name, price in titles.items():
        text += f"{name} — {price} капусты\n"

    await update.message.reply_text(text)


async def buy_title(update, context):
    titles = load_titles()
    users = load_users()
    user = get_user(users, update.effective_user.id)

    title_name = update.message.text.replace("Купить титул ", "").strip()

    if title_name not in titles:
        await update.message.reply_text("Такого титула нет")
        return

    price = titles[title_name]

    if user["money"] < price:
        await update.message.reply_text("Недостаточно капусты")
        return

    user["money"] -= price
    user["title"] = title_name
    save_users(users)

    await update.message.reply_text(f"Титул {title_name} куплен")


# ---------- ЗАПУСК ----------

def main():
    app = Application.builder().token(TOKEN).build()

    # ===== СТАТЬИ (РЕГИСТР НЕ ВАЖЕН) =====
    app.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^гб статья$", re.IGNORECASE)),
            gb_article
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"^ук рф статья$", re.IGNORECASE)),
            ukrf_article
        )
    )

    # ===== КОМАНДЫ =====
    app.add_handler(CommandHandler("gb_info", gb_info))

    app.add_handler(MessageHandler(filters.Regex(r"^Профиль разыскиваемого$"), profile))
    app.add_handler(MessageHandler(filters.Regex(r"^Список разыскиваемых$"), wanted_list))
    app.add_handler(MessageHandler(filters.Regex(r"^Топ капуста$"), top_money))
    app.add_handler(MessageHandler(filters.Regex(r"^Топ статьи$"), top_articles))
    app.add_handler(MessageHandler(filters.Regex(r"^Магаз титулов$"), shop_titles))
    app.add_handler(MessageHandler(filters.Regex(r"^Купить титул .+"), buy_title))

    # ===== ЗАПУСК (СТРОГО ПОСЛЕДНИЙ) =====
    app.run_polling()


if __name__ == "__main__":
    main()
