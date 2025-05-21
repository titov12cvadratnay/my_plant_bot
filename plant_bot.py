from telebot import TeleBot, types
import sqlite3
import random
import threading
import time
import schedule

bot = TeleBot('7711021224:AAG-Hg2FiNxMuqc2jMWlwmok4nqyNcqjzyk')

connection = sqlite3.connect('plant.db', check_same_thread=False)
cursor = connection.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS plants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        water INTEGER DEFAULT 50,
        level INTEGER DEFAULT 1,
        points INTEGER DEFAULT 50,
        mood INTEGER DEFAULT 50,
        scin INTEGER DEFAULT 1,
        scin_all INTEGER DEFAULT 1
    )
''')

import os
from flask import Flask

app = Flask(__name__)

@app.route('/ping')
def ping():
    return 'OK', 200

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
def generate_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_dog = types.KeyboardButton('/dog')
    btn_water = types.KeyboardButton('/water')
    btn_shop = types.KeyboardButton('/shop')
    btn_status = types.KeyboardButton('/status')
    btn_help = types.KeyboardButton('/help')
    btn_f = types.KeyboardButton('/flowers')
    markup.row(btn_dog, btn_water)
    markup.row(btn_shop, btn_f)
    markup.row(btn_status, btn_help)
    return markup

def shop_menu():
    inline_menu_markup = types.InlineKeyboardMarkup(row_width=2)
    button1 = types.InlineKeyboardButton("Смотрите радуга🌈 25$", callback_data="Rainbow_ray") 
    button2 = types.InlineKeyboardButton("Солнечный удар☀ 25$", callback_data="Sunstroke") 
    button3 = types.InlineKeyboardButton("Тёплый дождь☔ 25$", callback_data="Warm_Rain") 
    button4 = types.InlineKeyboardButton("VIP солнце ☀☀ 99$", callback_data="VIP") 
    inline_menu_markup.add(button1) 
    inline_menu_markup.add(button2) 
    inline_menu_markup.add(button3) 
    inline_menu_markup.add(button4) 
    return inline_menu_markup

def you_user(user_id):
    cursor.execute('''SELECT COUNT(*) FROM plants WHERE user_id=?''', (user_id,))
    count = cursor.fetchone()[0]
    return bool(count)

def welcome_user(user_id):
    cursor.execute(
        '''INSERT INTO plants (user_id, water, level, points, mood, scin, scin_all) VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (user_id, 50, 1, 50, 50, 1, 1)  
    )

def data_select(user_id):
    cursor.execute('''SELECT id, user_id, water, level, points, mood FROM plants WHERE user_id=?''', (user_id,))
    result = cursor.fetchone()      
    if result is None:
        return "Игрок не найден." 
    columns = ['id', 'user_id', 'water', 'level', 'points', 'mood']
    default_values = [None]*len(columns)
    data = dict(zip(columns, result + tuple(default_values[len(result)-len(columns):])))
   
    columns = ['id', 'user_id', 'water', 'level', 'points', 'mood']
    data = dict(zip(columns, result))
    return data

import threading
from concurrent.futures import ThreadPoolExecutor

db_lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=5)

def data_update(water, level, points, mood, plant_id):
    with db_lock:
        cursor.execute("UPDATE plants SET water=?, level=?, points=?, mood=? WHERE id=?", (water, level, points, mood, plant_id,))
        connection.commit()

def send_notification(chat_id, notification):
    executor.submit(bot.send_message, chat_id, notification)


def harvest_fruits():
    cursor.execute("SELECT id, user_id, level, mood FROM plants")
    all_users = cursor.fetchall()

    for row in all_users:
        plant_id, user_id, level, mood = row
        fruits_collected = level  
        coins_per_fruit = 50  
        total_coins = fruits_collected * coins_per_fruit
        if mood > 0:
            total_coins = total_coins * 2
            new_level = level + 2 
            total_scins = 2
            bot.send_message(user_id, "🌽 Ура! Твоё растение в хорошем настроении, поэтому уровень увеличился вдвое! И у тебя новый цветок 🌾")
            cursor.execute("UPDATE plants SET scin_all=scin_all+? WHERE id=?", (total_scins ,plant_id))
        else:
            new_level = level + 1  

        cursor.execute("UPDATE plants SET level=?, points=points+? WHERE id=?", (new_level, total_coins, plant_id))
        connection.commit()

        bot.send_message(user_id, f"🌽 Ура! Пришло время собирать урожай! 🌾\nВы собрали {fruits_collected} плодов и получили {total_coins} монет. 💰\nВаш уровень вырос до {new_level}.")

