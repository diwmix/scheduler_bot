from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
import telebot
import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()
ADMIN_CHAT_IDS = [794436254] 
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
  username TEXT,
  chat_id INTEGER PRIMARY KEY,
  favorite_class TEXT
)''')
conn.commit()
conn.close()

class_ranges = {
    '1 Клас': 'B2:G9',
    '2 Клас': 'B12:G19',
    '3 Клас': 'B22:G29',
    '4 Клас': 'B32:G39',
    '5 Клас': 'J2:O9',
    '6 Клас': 'J12:O19',
    '7 Клас': 'J22:O29',
    '8 Клас': 'J32:O39',
    '9 Клас': 'R2:W9',
    '10 Клас': 'R12:W19',
    '11 Клас': 'R22:W29'
}
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'maidan-scheduler-bot-3f39fed62e37.json'

creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
service = build('sheets', 'v4', credentials=creds)

SPREADSHEET_ID = '1Nx87H2CGjzh77KiRslTcufHo-utWtC0ZRwOhhef9puU'

API_TOKEN = '7361937379:AAFYkv5X9nk1P8lihj3rEg3bk-w9x729lJI'
bot = telebot.TeleBot(API_TOKEN)

start_buttons = [
    'Пошук розкладу', 'Мій розклад'
]
start = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
start.add(*[telebot.types.KeyboardButton(text) for text in start_buttons])

class_buttons = [
    '1 Клас', '2 Клас', '3 Клас', '4 Клас', '5 Клас',
    '6 Клас', '7 Клас', '8 Клас', '9 Клас', '10 Клас', '11 Клас'
]
back_button = telebot.types.KeyboardButton('Назад')
classes = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)
classes.add(*[telebot.types.KeyboardButton(text) for text in class_buttons])
classes.add(back_button)

def get_add_to_favorite_markup(selected_class):
    add_to_favorite = telebot.types.InlineKeyboardMarkup(row_width=1)
    add_to_favorite_button = telebot.types.InlineKeyboardButton("Зробити основним", callback_data=f"record_to_sqlite:{selected_class}")
    add_to_favorite.add(add_to_favorite_button)
    return add_to_favorite

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "Привіт! Оберіть опцію:", reply_markup=start)

@bot.message_handler(func=lambda message: message.text == 'Пошук розкладу')
def handle_search_schedule(message):
    bot.send_message(message.chat.id, "Оберіть клас для перегляду:", reply_markup=classes)

@bot.message_handler(func=lambda message: message.text == 'Назад')
def handle_back_schedule(message):
    bot.send_message(message.chat.id, "Оберіть опцію:", reply_markup=start)

def show_scheduler(message, range_name, selected_class):
    bot.send_message(message.chat.id, 'Розклад загружається, зачекайте...')
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
    values = result.get('values', [])
    if selected_class in class_buttons:
        numberOfClass = selected_class
        if not values:
            bot.send_message(message.chat.id, 'Цього тижня у вас немає уроків')
        else:
            days = ["ПОНЕДІЛОК", "ВІВТОРОК", "СЕРЕДА", "ЧЕТВЕР", "П'ЯТНИЦЯ", "СУБОТА"]
            messages = f'<b>{numberOfClass}</b>\n_______________________________________________\n\n'
            time_slots = [
                "08:30 - 09:15", 
                "09:25 - 10:10", 
                "10:30 - 11:15",  
                "11:35 - 12:20", 
                "12:30 - 13:15",  
                "13:25 - 14:10",  
                "14:20 - 15:05",
                "15:15 - 16:00"
            ]
            for i, day in enumerate(days):  
                if not any(row[i].strip() for row in values if len(row) > i):
                    continue 
                messages += f"📆 {day} \n\n"
                lessons_for_day = [row[i] if len(row) > i else "" for row in values]
                for time_slot, lesson in zip(time_slots, lessons_for_day):
                    if lesson.strip():
                        messages += f"<code>🕑 {time_slot}</code> \n<b>{lesson}</b>\n\n"
                    else:
                        messages += f"<code>🕑 {time_slot}</code> \n - \n\n"
                messages += "_______________________________________________\n\n"
            
            total_lessons = sum(len([row[i] for row in values if len(row) > i and row[i].strip()]) for i in range(len(days)))
            messages += f"Загальна кількість уроків: {total_lessons}"

            bot.send_message(message.chat.id, messages, parse_mode='HTML', reply_markup=get_add_to_favorite_markup(selected_class))

@bot.message_handler(func=lambda message: message.text in class_buttons)
def handle_class_selection(message):
    if message.text in class_ranges:
        show_scheduler(message, class_ranges[message.text], message.text)

@bot.callback_query_handler(func=lambda call: call.data.startswith("record_to_sqlite"))
def handle_record_to_sqlite(call):
    selected_class = call.data.split(":")[1]
    chat_id = call.message.chat.id
    username = call.message.chat.username

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT favorite_class FROM users WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()

    if result and result[0] == selected_class:
        bot.answer_callback_query(call.id, "Цей розклад вже є основним!")
        bot.send_message(call.message.chat.id, "Цей розклад вже є основним!", reply_markup=start)
    else:
        cursor.execute('REPLACE INTO users (username, chat_id, favorite_class) VALUES (?, ?, ?)', (username, chat_id, selected_class))
        conn.commit()
        bot.answer_callback_query(call.id, "Розклад був добавлений до основного!")
        bot.send_message(call.message.chat.id, "Розклад був добавлений до основного!", reply_markup=start)
    
    conn.close()

@bot.message_handler(func=lambda message: message.text == 'Мій розклад')
def handle_my_schedule(message):
    chat_id = message.chat.id

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT favorite_class FROM users WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        favorite_class = result[0]
        if favorite_class in class_ranges:
            show_scheduler(message, class_ranges[favorite_class], favorite_class)
        else:
            bot.send_message(message.chat.id, f"Не вдалося знайти розклад для класу: {favorite_class}")
    else:
        bot.send_message(message.chat.id, "Ви не встановили улюблений клас. Спочатку виберіть клас в 'Пошук розкладу'.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text

    if chat_id in ADMIN_CHAT_IDS:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT chat_id FROM users")
            users = cursor.fetchall()
            for user in users:
                bot.send_message(user[0], text)
        except sqlite3.Error as e:  
            print(f"Помилка при відправленні повідомлень: {e}")
        finally:
            conn.close()

bot.polling(none_stop=True)
