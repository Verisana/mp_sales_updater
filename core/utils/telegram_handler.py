import logging
from io import BytesIO

import telegram


class TelegramHandler(logging.Handler):
    def __init__(self, token, chat_id, level=logging.NOTSET, timeout=2, disable_notification=False,
                 disable_web_page_preview=False, proxies=None):
        self.disable_web_page_preview = disable_web_page_preview
        self.disable_notification = disable_notification
        self.timeout = timeout
        self.proxies = proxies
        self.chat_id = chat_id

        super(TelegramHandler, self).__init__(level=level)

        self.bot = telegram.Bot(token)
        del token

    def emit(self, record):
        text = self.format(record)

        params = {
            'chat_id': self.chat_id,
            'disable_web_page_preview': self.disable_web_page_preview,
            'disable_notification': self.disable_notification,
        }

        document = telegram.InputFile(BytesIO(text.encode()), filename=f'{record.levelname}_{record.filename}_'
                                                                       f'{record.lineno}.json')
        self.bot.send_document(document=document, **params)
