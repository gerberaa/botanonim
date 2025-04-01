import asyncio
import logging
from bot import dp, bot
from client import client
import os

# Налаштування логування
LOG_DIR = '/home/pilk/anonim_bot/logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'bot.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    try:
        logger.info("Starting bot...")
        # Перевіряємо підключення до бота
        bot_info = await bot.get_me()
        logger.info(f"Bot connected successfully: @{bot_info.username}")
        
        # Перевіряємо підключення до клієнта
        logger.info("Starting client...")
        await client.start()
        logger.info("Client started successfully")
        
        # Запускаємо бота
        logger.info("Starting polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        logger.info("Script started")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True) 