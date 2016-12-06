# encoding=utf8
import json
import re
from lxml import html
from lxml.html.clean import Cleaner
import requests
from requests.compat import urlparse, quote_plus
from requests_toolbelt import MultipartEncoder

base_url = 'https://telegra.ph'
save_url = 'https://edit.telegra.ph/save'


def clean_article_html(html_string):

    c = Cleaner(
        allow_tags=['a', 'blockquote', 'br', 'div', 'em', 'figure', 'h3', 'h4', 'iframe', 'img', 'p', 'strong'],
        style=True,
        remove_unknown_tags=False,
        embedded=False
    )
    # wrap with div to be sure it is there
    # (otherwise lxml will add parent element in some cases
    html_string = '<div>%s</div>' % html_string
    cleaned = c.clean_html(html_string)
    # remove wrapped div
    cleaned = cleaned[5:-6]
    # remove all line breaks and empty strings
    html_string = re.sub('(^[\s\t]*)?\r?\n', '', cleaned, flags=re.MULTILINE)
    return html_string


def preprocess_tags(element):
    if isinstance(element, html.HtmlElement) and element.tag in ['iframe']:
        iframe_src = element.get('src')
        youtube = re.match('https?://(www\.)?youtube(-nocookie)?\.com/embed/', iframe_src)
        if youtube:
            yt_id = urlparse(iframe_src).path.replace('/embed/', '')
            element.set('src', '/embed/youtube?url=' + quote_plus('https://www.youtube.com/watch?v=' + yt_id))
            new_element = html.HtmlElement()
            new_element.tag = 'figure'
            new_element.append(element)
            element = new_element

    return element


def _recursive_convert(element):

    element = preprocess_tags(element)
    fragment_root_element = {
        '_': element.tag
    }

    content = []
    if element.text:
        content.append({'t': element.text})

    if element.attrib:
        fragment_root_element.update({
            'a': dict(element.attrib)
        })

    for child in element:
        content.append(_recursive_convert(child))
        # Append Text node after element, if exists
        if child.tail:
            content.append({'t': child.tail})

    if len(content):
        fragment_root_element.update({
            'c': content
        })

    return fragment_root_element


def convert_html_to_telegraph_format(html_string, clean_html=True):
    if clean_html:
        html_string = clean_article_html(html_string)

    fragments = html.fragments_fromstring(html_string)
    content = []

    for fragment in fragments:
        # convert and append text nodes before starting tag
        if not isinstance(fragment, html.HtmlElement):
            fragment = html.fromstring('<p>%s</p>' % fragment)

        content.append(_recursive_convert(fragment))
        # convert and append text nodes after closing tag
        if fragment.tail:
            content.append(
                _recursive_convert(html.fromstring('<p>%s</p>' % fragment.tail))
            )

    return json.dumps(content, ensure_ascii=False)


def upload_to_telegraph(title, author, text, author_url='', tph_uuid=None, page_id=None):

    if not title:
        raise Exception('Title is required')
    if not text:
        raise Exception('Text is required')

    content = convert_html_to_telegraph_format(text)
    cookies = dict(tph_uuid=tph_uuid) if tph_uuid and page_id else None

    fields = {
        'Data': ('content.html', content, 'plain/text'),
        'title': title,
        'author': author,
        'author_url': author_url,
        'page_id': page_id or '0'
    }

    m = MultipartEncoder(fields, boundary='TelegraPhBoundary21')

    headers = {
        'Content-Type': m.content_type,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'User-Agent': 'Python_telegraph_poster/0.1'
    }
    r = requests.Session()
    r.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))
    response = r.post(save_url, timeout=4, headers=headers, cookies=cookies, data=m.to_string())

    result = json.loads(response.text)
    if 'path' in result:
        result['tph_uuid'] = response.cookies.get('tph_uuid') or tph_uuid
        result['url'] = base_url + '/' + result['path']
        return result
    else:
        error_msg = 'Telegraph error msg: ' + result['error'] if 'error' in result else ''
        raise Exception(error_msg)


class TelegraphPoster(object):
    def __init__(self, tph_uuid=None, page_id=None):
        self.title = None
        self.author = None
        self.author_url = None
        self.text = None
        self.tph_uuid = tph_uuid
        self.page_id = page_id

    def post(self, title, author, text, author_url=''):
        result = self.edit(
            title,
            author,
            text
        )
        self.title = title
        self.author = author
        self.author_url = author_url
        self.text = text
        self.tph_uuid = result['tph_uuid']
        self.page_id = result['page_id']
        return result

    def edit(self, title=None, author=None, text=None):
        return upload_to_telegraph(
            title=title or self.title,
            author=author or self.author,
            text=text or self.text,
            author_url=self.author_url,
            tph_uuid=self.tph_uuid,
            page_id=self.page_id
        )
