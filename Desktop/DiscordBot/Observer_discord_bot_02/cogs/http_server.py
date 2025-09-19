import os, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from discord.ext import commands

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

class HttpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        threading.Thread(target=run_server, daemon=True).start()

async def setup(bot):
    await bot.add_cog(HttpCog(bot))
