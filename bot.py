import telebot
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

DATA_FILE = "data.json"

MONTHS = ["01","02","03","04","05","06","07","08","09","10","11","12"]
CATEGORIES = ["еда","транспорт","развлечения","квартира","коммуналка","кредиты","авто","прочее"]

DEFAULT_BUDGET = 100000

# ---------------- DATA ----------------
def load():
    if os.path.exists(DATA_FILE):
        try:
            d = json.load(open(DATA_FILE,"r",encoding="utf-8"))
            return d if isinstance(d, dict) else {}
        except:
            return {}
    return {}

def save():
    json.dump(data, open(DATA_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

data = load()
state = {}

# ---------------- SAFE INIT ----------------
def ensure(uid):
    if uid not in data or not isinstance(data.get(uid), dict):
        data[uid] = {}

    for m in MONTHS:
        if m not in data[uid]:
            data[uid][m] = []

    if "budget" not in data[uid]:
        data[uid]["budget"] = DEFAULT_BUDGET

# ---------------- MENU ----------------
def menu():
    kb = telebot.types.InlineKeyboardMarkup()

    kb.row(
        telebot.types.InlineKeyboardButton("💰 Доход", callback_data="income"),
        telebot.types.InlineKeyboardButton("💸 Расход", callback_data="expense")
    )

    kb.row(
        telebot.types.InlineKeyboardButton("⚡ Баланс", callback_data="balance"),
        telebot.types.InlineKeyboardButton("📊 Отчет", callback_data="report")
    )

    kb.row(
        telebot.types.InlineKeyboardButton("💡 Совет", callback_data="advice")
    )

    kb.row(
        telebot.types.InlineKeyboardButton("📅 Год график", callback_data="year_graph")
    )

    return kb

def cat_menu():
    kb = telebot.types.InlineKeyboardMarkup()
    for c in CATEGORIES:
        kb.add(telebot.types.InlineKeyboardButton(c, callback_data=f"cat_{c}"))
    return kb

# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id,
        "🏦 FINANCE BOT\n💰 Контроль бюджета",
        reply_markup=menu())

# ---------------- CALLBACK ----------------
@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    uid = str(c.message.chat.id)
    ensure(uid)

    if c.data == "income":
        state[uid] = "income"
        bot.send_message(c.message.chat.id,"💰 Введи доход:")

    elif c.data == "expense":
        state[uid] = "expense_cat"
        bot.send_message(c.message.chat.id,"Выбери категорию:",reply_markup=cat_menu())

    elif c.data == "balance":
        inc, exp = calc(uid)
        bot.send_message(c.message.chat.id,f"⚡ Баланс: {inc-exp}")

    elif c.data == "report":
        report(c.message.chat.id, uid)

    elif c.data == "advice":
        bot.send_message(c.message.chat.id, advice(uid))

    elif c.data == "year_graph":
        year_graph(c.message.chat.id, uid)

    elif c.data.startswith("cat_"):
        cat = c.data.replace("cat_","")
        state[uid] = f"expense_{cat}"
        bot.send_message(c.message.chat.id,"💸 Введи сумму:")

# ---------------- TEXT ----------------
@bot.message_handler(func=lambda m: True)
def msg(m):
    uid = str(m.chat.id)
    mth = datetime.now().strftime("%m")
    ensure(uid)

    try:
        val = float(m.text)
    except:
        return

    # income
    if uid in state and state[uid] == "income":
        data[uid][mth].append({"type":"income","amount":val})
        save()
        state[uid] = None
        bot.send_message(m.chat.id,"✅ Доход добавлен",reply_markup=menu())
        return

    # expense
    if uid in state and state[uid].startswith("expense_"):
        cat = state[uid].replace("expense_","")

        data[uid][mth].append({
            "type":"expense",
            "amount":val,
            "category":cat
        })

        save()
        state[uid] = None

        bot.send_message(m.chat.id,"💸 Расход добавлен",reply_markup=menu())
        # ---------------- CALC ----------------
def calc(uid):
    inc = 0
    exp = 0

    for m in MONTHS:
        for i in data.get(uid, {}).get(m, []):
            if i["type"]=="income":
                inc += i["amount"]
            else:
                exp += i["amount"]

    return inc, exp



# ---------------- ADVICE ----------------
def advice(uid):
    m = datetime.now().strftime("%m")
    exp = data[uid][m]

    if not exp:
        return "🧠 Нет данных"

    cats = {}
    total = 0

    for i in exp:
        if i["type"]=="expense":
            cats[i["category"]] = cats.get(i["category"],0)+i["amount"]
            total += i["amount"]

    if not cats:
        return "🧠 Нет расходов"

    top = max(cats, key=cats.get)

    return f"""
💡 СОВЕТ БАНКА

📌 Главная трата: {top}
💸 Всего: {total}

👉 Рекомендуем снизить {top} на 10-20%
"""

# ---------------- REPORT ----------------
def report(chat_id, uid):
    m = datetime.now().strftime("%m")

    inc = sum(i["amount"] for i in data[uid][m] if i["type"]=="income")
    exp = sum(i["amount"] for i in data[uid][m] if i["type"]=="expense")

    bot.send_message(chat_id,
        f"""
📊 ОТЧЕТ

💰 Доход: {inc}
💸 Расход: {exp}
⚡ Баланс: {inc-exp}
""", reply_markup=menu())

# ---------------- YEAR GRAPH ----------------
def year_graph(chat_id, uid):
    incs = []
    exps = []

    for m in MONTHS:
        incs.append(sum(i["amount"] for i in data.get(uid, {}).get(m, []) if i["type"]=="income"))
        exps.append(sum(i["amount"] for i in data.get(uid, {}).get(m, []) if i["type"]=="expense"))

    plt.figure()

    plt.plot(MONTHS, incs, label="Доход")
    plt.plot(MONTHS, exps, label="Расход")

    plt.legend()

    file = f"year_{chat_id}.png"
    plt.savefig(file)
    plt.close()

    bot.send_photo(chat_id, open(file,"rb"))

if __name__ == "__main__":
    print("BOT STARTED")
    bot.infinity_polling()
