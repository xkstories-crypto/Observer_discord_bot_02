# cogs/http_cog.py
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from discord.ext import commands

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

class HTTPCog(commands.Cog):
    """Render 用のヘルスチェック HTTP サーバー"""
    def __init__(self, bot):
        self.bot = bot
        self.start_server()

    def start_server(self):
        port = int(os.environ.get("PORT", 10000))
        threading.Thread(target=self.run_server, args=(port,), daemon=True).start()

    def run_server(self, port):
        server = HTTPServer(("0.0.0.0", port), Handler)
        server.serve_forever()

async def setup(bot):
    await bot.add_cog(HTTPCog(bot))
