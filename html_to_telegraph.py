# encoding=utf8
import lxml


def _recursive_convert(element):
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

    for el in element:
        content.append(_recursive_convert(el))
        # Append Text node after element, if exists
        if el.tail:
            content.append({'t': el.tail})

    if len(content):
        fragment_root_element.update({
            'c': content
        })

    return fragment_root_element


def convert_html_to_telegraph_format(html_string):
    return [
        _recursive_convert(fragment) for fragment in lxml.html.fragments_fromstring(html_string)
    ]
