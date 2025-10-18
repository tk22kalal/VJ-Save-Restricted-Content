import os
import asyncio
import time
import random
from pyrogram import Client, enums
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChannelPrivate, UserNotParticipant, ChatWriteForbidden, PeerIdInvalid
from database.db import db
from TechVJ.settings import clean_caption, clean_filename

class OptimizedBatchProcessor:
    def __init__(self):
        self.download_speeds = []
        self.upload_speeds = []
    
    async def process_message_fast(self, client: Client, acc, user_message: Message, chatid: int, msgid: int, user_settings: dict, destination_chat: int):
        try:
            # Get message - no topic filtering to save time
            msg = await acc.get_messages(chatid, msgid)
            if not msg or msg.empty:
                return "skipped", "Empty message", "unknown", 0, 0
            
            # Quick message type detection
            msg_type = self.get_message_type_fast(msg)
            if not msg_type:
                return "skipped", "Unknown type", "unknown", 0, 0
            
            # Quick filter check
            file_filter = user_settings.get('file_type_filter', 'all')
            if file_filter != 'all' and not self.matches_filter(msg_type, file_filter):
                return "filtered", f"Filtered ({msg_type})", msg_type.lower(), 0, 0
            
            # Handle text messages quickly
            if msg_type == "Text":
                try:
                    cleaned_text = clean_caption(msg.text, user_settings) if msg.text else msg.text
                    await client.send_message(
                        destination_chat,
                        cleaned_text or msg.text,
                        entities=msg.entities,
                        parse_mode=enums.ParseMode.HTML
                    )
                    return "success", "Text sent", "text", 0, 0
                except Exception as e:
                    return "error", f"Text failed: {str(e)}", "text", 0, 0
            
            # Download file with minimal overhead
            start_time = time.time()
            try:
                file = await acc.download_media(msg)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                file = await acc.download_media(msg)
            except Exception as e:
                return "error", f"Download failed: {str(e)}", msg_type.lower(), 0, 0
            
            if not file or not os.path.exists(file):
                return "error", "File not found", msg_type.lower(), 0, 0
            
            download_time = time.time() - start_time
            file_size = os.path.getsize(file)
            download_speed = file_size / download_time if download_time > 0 else 0
            
            # Clean caption quickly
            caption = clean_caption(msg.caption, user_settings) if msg.caption else None
            
            # Upload file
            start_time = time.time()
            upload_result = await self.upload_media_fast(client, destination_chat, file, msg_type, caption)
            upload_time = time.time() - start_time
            upload_speed = file_size / upload_time if upload_time > 0 else 0
            
            # Quick cleanup
            if os.path.exists(file):
                os.remove(file)
            
            if not upload_result:
                return "error", "Upload failed", msg_type.lower(), download_speed, upload_speed
            
            return "success", "Done", msg_type.lower(), download_speed, upload_speed
            
        except FloodWait as e:
            await asyncio.sleep(e.value)
            return await self.process_message_fast(client, acc, user_message, chatid, msgid, user_settings, destination_chat)
        except Exception as e:
            return "error", f"Unexpected: {str(e)}", "unknown", 0, 0
    
    async def upload_media_fast(self, client: Client, chat_id: int, file: str, msg_type: str, caption: str):
        """Fast upload without thumbnails or progress tracking"""
        try:
            if msg_type == "Document":
                await client.send_document(chat_id, file, caption=caption, parse_mode=enums.ParseMode.HTML)
            elif msg_type == "Video":
                await client.send_video(chat_id, file, caption=caption, parse_mode=enums.ParseMode.HTML)
            elif msg_type == "Animation":
                await client.send_animation(chat_id, file, caption=caption, parse_mode=enums.ParseMode.HTML)
            elif msg_type == "Sticker":
                await client.send_sticker(chat_id, file)
            elif msg_type == "Voice":
                await client.send_voice(chat_id, file, caption=caption, parse_mode=enums.ParseMode.HTML)
            elif msg_type == "Audio":
                await client.send_audio(chat_id, file, caption=caption, parse_mode=enums.ParseMode.HTML)
            elif msg_type == "Photo":
                await client.send_photo(chat_id, file, caption=caption, parse_mode=enums.ParseMode.HTML)
            else:
                return False
            return True
        except Exception:
            return False
    
    def get_message_type_fast(self, msg):
        """Fast message type detection"""
        if getattr(msg, "document", None):
            return "Document"
        elif getattr(msg, "video", None):
            return "Video"
        elif getattr(msg, "animation", None):
            return "Animation"
        elif getattr(msg, "sticker", None):
            return "Sticker"
        elif getattr(msg, "voice", None):
            return "Voice"
        elif getattr(msg, "audio", None):
            return "Audio"
        elif getattr(msg, "photo", None):
            return "Photo"
        elif getattr(msg, "text", None):
            return "Text"
        return None
    
    def matches_filter(self, msg_type: str, filter_type: str) -> bool:
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
    
    def format_speed(self, bytes_per_second: float) -> str:
        if bytes_per_second < 1024:
            return f"{bytes_per_second:.1f} B/s"
        elif bytes_per_second < 1024 * 1024:
            return f"{bytes_per_second / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_second / (1024 * 1024):.1f} MB/s"
    
    async def get_user_destination(self, user_id: int, user_message: Message):
        """Get user's upload destination quickly"""
        try:
            user_dest = await db.get_user_destination(user_id)
            if user_dest and user_dest.get('destination'):
                destination_chat = user_dest['destination']
                # Quick access test
                try:
                    await user_message._client.get_chat(destination_chat)
                    return destination_chat
                except:
                    return user_message.chat.id
            return user_message.chat.id
        except:
            return user_message.chat.id
    
    async def batch_process_fast(self, client: Client, acc, user_message: Message, 
                                chatid: int, from_id: int, to_id: int, 
                                user_settings: dict, max_concurrent: int = 2):  # Reduced concurrency
        total_messages = to_id - from_id + 1
        processed = successful = failed = filtered = 0
        file_types_count = {'video': 0, 'document': 0, 'photo': 0, 'audio': 0, 'text': 0, 'other': 0}
        self.download_speeds = []
        self.upload_speeds = []
        
        # Get destination quickly
        destination_chat = await self.get_user_destination(user_message.from_user.id, user_message)
        
        # Quick destination info
        try:
            if destination_chat == user_message.chat.id:
                destination_info = "Your chat"
            else:
                dest_chat = await client.get_chat(destination_chat)
                destination_info = f"@{dest_chat.username}" if dest_chat.username else f"{dest_chat.title}"
        except:
            destination_info = "Your chat"
        
        # MINIMAL TESTING - just check if we can access the first message
        test_msg = await user_message.reply("🚀 Starting batch process...")
        try:
            first_msg = await acc.get_messages(chatid, from_id)
            if not first_msg:
                await test_msg.edit_text("❌ Cannot access first message")
                return
        except Exception as e:
            await test_msg.edit_text(f"❌ Access failed: {str(e)}")
            return
        
        progress_msg = test_msg
        
        start_time = time.time()
        last_update = start_time
        
        # Use limited concurrency to avoid FloodWait
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single(msgid):
            nonlocal processed, successful, failed, filtered, last_update
            
            async with semaphore:
                # Add small random delay to avoid hitting rate limits
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                result, info, msg_type, dl_speed, ul_speed = await self.process_message_fast(
                    client, acc, user_message, chatid, msgid, user_settings, destination_chat
                )
                
                if dl_speed > 0:
                    self.download_speeds.append(dl_speed)
                if ul_speed > 0:
                    self.upload_speeds.append(ul_speed)
                
                processed += 1
                
                if result == "success":
                    successful += 1
                    if msg_type in ['video', 'animation']:
                        file_types_count['video'] += 1
                    elif msg_type == 'document':
                        file_types_count['document'] += 1
                    elif msg_type == 'photo':
                        file_types_count['photo'] += 1
                    elif msg_type in ['audio', 'voice']:
                        file_types_count['audio'] += 1
                    elif msg_type == 'text':
                        file_types_count['text'] += 1
                    else:
                        file_types_count['other'] += 1
                elif result == "error":
                    failed += 1
                elif result == "filtered":
                    filtered += 1
                
                # Update progress every 3 seconds or when complete
                current_time = time.time()
                if current_time - last_update >= 3 or processed == total_messages:
                    elapsed = current_time - start_time
                    speed = processed / elapsed if elapsed > 0 else 0
                    eta = (total_messages - processed) / speed if speed > 0 else 0
                    percentage = (processed / total_messages * 100)
                    
                    progress_text = (
                        f"🔄 **Processing** {processed}/{total_messages} ({percentage:.1f}%)\n"
                        f"✅ **{successful}** | ❌ **{failed}** | 🔍 **{filtered}**\n"
                        f"⚡ **{speed:.1f} msg/s** | ⏱ **{int(eta)}s** left\n"
                        f"📍 **{destination_info}**"
                    )
                    
                    try:
                        await progress_msg.edit_text(progress_text)
                    except:
                        pass
                    
                    last_update = current_time
        
        # Process messages sequentially at first, then increase concurrency
        tasks = []
        for i, msgid in enumerate(range(from_id, to_id + 1)):
            tasks.append(process_single(msgid))
            
            # Start with lower concurrency, then increase
            if i < 10:  # First 10 messages process more slowly
                if len(tasks) >= 1:  # Very low concurrency at start
                    await asyncio.gather(*tasks)
                    tasks = []
            else:
                if len(tasks) >= max_concurrent:
                    await asyncio.gather(*tasks)
                    tasks = []
        
        # Process any remaining tasks
        if tasks:
            await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Final report
        final_message = (
            f"✅ **Batch Complete!**\n\n"
            f"📊 **Total:** {total_messages}\n"
            f"✅ **Success:** {successful} | ❌ **Failed:** {failed} | 🔍 **Filtered:** {filtered}\n"
            f"⏱ **Time:** {int(total_time)}s | ⚡ **Speed:** {total_messages/total_time:.2f} msg/s\n"
            f"📍 **Destination:** {destination_info}"
        )
        
        if successful > 0:
            files_summary = []
            if file_types_count['video'] > 0:
                files_summary.append(f"🎬 {file_types_count['video']}v")
            if file_types_count['document'] > 0:
                files_summary.append(f"📄 {file_types_count['document']}d")
            if file_types_count['photo'] > 0:
                files_summary.append(f"🖼 {file_types_count['photo']}p")
            if file_types_count['audio'] > 0:
                files_summary.append(f"🎵 {file_types_count['audio']}a")
            if file_types_count['text'] > 0:
                files_summary.append(f"📝 {file_types_count['text']}t")
            
            if files_summary:
                final_message += f"\n📁 **Files:** {', '.join(files_summary)}"
        
        await progress_msg.edit_text(final_message)

batch_processor = OptimizedBatchProcessor()
