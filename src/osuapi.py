import os
from ossapi import Ossapi
from dotenv import load_dotenv
load_dotenv()

callback_url="http://localhost:3000"

osuapi = Ossapi(os.environ['OSU_CLIENT_ID'], os.environ['OSU_CLIENT_SECRET'], callback_url, grant="authorization", token_key="osutoken", token_directory="tokens")
