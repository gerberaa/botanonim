from telethon import TelegramClient, events
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from telethon.errors import (
    UsernameNotOccupiedError,
    UsernameInvalidError,
    FloodWaitError,
    UserDeactivatedError,
    ChatWriteForbiddenError
)
import asyncio
import os
from dotenv import load_dotenv
import time
import logging
from aiogram import Bot
from datetime import datetime, timedelta
import json

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Завантаження змінних середовища
load_dotenv()

# Дані для автентифікації
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE = os.getenv('PHONE')
BOT_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Ініціалізація клієнтів
client = TelegramClient('anon', API_ID, API_HASH)
bot = Bot(token=BOT_TOKEN)

# Час очікування між повідомленнями (2 години)
COOLDOWN_HOURS = 2

# Словник для зберігання активних чатів та їх налаштувань
active_chats = {}

def load_excluded_users():
    """Завантажує список користувачів без обмежень"""
    excluded_users = set()
    if os.path.exists('excluded_users.txt'):
        with open('excluded_users.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    excluded_users.add(line.strip())
    return excluded_users

def load_last_message_times():
    """Завантажує час останнього повідомлення для кожного користувача"""
    last_times = {}
    if os.path.exists('last_messages.txt'):
        with open('last_messages.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    user_id, timestamp = line.strip().split('|')
                    last_times[user_id] = datetime.fromisoformat(timestamp)
    return last_times

def save_last_message_time(user_id: str):
    """Зберігає час останнього повідомлення користувача"""
    current_time = datetime.now()
    last_times = load_last_message_times()
    last_times[user_id] = current_time
    
    with open('last_messages.txt', 'w', encoding='utf-8') as f:
        for uid, time in last_times.items():
            f.write(f"{uid}|{time.isoformat()}\n")

def can_send_message(user_id: str) -> tuple[bool, str]:
    """Перевіряє, чи може користувач надіслати повідомлення"""
    excluded_users = load_excluded_users()
    
    # Якщо користувач в списку виключень
    if user_id in excluded_users:
        return True, ""
    
    last_times = load_last_message_times()
    current_time = datetime.now()
    
    # Якщо користувач ще не надсилав повідомлень
    if user_id not in last_times:
        return True, ""
    
    # Перевіряємо час останнього повідомлення
    last_message_time = last_times[user_id]
    time_diff = current_time - last_message_time
    
    if time_diff < timedelta(hours=COOLDOWN_HOURS):
        remaining_time = timedelta(hours=COOLDOWN_HOURS) - time_diff
        hours = int(remaining_time.total_seconds() // 3600)
        minutes = int((remaining_time.total_seconds() % 3600) // 60)
        return False, f"⏳ Вы можете отправить следующее сообщение через {hours} часов {minutes} минут"
    
    return True, ""

async def notify_user(user_id: str, message: str):
    """Відправляє повідомлення користувачу через бота"""
    try:
        logging.info(f"Спроба відправки повідомлення користувачу {user_id}")
        await bot.send_message(chat_id=int(user_id), text=message)
        logging.info(f"Повідомлення успішно відправлено користувачу {user_id}")
        return True
    except Exception as e:
        logging.error(f"Помилка при відправці повідомлення користувачу {user_id}: {e}")
        return False

async def forward_message(target_username: str, message: str):
    try:
        # Видаляємо @ якщо він є
        target_username = target_username.lstrip('@')
        logging.info(f"Спроба відправки повідомлення до {target_username}")
        
        # Отримання інформації про цільового користувача
        target_user = await client.get_entity(target_username)
        logging.info(f"Цільовий користувач: {target_user.first_name}")
        
        # Формуємо повне повідомлення з привітанням та посиланням на бота
        full_message = f"💌 Привет! Тебе передали анонимное сообщение:\n\n{message}\n\nЕсли ты хочешь тоже отправить кому-то сообщение вот наш бот @anonim_messagessbot"
        
        # Відправка повідомлення
        sent_message = await client.send_message(target_user, full_message)
        logging.info(f"Повідомлення успішно відправлено до {target_user.first_name}")
        return True, None, sent_message.id
    except UsernameNotOccupiedError:
        error_msg = "Користувач з таким username не знайдений"
        logging.error(error_msg)
        return False, error_msg, None
    except UsernameInvalidError:
        error_msg = "Невірний формат username"
        logging.error(error_msg)
        return False, error_msg, None
    except FloodWaitError as e:
        error_msg = f"Забагато спроб. Спробуйте через {e.seconds} секунд"
        logging.error(error_msg)
        return False, error_msg, None
    except UserDeactivatedError:
        error_msg = "Користувач деактивований"
        logging.error(error_msg)
        return False, error_msg, None
    except ChatWriteForbiddenError:
        error_msg = "Неможливо написати користувачу (він не приймає повідомлення)"
        logging.error(error_msg)
        return False, error_msg, None
    except Exception as e:
        error_msg = f"Помилка при відправці: {str(e)}"
        logging.error(error_msg)
        return False, error_msg, None

def normalize_username(username: str) -> str:
    """Нормалізує username для порівняння"""
    return username.lower().strip()

async def process_single_application(application: str, processed_ids: set, failed_ids: set):
    """Обробляє одну заявку"""
    try:
        if not application.strip():  # Пропускаємо порожні рядки
            return False

        parts = application.strip().split('|')
        user_id = parts[0]
        username = parts[1]
        message = parts[2]
        reply_count = int(parts[3]) if len(parts) > 3 else 0
        
        logging.info(f"Обробка заявки від користувача {user_id} до {username}")
        
        # Перевіряємо, чи може користувач надіслати повідомлення
        can_send, cooldown_message = can_send_message(user_id)
        if not can_send:
            await notify_user(user_id, cooldown_message)
            return True
        
        # Відправляємо повідомлення
        success, error_msg, message_id = await forward_message(username, message)
        
        if success:
            # Зберігаємо час останнього повідомлення
            save_last_message_time(user_id)
            
            # Додаємо ID до оброблених
            processed_ids.add(user_id)
            with open('processed_ids.txt', 'a', encoding='utf-8') as f:
                f.write(f"{user_id}\n")
            
            # Якщо користувач хоче отримувати відповіді
            if reply_count > 0:
                # Зберігаємо інформацію про чат
                chat_info = {
                    'user_id': user_id,
                    'username': username,
                    'message_id': message_id,
                    'reply_count': reply_count,
                    'replies_received': 0
                }
                active_chats[normalize_username(username)] = chat_info
                logging.info(f"Збережено інформацію про чат: {chat_info}")
                
                # Повідомляємо користувача про успішну відправку та можливість отримання відповідей
                await notify_user(user_id, f"✅ Ваше сообщение успешно отправлено!\n\nВы можете получить к {reply_count} ответов от получателя.")
            else:
                # Повідомляємо користувача про успішну відправку
                await notify_user(user_id, "✅ Ваше сообщение успешно отправлено!")
            return True
        else:
            # Додаємо ID до невдалих
            failed_ids.add(user_id)
            with open('failed_ids.txt', 'a', encoding='utf-8') as f:
                f.write(f"{user_id}|{error_msg}\n")
            
            # Повідомляємо користувача про помилку
            await notify_user(user_id, f"❌ Не удалось отправить сообщение:\n{error_msg}")
            return True
            
    except Exception as e:
        logging.error(f"Помилка при обробці заявки: {e}")
        return False

@client.on(events.NewMessage)
async def handle_new_message(event):
    """Обробляє нові повідомлення від користувачів"""
    try:
        # Отримуємо інформацію про повідомлення
        sender = await event.get_sender()
        username = sender.username or sender.first_name
        normalized_username = normalize_username(username)
        logging.info(f"Отримано нове повідомлення від {username} (нормалізований: {normalized_username})")
        
        # Перевіряємо, чи є активний чат для цього користувача
        if normalized_username in active_chats:
            chat_info = active_chats[normalized_username]
            logging.info(f"Знайдено активний чат: {chat_info}")
            
            # Перевіряємо, чи не перевищено ліміт відповідей
            if chat_info['replies_received'] < chat_info['reply_count']:
                # Відправляємо повідомлення користувачу
                await notify_user(
                    chat_info['user_id'],
                    f"📩 Новое сообщение от {username}:\n\n{event.message.text}"
                )
                logging.info(f"Сообщение переслано пользователю {chat_info['user_id']}")
                
                # Оновлюємо лічильник відповідей
                chat_info['replies_received'] += 1
                logging.info(f"Обновлен счетчик ответов: {chat_info['replies_received']}/{chat_info['reply_count']}")
                
                # Якщо досягнуто ліміт відповідей, видаляємо чат
                if chat_info['replies_received'] >= chat_info['reply_count']:
                    del active_chats[normalized_username]
                    await notify_user(
                        chat_info['user_id'],
                        f"ℹ️ Вы получили все доступные сообщения от {username}."
                    )
                    logging.info(f"Достигнут предел сообщений, чат удален")
            else:
                # Повідомляємо отримувача про досягнення ліміту
                await event.reply("Извините, но лимит сообщений достигнут.")
                logging.info("Отправлено сообщение о достижении лимита")
    except Exception as e:
        logging.error(f"Ошибка при обработке нового сообщения: {e}")

async def process_applications():
    processed_ids = set()
    failed_ids = set()
    
    # Створюємо файли, якщо вони не існують
    if os.path.exists('processed_ids.txt'):
        with open('processed_ids.txt', 'r', encoding='utf-8') as f:
            processed_ids = set(line.strip() for line in f)
    if os.path.exists('failed_ids.txt'):
        with open('failed_ids.txt', 'r', encoding='utf-8') as f:
            failed_ids = set(line.strip() for line in f)
    
    while True:
        try:
            if os.path.exists('applications.txt'):
                with open('applications.txt', 'r', encoding='utf-8') as f:
                    applications = f.readlines()
                
                if applications:  # Якщо є нові заявки
                    logging.info(f"Знайдено {len(applications)} нових заявок")
                    # Обробляємо всі заявки
                    remaining_applications = []
                    for application in applications:
                        if await process_single_application(application, processed_ids, failed_ids):
                            logging.info("Заявка успішно оброблена")
                        else:
                            remaining_applications.append(application)
                    
                    # Оновлюємо файл з залишившимися заявками
                    with open('applications.txt', 'w', encoding='utf-8') as f:
                        f.writelines(remaining_applications)
                    logging.info(f"Залишилось {len(remaining_applications)} необроблених заявок")
            
            # Чекаємо 0.5 секунди перед наступною перевіркою
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logging.error(f"Помилка при обробці заявок: {e}")
            await asyncio.sleep(1)

async def main():
    try:
        # Підключення до Telegram
        await client.start(phone=PHONE)
        logging.info("Клієнт успішно підключений!")
        logging.info("Очікування нових заявок...")
        
        # Запускаємо обробку заявок
        await process_applications()
    except Exception as e:
        logging.error(f"Помилка в клієнті: {e}")
        raise
    finally:
        await client.disconnect()
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main()) 