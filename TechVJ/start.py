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
    PeerIdInvalid,
    ChannelPrivate,
    ChatWriteForbidden,
)
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import API_ID, API_HASH, ERROR_MESSAGE, LOGIN_SYSTEM, STRING_SESSION
from database.db import db
from TechVJ.strings import HELP_TXT
from TechVJ.settings import clean_caption, clean_filename
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


# Get user's upload destination
async def get_user_destination(client: Client, user_id: int, user_message: Message):
    """Get user's upload destination from database"""
    try:
        user_dest = await db.get_user_destination(user_id)
        if user_dest and user_dest.get('destination'):
            destination_chat = user_dest['destination']
            
            # Verify the bot has access to the destination
            try:
                await client.get_chat(destination_chat)
                return destination_chat
            except (PeerIdInvalid, ChannelPrivate, ChatWriteForbidden):
                # Fallback to user's chat if destination is invalid
                await user_message.reply("⚠️ Cannot access your configured destination channel. Using your chat instead.")
                return user_message.chat.id
        else:
            # No destination configured, use user's chat
            return user_message.chat.id
    except Exception:
        # Fallback to user's chat in case of any error
        return user_message.chat.id


# Get user settings
async def get_user_settings(user_id: int):
    """Get user settings from database"""
    try:
        settings = await db.get_user_settings(user_id)
        if not settings:
            # Default settings
            settings = {
                'file_type_filter': 'all',
                'caption_position': 'bottom',
                'remove_words': [],
                'custom_caption': None,
                'replace_words': {}
            }
        return settings
    except Exception:
        return {
            'file_type_filter': 'all',
            'caption_position': 'bottom',
            'remove_words': [],
            'custom_caption': None,
            'replace_words': {}
        }


# Check if message matches filter
def matches_filter(msg_type: str, filter_type: str) -> bool:
    if filter_type == 'all':
        return True
    elif filter_type == 'video':
        return msg_type in ['Video', 'Animation']
    elif filter_type == 'document':
        return msg_type == 'Document'
    elif filter_type == 'text':
        return msg_type == 'Text'
    elif filter_type == 'photo':
        return msg_type == 'Photo'
    elif filter_type == 'audio':
        return msg_type in ['Audio', 'Voice']
    return False


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
        
        # Get user settings
        user_settings = await get_user_settings(message.from_user.id)
        
        # Get destination
        destination_chat = await get_user_destination(client, message.from_user.id, message)
        
        # Get destination info for display
        try:
            if destination_chat == message.chat.id:
                destination_info = "Your chat"
            else:
                dest_chat = await client.get_chat(destination_chat)
                destination_info = f"@{dest_chat.username}" if dest_chat.username else f"{dest_chat.title}"
        except:
            destination_info = "Your chat"
        
        total_messages = toID - fromID + 1
        processed = 0
        successful = 0
        failed = 0
        filtered = 0
        
        file_filter = user_settings.get('file_type_filter', 'all').title()
        
        progress_msg = await message.reply(
            f"🚀 **Starting Batch Process**\n\n"
            f"📊 Total: **{total_messages}** messages\n"
            f"📍 Destination: **{destination_info}**\n"
            f"🎞 Filter: **{file_filter}**\n\n"
            f"Processing: **0/{total_messages}**"
        )
        
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

            # Process message with settings
            result = None
            
            # private (/c/)
            if "https://t.me/c/" in message.text:
                if is_supergroup and topic_id is not None and chatid is not None:
                    try:
                        result = await handle_private_supergroup(client, acc, message, chatid, topic_id, msgid, user_settings, destination_chat)
                    except Exception as e:
                        if ERROR_MESSAGE:
                            await client.send_message(message.chat.id, f"Error processing supergroup message {msgid}: {e}", reply_to_message_id=message.id)
                        result = "error"
                else:
                    try:
                        if chatid is None:
                            chatid = int("-100" + datas[4])
                    except Exception:
                        await client.send_message(message.chat.id, "**Unable to parse private chat link**", reply_to_message_id=message.id)
                        return
                    try:
                        result = await handle_private(client, acc, message, chatid, msgid, user_settings, destination_chat)
                    except Exception as e:
                        if ERROR_MESSAGE:
                            await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)
                        result = "error"

            # bot (/b/)
            elif "https://t.me/b/" in message.text:
                try:
                    username = datas[4]
                    result = await handle_private(client, acc, message, username, msgid, user_settings, destination_chat)
                except Exception as e:
                    if ERROR_MESSAGE:
                        await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)
                    result = "error"

            # public
            else:
                username = datas[3]
                try:
                    msg = await client.get_messages(username, msgid)
                except UsernameNotOccupied:
                    await client.send_message(message.chat.id, "The username is not occupied by anyone", reply_to_message_id=message.id)
                    return
                try:
                    result = await handle_public(client, acc, message, username, msgid, user_settings, destination_chat)
                except Exception as e:
                    if ERROR_MESSAGE:
                        await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)
                    result = "error"
            
            # Update counters
            processed += 1
            if result == "success":
                successful += 1
            elif result == "filtered":
                filtered += 1
            elif result == "error":
                failed += 1
            
            # Update progress every 3 messages or at end
            if processed % 3 == 0 or processed == total_messages:
                percentage = (processed / total_messages * 100) if total_messages > 0 else 0
                await progress_msg.edit_text(
                    f"🚀 **Batch Processing** ({percentage:.1f}%)\n\n"
                    f"📊 **{processed}/{total_messages}** processed\n"
                    f"✅ Success: **{successful}** | ❌ Failed: **{failed}** | 🔍 Filtered: **{filtered}**\n\n"
                    f"📍 Destination: **{destination_info}**"
                )

            # wait time between iterations
            await asyncio.sleep(3)

        batch_temp.IS_BATCH[message.from_user.id] = True
        
        # Final summary
        await progress_msg.edit_text(
            f"✅ **Batch Complete!**\n\n"
            f"📊 Total: {total_messages} | ✅ Success: **{successful}** | ❌ Failed: **{failed}** | 🔍 Filtered: **{filtered}**\n\n"
            f"📍 Destination: **{destination_info}**"
        )


