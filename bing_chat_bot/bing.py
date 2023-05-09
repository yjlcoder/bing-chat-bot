from typing import List, Optional

import EdgeGPT
from EdgeGPT import Chatbot, ConversationStyle


class BingBotResponse:
    def __init__(self,
                 success,
                 message,
                 current_conversation_num: Optional[int] = None,
                 max_conversation_num: Optional[int] = None,
                 suggested_responses: Optional[List[str]] = None,
                 links: Optional[str] = None,
                 citations: Optional[str] = None):
        self.success: bool = success
        self.message: str = message
        self.current_conversation_num: Optional[int] = current_conversation_num
        self.max_conversation_num: Optional[int] = max_conversation_num
        self.suggested_responses: Optional[List[str]] = suggested_responses
        self.links: Optional[str] = links
        self.citations: Optional[str] = citations


class BingBotStatus:
    def __init__(self, current_style, profile_index, profile_total_num):
        self.current_style: str = current_style
        self.profile_index: int = profile_index
        self.profile_total_num: int = profile_total_num


class BingBot:
    def __init__(self, cookie_paths: List[str]):
        self._cookie_paths = cookie_paths
        self._profile_index = 0

        self._bot = Chatbot(cookie_path=self._cookie_paths[0])
        self._current_style = ConversationStyle.balanced

    def get_bot_status(self) -> BingBotStatus:
        return BingBotStatus(
            self._current_style.name,
            self._profile_index + 1,
            len(self._cookie_paths)
        )

    async def switch_profile(self):
        """
        Switch Bing profile (account)
        """
        try:
            await self._bot.close()
        except Exception:
            pass
        self._profile_index = (self._profile_index + 1) % len(self._cookie_paths)
        self._bot = Chatbot(cookiePath=self._cookie_paths[self._profile_index])

    async def reset(self):
        await self._bot.reset()

    async def switch_style(self, style: str):
        style_value = ConversationStyle[style]
        if style_value is None:
            raise f"Cannot find style {style}"
        self._current_style = style_value
        print(f"Successfully switch style to {style}")
        await self.reset()

    async def converse(self, text: str) -> BingBotResponse:
        response = await self._bot.ask(prompt=text, conversation_style=self._current_style)
        response_item = response['item']
        result = response_item['result']
        if result['value'] != 'Success':
            try:
                await self.reset()
            except EdgeGPT.NotAllowedToAccess as e:
                return BingBotResponse(False, f'Error: {str(e)}')
            return BingBotResponse(False, f'Error: conversation has been reset. Reason: {result["value"]}')

        throttling = response_item['throttling']
        cur_num, max_num = int(throttling['numUserMessagesInConversation']), int(
            throttling['maxNumUserMessagesInConversation'])

        message = response_item['messages'][-1]
        if message['author'] is None or message['author'] != 'bot':
            await self.reset()
            return BingBotResponse(False, f'Error: No response from Bing Chat Bot')
        message_text = message['text']

        suggested_responses = []
        try:
            suggested_responses = [i['text'] for i in message['suggestedResponses']]
        except Exception:
            pass

        links = None
        try:
            links = message['adaptiveCards'][0]['body'][1]['text']
        except Exception:
            pass

        citations = None
        try:
            citation_text = message['adaptiveCards'][0]['body'][0]['text']
            if citation_text.startswith('[1]'):
                citations = citation_text.split('\n\n')[0]
        except Exception:
            pass

        return BingBotResponse(True, message_text, cur_num, max_num, suggested_responses, links, citations)
