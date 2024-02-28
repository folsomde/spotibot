from discord.ext import commands
import discord
import logging, random, datetime

log = logging.getLogger('stats')


def escape_markdown(text):
    MD_SPECIAL_CHARS = "`*_#"
    for char in MD_SPECIAL_CHARS:
        text = text.replace(char, "\\"+char)
    return text

class Statistics(commands.Cog, name='Statistics'):
    def __init__(self, bot):
        self.bot = bot
        log.info('Cog loaded')

    @commands.hybrid_command(name="lasttrack", description='Get the last track posted for each user (or someone in particular)', aliases=['lt'])
    async def lasttrack(self, ctx: commands.Context[commands.Bot], user: discord.User = None) -> None:
        '''Get the last track posted for each user (or someone in particular)'''
        # handle this easy case first
        if user is not None:
            lasttime = self.bot.manager.parser.get_last_track_time(user.id)
            lasttrack = self.bot.manager.parser.get_last_track_id(user.id)
            if lasttrack is None:
                embed = discord.Embed(title=f"Last track from {user.display_name}", description='No tracks found!',
                                  url = self.bot.manager.get_playlist_link(), color=0x7289da)
            else:
                data = self.bot.manager.sp.get_track_info([lasttrack])['tracks'][0]
                outline = ''
                # outline += escape_markdown(user.display_name)
                # outline += f' added\n'
                outline += f'[' + escape_markdown(data['artists'][0]['name']) + ' / ' + escape_markdown(data['name']) + f']({data["external_urls"]["spotify"]})'
                outline += f', added <t:{lasttime}:R>'
                embed = discord.Embed(title=f"Last track from {user.display_name}", description=outline,
                                  url = self.bot.manager.get_playlist_link(), color=0x7289da)
                embed.set_thumbnail(url=data['album']['images'][0]['url'])
            await ctx.reply(embed=embed, ephemeral=(ctx.prefix == '/'))
            return
        # go into the meat of constructing the table
        senderid = ctx.author.id
        times = self.bot.manager.parser.get_all_last_track_times()
        urls = self.bot.manager.parser.get_all_last_track_ids()
        srt = [(k, urls[k]) for k in sorted(times, key=times.get, reverse=True)]
        big_urls = [t[1] for t in srt[:10]]
        info = self.bot.manager.sp.get_track_info(big_urls)['tracks']
        output = ''
        found_user = False
        for i, tup in enumerate(srt[:10]):
            uid, url = tup
            thisline = f'{i+1}.'
            user = await self.bot.fetch_user(uid)
            thisline += f'  '
            thisline += '<@{uid}>' if user is None else escape_markdown(user.display_name)
            thistrack = info[i]
            thisline += f' — [' + escape_markdown(thistrack['artists'][0]['name']) + ' / ' + escape_markdown(thistrack['name']) + f']({thistrack["external_urls"]["spotify"]})'
            if uid == senderid:
                found_user = True
                thisline = f'**{thisline}**'
            output += thisline +'\n'
        if not found_user:
            try:
                user_idx = [s[0] for s in srt].index(senderid) + 1
                thisurl = [urls[senderid],]
                artists, tracks = self.bot.manager.sp.get_track_info(thisurl)
                addl_text = escape_markdown(artists[0]) + ' / ' + escape_markdown(tracks[0])
            except ValueError:
                user_idx = len(srt) + 1
                addl_text = 'No submissions!'
            output += f'**{user_idx}. {escape_markdown(ctx.author.display_name)} — {addl_text}**'
        embed = discord.Embed(title=f"Songs of Sandyland", description=output, 
                              timestamp = datetime.datetime.utcfromtimestamp(self.bot.manager.parser.creation_time), 
                              url = self.bot.manager.get_playlist_link(), color=0x7289da)
        # embed.set_footer(text=f'{total_count} total tracks')
        await ctx.reply(embed=embed, ephemeral=(ctx.prefix == '/'))

    @commands.hybrid_command(name="leaderboard", description='See who has posted the most songs so far', aliases=['lb'])
    async def leaderboard(self, ctx: commands.Context[commands.Bot]) -> None:
        '''See who has posted the most songs so far'''
        senderid = ctx.author.id
        counts = self.bot.manager.parser.get_all_track_counts()
        total_count = sum(cts for cts in counts.values())
        srt = [(k, counts[k]) for k in sorted(counts, key=counts.get, reverse=True)]
        output = ''
        found_user = False
        for i, tup in enumerate(srt[:10]):
            uid, playcount = tup
            thisline = ''
            if i == 0:
                thisline +='👑'
            else:
                thisline += f'{i+1}.'
            user = await self.bot.fetch_user(uid)
            thisline += f'  '
            thisline += '<@{uid}>' if user is None else escape_markdown(user.display_name)
            thisline += f' — {playcount} tracks'
            if uid == senderid:
                found_user = True
                thisline = f'**{thisline}**'
            output += thisline +'\n'
        if not found_user:
            try:
                user_idx = [s[0] for s in srt].index(senderid) + 1
                playcount = counts[senderid]
            except ValueError:
                user_idx = len(srt) + 1
                playcount = 0
            output += f'**{user_idx}. {escape_markdown(ctx.author.display_name)} — {playcount} tracks**'
        embed = discord.Embed(title=f"Songs of Sandyland", description=output, 
                              timestamp = datetime.datetime.utcfromtimestamp(self.bot.manager.parser.creation_time), 
                              url = self.bot.manager.get_playlist_link(), color=0x7289da)
        embed.set_footer(text=f'{total_count} total tracks')
        await ctx.reply(embed=embed, ephemeral=(ctx.prefix == '/'))

    @commands.hybrid_command(name="random", description='Get a random song from the playlist (optionally specifying a user)', aliases=['r'])
    async def get_random_song(self, ctx: commands.Context[commands.Bot], user: discord.User = None) -> None:
        '''Get a random song from the playlist (optionally specifying a user)'''
        tracks = self.bot.manager.parser.get_all_tracks()
        songbank = []
        if user is None:
            list(map(songbank.extend, tracks.values())) 
        else:
            if user.id not in tracks:
                await ctx.reply(f'No tracks found from {user.display_name}', ephemeral=(ctx.prefix == '/'))
                return
            songbank = tracks[user.id]
        await ctx.reply(f'https://open.spotify.com/track/{random.choice(songbank)}', ephemeral=(ctx.prefix == '/'))

async def setup(bot):
    await bot.add_cog(Statistics(bot))