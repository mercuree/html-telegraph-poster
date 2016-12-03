# encoding=utf8
from lxml import html


def _recursive_convert(element):
    # All strings outside tags should be ignored
    if not isinstance(element, html.HtmlElement):
        return

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


def convert_html_to_telegraph_format(html_string):
    return [
        _recursive_convert(fragment) for fragment in html.fragments_fromstring(html_string)
    ]
