from typing import List

from EdgeGPT import Chatbot, ConversationStyle


class BingBotResponse:
    def __init__(self, success, message, current_conversation_num, max_conversation_num, suggested_responses, links):
        self.success: bool = success
        self.message: str = message
        self.current_conversation_num: int = current_conversation_num
        self.max_conversation_num: int = max_conversation_num
        self.suggested_responses: List[int] = suggested_responses
        self.links: str = links


class BingBot:
    def __init__(self, cookie_path: str):
        self._bot = Chatbot(cookiePath=cookie_path)
        self._current_style = ConversationStyle.balanced

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
            await self.reset()
            return BingBotResponse(False, f'Error: conversation has been reset. Reason: {result["value"]}', None, None, None)

        throttling = response_item['throttling']
        cur_num, max_num = int(throttling['numUserMessagesInConversation']), int(throttling['maxNumUserMessagesInConversation'])

        message = response_item['messages'][-1]
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

        return BingBotResponse(True, message_text, cur_num, max_num, suggested_responses, links)
