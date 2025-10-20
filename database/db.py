import motor.motor_asyncio
from config import DB_NAME, DB_URI

class Database:
    
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users

    def new_user(self, id, name):
        return dict(
            id = id,
            name = name,
            session = None,
            settings = {
                'destination_channel': None,
                'file_type_filter': 'all',
                'caption_cleanup': {
                    'remove_usernames': False,
                    'remove_links': False,
                    'remove_hashtags': False
                },
                'custom_remove_words': []
            }
        )
    
    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)
    
    async def is_user_exist(self, id):
        user = await self.col.find_one({'id':int(id)})
        return bool(user)
    
    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count

    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})

    async def set_session(self, id, session):
        await self.col.update_one({'id': int(id)}, {'$set': {'session': session}})

    async def get_session(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('session')

    async def get_user_settings(self, id):
        user = await self.col.find_one({'id': int(id)})
        if user and 'settings' in user:
            return user['settings']
        return {
            'destination_channel': None,
            'file_type_filter': 'all',
            'caption_cleanup': {
                'remove_usernames': False,
                'remove_links': False,
                'remove_hashtags': False
            },
            'custom_remove_words': []
        }

    async def update_user_settings(self, id, settings):
        await self.col.update_one({'id': int(id)}, {'$set': {'settings': settings}})

    async def set_destination_channel(self, id, channel):
        settings = await self.get_user_settings(id)
        settings['destination_channel'] = channel
        await self.update_user_settings(id, settings)

    async def set_file_type_filter(self, id, filter_type):
        settings = await self.get_user_settings(id)
        settings['file_type_filter'] = filter_type
        await self.update_user_settings(id, settings)

    async def set_caption_cleanup(self, id, cleanup_type, value):
        settings = await self.get_user_settings(id)
        settings['caption_cleanup'][cleanup_type] = value
        await self.update_user_settings(id, settings)

    async def add_custom_remove_word(self, id, word):
        settings = await self.get_user_settings(id)
        if word not in settings['custom_remove_words']:
            settings['custom_remove_words'].append(word)
        await self.update_user_settings(id, settings)

    async def remove_custom_remove_word(self, id, word):
        settings = await self.get_user_settings(id)
        if word in settings['custom_remove_words']:
            settings['custom_remove_words'].remove(word)
        await self.update_user_settings(id, settings)

    async def clear_custom_remove_words(self, id):
        settings = await self.get_user_settings(id)
        settings['custom_remove_words'] = []
        await self.update_user_settings(id, settings)

    async def reset_user_settings(self, id):
        default_settings = {
            'destination_channel': None,
            'file_type_filter': 'all',
            'caption_cleanup': {
                'remove_usernames': False,
                'remove_links': False,
                'remove_hashtags': False
            },
            'custom_remove_words': []
        }
        await self.update_user_settings(id, default_settings)

    async def save_batch_progress(self, user_id, chat_id, last_processed_msg_id, total_messages):
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {
                'batch_progress': {
                    'chat_id': chat_id,
                    'last_processed': last_processed_msg_id,
                    'total': total_messages
                }
            }}
        )

    async def get_batch_progress(self, user_id):
        user = await self.col.find_one({'id': int(user_id)})
        if user and 'batch_progress' in user:
            return user['batch_progress']
        return None

    async def clear_batch_progress(self, user_id):
        await self.col.update_one(
            {'id': int(user_id)},
            {'$unset': {'batch_progress': ''}}
        )

    async def refresh_session(self, user_id):
        user = await self.col.find_one({'id': int(user_id)})
        if user and user.get('session'):
            return user.get('session')
        return None

db = Database(DB_URI, DB_NAME)
