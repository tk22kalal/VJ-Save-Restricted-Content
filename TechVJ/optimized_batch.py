import os
import asyncio
import time
import re
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChannelPrivate, UserNotParticipant, ChatWriteForbidden
from database.db import db
from TechVJ.settings import clean_caption, clean_filename

class OptimizedBatchProcessor:
    def __init__(self):
        self.active_tasks = {}
        self.download_speeds = []
        self.upload_speeds = []
        self.current_file = 0
    
    async def process_message_concurrent(self, client: Client, acc, user_message: Message, chatid: int, msgid: int, user_settings: dict):
        try:
            # Try to get the message first
            try:
                msg = await acc.get_messages(chatid, msgid)
                if not msg or msg.empty:
                    return "error", "Message not found or empty", "unknown", 0, 0
            except ChannelPrivate:
                return "error", "Channel is private - need to join first", "unknown", 0, 0
            except UserNotParticipant:
                return "error", "Not a participant in this chat", "unknown", 0, 0
            except Exception as e:
                return "error", f"Failed to get message: {str(e)}", "unknown", 0, 0
            
            destination = user_settings.get('destination_channel') or user_message.chat.id
            
            msg_type = self.get_message_type(msg)
            if not msg_type:
                return "error", "Unknown message type", "unknown", 0, 0
            
            file_filter = user_settings.get('file_type_filter', 'all')
            if file_filter != 'all' and not self.matches_filter(msg_type, file_filter):
                return "filtered", f"Filtered out ({msg_type})", msg_type.lower(), 0, 0
            
            # Handle text messages
            if msg_type == "Text":
                cleaned_text = clean_caption(msg.text, user_settings) if msg.text else msg.text
                try:
                    await client.send_message(
                        destination,
                        cleaned_text or msg.text,
                        entities=msg.entities
                    )
                    return "success", "Text sent", "text", 0, 0
                except Exception as e:
                    return "error", f"Failed to send text: {str(e)}", "text", 0, 0
            
            # Handle media messages
            start_time = time.time()
            try:
                file = await acc.download_media(msg)
                download_time = time.time() - start_time
                
                if not file or not os.path.exists(file):
                    return "error", "Download failed - file not found", msg_type.lower(), 0, 0
                
                file_size = os.path.getsize(file) if os.path.exists(file) else 0
                download_speed = file_size / download_time if download_time > 0 else 0
                
                caption = msg.caption if msg.caption else None
                if caption:
                    caption = clean_caption(caption, user_settings)
                
                start_time = time.time()
                upload_result, upload_error = await self.upload_media(client, destination, file, msg, msg_type, caption, acc)
                upload_time = time.time() - start_time
                upload_speed = file_size / upload_time if upload_time > 0 else 0
                
                # Cleanup downloaded file
                if os.path.exists(file):
                    os.remove(file)
                
                if upload_result == "error":
                    return "error", f"Upload failed: {upload_error}", msg_type.lower(), download_speed, upload_speed
                
                return "success", f"DL: {self.format_speed(download_speed)}, UL: {self.format_speed(upload_speed)}", msg_type.lower(), download_speed, upload_speed
                
            except Exception as e:
                if os.path.exists(file):
                    os.remove(file)
                return "error", f"Download/Upload error: {str(e)}", msg_type.lower(), 0, 0
            
        except FloodWait as e:
            await asyncio.sleep(e.value)
            return await self.process_message_concurrent(client, acc, user_message, chatid, msgid, user_settings)
        except Exception as e:
            return "error", f"Unexpected error: {str(e)}", "unknown", 0, 0
    
    async def upload_media(self, client: Client, chat_id, file: str, msg, msg_type: str, caption: str, acc):
        try:
            # Verify we can send to destination
            try:
                await client.get_chat(chat_id)
            except Exception as e:
                return "error", f"Cannot access destination: {str(e)}"
            
            if msg_type == "Document":
                ph_path = None
                try:
                    if msg.document and msg.document.thumbs:
                        ph_path = await acc.download_media(msg.document.thumbs[0].file_id)
                except:
                    pass
                
                try:
                    await client.send_document(
                        chat_id,
                        file,
                        thumb=ph_path,
                        caption=caption
                    )
                except ChatWriteForbidden:
                    return "error", "Bot cannot send messages to this chat"
                except Exception as e:
                    return "error", f"Document send failed: {str(e)}"
                
                if ph_path and os.path.exists(ph_path):
                    os.remove(ph_path)
            
            elif msg_type == "Video":
                ph_path = None
                try:
                    if msg.video and msg.video.thumbs:
                        ph_path = await acc.download_media(msg.video.thumbs[0].file_id)
                except:
                    pass
                
                try:
                    await client.send_video(
                        chat_id,
                        file,
                        duration=getattr(msg.video, "duration", None),
                        width=getattr(msg.video, "width", None),
                        height=getattr(msg.video, "height", None),
                        thumb=ph_path,
                        caption=caption
                    )
                except ChatWriteForbidden:
                    return "error", "Bot cannot send messages to this chat"
                except Exception as e:
                    return "error", f"Video send failed: {str(e)}"
                
                if ph_path and os.path.exists(ph_path):
                    os.remove(ph_path)
            
            elif msg_type == "Animation":
                try:
                    await client.send_animation(chat_id, file, caption=caption)
                except ChatWriteForbidden:
                    return "error", "Bot cannot send messages to this chat"
                except Exception as e:
                    return "error", f"Animation send failed: {str(e)}"
            
            elif msg_type == "Sticker":
                try:
                    await client.send_sticker(chat_id, file)
                except ChatWriteForbidden:
                    return "error", "Bot cannot send messages to this chat"
                except Exception as e:
                    return "error", f"Sticker send failed: {str(e)}"
            
            elif msg_type == "Voice":
                try:
                    await client.send_voice(chat_id, file, caption=caption)
                except ChatWriteForbidden:
                    return "error", "Bot cannot send messages to this chat"
                except Exception as e:
                    return "error", f"Voice send failed: {str(e)}"
            
            elif msg_type == "Audio":
                ph_path = None
                try:
                    if msg.audio and getattr(msg.audio, "thumbs", None):
                        ph_path = await acc.download_media(msg.audio.thumbs[0].file_id)
                except:
                    pass
                
                try:
                    await client.send_audio(chat_id, file, thumb=ph_path, caption=caption)
                except ChatWriteForbidden:
                    return "error", "Bot cannot send messages to this chat"
                except Exception as e:
                    return "error", f"Audio send failed: {str(e)}"
                
                if ph_path and os.path.exists(ph_path):
                    os.remove(ph_path)
            
            elif msg_type == "Photo":
                try:
                    await client.send_photo(chat_id, file, caption=caption)
                except ChatWriteForbidden:
                    return "error", "Bot cannot send messages to this chat"
                except Exception as e:
                    return "error", f"Photo send failed: {str(e)}"
            
            return "success", ""
        except Exception as e:
            return "error", str(e)
    
    def get_message_type(self, msg):
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
    
    async def batch_process_with_concurrency(self, client: Client, acc, user_message: Message, 
                                            chatid: int, from_id: int, to_id: int, 
                                            user_settings: dict, max_concurrent: int = 3):
        total_messages = to_id - from_id + 1
        processed = 0
        successful = 0
        failed = 0
        filtered = 0
        file_types_count = {'video': 0, 'document': 0, 'photo': 0, 'audio': 0, 'text': 0, 'other': 0}
        self.download_speeds = []
        self.upload_speeds = []
        
        destination_info = user_settings.get('destination_channel') or "Bot Chat"
        file_filter = user_settings.get('file_type_filter', 'all').title()
        
        # Test account access first
        try:
            test_msg = await acc.get_messages(chatid, from_id)
            if not test_msg or test_msg.empty:
                await user_message.reply("❌ **Cannot access messages with this account.**\n\n"
                                       "Possible reasons:\n"
                                       "• Account needs to join the channel/group\n"
                                       "• Messages are restricted\n"
                                       "• Invalid chat ID")
                return
        except Exception as e:
            await user_message.reply(f"❌ **Account access failed:** {str(e)}\n\n"
                                   "Please ensure your account has access to this chat.")
            return
        
        progress_msg = await user_message.reply(
            f"🚀 **Starting Optimized Batch Process**\n\n"
            f"📊 Total messages: **{total_messages}**\n"
            f"⚡ Concurrent tasks: **{max_concurrent}**\n"
            f"📍 Destination: **{destination_info}**\n"
            f"🎞 File filter: **{file_filter}**\n\n"
            f"Testing access..."
        )
        
        start_time = time.time()
        last_update = start_time
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(msgid):
            nonlocal processed, successful, failed, filtered, last_update
            
            async with semaphore:
                result, info, msg_type, dl_speed, ul_speed = await self.process_message_concurrent(
                    client, acc, user_message, chatid, msgid, user_settings
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
                else:
                    failed += 1
                
                current_time = time.time()
                if current_time - last_update >= 2 or processed == total_messages:
                    elapsed = current_time - start_time
                    speed = processed / elapsed if elapsed > 0 else 0
                    eta = (total_messages - processed) / speed if speed > 0 else 0
                    percentage = (processed / total_messages * 100) if total_messages > 0 else 0
                    
                    avg_dl_speed = sum(self.download_speeds) / len(self.download_speeds) if self.download_speeds else 0
                    avg_ul_speed = sum(self.upload_speeds) / len(self.upload_speeds) if self.upload_speeds else 0
                    
                    progress_bar = self.create_progress_bar(processed, total_messages)
                    
                    # Show last error for debugging
                    last_error = info if result == "error" and processed == total_messages else ""
                    
                    await progress_msg.edit_text(
                        f"🚀 **Batch Processing** ({percentage:.1f}%)\n\n"
                        f"{progress_bar}\n"
                        f"📊 **{processed}/{total_messages}** files processed\n\n"
                        f"✅ Successful: **{successful}**\n"
                        f"❌ Failed: **{failed}**\n"
                        f"🔍 Filtered: **{filtered}**\n\n"
                        f"📁 **Files by Type:**\n"
                        f"🎬 Videos: {file_types_count['video']} | "
                        f"📄 Docs: {file_types_count['document']}\n"
                        f"🖼 Photos: {file_types_count['photo']} | "
                        f"🎵 Audio: {file_types_count['audio']}\n"
                        f"📝 Text: {file_types_count['text']}\n\n"
                        f"⬇️ Download: **{self.format_speed(avg_dl_speed)}**\n"
                        f"⬆️ Upload: **{self.format_speed(avg_ul_speed)}**\n"
                        f"⚡ Speed: **{speed:.1f} msg/s** | ⏱ ETA: **{int(eta)}s**\n"
                        f"{f'Last Error: {last_error}' if last_error else ''}"
                    )
                    last_update = current_time
        
        tasks = [process_with_semaphore(msgid) for msgid in range(from_id, to_id + 1)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        avg_speed = total_messages / total_time if total_time > 0 else 0
        avg_dl_speed = sum(self.download_speeds) / len(self.download_speeds) if self.download_speeds else 0
        avg_ul_speed = sum(self.upload_speeds) / len(self.upload_speeds) if self.upload_speeds else 0
        
        await progress_msg.edit_text(
            f"✅ **Batch Processing Complete!**\n\n"
            f"📊 **Total:** {total_messages} messages\n"
            f"✅ Successful: **{successful}**\n"
            f"❌ Failed: **{failed}**\n"
            f"🔍 Filtered: **{filtered}**\n\n"
            f"📁 **Files Processed:**\n"
            f"🎬 Videos: {file_types_count['video']}\n"
            f"📄 Documents: {file_types_count['document']}\n"
            f"🖼 Photos: {file_types_count['photo']}\n"
            f"🎵 Audio: {file_types_count['audio']}\n"
            f"📝 Text: {file_types_count['text']}\n\n"
            f"📍 **Destination:** {destination_info}\n"
            f"⬇️ **Avg Download:** {self.format_speed(avg_dl_speed)}\n"
            f"⬆️ **Avg Upload:** {self.format_speed(avg_ul_speed)}\n"
            f"⏱ **Time:** {int(total_time)}s | ⚡ **Speed:** {avg_speed:.2f} msg/s\n\n"
            f"{'❌ All files failed - check account permissions' if successful == 0 and failed > 0 else ''}"
        )
    
    def create_progress_bar(self, current: int, total: int, length: int = 10) -> str:
        percent = current / total if total > 0 else 0
        filled = int(length * percent)
        bar = '█' * filled + '░' * (length - filled)
        return f"[{bar}] {int(percent * 100)}%"

batch_processor = OptimizedBatchProcessor()
