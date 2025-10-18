import re
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.db import db

user_states = {}

@Client.on_message(filters.command(["settings"]))
async def settings_menu(client: Client, message: Message):
    user_id = message.from_user.id
    user_states.pop(user_id, None)
    await show_main_settings_message(client, message, user_id)

async def show_main_settings_message(client: Client, message: Message, user_id: int):
    settings = await db.get_user_settings(user_id)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗂 Destination Channel", callback_data="settings_destination")],
        [InlineKeyboardButton("🎞 File Type Filter", callback_data="settings_filetype")],
        [InlineKeyboardButton("✂️ Caption Cleanup", callback_data="settings_caption")],
        [InlineKeyboardButton("🧾 Custom Remove Words", callback_data="settings_customwords")],
        [InlineKeyboardButton("🔄 Reset All Settings", callback_data="settings_reset")],
        [InlineKeyboardButton("❌ Close", callback_data="settings_close")]
    ])
    
    cleanup_status = "Enabled" if any(settings['caption_cleanup'].values()) else "Disabled"
    
    text = (
        "**⚙️ Settings Menu**\n\n"
        "Configure your batch download and upload preferences:\n\n"
        f"**Current Settings:**\n"
        f"📍 Destination: {settings['destination_channel'] or 'Not Set'}\n"
        f"🎞 File Type: {settings['file_type_filter'].title()}\n"
        f"✂️ Caption Cleanup: {cleanup_status}\n"
        f"🧾 Custom Words: {len(settings['custom_remove_words'])} word(s)"
    )
    
    await message.reply(text, reply_markup=keyboard)

