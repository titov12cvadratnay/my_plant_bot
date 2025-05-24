from telebot import TeleBot, types
import sqlite3
import random
import threading
import time
import schedule

# Импортируем необходимые модули для работы с Telegram API, SQLite базой данных, потоками и расписаниями.

# Токен бота, который берётся из официального интерфейса Telegram @BotFather
bot = TeleBot('ВАШ_ТОКЕН_БОТА')

# Устанавливаем соединение с локальной базой данных SQLite
connection = sqlite3.connect('plant.db', check_same_thread=False)
cursor = connection.cursor()

# Создание таблицы для хранения данных игроков (растений)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS plants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,      -- Уникальный идентификатор записи
        user_id INTEGER NOT NULL,                 -- Идентификатор пользователя Telegram
        water INTEGER DEFAULT 50,                 -- Показатель уровня воды (от 0 до 100%)
        level INTEGER DEFAULT 1,                  -- Текущий уровень развития растения
        points INTEGER DEFAULT 50,                -- Количество игровых монет
        mood INTEGER DEFAULT 50,                  -- Настроение растения (чем выше, тем быстрее рост)
        scin INTEGER DEFAULT 1,                   -- Номер выбранного скина для отображения внешнего вида растения
        scin_all INTEGER DEFAULT 1                -- Общее количество доступных скинов для растения
    )
''')

# Генерация меню для быстрого доступа к основным действиям
def generate_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_dog = types.KeyboardButton('/dog')     # Команда поиска монет собакой
    btn_water = types.KeyboardButton('/water')  # Команда полива растения
    btn_shop = types.KeyboardButton('/shop')    # Магазин предметов
    btn_status = types.KeyboardButton('/status') # Статус растения
    btn_help = types.KeyboardButton('/help')    # Справочная информация
    btn_f = types.KeyboardButton('/flowers')    # Управление внешностью растения
    btn_mail = types.KeyboardButton('/mail')    # Отправка монет другому пользователю
    markup.row(btn_help, btn_status, btn_mail)
    markup.row(btn_shop, btn_dog, btn_water)
    markup.row(btn_f)
    return markup

# Генерация меню магазина
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

# Проверяет существование пользователя в базе данных
def you_user(user_id):
    cursor.execute('''SELECT COUNT(*) FROM plants WHERE user_id=?''', (user_id,))
    count = cursor.fetchone()[0]
    return bool(count)

# Регистрация нового пользователя
def welcome_user(user_id):
    cursor.execute(
        '''INSERT INTO plants (user_id, water, level, points, mood, scin, scin_all) VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (user_id, 50, 1, 50, 50, 1, 1)  
    )

# Получение текущих данных пользователя
def data_select(user_id):
    cursor.execute('''SELECT id, user_id, water, level, points, mood FROM plants WHERE user_id=?''', (user_id,))
    result = cursor.fetchone()      
    if result is None:
        return "Игрок не найден." 
    columns = ['id', 'user_id', 'water', 'level', 'points', 'mood']
    data = dict(zip(columns, result))
    return data

# Параллельная обработка запросов с защитой блокировки базы данных
db_lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=5)

# Обновление данных игрока в базе данных
def data_update(water, level, points, mood, plant_id):
    with db_lock:
        cursor.execute("UPDATE plants SET water=?, level=?, points=?, mood=? WHERE id=?", (water, level, points, mood, plant_id,))
        connection.commit()

# Отправка уведомлений пользователю
def send_notification(chat_id, notification):
    executor.submit(bot.send_message, chat_id, notification)

# Автоматическое получение урожая раз в сутки
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

# Планировщик автоматического запуска ежедневного сбора урожая
schedule.every().day.at("09:59").do(harvest_fruits)

# Потоковая работа планировщика
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.daemon = True
scheduler_thread.start()

# Периодическая проверка состояния растения
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
        connection.commit()
        bot.send_message(chat_id, text="Ваше растение уходит от вас в далёкую страну растений😀")
        timer.cancel()

    timer = threading.Timer(60*20, update_plant_data, args=(chat_id,))
    timer.start()

# Запуск периодической проверки состояния растения
def start_update_timer(chat_id):
    update_plant_data(chat_id)

# Возвращает общее количество доступных скинов
def plant_all_s(plant_id):
    cursor.execute('''SELECT scin_all FROM plants WHERE user_id=?''', (plant_id,))
    result = cursor.fetchone()  
    connection.commit()
    if result:
        return result[0]
    return 0 

# Определение внешнего вида растения по номеру скина
def plant_p(plant_id):
    cursor.execute('''SELECT scin FROM plants WHERE user_id=?''', (plant_id,))
    numb = cursor.fetchone()  
    connection.commit()
    if numb and numb[0] == 1:
        return "URL_СКИНА_1"
    elif numb and numb[0] == 2:
        return "URL_СКИНА_2"
    elif numb and numb[0] == 3:
        return "URL_СКИНА_3"
    elif numb and numb[0] == 4:
        return "URL_СКИНА_4"
    else:
        return "DEFAULT_URL_СКИН"

# Название скина по его номеру
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

