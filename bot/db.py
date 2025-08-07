from datetime import datetime

import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def get_connection():
    db_conf = {
        "user": os.getenv('DB_USER'),
        "password": os.getenv('DB_PASSWORD'),
        "database": os.getenv('DB_NAME'),
        "host": os.getenv('DB_HOST'),
        "port": os.getenv('DB_PORT')
    }

    return await asyncpg.connect(**db_conf)

async def get_tasks(user_id: int):
    conn = await get_connection()
    try:
        tasks = await conn.fetch(
            "SELECT * FROM tasks WHERE user_id = $1 ORDER BY priority, id",
            user_id)
        return tasks
    finally:
        await conn.close()

async def get_uncompleted_tasks(user_id: int):
    conn = await get_connection()
    try:
        tasks = await conn.fetch(
            "SELECT * FROM tasks "
            "WHERE user_id = $1 AND is_completed = false "
            "ORDER BY priority, id;",
            user_id)
        return tasks
    finally:
        await conn.close()

async def cr_task(user_id: int, name: str, desc: str, priority: bool = False, reminder: datetime = None):
    conn = await get_connection()
    try:
        await conn.execute(
            'INSERT INTO tasks (user_id, name, description, priority, reminder)'
            'VALUES ($1, $2, $3, $4, $5)',
            user_id, name, desc, priority, reminder)
    finally:
        await conn.close()

async def del_task_by_id(task_id: int):
    conn = await get_connection()
    try:
        await conn.execute(
            'DELETE FROM tasks WHERE id = $1',
            task_id)
    finally:
        await conn.close()

async def del_reminder_for_task(task_id: int):
    conn = await get_connection()
    try:
        await conn.execute(
            'UPDATE tasks SET reminder = NULL WHERE id = $1',
            task_id)
    finally:
        await conn.close()

async def upd_ready(task_id: int):
    conn = await get_connection()

    try:
        await conn.execute(
            "UPDATE tasks SET is_completed = True WHERE id = $1",
            task_id)
    finally:
        await conn.close()

async def get_task_by_id(task_id: int):
    conn = await get_connection()

    try:
        return await conn.fetch(
            "SELECT * FROM tasks WHERE id = $1",
            task_id)
    finally:
        await conn.close()

async def get_remind_tasks():
    conn = await get_connection()
    try:
        tasks = await conn.fetch(
            "SELECT * FROM tasks WHERE reminder IS NOT NULL AND reminder_sent = false",
        )
        return tasks
    finally:
        await conn.close()

async def get_remind_tasks_for_user(user_id: int):
    conn = await get_connection()
    tasks = await conn.fetch(
        "SELECT * FROM tasks WHERE user_id = $1 AND reminder IS NOT NULL AND reminder_sent = false",
        user_id
    )
    await conn.close()
    return tasks

async def upd_sent_reminder(task_id: int):
    conn = await get_connection()

    try:
        await conn.execute(
            "UPDATE tasks SET reminder_sent = true WHERE id = $1",
            task_id)
    finally:
        await conn.close()