@Client.on_callback_query(filters.regex("^settings_"))
async def settings_callback(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    settings = await db.get_user_settings(user_id)
    
    if data == "settings_close":
        user_states.pop(user_id, None)
        await callback.message.delete()
        return
    
    elif data == "settings_destination":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Set Channel/Group", callback_data="dest_set")],
            [InlineKeyboardButton("🗑 Clear Destination", callback_data="dest_clear")],
            [InlineKeyboardButton("« Back", callback_data="settings_back")]
        ])
        await callback.message.edit_text(
            "**🗂 Destination Channel Setup**\n\n"
            f"Current: {settings['destination_channel'] or 'Not Set'}\n\n"
            "Set a destination channel/group where extracted files will be uploaded.\n\n"
            "Click 'Set Channel/Group' to enter a channel.",
            reply_markup=keyboard
        )
    
    elif data == "settings_filetype":
        current_filter = settings['file_type_filter']
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{'✅' if current_filter == 'all' else '⬜'} All Types", callback_data="filter_all")],
            [InlineKeyboardButton(f"{'✅' if current_filter == 'video' else '⬜'} Videos Only", callback_data="filter_video")],
            [InlineKeyboardButton(f"{'✅' if current_filter == 'document' else '⬜'} Documents Only", callback_data="filter_document")],
            [InlineKeyboardButton(f"{'✅' if current_filter == 'text' else '⬜'} Text Only", callback_data="filter_text")],
            [InlineKeyboardButton(f"{'✅' if current_filter == 'photo' else '⬜'} Photos Only", callback_data="filter_photo")],
            [InlineKeyboardButton(f"{'✅' if current_filter == 'audio' else '⬜'} Audio Only", callback_data="filter_audio")],
            [InlineKeyboardButton("« Back", callback_data="settings_back")]
        ])
        await callback.message.edit_text(
            "**🎞 File Type Filter**\n\n"
            f"Current: {current_filter.title()}\n\n"
            "Select which types of files to extract and upload during batch operations:",
            reply_markup=keyboard
        )
    
    elif data == "settings_caption":
        cleanup = settings['caption_cleanup']
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{'✅' if cleanup['remove_usernames'] else '⬜'} Remove @Usernames",
                callback_data="caption_toggle_usernames"
            )],
            [InlineKeyboardButton(
                f"{'✅' if cleanup['remove_links'] else '⬜'} Remove Links",
                callback_data="caption_toggle_links"
            )],
            [InlineKeyboardButton(
                f"{'✅' if cleanup['remove_hashtags'] else '⬜'} Remove #Hashtags",
                callback_data="caption_toggle_hashtags"
            )],
            [InlineKeyboardButton("« Back", callback_data="settings_back")]
        ])
        await callback.message.edit_text(
            "**✂️ Caption Cleanup Options**\n\n"
            "Automatically clean captions before uploading:\n\n"
            f"• @Usernames: {'Enabled' if cleanup['remove_usernames'] else 'Disabled'}\n"
            f"• Links: {'Enabled' if cleanup['remove_links'] else 'Disabled'}\n"
            f"• #Hashtags: {'Enabled' if cleanup['remove_hashtags'] else 'Disabled'}\n\n"
            "Click to toggle each option.",
            reply_markup=keyboard
        )
    
    elif data == "settings_customwords":
        custom_words = settings['custom_remove_words']
        words_list = ', '.join(custom_words) if custom_words else 'None'
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Word/Phrase", callback_data="customword_add")],
            [InlineKeyboardButton("🗑 Clear All", callback_data="customword_clear")],
            [InlineKeyboardButton("« Back", callback_data="settings_back")]
        ])
        await callback.message.edit_text(
            "**🧾 Custom Remove Words**\n\n"
            f"Current words: {words_list}\n\n"
            "Add custom words or phrases to remove from filenames and captions.\n\n"
            "Click 'Add Word/Phrase' to enter text.",
            reply_markup=keyboard
        )
    
    elif data == "settings_reset":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirm Reset", callback_data="reset_confirm")],
            [InlineKeyboardButton("❌ Cancel", callback_data="settings_back")]
        ])
        await callback.message.edit_text(
            "**🔄 Reset All Settings**\n\n"
            "Are you sure you want to reset all settings to default?\n\n"
            "This will clear:\n"
            "• Destination channel\n"
            "• File type filter\n"
            "• Caption cleanup options\n"
            "• Custom remove words",
            reply_markup=keyboard
        )
    
    elif data == "settings_back":
        user_states.pop(user_id, None)
        await show_main_settings(callback.message, user_id)
    
    elif data.startswith("filter_"):
        filter_type = data.replace("filter_", "")
        await db.set_file_type_filter(user_id, filter_type)
        await callback.answer(f"✅ File filter set to: {filter_type.title()}", show_alert=True)
        
        settings = await db.get_user_settings(user_id)
        current_filter = settings['file_type_filter']
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{'✅' if current_filter == 'all' else '⬜'} All Types", callback_data="filter_all")],
            [InlineKeyboardButton(f"{'✅' if current_filter == 'video' else '⬜'} Videos Only", callback_data="filter_video")],
            [InlineKeyboardButton(f"{'✅' if current_filter == 'document' else '⬜'} Documents Only", callback_data="filter_document")],
            [InlineKeyboardButton(f"{'✅' if current_filter == 'text' else '⬜'} Text Only", callback_data="filter_text")],
            [InlineKeyboardButton(f"{'✅' if current_filter == 'photo' else '⬜'} Photos Only", callback_data="filter_photo")],
            [InlineKeyboardButton(f"{'✅' if current_filter == 'audio' else '⬜'} Audio Only", callback_data="filter_audio")],
            [InlineKeyboardButton("« Back", callback_data="settings_back")]
        ])
        await callback.message.edit_text(
            "**🎞 File Type Filter**\n\n"
            f"Current: {current_filter.title()}\n\n"
            "Select which types of files to extract and upload during batch operations:",
            reply_markup=keyboard
        )
    
    elif data.startswith("caption_toggle_"):
        cleanup_type = data.replace("caption_toggle_", "")
        current_value = settings['caption_cleanup'][f'remove_{cleanup_type}']
        new_value = not current_value
        await db.set_caption_cleanup(user_id, f'remove_{cleanup_type}', new_value)
        
        action = "enabled" if new_value else "disabled"
        await callback.answer(f"✅ {cleanup_type.title()} cleanup {action}", show_alert=True)
        
        settings = await db.get_user_settings(user_id)
        cleanup = settings['caption_cleanup']
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{'✅' if cleanup['remove_usernames'] else '⬜'} Remove @Usernames",
                callback_data="caption_toggle_usernames"
            )],
            [InlineKeyboardButton(
                f"{'✅' if cleanup['remove_links'] else '⬜'} Remove Links",
                callback_data="caption_toggle_links"
            )],
            [InlineKeyboardButton(
                f"{'✅' if cleanup['remove_hashtags'] else '⬜'} Remove #Hashtags",
                callback_data="caption_toggle_hashtags"
            )],
            [InlineKeyboardButton("« Back", callback_data="settings_back")]
        ])
        await callback.message.edit_text(
            "**✂️ Caption Cleanup Options**\n\n"
            "Automatically clean captions before uploading:\n\n"
            f"• @Usernames: {'Enabled' if cleanup['remove_usernames'] else 'Disabled'}\n"
            f"• Links: {'Enabled' if cleanup['remove_links'] else 'Disabled'}\n"
            f"• #Hashtags: {'Enabled' if cleanup['remove_hashtags'] else 'Disabled'}\n\n"
            "Click to toggle each option.",
            reply_markup=keyboard
        )
    
    elif data == "reset_confirm":
        await db.reset_user_settings(user_id)
        await callback.answer("✅ All settings reset to default!", show_alert=True)
        await show_main_settings(callback.message, user_id)
    
    elif data == "dest_set":
        user_states[user_id] = 'awaiting_destination'
        await callback.message.edit_text(
            "**🗂 Set Destination Channel**\n\n"
            "Send the channel username (with @) or channel ID now.\n\n"
            "Examples:\n"
            "• @mychannel\n"
            "• -1001234567890\n\n"
            "Or send /cancel to go back."
        )
        await callback.answer()
    
    elif data == "dest_clear":
        await db.set_destination_channel(user_id, None)
        await callback.answer("✅ Destination cleared!", show_alert=True)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Set Channel/Group", callback_data="dest_set")],
            [InlineKeyboardButton("🗑 Clear Destination", callback_data="dest_clear")],
            [InlineKeyboardButton("« Back", callback_data="settings_back")]
        ])
        settings = await db.get_user_settings(user_id)
        await callback.message.edit_text(
            "**🗂 Destination Channel Setup**\n\n"
            f"Current: {settings['destination_channel'] or 'Not Set'}\n\n"
            "Set a destination channel/group where extracted files will be uploaded.\n\n"
            "Click 'Set Channel/Group' to enter a channel.",
            reply_markup=keyboard
        )
    
    elif data == "customword_add":
        user_states[user_id] = 'awaiting_custom_word'
        await callback.message.edit_text(
            "**➕ Add Custom Word/Phrase**\n\n"
            "Send the word or phrase you want to remove from filenames and captions now.\n\n"
            "Example: NextPulse\n\n"
            "Or send /cancel to go back."
        )
        await callback.answer()
    
    elif data == "customword_clear":
        await db.clear_custom_remove_words(user_id)
        await callback.answer("✅ All custom words cleared!", show_alert=True)
        
        settings = await db.get_user_settings(user_id)
        custom_words = settings['custom_remove_words']
        words_list = ', '.join(custom_words) if custom_words else 'None'
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Word/Phrase", callback_data="customword_add")],
            [InlineKeyboardButton("🗑 Clear All", callback_data="customword_clear")],
            [InlineKeyboardButton("« Back", callback_data="settings_back")]
        ])
        await callback.message.edit_text(
            "**🧾 Custom Remove Words**\n\n"
            f"Current words: {words_list}\n\n"
            "Add custom words or phrases to remove from filenames and captions.\n\n"
            "Click 'Add Word/Phrase' to enter text.",
            reply_markup=keyboard
        )

