from discord.ext import commands, tasks
from discord import app_commands
import discord
from urlextract import URLExtract
import datetime, time, logging

log = logging.getLogger('playlist')

utc = datetime.timezone.utc
times = [
    datetime.time(hour=8, tzinfo=utc),
    datetime.time(hour=8, minute=15, tzinfo=utc),
    datetime.time(hour=8, minute=30, tzinfo=utc),
    datetime.time(hour=8, minute=30, tzinfo=utc),
]


class PlaylistManagement(commands.Cog, name='Playlist management'):
    def __init__(self, bot):
        self.bot = bot
        self.re = URLExtract()
        self.check_for_playlist_update.start()
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
            i = 0
            for url in self.re.gen_urls(message.content):
                if 'open.spotify.com/track/' in url:
                    track_added = self.bot.manager.add_to_playlist(message.author.id, url)
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

async def setup(bot):
    await bot.add_cog(PlaylistManagement(bot))