# coding=utf8
import unittest
from html_telegraph_poster.converter import convert_html_to_telegraph_format
from html_telegraph_poster.converter import convert_json_to_html
import json


class JSONAssertion(unittest.TestCase):
    def assertJson(self, first, second):
        self.assertEqual(
            first,
            json.loads(second)
        )


class TelegraphConversionTest(JSONAssertion):

    def test_text_only_plain(self):
        html = 'only plain text'
        self.assertJson(
            [{'children': ['only plain text'], 'tag': 'p'}],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_text_only_empty(self):
        html_empty_string = '               '
        self.assertJson(
            [],
            convert_html_to_telegraph_format(html_empty_string, clean_html=True)
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
                {"children": ["text as first child node "], "tag": "p"},
                {"children": [" Text Header "], "tag": "h3"},
                {"children": [" Text Para"], "tag": "p"}
             ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_text_after_para(self):
        html = ' <p>text inside para</p> Text after para'
        self.assertEqual(
            '<body><p>text inside para</p><p> Text after para</p></body>',
            convert_html_to_telegraph_format(html, output_format='html_string', clean_html=True)
        )

    def test_em(self):
        html = '<em> Em text </em>'
        self.assertJson(
            [{"children": [{"tag": "em", "children": [" Em text "]}], "tag": "p"}],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_em_text_after_html(self):
        # Text node after inline element should be wrapped into single paragraph together with em
        html_text_after = '<em> Em text </em>Text node after'
        self.assertJson(
            [{"children": [{"tag": "em", "children": [" Em text "]}, "Text node after"], "tag": "p"}],
            convert_html_to_telegraph_format(html_text_after, clean_html=True)
        )

    def test_em_text_before_html(self):
        # Text node before inline element should be wrapped into separate paragraph
        html_text_before = 'text node before <em> Em text </em>'
        self.assertJson(
            [{'children': ["text node before "], "tag": "p"},
             {"children": [{"tag": "em", "children": [" Em text "]}], "tag": "p"}],
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

    def test_figure_inside(self):
        html_figure_inside = '<div><figure>Some figure content</figure><p>paragraph text</p></div>'
        self.assertJson(
            [
                {"children": ["Some figure content"], "tag": "figure"},
                {"children": ["paragraph text"], "tag": "p"}
            ],
            convert_html_to_telegraph_format(html_figure_inside, clean_html=True)
        )

    def test_figure_inside_with_img(self):
        html_figure_inside_with_img = '<div><figure>Some figure content <img src="image.png"/></figure></div>'
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

        self.assertJson(
            [{'tag': 'p', 'children': ['text']}],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_br_tags_two(self):
        html = '<br><br /> <br clear="someoldattribute">  <div>' \
               '</div> <br/> text <br>'
        self.assertJson(
            [
                {'children': ['\ntext \n'], 'tag': 'p'}
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

        self.assertJson(
            [
                {'tag': 'ul', 'children': [{'tag': 'li', 'children': ['abc']}, {'tag': 'li', 'children': ['def']}]},
                {'tag': 'ol', 'children': [{'tag': 'li', 'children': ['first']}, {'tag': 'li', 'children': ['second']}]}
            ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_lists_empty(self):
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
                {'tag': 'ul', 'children': [{'tag': 'li', 'children': ['second']}]},
                {'tag': 'ol', 'children': [{'tag': 'li', 'children': ['first']}]}
            ],
            convert_html_to_telegraph_format(empty_list, clean_html=True)
        )

    def test_blockquote(self):
        html = '<blockquote>Text inside blockquote</blockquote>'
        self.assertJson(
            [{'children': ['Text inside blockquote'], 'tag': 'blockquote'}],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_blockquote_with_para(self):
        quote_with_para = '<blockquote><p>first para</p><p>second para</p></blockquote>'
        self.assertJson(
            [{'children': ['first para\nsecond para'], 'tag': 'blockquote'}],
            convert_html_to_telegraph_format(quote_with_para, clean_html=True)
        )

    def test_blockquote_para_strong(self):
        quote_para_strong = '<blockquote><p>first para</p><strong>strong text</strong></blockquote>'
        self.assertJson(
            [{'children': ['first para\n', {u'children': [u'strong text'], u'tag': u'strong'}], 'tag': 'blockquote'}],
            convert_html_to_telegraph_format(quote_para_strong, clean_html=True)
        )

    def test_blockquote_inside_figure(self):
        quote_inside_figure = '<figure><blockquote>Blockquote text inside figure</blockquote></figure>'
        self.assertJson(
            [{'children': ['Blockquote text inside figure'], 'tag': 'blockquote'}],
            convert_html_to_telegraph_format(quote_inside_figure, clean_html=True))

    def test_bad_para(self):
        html = '<aside><p>text inside para</p><p>another para</p></aside>'
        # TODO: write html6 test
        html6 = '''<blockquote class="cut">\n<p>text inside</p>\n</blockquote>'''
        self.assertJson(
            [{'children': ['text inside para\nanother para'], 'tag': 'aside'}],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_bad_para_inside_figcaption(self):
        html2 = '<figure><figcaption><p>text inside para</p><p>another para</p></figcaption></figure>'
        self.assertJson(
            [{'children': [{'children': ['text inside para\nanother para'], 'tag': 'figcaption'}], 'tag': 'figure'}],
            convert_html_to_telegraph_format(html2, clean_html=True)
        )

    def test_bad_para_inside_figcaption_with_link(self):
        figcaption_para_with_link = '<figure><figcaption>' \
                                    '<p><a href="https://telegram.org/">Telegram</a></p><p>Text after link</p>' \
                                    '</figcaption></figure>'
        self.assertJson(
            [{"tag": "figure", "children": [{"tag": "figcaption", "children": ["Telegram\nText after link"]}]}],
            convert_html_to_telegraph_format(figcaption_para_with_link, clean_html=True)
        )

    def test_bad_para_inside_blockquote(self):
        html3 = '<blockquote><p></p><p>second para</p></blockquote>'
        self.assertJson(
            [{'children': ['second para'], 'tag': 'blockquote'}],
            convert_html_to_telegraph_format(html3, clean_html=True)
        )

    def test_bad_para_inside_blockquote_with_em(self):
        html4 = '<blockquote><p>first para</p><strong><em></em></strong><em>em text</em></blockquote>'
        self.assertJson(
            [{'children': [u'first para\n', {'children': ['em text'], 'tag': 'em'}], 'tag': 'blockquote'}],
            convert_html_to_telegraph_format(html4, clean_html=True)
        )

    def test_bad_para_inside_blockquote_with_empty_em(self):
        html5 = '<blockquote><p>first para</p><em></em><strong></strong><em></em></blockquote>'
        self.assertJson(
            [{'children': [u'first para'], 'tag': 'blockquote'}],
            convert_html_to_telegraph_format(html5, clean_html=True)
        )

    def test_convert_without_clean(self):
        # multiple br tags should be replaced with one line break
        html = 'Text first line' \
               '<br><br /> <br class="somebrclass">  <div>' \
               '</div> <br id="somebrid"/> <p>text</p> <br>' \
               '<span><em><strong><i></i><u></u></strong></em></span>'
        self.assertJson(
            [{'tag': 'p', 'children': ['Text first line']}, {'tag': 'br'}, {'tag': 'br'},
             {'tag': 'br', 'attrs': {'class': 'somebrclass'}}, {'tag': 'div'},
             {'tag': 'br', 'attrs': {'id': 'somebrid'}}, {'tag': 'p', 'children': ['text']}, {'tag': 'br'},
             {'tag': 'span',
              'children': [{'tag': 'em', 'children': [{'tag': 'strong', 'children': [{'tag': 'i'}, {'tag': 'u'}]}]}]}],
            convert_html_to_telegraph_format(html, clean_html=False)
        )

    def test_empty_links(self):
        html = '<a href="http://example.com/">   <img src="http://httpbin.org/image/jpeg"/>   </a>'

        self.assertJson(
            [
                {'tag': 'figure', 'children': [{'tag': 'img', 'attrs': {'src': 'http://httpbin.org/image/jpeg'}}]}
            ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_duplicated_bad_tags(self):
        # paragraph appears twice in bad_tags list
        text = '<aside><figure><figcaption><p>Text</p></figcaption></figure></aside>'
        self.assertJson(
            [{'children': [{'children': ['Text'], 'tag': 'figcaption'}], 'tag': 'figure'}],
            convert_html_to_telegraph_format(text, clean_html=True)
        )

    def test_remove_head(self):
        text = '<!doctype html>' \
               '<html><head><title>Title text</title></head><body><p>Para text</p></body></html>'
        self.assertJson(
            [{'children': ['Para text'], 'tag': 'p'}],
            convert_html_to_telegraph_format(text, clean_html=True)
        )

    def test_remove_processing_instructions(self):
        text = '<p>text<?xml version=”1.0″ encoding=”UTF-8″?></p>'
        self.assertJson(
            [{'children': ['text'], 'tag': 'p'}],
            convert_html_to_telegraph_format(text, clean_html=False)
        )

    def test_json_to_html(self):

        json_text = '[{"tag":"p","children":["First paragraph text (текст).\\nSecond string "]},' \
                    '{"tag":"p","children":["Next paragraph"]},{"tag":"figure","children":' \
                    '[{"tag":"img","attrs":{"src":"\/file\/d12da8bd435240bc3c6d2.jpg"}},' \
                    '{"tag":"figcaption","children":["Test girl with cat"]}]},' \
                    '{"tag":"ul","children":[{"tag":"li","children":[{"tag":"strong","children":["Unordered "]},' \
                    '"list first item"]},{"tag":"li","children":[{"tag":"em","children":["Unordered "]},"list ",' \
                    '{"tag":"a","attrs":{"href":"\/"},"children":["second "]},"item"]}]},' \
                    '{"tag":"blockquote","children":["Blockquote text Blockquote text Blockquote text ",' \
                    '{"tag":"a","attrs":{"href":"https:\/\/telegram.org\/","target":"_blank"},' \
                    '"children":["Blockquote "]},' \
                    '"text Blockquote text Blockquote text Blockquote text Blockquote text Blockquote text"]},' \
                    '{"tag":"h3","attrs":{"id":"Big-Header"},"children":["Big Header"]},' \
                    '{"tag":"h4","attrs":{"id":"Not-so-big-header"},"children":["Not so big ",' \
                    '{"tag":"a","attrs":{"href":"https:\/\/telegram.org\/","target":"_blank"},' \
                    '"children":["header"]}]},{"tag":"pre","children":["Block of code text\\nnew line\\n"]}]'

        html_text = u'<p>First paragraph text (текст).<br/>Second string </p><p>Next paragraph</p><figure>' \
            '<img src="http://telegra.ph/file/d12da8bd435240bc3c6d2.jpg"><figcaption>Test girl with cat</figcaption>' \
            '</figure><ul><li><strong>Unordered </strong>list first item</li><li><em>Unordered </em>list ' \
            '<a href="http://telegra.ph/">second </a>item</li></ul>' \
            '<blockquote>Blockquote text Blockquote text Blockquote text ' \
            '<a href="https://telegram.org/" target="_blank">Blockquote </a>' \
            'text Blockquote text Blockquote text Blockquote text Blockquote text Blockquote text</blockquote>' \
            '<h3 id="Big-Header">Big Header</h3><h4 id="Not-so-big-header">Not so big ' \
            '<a href="https://telegram.org/" target="_blank">header</a></h4><pre>Block of code text\nnew line\n</pre>'

        self.assertEqual(convert_json_to_html(json.loads(json_text)), html_text)


class TelegraphConversionIframeTest(JSONAssertion):
    def setUp(self):
        self.iframe_with_text = '<iframe src="//www.youtube.com/embed/abcdef">legacy text</iframe>'
        self.iframe_empty_src = '<iframe src=""></iframe>'
        self.iframe_no_src = '<iframe></iframe>'
        self.iframe_child_no_src = '<p><iframe></iframe></p>'

    def test_iframe_with_text(self):
        self.assertJson(
            [
                {'tag': 'figure', 'children': [{'tag': 'iframe', 'attrs': {
                    'src': '/embed/youtube?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dabcdef'}}]}
            ],
            convert_html_to_telegraph_format(self.iframe_with_text, clean_html=True)
        )

    def test_iframe_empty_src(self):
        self.assertJson(
            [],
            convert_html_to_telegraph_format(self.iframe_empty_src, clean_html=True)
        )

    def test_iframe_no_src(self):
        self.assertJson(
            [],
            convert_html_to_telegraph_format(self.iframe_no_src, clean_html=True)
        )

    def test_iframe_child_no_src(self):
        self.assertJson(
            [],
            convert_html_to_telegraph_format(self.iframe_child_no_src, clean_html=True)
        )

    def test_iframe_text_before(self):
        iframe_text_before = 'text before <iframe></iframe>'
        self.assertJson(
            [
                {'children': ['text before '], 'tag': 'p'}
            ],
            convert_html_to_telegraph_format(iframe_text_before, clean_html=True)
        )

    def test_iframe_text_after(self):
        iframe_text_after = '<p><iframe src="//www.youtube.com/embed/abcdef"></iframe>Text after </p>'
        self.assertJson(
            [
                {"tag": "figure", "children": [{"tag": "iframe", "attrs": {
                    "src": "/embed/youtube?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dabcdef"}}]},
                {"tag": "p", "children": ["Text after "]}
            ],
            convert_html_to_telegraph_format(iframe_text_after, clean_html=True)
        )

    def test_iframe_not_allowed_src(self):
        iframe_not_allowed_src = '<div><iframe src="http://example.com"></iframe></div>'
        self.assertJson(
            [],
            convert_html_to_telegraph_format(iframe_not_allowed_src, clean_html=True)
        )

    def test_iframe_vimeo(self):
        iframe_vimeo = '<iframe src="https://player.vimeo.com/video/1185346"></iframe>'
        self.assertJson(
            [
                {'tag': 'figure', 'children': [
                    {'tag': 'iframe', 'attrs': {'src': '/embed/vimeo?url=https%3A%2F%2Fvimeo.com%2F1185346'}}]}
            ],
            convert_html_to_telegraph_format(iframe_vimeo, clean_html=True)
        )

    def test_iframe_telegram(self):
        iframe_telegram = '<iframe src="https://t.me/tginfo/1220?embed=1"></iframe>'
        self.assertJson(
            [
                {'tag': 'figure', 'children': [{'tag': 'iframe', 'attrs':
                    {'src': '/embed/telegram?url=https%3A%2F%2Ft.me%2Ftginfo%2F1220%3Fembed%3D1'}}]}
            ],
            convert_html_to_telegraph_format(iframe_telegram, clean_html=True)
        )

    def test_script_telegram(self):
        script_telegram = '<script async src="https://telegram.org/js/telegram-widget.js?2" ' \
                          'data-telegram-post="tginfo/1220" data-width="100%"></script>'
        self.assertJson(
            [
                {'tag': 'figure', 'children': [{'tag': 'iframe', 'attrs':
                    {'src': '/embed/telegram?url=https%3A%2F%2Ft.me%2Ftginfo%2F1220'}}]}
            ],
            convert_html_to_telegraph_format(script_telegram, clean_html=True)
        )

    def test_iframe_mix(self):
        mix = self.iframe_child_no_src + self.iframe_with_text + self.iframe_empty_src + self.iframe_no_src
        self.assertJson(
            [
                {'tag': 'figure', 'children': [{'tag': 'iframe', 'attrs': {
                    'src': '/embed/youtube?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dabcdef'}}]}
            ],
            convert_html_to_telegraph_format(mix, clean_html=True)
        )

    def test_iframe_with_figure(self):
        iframe_with_figure = '<figure><iframe src="//www.youtube.com/embed/abcdef"></iframe>Text after </figure>'
        self.assertJson(
            [
                {u'tag': u'figure', u'children': [{u'tag': u'iframe', u'attrs': {
                    u'src': u'/embed/youtube?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dabcdef'}}, u'Text after ']}
            ],
            convert_html_to_telegraph_format(iframe_with_figure, clean_html=True)
        )

    def test_multiple_iframes(self):
        multiple_iframes = '<p>' \
                           'Text before' \
                           '<a href="/123">link</a><iframe src="//www.youtube.com/embed/abcdef"></iframe> text' \
                           '<a href="/246">link2</a> Text after link' \
                           '<iframe src="//www.youtube.com/embed/xyzxyzxyz"></iframe>' \
                           '</p>'
        self.assertJson(
            [
                {"tag": "p",
                 "children": ["Text before", {"tag": "a", "attrs": {"href": "/123"}, "children": ["link"]}]},
                {"tag": "figure", "children": [{"tag": "iframe", "attrs": {
                    "src": "/embed/youtube?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dabcdef"}}]},
                {"tag": "p", "children": [" text", {"tag": "a", "attrs": {"href": "/246"}, "children": ["link2"]},
                                          " Text after link"]},
                {"tag": "figure", "children": [{"tag": "iframe", "attrs": {
                    "src": "/embed/youtube?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dxyzxyzxyz"}}]}],
            convert_html_to_telegraph_format(multiple_iframes, clean_html=True)
        )


class TelegraphConversionCodeBlockTest(JSONAssertion):
    def test_pre_block(self):
        html = '''<pre>
        def test_code_block(self):
            html = ''
            print("hello world")
        </pre>'''
        self.assertJson(
            [
                {"tag": "pre", "children": [
                    "\n        def test_code_block(self):\n            html = ''\n            "
                    "print(\"hello world\")\n        "]}
            ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_pre_inside_para(self):
        html2 = '''
            <p><pre
            class="code">
                def hello_world():
                    print("hello")
            </pre>
            <pre>print("second pre")</pre>
            </p>
            <p> Text after pre </p>
        '''
        self.assertJson(
            [
                {"tag": "pre", "children": [
                    "\n                def hello_world():\n                    "
                    "print(\"hello\")\n            \nprint(\"second pre\")"]},
                {"tag": "p", "children": [" Text after pre "]}
            ],
            convert_html_to_telegraph_format(html2, clean_html=True)
        )

    def test_multiple_pre(self):
        html3 = '''
<pre><code class="python hljs">my_list = [<span class="hljs-number">1</span>, <span class="hljs-number">2</span>, <span class="hljs-number">3</span>, <span class="hljs-number">4</span>, <span class="hljs-number">5</span>, <span class="hljs-number">6</span>, <span class="hljs-number">7</span>]
EVEN = slice(<span class="hljs-number">1</span>, <span class="hljs-keyword">None</span>, <span class="hljs-number">2</span>)
print(my_list[EVEN])     <span class="hljs-comment"># [2, 4, 6]</span>
</code></pre>
<p> paragraph splitter</p>
<pre> String anotherCodeBlock = "separated code block"</pre>
<pre>  String anotherCodeBlock2 = "separated code block2"</pre>
<pre>  String anotherCodeBlock3 = "separated code block3"</pre>
<p> paragraph splitter</p>
<pre>  String anotherCodeBlock4 = "separated code block4"</pre>
<pre>  String anotherCodeBlock5 = "separated code block5"</pre>
<p> paragraph splitter</p>
<pre>  String anotherCodeBlock6 = "separated code block6"</pre>
                '''
        self.assertJson(
            [
                {"tag": "pre", "children": [
                    "my_list = [1, 2, 3, 4, 5, 6, 7]\nEVEN = slice(1, None, 2)\nprint(my_list[EVEN])     # [2, 4, 6]\n"]},
                {"tag": "p", "children": [" paragraph splitter"]},
                {"tag": "pre", "children": [
                    " String anotherCodeBlock = \"separated code block\"\n  String anotherCodeBlock2 = \"separated code block2\"\n  String anotherCodeBlock3 = \"separated code block3\""]},
                {"tag": "p", "children": [" paragraph splitter"]},
                {"tag": "pre", "children": [
                    "  String anotherCodeBlock4 = \"separated code block4\"\n  String anotherCodeBlock5 = \"separated code block5\""]},
                {"tag": "p", "children": [" paragraph splitter"]},
                {"tag": "pre", "children": ["  String anotherCodeBlock6 = \"separated code block6\""]}
            ],
            convert_html_to_telegraph_format(html3, clean_html=True)
        )

    def test_para_inside_pre(self):
        html4 = '''
<pre class="code literal-block"><p class="nv">$ </p>mkvirtualenv myvirtualenv --python<p class="o">=</p>/usr/bin/python3.4


Running virtualenv with interpreter /usr/bin/python3.4
Using base prefix <p class="s1">'/usr'</p>
New python executable in myvirtualenv/bin/python3.4
Also creating executable in myvirtualenv/bin/python
Installing setuptools, pip...done.
</pre>
                '''
        self.assertJson(
            [
                {"tag": "pre", "children": [
                    "$ mkvirtualenv myvirtualenv --python=/usr/bin/python3.4\n\n\n"
                    "Running virtualenv with interpreter /usr/bin/python3.4\n"
                    "Using base prefix '/usr'\n"
                    "New python executable in myvirtualenv/bin/python3.4\n"
                    "Also creating executable in myvirtualenv/bin/python\n"
                    "Installing setuptools, pip...done.\n"]}
            ],
            convert_html_to_telegraph_format(html4, clean_html=True)
        )

    def test_code_tag(self):
        html5 = '''
        <p>Text before <code> inline_code = True</code> Text after</p>
        <code> multiline_code = True
        next_line = True
        </code>
        <code></code>empty code
            '''
        self.assertJson(
            [
                {"tag": "p",
                 "children": ["Text before ", {"tag": "code", "children": [" inline_code = True"]}, " Text after"]},
                {"tag": "pre", "children": [" multiline_code = True\n        next_line = True\n        "]},
                {'tag': 'p', 'children': [{'tag': 'code'}, 'empty code']}
            ],
            convert_html_to_telegraph_format(html5, clean_html=True)
        )

    def test_br_inside_pre(self):
        html_br_inside_pre = '''
<pre># test_div.py<br>import pytest<br /><br>@pytest.fixture<br>def input_value():<br>   input = 39<br>   return input<br>
def test_divisible_by_3(input_value):<br>   assert input_value % 3 == 0<br>
def test_divisible_by_6(input_value):<br>   assert input_value % 6 == 0
</pre>
                '''
        self.assertJson(
            [{"tag": "pre", "children": [
                "# test_div.py\nimport pytest\n\n"
                "@pytest.fixture\n"
                "def input_value():\n"
                "   input = 39\n"
                "   return input\n\n"
                "def test_divisible_by_3(input_value):\n"
                "   assert input_value % 3 == 0\n\n"
                "def test_divisible_by_6(input_value):\n"
                "   assert input_value % 6 == 0\n"
            ]}],
            convert_html_to_telegraph_format(html_br_inside_pre, clean_html=True)
        )


class TelegraphConversionImagesTest(JSONAssertion):
    def setUp(self):
        self.html_with_text_after = '<img src="image1.jpg" title="image"/> Text after'
        self.html_with_text_before = 'Text before <img src="image0.jpg" title="image"/>'

    def test_images(self):
        images_without_src = '<img title="image"/>'
        self.assertJson(
            [],
            convert_html_to_telegraph_format(images_without_src, clean_html=True)
        )

    def test_image_inside_paragraph(self):
        html = '<p> <img src="image0.jpg"/></p>' \
               '<p>  <span> <img src="image1.jpg"/>   </span> <img src="image2.jpg"/> </p>'
        self.assertJson(
            [
                {"children": [{"attrs": {"src": "image0.jpg"}, "tag": "img"}], "tag": "figure"},
                {"children": [{"attrs": {"src": "image1.jpg"}, "tag": "img"}], "tag": "figure"},
                {"children": [{"attrs": {"src": "image2.jpg"}, "tag": "img"}], "tag": "figure"}
            ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_image_inside_paragraph_with_text(self):
        para_with_text = '<p> abc <span> <img src="image1.jpg"/>xyz </span> </p>'
        self.assertJson(
            [
                {"tag": "p", "children": [" abc "]},
                {"tag": "figure", "children": [{"tag": "img", "attrs": {"src": "image1.jpg"}}]},
                {"tag": "p", "children": ["xyz "]}
            ],
            convert_html_to_telegraph_format(para_with_text, clean_html=True)
        )

    def test_image_inside_paragraph_with_figure(self):
        para_with_figure = '<p> <figure> <img src="image0.jpg"/> <figcaption>test</figcaption></figure> </p>'
        self.assertJson(
            [
                {'tag': 'figure', 'children': [' ', {'tag': 'img', 'attrs': {'src': 'image0.jpg'}}, ' ',
                                                {'tag': 'figcaption', 'children': ['test']}]}
            ],
            convert_html_to_telegraph_format(para_with_figure, clean_html=True)
        )

    def test_image_inside_paragraph_with_figure_para_after(self):
        html = '<p>Text 1 <figure> <img src="image0.jpg"/> <figcaption><em>test</em></figcaption></figure> </p>' \
                    '<p>Text 2<p>'
        self.assertJson(
            [
                {"tag": "p", "children": ["Text 1 "]},
                {
                    "tag": "figure", "children":
                    [" ", {"tag": "img", "attrs": {"src": "image0.jpg"}}, " ",
                        {"tag": "figcaption", "children": ["test"]}]
                },
                {"tag": "p", "children": ["Text 2"]}
            ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_image_inside_paragraph_without_figure_para_after(self):
        html = '<p> Text 1 <img src="image0.jpg"/>Text after image </p><p>Text 2 </p>'
        self.assertJson(
            [
                {"tag": "p", "children": [" Text 1 "]},
                {"tag": "figure", "children": [{"tag": "img", "attrs": {"src": "image0.jpg"}}]},
                {"tag": "p", "children": ["Text after image "]}, {"tag": "p", "children": ["Text 2 "]}
             ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_image_inside_paragraph_data_img(self):
        html = '<p> Text <img src="  data:image/png;base64,' \
                    'iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/' \
                    'w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHw' \
                    'AAAABJRU5ErkJggg=="/></p>'
        self.assertJson(
            [{'children': [' Text '], 'tag': 'p'}],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_image_tag_at_the_top(self):
        html = '<img src="image.jpg" title="image"/>'
        self.assertJson(
            [
                {"children": [{"attrs": {"src": "image.jpg"}, "tag": "img"}], "tag": "figure"}
            ],
            convert_html_to_telegraph_format(html, clean_html=True)
        )

    def test_image_html_with_text_after(self):
        self.assertJson(
            [
                {"tag": "figure", "children": [{"tag": "img", "attrs": {"src": "image1.jpg"}}]},
                {"tag": "p", "children": [" Text after"]}
            ],
            convert_html_to_telegraph_format(self.html_with_text_after, clean_html=True)
        )

    def test_image_html_with_text_before(self):
        self.assertJson(
            [
                {"children": ["Text before "], "tag": "p"},
                {"children": [{"attrs": {"src": "image0.jpg"}, "tag": "img"}], "tag": "figure"}
            ],
            convert_html_to_telegraph_format(self.html_with_text_before, clean_html=True)
        )

    def test_image_html_with_text_joined(self):
        html_joined = self.html_with_text_before + self.html_with_text_after
        self.assertJson(
            [
                {"tag": "p", "children": ["Text before "]},
                {"tag": "figure", "children": [{"tag": "img", "attrs": {"src": "image0.jpg"}}]},
                {"tag": "figure", "children": [{"tag": "img", "attrs": {"src": "image1.jpg"}}]},
                {"tag": "p", "children": [" Text after"]}
            ],
            convert_html_to_telegraph_format(html_joined, clean_html=True)
        )


class TelegraphConversionTwitterLinksTest(JSONAssertion):
    def setUp(self):
        self.assert_with = [
            {'tag': 'figure', 'children': [{'tag': 'iframe', 'attrs': {
                'src': '/embed/twitter?url=https%3A%2F%2Ftwitter.com%2Fdurov%2Fstatus%2F803680844200210432'}}]}
        ]

    def test_twitter_links(self):
        html = '''
        <blockquote class="twitter-tweet"><p>
        <a href="https://twitter.com/JoshConstine">@JoshConstine</a>
        <a href="https://twitter.com/TechCrunch">@TechCrunch</a> The distribution of games</p>
        <a href="https://twitter.com/durov/status/803680844200210432"></a>
        <a name="no_href"></a></blockquote>
        '''
        self.assertJson(self.assert_with, convert_html_to_telegraph_format(html, clean_html=True))

    def test_twitter_links_duplicated_link(self):
        duplicated_link_html = '''
        <blockquote class="twitter-tweet"><p>
        <a href="https://twitter.com/JoshConstine">@JoshConstine</a>
        <a href="https://twitter.com/TechCrunch">@TechCrunch</a> The distribution of games</p>
        <a href="https://twitter.com/durov/status/803680844200210432"></a>
        <a href="https://twitter.com/durov/status/803680844200210432"></a>
        <a name="no_href"></a></blockquote>
        '''
        self.assertJson(self.assert_with, convert_html_to_telegraph_format(duplicated_link_html, clean_html=True))
