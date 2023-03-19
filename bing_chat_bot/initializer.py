from typing import List

import discord

from .bing import BingBot, BingBotResponse
from .formatter import Formatter, FormatterResponse, FormatterOptions, FormatterResponseType


class BotManager:
    def __init__(self, bing_bot_cookie_paths):
        self.bing = BingBot(bing_bot_cookie_paths)
        self._formatter_options = FormatterOptions()
        self._formatter = Formatter(formatter_options=self._formatter_options)

    def initialize(self, bot: discord.Bot):
        @bot.event
        async def on_ready():
            print(f"{bot.user} is ready and online!")
            await self._switch_bot_status(bot)

        self._add_commands(bot)
        self._listen_on_message_event(bot)

    def _add_commands(self, bot: discord.Bot):
        self._add_command_reset(bot)
        self._add_command_style(bot)
        self._add_command_switch_profile(bot)
        self._add_command_toggle(bot)

    def _add_command_reset(self, bot: discord.Bot):
        # Reset the conversation and start a new one
        @bot.command(name='reset', description="Reset the conversation")
        async def reset(ctx: discord.ApplicationContext):
            await self.bing.reset()
            await ctx.respond("Reset the conversion")

    def _add_command_style(self, bot: discord.Bot):
        # Set the bing chat style: Creative, Balanced, Precise
        chat_style_command_group = bot.create_group("style", "Switch chat style")

        @chat_style_command_group.command(description="Switch chat style to Creative")
        async def creative(ctx: discord.ApplicationContext):
            await self.switch_chat_style(ctx, bot, "creative")

        @chat_style_command_group.command(description="Switch chat style to Balanced")
        async def balanced(ctx: discord.ApplicationContext):
            await self.switch_chat_style(ctx, bot, "balanced")

        @chat_style_command_group.command(description="Switch chat style to Precise")
        async def precise(ctx: discord.ApplicationContext):
            await self.switch_chat_style(ctx, bot, "precise")

    def _add_command_switch_profile(self, bot):
        @bot.command(name='profile', description="Switch the profile")
        async def profile(ctx: discord.ApplicationContext):
            await self.bing.switch_profile()
            bing_status = self.bing.get_bot_status()
            await self._switch_bot_status(bot)
            await ctx.respond(f"Switch to profile: {bing_status.profile_index}/{bing_status.profile_total_num}")
            print(f"Switch to profile: {bing_status.profile_index}/{bing_status.profile_total_num}")

    def _add_command_toggle(self, bot: discord.Bot):
        toggle_command_group = bot.create_group("toggle", "Toggle chat configuration")

        @toggle_command_group.command(desciption="Toggle if showing citations")
        async def citations(ctx: discord.ApplicationContext):
            self._formatter_options.show_citations = not self._formatter_options.show_citations
            await ctx.respond(f"Toggle configuration - showing citations. Current value: {self._formatter_options.show_citations}")

        @toggle_command_group.command(description="Toggle if showing links")
        async def links(ctx: discord.ApplicationContext):
            self._formatter_options.show_links = not self._formatter_options.show_links
            await ctx.respond(f"Toggle configuration - showing links. Current value: {self._formatter_options.show_links}")

        @toggle_command_group.command(description="Toggle if showing limits")
        async def limits(ctx: discord.ApplicationContext):
            self._formatter_options.show_limits = not self._formatter_options.show_limits
            await ctx.respond(f"Toggle configuration - showing limits. Current value: {self._formatter_options.show_limits}")

    async def switch_chat_style(self, ctx: discord.ApplicationContext, bot: discord.Bot, style: str):
        await self.bing.switch_style(style)
        await ctx.respond(f"Switch chat style to {style.capitalize()}")
        await self._switch_bot_status(bot)

    async def _switch_bot_status(self, bot: discord.Bot):
        bing_status = self.bing.get_bot_status()
        status_name = f"{bing_status.current_style.capitalize()}, Profile: ({bing_status.profile_index}/{bing_status.profile_total_num})"
        await bot.change_presence(activity=discord.Game(status_name))

    def _listen_on_message_event(self, bot: discord.Bot):
        @bot.event
        async def on_message(message: discord.Message):
            if message.author.bot:
                return
            ctx: discord.ApplicationContext = await bot.get_application_context(message)
            async with ctx.typing():
                bing_resp: BingBotResponse = await self.bing.converse(message.content)
            formatter_responses = self._formatter.format_message(bing_resp)
            await self._respond_messages(formatter_responses, original_message=message)

    async def _respond_messages(self, formatter_responses: List[FormatterResponse], original_message: discord.Message):
        if len(formatter_responses) == 0:
            return
        texts = [response.value for response in formatter_responses if response.type == FormatterResponseType.NORMAL]
        embeds = [response.value for response in formatter_responses if response.type == FormatterResponseType.EMBED]
        embed = embeds[0] if len(embeds) > 0 else None
        for index, obj in enumerate(texts):
            params = {
                'content': obj
            }
            if index == len(texts) - 1:
                params['embed'] = embed
            if index == 0:
                await original_message.reply(mention_author=False, **params)
            else:
                await original_message.channel.send(**params)


async def get_bot(bing_bot_cookie_paths) -> discord.Bot:
    intents = discord.Intents.all()
    bot = discord.Bot(intents=intents)

    bot_manager = BotManager(bing_bot_cookie_paths=bing_bot_cookie_paths)
    bot_manager.initialize(bot)

    return bot
