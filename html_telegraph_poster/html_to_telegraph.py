# encoding=utf8
import json
import re
from lxml import html
from lxml.html.clean import Cleaner
import requests
from requests.compat import urlparse, quote_plus
from requests_toolbelt import MultipartEncoder
from .errors import *

base_url = 'https://telegra.ph'
save_url = 'https://edit.telegra.ph/save'
default_user_agent = 'Python_telegraph_poster/0.1'
allowed_tags = ['a', 'aside', 'b', 'blockquote', 'br', 'code', 'em', 'figcaption', 'figure', 'h3', 'h4', 'hr', 'i',
                'iframe', 'img', 'li', 'ol', 'p', 'pre', 's', 'strong', 'u', 'ul', 'video']
allowed_top_level_tags = ['aside', 'blockquote', 'pre', 'figure', 'h3', 'h4', 'hr', 'ol', 'p', 'ul']

youtube_re = r'(https?:)?//(www\.)?youtube(-nocookie)?\.com/embed/'
vimeo_re = r'(https?:)?//player\.vimeo\.com/video/(\d+)'
twitter_re = re.compile(r'(https?:)?//(www\.)?twitter\.com/[A-Za-z0-9_]{1,15}/status/\d+')
pre_content_re = re.compile(r'<(pre|code)(>|\s[^>]*>)[\s\S]*?</\1>')
line_breaks_and_empty_strings = re.compile('(^[\s\t]*)?\r?\n', flags=re.MULTILINE)


def clean_article_html(html_string):

    html_string = html_string.replace('<h1', '<h3').replace('</h1>', '</h3>')
    # telegram will convert <b> anyway
    html_string = re.sub(r'<(/?)b(?=\s|>)', r'<\1strong', html_string)
    html_string = re.sub(r'<(/?)(h2|h5|h6)', r'<\1h4', html_string)

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


def replace_line_breaks_except_pre(html_string):
    # Remove all line breaks and empty strings, except pre tag
    # how to make it in one string? :\
    pre_ranges = [0]
    out = ''

    # get <pre> start/end postion
    for x in pre_content_re.finditer(html_string):
        start, end = x.start(), x.end()
        pre_ranges.extend((start, end))
    pre_ranges.append(len(html_string))

    # all odd elements are <pre>, leave them untouched
    for k in range(1, len(pre_ranges)):
        part = html_string[pre_ranges[k-1]:pre_ranges[k]]
        if k % 2 == 0:
            out += part
        else:
            out += line_breaks_and_empty_strings.sub('', part)
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
    return fragments


def preprocess_media_tags(element):
    if isinstance(element, html.HtmlElement):
        if element.tag in ['ol', 'ul']:
            # ignore any spaces between <ul> and <li>
            element.text = ''
        elif element.tag == 'li':
            # ignore spaces after </li>
            element.tail = ''
        elif element.tag == 'iframe' and element.get('src'):
            iframe_src = element.get('src')
            youtube = re.match(youtube_re, iframe_src)
            vimeo = re.match(vimeo_re, iframe_src)
            if youtube or vimeo:
                if youtube:
                    yt_id = urlparse(iframe_src).path.replace('/embed/', '')
                    element.set('src', '/embed/youtube?url=' + quote_plus('https://www.youtube.com/watch?v=' + yt_id))
                elif vimeo:
                    element.set('src', '/embed/vimeo?url=' + quote_plus('https://vimeo.com/' + vimeo.group(2)))

                if not len(element.xpath('./ancestor::figure')):
                    _wrap_figure(element)

        elif element.tag == 'blockquote' and element.get('class') == 'twitter-tweet':
            twitter_links = element.xpath('.//a')
            for tw_link in twitter_links:
                if twitter_re.match(tw_link.get('href')):
                    twitter_frame = html.HtmlElement()
                    twitter_frame.tag = 'iframe'
                    twitter_frame.set('src', '/embed/twitter?url=' + quote_plus(tw_link.get('href')))
                    element.addprevious(twitter_frame)
                    _wrap_figure(twitter_frame)
                    element.drop_tree()


def move_to_top(body):
    # this should be improved to include nested elements (like lists)
    # still buggy
    elements = body.xpath('./*/figure')
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

    # bad iframes
    ns = {'re': "http://exslt.org/regular-expressions"}
    bad_tags.extend(fragments[-1].xpath("//iframe[not(re:test(@src, '%s|%s', 'i'))]" % (youtube_re, vimeo_re), namespaces=ns))
    # figcaption may have only text content
    bad_tags.extend(fragments[-1].xpath("//figcaption//*"))

    # drop all tags inside pre
    bad_tags.extend(fragments[-1].xpath("//pre//*"))

    # bad lists (remove lists/list items if empty)
    nodes_not_to_be_empty = fragments[-1].xpath('//ul|//ol|//li')
    bad_tags.extend([x for x in nodes_not_to_be_empty if len(x.text_content().strip()) == 0])
    # remove links with images inside
    bad_tags.extend(body.xpath('.//a[descendant::img]'))
    for bad_tag in bad_tags:
        bad_tag.drop_tag()
        if bad_tag in fragments:
            fragments.remove(bad_tag)

    # code - > pre
    # convert multiline code into pre
    code_elements = body.xpath('.//code')
    for code_element in code_elements:
        if '\n' in code_element.text:
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
                fragment.addnext(paragraph)
                fragment.tail = ''

    images_to_wrap = body.xpath('.//img[not(ancestor::figure)]')
    for image in images_to_wrap:
        _wrap_figure(image)

    return len(body.getchildren()) and body or None


def post_process(body):

    bad_tags = body.xpath('//p|//a')

    for x in bad_tags:
        if len(x.text_content().strip()) == 0:
            x.drop_tag()

    # group following pre elements into single one (telegraph is buggy)
    join_following_elements(body.xpath('//pre'), join_string="\n")

    # remove class attributes for all
    elements_with_class = body.xpath('.//*[@class]')
    for element in elements_with_class:
        element.attrib.pop('class')


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


def convert_html_to_telegraph_format(html_string, clean_html=True):
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

    return json.dumps(content, ensure_ascii=False)


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
        'page_id': page_id or '0'
    }

    m = MultipartEncoder(fields, boundary='TelegraPhBoundary21')

    headers = {
        'Content-Type': m.content_type,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'User-Agent': user_agent
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
        error_msg = result['error'] if 'error' in result else ''
        raise TelegraphError(error_msg)


def upload_to_telegraph(title, author, text, author_url='', tph_uuid=None, page_id=None, user_agent=default_user_agent):
    return _upload(title, author, text, author_url, tph_uuid, page_id, user_agent)


class TelegraphPoster(object):
    def __init__(self, tph_uuid=None, page_id=None, user_agent=default_user_agent, clean_html=True):
        self.title = None
        self.author = None
        self.author_url = None
        self.text = None
        self.tph_uuid = tph_uuid
        self.page_id = page_id
        self.user_agent = user_agent
        self.clean_html = clean_html

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
        return _upload(
            title=title or self.title,
            author=author or self.author,
            text=text or self.text,
            author_url=self.author_url,
            tph_uuid=self.tph_uuid,
            page_id=self.page_id,
            user_agent=self.user_agent,
            clean_html=self.clean_html
        )
