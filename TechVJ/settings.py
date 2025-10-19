import re
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import PeerIdInvalid, ChannelPrivate, UsernameNotOccupied, ChatAdminRequired, UserNotParticipant
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
    dest_display = settings.get('destination_channel') or 'Not Set'
    
    text = (
        "**⚙️ Settings Menu**\n\n"
        "Configure your batch download and upload preferences:\n\n"
        f"**Current Settings:**\n"
        f"📍 Destination: `{dest_display}`\n"
        f"🎞 File Type: {settings['file_type_filter'].title()}\n"
        f"✂️ Caption Cleanup: {cleanup_status}\n"
        f"🧾 Custom Words: {len(settings['custom_remove_words'])} word(s)"
    )
    
    await message.reply(text, reply_markup=keyboard)

@Client.on_callback_query(filters.regex("^(settings_|dest_|filter_|caption_|customword_|reset_)"))
async def settings_callback(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    settings = await db.get_user_settings(user_id)
    
    if data == "settings_close":
        user_states.pop(user_id, None)
        await callback.answer()
        await callback.message.delete()
        return
    
    elif data == "settings_destination":
        await callback.answer()
        dest = settings.get('destination_channel') or 'Not Set'
        
        # Validate current destination if set
        validation_status = ""
        if settings.get('destination_channel'):
            try:
                chat_info = await client.get_chat(settings['destination_channel'])
                
                if chat_info.type in ["channel", "supergroup"]:
                    try:
                        bot_member = await client.get_chat_member(settings['destination_channel'], "me")
                        if bot_member.status == "administrator":
                            if bot_member.privileges.can_post_messages:
                                validation_status = "\n\n✅ **Status:** Valid & Working"
                            else:
                                validation_status = "\n\n⚠️ **Status:** Bot needs 'Post Messages' permission"
                        elif bot_member.status == "creator":
                            validation_status = "\n\n✅ **Status:** Valid & Working"
                        else:
                            validation_status = "\n\n❌ **Status:** Bot is not admin"
                    except:
                        validation_status = "\n\n❌ **Status:** Cannot access channel"
                else:
                    validation_status = "\n\n✅ **Status:** Valid"
            except:
                validation_status = "\n\n❌ **Status:** Invalid or inaccessible"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Set Channel/Group", callback_data="dest_set")],
            [InlineKeyboardButton("🗑 Clear Destination", callback_data="dest_clear")],
            [InlineKeyboardButton("« Back", callback_data="settings_back")]
        ])
        await callback.message.edit_text(
            "**🗂 Destination Channel Setup**\n\n"
            f"Current: `{dest}`{validation_status}\n\n"
            "Set a destination channel/group where extracted files will be uploaded.\n\n"
            "**Requirements:**\n"
            "• Bot must be added as admin\n"
            "• Must have 'Post Messages' permission\n\n"
            "Click 'Set Channel/Group' to enter a channel.",
            reply_markup=keyboard
        )
    
    elif data == "settings_filetype":
        await callback.answer()
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
        await callback.answer()
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
        await callback.answer()
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
        await callback.answer()
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
        await callback.answer()
        await show_main_settings_message(client, callback.message, user_id)
    
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
        await show_main_settings_message(client, callback.message, user_id)
    
    elif data == "dest_set":
        await callback.answer()
        user_states[user_id] = 'awaiting_destination'
        await callback.message.edit_text(
            "**🗂 Set Destination Channel**\n\n"
            "Send the channel username (with @) or channel ID now.\n\n"
            "**Examples:**\n"
            "• @mychannel\n"
            "• -1001234567890 (or -1002... for newer channels)\n\n"
            "**Requirements:**\n"
            "• Bot must be admin in the channel\n"
            "• Bot needs 'Post Messages' permission\n\n"
            "Or send /cancel to go back."
        )
    
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
            f"Current: Not Set\n\n"
            "Set a destination channel/group where extracted files will be uploaded.\n\n"
            "**Requirements:**\n"
            "• Bot must be added as admin\n"
            "• Must have 'Post Messages' permission\n\n"
            "Click 'Set Channel/Group' to enter a channel.",
            reply_markup=keyboard
        )
    
    elif data == "customword_add":
        await callback.answer()
        user_states[user_id] = 'awaiting_custom_word'
        await callback.message.edit_text(
            "**➕ Add Custom Word/Phrase**\n\n"
            "Send the word or phrase you want to remove from filenames and captions now.\n\n"
            "Example: NextPulse\n\n"
            "Or send /cancel to go back."
        )
    
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
        
        # Convert to int if it's a channel ID (starts with -)
        if channel.startswith('-'):
            try:
                channel = int(channel)
            except ValueError:
                user_states.pop(user_id, None)
                await message.reply(
                    f"❌ **Invalid Channel ID Format**\n\n"
                    f"`{channel}` is not a valid channel ID.\n\n"
                    f"**Valid formats:**\n"
                    f"• @channelname\n"
                    f"• -1001234567890 (or -1002234567890 for newer channels)"
                )
                message.stop_propagation()
                return
        
        # Validate the destination
        try:
            chat_info = await client.get_chat(channel)
            
            # Check if it's a channel or supergroup
            if chat_info.type in ["channel", "supergroup"]:
                try:
                    # Check if bot is member and has permissions
                    bot_member = await client.get_chat_member(channel, "me")
                    
                    if bot_member.status == "administrator":
                        if not bot_member.privileges.can_post_messages:
                            user_states.pop(user_id, None)
                            await message.reply(
                                f"❌ **Permission Error**\n\n"
                                f"Bot is admin in `{channel}` but doesn't have **'Post Messages'** permission.\n\n"
                                f"**Fix:** Give bot 'Post Messages' permission and try again."
                            )
                            message.stop_propagation()
                            return
                    elif bot_member.status != "creator":
                        user_states.pop(user_id, None)
                        await message.reply(
                            f"❌ **Admin Required**\n\n"
                            f"Bot must be admin in `{channel}`\n\n"
                            f"**Steps:**\n"
                            f"1. Add bot to the channel\n"
                            f"2. Promote bot to admin\n"
                            f"3. Enable 'Post Messages' permission\n"
                            f"4. Try setting destination again"
                        )
                        message.stop_propagation()
                        return
                        
                except UserNotParticipant:
                    user_states.pop(user_id, None)
                    await message.reply(
                        f"❌ **Bot Not Added**\n\n"
                        f"Bot is not a member of `{channel}`\n\n"
                        f"**Steps:**\n"
                        f"1. Add bot to the channel\n"
                        f"2. Promote bot to admin\n"
                        f"3. Enable 'Post Messages' permission\n"
                        f"4. Try again"
                    )
                    message.stop_propagation()
                    return
                except ChatAdminRequired:
                    user_states.pop(user_id, None)
                    await message.reply(
                        f"❌ **Admin Rights Required**\n\n"
                        f"Bot needs admin rights in `{channel}`\n\n"
                        f"Make bot admin with 'Post Messages' permission."
                    )
                    message.stop_propagation()
                    return
            
            # If all checks pass, save the destination
            await db.set_destination_channel(user_id, channel)
            user_states.pop(user_id, None)
            
            # Get display name
            if chat_info.username:
                display_name = f"@{chat_info.username}"
            elif chat_info.title:
                display_name = chat_info.title
            else:
                display_name = channel
            
            await message.reply(
                f"✅ **Destination Set Successfully!**\n\n"
                f"Channel: {display_name}\n"
                f"ID: `{channel}`\n\n"
                f"All batch uploads will now go to this channel.\n"
                f"Use /settings to change it again."
            )
            message.stop_propagation()
            
        except PeerIdInvalid:
            user_states.pop(user_id, None)
            await message.reply(
                f"❌ **Invalid Channel ID**\n\n"
                f"`{channel}` is not a valid channel ID or username.\n\n"
                f"**Valid formats:**\n"
                f"• @channelname\n"
                f"• -1001234567890 (or -1002234567890 for newer channels)"
            )
            message.stop_propagation()
        except ChannelPrivate:
            user_states.pop(user_id, None)
            await message.reply(
                f"❌ **Private Channel**\n\n"
                f"Cannot access `{channel}` - it's private.\n\n"
                f"Add bot to the channel first."
            )
            message.stop_propagation()
        except UsernameNotOccupied:
            user_states.pop(user_id, None)
            await message.reply(
                f"❌ **Username Not Found**\n\n"
                f"`{channel}` doesn't exist.\n\n"
                f"Check the username and try again."
            )
            message.stop_propagation()
        except Exception as e:
            user_states.pop(user_id, None)
            await message.reply(
                f"❌ **Error**\n\n"
                f"Failed to set destination: {str(e)}\n\n"
                f"Please try again or use /settings."
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
