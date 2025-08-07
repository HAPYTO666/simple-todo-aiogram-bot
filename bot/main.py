import asyncio
import logging

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asyncio.exceptions import CancelledError

from db import *
from utils import *

load_dotenv()
bt = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher()
cbrouter = Router()

reminder_check_delay = 30

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class AddT(StatesGroup):
    received_name = State()
    received_desc = State()
    received_priority = State()
    received_reminder_dt = State()
    received_reminder_time = State()
    received_exc = State()


class Reminder:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def start_(self, delay: int):
        logger.info('REMINDER STARTED')
        while True:
            r_tasks = await get_remind_tasks()

            for task in r_tasks:
                if task.get("reminder") == datetime.datetime.now().replace(second=0, microsecond=0):
                    cb_data = f"upd-status:{task.get("id")}"

                    await self.bot.send_message(task.get("user_id"),
                                                text=f"Remind you to do {task.get("name")}.",
                                                reply_markup=InlineKeyboardMarkup(
                                                    inline_keyboard=[[InlineKeyboardButton(text="Task is ready",
                                                                                           callback_data=cb_data)]]
                                                ))
                    logger.info(f"TASK {task.get('id')} WAS REMINDED")
                    await upd_sent_reminder(task.get("id"))
            await asyncio.sleep(delay)


@cbrouter.message(Command("reminders"))
async def view_r(m: Message, edit: bool = False):
    r_tasks = await get_remind_tasks_for_user(m.from_user.id)
    keyboard = InlineKeyboardBuilder()
    if r_tasks:
        text = ("Here is list of your reminders\n"
                "Click to task to delete reminder.")
        for task in r_tasks:
            keyboard.button(text=f"{task.get('name')} - {task.get('reminder').strftime("%d-%m %H:%M")}",
                            callback_data=f"task:{task['id']}:delete_reminder")
    else:
        text = 'You do not have any reminders.'

    if edit:
        await m.edit_text(text, reply_markup=keyboard.as_markup())
    else:
        await m.answer(text, reply_markup=keyboard.as_markup())

@cbrouter.callback_query(F.data.endswith('delete_reminder'))
async def del_reminder(c: CallbackQuery):
    try:
        await del_reminder_for_task(int(c.data.split(':')[-2]))
        await c.answer('Successfully deleted.')
        await view_r(c.message, edit=True)

    except Exception as e:
        logger.error(e)

@cbrouter.message(Command("add"))
async def add_task(m: Message, state: FSMContext):
    if await state.get_state() is not None:
        await state.clear()

    await m.answer('Enter name of the task.',
                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[[cancel_fsm_button]]))

    await state.set_state(AddT.received_name)
    await state.update_data()


@cbrouter.message(AddT.received_name)
async def add_desc(m: Message, state: FSMContext):
    await state.update_data({'name': m.text})
    await state.set_state(AddT.received_desc)

    await m.answer('Enter description of the task.',
                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[[cancel_fsm_button]]))


@cbrouter.message(AddT.received_desc)
async def add_priority(m: Message, state: FSMContext):
    await state.update_data({'desc': m.text})
    await state.set_state(AddT.received_priority)

    await m.answer(text='Enter priority (tasks with priority show first).',
                   reply_markup=InlineKeyboardMarkup(
                       inline_keyboard=[
                           [InlineKeyboardButton(text='Set priority',
                                                 callback_data=TaskCB(tid=await state.get_value("name"),
                                                                      text='priority-1').pack())],
                           [InlineKeyboardButton(text='No priority',
                                                 callback_data=TaskCB(tid=await state.get_value("name"),
                                                                      text='priority-0').pack())],
                           [cancel_fsm_button],
                       ])
                   )


