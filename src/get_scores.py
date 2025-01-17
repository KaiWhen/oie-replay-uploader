from datetime import datetime
from dateutil import parser
from osuapi import osuapi
from mongo import status_col, scores_col
from forms import get_score


def get_top100():
    cursor_pg2 = { "page": 2 }
    top50 = osuapi.ranking(mode="osu", country="IE", type="performance")
    top100 = osuapi.ranking(mode="osu", country="IE", type="performance", cursor=cursor_pg2)
    top100_users = []
    for player in top50.ranking + top100.ranking:
        top100_users.append(player.user.id)
    return top100_users


def get_top_scores():
    update_status = status_col.find_one({'country': 'IE'})
    if not update_status:
        now = datetime.now()
        timestamp = datetime.timestamp(now)
        status_col.insert_one({
            'country': 'IE',
            'last_updated': timestamp,
            'form_updated': timestamp
        })

    top100 = get_top100()
    valid_scores = []
    for player in top100:
        try:
            scores_top10 = osuapi.user_scores(user_id=player, type="best", limit=10, mode="osu")
        except:
            continue

        # try:
        #     scores_recent50 = osuapi.user_scores(user_id=player, type="recent", limit=50, mode="osu")
        # except:
        #     continue
        # if not scores_recent50:
        #     continue
        for score in scores_top10:
            if not score or datetime.timestamp(score.created_at) - update_status['last_updated'] < 0 or not score.replay or check_deranked(score.id):
                continue
            valid_scores.append(score.id)
            insert_score(score.id)

        # for score in scores_recent10:
        #     now = datetime.now()
        #     timestamp = datetime.timestamp(now)
        #     if (datetime.timestamp(score.created_at) - update_status['last_updated'] < 0
        #        or not score.replay
        #        or timestamp - datetime.timestamp(score.beatmap.beatmapset().ranked_date) < 432000
        #        or score.beatmap.difficulty_rating < 3
        #        or not score.passed
        #        or score.best_id in valid_scores
        #        or check_deranked(score.best_id)):
        #         continue
        #     playcount = score.beatmap.playcount
        #     rank_cutoff = get_rank_cutoff(playcount)
        #     score_obj = osuapi.score(mode="osu", score_id=score.best_id)
        #     if score_obj.rank_global <= rank_cutoff:
        #         valid_scores.append(score.best_id)
        #         insert_score(score.best_id)

    now = datetime.now()
    timestamp = datetime.timestamp(now)
    status_col.update_one({
        'country': 'IE'
    },{
        '$set': {
            'last_updated': timestamp
        }
    }, upsert=False)

    return valid_scores


def insert_score(score_id):
    score = osuapi.score(mode="osu", score_id=score_id)
    map_id = score.beatmap.id
    player = score._user.username
    map_title = score.beatmapset.title
    now = datetime.now()
    timestamp = datetime.timestamp(now)
    score_exists = scores_col.find_one({"score_id": score_id})
    if not score_exists:
        scores_col.insert_one({
            "score_id": score_id,
            "user_id": score.user_id,
            "map_id": map_id,
            "pp": score.pp,
            "mods": str(score.mods),
            "video_id": "",
            "description": f"{player} - {map_title}",
            "render_sent": False,
            "rendered": False,
            "uploaded": False,
            "timestamp": timestamp,
            "deleted": False
        })


# def get_rank_cutoff(playcount):
#     if playcount < 5000:
#         return 10
#     elif playcount > 5000 and playcount < 25000:
#         return 20
#     elif playcount > 25000 and playcount < 50000:
#         return 25
#     elif playcount > 50000:
#         return 50


def check_deranked(score_id):
    deranked = False
    score = get_score(score_id)
    if score is None:
        return deranked
    old_scores = scores_col.find({"map_id": score['beatmap']['id'], "user_id": score['user']['id'], "mods": ''.join(score['mods'])})
    if not old_scores:
        return deranked
    status_string = score['beatmap']['status']
    if status_string not in ['ranked', 'approved']:
        return deranked
    for s in old_scores:
        if score['id'] == s['score_id']:
            continue
        if score['pp'] < s['pp']:
            deranked = True
        elif score['pp'] > s['pp']:
            deranked = False
    return deranked

# score_obj = osuapi.score(mode="osu", score_id=4443385148)
# rank_cutoff = get_rank_cutoff(score_obj.beatmap.playcount)
# print(score_obj.beatmap.playcount)
# if score_obj.rank_global <= rank_cutoff:
#     print("loeignoiregn")

# print(check_deranked(4445737874))
# score = osuapi.score(mode="osu", score_id=4445737874)
# old_scores = osuapi.beatmap_user_scores(beatmap_id=score.beatmap.id, user_id=score.user_id, mode="osu")
# for s in old_scores:
#     print(str(s.mods))
