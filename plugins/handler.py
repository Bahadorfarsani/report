import time
from datetime import datetime
import subprocess
import bcrypt
import sqlalchemy as db
from sqlalchemy.orm import sessionmaker
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.enums import ChatAction
from pyrogram.types import Message, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from constants import messages
from database import Message, Account, User, Admin
import random
import string
import pandas as pd
import pyromod.listen

from os import listdir

def tree():
    return defaultdict(tree)


user_pocket = tree()

engine = db.create_engine("mysql://armin:T101vb$!GuYX@ub.pxnet.de/telegram_bot", echo=True)
connection = engine.connect()
Session = sessionmaker(bind=engine)


@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_pocket[message.from_user.id]["step"] = "start"
    await message.reply_chat_action(ChatAction.TYPING)
    keys = [[messages["today_messages"], messages["date_filter_messages"]], [messages["get_report"]]]
    keyboard = ReplyKeyboardMarkup(keys, resize_keyboard=True, one_time_keyboard=True)
    await client.send_message(chat_id=message.from_user.id, text=messages["welcome"], reply_markup=keyboard)

@Client.on_message(filters.regex(messages["today_messages"]) & filters.private)
async def today_messages(client: pyromod.listen.Client, message: Message):
    session = Session()
    msg_list = session.query(Message).filter_by(date=time.strftime('%Y-%m-%d')).all()
    if len(msg_list) == 0:
        await message.reply_text(messages["there_is_no_message"])
        return
    for msg in msg_list:
        await message.reply_text("{}\n{}\n\n{}".format(msg.username,msg.date,msg.message))

@Client.on_message(filters.regex(messages["date_filter_messages"]) & filters.private)
async def date_filter_messages(client: pyromod.listen.Client, message: Message):
    user_pocket[message.from_user.id]["step"] = "message_date"
    session = Session()
    date = await client.ask(chat_id=message.from_user.id, text=messages["please_enter_date"])
    if date.text == "back":
        await back()
    else:
        msg_list = session.query(Message).filter_by(date = date.text).all()
        if len(msg_list) == 0:
            await message.reply_text(messages["there_is_no_message"])
            return
        for msg in msg_list:
            await message.reply_text("{}\n{}\n\n{}".format(msg.username,msg.date,msg.message))


@Client.on_message(filters.regex(messages["get_report"]) & filters.private)
async def get_report(client: pyromod.listen.Client, message: Message):
    user_pocket[message.from_user.id]["step"] = "get_report"    
    keys = [[messages["summary_all"], messages["summary_today"]],[messages["users_report"]],
            [messages["hosts_report"]],[messages["back"]]]
    keyboard = ReplyKeyboardMarkup(keys, resize_keyboard=True)
    await message.reply_text(messages["choose_your_option"], reply_markup=keyboard)

@Client.on_message(filters.regex(messages["summary_all"]) & filters.private)
async def get_summary(client: pyromod.listen.Client, message: Message):
   if user_pocket[message.from_user.id]["step"] == "get_report":
        session = Session()
        host_name = await client.ask(chat_id=message.from_user.id, text=messages["enter_host_name"])
        if host_name.text == "back":
            await back()
        else:
            count = session.query(Account).filter_by(host=host_name.text).count()
            await message.reply_text("{}: {}\n".format(messages["all_accounts_count"], count))
            users = session.query(User).with_entities(User.username).all()
            msg = messages["accounts_per_user"]+ "\n\n"
            for user in users:
                account_per_user = session.query(Account).filter_by(host=host_name.text, creator=user[0]).count()
                if account_per_user != 0:
                    msg += "{}: {}\n".format(user[0], account_per_user)
            await message.reply_text(msg)

@Client.on_message(filters.regex(messages["summary_today"]) & filters.private)
async def get_today_summary(client: pyromod.listen.Client, message: Message):
   if user_pocket[message.from_user.id]["step"] == "get_report":
        session = Session()
        host_name = await client.ask(chat_id=message.from_user.id, text=messages["enter_host_name"])
        if host_name.text == "back":
            await back()
        else:
            count = session.query(Account).filter_by(host=host_name.text, created_date=time.strftime('%Y-%m-%d')).count()
            await message.reply_text("{}: {}\n".format(messages["accounts_created_today"], count))
            if count != 0:
                users = session.query(User).with_entities(User.username).all()
                msg = messages["accounts_per_user"]+ "\n\n"
                for user in users:
                    account_per_user = session.query(Account).filter_by(host=host_name.text, creator=user[0], created_date=time.strftime('%Y-%m-%d')).count()
                    if account_per_user != 0:
                        msg += "{}: {}\n".format(user[0], account_per_user)
                await message.reply_text(msg)        

@Client.on_message(filters.regex(messages["users_report"]) & filters.private)
async def users_report(client: pyromod.listen.Client, message: Message):
    if user_pocket[message.from_user.id]["step"] == "get_report" or user_pocket[message.from_user.id]["step"] == "authenticated":
        user_pocket[message.from_user.id]["step"] = "users_report"
        session = Session()
        user_name = await client.ask(chat_id=message.from_user.id, text=messages["enter_username"])
        if user_name.text == "back":
            await back()
        else:
            session = Session()
            if user_pocket[message.from_user.id]["type"] != "admin":
                exists = session.query(
                    session.query(Admin).filter_by(username=user_name.text).exists()
                ).scalar()
                if exists:
                    await message.reply_text(messages["user_not_found"])
                    return
            
            exists = session.query(
                session.query(User).filter_by(username=user_name.text).exists()
            ).scalar()
            if exists:
                await get_report_excel(client, message, "user",user_name.text)
            else:
                await message.reply_text(messages["user_not_found"]) 
                user_pocket[message.from_user.id]["step"] = "get_report"


