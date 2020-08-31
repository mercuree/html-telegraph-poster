# encoding=utf8
import json
import re
import os
from lxml import html
from lxml.html.clean import Cleaner
import requests
from requests.compat import urlparse, quote_plus
from requests_toolbelt import MultipartEncoder
from .errors import *

base_url = 'http://telegra.ph'
save_url = 'https://edit.telegra.ph/save'
api_url = 'https://api.telegra.ph'
default_user_agent = 'Python_telegraph_poster/0.1'
allowed_tags = ('a', 'aside', 'b', 'blockquote', 'br', 'code', 'em', 'figcaption', 'figure', 'h3', 'h4', 'hr', 'i',
                'iframe', 'img', 'li', 'ol', 'p', 'pre', 's', 'strong', 'u', 'ul', 'video')
allowed_top_level_tags = ('aside', 'blockquote', 'pre', 'figure', 'h3', 'h4', 'hr', 'ol', 'p', 'ul')

elements_with_text = ('a', 'aside', 'b', 'blockquote', 'em', 'h3', 'h4', 'p', 'strong')

youtube_re = re.compile(r'(https?:)?//(www\.)?youtube(-nocookie)?\.com/embed/')
vimeo_re = re.compile(r'(https?:)?//player\.vimeo\.com/video/(\d+)')
twitter_re = re.compile(r'(https?:)?//(www\.)?twitter\.com/[A-Za-z0-9_]{1,15}/status/\d+')
telegram_embed_iframe_re = re.compile(r'^(https?)://(t\.me|telegram\.me|telegram\.dog)/([a-zA-Z0-9_]+)/(\d+)', re.IGNORECASE)
telegram_embed_script_re = re.compile(r'''<script(?=[^>]+\sdata-telegram-post=['"]([^'"]+))[^<]+</script>''', re.IGNORECASE)
pre_content_re = re.compile(r'<(pre|code)(>|\s[^>]*>)[\s\S]*?</\1>')
line_breaks_inside_pre = re.compile(r'<br(/?>|\s[^<>]*>)')
line_breaks_and_empty_strings = re.compile(r'(\s{2,}|\s*\r?\n\s*)')
header_re = re.compile(r'<head[^a-z][\s\S]*</head>')


def clean_article_html(html_string):

    html_string = html_string.replace('<h1', '<h3').replace('</h1>', '</h3>')
    # telegram will convert <b> anyway
    html_string = re.sub(r'<(/?)b(?=\s|>)', r'<\1strong', html_string)
    html_string = re.sub(r'<(/?)(h2|h5|h6)', r'<\1h4', html_string)
    # convert telegram embed posts before cleaner
    html_string = re.sub(telegram_embed_script_re, r'<iframe src="https://t.me/\1"></iframe>', html_string)
    # remove <head> if present (can't do this with Cleaner)
    html_string = header_re.sub('', html_string)

    c = Cleaner(
        allow_tags=allowed_tags,
        style=True,
        remove_unknown_tags=False,
        embedded=False,
        safe_attrs_only=True,
        safe_attrs=('src', 'href', 'class')
    )
    # wrap with div to be sure it is there
    # (otherwise lxml will add parent element in some cases
    html_string = '<div>%s</div>' % html_string
    cleaned = c.clean_html(html_string)
    # remove wrapped div
    cleaned = cleaned[5:-6]
    # remove all line breaks and empty strings
    html_string = replace_line_breaks_except_pre(cleaned)
    # but replace multiple br tags with one line break, telegraph will convert it to <br class="inline">
    html_string = re.sub(r'(<br(/?>|\s[^<>]*>)\s*)+', '\n', html_string)

    return html_string.strip(' \t')


