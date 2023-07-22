import discord
from discord.ext import commands, tasks
from discord import File, Forbidden, HTTPException
import asyncio
import logging
import random
from dotenv import load_dotenv
import os
import datetime
import typing
import json
import requests
import torchaudio
from audiocraft.models import MusicGen
from audiocraft.data.audio import audio_write
from pathlib import Path

load_dotenv()
TOKEN = os.getenv('TOKEN')

intents = discord.Intents.all()
intents.message_content = True  # Add any other necessary intents here
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!", "/"), intents=intents)


# Configure logging
logging.basicConfig(level=logging.INFO)

# Set logger to output to console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger = logging.getLogger()
logger.addHandler(console)

# Event triggered when a message is sent
@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Check if the message starts with the command prefix and the command is 'music'
    if message.content.startswith('!music'):
        await bot.process_commands(message)
        print(f'{message.author.id} ran "{message.content}"')
    else:
        print(f'{message.author.id} - "{message.content}"')
        
@bot.event
async def on_connect():
    print('Connected to Discord servers.')

@bot.event
async def on_disconnect():
    print('Disconnected from Discord servers.')

@bot.event
async def on_ready():
    invite_url = discord.utils.oauth_url(bot.user.id)
    logger.info(f'Bot is connected as {bot.user}')
    #await update_status()#

random_descriptions = [
    "Pop dance track with catchy melodies, tropical percussion, and upbeat rhythms, perfect for the beach",
    "A grand orchestral arrangement with thunderous percussion, epic brass fanfares, and soaring strings, creating a cinematic atmosphere fit for a heroic battle",
    "classic reggae track with an electronic guitar solo",
    "earthy tones, environmentally conscious, ukulele-infused, harmonic, breezy, easygoing, organic instrumentation, gentle grooves",
    "lofi slow bpm electro chill with organic samples",
    "drum and bass beat with intense percussions",
    "A dynamic blend of hip-hop and orchestral elements, with sweeping strings and brass, evoking the vibrant energy of the city",
    "violins and synths that inspire awe at the finiteness of life and the universe",
    "80s electronic track with melodic synthesizers, catchy beat and groovy bass",
    "reggaeton track, with a booming 808 kick, synth melodies layered with Latin percussion elements, uplifting and energizing",
    "a piano and cello duet playing a sad chambers music",
    "smooth jazz, with a saxophone solo, piano chords, and snare full drums",
    "a light and cheerly EDM track, with syncopated drums, aery pads, and strong emotions",
    "a punchy double-bass and a distorted guitar riff",
    "acoustic folk song to play during roadtrips: guitar flute choirs",
    "rock with saturated guitars, a heavy bass line and crazy drum break and fills"
]

queue = asyncio.Queue(maxsize=3)

# Load the pretrained model
model = MusicGen.get_pretrained('medium')

@commands.command(description="Music Generation")
async def music(ctx, *, description=None):
    await ctx.message.add_reaction('🎵')
    
    if description is None:
        description = random.choice(random_descriptions)
        no_prompt = await ctx.send("No prompt given, using random prompt.")
        await asyncio.sleep(1)
        await no_prompt.delete()
        await asyncio.sleep(1)
    generating_message = await ctx.send(f"Generating audio ({description}) for {ctx.author.mention} 🎶...")
    
    async def generate_audio(description):

        # Set generation parameters
        model.set_generation_params(duration=15)

        # Check if user has made a payment
        #user_id = str(ctx.author.id)
        #payment_data = None
        #with open('example/Payments.json') as file:
            #data = json.load(file)
            #for payment in data['payments']:
                #if payment['userid'] == user_id:
                    #payment_data = payment
                    #break

        # Generate audio with user-provided description
        #if payment_data:
            #model.set_generation_params(duration=15)  # Set duration to 30 seconds
        descriptions = [description]
        wav = model.generate(descriptions)

        # Save the audio files
        for idx, one_wav in enumerate(wav):
            sanitized_description = "".join(c if c.isalnum() else "_" for c in description)  # Sanitize the description for use in the file name
            while True:
                file_path = f'{ctx.author.id}_{idx}_{sanitized_description}'  # Append user's Discord ID, index, unique ID, and sanitized description
                if not Path(file_path).exists():
                    break
                unique_id += 1
            audio_write(file_path, one_wav.cpu(), model.sample_rate, strategy="loudness", loudness_compressor=True)

        # Send the audio files to the user
        for idx in range(len(wav)):
            file_path = f'{ctx.author.id}_{idx}_{sanitized_description}.wav'  # Use the same unique ID generated earlier
            if Path(file_path).exists():
                file = discord.File(file_path)
                description_embed = f"🎶 {ctx.author.mention} - !music {description} 🎶"
                embed = discord.Embed(description=description_embed)
                embed.set_footer(text='Made by WoahDream', icon_url='https://share.woahlab.com/-H2ksedxri9/')
                await ctx.send(embed=embed, file=file)
                await asyncio.sleep(1)  # Delay between sending each audio file

                # Delete the WAV file from the root folder
                os.remove(file_path)

        await generating_message.delete()  # Delete the "generating" message after all audio files are sent
        await queue.get()
        queue.task_done()

    await queue.put(description)
    if queue.qsize() <= 3:
        asyncio.create_task(generate_audio(await queue.get()))
            
bot.add_command(music)


bot.run(TOKEN)