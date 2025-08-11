from aiogram.types import BotCommand

menu = [
    BotCommand(command='start', description='restart the bot'),
    BotCommand(command='add', description='add a task'),
    BotCommand(command='list', description='view list of tasks'),
    BotCommand(command='listuncompleted', description='view list of uncompleted tasks'),
    BotCommand(command='reminders', description='view reminders'),
]