def replace_line_breaks_except_pre(html_string, replace_by=' '):
    # Remove all line breaks and empty strings, except pre tag
    # how to make it in one string? :\
    pre_ranges = [0]
    out = ''

    # replace non-breaking space with usual space
    html_string = html_string.replace('\u00A0', ' ')

    # get <pre> start/end postion
    for x in pre_content_re.finditer(html_string):
        start, end = x.start(), x.end()
        pre_ranges.extend((start, end))
    pre_ranges.append(len(html_string))

    # all odd elements are <pre>, leave them untouched
    for k in range(1, len(pre_ranges)):
        part = html_string[pre_ranges[k-1]:pre_ranges[k]]
        if k % 2 == 0:
            out += line_breaks_inside_pre.sub('\n', part)
        else:
            out += line_breaks_and_empty_strings.sub(replace_by, part)
    return out


def _create_element(element, text=None):
    # creates lxml element without document tree (no body, no parents)
    new_element = html.HtmlElement()
    new_element.tag = element
    if text:
        new_element.text = text
    return new_element


def _insert_after(element, ref):
    parent = ref.getparent()
    parent.insert(parent.index(ref) + 1, element)
    return element


def _wrap_tag(element, wrapper):
    new_element = _create_element(wrapper)
    new_element.append(element)
    return new_element


def _wrap_figure(element):
    figure = _create_element('figure')
    element.addprevious(figure)
    element.drop_tag()
    element.tail = ''
    figure.append(element)
    return figure


def join_following_elements(elements, join_string=''):
    for element in elements:
        next_element = element.getnext()
        while next_element is not None and next_element in elements:
            current = next_element
            next_element = next_element.getnext()
            if current.text:
                current.text = join_string + current.text
            if current.tail:
                current.tail = current.tail.strip()
            element.append(current)
            elements.remove(current)
            current.drop_tag()


def _fragments_from_string(html_string):
    fragments = html.fragments_fromstring(html_string)
    if not len(fragments):
        return []
    # convert and append text node before starting tag
    if not isinstance(fragments[0], html.HtmlElement):
        if len(fragments[0].strip()) > 0:
            if len(fragments) == 1:
                return html.fragments_fromstring('<p>%s</p>' % fragments[0])
            else:
                paragraph = _create_element('p')
                paragraph.text = fragments[0]
                fragments[1].addprevious(paragraph)
                fragments.insert(1, paragraph)

        fragments.pop(0)
        if not len(fragments):
            return []

    # remove xml instructions (if cleaning is disabled)
    for instruction in fragments[0].xpath('//processing-instruction()'):
        instruction.drop_tag()

    return fragments


def preprocess_media_tags(element):
    if isinstance(element, html.HtmlElement):
        if element.tag in ['ol', 'ul']:
            # ignore any spaces between <ul> and <li>
            element.text = ''
        elif element.tag == 'li':
            # ignore spaces after </li>
            element.tail = ''
        elif element.tag == 'iframe':
            iframe_src = element.get('src')

            youtube = youtube_re.match(iframe_src)
            vimeo = vimeo_re.match(iframe_src)
            telegram = telegram_embed_iframe_re.match(iframe_src)
            if youtube or vimeo or telegram:
                element.text = ''  # ignore any legacy text
                if youtube:
                    yt_id = urlparse(iframe_src).path.replace('/embed/', '')
                    element.set('src', '/embed/youtube?url=' + quote_plus('https://www.youtube.com/watch?v=' + yt_id))
                elif vimeo:
                    element.set('src', '/embed/vimeo?url=' + quote_plus('https://vimeo.com/' + vimeo.group(2)))
                elif telegram:
                    element.set('src', '/embed/telegram?url=' + quote_plus(iframe_src))
                if not len(element.xpath('./ancestor::figure')):
                    _wrap_figure(element)
            else:
                element.drop_tag()

        elif element.tag == 'blockquote' and element.get('class') == 'twitter-tweet':
            twitter_links = element.xpath('.//a[@href]')
            for tw_link in twitter_links:
                if twitter_re.match(tw_link.get('href')):
                    twitter_frame = html.HtmlElement()
                    twitter_frame.tag = 'iframe'
                    twitter_frame.set('src', '/embed/twitter?url=' + quote_plus(tw_link.get('href')))
                    element.addprevious(twitter_frame)
                    _wrap_figure(twitter_frame)
                    element.drop_tree()
                    break


