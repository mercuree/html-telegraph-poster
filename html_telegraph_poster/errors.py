# coding=utf8


class Error(Exception):
    pass


class TitleRequiredError(Error):
    pass


class TextRequiredError(Error):
    pass


class GetImageRequestError(Error):
    pass


class ImageUploadHTTPError(Error):
    pass


class FileTypeNotSupported(Error):
    pass


class TelegraphUnknownError(Error):
    pass


class TelegraphContentTooBigError(Error):
    def __init__(self, message):
        message += ". Max size is 64kb including markup"
        super(Error, TelegraphError).__init__(self, message)


class TelegraphError(Error):
    def __init__(self, message):
        if 'Unknown error' in message:
            raise TelegraphUnknownError(message)
        elif 'Content is too big' in message:
            raise TelegraphContentTooBigError(message)
        else:
            super(Error, TelegraphError).__init__(self, message)
