# cogs/vc_highlight_cog.py
import discord
from discord.ext import commands, tasks
import asyncio
import numpy as np
import wave
import io
from collections import deque
import time

THRESHOLD = 0.05  # 音量閾値（0～1の範囲）
PRE_BUFFER_SECONDS = 17
POST_BUFFER_SECONDS = 3
SAMPLE_RATE = 48000  # Discord PCM は 48kHz
CHANNELS = 2  # ステレオ
SAMPLES_PER_FRAME = 960  # Discord voice frame: 20ms

class VCHighlightCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ring_buffer = deque(maxlen=int(PRE_BUFFER_SECONDS * SAMPLE_RATE / SAMPLES_PER_FRAME))
        self.recording = False
        self.post_frames_remaining = 0
        self.audio_queue = deque()
        self.vc = None
        self.listen_task = None
        self.target_channel_id = None  # WAV送信先チャンネル

    @commands.command(name="set_highlight_channel")
    async def set_channel(self, ctx: commands.Context):
        self.target_channel_id = ctx.channel.id
        await ctx.send(f"✅ このチャンネルにハイライト音声を送信します。")

    @commands.command(name="join_vc")
    async def join_vc(self, ctx: commands.Context):
        if ctx.author.voice:
            self.vc = await ctx.author.voice.channel.connect()
            self.listen_task = asyncio.create_task(self.listen_audio())
            await ctx.send("✅ VCに接続しました。")
        else:
            await ctx.send("⚠️ ボイスチャンネルに入っているユーザーがいません。")

    @commands.command(name="leave_vc")
    async def leave_vc(self, ctx: commands.Context):
        if self.vc:
            await self.vc.disconnect()
            self.vc = None
            if self.listen_task:
                self.listen_task.cancel()
            await ctx.send("✅ VCから切断しました。")
        else:
            await ctx.send("⚠️ VCに接続していません。")

    async def listen_audio(self):
        """
        擬似実装: Discord voice receive APIが必要
        ここではPCMデータが frame として得られる前提
        """
        while True:
            await asyncio.sleep(0.02)  # 20msごと
            frame = self.get_audio_frame()  # 自作関数でPCMデータ取得
            self.ring_buffer.append(frame)

            # RMSで音量判定
            rms = np.sqrt(np.mean(np.array(frame, dtype=np.float32)**2))
            if rms >= THRESHOLD and not self.recording:
                self.recording = True
                self.post_frames_remaining = int(POST_BUFFER_SECONDS * SAMPLE_RATE / SAMPLES_PER_FRAME)
                self.audio_queue.extend(self.ring_buffer)  # 前バッファをコピー
                print(f"トリガー検出: RMS={rms:.3f}")

            if self.recording:
                self.audio_queue.append(frame)
                self.post_frames_remaining -= 1
                if self.post_frames_remaining <= 0:
                    await self.save_and_send()
                    self.recording = False
                    self.audio_queue.clear()

    async def save_and_send(self):
        """
        WAVに保存して指定チャンネルに送信
        """
        if not self.target_channel_id:
            print("送信先チャンネル未設定")
            return
        channel = self.bot.get_channel(self.target_channel_id)
        if not channel:
            print("送信先チャンネルが見つかりません")
            return

        wav_buffer = io.BytesIO()
        wf = wave.open(wav_buffer, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16bit
        wf.setframerate(SAMPLE_RATE)
        # PCMデータを結合して書き込み
        for frame in self.audio_queue:
            wf.writeframes(frame)
        wf.close()
        wav_buffer.seek(0)
        await channel.send(file=discord.File(fp=wav_buffer, filename=f"highlight_{int(time.time())}.wav"))
        print("✅ ハイライト音声を送信しました")

    def get_audio_frame(self):
        """
        ダミー関数: 実際には discord.py VoiceClient receive を使う
        """
        # ここでは無音のステレオPCM 960サンプル
        return (b'\x00\x00' * SAMPLES_PER_FRAME * CHANNELS)