schedule.every().day.at("12:59").do(harvest_fruits)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.daemon = True
scheduler_thread.start()

def update_plant_data(chat_id):
    global timer 
    data = data_select(chat_id)
    water = data['water']
    mood = data['mood']

    new_water_ = max(water - 1, 0)  
    new_mood_ = max(mood - 30, 0)  

    data_update(new_water_, data["level"], data["points"], new_mood_, data["id"])

    if new_water_ <= 10 or new_mood_ <= 10:
        alert_text = "❗ Ваше растение нуждается в уходе! А то оно завянет🥀 \n💦 Вода: {}%, 🎭 Настроение: {}%".format(new_water_, new_mood_)
        bot.send_message(chat_id, alert_text)

    if new_water_ <= 1 :
        cursor.execute("DELETE FROM plants WHERE user_id=?", (chat_id,))
        bot.send_message(chat_id, text="Ваше растение уходит от вас в далёкую страну растений😀")
        timer.cancel()

    timer = threading.Timer(60*20, update_plant_data, args=(chat_id,))
    timer.start()

def start_update_timer(chat_id):
    update_plant_data(chat_id)

def plant_all_s(plant_id):
    cursor.execute('''SELECT scin_all FROM plants WHERE user_id=?''', (plant_id,))
    result = cursor.fetchone()  
    connection.commit()
    if result:
        return result[0]
    return 0 


def plant_p(plant_id):
    cursor.execute('''SELECT scin FROM plants WHERE user_id=?''', (plant_id,))
    numb = cursor.fetchone()  
    connection.commit()
    if numb and numb[0] == 1:
        return "https://i.pinimg.com/736x/3d/ee/38/3dee387811ad501b3060d121d73d7a06.jpg"
    elif numb and numb[0] == 2:
        return "https://i.pinimg.com/736x/1f/1f/27/1f1f274c006d6ec1f586dee83f2ffbbb.jpg"
    elif numb and numb[0] == 3:
        return "https://i.pinimg.com/736x/d2/e5/0c/d2e50c00ed009b357605f9bd085cd45a.jpg"
    elif numb and numb[0] == 4:
        return "https://i.pinimg.com/736x/f1/47/1b/f1471b6adde5f4ffef281314a5704f74.jpg"
    else:
        return "https://i.pinimg.com/736x/3d/ee/38/3dee387811ad501b3060d121d73d7a06.jpg"
    
def plant_s(plant_id):
    cursor.execute('''SELECT scin FROM plants WHERE user_id=?''', (plant_id,))
    numb = cursor.fetchone()     
    connection.commit()
    if numb and numb[0] == 1:
        return "Цветок🌼"
    elif numb and numb[0] == 2:
        return "Улыбашка🤣"
    elif numb and numb[0] == 3:
        return "Зелёный🌿"
    elif numb and numb[0] == 4:
        return "Ужасный😈🛑"
    else:
        return "Такого скина нет в игре"
    

@bot.message_handler(commands=['start'])
def welcome(message):
    markup = generate_menu()
    chat_id = message.chat.id
    markup = generate_menu() 
    
    if not you_user(chat_id):
        welcome_user(chat_id)
        response_text = f"Добро пожаловать в Plants lite 🤩! Вы успешно зарегистрированы! Эта сылка на мой канал https://t.me/+l9RHgfjX-Y1kZTVi /help - это помощь"
    else:
        response_text = f"С возвращением🤩!"

    start_update_timer(chat_id)
    bot.send_photo(chat_id=chat_id, photo='https://avatars.mds.yandex.net/i?id=f92473652c7adf131c2af4a6d454b28d854c1a63-5233182-images-thumbs&n=13',caption=response_text, reply_markup=markup)
    bot.send_sticker(chat_id, "CAACAgIAAxkBAAEOa0poGaNY8B2KTQGnhTqxHQ2y1vgCvAACjwEAAladvQqTBL2ODiSRxjYE")