@Client.on_message(filters.regex(messages["hosts_report"]) & filters.private)
async def hosts_report(client: pyromod.listen.Client, message: Message):
    if user_pocket[message.from_user.id]["step"] == "get_report":
        user_pocket[message.from_user.id]["step"] = "hosts_report"
        host_name = await client.ask(chat_id=message.from_user.id, text=messages["enter_host_name"])
        if host_name.text == "back":
            await back()
        else:
            session = Session()
            exists = session.query(
                session.query(Account).filter_by(host=host_name.text).exists()
            ).scalar()
            
            if exists:
                await get_report_excel(client, message, "host",host_name.text)
            else:
                await message.reply_text(messages["host_not_found"]) 
                user_pocket[message.from_user.id]["step"] = "get_report"


async def get_report_excel(client: pyromod.listen.Client, message:Message, mode, filter_item):
        keys = [[messages["full_report"], messages["filter_by_date"]],[messages["filter_by_expiration"]], [messages["back"]]]
        keyboard = ReplyKeyboardMarkup(keys, resize_keyboard=True)    
        await message.reply_text(messages["choose_your_option"], reply_markup=keyboard)
        res = await client.ask(chat_id=message.from_user.id, text=messages["choose_report_type"])
        session = Session()
        accounts = []
        while(res.text != messages["full_report"] and res.text != messages["filter_by_date"] and res.text != messages["back"] and res.text != messages["filter_by_expiration"]):
            if res.text == "back":
                await back()
            else:
                await message.reply_text(messages["try_again"])
                res = await client.ask(chat_id=message.from_user.id, text=messages["choose_report_type"])

        if res.text == messages["full_report"]:
            if mode == "user":
                accounts = session.query(Account).filter(Account.creator == filter_item)
            elif mode == "host":
                accounts = session.query(Account).filter(Account.host == filter_item)

        elif res.text == messages["filter_by_date"]:
            start_date = await client.ask(chat_id=message.from_user.id, text=messages["please_enter_start_date"])
            if start_date.text == "back":
                back()
                return
            end_date = await client.ask(chat_id=message.from_user.id, text=messages["please_enter_end_date"])
            if end_date.text == "back":
                back()
                return
            if mode == "user":
                accounts = session.query(Account).filter(Account.creator == filter_item).filter(Account.created_date.between(start_date.text,end_date.text))
            elif mode == "host":
                accounts = session.query(Account).filter(Account.host == filter_item).filter(Account.created_date.between(start_date.text,end_date.text))

        elif res.text == messages["filter_by_expiration"]:
            start_expiration = await client.ask(chat_id=message.from_user.id, text=messages["please_enter_start_expiration"])
            if start_expiration.text == "back":
                back()
                return
            end_expiration = await client.ask(chat_id=message.from_user.id, text=messages["please_enter_end_expiration"])
            if end_expiration.text == "back":
                back()
                return
            if mode == "user":
                accounts = session.query(Account).filter(Account.creator == filter_item).filter(Account.expiration.between(start_expiration.text,end_expiration.text))
            elif mode == "host":
                accounts = session.query(Account).filter(Account.host == filter_item).filter(Account.expiration.between(start_expiration.text,end_expiration.text))

        elif res.text == messages["back"]:
            await back(client,message)
            return
        filename = '{}-{}.xlsx'.format(filter_item,time.strftime('%m-%d %H:%M:%S'))
        data_list = [await to_dict(item) for item in accounts]
        df = pd.DataFrame(data_list)
        writer = pd.ExcelWriter(filename)
        df.to_excel(writer, index=False)
        writer.save()
        await message.reply_document(filename)
        subprocess.run(['rm','-rf',filename])
        user_pocket[message.from_user.id]["step"] = "get_report"    
        keys = [[messages["summary_all"], messages["summary_today"]], [messages["users_files_retrieval"]],[messages["users_report"]],
                [messages["hosts_report"]],[messages["back"]]]
        keyboard = ReplyKeyboardMarkup(keys, resize_keyboard=True)
        await message.reply_text(messages["choose_your_option"], reply_markup=keyboard)

async def to_dict(row):
    if row is None:
        return None

    rtn_dict = dict()
    keys = row.__table__.columns.keys()
    for key in keys:
        rtn_dict[key] = getattr(row, key)
    return rtn_dict



@Client.on_message(filters.regex(messages["back"]) & filters.private)
async def back(client: pyromod.listen.Client, message: Message):
    if user_pocket[message.from_user.id]["step"] == "message_date" or \
       user_pocket[message.from_user.id]["step"] == "get_report":
        user_pocket[message.from_user.id]["step"] = "start"
        keys = [[messages["today_messages"], messages["date_filter_messages"]], [messages["get_report"]]]
    else:
        user_pocket[message.from_user.id]["step"] = "get_report"
        keys = [[messages["summary_all"], messages["summary_today"]],[messages["users_report"]],
            [messages["hosts_report"]],[messages["back"]]]
        
    keyboard = ReplyKeyboardMarkup(keys, resize_keyboard=True, one_time_keyboard=True)
    await client.send_message(chat_id=message.from_user.id, text= messages["choose_your_option"], reply_markup=keyboard)   
    


