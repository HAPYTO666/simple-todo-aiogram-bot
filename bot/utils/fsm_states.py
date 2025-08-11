from aiogram.fsm.state import State, StatesGroup

class AddTask(StatesGroup):
    """Группа состояний для создания нового задания"""
    received_name = State()
    received_desc = State()
    received_priority = State()
    received_reminder_dt = State()
    received_reminder_time = State()
    received_exc = State()
