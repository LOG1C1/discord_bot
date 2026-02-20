import discord
from discord.ext import commands
from discord import app_commands
import datetime
import config

class Suggestions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    # ==================== ESEMÉNYEK ====================
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bot üzeneteit ne figyelje
        if message.author.bot:
            return
        
        # Csak az ötletek csatornában működjön
        if message.channel.id != config.SUGGESTIONS_CHANNEL_ID:
            return
        
        # Törölje az eredeti üzenetet
        try:
            await message.delete()
        except discord.Forbidden:
            print("Nincs jogosultság üzenet törléséhez!")
            return
        
        # Embed létrehozása
        embed = discord.Embed(
            title="💡 Új Javaslat",
            description=f"**Javaslat:**\n{message.content}",
            color=config.COLOR_DEFAULT,
            timestamp=datetime.datetime.now()
        )
        
        # Szerző adatai
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.display_avatar.url
        )
        
        # Kép csatolása ha van
        if message.attachments:
            embed.set_image(url=message.attachments[0].url)
        
        # Szavazatok állapota
        embed.add_field(
            name="🗳️ Szavazatok állása:",
            value=f"{config.EMOJI_UPVOTE} Jó ötlet: 0\n{config.EMOJI_DOWNVOTE} Rossz ötlet: 0",
            inline=False
        )
        
        # Beküldés ideje és beküldő
        embed.add_field(
            name="📅 Beküldés ideje",
            value=f"<t:{int(message.created_at.timestamp())}:F>",
            inline=True
        )
        embed.add_field(
            name="👤 Beküldő",
            value=f"{message.author.mention}",
            inline=True
        )
        
        # Egyedi azonosító (thread létrehozáshoz)
        suggestion_id = f"sugg_{message.id}"
        embed.add_field(
            name="🆔 Azonosító",
            value=f"`{suggestion_id}`",
            inline=False
        )
        
        # Üzenet küldése
        suggestion_msg = await message.channel.send(embed=embed)
        
        # Reakciók hozzáadása
        await suggestion_msg.add_reaction(config.EMOJI_UPVOTE)
        await suggestion_msg.add_reaction(config.EMOJI_DOWNVOTE)
        
        # Gombok hozzáadása
        view = SuggestionButtons(self.bot, suggestion_msg, message.author)
        await suggestion_msg.edit(view=view)
        
        # Thread létrehozása a megbeszéléshez
        try:
            thread = await suggestion_msg.create_thread(
                name=f"Megbeszélés: {message.author.display_name[:20]}",
                auto_archive_duration=1440  # 1 nap
            )
            await thread.send(f"📢 {message.author.mention} Megbeszélés a javaslatról!")
        except discord.Forbidden:
            pass
    
    # ==================== SLASH COMMANDOK ====================
    
    @app_commands.guilds(discord.Object(id=config.GUILD_ID))
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="javaslat_állapot", description="Javaslat állapotának módosítása (Csak admin!)")
    @app_commands.choices(állapot=[
        app_commands.Choice(name="✅ Elfogadás", value="approved"),
        app_commands.Choice(name="❌ Elutasítás", value="denied"),
        app_commands.Choice(name="🟡 Átgondoljuk", value="pending")
    ])
    async def set_status(self, interaction: discord.Interaction, üzenet_id: str, állapot: app_commands.Choice[str]):
        """Javaslat állapotának módosítása"""
        try:
            channel = self.bot.get_channel(config.SUGGESTIONS_CHANNEL_ID)
            message = await channel.fetch_message(int(üzenet_id))
            
            embed = message.embeds[0]
            
            if állapot.value == "approved":
                embed.color = discord.Color(config.COLOR_APPROVED)
                embed.title = "✅ Elfogadott Javaslat"
            elif állapot.value == "denied":
                embed.color = discord.Color(config.COLOR_DENIED)
                embed.title = "❌ Elutasított Javaslat"
            else:
                embed.color = discord.Color(config.COLOR_PENDING)
                embed.title = "🟡 Átgondolandó Javaslat"
            
            await message.edit(embed=embed)
            await interaction.response.send_message(f"✅ Javaslat állapota frissítve: **{állapot.name}**", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Hiba: {e}", ephemeral=True)

class SuggestionButtons(discord.ui.View):
    def __init__(self, bot: commands.Bot, message: discord.Message, author: discord.Member):
        super().__init__(timeout=None)
        self.bot = bot
        self.message = message
        self.author = author
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Ellenőrizzük, hogy admin-e
        admin_role = interaction.guild.get_role(config.ADMIN_ROLE_ID)
        if admin_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Csak rendszergazdák használhatják ezeket a gombokat!", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="Jó ötlet", style=discord.ButtonStyle.success, emoji="👍", custom_id="upvote_btn")
    async def upvote_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.message.embeds[0]
        
        # Szavazatok kinyerése és frissítése
        for i, field in enumerate(embed.fields):
            if field.name == "🗳️ Szavazatok állása:":
                lines = field.value.split('\n')
                current_up = int(lines[0].split(':')[1].strip())
                new_up = current_up + 1
                lines[0] = f"{config.EMOJI_UPVOTE} Jó ötlet: {new_up}"
                embed.set_field_at(i, name=field.name, value='\n'.join(lines), inline=field.inline)
                break
        
        await self.message.edit(embed=embed)
        await interaction.response.send_message("✅ Szavazat rögzítve!", ephemeral=True)
    
    @discord.ui.button(label="Rossz ötlet", style=discord.ButtonStyle.danger, emoji="👎", custom_id="downvote_btn")
    async def downvote_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.message.embeds[0]
        
        for i, field in enumerate(embed.fields):
            if field.name == "🗳️ Szavazatok állása:":
                lines = field.value.split('\n')
                current_down = int(lines[1].split(':')[1].strip())
                new_down = current_down + 1
                lines[1] = f"{config.EMOJI_DOWNVOTE} Rossz ötlet: {new_down}"
                embed.set_field_at(i, name=field.name, value='\n'.join(lines), inline=field.inline)
                break
        
        await self.message.edit(embed=embed)
        await interaction.response.send_message("✅ Szavazat rögzítve!", ephemeral=True)
    
    @discord.ui.button(label="Elfogadás", style=discord.ButtonStyle.success, emoji="✅", custom_id="approve_btn")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.message.embeds[0]
        embed.color = discord.Color(config.COLOR_APPROVED)
        embed.title = "✅ Elfogadott Javaslat"
        
        await self.message.edit(embed=embed, view=None)
        await interaction.response.send_message("✅ Javaslat elfogadva!", ephemeral=True)
    
    @discord.ui.button(label="Elutasítás", style=discord.ButtonStyle.danger, emoji="❌", custom_id="deny_btn")
    async def deny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.message.embeds[0]
        embed.color = discord.Color(config.COLOR_DENIED)
        embed.title = "❌ Elutasított Javaslat"
        
        await self.message.edit(embed=embed, view=None)
        await interaction.response.send_message("❌ Javaslat elutasítva!", ephemeral=True)
    
    @discord.ui.button(label="Átgondoljuk", style=discord.ButtonStyle.primary, emoji="🟡", custom_id="pending_btn")
    async def pending_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.message.embeds[0]
        embed.color = discord.Color(config.COLOR_PENDING)
        embed.title = "🟡 Átgondolandó Javaslat"
        
        await self.message.edit(embed=embed)
        await interaction.response.send_message("🟡 Javaslat átgondolás alatt!", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Suggestions(bot))