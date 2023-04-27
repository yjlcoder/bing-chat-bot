import logging
from io import BytesIO
from typing import List, Optional

import discord
from discord import MessageType

from .bing import BingBot, BingBotResponse
from .formatter import Formatter, FormatterResponse, FormatterOptions, FormatterResponseType

AUTO_RESET_DIFF_SECONDS = 30 * 60

logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self, bing_bot_cookie_paths):
        self.bing = BingBot(bing_bot_cookie_paths)
        self._formatter_options = FormatterOptions()

        self._bing_resp_cache = None
        self._original_message_cache: Optional[discord.Message] = None

        self._suggested_response_callback_generator = None

    def initialize(self, bot: discord.Bot):
        @bot.event
        async def on_ready():
            logger.info(f"{bot.user} is ready and online!")
            await self._switch_bot_status(bot)

        self._add_commands(bot)
        self._listen_on_message_event(bot)
        self._suggested_response_callback_generator = self._create_suggested_response_callback_generator(bot)

        self._formatter = Formatter(formatter_options=self._formatter_options, suggested_response_callback_generator=self._suggested_response_callback_generator)

    def _add_commands(self, bot: discord.Bot):
        self._add_command_reset(bot)
        self._add_command_style(bot)
        self._add_command_switch_profile(bot)
        self._add_command_toggle(bot)
        self._add_command_replay(bot)

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
            logger.info(f"Switch to profile: {bing_status.profile_index}/{bing_status.profile_total_num}")

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

    def _add_command_replay(self, bot: discord.Bot):
        @bot.command(name='replay', description="Re-present the last message")
        async def replay(ctx: discord.ApplicationContext):
            if self._bing_resp_cache is None or self._original_message_cache is None:
                await ctx.respond("No message to replay")
            await ctx.respond("Re-presenting the last message")
            await self._format_and_respond(self._bing_resp_cache, original_message=self._original_message_cache)

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
                # The message is sent from a bot
                return
            if message.type != MessageType.default:
                # Should not respond system message
                return
            if self._original_message_cache is not None:
                # If the new message comes more than AUTO_RESET_DIFF_SECONDS after the previous one, reset the conversation
                time_diff = message.created_at - self._original_message_cache.created_at
                time_diff_seconds = time_diff.total_seconds()
                if time_diff_seconds >= AUTO_RESET_DIFF_SECONDS:
                    await self.bing.reset()
                    logger.info(f"Reset previous bing conversation: {time_diff_seconds} since last message.")
            ctx: discord.ApplicationContext = await bot.get_application_context(message)
            async with ctx.typing():
                bing_resp: BingBotResponse = await self.bing.converse(message.content)
            self._bing_resp_cache = bing_resp
            self._original_message_cache = message
            await self._format_and_respond(bing_resp, original_message=message)

    async def _format_and_respond(self, bing_resp: BingBotResponse, original_message: discord.message):
        formatter_responses = self._formatter.format_message(bing_resp)
        await self._respond_messages(formatter_responses, original_message)

    async def _respond_messages(self, formatter_responses: List[FormatterResponse], original_message: discord.Message):
        if len(formatter_responses) == 0:
            return
        texts = [response.value for response in formatter_responses if response.type == FormatterResponseType.NORMAL]
        embeds = [response.value for response in formatter_responses if response.type == FormatterResponseType.EMBED]
        views = [response.value for response in formatter_responses if response.type == FormatterResponseType.VIEW]
        large_texts = [response.value for response in formatter_responses if response.type == FormatterResponseType.LARGE_TEXT]
        embed = embeds[0] if len(embeds) > 0 else None
        view = views[0] if len(views) > 0 else None
        large_text = large_texts[0] if len(large_texts) > 0 else None

        if large_text is not None:
            params = {
                'file': discord.File(BytesIO(large_text.encode('UTF-8')), filename="response.md"),
                'embed': embed,
                'view': view
            }
            await original_message.reply(mention_author=False, **params)
        else:
            for index, obj in enumerate(texts):
                params = {
                    'content': obj
                }
                if index == len(texts) - 1:
                    params['embed'] = embed
                    params['view'] = view
                if index == 0:
                    await original_message.reply(mention_author=False, **params)
                else:
                    await original_message.channel.send(**params)


    def _create_suggested_response_callback_generator(self, bot: discord.Bot):
        """
        This method is to create a callback generator
        """
        def callback_generator(button: discord.ui.Button):
            """
            This method is the callback generator that generates a callback function for each button
            """
            async def _handle_suggested_response(interaction: discord.Interaction):
                response_content = button.label
                await interaction.response.send_message(f"From user: **{response_content}**")
                message = await interaction.original_response()
                ctx: discord.ApplicationContext = await bot.get_application_context(message)
                async with ctx.typing():
                    bing_resp: BingBotResponse = await self.bing.converse(response_content)
                self._bing_resp_cache = bing_resp
                self._original_message_cache = message
                await self._format_and_respond(bing_resp, original_message=message)
            return _handle_suggested_response
        return callback_generator


async def get_bot(bing_bot_cookie_paths) -> discord.Bot:
    intents = discord.Intents.all()
    bot = discord.Bot(intents=intents)

    bot_manager = BotManager(bing_bot_cookie_paths=bing_bot_cookie_paths)
    bot_manager.initialize(bot)

    return bot