@bot.message_handler(commands=['help'])
def help(message):
    markup = generate_menu()
    chat_id = message.chat.id
    text_help = (   
        'Привет-привет! 🖐️🏻🌿 Приветствуем тебя в нашем уникальном мире зелёных любимцев! 🌵💨 Это бета версия\n\n'

        'Правила игры:\n'
        'Ты выращиваешь собственное уникальное растение, заботишься о нём, ухаживаешь и собираешь урожай. Чем лучше уход, тем счастливее и богаче ты станешь! 🌼💰\n\n'

        'Команды для управления:\n'
        'Команда	Действие	Смайлик\n'
        '/start	Начинает игру и регистрирует нового игрока.	🌿🚀\n'
        '/status	Показывает текущий статус растения (уровень, влажность, настроение, монеты).	📊💬\n'
        '/water	Поливает растение водой, повышает показатель влажности.	💧🌊\n'
        '/dog	Выполняет поиск монет с помощью собаки-помощника.	🐕💰\n'
        '/shop	Покупает полезные предметы для повышения здоровья и роста растения.	🛒🌹\n'
        '/help	Показывает справку по игре и доступным командам.	📝🔍\n'
        'Механизм выращивания и заработка:\n'
        'Рост растения: Чем выше уровень растения, тем больше плодов оно приносит и тем больше денег зарабатывается. 🌻💲\n'
        'Сбор урожая: Каждые сутки проводится автоматический сбор урожая в 13:00, который увеличивает количество монет и поднимает уровень растения. 🌽🎁\n'
        'Монеты: Используются для покупок полезных вещей в магазине. 💰🛒\n'
        'Уровень растения: Повышается автоматически после каждого удачного сбора урожая. 🎇🌺\n'
        'Интересные детали:\n'
        'Собаки помощники: Они помогают находить скрытые сокровища и увеличивать запасы монет. 🐕💰\n'
        'Магазин: Предлагает уникальные товары, улучшающие жизнь растения. 🛒🌼\n'
        'Автоматический полив: Если забудешь вовремя полить растение, оно начнёт страдать, а значит, снизятся шансы вырастить большой урожай. 💧🌳\n'
        'Заботься о своем растении, экспериментируй и наслаждайся ростом богатства и счастья! 🌳🌟\n'
    )
    bot.send_message(chat_id=chat_id, text=text_help, reply_markup=markup )
    bot.send_sticker(chat_id, "CAACAgIAAxkBAAEOguxoKKy0jwo6GlZ2jhGyAAGZfvgRppAAAqcBAAJWnb0Ks0y7N8sBoXA2BA")

lock = threading.Lock()

@bot.message_handler(commands=['status'])
def status_command (message):
    chat_id = message.chat.id
    data_dict = data_select(chat_id)
    markup = generate_menu()
    photo = plant_p(chat_id)
    scin = plant_s(chat_id)
    text_status = (
    f"⭐ ВАШ СТАТУС ⭐ \n"
    f"🔴 Твой ID: {data_dict['id']}  \n"
    f"🔶 🌿  ID растения: {data_dict['user_id']}  \n"
    f"🌼 💧 Вода: {data_dict['water']}%  \n"
    f"🎇 Уровень: {data_dict['level']}  \n"
    f"🎭 Настроение: {data_dict['mood']}% \n"
    f"💰 Монетки: {data_dict['points']}   \n"
    f"🎀Цветок : {scin}\n"
    "🎄 Следите за характеристиками!"
    )
    bot.send_message(chat_id=chat_id, text=text_status, reply_markup=markup )
    bot.send_sticker(chat_id, "CAACAgIAAxkBAAEObBFoGeivGKNXO5qLU58mdDeJ1NbN9QACpQEAAladvQqGK_PpTO07ZTYE")
    level = int(data_dict['level'])  
    markup = generate_menu()
    bot.send_photo(
        chat_id=chat_id,
        photo=photo,
        caption=f"Цветок {scin} Ур.{level}🎇",
        reply_markup=markup
    )
    p = 0
    for _ in range(level):
        bot.send_photo(
            chat_id=chat_id,
            photo='https://i.pinimg.com/736x/73/1c/0c/731c0cab2d76ff284e870cbb7bf8e373.jpg',
            caption=" ",
            reply_markup=markup
        )
        p  += 1
        if p > 10:
            bot.send_photo(
                chat_id=chat_id,
                photo='https://i.pinimg.com/736x/73/1c/0c/731c0cab2d76ff284e870cbb7bf8e373.jpg',
                caption="вау растение такое огромное что у меня закончились фотки 😀",
                reply_markup=markup
            )
            break