# handle public messages with settings
async def handle_public(client: Client, acc, message: Message, username: str, msgid: int, user_settings: dict, destination_chat: int):
    try:
        msg = await client.get_messages(username, msgid)
        if not msg or msg.empty:
            return "error"
        
        msg_type = get_message_type(msg)
        if not msg_type:
            return "error"
        
        # Apply file type filter
        file_filter = user_settings.get('file_type_filter', 'all')
        if file_filter != 'all' and not matches_filter(msg_type, file_filter):
            return "filtered"
        
        # Use destination chat
        chat_id = destination_chat
        reply_to_id = message.id if chat_id == message.chat.id else None
        
        # Handle text messages
        if msg_type == "Text":
            cleaned_text = clean_caption(msg.text, user_settings) if msg.text else msg.text
            try:
                await client.send_message(
                    chat_id,
                    cleaned_text or msg.text,
                    entities=msg.entities,
                    reply_to_message_id=reply_to_id,
                    parse_mode=enums.ParseMode.HTML
                )
                return "success"
            except Exception:
                return "error"
        
        # Try copy_message for public content
        try:
            await client.copy_message(chat_id, msg.chat.id, msg.id, reply_to_message_id=reply_to_id)
            return "success"
        except Exception:
            # Fallback to handle_private if copy fails
            return await handle_private(client, acc, message, username, msgid, user_settings, destination_chat)
    except Exception:
        return "error"


# handle private supergroup with topic/sub-group filtering
async def handle_private_supergroup(client: Client, acc, message: Message, chatid: int, topic_id: int, msgid: int, user_settings: dict, destination_chat: int):
    try:
        msg: Message = await acc.get_messages(chatid, msgid)
        
        if not msg or msg.empty:
            return "error"
        
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
        
        # Filter by topic
        if msg_topic_id != topic_id:
            return "filtered"
        
        return await handle_private(client, acc, message, chatid, msgid, user_settings, destination_chat)
        
    except Exception as e:
        if ERROR_MESSAGE:
            await client.send_message(message.chat.id, f"Error in supergroup handler: {e}", reply_to_message_id=message.id)
        return "error"


# handle private with settings
async def handle_private(client: Client, acc, message: Message, chatid: int, msgid: int, user_settings: dict, destination_chat: int):
    msg: Message = await acc.get_messages(chatid, msgid)
    if not msg or msg.empty:
        return "error"
    
    msg_type = get_message_type(msg)
    if not msg_type:
        return "error"
    
    # Apply file type filter
    file_filter = user_settings.get('file_type_filter', 'all')
    if file_filter != 'all' and not matches_filter(msg_type, file_filter):
        return "filtered"
    
    # Use destination chat
    chat = destination_chat
    reply_to_id = message.id if chat == message.chat.id else None
    
    if batch_temp.IS_BATCH.get(message.from_user.id):
        return "error"

    if msg_type == "Text":
        cleaned_text = clean_caption(msg.text, user_settings) if msg.text else msg.text
        try:
            await client.send_message(chat, cleaned_text or msg.text, entities=msg.entities, reply_to_message_id=reply_to_id, parse_mode=enums.ParseMode.HTML)
            return "success"
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
            return "error"

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
        return "error"

    if batch_temp.IS_BATCH.get(message.from_user.id):
        return "error"

    asyncio.create_task(upstatus(client, f"{message.id}upstatus.txt", smsg, chat))

    # Clean caption using settings
    caption = msg.caption if msg.caption else None
    if caption:
        caption = clean_caption(caption, user_settings)

    if batch_temp.IS_BATCH.get(message.from_user.id):
        return "error"

    upload_result = "error"

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
                reply_to_message_id=reply_to_id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
            upload_result = "success"
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
                reply_to_message_id=reply_to_id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
            upload_result = "success"
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
            await client.send_animation(chat, file, caption=caption, reply_to_message_id=reply_to_id, parse_mode=enums.ParseMode.HTML)
            upload_result = "success"
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)

    # Sticker
    elif msg_type == "Sticker":
        try:
            await client.send_sticker(chat, file, reply_to_message_id=reply_to_id)
            upload_result = "success"
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
                reply_to_message_id=reply_to_id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
            upload_result = "success"
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
                reply_to_message_id=reply_to_id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress,
                progress_args=[message, "up"],
            )
            upload_result = "success"
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
            await client.send_photo(chat, file, caption=caption, reply_to_message_id=reply_to_id, parse_mode=enums.ParseMode.HTML)
            upload_result = "success"
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
    
    return upload_result


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
