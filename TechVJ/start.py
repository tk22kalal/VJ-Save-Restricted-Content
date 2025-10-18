# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os
import asyncio
import pyrogram
from pyrogram import Client, filters, enums
from pyrogram.errors import (
    FloodWait,
    UserIsBlocked,
    InputUserDeactivated,
    UserAlreadyParticipant,
    InviteHashExpired,
    UsernameNotOccupied,
)
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import API_ID, API_HASH, ERROR_MESSAGE, LOGIN_SYSTEM, STRING_SESSION
from database.db import db
from TechVJ.strings import HELP_TXT
from TechVJ.optimized_batch import batch_processor
from TechVJ.settings import clean_caption
from bot import TechVJUser


class batch_temp(object):
    IS_BATCH = {}


async def downstatus(client, statusfile, message, chat):
    while True:
        if os.path.exists(statusfile):
            break
        await asyncio.sleep(3)

    while os.path.exists(statusfile):
        with open(statusfile, "r") as downread:
            txt = downread.read()
        try:
            await client.edit_message_text(chat, message.id, f"**Downloaded:** **{txt}**")
            await asyncio.sleep(10)
        except:
            await asyncio.sleep(5)


# upload status
async def upstatus(client, statusfile, message, chat):
    while True:
        if os.path.exists(statusfile):
            break
        await asyncio.sleep(3)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as upread:
            txt = upread.read()
        try:
            await client.edit_message_text(chat, message.id, f"**Uploaded:** **{txt}**")
            await asyncio.sleep(10)
        except:
            await asyncio.sleep(5)


# progress writer
def progress(current, total, message, type):
    with open(f"{message.id}{type}status.txt", "w") as fileup:
        fileup.write(f"{current * 100 / total:.1f}%")