# Первая точка входа в бот (/start)
@bot.message_handler(commands=['start'])
def welcome(message):
    markup = generate_menu()
    chat_id = message.chat.id
    markup = generate_menu() 
    
    if not you_user(chat_id):
        welcome_user(chat_id)
        response_text = f"Добро пожаловать в Plants lite 🤩! Вы успешно зарегистрированы! Эта ссылка на наш канал https://t.me/+l9RHgfjX-Y1kZTVi /help - это помощь"
    else:
        response_text = f"С возвращением🤩!"

    start_update_timer(chat_id)
    bot.send_photo(chat_id=chat_id, photo='DEFAULT_PHOTO_URL',caption=response_text, reply_markup=markup)
    bot.send_sticker(chat_id, "STICKER_ID")

# Справочный раздел (/help)
@bot.message_handler(commands=['help'])
def help(message):
    markup = generate_menu()
    chat_id = message.chat.id
    text_help = (   
        'Справочная информация о правилах игры и доступных командах.'
    )
    bot.send_message(chat_id=chat_id, text=text_help, reply_markup=markup )
    bot.send_sticker(chat_id, "STICKER_ID")

# Отображение текущего статуса растения (/status)
@bot.message_handler(commands=['status'])
def status_command (message):
    chat_id = message.chat.id
    data_dict = data_select(chat_id)
    markup = generate_menu()
    photo = plant_p(chat_id)
    scin = plant_s(chat_id)
    text_status = (
    f"Информация о вашем растении."
    )
    bot.send_message(chat_id=chat_id, text=text_status, reply_markup=markup )
    bot.send_sticker(chat_id, "STICKER_ID")
    level = int(data_dict['level'])  
    markup = generate_menu()
    bot.send_photo(
        chat_id=chat_id,
        photo=photo,
        caption=f"Цветок {scin} Ур.{level}🎇",
        reply_markup=markup
    )

# Реакция на отправку стикеров
@bot.message_handler(content_types=['sticker'])
def handle_sticker(message):
    chat_id = message.chat.id
    random_stiker = [
        'LIST_OF_STICKERS'
    ]
    selected_sticker = random.choice(random_stiker)
    bot.send_sticker(chat_id, selected_sticker)

# Посылка подарка монетами другому пользователю
USER_STATES_1 = {}

@bot.message_handler(commands=['mail'])
def mail(message):
    chat_id = message.chat.id
    data = data_select(chat_id)  
    USER_STATES_1[chat_id] = "mail"  
    bot.send_message(chat_id, f"У вас {data['points']} монеток 😀 \nХотите отправить монетки по ID( ID не растения ).\nВот как это сделать например :(1)🤩")
    bot.send_sticker(chat_id, "STICKER_ID")

@bot.message_handler(func=lambda message: USER_STATES_1.get(message.chat.id) == "mail")
def mail_points(message):
    chat_id = message.chat.id
    del USER_STATES_1[chat_id]  
    data = data_select(chat_id) 
    text = message.text.strip().lower()
    points_str = str(data['points']) 
    points = int(points_str)
    if points >= 50 : 
        try:
            update_points = data['points'] - 50  
            data_update(data["water"], data["level"], update_points, data['mood'], data["id"])  
            cursor.execute("UPDATE plants SET points=points+50 WHERE id=?", (text,))  
            cursor.execute('''SELECT user_id FROM plants WHERE id=?''', (text,))
            id = cursor.fetchone()
            connection.commit()
            bot.send_sticker(chat_id, "STICKER_ID")
            bot.send_message(chat_id, f"🤩🤩Вы отправили монетки !😀🤩")
            bot.send_message(id, f"🤩🤩У вас {update_points} монеток . Кто-то подарил вам 50 монеток !😀🤩")
        except Exception as e:
            print(e)  

# Команда полива растения (/water)
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

# Открытие магазина (/shop)
@bot.message_handler(commands=['shop'])
def shop (message):
    chat_id = message.chat.id
    data = data_select(chat_id)
    current_point = data["points"]
    bot.send_message(chat_id=chat_id, text=f"У вас {current_point}💰 монет 😀 \nУ каждого предмета своё свойство 🤩\nВот весь ассортимент👁‍🗨", reply_markup=shop_menu())

# Обработка нажатия кнопок в магазине
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
                    bot.send_sticker(chat_id, "STICKER_ID")

            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Подождите покупка совершается 🌼!")
            update_point = current_point - 25
            data_update(data["water"], data["level"], update_point, update_mood, data["id"])
            
        finally:
            lock.release()  
    else:
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="У вас недостаточно монеток для покупки 🌼!")
        bot.send_sticker(chat_id, "STICKER_ID")

# Функции показа анимаций при покупке товаров
def shop1(chat_id):
    bot.send_message(chat_id=chat_id, text="Вы купили радугу! 🌈")
    bot.send_animation(chat_id, animation='ANIMATION_URL', caption='Я РАДУГА')
def shop3(chat_id):
    bot.send_message(chat_id=chat_id, text="Вы купили дождик! 🌧️")
    bot.send_animation(chat_id, animation='ANIMATION_URL', caption="Дождик !")
def shop2(chat_id):
    bot.send_message(chat_id=chat_id, text="Вы купили солнечный свет! ☀️")
    bot.send_animation(chat_id, animation='ANIMATION_URL', caption='Эй хочешь конфетку...')
def shop4(chat_id):
    bot.send_photo(
        chat_id=chat_id,
        photo='PHOTO_URL',
        caption=f"Ваше растение получило солнце☀️"
    )

# Система смены внешности растения (/flowers)
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

@bot.message_handler(commands=['dog']) #случайный заработок монет
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
    
if __name__ == '__main__':#запукс цикла
    bot.infinity_polling()    
