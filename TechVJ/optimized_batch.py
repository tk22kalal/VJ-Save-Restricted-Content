import os
import asyncio
import time
import re
from pyrogram import Client, enums
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChannelPrivate, UserNotParticipant, ChatWriteForbidden, PeerIdInvalid
from database.db import db
from TechVJ.settings import clean_caption, clean_filename

class OptimizedBatchProcessor:
    def __init__(self):
        self.active_tasks = {}
        self.download_speeds = []
        self.upload_speeds = []
        self.current_file = 0
    
    async def process_message_concurrent(self, client: Client, acc, user_message: Message, chatid: int, msgid: int, user_settings: dict, topic_id: int = None):
        try:
            # Get message using the account
            msg = await acc.get_messages(chatid, msgid)
            if not msg or msg.empty:
                return None, "Empty message", "unknown", 0, 0
            
            # Filter by topic/subgroup if specified
            if topic_id is not None:
                msg_topic_id = None
                if hasattr(msg, 'reply_to_message_id') and msg.reply_to_message_id:
                    try:
                        reply_msg = await acc.get_messages(chatid, msg.reply_to_message_id)
                        if hasattr(reply_msg, 'message_thread_id'):
                            msg_topic_id = reply_msg.message_thread_id
                    except:
                        pass
                elif hasattr(msg, 'message_thread_id'):
                    msg_topic_id = msg.message_thread_id
                
                # Skip if message is not from the requested topic
                if msg_topic_id != topic_id:
                    return "filtered", f"Wrong topic (expected {topic_id}, got {msg_topic_id})", "unknown", 0, 0
            
            # ALWAYS use user's chat as destination for now to avoid PEER_ID_INVALID
            destination = user_message.chat.id
            
            msg_type = self.get_message_type(msg)
            if not msg_type:
                return None, "Unknown message type", "unknown", 0, 0
            
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
                        entities=msg.entities,
                        reply_to_message_id=user_message.id,
                        parse_mode=enums.ParseMode.HTML
                    )
                    return "success", "Text sent", "text", 0, 0
                except Exception as e:
                    return "error", f"Text send failed: {str(e)}", "text", 0, 0
            
            # Download file
            start_time = time.time()
            
            # Create status file for download progress
            status_file = f"{user_message.id}downstatus.txt"
            try:
                file = await acc.download_media(
                    msg, 
                    progress=self.progress, 
                    progress_args=(user_message, "down")
                )
            except Exception as e:
                return "error", f"Download failed: {str(e)}", msg_type.lower(), 0, 0
            
            download_time = time.time() - start_time
            
            if not file or not os.path.exists(file):
                return "error", "Download failed - file not found", msg_type.lower(), 0, 0
            
            file_size = os.path.getsize(file) if os.path.exists(file) else 0
            download_speed = file_size / download_time if download_time > 0 else 0
            
            # Clean caption
            caption = msg.caption if msg.caption else None
            if caption:
                caption = clean_caption(caption, user_settings)
            
            # Upload file
            start_time = time.time()
            upload_result, upload_error = await self.upload_media(client, acc, destination, file, msg, msg_type, caption, user_message)
            upload_time = time.time() - start_time
            upload_speed = file_size / upload_time if upload_time > 0 else 0
            
            # Cleanup
            if os.path.exists(file):
                os.remove(file)
            if os.path.exists(f"{user_message.id}downstatus.txt"):
                os.remove(f"{user_message.id}downstatus.txt")
            if os.path.exists(f"{user_message.id}upstatus.txt"):
                os.remove(f"{user_message.id}upstatus.txt")
            
            if upload_result == "error":
                return "error", f"Upload failed: {upload_error}", msg_type.lower(), download_speed, upload_speed
            
            return "success", f"DL: {self.format_speed(download_speed)}, UL: {self.format_speed(upload_speed)}", msg_type.lower(), download_speed, upload_speed
            
        except FloodWait as e:
            await asyncio.sleep(e.value)
            return await self.process_message_concurrent(client, acc, user_message, chatid, msgid, user_settings, topic_id)
        except Exception as e:
            return "error", f"Unexpected error: {str(e)}", "unknown", 0, 0
    
    def progress(self, current, total, message, type):
        """Progress callback like old batch code"""
        with open(f"{message.id}{type}status.txt", "w") as fileup:
            fileup.write(f"{current * 100 / total:.1f}%")
    
    async def upload_media(self, client: Client, acc, chat_id, file: str, msg, msg_type: str, caption: str, user_message: Message):
        try:
            # Use the same upload logic as old batch code but ensure we're sending to valid chat
            if msg_type == "Document":
                ph_path = None
                try:
                    if msg.document.thumbs:
                        ph_path = await acc.download_media(msg.document.thumbs[0].file_id)
                except Exception:
                    ph_path = None

                try:
                    await client.send_document(
                        chat_id,
                        file,
                        thumb=ph_path,
                        caption=caption,
                        reply_to_message_id=user_message.id,
                        parse_mode=enums.ParseMode.HTML,
                        progress=self.progress,
                        progress_args=[user_message, "up"],
                    )
                except PeerIdInvalid:
                    return "error", "Invalid destination channel - bot cannot access it"
                except Exception as e:
                    return "error", f"Document send failed: {str(e)}"
                
                if ph_path and os.path.exists(ph_path):
                    try:
                        os.remove(ph_path)
                    except:
                        pass

            elif msg_type == "Video":
                ph_path = None
                try:
                    if msg.video.thumbs:
                        ph_path = await acc.download_media(msg.video.thumbs[0].file_id)
                except Exception:
                    ph_path = None

                try:
                    await client.send_video(
                        chat_id,
                        file,
                        duration=getattr(msg.video, "duration", None),
                        width=getattr(msg.video, "width", None),
                        height=getattr(msg.video, "height", None),
                        thumb=ph_path,
                        caption=caption,
                        reply_to_message_id=user_message.id,
                        parse_mode=enums.ParseMode.HTML,
                        progress=self.progress,
                        progress_args=[user_message, "up"],
                    )
                except PeerIdInvalid:
                    return "error", "Invalid destination channel - bot cannot access it"
                except Exception as e:
                    return "error", f"Video send failed: {str(e)}"
                
                if ph_path and os.path.exists(ph_path):
                    try:
                        os.remove(ph_path)
                    except:
                        pass

            elif msg_type == "Animation":
                try:
                    await client.send_animation(
                        chat_id, 
                        file, 
                        caption=caption, 
                        reply_to_message_id=user_message.id, 
                        parse_mode=enums.ParseMode.HTML
                    )
                except PeerIdInvalid:
                    return "error", "Invalid destination channel - bot cannot access it"
                except Exception as e:
                    return "error", f"Animation send failed: {str(e)}"

            elif msg_type == "Sticker":
                try:
                    await client.send_sticker(chat_id, file, reply_to_message_id=user_message.id)
                except PeerIdInvalid:
                    return "error", "Invalid destination channel - bot cannot access it"
                except Exception as e:
                    return "error", f"Sticker send failed: {str(e)}"

            elif msg_type == "Voice":
                try:
                    await client.send_voice(
                        chat_id,
                        file,
                        caption=caption,
                        caption_entities=getattr(msg, "caption_entities", None),
                        reply_to_message_id=user_message.id,
                        parse_mode=enums.ParseMode.HTML,
                        progress=self.progress,
                        progress_args=[user_message, "up"],
                    )
                except PeerIdInvalid:
                    return "error", "Invalid destination channel - bot cannot access it"
                except Exception as e:
                    return "error", f"Voice send failed: {str(e)}"

            elif msg_type == "Audio":
                ph_path = None
                try:
                    if getattr(msg.audio, "thumbs", None):
                        ph_path = await acc.download_media(msg.audio.thumbs[0].file_id)
                except Exception:
                    ph_path = None

                try:
                    await client.send_audio(
                        chat_id,
                        file,
                        thumb=ph_path,
                        caption=caption,
                        reply_to_message_id=user_message.id,
                        parse_mode=enums.ParseMode.HTML,
                        progress=self.progress,
                        progress_args=[user_message, "up"],
                    )
                except PeerIdInvalid:
                    return "error", "Invalid destination channel - bot cannot access it"
                except Exception as e:
                    return "error", f"Audio send failed: {str(e)}"
                
                if ph_path and os.path.exists(ph_path):
                    try:
                        os.remove(ph_path)
                    except:
                        pass

            elif msg_type == "Photo":
                try:
                    await client.send_photo(
                        chat_id, 
                        file, 
                        caption=caption, 
                        reply_to_message_id=user_message.id, 
                        parse_mode=enums.ParseMode.HTML
                    )
                except PeerIdInvalid:
                    return "error", "Invalid destination channel - bot cannot access it"
                except Exception as e:
                    return "error", f"Photo send failed: {str(e)}"

            return "success", ""
        except Exception as e:
            return "error", str(e)
    
    def get_message_type(self, msg):
        """Same message type detection as old code"""
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
                                            user_settings: dict, max_concurrent: int = 3, topic_id: int = None):
        total_messages = to_id - from_id + 1
        processed = 0
        successful = 0
        failed = 0
        filtered = 0
        file_types_count = {'video': 0, 'document': 0, 'photo': 0, 'audio': 0, 'text': 0, 'other': 0}
        self.download_speeds = []
        self.upload_speeds = []
        error_messages = []
        
        # IGNORE user destination settings for now - always use user's chat to avoid PEER_ID_INVALID
        destination_info = "Your chat (safe mode)"
        
        file_filter = user_settings.get('file_type_filter', 'all').title()
        topic_info = f" | 🎯 Topic: {topic_id}" if topic_id is not None else ""
        
        # Test first message to verify permissions and avoid slow starts
        test_msg = await user_message.reply("🔍 Testing permissions...")
        try:
            first_msg = await acc.get_messages(chatid, from_id)
            if not first_msg or first_msg.empty:
                await test_msg.edit_text("❌ Cannot access messages. Check if:\n• The account has joined the chat\n• Messages are not deleted")
                return
            await test_msg.delete()
        except ChannelPrivate:
            await test_msg.edit_text("❌ Chat is private and account hasn't joined. Send invite link first using the old batch method.")
            return
        except UserNotParticipant:
            await test_msg.edit_text("❌ Account is not a participant of this chat. Join the chat first.")
            return
        except PeerIdInvalid:
            await test_msg.edit_text("❌ Invalid chat ID. Please check the link.")
            return
        except Exception as e:
            await test_msg.edit_text(f"❌ Permission test failed: {str(e)}")
            return
        
        progress_msg = await user_message.reply(
            f"🚀 **Starting Optimized Batch Process**\n\n"
            f"📊 Total messages: **{total_messages}**\n"
            f"⚡ Concurrent tasks: **{max_concurrent}**\n"
            f"📍 Destination: **{destination_info}**{topic_info}\n"
            f"🎞 File filter: **{file_filter}**\n\n"
            f"Processing..."
        )
        
        start_time = time.time()
        last_update = start_time
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(msgid):
            nonlocal processed, successful, failed, filtered, last_update
            
            async with semaphore:
                result, info, msg_type, dl_speed, ul_speed = await self.process_message_concurrent(
                    client, acc, user_message, chatid, msgid, user_settings, topic_id
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
                    if len(error_messages) < 5:  # Store first 5 errors
                        error_messages.append(f"Msg {msgid}: {info}")
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
                    
                    status_text = (
                        f"🚀 **Batch Processing** ({percentage:.1f}%)\n\n"
                        f"{progress_bar}\n"
                        f"📊 **{processed}/{total_messages}** files processed\n\n"
                        f"✅ Successful: **{successful}**\n"
                        f"❌ Failed: **{failed}**\n"
                        f"🔍 Filtered: **{filtered}**\n\n"
                    )
                    
                    if successful > 0:
                        status_text += (
                            f"📁 **Files by Type:**\n"
                            f"🎬 Videos: {file_types_count['video']} | "
                            f"📄 Docs: {file_types_count['document']}\n"
                            f"🖼 Photos: {file_types_count['photo']} | "
                            f"🎵 Audio: {file_types_count['audio']}\n"
                            f"📝 Text: {file_types_count['text']}\n\n"
                        )
                    
                    if avg_dl_speed > 0 or avg_ul_speed > 0:
                        status_text += (
                            f"⬇️ Download: **{self.format_speed(avg_dl_speed)}**\n"
                            f"⬆️ Upload: **{self.format_speed(avg_ul_speed)}**\n"
                        )
                    
                    status_text += f"⚡ Speed: **{speed:.1f} msg/s** | ⏱ ETA: **{int(eta)}s**"
                    
                    if failed > 0 and len(error_messages) > 0:
                        status_text += f"\n\n❌ **Last Error:** {error_messages[-1]}"
                    
                    await progress_msg.edit_text(status_text)
                    last_update = current_time
        
        tasks = [process_with_semaphore(msgid) for msgid in range(from_id, to_id + 1)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        avg_speed = total_messages / total_time if total_time > 0 else 0
        avg_dl_speed = sum(self.download_speeds) / len(self.download_speeds) if self.download_speeds else 0
        avg_ul_speed = sum(self.upload_speeds) / len(self.upload_speeds) if self.upload_speeds else 0
        
        final_message = (
            f"✅ **Batch Processing Complete!**\n\n"
            f"📊 **Total:** {total_messages} messages\n"
            f"✅ Successful: **{successful}**\n"
            f"❌ Failed: **{failed}**\n"
            f"🔍 Filtered: **{filtered}**\n\n"
        )
        
        if successful > 0:
            final_message += (
                f"📁 **Files Processed:**\n"
                f"🎬 Videos: {file_types_count['video']}\n"
                f"📄 Documents: {file_types_count['document']}\n"
                f"🖼 Photos: {file_types_count['photo']}\n"
                f"🎵 Audio: {file_types_count['audio']}\n"
                f"📝 Text: {file_types_count['text']}\n\n"
            )
        
        final_message += (
            f"📍 **Destination:** {destination_info}\n"
            f"⬇️ **Avg Download:** {self.format_speed(avg_dl_speed)}\n"
            f"⬆️ **Avg Upload:** {self.format_speed(avg_ul_speed)}\n"
            f"⏱ **Time:** {int(total_time)}s | ⚡ **Speed:** {avg_speed:.2f} msg/s\n"
        )
        
        if failed > 0 and error_messages:
            final_message += f"\n**First few errors:**\n" + "\n".join(error_messages[:3])
        
        await progress_msg.edit_text(final_message)
    
    def create_progress_bar(self, current: int, total: int, length: int = 10) -> str:
        percent = current / total if total > 0 else 0
        filled = int(length * percent)
        bar = '█' * filled + '░' * (length - filled)
        return f"[{bar}] {int(percent * 100)}%"

batch_processor = OptimizedBatchProcessor()