def move_to_top(body):
    # this should be improved to include nested elements (like lists)
    # still buggy
    elements = body.xpath('./*/figure|./*//blockquote')
    for element in elements:
        preceding_elements = element.xpath('./preceding-sibling::*')
        parent = element.getparent()
        if len(preceding_elements) > 0 or parent.text and len(parent.text) > 0:

            new_container = _create_element(parent.tag)
            new_container.text = parent.text
            parent.text = ''
            parent.addprevious(new_container)

            for preceding in preceding_elements:
                new_container.append(preceding)

        parent_for_figure = element.xpath('./ancestor::*[parent::body]')[0]
        # tail leaves inside parent
        element.drop_tree()
        element.tail = ''
        parent_for_figure.addprevious(element)


def preprocess_fragments(fragments):
    bad_tags = []

    if not len(fragments):
        return None

    body = fragments[0].getparent()

    # remove para inside blockquote/aside/figure  (telegraph removes it anyway) and replace with line-break
    paras_inside_quote = body.xpath('.//*[self::blockquote|self::aside|self::figure]//p[text()][following-sibling::*[text()]]')
    for para in paras_inside_quote:
        para.tail = '\n'

    bad_tags.extend(body.xpath('.//*[self::blockquote|self::aside]//p'))

    # remove empty iframes
    bad_tags.extend(body.xpath('.//iframe[not(@src)]|.//img[not(@src)]'))

    # remove images with data URIs
    bad_tags.extend(body.xpath('.//img[starts-with(normalize-space(@src), "data:")]'))

    # figcaption may have only text content
    bad_tags.extend(body.xpath(".//figcaption//*"))

    # drop all tags inside pre
    bad_tags.extend(body.xpath(".//pre//*"))

    # bad lists (remove lists/list items if empty)
    nodes_not_to_be_empty = body.xpath('.//ul|.//ol|.//li')
    bad_tags.extend([x for x in nodes_not_to_be_empty if len(x.text_content().strip()) == 0])
    # remove links with images inside
    bad_tags.extend(body.xpath('.//a[descendant::img]'))
    for bad_tag in set(bad_tags):
        bad_tag.drop_tag()

    # code - > pre
    # convert multiline code into pre
    code_elements = body.xpath('.//code')
    for code_element in code_elements:
        if '\n' in code_element.text_content():
            code_element.tag = 'pre'

    for fragment in body.getchildren():
        if fragment.tag not in allowed_top_level_tags:
            paragraph = _create_element('p')
            fragment.addprevious(paragraph)
            paragraph.append(fragment)
        else:
            # convert and append text nodes after closing tag
            if fragment.tail and len(fragment.tail.strip()) != 0:
                paragraph = _create_element('p')
                paragraph.text = fragment.tail
                fragment.tail = None
                fragment.addnext(paragraph)

    images_to_wrap = body.xpath('.//img[not(ancestor::figure)]')
    for image in images_to_wrap:
        _wrap_figure(image)

    return body if len(body.getchildren()) else None


def post_process(body):

    elements_not_empty = './/*[%s]' % '|'.join(['self::' + x for x in elements_with_text])
    bad_tags = body.xpath(elements_not_empty)

    for x in bad_tags:
        if len(x.text_content().strip()) == 0:
            x.drop_tag()

    # group following pre elements into single one (telegraph is buggy)
    join_following_elements(body.xpath('.//pre'), join_string="\n")

    # remove class attributes for all
    elements_with_class = body.xpath('.//*[@class]')
    for element in elements_with_class:
        element.attrib.pop('class')

    # remove empty figure
    for x in body.xpath('.//figure[not(descendant::*[self::iframe|self::figcaption|self::img|self::video])]'
                        '[not(normalize-space(text()))]'):
        x.drop_tree()


