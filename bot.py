import asyncio

ARTICLE_LOCK = asyncio.Lock()

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

            parts = line.strip().split("|")
            if len(parts) < 3:
                continue

            uid = int(parts[0])
            money = int(parts[1])
            articles = int(parts[2])
            title = parts[3] if len(parts) > 3 else "Нет"

            used_articles = []
            if len(parts) >= 5 and parts[4]:
                used_articles = parts[4].split(",")

            users[uid] = {
                "money": money,
                "articles": articles,
                "title": title,
                "used_articles": used_articles
            }

    return users


async def save_users(users):
    async with ARTICLE_LOCK:
        os.makedirs("data", exist_ok=True)
        tmp_file = USERS_FILE + ".tmp"

        with open(tmp_file, "w", encoding="utf-8") as f:
            for uid, data in users.items():
                used = ",".join(data["used_articles"])
                f.write(
                    f"{uid}|{data['money']}|{data['articles']}|{data['title']}|{used}\n"
                )

        os.replace(tmp_file, USERS_FILE)


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
    user = users.get(user_id)

    if not user:
        user = {
            "money": 0,
            "articles": 0,
            "title": "Нет",
            "used_articles": []
        }
        users[user_id] = user
        return user

    # ⬇️ КРИТИЧЕСКИ ВАЖНО
    if "used_articles" not in user:
        user["used_articles"] = []

    if "money" not in user:
        user["money"] = 0

    if "articles" not in user:
        user["articles"] = 0

    if "title" not in user:
        user["title"] = "Нет"

    return user


async def give_article(update, context, pool):
    users = load_users()
    user = get_user(users, update.effective_user.id)

    loading = await update.message.reply_text("Загрузка...")

    try:
        if not pool:
            await update.message.reply_text("Статьи закончились.")
            return

        article = random.choice(pool)

        # НАГРАДА
        if random.randint(1, 100) <= 4:
            money = 1
        else:
            money = 100

        user["money"] += money
        user["articles"] += 1

        await save_users(users)
        await update.message.reply_text(
            f"{article}\n\n"
            f"🥬 +{money}\n"
            f"Всего капусты: {user['money']}\n"
            f"Всего статей: {user['articles']}"
        )

    finally:
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
    print(update.effective_user.id)
    
    users = load_users()
    user = get_user(users, update.effective_user.id)

    await update.message.reply_text(
        f"Профиль разыскиваемого\n\n"
        f"Капусты: {user['money']}\n"
        f"Статьи: {user['articles']}\n"
        f"Титул: {user['title']}"
    )


async def wanted_list(update, context):
    await update.message.reply_text("Список разыскиваемых")


async def top_money(update, context):
    users = load_users()
    top = sorted(users.items(), key=lambda x: x[1]["money"], reverse=True)[:30]

    text = "Топ 30 по капусте:\n"
    for i, (uid, data) in enumerate(top, 1):
        text += f"{i}. {uid} — {data['money']}Капусты\n"

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

    await save_users(users)

    await update.message.reply_text(f"Титул {title_name} куплен")
    
async def admin_restore(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Использование: /admin_restore ID")
        return

    target_id = int(context.args[0])

    users = load_users()
    user = get_user(users, target_id)

    user["money"] += 13000
    user["articles"] += 135

    await save_users(users)

    await update.message.reply_text(
        "✅ ВОССТАНОВЛЕНО:\n"
        "🥬 +13 000 капусты\n"
        "📄 +135 статей\n"
        "🎖 Титул покупается самостоятельно"
    )
    
    TOKEN = "8388511848:AAEMnwXxJ6-gidIUWhZTuNOlsNxmQvynZV8"
    
    def main():
        print("MAIN STARTED")
    
    app = Application.builder().token(TOKEN).build()

  
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(re.compile(r"^гб статья$", re.IGNORECASE)),
            gb_article
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(re.compile(r"^ук рф статья$", re.IGNORECASE)),
            ukrf_article
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"(?i)^\s*гб\s+инфо\s*$"),
            gb_info
        )
    )

    app.add_handler(CommandHandler("gb_info", gb_info))

    
    app.add_handler(MessageHandler(filters.Regex(r"^Профиль разыскиваемого$"), profile))
    app.add_handler(MessageHandler(filters.Regex(r"^Список разыскиваемых$"), wanted_list))
    app.add_handler(MessageHandler(filters.Regex(r"^Топ капусты$"), top_money))
    app.add_handler(MessageHandler(filters.Regex(r"^Топ статей$"), top_articles))
    app.add_handler(MessageHandler(filters.Regex(r"^Магаз титулов$"), shop_titles))
    app.add_handler(MessageHandler(filters.Regex(r"^Купить титул .+"), buy_title))

    app.add_handler(CommandHandler("admin_restore", admin_restore))

    print("STARTING POLLING")
    app.run_polling()
    

if __name__ == "__main__":
    main()
