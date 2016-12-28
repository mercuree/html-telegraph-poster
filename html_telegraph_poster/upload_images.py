import mimetypes
import re
import requests
from html_telegraph_poster.html_to_telegraph import default_user_agent

from io import BytesIO
base_url = 'https://telegra.ph'
save_url = 'https://edit.telegra.ph/save'
upload_file_url = 'http://telegra.ph/upload'


def _check_mimetypes(type):
    return type in ['image/jpeg', 'image/png', 'image/gif', 'video/mp4']


def upload_image(file_name_or_url):

    if re.match(r'^https?://', file_name_or_url, flags=re.IGNORECASE):
        img = requests.get(file_name_or_url, headers={'User-Agent': default_user_agent})

        if img.status_code != 200 or 'Content-Type' not in img.headers:
            raise Exception('Url request failed')

        img_content_type = img.headers['Content-Type']
        img = BytesIO(img.content)

    else:
        img_content_type = mimetypes.guess_type(file_name_or_url)[0]
        img = open(file_name_or_url, 'rb').read()

    # simple filecheck, based on file extension
    if not _check_mimetypes(img_content_type):
        raise Exception('The "%s" filetype is not supported' % img_content_type)

    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': base_url + '/',
        'User-Agent': default_user_agent
    }

    files = {
        'file': ('blob', img, img_content_type)
    }
    try:
        json_response = requests.post(upload_file_url, timeout=7, files=files, headers=headers)
    except requests.exceptions.ReadTimeout:
        raise Exception('Request timeout')

    if json_response and json_response.status_code == requests.codes.ok and json_response.content:
        json_response = json_response.json()
        if type(json_response) is list and len(json_response):
            return 'src' in json_response[0] and base_url + json_response[0]['src'] or ''
        elif type(json_response) is dict:
            return ''
    else:
        raise Exception('Error while uploading the image')