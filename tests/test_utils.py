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

    def test_upload_all_images(self):
        html_images = self.document.format(headcontent='', bodycontent='''
            <figure>
                <img src="http://httpbin.org/image/jpeg" />
                <figcaption> image caption</figcaption>
            </figure>
            <figure>
                <img src="http://httpbin.org/image/png" />
                <figcaption>image caption</figcaption>
            </figure>
        ''')

        dp = DocumentPreprocessor(html_images)
        dp.upload_all_images()

        self.assertEqual(
            2, len(dp.parsed_document.body.xpath('.//img[starts-with(@src, "http://telegra.ph/file/")]'))
        )
        self.assertTrue(
            '<img src="http://telegra.ph/file/' in dp.get_processed_html()
        )

    def test_make_links_absolute_document_base_url(self):
        html_images = self.document.format(
            headcontent='<base href="http://httpbin.org/">',
            bodycontent='''
            <figure>
                <img src="image/jpeg" />
                <figcaption> image caption</figcaption>
            </figure>
            <figure>
                <img src="image/png" />
                <figcaption>image caption</figcaption>
            </figure>
        ''')

        dp = DocumentPreprocessor(html_images)
        dp._make_links_absoulte()
        self.assertTrue(
            '<img src="http://httpbin.org/image/png">' in dp.get_processed_html()
        )
        self.assertTrue(
            '<img src="http://httpbin.org/image/jpeg">' in dp.get_processed_html()
        )

    def test_make_links_absolute_document_without_base_url(self):
        html_images = self.document.format(
            headcontent='',
            bodycontent='''
            <figure>
                <img src="image/jpeg" />
                <figcaption> image caption</figcaption>
            </figure>
            <figure>
                <img src="image/png" />
                <figcaption>image caption</figcaption>
            </figure>
        ''')

        dp = DocumentPreprocessor(html_images)
        dp._make_links_absoulte()
        print(dp.get_processed_html())
        self.assertFalse(
            '<img src' in dp.get_processed_html()
        )
        self.assertFalse(
            '<img src' in dp.get_processed_html()
        )
