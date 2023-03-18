import discord

from .bing import BingBot, BingBotResponse


def add_command_reset(bot: discord.Bot, bing: BingBot):
    # Reset the conversation and start a new one
    @bot.command(name='reset', description="Reset the conversation")
    async def reset(ctx: discord.ApplicationContext):
        await bing.reset()
        await ctx.respond("Reset the conversion")


def add_command_style(bot: discord.Bot, bing: BingBot):
    # Set the bing chat style: Creative, Balanced, Precise
    chat_style_command_group = bot.create_group("style", "Switch chat style")

    @chat_style_command_group.command(description="Switch chat style to Creative")
    async def creative(ctx: discord.ApplicationContext):
        await bing.switch_style('creative')
        await ctx.respond("Switch chat style to Creative")
        await bot.change_presence(activity=discord.Game('Creative'))

    @chat_style_command_group.command(description="Switch chat style to Balanced")
    async def balanced(ctx: discord.ApplicationContext):
        await bing.switch_style('balanced')
        await ctx.respond("Switch chat style to Balanced")
        await bot.change_presence(activity=discord.Game('Balanced'))

    @chat_style_command_group.command(description="Switch chat style to Precise")
    async def precise(ctx: discord.ApplicationContext):
        await bing.switch_style('precise')
        await ctx.respond("Switch chat style to Precise")
        await bot.change_presence(activity=discord.Game('Precise'))


def listen_on_message_event(bot: discord.Bot, bing: BingBot):
    @bot.event
    async def on_message(message: discord.Message):
        if message.author.bot:
            return
        ctx: discord.ApplicationContext = await bot.get_application_context(message)
        async with ctx.typing():
            bing_resp: BingBotResponse = await bing.converse(message.content)
        await message.reply(format_response_body(bing_resp), embed=format_response_embed(bing_resp), mention_author=False)


async def get_bot(bing_bot_cookie_path) -> discord.Bot:
    bing_bot = BingBot(bing_bot_cookie_path)

    intents = discord.Intents.all()
    bot = discord.Bot(intents=intents)

    @bot.event
    async def on_ready():
        print(f"{bot.user} is ready and online!")
        await bot.change_presence(activity=discord.Game('Balanced'))

    add_command_reset(bot, bing_bot)
    add_command_style(bot, bing_bot)
    listen_on_message_event(bot, bing_bot)

    return bot


def format_response_body(bing_resp: BingBotResponse):
    return bing_resp.message


def format_response_embed(bing_resp):
    embed = discord.Embed()
    if bing_resp.links:
        embed.add_field(name="Links", value=bing_resp.links)
    embed.add_field(name="Limit", value=f"({bing_resp.current_conversation_num}/{bing_resp.max_conversation_num})")
    return embed