@bot.message_handler(commands=['water'])
def water(message):
    markup = generate_menu()
    chat_id = message.chat.id
    data = data_select(chat_id)

    if isinstance(data, str):
        bot.send_message(chat_id=chat_id, text=data, reply_markup=markup)
        return

    current_water = data["water"]
    bot.send_message(chat_id=chat_id, text=f"Уровень воды в растении {current_water}%💧😀", reply_markup=markup)

    if current_water == 100:
        bot.send_message(chat_id=chat_id, text=f"Ваше растение не нуждается в воде😀🌼", reply_markup=markup)
    else:
        updated_water = 100
        data_update(updated_water, data["level"], data["points"], data["mood"], data["id"])
        bot.send_message(chat_id=chat_id, text=f"Уровень воды в растении пополнен🌼 {updated_water}%💧😀", reply_markup=markup)

@bot.message_handler(commands=['shop'])
def shop (message):
    chat_id = message.chat.id
    data = data_select(chat_id)
    current_point = data["points"]
    bot.send_message(chat_id=chat_id, text=f"У вас {current_point}💰 монет 😀 \nУ каждого предмета своё свойство 🤩\nВот весь асортимент👁‍🗨", reply_markup=shop_menu())

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data_shop = call.data
    data = data_select(chat_id)
    current_point = data["points"]
    current_mood = data["mood"]
    update_mood = current_mood

    if current_point >= 25:
        lock.acquire() 

        try:

            if data_shop == "Rainbow_ray":
                update_mood = 80
                shop1(chat_id)
            elif data_shop == "Warm_Rain":
                update_mood = 81
                shop3(chat_id)
            elif data_shop == "Sunstroke":
                update_mood = 80
                shop2(chat_id)
            elif data_shop == "VIP":
                if current_point >= 99:
                    update_mood = 99
                    update_point = current_point - 74
                    shop4(chat_id)
                else:
                    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="У вас недостаточно монеток для покупки 🌼!")
                    bot.send_sticker(chat_id, "CAACAgIAAxkBAAEOgP1oJ23Broxg3oXNldf85M2-vCdM7AAClQEAAladvQp2JZLWwRjgLDYE")

            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Подождите покупка совершается 🌼!")
            update_point = current_point - 25
            data_update(data["water"], data["level"], update_point, update_mood, data["id"])
            
        finally:
            lock.release()  
    else:
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="У вас недостаточно монеток для покупки 🌼!")
        bot.send_sticker(chat_id, "CAACAgIAAxkBAAEOgP1oJ23Broxg3oXNldf85M2-vCdM7AAClQEAAladvQp2JZLWwRjgLDYE")

def shop1(chat_id):
    bot.send_message(chat_id=chat_id, text="Вы купили радугу! 🌈")
    bot.send_animation(chat_id, animation='https://steamuserimages-a.akamaihd.net/ugc/97233690491092121/44BEC54EB389960A035A45AAF300865964F723D5/?imw=512&amp;imh=305&amp;ima=fit&amp;impolicy=Letterbox&amp;imcolor=%23000000&amp;letterbox=true', caption='Я РАДУГА')
def shop3(chat_id):
    bot.send_message(chat_id=chat_id, text="Вы купили дождик! 🌧️")
    bot.send_animation(chat_id, animation='https://content.foto.my.mail.ru/community/blog_vitalderov/_groupsphoto/h-18078.jpg', caption="Дождик !")
def shop2(chat_id):
    bot.send_message(chat_id=chat_id, text="Вы купили солнечный свет! ☀️")
    bot.send_animation(chat_id, animation='https://media1.tenor.com/m/pknwZ7GL8qAAAAAd/yetee-the-yetee.gif', caption='Эй хочешь конфетку...')
