import discord
import math
import asyncio
import os
import sys
import numpy as np
from mongo import skins_col, bot_col
from render import skin_exists
from forms import get_form_resp
from discord.ext import tasks
from discord import app_commands
from osuapi import osuapi
from osu_sr_calculator import calculateStarRating
from configure_upload import dl_send_replay
from get_scores import insert_score
from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    sys.stdout.write(f'We have logged in as {client.user}')
    await tree.sync()
    await get_form_job.start()


@tasks.loop(minutes=1)
async def get_form_job():
    channel = client.get_channel(1110508875238604871)

    bot_status = bot_col.find_one({'country': 'IE'})
    if bot_status['bot_upload_id'] != bot_status['new_upload_id']:
        notif_channel = client.get_channel(257559748075847680)
        link = f"https://youtu.be/{bot_status['new_upload_id']}"
        await notif_channel.send(f"{link}")
        bot_col.update_one({
            'country': 'IE'
        },{
            '$set': {
                'bot_upload_id': bot_status['new_upload_id']
            }
        }, upsert=False)

    score_ids = get_form_resp()
    votes = 3
    # score_ids = [4431716274]
    # await channel.purge(limit=50)
    if len(score_ids) > 0:
        players = []
        for id in score_ids:
            score = osuapi.score(mode="osu", score_id=id)
            players.append(score._user.username)
        players_arr = np.array(players)
        unique, counts = np.unique(players_arr, return_counts=True)
        players_dict = dict(zip(unique, counts))
        players_str = f"Received {len(score_ids)} request(s) for score(s) by:"
        for player in players_dict:
            players_str = f"{players_str} {player} ({players_dict[player]})"
        await channel.send(players_str)
        for id in score_ids:
            score = osuapi.score(mode="osu", score_id=id)
            user_id = score.user_id
            username = score._user.username
            pp = 0
            acc = math.floor(score.accuracy * 10000) / 100
            mods = score.mods.__str__()
            if score.pp:
                pp = round(score.pp)

            ar = f"{score.beatmap.ar}"
            cs = f"{score.beatmap.cs}"
            bpm = f"{score.beatmap.bpm}"
            star_rating = round(score.beatmap.difficulty_rating, 2)
            mods = score.mods.__str__()
            if "DT" in mods or "NC" in mods:
                ar = f"{ar}*"
                bpm = f"{bpm} ({round(score.beatmap.bpm * 1.5)})"
                star_rating = round(calculateStarRating(map_id=score.beatmap.id, mods=['DT'])['DT'], 2)
            if "HT" in mods:
                ar = f"{ar}*"
                bpm = f"{bpm} ({round(score.beatmap.bpm * 0.75)})"
                star_rating = round(calculateStarRating(map_id=score.beatmap.id, mods=['HT'])['HT'], 2)
            if "HR" in mods:
                ar_hr = round(score.beatmap.ar * 1.4, 1)
                if ar_hr > 10:
                    ar_hr = 10
                ar = f"{ar} ({ar_hr})"
                cs = f"{cs} ({round(score.beatmap.cs * 1.3, 1)})"
                star_rating = round(calculateStarRating(map_id=score.beatmap.id, mods=['HR'])['HR'], 2)
            status = score.beatmap.status.__str__()[11:]

            beatmap_score_obj = osuapi.beatmap_scores(beatmap_id=score.beatmap.id, mode="osu", type="country")
            count = 1
            for score_obj in beatmap_score_obj.scores:
                if score.user_id == score_obj.user_id:
                    country_ranking = count
                    break
                count = count + 1

            msg = f"**Replay upload request for score by {username}**"
            map_title = f"{score.beatmapset.artist} - {score.beatmapset.title} [{score.beatmap.version}] +{mods} [{star_rating}★]"
            em = discord.Embed()
            em.set_author(name=map_title, icon_url=f"https://a.ppy.sh/{user_id}", url=f"https://osu.ppy.sh/b/{score.beatmap.id}")
            em.add_field(name=f"{pp}PP ▸ Accuracy: {acc}% ▸ Combo: {score.max_combo}x/{score.beatmap.max_combo}x ▸ Misses: {score.statistics.count_miss}", 
                         value=f"{bpm} bpm ▸ AR{ar} ▸ CS{cs} ▸ {status} ▸ 🌐 #{score.rank_global} ▸ 🇮🇪 #{country_ranking}\nDate set: {str(score.created_at)[:-6]}")
            em.set_image(url=f"https://assets.ppy.sh/beatmaps/{score.beatmapset.id}/covers/card.jpg")
            em.set_footer(text=f"React below to approve or disapprove this request (requires {votes} votes for yes or no)")
            message = await channel.send(content=msg,embed=em)
            await message.add_reaction("✅")
            await message.add_reaction("❌")

            yes_count = 0
            no_count = 0

            def check(reaction, user):
                return reaction.message.channel.id == message.channel.id and reaction.message.id == message.id and str(reaction.emoji) in ["✅", "❌"]
            
            reacted_users = []

            while yes_count < votes and no_count < votes:
                try:
                    reaction, user = await client.wait_for('reaction_add', timeout=86400, check=check)
                    if user.id in reacted_users:
                        continue
                    if str(reaction.emoji) == "✅":
                        yes_count = yes_count + 1
                        reacted_users.append(user.id)
                    elif str(reaction.emoji) == "❌":
                        no_count = no_count + 1
                        reacted_users.append(user.id)
                except asyncio.TimeoutError:
                    await channel.send(f"Request for score {score.id} aborted")
                    break

            
            if yes_count == votes and no_count < votes:
                insert_score(score.id)
                replay_sent = dl_send_replay(score.id)
                if replay_sent:
                    await channel.send("**Replay queued for upload**")
                else:
                    await channel.send("**Error occurred while sending replay for upload**")
            elif yes_count < votes and no_count == votes:
                await channel.send("rip bozo")


@get_form_job.before_loop
async def get_form_before_loop():
    await client.wait_until_ready()


@tree.command(name = "shutdown", description = "Shutdown the bot")
async def shutdown(interaction: discord.Interaction):
    if interaction.user.id == 282617728320405514:
        await interaction.response.send_message("Shutting down...", ephemeral=True)
        await client.close()


@tree.command(name = "setskin", description = "Set skin for player")
async def set_skin(interaction: discord.Interaction, osu_name: str, skin_id: str):
    try:
        player = osuapi.user(user=osu_name)
    except:
        await interaction.response.send_message("Invalid player name. Please try again.")
        return

    if not skin_exists(skin_id):
        await interaction.response.send_message("Skin does not exist on o!rdr.")
        return

    player_id = player.id
    player_exists = skins_col.find_one({'user_id': player_id})
    if not player_exists:
        skins_col.insert_one({
            'username': osu_name,
            'user_id': player_id,
            'skin_id': skin_id
        })
    else:
        skins_col.update_one({
            'user_id': player_id
        }, {
            '$set': {
                'skin_id': skin_id
            }
        }, upsert=False)
    await interaction.response.send_message(f"Skin {skin_id} successfully added for {osu_name}.")


client.run(os.environ['BOT_TOKEN'])