def _recursive_convert(element):

    fragment_root_element = {
        'tag': element.tag
    }

    content = []
    if element.text:
        content.append(element.text)

    if element.attrib:
        fragment_root_element.update({
            'attrs': dict(element.attrib)
        })

    for child in element:
        content.append(_recursive_convert(child))
        # Append Text node after element, if exists
        if child.tail:
            content.append(child.tail)

    if len(content):
        fragment_root_element.update({
            'children': content
        })

    return fragment_root_element


def _recursive_convert_json(element):

    content = _create_element(element.get('tag'))

    attributes = element.get('attrs')
    if attributes:
        # preserve order to conform the tests
        for attr in [(key, attributes[key]) for key in sorted(attributes.keys())]:
            content.set(attr[0], attr[1])
    children = element.get('children') or []
    for child in children:
        if not isinstance(child, (dict, list)):
            # temporarily wrap text with span tag
            content.append(_create_element('span', text=child))
        else:
            content.append(_recursive_convert_json(child))

    return content


def convert_json_to_html(elements):
    content = html.fragment_fromstring('<div></div>')
    for element in elements:
        content.append(_recursive_convert_json(element))
    content.make_links_absolute(base_url=base_url)
    for x in content.xpath('.//span'):
        x.drop_tag()
    html_string = html.tostring(content, encoding='unicode')
    html_string = replace_line_breaks_except_pre(html_string, '<br/>')
    html_string = html_string[5:-6]
    return html_string


def convert_html_to_telegraph_format(html_string, clean_html=True, output_format="json_string"):
    if clean_html:
        html_string = clean_article_html(html_string)

        body = preprocess_fragments(
            _fragments_from_string(html_string)
        )
        if body is not None:
            desc = [x for x in body.iterdescendants()]
            for tag in desc:
                preprocess_media_tags(tag)
            move_to_top(body)
            post_process(body)
    else:
        fragments = _fragments_from_string(html_string)
        body = fragments[0].getparent() if len(fragments) else None

    content = []
    if body is not None:
        content = [_recursive_convert(x) for x in body.iterchildren()]

    if output_format == 'json_string':
        return json.dumps(content, ensure_ascii=False)
    elif output_format == 'python_list':
        return content
    elif output_format == 'html_string':
        return html.tostring(body, encoding='unicode')


def _upload(title, author, text,
            author_url='', tph_uuid=None, page_id=None, user_agent=default_user_agent, convert_html=True,
            clean_html=True):

    if not title:
        raise TitleRequiredError('Title is required')
    if not text:
        raise TextRequiredError('Text is required')

    content = convert_html_to_telegraph_format(text, clean_html) if convert_html else text
    cookies = dict(tph_uuid=tph_uuid) if tph_uuid and page_id else None

    fields = {
        'Data': ('content.html', content, 'plain/text'),
        'title': title,
        'author': author,
        'author_url': author_url,
        'page_id': page_id or '0',
        'save_hash': ''
    }

    m = MultipartEncoder(fields, boundary='TelegraPhBoundary21')

    headers = {
        'Content-Type': m.content_type,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'User-Agent': user_agent,
        'Origin': 'http://telegra.ph'
    }
    with requests.Session() as r:
        r.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))

        response = r.post(save_url, timeout=4, headers=headers, cookies=cookies, data=m.to_string())
        result = json.loads(response.text)
        if 'path' in result:
            result['tph_uuid'] = response.cookies.get('tph_uuid') or tph_uuid
            result['url'] = base_url + '/' + result['path']
            return result
        else:
            error_msg = result['error'] if 'error' in result else ''
            raise TelegraphError(error_msg)


