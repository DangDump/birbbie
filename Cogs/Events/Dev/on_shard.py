import discord
from discord.ext import commands
from utils.emojis import *
import os


class Shards(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_shard_connect(self, shard: int):
        await self.client.wait_until_ready()
        try:
            channel = await self.client.fetch_channel(
                os.getenv("SHARD_CHANNEL", 1371586445466407012)
            )
            await channel.send(
                content=f" • `{shard}` has connected."
            )
        except discord.Forbidden:
            return

    @commands.Cog.listener()
    async def on_shard_disconnect(self, shard: int):
        await self.client.wait_until_ready()
        try:
            channel = await self.client.fetch_channel(
                os.getenv("SHARD_CHANNEL", 1371586445466407012)
            )
            await channel.send(
                content=f" • `{shard}` has disconnected."
            )
        except discord.Forbidden:
            return


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Shards(client))