@cbrouter.callback_query(AddT.received_priority, F.data.contains('priority'))
async def add_reminder(c: CallbackQuery | Message, state: FSMContext, is_pr: bool = None):
    sample = ("Enter the date if you want to receive notifications.\n"
              "Date should be <i>day.month</i> (ex. 01.06)")
    mk = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Today',
                                  callback_data=TaskCB(tid=await state.get_value("name"), text='rem-today').pack()),
             InlineKeyboardButton(text='Tomorrow', callback_data=TaskCB(tid=await state.get_value("name"),
                                                                        text='rem-tomorrow').pack())],
            [InlineKeyboardButton(text="Don't create reminder",
                                  callback_data=f"task-{await state.get_value("name")}-rem-0")],
            [cancel_fsm_button]
        ]
    )

    mess = c
    if is_pr is None:
        is_pr = bool(c.data.split('-')[-1])
        mess = c.message

    if is_pr:  # with priority
        await state.update_data({'priority': is_pr})
        await mess.answer(text=sample, reply_markup=mk, parse_mode="HTML")
        await state.set_state(AddT.received_reminder_dt)
    else:  # with no priority
        await mess.answer(text=sample, reply_markup=mk, parse_mode="HTML")
        await state.set_state(AddT.received_reminder_dt)


@cbrouter.callback_query(AddT.received_reminder_dt, F.data.contains('today') | F.data.contains('tomorrow'))
async def user_ex_rem_date(c: CallbackQuery, state: FSMContext):
    match c.data.split('-')[-1]:
        case 'today':
            date = datetime.datetime.now()
            await user_rem_date(c.message, state, datetime.datetime.strptime(f"{date.day}.{date.month}", "%d.%m"))
        case 'tomorrow':
            date = datetime.datetime.now() + datetime.timedelta(days=1)
            await user_rem_date(c.message, state, datetime.datetime.strptime(f"{date.day}.{date.month}", "%d.%m"))


@cbrouter.message(AddT.received_reminder_dt)
async def user_rem_date(c: Message, state: FSMContext, date=None):
    try:
        if not date:
            date = datetime.datetime.strptime(c.text, "%d.%m")

        await state.update_data({'reminder': handle_date(date)})

        await state.set_state(AddT.received_reminder_time)
        await c.answer(text='Enter reminder time.\n'
                            'Time should be hours:minutes (ex. 15:30)')
    except ValueError:
        await c.answer('Invalid date or format.\nTry again.')
        await state.set_state(AddT.received_reminder_dt)
    except Exception as e:
        logger.error(e)


@cbrouter.message(AddT.received_reminder_time)
async def finish_creation(c: Message, state: FSMContext):
    try:
        tm = datetime.datetime.strptime(f"{await state.get_value('reminder')} {c.text.strip()}",
                                        f"%Y-%m-%d %H:%M")

        if datetime.datetime.now() < tm:
            await state.update_data({'reminder': tm})
            await cr_task(user_id=c.from_user.id, **await state.get_data())

            await c.answer(text=r'Task was <b>successfully</b> created! Type /list to see your tasks.',
                           parse_mode='HTML')
            logger.info(f'USER {c.from_user.id} CREATED TASK.')
            await state.clear()
        else:
            await c.answer('Your reminder date is before current date.\nTry again.')
            await state.update_data({'reminder': None})
            await add_reminder(c, state, await state.get_value("priority"))
    except ValueError:
        await c.answer('Invalid time or format.\nTry again.')
        await state.set_state(AddT.received_reminder_time)
    except Exception as e:
        logger.error(e)


@cbrouter.callback_query(F.data.endswith('rem-0'), AddT.received_reminder_dt)
async def finish_with_no_reminder(c: CallbackQuery, state: FSMContext):
    try:
        await cr_task(user_id=c.from_user.id, **await state.get_data())
    except Exception as e:
        logger.error(f'ERROR WITH INSERT INTO DB, NO REMINDER : {e}')

    await c.message.answer(text=r'Task was <b>successfully</b> created! Type /list to see your tasks.',
                           parse_mode='HTML')
    logger.info(f'task {await state.get_value("name")} created {await state.get_value('priority')}')
    await state.clear()


