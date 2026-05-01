# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
import os
import asyncio
import pyrogram
import time
from pyrogram import Client, filters, enums
from pyrogram.errors import (
    FloodWait,
    UserIsBlocked,
    InputUserDeactivated,
    UserAlreadyParticipant,
    InviteHashExpired,
    UsernameNotOccupied,
    ChatWriteForbidden,
)
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import API_ID, API_HASH, ERROR_MESSAGE, LOGIN_SYSTEM, STRING_SESSION
from database.db import db
from TechVJ.strings import HELP_TXT
from TechVJ.settings import clean_caption, clean_filename
from bot import TechVJUser

os.makedirs("downloads", exist_ok=True)


class batch_temp(object):
    IS_BATCH = {}


async def retry_on_error(func, *args, max_retries=10, initial_delay=3, **kwargs):
    """
    Retry a function with exponential backoff for connection errors.
    Handles OSError, TimeoutError, and other network-related exceptions.
    """
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except FloodWait as e:
            print(f"FloodWait {e.value}s on attempt {attempt + 1}, waiting...")
            await asyncio.sleep(e.value)
        except (OSError, TimeoutError, ConnectionError) as e:
            if attempt == max_retries - 1:
                print(f"Failed after {max_retries} retries: {e}")
                raise
            delay = min(initial_delay * (2 ** attempt), 60)
            print(f"Connection/Timeout error on attempt {attempt + 1}/{max_retries}: {e}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
        except (pyrogram.errors.AuthKeyUnregistered, pyrogram.errors.AuthKeyInvalid, pyrogram.errors.SessionRevoked):
            raise
        except Exception as e:
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['timeout', 'connection', 'network', 'disconnect', 'lost', 'timed out']):
                if attempt == max_retries - 1:
                    print(f"Failed after {max_retries} retries: {e}")
                    raise
                delay = min(initial_delay * (2 ** attempt), 60)
                print(f"Network-related error on attempt {attempt + 1}/{max_retries}: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                raise
    raise Exception(f"Failed after {max_retries} attempts")


def format_send_error(e: Exception, destination_chat) -> str:
    """Format error messages for sending to destination channels"""
    if isinstance(e, ChatWriteForbidden):
        return (
            "❌ **Bot Permission Error**\n\n"
            f"Cannot send to destination channel `{destination_chat}`\n\n"
            "**Required Actions:**\n"
            "1. Add the bot to the channel\n"
            "2. Promote bot to admin\n"
            "3. Enable 'Post Messages' permission\n\n"
            "Or use /settings to change the destination channel."
        )
    return f"Error: {e}"


async def downstatus(client, statusfile, message, chat, link=""):
    while True:
        if os.path.exists(statusfile):
            break
        await asyncio.sleep(3)

    while os.path.exists(statusfile):
        with open(statusfile, "r") as downread:
            txt = downread.read()
        try:
            link_line = f"\n{link}" if link else ""
            await client.edit_message_text(chat, message.id, f"**Downloading:** **{txt}**{link_line}")
            await asyncio.sleep(10)
        except:
            await asyncio.sleep(5)


async def upstatus(client, statusfile, message, chat, link=""):
    while True:
        if os.path.exists(statusfile):
            break
        await asyncio.sleep(3)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as upread:
            txt = upread.read()
        try:
            link_line = f"\n{link}" if link else ""
            await client.edit_message_text(chat, message.id, f"**Uploading:** **{txt}**{link_line}")
            await asyncio.sleep(10)
        except:
            await asyncio.sleep(5)


# progress writer
def progress(current, total, message, type):
    with open(f"{message.id}{type}status.txt", "w") as fileup:
        fileup.write(f"{current * 100 / total:.1f}%")


def build_msg_link(chatid, msgid, toID=None):
    """Build a Telegram message link, optionally showing the full batch range."""
    if chatid:
        clean_id = str(chatid).replace("-100", "")
        if toID and toID != msgid:
            return f"https://t.me/c/{clean_id}/{msgid}-{toID}"
        return f"https://t.me/c/{clean_id}/{msgid}"
    return ""


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
            "Send me a Telegram post link (for example: https://t.me/somechannel/123) and I'll try to fetch it for you.</b>"
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


# speedtest command
@Client.on_message(filters.command(["speedtest"]))
async def speedtest_cmd(client: Client, message: Message):
    size_mb = 5
    size_bytes = size_mb * 1024 * 1024
    test_file = f"speedtest_{message.from_user.id}.bin"

    status_msg = await message.reply("**🚀 Speed Test Starting...**\n\nGenerating test file...")

    try:
        with open(test_file, "wb") as f:
            f.write(os.urandom(size_bytes))

        # Upload test
        await status_msg.edit("**🚀 Running Speed Test...**\n\n📤 Testing upload speed...")
        up_start = time.time()
        sent = await client.send_document(
            message.chat.id,
            test_file,
            caption=f"⚡ Speed test file ({size_mb} MB) — will be deleted automatically",
        )
        up_elapsed = time.time() - up_start
        up_speed = (size_bytes / up_elapsed) / (1024 * 1024)

        # Download test
        await status_msg.edit("**🚀 Running Speed Test...**\n\n📥 Testing download speed...")
        down_start = time.time()
        downloaded = await client.download_media(sent)
        down_elapsed = time.time() - down_start
        down_speed = (size_bytes / down_elapsed) / (1024 * 1024)

        # Cleanup the sent file message
        try:
            await sent.delete()
        except:
            pass
        if downloaded and os.path.exists(downloaded):
            try:
                os.remove(downloaded)
            except:
                pass

        result = (
            f"**🚀 Speed Test Results**\n\n"
            f"📁 **File Size:** {size_mb} MB\n\n"
            f"📤 **Upload Speed:** `{up_speed:.2f} MB/s`\n"
            f"   ⏱ Time taken: `{up_elapsed:.2f}s`\n\n"
            f"📥 **Download Speed:** `{down_speed:.2f} MB/s`\n"
            f"   ⏱ Time taken: `{down_elapsed:.2f}s`"
        )
        await status_msg.edit(result)

    except Exception as e:
        await status_msg.edit(f"**❌ Speed test failed:** `{e}`")
    finally:
        if os.path.exists(test_file):
            try:
                os.remove(test_file)
            except:
                pass


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
        
        batch_progress = await db.get_batch_progress(message.from_user.id)
        start_from = fromID
        
        if batch_progress and batch_progress.get('chat_id') == str(chatid):
            last_processed = batch_progress.get('last_processed', fromID - 1)
            if last_processed >= fromID and last_processed < toID:
                start_from = last_processed + 1
                await message.reply(f"**Resuming batch from message {start_from} ({toID - start_from + 1} remaining)...**")
        
        if start_from == fromID:
            await message.reply(f"**Starting batch download of {total_messages} message(s)...**")
        
        acc = None
        
        if LOGIN_SYSTEM == True:
            user_data = await db.get_session(message.from_user.id)
            if user_data is None:
                await message.reply("**For Downloading Restricted Content You Have To /login First.**")
                batch_temp.IS_BATCH[message.from_user.id] = True
                return
            try:
                acc = Client(f"saverestricted_{message.from_user.id}", session_string=user_data, api_hash=API_HASH, api_id=API_ID)
                await acc.start()
            except (pyrogram.errors.AuthKeyUnregistered, pyrogram.errors.AuthKeyInvalid, pyrogram.errors.SessionRevoked):
                batch_temp.IS_BATCH[message.from_user.id] = True
                await db.clear_batch_progress(message.from_user.id)
                return await message.reply("**Your Login Session Expired. So /logout First Then Login Again By - /login**")
            except Exception as e:
                batch_temp.IS_BATCH[message.from_user.id] = True
                await db.clear_batch_progress(message.from_user.id)
                return await message.reply(f"**Unable to connect. Please try /logout and /login again.**\n`{e}`")
        else:
            if TechVJUser is None:
                batch_temp.IS_BATCH[message.from_user.id] = True
                await client.send_message(message.chat.id, f"**String Session is not Set**", reply_to_message_id=message.id)
                return
            acc = TechVJUser
        
        processed_count = 0
        success_count = 0
        
        try:
            for msgid in range(start_from, toID + 1):
                if batch_temp.IS_BATCH.get(message.from_user.id):
                    await db.clear_batch_progress(message.from_user.id)
                    break
                
                processed_count += 1

                # Save progress every 10 messages
                if processed_count % 10 == 0:
                    await db.save_batch_progress(message.from_user.id, str(chatid), msgid - 1, total_messages)
                
                # private (/c/)
                if "https://t.me/c/" in message.text:
                    if is_supergroup and topic_id is not None and chatid is not None:
                        try:
                            await retry_on_error(handle_private_supergroup, client, acc, message, chatid, topic_id, msgid, toID)
                            success_count += 1
                        except (pyrogram.errors.AuthKeyUnregistered, pyrogram.errors.AuthKeyInvalid, pyrogram.errors.SessionRevoked):
                            await db.save_batch_progress(message.from_user.id, str(chatid), msgid - 1, total_messages)
                            await message.reply(f"**❌ Session expired. Progress saved at message {msgid - 1}. Please /logout and /login again, then resend the batch link to resume.**")
                            batch_temp.IS_BATCH[message.from_user.id] = True
                            break
                        except Exception as e:
                            if ERROR_MESSAGE:
                                await client.send_message(message.chat.id, f"Error processing message {msgid}: {e}", reply_to_message_id=message.id)
                            continue
                    else:
                        try:
                            if chatid is None:
                                chatid = int("-100" + datas[4])
                        except Exception:
                            await client.send_message(message.chat.id, "**Unable to parse private chat link**", reply_to_message_id=message.id)
                            continue
                        try:
                            await retry_on_error(handle_private, client, acc, message, chatid, msgid, toID)
                            success_count += 1
                        except (pyrogram.errors.AuthKeyUnregistered, pyrogram.errors.AuthKeyInvalid, pyrogram.errors.SessionRevoked):
                            await db.save_batch_progress(message.from_user.id, str(chatid), msgid - 1, total_messages)
                            await message.reply(f"**❌ Session expired. Progress saved at message {msgid - 1}. Please /logout and /login again, then resend the batch link to resume.**")
                            batch_temp.IS_BATCH[message.from_user.id] = True
                            break
                        except Exception as e:
                            if ERROR_MESSAGE:
                                await client.send_message(message.chat.id, f"Error processing message {msgid}: {e}", reply_to_message_id=message.id)
                            continue

                # bot (/b/)
                elif "https://t.me/b/" in message.text:
                    username = datas[4]
                    try:
                        await retry_on_error(handle_private, client, acc, message, username, msgid, toID)
                        success_count += 1
                    except (pyrogram.errors.AuthKeyUnregistered, pyrogram.errors.AuthKeyInvalid, pyrogram.errors.SessionRevoked):
                        await db.save_batch_progress(message.from_user.id, str(chatid), msgid - 1, total_messages)
                        await message.reply(f"**❌ Session expired. Progress saved at message {msgid - 1}. Please /logout and /login again, then resend the batch link to resume.**")
                        batch_temp.IS_BATCH[message.from_user.id] = True
                        break
                    except Exception as e:
                        if ERROR_MESSAGE:
                            await client.send_message(message.chat.id, f"Error processing message {msgid}: {e}", reply_to_message_id=message.id)
                        continue

                # public
                else:
                    username = datas[3]
                    try:
                        msg = await retry_on_error(client.get_messages, username, msgid)
                    except UsernameNotOccupied:
                        await client.send_message(message.chat.id, "The username is not occupied by anyone", reply_to_message_id=message.id)
                        continue
                    except Exception as e:
                        if ERROR_MESSAGE:
                            await client.send_message(message.chat.id, f"Error getting message {msgid}: {e}", reply_to_message_id=message.id)
                        continue
                    try:
                        await retry_on_error(client.copy_message, message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                        success_count += 1
                    except Exception:
                        try:
                            await retry_on_error(handle_private, client, acc, message, username, msgid, toID)
                            success_count += 1
                        except (pyrogram.errors.AuthKeyUnregistered, pyrogram.errors.AuthKeyInvalid, pyrogram.errors.SessionRevoked):
                            await db.save_batch_progress(message.from_user.id, str(chatid if chatid else username), msgid - 1, total_messages)
                            await message.reply(f"**❌ Session expired. Progress saved at message {msgid - 1}. Please /logout and /login again, then resend the batch link to resume.**")
                            batch_temp.IS_BATCH[message.from_user.id] = True
                            break
                        except Exception as e:
                            if ERROR_MESSAGE:
                                await client.send_message(message.chat.id, f"Error processing message {msgid}: {e}", reply_to_message_id=message.id)
                            continue

        except Exception as batch_error:
            print(f"Batch processing error: {batch_error}")
            if ERROR_MESSAGE:
                await message.reply(f"**⚠️ Batch processing encountered an error:** `{str(batch_error)}`")
        finally:
            if LOGIN_SYSTEM and acc and hasattr(acc, 'stop'):
                try:
                    await acc.stop()
                except:
                    pass
            
            batch_temp.IS_BATCH[message.from_user.id] = True
            await db.clear_batch_progress(message.from_user.id)
            
            if processed_count > 0:
                failed_count = processed_count - success_count
                await message.reply(f"**✅ Batch download completed!**\n\n**Processed:** {processed_count}/{total_messages}\n**Success:** {success_count}\n**Failed/Skipped:** {failed_count}")


# handle private supergroup with topic/sub-group filtering
async def handle_private_supergroup(client: Client, acc, message: Message, chatid: int, topic_id: int, msgid: int, toID: int = None):
    try:
        msg: Message = await retry_on_error(acc.get_messages, chatid, msgid)
        
        if not msg or msg.empty:
            return
        
        if hasattr(msg, 'reply_to_message_id') and msg.reply_to_message_id:
            reply_msg = await retry_on_error(acc.get_messages, chatid, msg.reply_to_message_id)
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
        
        await handle_private(client, acc, message, chatid, msgid, toID)
        
    except (pyrogram.errors.AuthKeyUnregistered, pyrogram.errors.AuthKeyInvalid, pyrogram.errors.SessionRevoked):
        raise
    except Exception as e:
        if ERROR_MESSAGE:
            await client.send_message(message.chat.id, f"Error in supergroup handler: {e}", reply_to_message_id=message.id)


# handle private
async def handle_private(client: Client, acc, message: Message, chatid, msgid: int, toID: int = None):
    os.makedirs("downloads", exist_ok=True)

    msg: Message = await retry_on_error(acc.get_messages, chatid, msgid)
    if not msg or msg.empty:
        return
    msg_type = get_message_type(msg)
    if not msg_type:
        return
    
    user_settings = await db.get_user_settings(message.from_user.id)
    
    if not should_process_message(msg_type, user_settings):
        return
    
    chat = message.chat.id
    destination_chat = user_settings.get('destination_channel') or chat
    
    if batch_temp.IS_BATCH.get(message.from_user.id):
        return

    # Build message link for status display
    msg_link = build_msg_link(chatid, msgid, toID) if isinstance(chatid, int) else ""

    if msg_type == "Text":
        try:
            text_to_send = msg.text
            entities_to_send = msg.entities
            
            if user_settings.get('caption_cleanup') and any(user_settings['caption_cleanup'].values()):
                text_to_send = clean_caption(msg.text, user_settings) if msg.text else msg.text
                entities_to_send = None
            
            await retry_on_error(client.send_message, destination_chat, text_to_send, entities=entities_to_send, parse_mode=enums.ParseMode.HTML)
            if destination_chat != chat:
                await message.reply("✅ Sent to destination channel!")
            return
        except Exception as e:
            if ERROR_MESSAGE:
                error_msg = format_send_error(e, destination_chat)
                await client.send_message(message.chat.id, error_msg, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
            return

    smsg = await client.send_message(message.chat.id, "**Downloading**", reply_to_message_id=message.id)
    asyncio.create_task(downstatus(client, f"{message.id}downstatus.txt", smsg, chat, msg_link))
    
    file = None
    try:
        file = await retry_on_error(acc.download_media, msg, progress=progress, progress_args=[message, "down"])
    except Exception as e:
        print(f"Download failed for message {msgid}: {e}")
    finally:
        if os.path.exists(f"{message.id}downstatus.txt"):
            os.remove(f"{message.id}downstatus.txt")

    if not file or not os.path.exists(file) or os.path.getsize(file) == 0:
        if file and os.path.exists(file):
            try:
                os.remove(file)
            except:
                pass
        await smsg.delete()
        return

    if batch_temp.IS_BATCH.get(message.from_user.id):
        if file and os.path.exists(file):
            try:
                os.remove(file)
            except:
                pass
        return

    asyncio.create_task(upstatus(client, f"{message.id}upstatus.txt", smsg, chat, msg_link))

    caption = msg.caption if msg.caption else None
    caption_entities = None
    caption_was_cleaned = False
    
    if caption:
        cleaned_caption = clean_caption(caption, user_settings)
        if cleaned_caption != caption:
            caption_was_cleaned = True
        caption = cleaned_caption

    if batch_temp.IS_BATCH.get(message.from_user.id):
        return
    
    if not file or not os.path.exists(file):
        if ERROR_MESSAGE:
            await client.send_message(message.chat.id, f"**Upload failed:** File path is invalid or file was deleted", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        await smsg.delete()
        return
    
    if os.path.getsize(file) == 0:
        if ERROR_MESSAGE:
            await client.send_message(message.chat.id, "**Upload failed:** File size is 0 bytes - cannot upload empty file", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        try:
            os.remove(file)
        except:
            pass
        await smsg.delete()
        return

    # Document
    if msg_type == "Document":
        ph_path = None
        try:
            if msg.document.thumbs:
                ph_path = await retry_on_error(acc.download_media, msg.document.thumbs[0].file_id)
        except Exception:
            ph_path = None

        try:
            await retry_on_error(
                client.send_document,
                destination_chat,
                file,
                thumb=ph_path,
                caption=caption,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
            if destination_chat != chat:
                await message.reply("✅ Sent to destination channel!")
        except Exception as e:
            if ERROR_MESSAGE:
                error_msg = format_send_error(e, destination_chat)
                await client.send_message(message.chat.id, error_msg, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
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
                ph_path = await retry_on_error(acc.download_media, msg.video.thumbs[0].file_id)
        except Exception:
            ph_path = None

        try:
            await retry_on_error(
                client.send_video,
                destination_chat,
                file,
                duration=getattr(msg.video, "duration", None),
                width=getattr(msg.video, "width", None),
                height=getattr(msg.video, "height", None),
                thumb=ph_path,
                caption=caption,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
            if destination_chat != chat:
                await message.reply("✅ Sent to destination channel!")
        except Exception as e:
            if ERROR_MESSAGE:
                error_msg = format_send_error(e, destination_chat)
                await client.send_message(message.chat.id, error_msg, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        if ph_path:
            try:
                os.remove(ph_path)
            except:
                pass

    # Animation (gif)
    elif msg_type == "Animation":
        try:
            await retry_on_error(client.send_animation, destination_chat, file, caption=caption, parse_mode=enums.ParseMode.HTML)
            if destination_chat != chat:
                await message.reply("✅ Sent to destination channel!")
        except Exception as e:
            if ERROR_MESSAGE:
                error_msg = format_send_error(e, destination_chat)
                await client.send_message(message.chat.id, error_msg, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)

    # Sticker
    elif msg_type == "Sticker":
        try:
            await retry_on_error(client.send_sticker, destination_chat, file)
            if destination_chat != chat:
                await message.reply("✅ Sent to destination channel!")
        except Exception as e:
            if ERROR_MESSAGE:
                error_msg = format_send_error(e, destination_chat)
                await client.send_message(message.chat.id, error_msg, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)

    # Voice
    elif msg_type == "Voice":
        try:
            voice_entities = None if caption_was_cleaned else getattr(msg, "caption_entities", None)
            await retry_on_error(
                client.send_voice,
                destination_chat,
                file,
                caption=caption,
                caption_entities=voice_entities,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
            if destination_chat != chat:
                await message.reply("✅ Sent to destination channel!")
        except Exception as e:
            if ERROR_MESSAGE:
                error_msg = format_send_error(e, destination_chat)
                await client.send_message(message.chat.id, error_msg, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)

    # Audio
    elif msg_type == "Audio":
        ph_path = None
        try:
            if getattr(msg.audio, "thumbs", None):
                ph_path = await retry_on_error(acc.download_media, msg.audio.thumbs[0].file_id)
        except Exception:
            ph_path = None

        try:
            await retry_on_error(
                client.send_audio,
                destination_chat,
                file,
                thumb=ph_path,
                caption=caption,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
            if destination_chat != chat:
                await message.reply("✅ Sent to destination channel!")
        except Exception as e:
            if ERROR_MESSAGE:
                error_msg = format_send_error(e, destination_chat)
                await client.send_message(message.chat.id, error_msg, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        if ph_path:
            try:
                os.remove(ph_path)
            except:
                pass

    # Photo
    elif msg_type == "Photo":
        try:
            await retry_on_error(client.send_photo, destination_chat, file, caption=caption, parse_mode=enums.ParseMode.HTML)
            if destination_chat != chat:
                await message.reply("✅ Sent to destination channel!")
        except Exception as e:
            if ERROR_MESSAGE:
                error_msg = format_send_error(e, destination_chat)
                await client.send_message(message.chat.id, error_msg, reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)

    # cleanup
    try:
        if os.path.exists(f"{message.id}upstatus.txt"):
            os.remove(f"{message.id}upstatus.txt")
        if file and os.path.exists(file):
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


# check if message type matches filter
def should_process_message(msg_type: str, settings: dict) -> bool:
    if not msg_type:
        return False
    
    file_filter = settings.get('file_type_filter', 'all')
    
    if file_filter == 'all':
        return True
    
    msg_type_lower = msg_type.lower()
    
    if file_filter == 'video' and msg_type_lower in ['video', 'animation']:
        return True
    elif file_filter == 'document' and msg_type_lower == 'document':
        return True
    elif file_filter == 'photo' and msg_type_lower == 'photo':
        return True
    elif file_filter == 'audio' and msg_type_lower in ['audio', 'voice']:
        return True
    elif file_filter == 'text' and msg_type_lower == 'text':
        return True
    
    return False
