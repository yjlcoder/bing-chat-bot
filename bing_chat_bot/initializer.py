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
        await switch_chat_style(ctx, bot, bing, "creative")

    @chat_style_command_group.command(description="Switch chat style to Balanced")
    async def balanced(ctx: discord.ApplicationContext):
        await switch_chat_style(ctx, bot, bing, "balanced")

    @chat_style_command_group.command(description="Switch chat style to Precise")
    async def precise(ctx: discord.ApplicationContext):
        await switch_chat_style(ctx, bot, bing, "precise")


def add_command_switch_profile(bot, bing: BingBot):
    @bot.command(name='profile', description="Switch the profile")
    async def profile(ctx: discord.ApplicationContext):
        await bing.switch_profile()
        bing_status = bing.get_bot_status()
        await switch_bot_status(bot, bing)
        await ctx.respond(f"Switch to profile: {bing_status.profile_index}/{bing_status.profile_total_num}")
        print(f"Switch to profile: {bing_status.profile_index}/{bing_status.profile_total_num}")


async def switch_chat_style(ctx: discord.ApplicationContext, bot: discord.Bot, bing: BingBot, style: str):
    await bing.switch_style(style)
    await ctx.respond(f"Switch chat style to {style.capitalize()}")
    await switch_bot_status(bot, bing)


async def switch_bot_status(bot: discord.Bot, bing: BingBot):
    bing_status = bing.get_bot_status()
    status_name = f"{bing_status.current_style.capitalize()}, Profile: ({bing_status.profile_index}/{bing_status.profile_total_num})"
    await bot.change_presence(activity=discord.Game(status_name))


def listen_on_message_event(bot: discord.Bot, bing: BingBot):
    @bot.event
    async def on_message(message: discord.Message):
        if message.author.bot:
            return
        ctx: discord.ApplicationContext = await bot.get_application_context(message)
        async with ctx.typing():
            bing_resp: BingBotResponse = await bing.converse(message.content)
        await message.reply(format_response_body(bing_resp), embed=format_response_embed(bing_resp),
                            mention_author=False)


async def get_bot(bing_bot_cookie_paths) -> discord.Bot:
    bing_bot = BingBot(bing_bot_cookie_paths)

    intents = discord.Intents.all()
    bot = discord.Bot(intents=intents)

    @bot.event
    async def on_ready():
        print(f"{bot.user} is ready and online!")
        await switch_bot_status(bot, bing_bot)

    add_command_reset(bot, bing_bot)
    add_command_style(bot, bing_bot)
    add_command_switch_profile(bot, bing_bot)
    listen_on_message_event(bot, bing_bot)

    return bot


def format_response_body(bing_resp: BingBotResponse):
    return bing_resp.message


def format_response_embed(bing_resp):
    has_value = False

    embed = discord.Embed()

    # Links
    if bing_resp.links:
        has_value = True
        embed.add_field(name="Links", value=bing_resp.links)

    # Throttling Limit
    if bing_resp.current_conversation_num is not None and bing_resp.max_conversation_num is not None:
        has_value = True
        embed.add_field(name="Limit", value=f"({bing_resp.current_conversation_num}/{bing_resp.max_conversation_num})")

    return embed if has_value else None
