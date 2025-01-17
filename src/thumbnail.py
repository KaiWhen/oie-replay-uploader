import os
import sys
import requests
import math
import re
from zipfile import ZipFile
from PIL import Image, ImageFont, ImageDraw
from osuapi import osuapi


def create_thumbnail(score_id):
    score_obj = osuapi.score(mode="osu", score_id=score_id)
    user_obj = osuapi.user(user=score_obj.user_id)
    beatmap_score_obj = osuapi.beatmap_scores(beatmap_id=score_obj.beatmap.id, mode="osu", type="country")
    scores_top50 = osuapi.user_scores(user_id=score_obj.user_id, type="best", limit=50, mode="osu")

    set_id = score_obj.beatmapset.id
    diff = score_obj.beatmap.version
    bg_path = get_map_bg(set_id, diff)
    if not bg_path:
        sys.stdout.write("oop bg path not found")
        return None
    
    if not os.path.exists(f"thumbnails/{score_id}"):
        os.mkdir(f"thumbnails/{score_id}")

    rank = score_obj.rank.__str__()[6:]
    user_id = score_obj.user_id

    r = requests.get(f"https://a.ppy.sh/{user_id}")
    avatar_path = f"thumbnails/{score_id}/{user_id}.png"
    with open(avatar_path, 'wb') as outfile:
        outfile.write(r.content)

    ratio = 1.5

    thumbnail = Image.open(bg_path).convert('RGBA').resize((1280, 720))
    base = Image.open("thumbnails/assets/base.png").convert('RGBA').resize((1280, 720))
    rank_image = Image.open(f"thumbnails/assets/{rank}.png").convert('RGBA').resize((1280, 720))
    dim_image = Image.open(f"thumbnails/assets/dim.png").convert('RGBA').resize((1280, 720))
    avatar = Image.open(avatar_path).convert('RGBA').resize((round(256/ratio), round(256/ratio)))
    pb_image = Image.open("thumbnails/assets/pb.png").convert('RGBA').resize((1280, 720))
    
    bg_w, _ = thumbnail.size

    count = 1
    country_ranking = None
    for score in beatmap_score_obj.scores:
        if score.user_id == score_obj.user_id:
            country_ranking = count
            break
        count = count + 1
    
    count = 1
    pb_text = None
    for score in scores_top50:
        if score_obj.id == score.id:
            pb_text = f"#{count}"
            break
        count = count + 1

    acc = math.floor(score_obj.accuracy * 10000) / 100
    acc_text_before = f"{'%.2f' % acc}%"
    acc_text = f"{'%.2f' % acc}% | "
    mods_text = f"{score_obj.mods}"
    username_text = f"{user_obj.username}"

    if country_ranking is not None:
        country_ranking_text = f"#{country_ranking}"
        country_rank_text = f"#{user_obj.statistics.country_rank}"
    else:
        country_ranking_text = f"#-"
        country_rank_text = f"#-"

    global_ranking_text = f"#{score_obj.rank_global}"
    
    global_rank_text = f"#{user_obj.statistics.global_rank}"

    move_diff_y = 0

    title_text = f"{score_obj.beatmapset.artist} - {score_obj.beatmapset.title}"
    title_font_size = 50
    if len(title_text) > 45:
        move_diff_y = 10
        title_font_size = title_font_size - round((len(title_text) - 45) / 1.6)

    diff_text = f"[{score_obj.beatmap.version}]"
    diff_font_size = 50
    if len(diff_text) > 45:
        
        diff_font_size = diff_font_size - round((len(diff_text) - 45) / 1.6)

    is_fc_text = ""
    fc_text_colour = (255, 255, 255)
    if score_obj.max_combo == score_obj.beatmap.max_combo:
        is_fc_text = "FC"
        fc_text_colour = (255, 235, 122)
    elif score_obj.statistics.count_miss > 0:
        is_fc_text = f"{score_obj.statistics.count_miss}x"
        fc_text_colour = (255, 0, 0)

    pp_text = "0pp"
    status_string = score_obj.beatmap.status.__str__()[11:]
    if status_string in ['RANKED', 'APPROVED']:
        pp_text = f"{round(score_obj.pp)}pp"
    elif status_string == 'LOVED':
        pp_text = "Loved"
    
    acc_pp_text = f"{acc_text} | {pp_text}"

    if len(acc_text_before) > 6:
        pp_offset = round(390/ratio)
    else:
        pp_offset = round(340/ratio)

    futura_medium = "thumbnails/assets/futura_medium.ttf"
    nexa_heavy = "thumbnails/assets/Nexa-Heavy.ttf"

    title_font = ImageFont.truetype(futura_medium, title_font_size)
    diff_font = ImageFont.truetype(futura_medium, diff_font_size)
    acc_font = ImageFont.truetype(futura_medium, 50)
    pb_font = ImageFont.truetype(nexa_heavy, 35)
    ie_font = ImageFont.truetype(nexa_heavy, 30)
    country_font = ImageFont.truetype(nexa_heavy, 47)
    user_font = ImageFont.truetype(futura_medium, 50)
    fc_font = ImageFont.truetype(futura_medium, 150)

    thumbnail.paste(dim_image, (0, 0), dim_image)
    thumbnail.paste(base, (0, 0), base)
    thumbnail.paste(rank_image, (0, 0), rank_image)
    thumbnail.paste(avatar, (round(23/ratio), round(795/ratio)), avatar)

    mods = [mods_text[i:i+2] for i in range(0, len(mods_text), 2)]
    mod_w = round(165/ratio)
    mods_length = mod_w * len(mods)
    mods_offset = (bg_w - mods_length) // 2
    count = 0
    for mod in mods:
        mod_image = Image.open(f"thumbnails/assets/mod_{mod}.png").convert('RGBA').resize((113, 92))
        thumbnail.paste(mod_image, ((mods_offset + mod_w*count) - 20, round(540/ratio)), mod_image)
        count = count + 1

    image = ImageDraw.Draw(thumbnail)
    _, _, title_w, _ = image.textbbox((0, 0), title_text, font=title_font)
    image.text(((bg_w - title_w)/2, 120), title_text, (255, 255, 255), font=title_font)
    _, _, diff_w, _ = image.textbbox((0, 0), diff_text, font=diff_font)
    image.text(((bg_w - diff_w)/2, 180-move_diff_y), diff_text, (255, 255, 255), font=diff_font)
    _, _, acc_w, _ = image.textbbox((0, 0), acc_pp_text, font=acc_font)
    image.text(((bg_w - acc_w)/2, round(400/ratio)), acc_text, (255, 255, 255), font=acc_font)
    image.text(((bg_w - acc_w)/2 + pp_offset, round(400/ratio)), pp_text, (0, 255, 106), font=acc_font)

    image.text((round(305/ratio), round(970/ratio)), username_text, (255, 255, 255), font=user_font)
    image.text((round(1630/ratio), round(387/ratio)), country_ranking_text, (255, 255, 255), font=ie_font)
    image.text((round(1630/ratio), round(483/ratio)), global_ranking_text, (255, 255, 255), font=ie_font)
    image.text((round(394/ratio), round(800/ratio)), country_rank_text, (255, 255, 255), font=country_font)
    image.text((round(394/ratio), round(890/ratio)), global_rank_text, (255, 255, 255), font=country_font)
    image.text((round(1480/ratio), round(844/ratio)), is_fc_text, fc_text_colour, font=fc_font)
    if pb_text:
        thumbnail.paste(pb_image, (0, 0), pb_image)
        image.text((round(1430/ratio), round(425/ratio)), pb_text, (255, 255, 255), font=pb_font)

    thumb_path = f"thumbnails/{score_id}/{score_id}.png"

    thumbnail.save(thumb_path)

    return thumb_path


