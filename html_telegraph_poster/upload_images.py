import mimetypes
import re
import requests

from io import BytesIO
base_url = 'http://graph.org'
save_url = 'https://edit.graph.org/save'
upload_file_url = 'http://graph.org/upload'


class Error(Exception):
    pass


class GetImageRequestError(Error):
    pass


class ImageUploadHTTPError(Error):
    pass


class FileTypeNotSupported(Error):
    pass


def _check_mimetypes(type):
    return type in ['image/jpeg', 'image/png', 'image/gif', 'video/mp4']


def upload_image(file_name_or_url, user_agent='Python_telegraph_poster/0.1'):

    if re.match(r'^https?://', file_name_or_url, flags=re.IGNORECASE):
        img = requests.get(file_name_or_url, headers={'User-Agent': user_agent})

        if img.status_code != 200 or 'Content-Type' not in img.headers:
            raise GetImageRequestError('Url request failed')

        img_content_type = re.split(';|,', img.headers['Content-Type'])[0]
        img = BytesIO(img.content)

    else:
        img_content_type = mimetypes.guess_type(file_name_or_url)[0]
        img = open(file_name_or_url, 'rb').read()

    # simple filecheck, based on file extension
    if not _check_mimetypes(img_content_type):
        raise FileTypeNotSupported('The "%s" filetype is not supported' % img_content_type)

    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': base_url + '/',
        'User-Agent': user_agent
    }

    files = {
        'file': ('blob', img, img_content_type)
    }
    try:
        json_response = requests.post(upload_file_url, timeout=7, files=files, headers=headers)
    except requests.exceptions.ReadTimeout:
        raise ImageUploadHTTPError('Request timeout')

    if json_response.status_code == requests.codes.ok and json_response.content:
        json_response = json_response.json()
        if type(json_response) is list and len(json_response):
            return 'src' in json_response[0] and base_url + json_response[0]['src'] or ''
        elif type(json_response) is dict:
            return ''
    else:
        raise Exception('Error while uploading the image')
