import mimetypes
import re

import httpx
import requests

from io import BytesIO
base_url = 'http://telegra.ph'
save_url = 'https://edit.telegra.ph/save'
upload_file_url = 'https://telegra.ph/upload'


class Error(Exception):
    pass


class GetImageRequestError(Error):
    pass


class ImageUploadHTTPError(Error):
    pass


class FileTypeNotSupported(Error):
    pass


def _check_mimetypes(type):
    return type in ('image/jpeg', 'image/png', 'image/gif', 'video/mp4')


def _get_mimetype_from_response_headers(headers):
    types = re.split(r'[;,]', headers['Content-Type'])
    if len(types):
        ext = mimetypes.guess_extension(types[0], strict=False)
        if ext:
            return mimetypes.types_map.get(ext, mimetypes.common_types.get(ext, ''))
    return ''


async def upload_image(
        file_name_or_url,
        user_agent='Python_telegraph_poster/0.1',
        return_json=False,
        get_timeout=(10.0, 10.0),
        upload_timeout=(7.0, 7.0)
    ):

    if hasattr(file_name_or_url, 'read') and hasattr(file_name_or_url, 'name'):
        img = file_name_or_url
        img_content_type = mimetypes.guess_type(file_name_or_url.name)[0]
    elif re.match(r'^https?://', file_name_or_url, flags=re.IGNORECASE):
        try:
            async with httpx.AsyncClient(timeout=get_timeout) as client:
                img = await client.get(file_name_or_url, headers={'User-Agent': user_agent})
        except:
            raise GetImageRequestError('Url request failed')

        if img.status_code != 200 or 'Content-Type' not in img.headers:
            raise GetImageRequestError('Url request failed')

        img_content_type = _get_mimetype_from_response_headers(img.headers)
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
        async with httpx.AsyncClient(timeout=upload_timeout) as client:
            json_response = await client.post(upload_file_url, files=files, headers=headers)
    except httpx.ReadTimeout:
        raise ImageUploadHTTPError('Request timeout')

    if json_response.status_code == requests.codes.ok and json_response.content:
        json_response = json_response.json()
        if return_json:
            return json_response
        elif type(json_response) is list and len(json_response):
            return 'src' in json_response[0] and base_url + json_response[0]['src'] or ''
        elif type(json_response) is dict:
            if json_response.get('error') == 'File type invalid':
                raise FileTypeNotSupported('This file is unsupported')
            else:
                return str(json_response)
    else:
        raise Exception('Error while uploading the image')
