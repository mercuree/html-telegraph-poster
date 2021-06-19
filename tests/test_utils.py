# coding=utf8

import unittest
from html_telegraph_poster.utils import DocumentPreprocessor


class DocumentPreprocessorImageUploadTest(unittest.TestCase):
    def setUp(self):
        self.document = '''
        <!doctype html>
        <html>
            <head>
                <title>Test title</title>
                <!-- base element if present -->
                {headcontent}
            </head>
            <body>
                <!--image elements-->
                {bodycontent} 
            </body>
        </html>'''
        self.html_figures = '''
            <figure>
                <img src="{0}" />
                <figcaption> image caption</figcaption>
            </figure>
            <figure>
                <img src="{1}" />
                <figcaption>image caption</figcaption>
            </figure>
        '''

    def test_upload_all_images(self):
        html_images = self.document.format(
            headcontent='',
            bodycontent='<img src="http://telegra.ph/file/test.jpeg" /> ' +
                        self.html_figures.format('http://httpbin.org/image/jpeg', 'http://httpbin.org/image/png')
        )

        dp = DocumentPreprocessor(html_images)
        dp.upload_all_images()

        self.assertEqual(
            3, len(dp.parsed_document.body.xpath('.//img[starts-with(@src, "http://telegra.ph/file/")]'))
        )
        self.assertTrue(
            '<img src="http://telegra.ph/file/' in dp.get_processed_html()
        )

    def test_make_links_absolute_document_base_url(self):
        html_images = self.document.format(
            headcontent='<base href="http://httpbin.org/">',
            bodycontent=self.html_figures.format('image/jpeg', 'image/png')
        )

        dp = DocumentPreprocessor(html_images)
        dp._make_links_absolute()
        processed_html = dp.get_processed_html()
        self.assertTrue(
            '<img src="http://httpbin.org/image/png">' in processed_html
        )
        self.assertTrue(
            '<img src="http://httpbin.org/image/jpeg">' in processed_html
        )

    def test_make_links_absolute_document_without_base_url(self):
        html_images = self.document.format(
            headcontent='',
            bodycontent=self.html_figures.format('image/jpeg', 'image/png')
        )
        dp = DocumentPreprocessor(html_images)
        dp._make_links_absolute()
        processed_html = dp.get_processed_html()
        self.assertFalse(
            '<img src' in processed_html
        )
        self.assertFalse(
            '<img src' in processed_html
        )

    def test_make_links_absolute_pass_base_url(self):
        html_images = self.document.format(
            headcontent='',
            bodycontent='<a href="test_link.html">test Link</a>' + self.html_figures.format('image/jpeg', 'image/png')
        )
        dp = DocumentPreprocessor(html_images)
        dp._make_links_absolute(base_url='http://httpbin.org')
        processed_html = dp.get_processed_html()
        self.assertTrue(
            '<img src="http://httpbin.org/image/png">' in processed_html
        )
        self.assertTrue(
            '<img src="http://httpbin.org/image/jpeg">' in processed_html
        )
        self.assertTrue(
            '<a href="http://httpbin.org/test_link.html">' in processed_html
        )

    def test_pass_invalid_document_type(self):
        self.assertRaises(TypeError, DocumentPreprocessor, b'byte string')
