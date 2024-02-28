import logging, argparse, json, time, asyncio, glob, os
import discord
from discord.ext import commands
from Manager import Manager as man
from cogs.HelpCommand import HelpCommand
#--------------------------------------------------
# SETUP: load in config files, etc.
#--------------------------------------------------
# setup arguments
parser = argparse.ArgumentParser(prog = 'spotibot.py', description='Save spotify links from a discord channel to a monthly playlist.')
parser.add_argument('-o', '--owner', type = int, help ='Discord ID of the bot owner', default = 128822128072982528)
parser.add_argument('-t', '--tokens', type = str, help ='.json file with Discord bot tokens', default = 'APItokens.json')
parser.add_argument('-c', '--config', type = str, help ='.json file with configuration', default = 'bot_config.json')
parser.add_argument('-v', '--verbose', action='count', default=0, dest='verbosity', help ='Set verbosity level (warning, info, debug)')
parser.add_argument("--testing", action='store_true', help="Disable Spotify API calls")
parser.add_argument('--reload', action=argparse.BooleanOptionalAction, default=True)
args = parser.parse_args()

if args.testing:
    args.config = 'test_config.json'
    args.verbosity = 1 if args.verbosity == 0 else args.verbosity

# check verbosity
verb = 0 if args.verbosity < 0 else 2 if args.verbosity > 2 else args.verbosity
logging.basicConfig(level=[logging.WARNING, logging.INFO, logging.DEBUG][verb])
logging.getLogger('SETUP').info(f'Log level set to {["WARNING", "INFO", "DEBUG"][verb]}')

# load in API tokens
with open(args.tokens) as f:
    tokens = json.load(f)
    logging.getLogger('SETUP').info(f'Loaded tokens from {args.tokens}')

# load in bot configuration
with open(args.config) as f:
    config = json.load(f)
    logging.getLogger('SETUP').info(f'Loaded config from {args.config}')
use_spotify = not (args.testing or not config['use_spotify']) 
config['use_spotify'] = use_spotify
logging.getLogger('SETUP').info('Using Spotify API' if use_spotify else 'Not using Spotify API')

# see if we should grab the last playlist
if args.reload:
    list_of_files = glob.glob('playlist_data/*.json')
    json_name = None if not len(list_of_files) else max(list_of_files, key=os.path.getctime)
elif args.testing:
    json_name = 'playlist_data/testing.json'
else:
    json_name = None

#--------------------------------------------------
# BOT
#--------------------------------------------------

intents = discord.Intents(guild_messages=True, guilds=True, guild_reactions=True, message_content=True)
bot = commands.Bot(command_prefix='!', intents=intents, owner_id=args.owner)
bot.config = config
bot.manager = man(config, tokens, json_name = json_name)
# manually add command which will sync the CommandTree
@bot.command()
@commands.is_owner()
async def sync(ctx: commands.Context) -> None:
    """Sync commands with Discord **[stellar only]**"""
    synced = await ctx.bot.tree.sync()
    print(synced)
    await ctx.send(f"Synced {len(synced)} commands globally")

@bot.event
async def on_ready():
    print('Ready!')
    bot.help_command = HelpCommand()
    

async def main():
    async with bot:
        await bot.load_extension("cogs.PlaylistManagement")
        await bot.load_extension("cogs.Statistics")
        await bot.start(tokens['discord_token'])

asyncio.run(main())