import discord
from discord.ext import commands
import json
import random
import asyncio
from discord import FFmpegPCMAudio


intents = discord.Intents.default()
intents.reactions = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author.id == 116706268592209920 : #zweistar's id
        random_number = random.randint(1, 100)
        if random_number == 1:
            insult = await message.channel.send(f"shut up bitch")
            await asyncio.sleep(2)
            await insult.delete()

    with open('positive_qualifiers.txt', 'r') as f:
        qualifier_list = [word.strip() for word in f.readlines()]
        for word in qualifier_list:
            if message.content.startswith("I "+word):
                await silent_add("I "+word, message, 'like')

    with open('negative_qualifiers.txt', 'r') as f:
        qualifier_list = [word.strip() for word in f.readlines()]
        for word in qualifier_list:
            if message.content.startswith("I "+word):
                await silent_add("I "+word, message, 'dislike')

    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel:  # Check if the member joined a voice channel
        #if member.id == 257523633000284160:  # Check if the member is the specified user
            channel = after.channel
            voice_channel = await channel.connect()

            # Play a sound (replace 'sound_file.mp3' with the actual sound file)
            voice_channel.play(FFmpegPCMAudio('sound_file_1.mp3', executable="./ffmpeg/bin/ffmpeg.exe"))

            # Disconnect after playing the sound
            while voice_channel.is_playing():
                await asyncio.sleep(1)
            await voice_channel.disconnect()

@bot.command()
async def DYL(ctx, *, thingy):
    thing = thingy.replace('?','')
    existing_poll = get_poll_by_thing('poll_list.json',thing.lower())

    if existing_poll:
        # Edit the existing poll entry
        poll_message = await ctx.send(embed=get_poll_embed(thing.lower()))
        await poll_message.add_reaction('👍')
        await poll_message.add_reaction('👎')
        await ctx.send(f"Vote now!")
    else:
        # Create a new poll entry
        poll = {'thing': thing.lower()}
        add_poll('poll_list.json',poll)
        with open('poll_list.txt', 'a') as f:
            f.write(thing.lower() + '\n')
        poll_message = await ctx.send(embed=get_poll_embed(thing.lower()))
        await poll_message.add_reaction('👍')
        await poll_message.add_reaction('👎')

        await ctx.send(f"Created a new poll for {thing.lower()}.\nVote now!")

@bot.command()
async def likelist(ctx):
    await ctx.send(file=discord.File('poll_list.txt'))

@bot.event
async def on_raw_reaction_add(payload):
    emoji = payload.emoji.name
    user_id = payload.user_id

    if user_id == bot.user.id:
        return  # Ignore reactions from the bot itself

    # Use thing as the key
    thingy = await get_thing_from_reaction(bot, payload)
    thing = thingy.replace('?','')
    existing_poll = get_poll_by_thing('poll_list.json',thing.lower())

    if existing_poll:
        user_vote = find_vote('user_votes.json',thing.lower(),user_id)
        if emoji == '👍':
            if user_vote:
                if user_vote.get('vote')== 'dislike':
                    update_dictionary_value('user_votes.json','user_id',user_id,'thing',thing.lower(),'vote','like')
            else:
                vote = {'thing': thing.lower(), 'vote': 'like', 'user_id': user_id}
                add_poll('user_votes.json', vote)
                
        elif emoji == '👎':
            if user_vote:
                if user_vote['vote'] == 'like':
                    update_dictionary_value('user_votes.json','user_id',user_id,'thing',thing.lower(),'vote','dislike')
            else:
                vote = {'thing': thing.lower(), 'vote': 'dislike', 'user_id': user_id}
                add_poll('user_votes.json', vote)
                
