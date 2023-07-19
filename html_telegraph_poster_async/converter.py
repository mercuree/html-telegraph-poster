# encoding=utf8
import json
import re
import sys
from lxml import html
from lxml.html.clean import Cleaner

if sys.version_info[0] == 2:
    from urllib import quote_plus
    from urlparse import urlparse
else:
    from urllib.parse import urlparse, quote_plus

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


class OutputFormat:
    HTML_STRING = 'html_string'
    JSON_STRING = 'json_string'
    PYTHON_LIST = 'python_list'


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
    if isinstance(fragments[0], str):
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
    paras_inside_quote = body.xpath(
        './/*[self::blockquote|self::aside|self::figure]//'
        'p[descendant-or-self::*[text()]][following-sibling::*[text()]]'
    )
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


def convert_json_to_html(elements, base_url='http://telegra.ph'):
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


def convert_html_to_telegraph_format(html_string, clean_html=True, output_format=OutputFormat.JSON_STRING):
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

    if output_format == OutputFormat.JSON_STRING:
        return json.dumps(content, ensure_ascii=False)
    elif output_format == OutputFormat.PYTHON_LIST:
        return content
    elif output_format == OutputFormat.HTML_STRING:
        return html.tostring(body, encoding='unicode')