@Client.on_message(filters.text & filters.private, group=-1)
async def handle_settings_input(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    
    if message.text == '/cancel':
        user_states.pop(user_id, None)
        await message.reply("❌ Cancelled. Use /settings to open settings menu again.")
        message.stop_propagation()
        return
    
    if state == 'awaiting_destination':
        channel = message.text.strip()
        await db.set_destination_channel(user_id, channel)
        user_states.pop(user_id, None)
        await message.reply(
            f"✅ Destination channel set to: {channel}\n\n"
            "All batch uploads will now go to this channel.\n"
            "Use /settings to change it again."
        )
        message.stop_propagation()
    
    elif state == 'awaiting_custom_word':
        word = message.text.strip()
        await db.add_custom_remove_word(user_id, word)
        user_states.pop(user_id, None)
        await message.reply(
            f"✅ Added custom word: {word}\n\n"
            "This word will be removed from filenames and captions.\n"
            "Use /settings to manage your custom words."
        )
        message.stop_propagation()

async def show_main_settings(message: Message, user_id: int):
    settings = await db.get_user_settings(user_id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗂 Destination Channel", callback_data="settings_destination")],
        [InlineKeyboardButton("🎞 File Type Filter", callback_data="settings_filetype")],
        [InlineKeyboardButton("✂️ Caption Cleanup", callback_data="settings_caption")],
        [InlineKeyboardButton("🧾 Custom Remove Words", callback_data="settings_customwords")],
        [InlineKeyboardButton("🔄 Reset All Settings", callback_data="settings_reset")],
        [InlineKeyboardButton("❌ Close", callback_data="settings_close")]
    ])
    
    cleanup_status = "Enabled" if any(settings['caption_cleanup'].values()) else "Disabled"
    
    await message.edit_text(
        "**⚙️ Settings Menu**\n\n"
        "Configure your batch download and upload preferences:\n\n"
        f"**Current Settings:**\n"
        f"📍 Destination: {settings['destination_channel'] or 'Not Set'}\n"
        f"🎞 File Type: {settings['file_type_filter'].title()}\n"
        f"✂️ Caption Cleanup: {cleanup_status}\n"
        f"🧾 Custom Words: {len(settings['custom_remove_words'])} word(s)",
        reply_markup=keyboard
    )

def clean_caption(caption: str, settings: dict) -> str:
    if not caption:
        return caption
    
    cleanup_settings = settings.get('caption_cleanup', {})
    cleaned = caption
    
    if cleanup_settings.get('remove_usernames', False):
        cleaned = re.sub(r'@\w+', '', cleaned)
    
    if cleanup_settings.get('remove_links', False):
        cleaned = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', cleaned)
        cleaned = re.sub(r't\.me/\S+', '', cleaned)
    
    if cleanup_settings.get('remove_hashtags', False):
        cleaned = re.sub(r'#\w+', '', cleaned)
    
    for word in settings.get('custom_remove_words', []):
        cleaned = cleaned.replace(word, '')
    
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

def clean_filename(filename: str, settings: dict) -> str:
    if not filename:
        return filename
    
    cleaned = filename
    
    for word in settings.get('custom_remove_words', []):
        cleaned = cleaned.replace(word, '')
    
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned
