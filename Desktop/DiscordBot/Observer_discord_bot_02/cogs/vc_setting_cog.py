# cogs/voice_chat/vc_setting_cog.py
import discord
from discord.ext import commands, tasks
import asyncio

class VCSettingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.auto_vc_channels = set()  # 自動参加対象のVC ID
        self.connected_vcs = {}        # VCごとの VoiceClient

    @commands.command(name="add_auto_vc")
    async def add_auto_vc(self, ctx: commands.Context, channel: discord.VoiceChannel):
        """対象VCを自動参加リストに追加"""
        self.auto_vc_channels.add(channel.id)
        await ctx.send(f"✅ 自動参加対象VCに {channel.name} を追加しました。")

    @commands.command(name="remove_auto_vc")
    async def remove_auto_vc(self, ctx: commands.Context, channel: discord.VoiceChannel):
        """対象VCから削除"""
        self.auto_vc_channels.discard(channel.id)
        await ctx.send(f"⚠️ 自動参加対象VCから {channel.name} を削除しました。")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before, after):
        # Bot自身の移動は無視
        if member.bot:
            return

        # VC入室チェック
        if after.channel and after.channel.id in self.auto_vc_channels:
            vc_id = after.channel.id
            if vc_id not in self.connected_vcs:
                # Botがまだ接続していなければ join
                try:
                    vc_client = await after.channel.connect()
                    self.connected_vcs[vc_id] = vc_client
                    print(f"Bot joined VC {after.channel.name}")
                except Exception as e:
                    print(f"VC join failed: {e}")

        # VC退室チェック
        if before.channel and before.channel.id in self.auto_vc_channels:
            vc = before.channel
            if len([m for m in vc.members if not m.bot]) == 0:
                # 人間が誰もいなければ Botが退出
                vc_id = vc.id
                if vc_id in self.connected_vcs:
                    try:
                        await self.connected_vcs[vc_id].disconnect()
                        print(f"Bot left VC {vc.name} (empty)")
                        del self.connected_vcs[vc_id]
                    except Exception as e:
                        print(f"VC leave failed: {e}")
