import requests
import os
import sys
from osuapi import osuapi
from urllib.request import urlretrieve
from mongo import scores_col, skins_col
from datetime import datetime
from dateutil import parser
from dotenv import load_dotenv
load_dotenv()

url = "https://apis.issou.best/ordr/renders"
dl_url = "https://apis.issou.best/dynlink/ordr/gen?id="
skin_url = "https://apis.issou.best/ordr/skins/custom"
osu_url = "https://osu.ppy.sh/api/v2/"

DEFAULT_SKIN = "7496"


def send_render(replay_file, score_id):
    global url
    replay = open(replay_file, 'rb')

    score = osuapi.score(mode="osu", score_id=score_id)
    user_id = score.user_id
    skin = skins_col.find_one({'user_id': user_id})
    skin_id = DEFAULT_SKIN
    if skin:
        skin_id = skin['skin_id']

    files = {
        'replayFile': replay
    }
    post_data = {
        'username': "o!IEBot",
        'resolution': "1280x720",
        'skin': str(skin_id),
        'customSkin': "true",
        'showDanserLogo': "false",
        'showHitCounter': "true",
        'showSliderBreaks': "true",
        'verificationKey': os.environ['ORDR_KEY']
    }

    resp = requests.post(url, files=files, data=post_data)

    if resp.status_code != 201:
        sys.stdout.write(f"error code: {resp.status_code}")
        return False
    
    scores_col.update_one({
        'score_id': score_id
    },{
        '$set': {
            'render_sent': True
        }
    }, upsert=False)
    
    sys.stdout.write(f"Render sent for score {score_id}")

    return True


def get_render(player, score_id):
    global url
    url_get = f"{url}?replayUsername={player}&ordrUsername=o!IEBot"

    resp = requests.get(url_get)
    if resp.json()['maxRenders'] == 0:
        return False
    renders = resp.json()['renders']

    got_render = False
    for render in renders:
        render_created = datetime.timestamp(parser.parse(render['date']))
        score = scores_col.find_one({'score_id': score_id})
        if not score:
            sys.stdout.write("score not found")
            continue
        render_map_id = render['mapID']
        score_obj = osuapi.score(mode="osu", score_id=score_id)
        map_id = score_obj.beatmapset.id
        if render_created - score['timestamp'] < 0 or render['progress'] != 'Done.' or render_map_id != map_id:
            continue
        render_id = render['renderID']
        video_url = requests.get(f"{dl_url}{render_id}").json()['url']
        urlretrieve(video_url, f'videos/{score_id}.mp4')
        got_render = True
        sys.stdout.write(f"render retrieved for score {score_id}")

    return got_render


def skin_exists(skin_id):
    skin = requests.get(f"{skin_url}?id={skin_id}").json()
    return skin['found']


# from osuapi import osuapi

# replay = osuapi.download_score(mode="osu", score_id=3979241792, raw=True)

# send_render("replays/3979241792.osr")

# with open("replays/3979241792.osr", 'wb') as b:
#     b.write(replay)

#get_render("KaiWhen", 3454998634)