@bot.event
async def on_raw_reaction_remove(payload):
    emoji = payload.emoji.name
    user_id = payload.user_id

    if user_id == bot.user.id:
        return  # Ignore reactions from the bot itself

    # Use thing as the key
    thingy = await get_thing_from_reaction(bot, payload)
    thing = thingy.replace('?','')
    existing_poll = get_poll_by_thing('poll_list.json',thing.lower())
    if existing_poll:
        user_vote = find_vote('user_votes.json',thing.lower(),user_id)
        if emoji == '👍':
            if user_vote:
                if user_vote['vote'] == 'like':
                    remove_poll('user_votes.json',user_vote)
                
        elif emoji == '👎':
            if user_vote:
                if user_vote['vote'] == 'dislike':
                    remove_poll('user_votes.json',user_vote)

@bot.command()
async def doeslike(ctx, user: discord.Member, *, thingy):
    thing = thingy.replace('?','')
    poll = get_poll_by_thing('poll_list.json',thing.lower())
    if poll:
        user_vote = find_vote('user_votes.json',thing.lower(),user.id)
        if user_vote:
            vote = user_vote['vote']
            await ctx.send(f"{user} {vote}s {thing.lower()}.")
        else:
            await ctx.send(f"{user} has not voted on the poll about {thing}.")
    else:
        await ctx.send(f"No poll found for {thing.lower()}.")

async def silent_add(qualifier, message, alignment):
    thing = message.content[len(qualifier):].strip().replace('?', '').replace('.', '').replace('!','')
    existing_poll = get_poll_by_thing('poll_list.json',thing.lower())
    user_id = message.author.id
    if existing_poll:
        user_vote = find_vote('user_votes.json',thing.lower(),user_id)
        if user_vote:
            if user_vote['vote'] != alignment:
                await respond_with("you're lying",message)
        else:
            vote = {'thing': thing.lower(), 'vote': alignment, 'user_id': user_id}
            add_poll('user_votes.json', vote)
    else:
        poll = {'thing': thing.lower()}
        add_poll('poll_list.json',poll)
        with open('poll_list.txt', 'a') as f:
            f.write(thing.lower() + '\n')
        await silent_add(qualifier, message, alignment)

async def respond_with(response, message):
    await message.channel.send(f""+response)

def get_poll_by_thing(path,thing):
    try:
        with open(path, 'r') as f:
            polls = json.load(f)
    except json.JSONDecodeError:
        polls = []
    
    for poll in polls:
        if thing in poll.values():
            return poll
    return None

def add_poll(path,poll):
    try:
        with open(path, 'r') as f:
            polls = json.load(f)
    except json.JSONDecodeError:
        polls = []
    polls.append(poll)
    with open(path, 'w') as file:
        json.dump(polls, file, indent=2)

def remove_poll(path,user_vote):
    try:
        with open(path, 'r') as f:
            polls = json.load(f)
    except json.JSONDecodeError:
        polls = []
    for item in polls:
        if user_vote == item:
            polls.remove(item)
            break  # Stop searching once the first matching dictionary is found
    with open(path, 'w') as file:
        json.dump(polls, file, indent=2)

def update_dictionary_value(path, condition_key, condition_value, second_condition_key,second_condition_value, new_value_key, new_value):
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        data = []
    for item in data:
        if item.get(condition_key) == condition_value and item.get(second_condition_key) == second_condition_value:
            item[new_value_key] = new_value
            break  # Stop searching once the first matching dictionary is found
    with open(path, 'w') as file:
        json.dump(data, file, indent=2)

def find_vote(path,thing,user_id):
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        data = []
    for item in data:
        if item.get('thing') == thing and item.get('user_id') == user_id: 
            return item

def get_poll_embed(thing):
    return discord.Embed(title=f"Do you like {thing}?", description="React with 👍 or 👎 to vote!", color=0x008080)

async def get_thing_from_reaction(bot, payload):
    
    message_id = payload.message_id
    channel = bot.get_channel(payload.channel_id)
    message = await channel.fetch_message(message_id)
    return message.embeds[0].title.split("Do you like ", 1)[1].split("?", 1)[0]

bot.run('MTE5MzQ3NTUxMDAzMDgzNTcyMw.GzO7lw.nxqnaiFf5-SsJK_qiphXVhlt_gSkWoDuZxDgo0')