def shop4(chat_id):
    bot.send_photo(
        chat_id=chat_id,
        photo='https://i.pinimg.com/736x/19/57/0e/19570ee43d8b7ee0fa5d6f4213b76dfc.jpg',
        caption=f"Ваше растение получило солнце☀️"
    )
 
USER_STATES = {}

@bot.message_handler(commands=['flowers'])
def scins(message):
    chat_id = message.chat.id
    scins = plant_all_s(chat_id)
    USER_STATES[chat_id] = "choosing_scin"  
    bot.send_message(chat_id, f"У вас {scins} скинов на цветочек 🎀😀 \nА теперь напишите номер скина вот так (цветок 1)🤩")
    bot.send_sticker(chat_id, "CAACAgIAAxkBAAEOhPhoKrWcqHEvkRW0fPXwGW7xF350MwACrgEAAladvQqAXIyr2L0TUjYE")

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == "choosing_scin")
def choose_scin(message):
    chat_id = message.chat.id
    del USER_STATES[chat_id]  
    text = message.text.strip().lower()
    scin_all = plant_all_s(chat_id)

    if text.startswith("цветок"): 
        parts = text.split()  
        if len(parts) > 1: 
            try:
                chosen_number = int(parts[1])  
                if chosen_number <= scin_all:
                    scining = chosen_number
                    bot.send_message(chat_id, f"Выбран скин №{scining}, обновление...")
                    cursor.execute("UPDATE plants SET scin=? WHERE user_id=?", (scining, chat_id,))
                    connection.commit()  
                    
                    cursor.execute('''SELECT scin FROM plants WHERE user_id=?''', (chat_id,))
                    result = cursor.fetchone()  
                    
                    photo = plant_p(chat_id)
                    bot.send_photo(chat_id, photo, caption=f"Красота ☀️ ")
                    
                    bot.send_message(chat_id, f"ВЫБРАЛИ {chosen_number}-й скин! 🎀")
                else:
                    bot.send_message(chat_id, f"Неверная команда. У вас недостаточно скинов для выбора указанного номера.")
            except ValueError:
                bot.send_message(chat_id, "Номер скина должен быть числом. Попробуйте снова.")
        else:
            bot.send_message(chat_id, "Вы забыли указать номер скина после слова \"цветок\". Попробуйте снова.")
    else:
        bot.send_message(chat_id, f"Неверная команда. Вам доступно {scin_all} скинов на цветочек 🎀. Выбери один из них, например, вот так (цветок 1) или (цветок 2)")

@bot.message_handler(commands=['dog'])
def dog (message):
    chat_id = message.chat.id
    data = data_select(chat_id)
    bot.send_message(chat_id=chat_id, text="Ты позвал свою собаку 🐕\n Твоя собака может найти монетки  💪.Это зависит от удачи ,🍀шанс что твоя собака найдёт монетки равна 30%🤣.\n Подождите 30 секунд")
    bot.send_sticker(chat_id, "CAACAgIAAxkBAAEOggxoKBlCBwskPv-HJuXxx9ysWTUtIAACXgADrWW8FLy_0yJMyvjLNgQ")
    lock.acquire() 

    try:
        dog_points = random.randint(0, 10)
        current_point = data["points"]
        time.sleep(30)
        if dog_points > 6:
            update_points2 = current_point + 15
            bot.send_message(chat_id=chat_id, text="Ваша собака ... \n\nНАШЛА МОНЕТКИ🔎  вам прибавилось 15+ м.")
            bot.send_animation(chat_id, animation='https://telepot.ru/images/stickers_img/dae260ddf9.gif', caption="УРА !")
        else:
            update_points2 = current_point 
            bot.send_message(chat_id=chat_id, text="Ваша собака ... \n\nНЕ НАШЛА МОНЕТКИ🔎  вам прибавилось 0+ м.🌧️")
            bot.send_animation(chat_id, animation='https://media.tenor.com/9sPQlkbGzDQAAAAC/sad-emote.gif', caption="Нет !")
        data_update(data["water"], data["level"], update_points2, data["mood"], data["id"])
    finally:
        lock.release()
    
if __name__ == '__main__':
    bot.infinity_polling()
