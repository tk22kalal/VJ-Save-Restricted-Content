import os
import asyncio
import time
import re
from pyrogram import Client, enums
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChannelPrivate, UserNotParticipant, ChatWriteForbidden, PeerIdInvalid, RPCError
from database.db import db
from TechVJ.settings import clean_caption, clean_filename

class OptimizedBatchProcessor:
    def __init__(self):
        self.download_speeds = []
        self.upload_speeds = []

    async def process_message_concurrent(self, client: Client, acc, user_message: Message, chatid: int, msgid: int, user_settings: dict, topic_id: int = None):
        try:
            msg = await acc.get_messages(chatid, msgid)
            if not msg or msg.empty:
                return None, "Empty message", "unknown", 0, 0

            msg_type = self.get_message_type(msg)
            if not msg_type:
                return None, "Unknown message type", "unknown", 0, 0

            # File type filter
            file_filter = user_settings.get("file_type_filter", "all")
            if file_filter != "all" and not self.matches_filter(msg_type, file_filter):
                return "filtered", f"Filtered ({msg_type})", msg_type.lower(), 0, 0

            # Use channel destination if available
            destination = user_settings.get("upload_destination", user_message.chat.id)

            # --- Handle text messages quickly ---
            if msg_type == "Text":
                cleaned = clean_caption(msg.text, user_settings) if msg.text else ""
                try:
                    await client.send_message(destination, cleaned or msg.text, parse_mode=enums.ParseMode.HTML)
                    return "success", "Text sent", "text", 0, 0
                except Exception as e:
                    return "error", f"Text send failed: {str(e)}", "text", 0, 0

            # --- Fast Download ---
            start_dl = time.time()
            try:
                file = await acc.download_media(msg, file_name=f"temp_{msgid}", block=True)
            except FloodWait as e:
                await asyncio.sleep(min(e.value, 5))  # cap wait
                file = await acc.download_media(msg, file_name=f"temp_{msgid}", block=True)
            except RPCError as e:
                return "error", f"Download RPCError: {str(e)}", msg_type.lower(), 0, 0
            if not file:
                return "error", "Download failed", msg_type.lower(), 0, 0
            download_time = time.time() - start_dl
            size = os.path.getsize(file)
            dl_speed = size / download_time if download_time > 0 else 0

            # --- Upload ---
            caption = clean_caption(msg.caption, user_settings) if msg.caption else None
            start_ul = time.time()
            try:
                upload_status, err = await self.upload_media(client, file, msg, msg_type, caption, destination)
            except FloodWait as e:
                await asyncio.sleep(min(e.value, 5))
                upload_status, err = await self.upload_media(client, file, msg, msg_type, caption, destination)
            upload_time = time.time() - start_ul
            ul_speed = size / upload_time if upload_time > 0 else 0

            if os.path.exists(file):
                os.remove(file)

            if upload_status == "error":
                # fallback to user chat
                try:
                    await client.send_message(user_message.chat.id, f"⚠️ Upload failed to channel: {err}\nSending to your chat instead...")
                    await self.upload_media(client, file, msg, msg_type, caption, user_message.chat.id)
                    return "success", "Uploaded via fallback", msg_type.lower(), dl_speed, ul_speed
                except Exception as e:
                    return "error", f"Upload failed: {str(e)}", msg_type.lower(), dl_speed, ul_speed

            return "success", f"DL {self.format_speed(dl_speed)}, UL {self.format_speed(ul_speed)}", msg_type.lower(), dl_speed, ul_speed

        except Exception as e:
            return "error", f"Unexpected error: {str(e)}", "unknown", 0, 0

    async def upload_media(self, client, file, msg, msg_type, caption, destination):
        """Fast upload to target chat/channel"""
        try:
            if msg_type == "Video":
                await client.send_video(destination, file, caption=caption, parse_mode=enums.ParseMode.HTML)
            elif msg_type == "Document":
                await client.send_document(destination, file, caption=caption, parse_mode=enums.ParseMode.HTML)
            elif msg_type == "Photo":
                await client.send_photo(destination, file, caption=caption, parse_mode=enums.ParseMode.HTML)
            elif msg_type == "Audio":
                await client.send_audio(destination, file, caption=caption, parse_mode=enums.ParseMode.HTML)
            elif msg_type == "Voice":
                await client.send_voice(destination, file, caption=caption, parse_mode=enums.ParseMode.HTML)
            elif msg_type == "Animation":
                await client.send_animation(destination, file, caption=caption, parse_mode=enums.ParseMode.HTML)
            else:
                await client.send_message(destination, caption or "Unsupported message type.")
            return "success", ""
        except PeerIdInvalid:
            return "error", "Invalid destination (bot not admin or channel not found)"
        except Exception as e:
            return "error", str(e)

    def get_message_type(self, msg):
        if getattr(msg, "video", None): return "Video"
        if getattr(msg, "document", None): return "Document"
        if getattr(msg, "photo", None): return "Photo"
        if getattr(msg, "audio", None): return "Audio"
        if getattr(msg, "voice", None): return "Voice"
        if getattr(msg, "animation", None): return "Animation"
        if getattr(msg, "text", None): return "Text"
        return None

    def matches_filter(self, msg_type, filter_type):
        filters = {
            "video": ["Video", "Animation"],
            "document": ["Document"],
            "photo": ["Photo"],
            "audio": ["Audio", "Voice"],
            "text": ["Text"]
        }
        return filter_type == "all" or msg_type in filters.get(filter_type, [])

    def format_speed(self, bps):
        if bps < 1024: return f"{bps:.1f} B/s"
        if bps < 1024 * 1024: return f"{bps/1024:.1f} KB/s"
        return f"{bps/(1024*1024):.1f} MB/s"

batch_processor = OptimizedBatchProcessor()