def _upload_via_api(title, author, text, author_url='', access_token=None, user_agent=default_user_agent,
                    convert_html=True,  clean_html=True, path=None):

    if not title:
        raise TitleRequiredError('Title is required')
    if not text:
        raise TextRequiredError('Text is required')
    if not access_token:
        raise APITokenRequiredError('API token is required')
    if not author:
        author = ''  # author is optional
    if not author_url:
        author_url = ''  # author_url is optional

    content = convert_html_to_telegraph_format(text, clean_html) if convert_html else text
    method = '/createPage' if not path else '/editPage'

    params = {
        'access_token': access_token,
        'title': title[:256],
        'author_name': author[:128],
        'author_url': author_url[:512],
        'content': content,
    }
    if path:
        params.update({'path': path})

    resp = requests.post(api_url + method, params, headers={'User-Agent': user_agent}).json()
    if resp['ok'] is True:
        return {
            'path': resp['result']['path'],
            'url': base_url + '/' + resp['result']['path']
        }
    else:
        error_msg = resp['error'] if 'error' in resp else ''
        raise TelegraphError(error_msg)


def create_api_token(short_name, author_name=None, author_url=None, user_agent=default_user_agent):
    params = {
        'short_name': short_name,
    }
    if author_name:
        params.update({'author_name': author_name})
    if author_url:
        params.update({'author_url': author_url})

    resp = requests.get(api_url+'/createAccount', params, headers={'User-Agent': user_agent})
    json_data = resp.json()
    return json_data['result']


def upload_to_telegraph(title, author, text, author_url='', tph_uuid=None, page_id=None, user_agent=default_user_agent):
    return _upload(title, author, text, author_url, tph_uuid, page_id, user_agent)


