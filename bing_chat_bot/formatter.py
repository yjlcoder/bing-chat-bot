import re
from enum import Enum, auto
from typing import List

import discord

from .bing import BingBotResponse


class FormatterOptions:
    def __init__(self, show_embed: True):
        self.show_embed: bool = show_embed


class FormatterResponseType(Enum):
    NORMAL = auto(),
    EMBED = auto()


class FormatterResponse:
    def __init__(self, response_type: FormatterResponseType, obj: object):
        self._response_type = response_type
        self._obj = obj

    @property
    def type(self):
        return self._response_type

    @property
    def value(self):
        return self._obj


class Formatter:
    def __init__(self, formatter_options: FormatterOptions):
        self._formatter_options = formatter_options

    def format_message(self, bing_resp: BingBotResponse) -> List[FormatterResponse]:
        results = []

        results.append(FormatterResponse(FormatterResponseType.NORMAL, bing_resp.message))
        if self._formatter_options.show_embed:
            embed = self._format_response_embed(bing_resp)
            if embed is not None:
                results.append(FormatterResponse(FormatterResponseType.EMBED, embed))

        return results

    def _format_response_embed(self, bing_resp: BingBotResponse):
        has_value = False

        embed = discord.Embed()
        embed.title = ""
        embed.description = ""

        # Citations
        if bing_resp.citations is not None:
            has_value = True
            self._format_response_embed_add_citations(bing_resp, embed)

        # Links
        if bing_resp.links:
            has_value = True
            self._format_response_embed_add_links(bing_resp, embed)

        # Throttling Limit
        if bing_resp.current_conversation_num is not None and bing_resp.max_conversation_num is not None:
            has_value = True
            embed.add_field(name="Limit",
                            value=f"({bing_resp.current_conversation_num}/{bing_resp.max_conversation_num})")

        return embed if has_value else None

    def _format_response_embed_add_links(self, bing_resp: BingBotResponse, embed: discord.Embed):
        links = bing_resp.links
        if links is None or len(links) == 0:
            return

        pattern = re.compile(r"\[([0-9]+\.\ \S+)\]\(([\S]+)\)")
        matches = re.findall(pattern, links)
        if matches is None or len(matches) == 0:
            if len(links) > 1023:
                links = "Message cannot show: too long."
            embed.add_field(name="Links", value=links)
        else:
            for match in matches:
                hostname, url = match
                embed.add_field(name=hostname, value=f"[Link]({url})")

    def _format_response_embed_add_citations(self, bing_resp, embed):
        citations = bing_resp.citations
        if citations is None or len(citations) == 0:
            return

        pattern = re.compile(r'\[(\d+)\]: (\S+) \"([^\"]+)\"')
        matches = re.findall(pattern, citations)
        if matches is None or len(matches) == 0:
            if len(citations) > 4095:
                citations = "Citations cannot show: too long"
            embed.description = citations
        else:
            embed.title = "Citations"
            for match in matches:
                citation_num, url, title = match
                embed.description += f"[[{citation_num}] {title}]({url})\n\n"
