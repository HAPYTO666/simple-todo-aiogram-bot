from aiogram.filters.callback_data import CallbackData

class TaskCB(CallbackData, prefix='task'):
    tid: str
    text: str
