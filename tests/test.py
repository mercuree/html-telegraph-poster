# coding=utf8
import unittest
from html_telegraph_poster.html_to_telegraph import convert_html_to_telegraph_format
import json


def json_loads_byteified(json_text):
    return _byteify(
        json.loads(json_text, object_hook=_byteify),
        ignore_dicts=True
    )

# thanks stackoverflow
def _byteify(data, ignore_dicts = False):
    # if this is a unicode string, return its string representation
    if isinstance(data, unicode):
        return data.encode('utf-8')
    # if this is a list of values, return list of byteified values
    if isinstance(data, list):
        return [ _byteify(item, ignore_dicts=True) for item in data ]
    # if this is a dictionary, return dictionary of byteified keys and values
    # but only if we haven't already byteified it
    if isinstance(data, dict) and not ignore_dicts:
        return {
            _byteify(key, ignore_dicts=True): _byteify(value, ignore_dicts=True)
            for key, value in data.iteritems()
        }
    # if it's anything else, return it in its original form
    return data


class TelegraphConversionTest(unittest.TestCase):

    def test_text_on_top(self):
        html = '''
<div>
    text as first child node
    <h1> Text Header </h1>
    <p> Text Para</p>
</div>
        '''
        self.assertEqual(
            [
                {"c": [{"t": "text as first child node    "}], "_": "p"},
                {"c": [{"t": " Text Header "}], "_": "h3"},
                {"c": [{"t": " Text Para"}], "_": "p"}
             ],
            json_loads_byteified(convert_html_to_telegraph_format(html, clean_html=True))
        )

    def test_em(self):
        html = '<em> Em text </em>'
        # Text node after inline element should be wrapped into single paragraph together with em
        html_text_after = '<em> Em text </em>Text node after'
        # Text node before inline element should be wrapped into separate paragraph
        html_text_before = 'text node before <em> Em text </em>'

        self.assertEqual(
            [{"c": [{"_": "em", "c": [{"t": " Em text "}]}], "_": "p"}],
            json_loads_byteified(convert_html_to_telegraph_format(html, clean_html=True))
        )
        self.assertEqual(
            [{"c": [{"_": "em", "c": [{"t": " Em text "}]}, {"t": "Text node after"}], "_": "p"}],
            json_loads_byteified(convert_html_to_telegraph_format(html_text_after, clean_html=True))
        )
        self.assertEqual(
            [{'c': [{'t': 'text node before '}], '_': 'p'}, {"c": [{"_": "em", "c": [{"t": " Em text "}]}], "_": "p"}],
            json_loads_byteified(convert_html_to_telegraph_format(html_text_before, clean_html=True))
        )

    def test_em_with_div(self):
        html = '''
<div>
    <em> Em text </em>
</div>
        '''
        self.assertEqual(
            [
                {"c": [{"_": "em", "c": [{"t": " Em text "}]}], "_": "p"}
            ],
            json_loads_byteified(convert_html_to_telegraph_format(html, clean_html=True))
        )

    def test_em_with_div_text_after(self):
        html = '''
<div>
    <em> Em text </em>
</div> Some text node after div
        '''
        self.assertEqual(
            [
                {"c": [{"_": "em", "c": [{"t": " Em text "}]}, {'t': ' Some text node after div'}], "_": "p"}
            ],
            json_loads_byteified(convert_html_to_telegraph_format(html, clean_html=True))
        )

    def test_header_elements(self):
        html = '<h1> H1 header (h3) </h1>' \
               '<h2> H2 header (h4) </h2>' \
               '<h3> h3 header </h3>' \
               '<h4> h4 header </h4>' \
               '<h5> h5 header (h4) </h5>' \
               '<h6> h6 header (h4) </h6>'
        self.assertEqual(
            [
                {"c": [{"t": " H1 header (h3) "}], "_": "h3"},
                {"c": [{"t": " H2 header (h4) "}], "_": "h4"},
                {"c": [{"t": " h3 header "}], "_": "h3"},
                {"c": [{"t": " h4 header "}], "_": "h4"},
                {"c": [{"t": " h5 header (h4) "}], "_": "h4"},
                {"c": [{"t": " h6 header (h4) "}], "_": "h4"}
            ],
            json_loads_byteified(convert_html_to_telegraph_format(html, clean_html=True))
        )

    def test_h3_after_text(self):
        html = '<h3> H3 header</h3> text after h3 header'
        self.assertEqual(
            [
                {"c": [{"t": " H3 header"}], "_": "h3"},
                {"c": [{"t": " text after h3 header"}], "_": "p"}
            ],
            json_loads_byteified(convert_html_to_telegraph_format(html, clean_html=True))
        )

    def test_h3_after_text_with_br(self):
        html = '<h3> H3 header</h3> text after h3 header<br/> and new line'
        self.assertEqual(
            [
                {"c": [{"t": " H3 header"}], "_": "h3"},
                {"c": [{"t": " text after h3 header\nand new line"}], "_": "p"}
            ],
            json_loads_byteified(convert_html_to_telegraph_format(html, clean_html=True))
        )

    def test_image_tag_at_the_top(self):
        html = '<img src="image.jpg" title="image"/>'
        html_with_text_after = '<img src="image.jpg" title="image"/> Text after'
        html_with_text_before = 'Text before <img src="image.jpg" title="image"/>'
        html_joined = html_with_text_before + html_with_text_after
        self.assertEqual(
            [
                {"c": [{"a": {"src": "image.jpg", "title": "image"}, "_": "img"}], "_": "p"}
            ],
            json_loads_byteified(convert_html_to_telegraph_format(html, clean_html=True))
        )

        self.assertEqual(
            [
                {"c": [{"a": {"src": "image.jpg", "title": "image"}, "_": "img"}, {'t': ' Text after'}], "_": "p"}
            ],
            json_loads_byteified(convert_html_to_telegraph_format(html_with_text_after, clean_html=True))
        )

        self.assertEqual(
            [
                {"c": [{"t": "Text before "}], "_": "p"},
                {"c": [{"a": {"src": "image.jpg", "title": "image"}, "_": "img"}], "_": "p"}
            ],
            json_loads_byteified(convert_html_to_telegraph_format(html_with_text_before, clean_html=True))
        )
        self.assertEqual(
            [
                {"c": [{"t": "Text before "}], "_": "p"},
                {"c": [{"a": {"src": "image.jpg", "title": "image"}, "_": "img"}], "_": "p"},
                {"c": [{"a": {"src": "image.jpg", "title": "image"}, "_": "img"}, {"t": " Text after"}], "_": "p"}
            ],
            json_loads_byteified(convert_html_to_telegraph_format(html_joined, clean_html=True))
        )

    def test_figure_inside(self):
        html_figure_inside = '<div><figure>Some figure content</figure><p>paragraph text</p></div>'
        html_figure_inside_with_img = '<div><figure>Some figure content <img src="image.png"/></figure></div>'
        self.assertEqual(
            [
                {"c": [{"t": "Some figure content"}], "_": "figure"},
                {"c": [{"t": "paragraph text"}], "_": "p"}
            ],
            json_loads_byteified(convert_html_to_telegraph_format(html_figure_inside, clean_html=True))
        )

        self.assertEqual(
            [
                {"c": [{"t": "Some figure content "}, {"a": {"src": "image.png"}, "_": "img"}], "_": "figure"}
            ],
            json_loads_byteified(convert_html_to_telegraph_format(html_figure_inside_with_img, clean_html=True))
        )

    def test_br_tags(self):
        # multiple br tags should be replaced with one line break
        html = '<br><br /> <br class="somebrclass">  <div>' \
               '</div> <br id="somebrid"/> <p>text</p> <br>'
        html2 = '<br><br /> <br clear="someoldattribute">  <div>' \
               '</div> <br/> text <br>'
        self.assertEqual(
            [{'_': 'p', 'c': [{'t': 'text'}]}],
            json_loads_byteified(convert_html_to_telegraph_format(html, clean_html=True))
        )
        self.assertEqual(
            [
                {'c': [{'t': '\ntext \n'}], '_': 'p'}
            ],
            json_loads_byteified(convert_html_to_telegraph_format(html2, clean_html=True))
        )
