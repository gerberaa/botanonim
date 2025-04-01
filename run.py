import asyncio
import logging
from bot import dp, bot
from client import main as client_main

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    try:
        # Запускаємо обидва компоненти паралельно
        await asyncio.gather(
            dp.start_polling(bot),
            client_main()
        )
    except Exception as e:
        logger.error(f"Помилка при запуску: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 