def get_map_bg(set_id, diff):
    if not os.path.exists(f"maps/{set_id}"):
        os.mkdir(f"maps/{set_id}")

        chimu_url = f"https://catboy.best/d/{set_id}n"
        beatconnect_url = f"https://beatconnect.io/b/{set_id}"
        r = requests.get(chimu_url)
        if not r.ok:
            r = requests.get(beatconnect_url)
        with open(f"maps/{set_id}/map.osz", 'wb') as outfile:
            outfile.write(r.content)

        with ZipFile(f"maps/{set_id}/map.osz", 'r') as zip_ref:
            zip_ref.extractall(f"maps/{set_id}")

    bg_path = None
    backup_bg_path = "thumbnails/assets/default.png"

    special_chars = "\":@%^*?=,<>/|"
    diff_name = diff.casefold()
    # print(diff_name)

    for fname in os.listdir(f'maps/{set_id}'):
        for c in diff_name:
            if c in special_chars:
                diff_name = diff_name.replace(c, "")
            # print(diff_name)
        if fname.casefold().endswith(f"[{diff_name}].osu"):
            f = open(f"maps/{set_id}/{fname}", 'r')
            file_strings = re.findall('(?:")([^"]*)(?:")', f.read())
            print(file_strings)
            for string in file_strings:
                if string.casefold().endswith(".png") or string.casefold().endswith(".jpg") or string.casefold().endswith(".jpeg"):
                    bg_path = f"maps/{set_id}/{string}"
                    continue
        elif not fname.casefold().endswith(".png") and not fname.casefold().endswith(".jpg") and not fname.casefold().endswith(".jpeg") and not fname.casefold().endswith(".osu"):
            if os.path.isdir(f"maps/{set_id}/{fname}"):
                continue
            else:
                os.remove(f"maps/{set_id}/{fname}")
        elif fname.casefold().endswith(".png") or fname.casefold().endswith(".jpg") or fname.casefold().endswith(".jpeg"):
            backup_bg_path = f"maps/{set_id}/{fname}"
    print(bg_path)
    if bg_path is not None:
        file_exists = os.path.exists(bg_path)
        if not file_exists:
            bg_path = backup_bg_path
    else:
        bg_path = backup_bg_path
    return bg_path

# score_obj = osuapi.score(mode="osu", score_id=4394031592)
# bmscore_obj = osuapi.beatmap_scores(beatmap_id=score_obj.beatmap.id, mode="osu", type="country")
# user_obj = osuapi.user(user=score_obj.user_id)
# sys.stdout.write(score_obj.beatmap.status.__str__()[11:])
# create_thumbnail(4395074261)

# sys.stdout.write(get_map_bg(683123, "Flandre"))
