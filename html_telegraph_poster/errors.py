# coding=utf8


class Error(Exception):
    pass


class TitleRequiredError(Error):
    pass


class TextRequiredError(Error):
    pass


class APITokenRequiredError(Error):
    pass


class GetImageRequestError(Error):
    pass


class ImageUploadHTTPError(Error):
    pass


class FileTypeNotSupported(Error):
    pass


class TelegraphUnknownError(Error):
    pass


class TelegraphPageSaveFailed(Error):
    # reason is unknown
    pass


class TelegraphContentTooBigError(Error):
    def __init__(self, message):
        message += ". Max size is 64kb including markup"
        super(Error, TelegraphError).__init__(self, message)


class TelegraphFloodWaitError(Error):
    def __init__(self, message):
        super(Error, TelegraphError).__init__(self, message)
        self.FLOOD_WAIT_IN_SECONDS = int(message.split('FLOOD_WAIT_')[1])


class TelegraphError(Error):
    def __init__(self, message):
        if 'Unknown error' in message:
            raise TelegraphUnknownError(message)
        elif 'Content is too big' in message:
            raise TelegraphContentTooBigError(message)
        elif 'FLOOD_WAIT_' in message:
            raise TelegraphFloodWaitError(message)
        elif 'PAGE_SAVE_FAILED' in message:
            raise TelegraphPageSaveFailed(message)
        else:
            super(Error, TelegraphError).__init__(self, message)
