from discord.ext import commands, tasks
from discord import app_commands
import discord
from urlextract import URLExtract
import datetime, time, logging, queue

log = logging.getLogger('playlist')

utc = datetime.timezone.utc
times = [
    datetime.time(hour=8, tzinfo=utc),
    datetime.time(hour=8, minute=15, tzinfo=utc),
    datetime.time(hour=8, minute=30, tzinfo=utc),
    datetime.time(hour=8, minute=30, tzinfo=utc),
]

# ids and commands for other bots who get spotify links
# will wait 5 seconds and capture the first bot-posted spotify link
# and associate it with whomever last did one of these commands
spotify_bot_ids = [356268235697553409, 128822128072982528] 
spotify_bot_commands = ['.s', '.spotify',]

class PlaylistManagement(commands.Cog, name='Playlist management'):
    def __init__(self, bot):
        self.bot = bot
        self.re = URLExtract()
        self.check_for_playlist_update.start()
        # handles the use of other bots
        self.command_waiting = queue.SimpleQueue() # queue the IDs of users waiting for bot
        self.waiting_tasks = [] # holds task which will kill queue entry on timeout
        log.info('Cog loaded')

    @app_commands.command(name='add', description='Add a Spotify track to the playlist')
    async def add(self, inter: discord.Interaction, spotify_url: str) -> None:
        if 'open.spotify.com/track/' in spotify_url:
            track_added = self.bot.manager.add_to_playlist(inter.user.id, spotify_url)
            if track_added:
                await inter.response.send_message('Track added!', ephemeral=True)
            else:
                await inter.response.send_message("Track not added: it's already in the playlist!", ephemeral=True)
        else:
            await inter.response.send_message('Unrecognized link! Please provide a Spotify track URL.', ephemeral=True)

    @commands.command(name='new_playlist', description='Switch to a new playlist')
    @commands.is_owner()
    async def new_playlist(self, ctx: commands.Context, spotify_url: str = None) -> None:
        if spotify_url is None:
            self.bot.manager.swap_to_new_playlist()
            await ctx.reply(f'New playlist created, check it out: {self.bot.manager.get_playlist_link()}', ephemeral=True)
            return
        # try to load in the provided URL: get the playlist ID from it
        split = spotify_url.split('/')
        try:
            plidx = split.index('playlist')
        except ValueError:
            await ctx.reply('Invalid playlist URL', ephemeral=True)
            return
        playlist_id = split[plidx + 1]
        try:
            qidx = playlist_id.index('?')
            playlist_id = playlist_id[:qidx]
        except ValueError:
            pass
        self.bot.manager.create_json_from_existing_playlist(playlist_id)
        await ctx.reply(f'Playlist loaded: {self.bot.manager.get_playlist_link()}', ephemeral=True)

    @commands.hybrid_command(name="playlist", description='Get the current playlist', aliases=['p','pl'])
    async def get_playlist(self, ctx: commands.Context[commands.Bot]) -> None:
        await ctx.reply(f'Current playlist URL: {self.bot.manager.get_playlist_link()}', ephemeral=(ctx.prefix == '/'))

    @commands.Cog.listener()
    async def on_message(self, message):
        channel = message.channel
        if channel.id == self.bot.config['watch_channel']:
            if message.content.split(' ')[0] in spotify_bot_commands:
                self.command_waiting.put(message.author.id)
                self.start_waiting()
                return # ignore commands for other bots
            i = 0
            for url in self.re.gen_urls(message.content):
                if 'open.spotify.com/track/' in url:
                    if (message.author.id in spotify_bot_ids) and (not self.command_waiting.empty()):
                        self.waiting_tasks[0].cancel()
                        logged_id = self.command_waiting.get_nowait()
                        log.info(f'Track {url} assigned to {logged_id} rather than bot ID {message.author.id}')
                    else:
                        logged_id = message.author.id
                    track_added = self.bot.manager.add_to_playlist(logged_id, url)
                    # can do something with this bool if needed

    @tasks.loop(time=times)
    async def check_for_playlist_update(self):
        creation_time = self.bot.manager.parser.creation_time
        current_time = int(time.time())
        ndays = 20
        delta = (current_time - creation_time)//86400
        if datetime.datetime.now().day != 1:
            log.debug("Check for playlist update loop ran but it's not the first")
        elif delta < ndays:
            log.debug(f"It's been {delta} days since the last playlist so a new one is not yet created")
        else:
            channel = await self.bot.fetch_channel(self.bot.config['watch_channel'])
            oldlink = self.bot.manager.get_playlist_link()
            self.bot.manager.swap_to_new_playlist()
            newlink = self.bot.manager.get_playlist_link()
            await channel.send(f'🎉 **NEW PLAYLIST TIME!!!** Check out the old one [here](<{oldlink}>), new songs will be added to {newlink}')

    def start_waiting(self): # spawns a task which monitors for timeouts
        new_task = tasks.loop(seconds=5, count=1)(self.wait_to_pop_queue)
        new_task.after_loop(self.clear_waiting)
        new_task.start()
        self.waiting_tasks.append(new_task)

    async def wait_to_pop_queue(self):
        # this runs immediately as a spotify command is called
        log.debug(f'Waiting for other bot, queue length = {self.command_waiting.qsize()}, {len(self.waiting_tasks)} tasks pending')

    async def clear_waiting(self): 
        # don't pop if we successfully popped above
        if self.waiting_tasks[0].is_being_cancelled():
            log.info('Timeout canceled, link found')
            del self.waiting_tasks[0]
            return
        # remove from the queue if we timeout waiting for a bot request
        if not self.command_waiting.empty():
            deleting = self.command_waiting.get_nowait()
            log.warning(f'Timeout, {deleting} from queue')
        else:
            log.error('Timeout requested but queue empty')
        del self.waiting_tasks[0]

async def setup(bot):
    await bot.add_cog(PlaylistManagement(bot))

