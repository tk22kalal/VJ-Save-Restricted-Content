import os

#Bot token @Botfather
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

#Your API ID from my.telegram.org
API_ID = int(os.environ.get("API_ID", "24058425"))

#Your API Hash from my.telegram.org
API_HASH = os.environ.get("API_HASH", "694b063e55c24287a3d30aed90191373")

#Database 
DB_URI = os.environ.get("DB_URI", "mongodb+srv://tk22kalal:tk22kalal@cluster0.n5urzc6.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
