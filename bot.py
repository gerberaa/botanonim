import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import time
import os
from dotenv import load_dotenv

# Завантаження змінних середовища
load_dotenv()

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота та диспетчера
bot = Bot(token=os.getenv('BOT_TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Стани для FSM
class ApplicationStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_message = State()
    waiting_for_reply_choice = State()
    waiting_for_reply_count = State()

# Клавіатура для скасування
cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отменить")]],
    resize_keyboard=True
)

# Клавіатура для вибору кількості відповідей
def get_reply_count_keyboard():
    keyboard = []
    for i in range(1, 16):
        keyboard.append([InlineKeyboardButton(text=str(i), callback_data=f"reply_count_{i}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Обробник команди /start
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "Привет! Я бот для анонимных сообщений 🤖\n\n"
        "Для отправки анонимного сообщения нажмите кнопку ниже:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✉️ Отправить сообщение")]],
            resize_keyboard=True
        )
    )

# Обробник кнопки "Відправити повідомлення"
@dp.message(lambda message: message.text == "✉️ Отправить сообщение")
async def start_application(message: Message, state: FSMContext):
    await message.answer(
        "Введите username получателя (без символа @):",
        reply_markup=cancel_keyboard
    )
    await state.set_state(ApplicationStates.waiting_for_username)

# Обробник username
@dp.message(ApplicationStates.waiting_for_username)
async def process_username(message: Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer(
            "Операция отменена. Нажмите кнопку ниже, чтобы начать заново:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="✉️ Отправить сообщение")]],
                resize_keyboard=True
            )
        )
        return

    await state.update_data(username=message.text)
    await message.answer("Теперь введите текст сообщения:")
    await state.set_state(ApplicationStates.waiting_for_message)

# Обробник повідомлення
@dp.message(ApplicationStates.waiting_for_message)
async def process_message(message: Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer(
            "Операция отменена. Нажмите кнопку ниже, чтобы начать заново:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="✉️ Отправить сообщение")]],
                resize_keyboard=True
            )
        )
        return

    data = await state.get_data()
    username = data['username']
    
    # Зберігаємо повідомлення в стані
    await state.update_data(message=message.text)
    
    # Запитуємо про бажання отримувати відповіді
    await message.answer(
        "Хотите ли вы получать ответы на ваше сообщение?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да", callback_data="want_reply_yes")],
                [InlineKeyboardButton(text="❌ Нет", callback_data="want_reply_no")]
            ]
        )
    )
    await state.set_state(ApplicationStates.waiting_for_reply_choice)

# Обробник вибору отримання відповідей
@dp.callback_query(ApplicationStates.waiting_for_reply_choice)
async def process_reply_choice(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "want_reply_no":
        data = await state.get_data()
        username = data['username']
        message = data['message']
        
        # Зберігаємо заявку у файл без кількості відповідей
        with open('applications.txt', 'a', encoding='utf-8') as f:
            f.write(f"{callback.from_user.id}|{username}|{message}|0\n")
        
        await callback.message.edit_text(
            "⏳ Ваше сообщение принято! Вы получите уведомление о статусе отправки в ближайшее время.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="✉️Отправить сообщение")]],
                resize_keyboard=True
            )
        )
        await state.clear()
        return

    await callback.message.edit_text(
        "Выберите количество ответов, которые вы хотите получить (от 1 до 15):",
        reply_markup=get_reply_count_keyboard()
    )
    await state.set_state(ApplicationStates.waiting_for_reply_count)

# Обробник вибору кількості відповідей
@dp.callback_query(ApplicationStates.waiting_for_reply_count)
async def process_reply_count(callback: types.CallbackQuery, state: FSMContext):
    reply_count = int(callback.data.split('_')[2])
    data = await state.get_data()
    username = data['username']
    message = data['message']
    
    # Зберігаємо заявку у файл з кількістю відповідей
    with open('applications.txt', 'a', encoding='utf-8') as f:
        f.write(f"{callback.from_user.id}|{username}|{message}|{reply_count}\n")
    
    await callback.message.edit_text(
        "⏳ Ваше сообщение принято! Вы получите уведомление о статусе отправки в ближайшее время.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✉️ Отправить сообщение")]],
            resize_keyboard=True
        )
    )
    await state.clear()

