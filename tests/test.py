# coding=utf8
import unittest
from html_telegraph_poster.html_to_telegraph import convert_html_to_telegraph_format
from html_telegraph_poster.upload_images import upload_image
import json


class TelegraphConversionTest(unittest.TestCase):

    def assertJson(self, first, second):
        self.assertEqual(
            first,
            json.loads(second)
        )

    def test_text_on_top(self):
        html = '''
<div>
    text as first child node
    <h1> Text Header </h1>
    <p> Text Para</p>
</div>
        '''
        self.assertJson(
            [
                {"children": ["text as first child node    "], "tag": "p"},
                {"children": [" Text Header "], "tag": "h3"},
                {"children": [" Text Para"], "tag": "p"}
             ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_em(self):
        html = '<em> Em text </em>'
        # Text node after inline element should be wrapped into single paragraph together with em
        html_text_after = '<em> Em text </em>Text node after'
        # Text node before inline element should be wrapped into separate paragraph
        html_text_before = 'text node before <em> Em text </em>'

        self.assertJson(
            [{"children": [{"tag": "em", "children": [" Em text "]}], "tag": "p"}],
            convert_html_to_telegraph_format(html, clean_html=True)
        )
        self.assertJson(
            [{"children": [{"tag": "em", "children": [" Em text "]}, "Text node after"], "tag": "p"}],
            convert_html_to_telegraph_format(html_text_after, clean_html=True)
        )
        self.assertJson(
            [{'children': ["text node before "], "tag": "p"}, {"children": [{"tag": "em", "children": [" Em text "]}], "tag": "p"}],
            convert_html_to_telegraph_format(html_text_before, clean_html=True)
        )

    def test_em_with_div(self):
        html = '''
<div>
    <em> Em text </em>
</div>
        '''
        self.assertJson(
            [
                {"children": [{"tag": "em", "children": [" Em text "]}], "tag": "p"}
            ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_em_with_div_text_after(self):
        html = '''
<div>
    <em> Em text </em>
</div> Some text node after div
        '''
        self.assertJson(
            [
                {"children": [{"tag": "em", "children": [" Em text "]}, ' Some text node after div'], "tag": "p"}
            ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_header_elements(self):
        html = '<h1> H1 header (h3) </h1>' \
               '<h2> H2 header (h4) </h2>' \
               '<h3> h3 header </h3>' \
               '<h4> h4 header </h4>' \
               '<h5> h5 header (h4) </h5>' \
               '<h6> h6 header (h4) </h6>'
        self.assertJson(
            [
                {"children": [" H1 header (h3) "], "tag": "h3"},
                {"children": [" H2 header (h4) "], "tag": "h4"},
                {"children": [" h3 header "], "tag": "h3"},
                {"children": [" h4 header "], "tag": "h4"},
                {"children": [" h5 header (h4) "], "tag": "h4"},
                {"children": [" h6 header (h4) "], "tag": "h4"}
            ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_h3_after_text(self):
        html = '<h3> H3 header</h3> text after h3 header'
        self.assertJson(
            [
                {"children": [" H3 header"], "tag": "h3"},
                {"children": [" text after h3 header"], "tag": "p"}
            ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_h3_after_text_with_br(self):
        html = '<h3> H3 header</h3> text after h3 header<br/> and new line'
        self.assertJson(
            [
                {"children": [" H3 header"], "tag": "h3"},
                {"children": [" text after h3 header\nand new line"], "tag": "p"}
            ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_image_inside_paragraph(self):
        html = '<p> <img src="image0.jpg"/></p>' \
               '<p>  <span> <img src="image1.jpg"/>   </span> <img src="image2.jpg"/> </p>'

        para_with_text = '<p>  <span> <img src="image1.jpg"/>abc </span> </p>'
        para_with_figure = '<p> <figure> <img src="image0.jpg"/> <figcaption>test</figcaption></figure> </p>'

        self.assertJson(
            [
                {"children": [{"attrs": {"src": "image0.jpg"}, "tag": "img"}], "tag": "figure"},
                {"children": [{"attrs": {"src": "image1.jpg"}, "tag": "img"}], "tag": "figure"},
                {"children": [{"attrs": {"src": "image2.jpg"}, "tag": "img"}], "tag": "figure"}
            ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )
        self.assertJson(
            [
                {'tag': 'p', 'children': ['   ', {'tag': 'img', 'attrs': {'src': 'image1.jpg'}}, 'abc  ']}
            ],
            convert_html_to_telegraph_format(para_with_text, clean_html=True)
        )
        self.assertJson(
            [
                {'tag': 'figure', 'children': [' ', {'tag': 'img', 'attrs': {'src': 'image0.jpg'}}, ' ',
                                                {'tag': 'figcaption', 'children': ['test']}]}
            ],
            convert_html_to_telegraph_format(para_with_figure, clean_html=True)
        )

    def test_image_tag_at_the_top(self):
        html = '<img src="image.jpg" title="image"/>'
        html_with_text_after = '<img src="image.jpg" title="image"/> Text after'
        html_with_text_before = 'Text before <img src="image.jpg" title="image"/>'
        html_joined = html_with_text_before + html_with_text_after
        self.assertJson(
            [
                {"children": [{"attrs": {"src": "image.jpg"}, "tag": "img"}], "tag": "p"}
            ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

        self.assertJson(
            [
                {"children": [{"attrs": {"src": "image.jpg"}, "tag": "img"}, ' Text after'], "tag": "p"}
            ],
            convert_html_to_telegraph_format(html_with_text_after, clean_html=True)
        )

        self.assertJson(
            [
                {"children": ["Text before "], "tag": "p"},
                {"children": [{"attrs": {"src": "image.jpg"}, "tag": "img"}], "tag": "p"}
            ],
            convert_html_to_telegraph_format(html_with_text_before, clean_html=True)
        )
        self.assertJson(
            [
                {"children": ["Text before "], "tag": "p"},
                {"children": [{"attrs": {"src": "image.jpg"}, "tag": "img"}], "tag": "p"},
                {"children": [{"attrs": {"src": "image.jpg"}, "tag": "img"}, " Text after"], "tag": "p"}
            ],
            convert_html_to_telegraph_format(html_joined, clean_html=True)
        )

    def test_figure_inside(self):
        html_figure_inside = '<div><figure>Some figure content</figure><p>paragraph text</p></div>'
        html_figure_inside_with_img = '<div><figure>Some figure content <img src="image.png"/></figure></div>'
        self.assertJson(
            [
                {"children": ["Some figure content"], "tag": "figure"},
                {"children": ["paragraph text"], "tag": "p"}
            ],
            convert_html_to_telegraph_format(html_figure_inside, clean_html=True)
        )

        self.assertJson(
            [
                {"children": ["Some figure content ", {"attrs": {"src": "image.png"}, "tag": "img"}], "tag": "figure"}
            ],
            convert_html_to_telegraph_format(html_figure_inside_with_img, clean_html=True)
        )

    def test_br_tags(self):
        # multiple br tags should be replaced with one line break
        html = '<br><br /> <br class="somebrclass">  <div>' \
               '</div> <br id="somebrid"/> <p>text</p> <br>'
        html2 = '<br><br /> <br clear="someoldattribute">  <div>' \
               '</div> <br/> text <br>'
        self.assertJson(
            [{'tag': 'p', 'children': ['text']}],
            convert_html_to_telegraph_format(html, clean_html=True)
        )
        self.assertJson(
            [
                {'children': ['\ntext \n'], 'tag': 'p'}
            ],
            convert_html_to_telegraph_format(html2, clean_html=True)
        )

    def test_iframe(self):
        # multiple br tags should be replaced with one line break
        html = '<iframe src="//www.youtube.com/embed/abcdef"></iframe>'
        iframe_empty_src = '<iframe src=""></iframe>'
        iframe_no_src = '<iframe></iframe>'
        iframe_child_no_src = '<p><iframe></iframe></p>'
        iframe_text_before = 'text before <iframe></iframe>'
        mix = iframe_child_no_src + html + iframe_empty_src + iframe_no_src
        self.assertJson(
            [
                {'tag': 'p', 'children': [{'tag': 'figure', 'children': [{'tag': 'iframe', 'attrs': {
                'src': '/embed/youtube?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dabcdef'}}]}]}
             ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )
        self.assertJson(
            [],
            convert_html_to_telegraph_format(iframe_empty_src, clean_html=True)
        )
        self.assertJson(
            [],
            convert_html_to_telegraph_format(iframe_no_src, clean_html=True)
        )
        self.assertJson(
            [],
            convert_html_to_telegraph_format(iframe_child_no_src, clean_html=True)
        )

        self.assertJson(
            [
                {'tag': 'p', 'children': [{'tag': 'figure', 'children': [{'tag': 'iframe', 'attrs': {
                    'src': '/embed/youtube?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dabcdef'}}]}]}
            ],
            convert_html_to_telegraph_format(mix, clean_html=True)
        )

        self.assertJson(
            [
                {'children': ['text before '], 'tag': 'p'}
            ],
            convert_html_to_telegraph_format(iframe_text_before, clean_html=True)
        )

    def test_twitter_links(self):
        html = '''
        <blockquote class="twitter-tweet"><p>
        <a href="https://twitter.com/JoshConstine">@JoshConstine</a>
        <a href="https://twitter.com/TechCrunch">@TechCrunch</a> The distribution of games</p>
        <a href="https://twitter.com/durov/status/803680844200210432"></a></blockquote>
        '''
        self.assertJson(
            [
                {'tag': 'figure', 'children': [{'tag': 'iframe', 'attrs': {
                    'src': '/embed/twitter?url=https%3A%2F%2Ftwitter.com%2Fdurov%2Fstatus%2F803680844200210432'}}]}
            ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_lists(self):
        html = '''
        <ul>
            <li>abc</li>
            <li>def</li>
        </ul>
        <ol>
            <li>first</li>
            <li>second</li>
        </ol>
        '''
        empty_list = '''
        <ul>
            <li></li>
            <li>second</li>
        </ul>
        <ul><li></li>
        </ul>
        <ol></ol>
        <ol>
            <li>first</li>
            <li>    </li>
        </ol>
        '''

        self.assertJson(
            [
                {'tag': 'ul', 'children': [{'tag': 'li', 'children': ['abc']}, {'tag': 'li', 'children': ['def']}]},
                {'tag': 'ol', 'children': [{'tag': 'li', 'children': ['first']}, {'tag': 'li', 'children': ['second']}]}
            ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )
        self.assertJson(
            [
                {'tag': 'ul', 'children': [{'tag': 'li', 'children': ['second']}]},
                {'tag': 'ol', 'children': [{'tag': 'li', 'children': ['first']}]}
            ],
            convert_html_to_telegraph_format(empty_list, clean_html=True)
        )


class UploadImageTest(unittest.TestCase):

    def test_upload(self):
        telegraph_url = upload_image('http://httpbin.org/image/jpeg')
        self.assertIn('https://telegra.ph/file/', telegraph_url)