# start command
@Client.on_message(filters.command(["start"]))
async def send_start(client: Client, message: Message):
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
    buttons = [
        [InlineKeyboardButton("❣️ Developer", url="https://t.me/kingvj01")],
        [
            InlineKeyboardButton("🔍 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ", url="https://t.me/vj_bot_disscussion"),
            InlineKeyboardButton("🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ", url="https://t.me/vj_botz"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await client.send_message(
        chat_id=message.chat.id,
        text=(
            f"<b>👋 Hi {message.from_user.mention}, I am Save Restricted Content Bot.\n\n"
            "I can send you restricted content by its post link.\n\n"
            "For downloading restricted content use /login first (if login system is enabled).\n\n"
            "Send me a Telegram post link (for example: https://t.me/somechannel/123) and I'll try to fetch it for you.\n\n"
            "🚀 NEW: Use /settings to customize batch processing, caption cleanup, and more!</b>"
        ),
        reply_markup=reply_markup,
        reply_to_message_id=message.id,
        parse_mode=enums.ParseMode.HTML,
    )
    return


# help command
@Client.on_message(filters.command(["help"]))
async def send_help(client: Client, message: Message):
    await client.send_message(chat_id=message.chat.id, text=f"{HELP_TXT}", parse_mode=enums.ParseMode.HTML)


# cancel command
@Client.on_message(filters.command(["cancel"]))
async def send_cancel(client: Client, message: Message):
    batch_temp.IS_BATCH[message.from_user.id] = True
    await client.send_message(chat_id=message.chat.id, text="**Batch Successfully Cancelled.**")


@Client.on_message(filters.text & filters.private)
async def save(client: Client, message: Message):
    # joining chats
    if ("https://t.me/+" in message.text or "https://t.me/joinchat/" in message.text) and LOGIN_SYSTEM == False:
        if TechVJUser is None:
            await client.send_message(message.chat.id, f"**String Session is not Set**", reply_to_message_id=message.id)
            return
        try:
            try:
                await TechVJUser.join_chat(message.text)
            except Exception as e:
                await client.send_message(message.chat.id, f"**Error** : __{e}__", reply_to_message_id=message.id)
                return
            await client.send_message(message.chat.id, "**Chat Joined**", reply_to_message_id=message.id)
        except UserAlreadyParticipant:
            await client.send_message(message.chat.id, "**Chat already Joined**", reply_to_message_id=message.id)
        except InviteHashExpired:
            await client.send_message(message.chat.id, "**Invalid Link**", reply_to_message_id=message.id)
        return

    if "https://t.me/" in message.text:
        # ensure user has no other batch running
        if batch_temp.IS_BATCH.get(message.from_user.id) == False:
            return await message.reply_text(
                "**One Task Is Already Processing. Wait For Complete It. If You Want To Cancel This Task Then Use - /cancel**"
            )

        datas = message.text.split("/")
        
        is_supergroup = False
        topic_id = None
        chatid = None
        
        if "https://t.me/c/" in message.text and len(datas) >= 7:
            is_supergroup = True
            try:
                chatid = int("-100" + datas[4])
                topic_id = int(datas[5])
                temp = datas[6].replace("?single", "").split("-")
            except:
                temp = datas[-1].replace("?single", "").split("-")
                is_supergroup = False
        else:
            temp = datas[-1].replace("?single", "").split("-")
        
        try:
            fromID = int(temp[0].strip())
        except:
            return await message.reply_text("Invalid message link / id.")
        try:
            toID = int(temp[1].strip())
        except:
            toID = fromID

        batch_temp.IS_BATCH[message.from_user.id] = False
        
        total_messages = toID - fromID + 1
        
        user_settings = await db.get_user_settings(message.from_user.id)
        # NEW CODE (use this):
        # Always use optimized batch processor for better performance and features
        use_optimized = True  # Force use optimized processor
        
        if use_optimized:
            acc = None
            acc_created = False
            
            if LOGIN_SYSTEM == True:
                user_data = await db.get_session(message.from_user.id)
                if user_data is None:
                    await message.reply("**For Downloading Restricted Content You Have To /login First.**")
                    batch_temp.IS_BATCH[message.from_user.id] = True
                    return
                try:
                    acc = Client("saverestricted", session_string=user_data, api_hash=API_HASH, api_id=API_ID)
                    await acc.start()
                    acc_created = True
                except Exception as e:
                    batch_temp.IS_BATCH[message.from_user.id] = True
                    return await message.reply(f"**Your Login Session Expired. So /logout First Then Login Again By - /login. Error: {e}**")
            else:
                if TechVJUser is None:
                    batch_temp.IS_BATCH[message.from_user.id] = True
                    await client.send_message(message.chat.id, f"**String Session is not Set**", reply_to_message_id=message.id)
                    return
                acc = TechVJUser
            
            # Parse chatid before calling batch processor
            if chatid is None:
                if "https://t.me/c/" in message.text:
                    chatid = int("-100" + datas[4])
                elif "https://t.me/b/" in message.text:
                    chatid = datas[4]
                else:
                    chatid = datas[3]
            
            # Use try/finally to ensure session cleanup happens no matter what
            try:
                # Use optimized batch processor with settings
                await batch_processor.batch_process_with_concurrency(
                    client, acc, message, chatid, fromID, toID, user_settings, max_concurrent=2, topic_id=topic_id
                )
            except Exception as e:
                # If optimized processor fails, show error but don't fall back to old method
                await message.reply(f"**❌ Optimized batch processor failed. Error: {str(e)}**")
            finally:
                # Always clean up the session if we created it
                if acc_created and acc is not None:
                    try:
                        await acc.stop()
                    except:
                        pass
                batch_temp.IS_BATCH[message.from_user.id] = True
            return
        
        await message.reply(f"**Starting batch download of {total_messages} message(s)...**")
        
        for msgid in range(fromID, toID + 1):
            if batch_temp.IS_BATCH.get(message.from_user.id):
                break

            # decide which account to use
            if LOGIN_SYSTEM == True:
                user_data = await db.get_session(message.from_user.id)
                if user_data is None:
                    await message.reply("**For Downloading Restricted Content You Have To /login First.**")
                    batch_temp.IS_BATCH[message.from_user.id] = True
                    return
                try:
                    acc = Client("saverestricted", session_string=user_data, api_hash=API_HASH, api_id=API_ID)
                    await acc.start()
                except Exception:
                    batch_temp.IS_BATCH[message.from_user.id] = True
                    return await message.reply("**Your Login Session Expired. So /logout First Then Login Again By - /login**")
            else:
                if TechVJUser is None:
                    batch_temp.IS_BATCH[message.from_user.id] = True
                    await client.send_message(message.chat.id, f"**String Session is not Set**", reply_to_message_id=message.id)
                    return
                acc = TechVJUser

            # private (/c/)
            if "https://t.me/c/" in message.text:
                if is_supergroup and topic_id is not None and chatid is not None:
                    try:
                        await handle_private_supergroup(client, acc, message, chatid, topic_id, msgid)
                    except Exception as e:
                        if ERROR_MESSAGE:
                            await client.send_message(message.chat.id, f"Error processing supergroup message {msgid}: {e}", reply_to_message_id=message.id)
                else:
                    try:
                        if chatid is None:
                            chatid = int("-100" + datas[4])
                    except Exception:
                        await client.send_message(message.chat.id, "**Unable to parse private chat link**", reply_to_message_id=message.id)
                        return
                    try:
                        await handle_private(client, acc, message, chatid, msgid)
                    except Exception as e:
                        if ERROR_MESSAGE:
                            await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)

            # bot (/b/)
            elif "https://t.me/b/" in message.text:
                try:
                    username = datas[4]
                    await handle_private(client, acc, message, username, msgid)
                except Exception as e:
                    if ERROR_MESSAGE:
                        await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)

            # public
            else:
                username = datas[3]
                try:
                    msg = await client.get_messages(username, msgid)
                except UsernameNotOccupied:
                    await client.send_message(message.chat.id, "The username is not occupied by anyone", reply_to_message_id=message.id)
                    return
                try:
                    await client.copy_message(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                except Exception:
                    try:
                        await handle_private(client, acc, message, username, msgid)
                    except Exception as e:
                        if ERROR_MESSAGE:
                            await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)

            # wait time between iterations
            await asyncio.sleep(3)

        batch_temp.IS_BATCH[message.from_user.id] = True
        await message.reply("**✅ Batch download completed!**")


# handle private supergroup with topic/sub-group filtering
async def handle_private_supergroup(client: Client, acc, message: Message, chatid: int, topic_id: int, msgid: int):
    try:
        msg: Message = await acc.get_messages(chatid, msgid)
        
        if not msg or msg.empty:
            return
        
        if hasattr(msg, 'reply_to_message_id') and msg.reply_to_message_id:
            reply_msg = await acc.get_messages(chatid, msg.reply_to_message_id)
            if hasattr(reply_msg, 'message_thread_id'):
                msg_topic_id = reply_msg.message_thread_id
            else:
                msg_topic_id = None
        elif hasattr(msg, 'message_thread_id'):
            msg_topic_id = msg.message_thread_id
        else:
            msg_topic_id = None
        
        if msg_topic_id != topic_id:
            return
        
        await handle_private(client, acc, message, chatid, msgid)
        
    except Exception as e:
        if ERROR_MESSAGE:
            await client.send_message(message.chat.id, f"Error in supergroup handler: {e}", reply_to_message_id=message.id)


# handle private
async def handle_private(client: Client, acc, message: Message, chatid: int, msgid: int):
    msg: Message = await acc.get_messages(chatid, msgid)
    if not msg or msg.empty:
        return
    msg_type = get_message_type(msg)
    if not msg_type:
        return
    chat = message.chat.id
    if batch_temp.IS_BATCH.get(message.from_user.id):
        return

    if msg_type == "Text":
        try:
            await client.send_message(chat, msg.text, entities=msg.entities, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
            return
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
            return

    smsg = await client.send_message(message.chat.id, "**Downloading**", reply_to_message_id=message.id)
    asyncio.create_task(downstatus(client, f"{message.id}downstatus.txt", smsg, chat))
    try:
        file = await acc.download_media(msg, progress=progress, progress_args=[message, "down"])
        if os.path.exists(f"{message.id}downstatus.txt"):
            os.remove(f"{message.id}downstatus.txt")
    except Exception as e:
        if ERROR_MESSAGE:
            await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        await smsg.delete()
        return

    if batch_temp.IS_BATCH.get(message.from_user.id):
        return

    asyncio.create_task(upstatus(client, f"{message.id}upstatus.txt", smsg, chat))

    caption = msg.caption if msg.caption else None

    if batch_temp.IS_BATCH.get(message.from_user.id):
        return

    # Document
    if msg_type == "Document":
        ph_path = None
        try:
            if msg.document.thumbs:
                ph_path = await acc.download_media(msg.document.thumbs[0].file_id)
        except Exception:
            ph_path = None

        try:
            await client.send_document(
                chat,
                file,
                thumb=ph_path,
                caption=caption,
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        if ph_path:
            try:
                os.remove(ph_path)
            except:
                pass

    # Video
    elif msg_type == "Video":
        ph_path = None
        try:
            if msg.video.thumbs:
                ph_path = await acc.download_media(msg.video.thumbs[0].file_id)
        except Exception:
            ph_path = None

        try:
            await client.send_video(
                chat,
                file,
                duration=getattr(msg.video, "duration", None),
                width=getattr(msg.video, "width", None),
                height=getattr(msg.video, "height", None),
                thumb=ph_path,
                caption=caption,
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        if ph_path:
            try:
                os.remove(ph_path)
            except:
                pass

    # Animation (gif)
    elif msg_type == "Animation":
        try:
            await client.send_animation(chat, file, caption=caption, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)

    # Sticker
    elif msg_type == "Sticker":
        try:
            await client.send_sticker(chat, file, reply_to_message_id=message.id)
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)

    # Voice
    elif msg_type == "Voice":
        try:
            await client.send_voice(
                chat,
                file,
                caption=caption,
                caption_entities=getattr(msg, "caption_entities", None),
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)

    # Audio
    elif msg_type == "Audio":
        ph_path = None
        try:
            if getattr(msg.audio, "thumbs", None):
                ph_path = await acc.download_media(msg.audio.thumbs[0].file_id)
        except Exception:
            ph_path = None

        try:
            await client.send_audio(
                chat,
                file,
                thumb=ph_path,
                caption=caption,
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        if ph_path:
            try:
                os.remove(ph_path)
            except:
                pass

    # Photo
    elif msg_type == "Photo":
        try:
            await client.send_photo(chat, file, caption=caption, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)

    # cleanup
    try:
        if os.path.exists(f"{message.id}upstatus.txt"):
            os.remove(f"{message.id}upstatus.txt")
        if os.path.exists(file):
            os.remove(file)
    except Exception:
        pass

    try:
        await client.delete_messages(message.chat.id, [smsg.id])
    except:
        pass


# get the type of message
def get_message_type(msg: pyrogram.types.messages_and_media.message.Message):
    try:
        if getattr(msg, "document", None) and getattr(msg.document, "file_id", None):
            return "Document"
    except:
        pass

    try:
        if getattr(msg, "video", None) and getattr(msg.video, "file_id", None):
            return "Video"
    except:
        pass

    try:
        if getattr(msg, "animation", None) and getattr(msg.animation, "file_id", None):
            return "Animation"
    except:
        pass

    try:
        if getattr(msg, "sticker", None) and getattr(msg.sticker, "file_id", None):
            return "Sticker"
    except:
        pass

    try:
        if getattr(msg, "voice", None) and getattr(msg.voice, "file_id", None):
            return "Voice"
    except:
        pass

    try:
        if getattr(msg, "audio", None) and getattr(msg.audio, "file_id", None):
            return "Audio"
    except:
        pass

    try:
        if getattr(msg, "photo", None):
            return "Photo"
    except:
        pass

    try:
        if getattr(msg, "text", None):
            return "Text"
    except:
        pass
    return None
