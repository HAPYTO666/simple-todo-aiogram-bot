import datetime
import asyncpg

def handle_task(task: asyncpg.Record) -> str:
    """Работа с asyncpg записью и её вывод в виде отформатированной строки."""
    opts = [f'<b>{task.get("name")}</b>'
            f'<i>{task.get("description")}</i>',
            f'Status: {("\u274C", "\u2705")[task.get("is_completed")]}',
            f'Priority: {("\u274C", "\u2705")[task.get("priority")]}',
            f'Date of creation: {task.get("created_at").strftime("%d.%m.%Y %H:%M")}']

    if task.get('reminder') and task['reminder'] >= datetime.datetime.now():
        opts += [f"Reminder: {task['reminder'].strftime('%d-%m %H:%M')}{("\u274C", "\u2705")[task.get("reminder_sent")]}"]

    return '\n'.join(opts)

def handle_date(date: datetime.datetime):
    """Работает с датой, заменяя год на текущий."""
    return date.replace(year=datetime.datetime.now().year).date()
