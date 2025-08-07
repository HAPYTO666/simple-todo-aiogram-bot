import datetime
import asyncpg

from aiogram.types import BotCommand, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData


class TaskCB(CallbackData, prefix='task'):
    tid: str
    text: str


menu = [
    BotCommand(command='start', description='restart the bot'),
    BotCommand(command='add', description='add a task'),
    BotCommand(command='list', description='view list of tasks'),
    BotCommand(command='listuncompleted', description='view list of uncompleted tasks'),
    BotCommand(command='reminders', description='view reminders'),
]

cancel_fsm_button = InlineKeyboardButton(text='Cancel❌', callback_data='cancel_add')


def handle_task(task: asyncpg.Record):
    opts = [f'<b>{task.get("name")}</b>',
            f'<i>{task.get("description")}</i>',
            f'Status: {("\u274C", "\u2705")[task.get("is_completed")]}',
            f'Priority: {("\u274C", "\u2705")[task.get("priority")]}',
            f'Date of creation: {task.get("created_at").strftime("%d.%m.%Y %H:%M")}']

    if task.get('reminder') and task['reminder'] >= datetime.datetime.now():
        opts += [f"Reminder: {task['reminder'].strftime('%d-%m %H:%M')}{("\u274C", "\u2705")[task.get("reminder_sent")]}"]

    return '\n'.join(opts)

def handle_date(date: datetime.datetime):
    return date.replace(year=datetime.datetime.now().year).date()

def validate_date(date: datetime.datetime):
    return date > datetime.datetime.now().replace(second=0)
