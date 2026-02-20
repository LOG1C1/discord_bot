import discord
from discord.ext import commands
import config

class SuggestionBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
    
    async def setup_hook(self):
        # Cog betöltése
        await self.load_extension("cogs.suggestions")
        print("✅ Suggestions cog betöltve!")
        
        # Slash commandok szinkronizálása
        try:
            synced = await self.tree.sync(guild=discord.Object(id=config.GUILD_ID))
            print(f"✅ {len(synced)} slash command szinkronizálva!")
        except Exception as e:
            print(f"❌ Hiba a szinkronizáláskor: {e}")
    
    async def on_ready(self):
        print(f"🤖 {self.user} bejelentkezett!")
        print(f"📊 Jelenleg {len(self.guilds)} szerveren vagyok!")

# Bot indítása
bot = SuggestionBot()

if __name__ == "__main__":
    bot.run(config.BOT_TOKEN)