import os
import asyncio
import time
from pyrogram import Client, enums
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from database.db import db
from TechVJ.settings import clean_caption

class OptimizedBatchProcessor:
    def __init__(self):
        self.processed_count = 0
        self.success_count = 0
        self.failed_count = 0
        
    async def process_single_message(self, client: Client, acc, user_message: Message, chatid: int, msgid: int, user_settings: dict):
        """Process a single message - similar to old batch code but with settings"""
        try:
            # Get the message
            msg = await acc.get_messages(chatid, msgid)
            if not msg or msg.empty:
                return "error", "Message not found", "unknown"
            
            # Check file filter
            msg_type = self.get_message_type(msg)
            if not msg_type:
                return "error", "Unknown message type", "unknown"
            
            file_filter = user_settings.get('file_type_filter', 'all')
            if file_filter != 'all' and not self.matches_filter(msg_type, file_filter):
                return "filtered", f"Filtered out ({msg_type})", msg_type.lower()
            
            destination = user_settings.get('destination_channel') or user_message.chat.id
            
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
                    return "success", "Text sent", "text"
                except Exception as e:
                    return "error", f"Text send failed: {str(e)}", "text"
            
            # For media messages, use the old reliable method
            return await self.handle_media_message(client, acc, user_message, msg, msg_type, destination, user_settings)
            
        except FloodWait as e:
            await asyncio.sleep(e.value)
            return await self.process_single_message(client, acc, user_message, chatid, msgid, user_settings)
        except Exception as e:
            return "error", f"Unexpected error: {str(e)}", "unknown"
    
    async def handle_media_message(self, client: Client, acc, user_message: Message, msg, msg_type: str, destination: int, user_settings: dict):
        """Handle media messages using the proven old method"""
        try:
            # Download the file
            file = await acc.download_media(msg)
            if not file or not os.path.exists(file):
                return "error", "Download failed", msg_type.lower()
            
            # Clean caption
            caption = msg.caption if msg.caption else None
            if caption:
                caption = clean_caption(caption, user_settings)
            
            # Upload based on message type
            if msg_type == "Document":
                ph_path = None
                try:
                    if msg.document.thumbs:
                        ph_path = await acc.download_media(msg.document.thumbs[0].file_id)
                except:
                    pass
                
                await client.send_document(
                    destination,
                    file,
                    thumb=ph_path,
                    caption=caption,
                    reply_to_message_id=user_message.id,
                    parse_mode=enums.ParseMode.HTML
                )
                
                if ph_path and os.path.exists(ph_path):
                    os.remove(ph_path)

            elif msg_type == "Video":
                ph_path = None
                try:
                    if msg.video.thumbs:
                        ph_path = await acc.download_media(msg.video.thumbs[0].file_id)
                except:
                    pass
                
                await client.send_video(
                    destination,
                    file,
                    duration=getattr(msg.video, "duration", None),
                    width=getattr(msg.video, "width", None),
                    height=getattr(msg.video, "height", None),
                    thumb=ph_path,
                    caption=caption,
                    reply_to_message_id=user_message.id,
                    parse_mode=enums.ParseMode.HTML
                )
                
                if ph_path and os.path.exists(ph_path):
                    os.remove(ph_path)

            elif msg_type == "Animation":
                await client.send_animation(
                    destination, 
                    file, 
                    caption=caption, 
                    reply_to_message_id=user_message.id, 
                    parse_mode=enums.ParseMode.HTML
                )

            elif msg_type == "Sticker":
                await client.send_sticker(destination, file, reply_to_message_id=user_message.id)

            elif msg_type == "Voice":
                await client.send_voice(
                    destination,
                    file,
                    caption=caption,
                    caption_entities=getattr(msg, "caption_entities", None),
                    reply_to_message_id=user_message.id,
                    parse_mode=enums.ParseMode.HTML
                )

            elif msg_type == "Audio":
                ph_path = None
                try:
                    if getattr(msg.audio, "thumbs", None):
                        ph_path = await acc.download_media(msg.audio.thumbs[0].file_id)
                except:
                    pass
                
                await client.send_audio(
                    destination,
                    file,
                    thumb=ph_path,
                    caption=caption,
                    reply_to_message_id=user_message.id,
                    parse_mode=enums.ParseMode.HTML
                )
                
                if ph_path and os.path.exists(ph_path):
                    os.remove(ph_path)

            elif msg_type == "Photo":
                await client.send_photo(
                    destination, 
                    file, 
                    caption=caption, 
                    reply_to_message_id=user_message.id, 
                    parse_mode=enums.ParseMode.HTML
                )
            
            # Cleanup
            if os.path.exists(file):
                os.remove(file)
                
            return "success", f"{msg_type} sent", msg_type.lower()
            
        except Exception as e:
            # Cleanup on error
            if 'file' in locals() and os.path.exists(file):
                os.remove(file)
            return "error", f"Media processing failed: {str(e)}", msg_type.lower()
    
    def get_message_type(self, msg):
        """Same reliable message type detection"""
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
    
    async def batch_process_with_concurrency(self, client: Client, acc, user_message: Message, 
                                            chatid: int, from_id: int, to_id: int, 
                                            user_settings: dict, max_concurrent: int = 2):  # Reduced concurrency for Heroku
        """Simplified batch processor that works within Heroku constraints"""
        total_messages = to_id - from_id + 1
        processed = 0
        successful = 0
        failed = 0
        filtered = 0
        file_types_count = {'video': 0, 'document': 0, 'photo': 0, 'audio': 0, 'text': 0, 'other': 0}
        
        destination_info = user_settings.get('destination_channel') or "Bot Chat"
        file_filter = user_settings.get('file_type_filter', 'all').title()
        
        progress_msg = await user_message.reply(
            f"🚀 **Starting Batch Process**\n\n"
            f"📊 Total messages: **{total_messages}**\n"
            f"📍 Destination: **{destination_info}**\n"
            f"🎞 File filter: **{file_filter}**\n\n"
            f"Processing 0/{total_messages}..."
        )
        
        start_time = time.time()
        
        # Process messages sequentially with small delays (more reliable on Heroku)
        for msgid in range(from_id, to_id + 1):
            result, info, msg_type = await self.process_single_message(
                client, acc, user_message, chatid, msgid, user_settings
            )
            
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
            
            # Update progress every message (for small batches) or every few seconds
            current_time = time.time()
            elapsed = current_time - start_time
            speed = processed / elapsed if elapsed > 0 else 0
            eta = (total_messages - processed) / speed if speed > 0 else 0
            percentage = (processed / total_messages * 100) if total_messages > 0 else 0
            
            progress_bar = self.create_progress_bar(processed, total_messages)
            
            status_text = (
                f"🚀 **Batch Processing** ({percentage:.1f}%)\n\n"
                f"{progress_bar}\n"
                f"📊 **{processed}/{total_messages}** files processed\n\n"
                f"✅ Successful: **{successful}**\n"
                f"❌ Failed: **{failed}**\n"
                f"🔍 Filtered: **{filtered}**\n\n"
                f"⚡ Speed: **{speed:.1f} msg/s** | ⏱ ETA: **{int(eta)}s**\n"
            )
            
            if successful > 0:
                status_text += (
                    f"📁 **Files by Type:**\n"
                    f"🎬 Videos: {file_types_count['video']} | "
                    f"📄 Docs: {file_types_count['document']}\n"
                    f"🖼 Photos: {file_types_count['photo']} | "
                    f"🎵 Audio: {file_types_count['audio']}\n"
                    f"📝 Text: {file_types_count['text']}\n"
                )
            
            await progress_msg.edit_text(status_text)
            
            # Small delay between messages to avoid Heroku timeouts
            if processed < total_messages:
                await asyncio.sleep(1)
        
        total_time = time.time() - start_time
        avg_speed = total_messages / total_time if total_time > 0 else 0
        
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
            f"⏱ **Time:** {int(total_time)}s | ⚡ **Speed:** {avg_speed:.2f} msg/s\n"
        )
        
        await progress_msg.edit_text(final_message)
    
    def create_progress_bar(self, current: int, total: int, length: int = 10) -> str:
        percent = current / total if total > 0 else 0
        filled = int(length * percent)
        bar = '█' * filled + '░' * (length - filled)
        return f"[{bar}] {int(percent * 100)}%"

batch_processor = OptimizedBatchProcessor()
