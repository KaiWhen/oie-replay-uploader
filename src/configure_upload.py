import math
import sys
from render import get_render, send_render
from upload_video import initialize_upload
from mongo import scores_col, status_col
from osuapi import osuapi
from thumbnail import create_thumbnail
from osu_sr_calculator import calculateStarRating
from upload_video import youtube
from datetime import datetime


def render_replay(score_id):
    score_obj = osuapi.score(mode="osu", score_id=score_id)
    username = score_obj._user.username
    is_rendered = get_render(username, score_id)
    if is_rendered:
        scores_col.update_one({
            'score_id': score_id
        },{
            '$set': {
                'rendered': True
            }
        }, upsert=False)


def upload_replay(score_id):
    score_obj = osuapi.score(mode="osu", score_id=score_id)
    user_obj = osuapi.user(user=score_obj.user_id, mode="osu")
    username = score_obj._user.username
    acc = math.floor(score_obj.accuracy * 10000) / 100
    ar = f"{score_obj.beatmap.ar}"
    cs = f"{score_obj.beatmap.cs}"
    bpm = f"{score_obj.beatmap.bpm}"
    star_rating = round(score_obj.beatmap.difficulty_rating, 2)
    mods = score_obj.mods.__str__()
    if mods == "NM":
        mods = ""
    else:
        mods = f"+{score_obj.mods.__str__()} "
    if "DT" in mods or "NC" in mods:
        ar = f"{ar}*"
        bpm = f"{bpm} ({round(score_obj.beatmap.bpm * 1.5)})"
        star_rating = round(calculateStarRating(map_id=score_obj.beatmap.id, mods=['DT'])['DT'], 2)
    if "HT" in mods:
        ar = f"{ar}*"
        bpm = f"{bpm} ({round(score_obj.beatmap.bpm * 0.75)})"
        star_rating = round(calculateStarRating(map_id=score_obj.beatmap.id, mods=['HT'])['HT'], 2)
    if "HR" in mods:
        ar_hr = round(score_obj.beatmap.ar * 1.4, 1)
        if ar_hr > 10:
            ar_hr = 10
        ar = f"{ar} ({ar_hr})"
        cs = f"{cs} ({round(score_obj.beatmap.cs * 1.3, 1)})"
        star_rating = round(calculateStarRating(map_id=score_obj.beatmap.id, mods=['HR'])['HR'], 2)
    description = f"👤 Player info \
                    \nProfile: https://osu.ppy.sh/users/{score_obj.user_id} \
                    \nGlobal # {user_obj.statistics.global_rank} | IE # {user_obj.statistics.country_rank} | {user_obj.statistics.play_count} plays | {round(user_obj.statistics.play_time/3600)} hrs \
                    \n\n🗺️ Map info \
                    \nMap Link: https://osu.ppy.sh/b/{score_obj.beatmap.id} \
                    \n{star_rating}⭐ | BPM: {bpm} | AR: {ar} | CS: {cs} \
                    \n\nThis channel is currently run by a bot made by https://osu.ppy.sh/users/10040214 \
                    \nThe bot tracks top 10 personal pp plays of the top 100 players of Ireland. \
                    \nIf you have a score that does not meet the above requirements but you think should be uploaded, just fill in this form here: https://forms.gle/ZABXAzAVnewbhSNr7 \
                    \nIf you would like your skin to be used in your replay, upload your skin to https://ordr.issou.best/skins and DM the skin ID to kaiwhen on Discord. \
                    \n\nosu!Irish Discord: https://discord.gg/aqqU7VcJuK \
                    \n\n\n#{user_obj.username} #osuireland"
    map_title = f"{score_obj.beatmapset.artist} - {score_obj.beatmapset.title} [{score_obj.beatmap.version}]"
    title_len = len(map_title) + len(f"{username} | ") + len(f" {score_obj.mods} ") + len(f" {acc}%") + 6
    if title_len > 100:
        title_elems = [f"{score_obj.beatmapset.artist}", f"{score_obj.beatmapset.title}", f"{score_obj.beatmap.version}"]
        longest = max(title_elems, key=len)
        longest_idx = title_elems.index(longest)
        longest = longest[0:(len(longest) - ((title_len - 100) + 3))]
        longest += "..."
        title_elems[longest_idx] = longest
        map_title = f"{title_elems[0]} - {title_elems[1]} [{title_elems[2]}]"
    title = f"{username} | {map_title} {mods}{acc}%"
    special_chars = "<>"
    for c in title:
        if c in special_chars:
            title = title.replace(c, "")
    tag_title = score_obj.beatmapset.title
    for c in tag_title:
        if c in special_chars:
            tag_title = tag_title.replace(c, "")
    if score_obj.pp:
        pp = round(score_obj.pp)
        title = f"{title} {pp}PP"
    sys.stdout.write(title)
    upload_args = {
        "file": f"videos/{score_id}.mp4",
        "title": f"{title}",
        "description": f"{description}",
        "tags": f"osu!,osu ireland,{username},{tag_title} osu",
        "category": 20,
        "privacyStatus": 'public'
    }
    thumb_path = create_thumbnail(score_id)
    if not thumb_path:
        sys.stdout.write("thumbnail creation failed")
        return False
    initialize_upload(upload_args, score_id, thumb_path)
    if check_and_delete(score_id, youtube):
        sys.stdout.write("A previous score was deleted")
    return True


def dl_send_replay(score_id):
    try:
        replayData = osuapi.download_score(mode="osu", score_id=score_id, raw=True)
    except:
        sys.stdout.write("download failed")
        return False

    replay_path = f"replays/{score_id}.osr"

    with open(replay_path, 'wb') as b:
        b.write(replayData)

    render_sent = send_render(replay_path, score_id)

    if not render_sent:
        sys.stdout.write(f"score {score_id} was not sent successfully, oopsies!")
        return render_sent
    
    return render_sent


def check_and_delete(score_id, youtube):
    delete = False
    score = osuapi.score(mode="osu", score_id=score_id)
    old_scores = scores_col.find({"map_id": score.beatmap.id, "user_id": score.user_id, "deleted": False})
    if not old_scores:
        return delete
    timestamps = []
    for s in old_scores:
        if score.id == s['score_id']:
            continue
        timestamps.append(s['timestamp'])
    if len(timestamps) == 0:
        return delete
    recent_timestamp = max(timestamps)
    old_score = scores_col.find_one({"map_id": score.beatmap.id, "user_id": score.user_id, "timestamp": recent_timestamp})
    old_mods = old_score['mods']
    if score.mods == old_mods or ("DT" or "NC" in str(score.mods) and str(old_mods)):
        now = datetime.now()
        timestamp = datetime.timestamp(now)
        status_string = score.beatmap.status.__str__()[11:]
        if status_string == 'LOVED':
            if timestamp - old_score['timestamp'] < 2629743:
                delete = True
        elif status_string in ['RANKED', 'APPROVED']:
            if score.pp > old_score['pp'] and timestamp - old_score['timestamp'] < 604800*2:
                delete = True
    if delete:
        request = youtube.videos().update(
        part="status",
        body={
          "id": old_score['video_id'],
          "status": {
            "privacyStatus": "private"
          }
        }
    )
        request.execute()

        status_col.update_one({
                'country': 'IE'
            },{
                '$inc': {
                    'units_used': 50
                }
            }, upsert=False)
        
        scores_col.update_one({"map_id": score.beatmap.id, "user_id": score.user_id, "timestamp": recent_timestamp}, {
            '$set': {
                "deleted": True
            }
        }, upsert=False)

    return delete