@cbrouter.callback_query(F.data == 'cancel_add')
async def cancel_add(c: CallbackQuery, state: FSMContext):
    if await state.get_state():
        await state.clear()

    logger.info(f"USER {c.from_user.id} CANCELLED CREATING A TASK")
    await c.message.answer('You cancelled creating a task.')


@cbrouter.message(Command("list"))
async def show_list(m: Message, exc: bool = False):
    tasks = await get_tasks(m.chat.id)

    if not tasks:
        text = "You don't have any tasks yet."
        keyboard = None
    else:
        text = 'Here is list of your tasks:'
        keyboard = InlineKeyboardBuilder()
        for task in tasks:
            txt = (task.get("name"), ("\u2705", "❌")[not task.get("is_completed")])
            keyboard.button(text=' '.join(txt), callback_data=f'show-task:{task.get("id")}')
        keyboard.adjust(1)

    if exc:
        await m.edit_text(text, reply_markup=keyboard.as_markup()) if keyboard else await m.edit_text(text)
    else:
        await m.answer(text, reply_markup=keyboard.as_markup()) if keyboard else await m.answer(text)


@cbrouter.message(Command("listuncompleted"))
async def show_unc_tasks(m: Message, exc: bool = False):
    tasks = await get_uncompleted_tasks(m.chat.id)

    if not tasks:
        text = "You don't have any uncompleted tasks yet."
        keyboard = None
    else:
        text = 'Here is list of your uncompleted tasks.'
        keyboard = InlineKeyboardBuilder()
        for task in tasks:
            txt = (task.get("name"), "❌")
            keyboard.button(text=' '.join(txt), callback_data=f'show-task:{task.get("id")}')
        keyboard.adjust(1)

    if exc:
        await m.edit_text(text, reply_markup=keyboard.as_markup()) if keyboard else await m.edit_text(text)
    else:
        await m.answer(text, reply_markup=keyboard.as_markup()) if keyboard else await m.answer(text)


@cbrouter.callback_query(F.data.startswith("show-task"))
async def show_exact_task(c: CallbackQuery):
    task = await get_task_by_id(task_id := int(c.data.split(':')[-1]))

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text='Back⬅️', callback_data='back-to-list')
    keyboard.button(text='Delete task🗑️', callback_data=f'del-task:{task_id}')
    if not task[-1].get('is_completed'):
        keyboard.button(text='Task is ready✅', callback_data=f'upd-status:{task_id}')

    await c.message.edit_text(handle_task(*task), reply_markup=keyboard.as_markup(), parse_mode='HTML')


@cbrouter.callback_query(F.data == "back-to-list")
async def back_to_list(c: CallbackQuery):
    await show_list(c.message, True)


@cbrouter.callback_query(F.data.startswith("del-task"))
async def del_task(c: CallbackQuery):
    try:
        await del_task_by_id(int(c.data.split(':')[-1]))
        await c.answer('Successfully deleted✅')
        await show_list(c.message, True)
    except Exception as e:
        logger.warning(e)


@cbrouter.callback_query(F.data.startswith("upd-status"))
async def ready_task(c: CallbackQuery):
    try:
        await upd_ready(int(c.data.split(':')[-1]))
        await c.answer('Successfully updated✅')
        await show_exact_task(c)
    except Exception as e:
        logger.warning(e)

@cbrouter.message(CommandStart())
async def start(m: Message, state: FSMContext):
    if await state.get_state():
        await state.clear()

    await m.answer('This is simple to-do bot with notifications.\n'
                   'Type /add to add new task.')

@cbrouter.message()
async def any_message(m: Message, state: FSMContext):
    if await state.get_state():
        await m.answer('Invalid input. Try again.')
        await state.set_state(await state.get_state())
    else:
        await m.reply('Invalid command. Type / to see menu.')

async def start_reminder():
    await Reminder(bt).start_(reminder_check_delay)

async def start_bt():
    dp.include_router(cbrouter)
    await bt.set_my_commands(menu)

    try:
        await dp.start_polling(bt)
    except CancelledError:
        pass


async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(start_bt())
        tg.create_task(start_reminder())


asyncio.run(main())
