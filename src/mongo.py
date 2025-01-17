import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
load_dotenv()

mongo_client = MongoClient(os.environ['MONGO_URI'], server_api=ServerApi('1'))

db = mongo_client['replaybotdb']
status_col = db['status']
scores_col = db['scores']
skins_col = db['skins']
bot_col = db['botstatus']
