import asyncio
import logging
from bot import main as bot_main
from client import main as client_main

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def main():
    try:
        # Створюємо завдання для бота та клієнта
        bot_task = asyncio.create_task(bot_main())
        client_task = asyncio.create_task(client_main())
        
        print("🚀 Запуск системи...")
        print("🤖 Бот запущений")
        print("👤 Клієнт запущений")
        print("Для зупинки натисніть Ctrl+C")
        
        # Чекаємо завершення обох завдань
        await asyncio.gather(bot_task, client_task)
        
    except KeyboardInterrupt:
        print("\n⚠️ Зупинка системи...")
    except Exception as e:
        print(f"❌ Помилка: {e}")
    finally:
        print("👋 Система зупинена")

if __name__ == "__main__":
    asyncio.run(main()) 