class TelegraphPoster(object):
    def __init__(self, tph_uuid=None, page_id=None, user_agent=default_user_agent, clean_html=True, convert_html=True,
                 use_api=False, access_token=None):
        self.title = None
        self.author = None
        self.author_url = None
        self.text = None
        self.path = None
        self.tph_uuid = tph_uuid
        self.page_id = page_id
        self.user_agent = user_agent
        self.clean_html = clean_html
        self.convert_html = convert_html
        self.access_token = access_token or os.getenv('TELEGRAPH_ACCESS_TOKEN', None)
        self.account = None
        self.use_api = use_api
        if self.access_token:
            # use api anyway
            self.use_api = True

    def _api_request(self, method, params=None):
        params = params or {}
        if self.access_token:
            params['access_token'] = self.access_token
        resp = requests.get(api_url + '/' + method, params, headers={'User-Agent': self.user_agent})
        return resp.json()

    def post(self, title, author, text, author_url=''):
        self.path = None
        self.title = title
        self.author = author
        self.author_url = author_url
        self.text = text
        result = self.edit()
        if not self.use_api:
            self.tph_uuid = result['tph_uuid']
            self.page_id = result['page_id']
        return result

    def edit(self, title=None, author=None, text=None, author_url='', path=None):
        params = {
            'title': title or self.title,
            'author': author or self.author,
            'text': text or self.text,
            'author_url': author_url or self.author_url,
            'user_agent': self.user_agent,
            'clean_html': self.clean_html,
            'convert_html': self.convert_html
        }
        if self.use_api:
            result = _upload_via_api(access_token=self.access_token, path=path or self.path, **params)
            self.path = result['path']
            return result
        else:
            return _upload(
                tph_uuid=self.tph_uuid,
                page_id=self.page_id,
                **params
            )

    def get_account_info(self, fields=None):
        """
        Use this method to get information about a Telegraph account.
        :param fields: (Array of String, default = ['short_name','author_name','author_url'])
        List of account fields to return. Available fields: short_name, author_name, author_url, auth_url, page_count.
        :return: Returns an Account object on success.
        """
        if not self.access_token:
            raise Exception('Access token is required')

        return self._api_request('getAccountInfo', {
            'fields': json.dumps(fields) if fields else ''
        }).get('result')

    def edit_account_info(self, short_name, author_name='', author_url=''):
        """
            Use this method to update information about a Telegraph account.
            Pass only the parameters that you want to edit
        :param short_name: (String, 1-32 characters) New account name.
        :param author_name: (String, 0-128 characters) New default author name used when creating new articles.
        :param author_url: (String, 0-512 characters) New default profile link, opened when users click on the
            author's name below the title.
            Can be any link, not necessarily to a Telegram profile or channel.
        :return:  Account object with the default fields.
        """
        if not self.access_token:
            raise Exception('Access token is required')
        params = {
            'short_name': short_name
        }
        if author_name:
            params['author_name'] = author_name
        if author_url:
            params['author_url'] = author_url
        return self._api_request('editAccountInfo', params).get('result')

    def get_page(self, path, return_content=False):
        """
        Use this method to get a Telegraph page. Returns a Page object on success.
        :param path:  (String) Required. Path to the Telegraph page (in the format Title-12-31, i.e.
            everything that comes after http://telegra.ph/).
        :param return_content: (Boolean, default = false) If true, content field will be returned in Page object.
        :return: Returns a Page object on success
        """
        json_response = self._api_request('getPage', {
            'path': path,
            'return_content': return_content
        })
        if return_content:
            json_response['result']['html'] = convert_json_to_html(json_response['result']['content'])
        return json_response.get('result')

    def get_page_list(self, offset=0, limit=50):
        """
            Use this method to get a list of pages belonging to a Telegraph account.
        :param offset: Sequential number of the first page to be returned.
        :param limit: Limits the number of pages to be retrieved.
        :return: PageList object, sorted by most recently created pages first.
        """
        json_response = self._api_request('getPageList', {
            'offset': offset,
            'limit': limit
        })
        return json_response.get('result')

    def get_views(self, path, year=None, month=None, day=None, hour=None):
        """
            Use this method to get the number of views for a Telegraph article.
        :param path: Required. Path to the Telegraph page (in the format Title-12-31, where 12 is the month and 31 the
            day the article was first published).
        :param year: Required if month is passed. If passed, the number of page views for the requested year will be
            returned.
        :param month: Required if day is passed. If passed, the number of page views for the requested month will be
            returned.
        :param day: Required if hour is passed. If passed, the number of page views for the requested day will be
            returned.
        :param hour: If passed, the number of page views for the requested hour will be returned.
        :return: Returns a PageViews object on success. By default, the total number of page views will be returned.
        """
        return self._api_request('getViews', {
            'path': path,
            'year': year,
            'month': month,
            'day': day,
            'hour': hour
        }).get('result')

    def create_api_token(self, short_name, author_name=None, author_url=None):
        """
            Use this method to create a new Telegraph account.
            Most users only need one account, but this can be useful for channel administrators who would like to keep
            individual author names and profile links for each of their channels.
        :param short_name: Account name, helps users with several accounts remember which they are currently using.
            Displayed to the user above the "Edit/Publish" button on Telegra.ph, other users don't see this name.
        :param author_name: Default author name used when creating new articles.
        :param author_url: Default profile link, opened when users click on the author's name below the title.
            Can be any link, not necessarily to a Telegram profile or channel.
        :return: Account object with the regular fields and an additional access_token field.
        """
        token_data = create_api_token(short_name, author_name, author_url, self.user_agent)
        self.use_api = True
        self.account = token_data
        self.access_token = token_data['access_token']
        return token_data

    def revoke_access_token(self):
        """
            Use this method to revoke access_token and generate a new one, for example, if the user would like to reset
            all connected sessions, or you have reasons to believe the token was compromised
        :return: Account object with new access_token and auth_url fields.
        """
        if not self.access_token:
            raise Exception('Access token is required')

        json_response = self._api_request('revokeAccessToken')
        if json_response['ok'] is True:
            self.access_token = json_response['result']['access_token']

        return json_response['result']

    def create_page(self, *args, **kwargs):
        """
            Shortcut method for post()
        """
        return self.post(*args, **kwargs)

    def edit_page(self, *args, **kwargs):
        """
            Shortcut method for edit()
        """
        return self.edit(*args, **kwargs)

    def create_account(self, *args, **kwargs):
        """
            Shortcut method for create_api_token()
        """
        return self.create_api_token(*args, **kwargs)
