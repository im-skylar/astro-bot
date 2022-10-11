#/bin/python3

import os
import datetime
import discord
from discord.ext import tasks
import requests
import json
import locale

# Set your locale here
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
# Set to the some new moon in the past, the more recent, the more accurate the moon phase is
new_moon = datetime.datetime(2022, 8, 27, 4, 17)
# Set the latitude and longitude of your city
lat = "40.7648"
lon = "-73.9808"
# The hour of the daily digest
digest_hour = 13
# The channel name to send the digest to
digest_channel = "astro-bot"
# If you want a language other than english also remember to change the strings beginning in line 67


if not "DISCORD_KEY" in os.environ or not "OPENWEATHER_KEY" in os.environ:
    print("You need to specify the API keys in the DISCORD_KEY and OPENWEATHER_KEY environment variables")
    quit()

dc_key = os.environ["DISCORD_KEY"]
ow_key = os.environ["OPENWEATHER_KEY"]

def lunar_cycle(dt):
    cycle = 29.53058770576
    day = 24 * 60 * 60
    lunarsecs = cycle * day

    #first = datetime.datetime(2000, 1, 6, 18, 14, tzinfo=datetime.timezone.utc)
    first = new_moon

    delta = dt - first

    return (delta.total_seconds() % lunarsecs) / lunarsecs

def moon_emoji(phase):
    if phase < 0.0339 or phase > 0.9661:
        return ":new_moon_with_face:"
    if phase < 0.2161:
        return ":waxing_crescent_moon:"
    if phase < 0.2839:
        return "first_quarter_moon:"
    if phase < 0.4661:
        return ":waxing_gibbous_moon:"
    if phase < 0.5339:
        return ":full_moon:"
    if phase < 0.7161:
        return ":waning_gibbous_moon:"
    if phase < 0.7839:
        return ":last_quarter_moon:"
    if phase < 0.9661:
        return ":waning_crescent_moon:"

def openweather_call():
    res = requests.get("https://api.openweathermap.org/data/2.5/forecast", {"lat": lat, "lon": lon, "appid": ow_key, "units": "metric"})

    return res

def get_weather(res):
    if not res.ok:
        return [discord.Embed(title="Can't connect to the OpenWeatherMap API", colour=discord.Colour.red())]

    try:
        weather = json.loads(res.content)
        #with open("owm_response.json") as f:
        #    weather = json.loads(f.read())
    except json.JSONDecodeError:
        with open("owm_response.json", "w") as f:
            f.write(res.content)
        return [discord.Embed(title="Couldn't parse OpenWeatherMaps response. Saved to file", colour=discord.Colour.red())]
    
    days = {}

    for datapoint in weather["list"]:
        dt = datetime.datetime.fromtimestamp(datapoint["dt"])
        if dt.hour < 19:
            continue

        if datapoint["clouds"]["all"] > 30:
            continue
        
        if dt.day in days:
            days[dt.day].append(datapoint)
        else:
            days[dt.day] = [datapoint]
    
    result = []
    for day in days:
        day = days[day]
        dt = datetime.datetime.fromtimestamp(day[0]["dt"])
        sunset = datetime.datetime.fromtimestamp(weather["city"]["sunset"]).strftime("%H:%M")
        emb = discord.Embed(title=f":telescope:  Good astronomy weather on {dt.strftime('%A, the %d.%m.%y')}", description=f"Moon: {moon_emoji(lunar_cycle(dt))}\nSunset: {sunset}", timestamp=dt, colour=discord.Colour.fuchsia())

        for time in day:
            hour = datetime.datetime.fromtimestamp(time["dt"]).hour
            temp = time["main"]["temp"]
            cloudiness = time["clouds"]["all"]
            wind = time["wind"]["speed"]
            gust = time["wind"]["gust"]
            pop = time["pop"]

            emb.add_field(name=f":clock3:  {hour} o'Clock", value=f":thermometer: Temperature: {temp}°C\n:cloud: Cloudiness: {cloudiness}%\n:wind_blowing_face: Wind Speed: {wind}km/h\n:cloud_tornado: Gusts: {gust}km/h\n:cloud_rain: Rain probability: {int(pop*100)}%", inline=False)

        result.append(emb)
    
    return result




intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    astro_digest.start()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('!astro'):
        emb = get_weather(openweather_call())
        await message.channel.send(embeds=emb)
    
    """if message.content.startswith('!debug'):
        await message.channel.send(" ".join(x.name for x in client.guilds))
        await message.channel.send(" ".join(x.name for x in message.guild.channels))
        print(datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo.tzname(datetime.datetime.now()))
        print("Debug :)")"""

@tasks.loop(time=datetime.time(digest_hour, 0, tzinfo=datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo))
async def astro_digest():
    print("Digest!")
    for guild in client.guilds:
        emb = get_weather(openweather_call())
        for channel in guild.channels:
            if channel.name == digest_channel:
                await channel.send(embeds=emb)


client.run(dc_key)
