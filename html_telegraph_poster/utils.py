# coding=utf8

from urllib.parse import urlparse
from .upload_images import upload_image
from .converter import _fragments_from_string
import lxml.html


class DocumentPreprocessor:
    def __init__(self, input_html):
        self.input_html = input_html
        self.parsed_document = self._parse_document()

    def _parse_document(self):
        fragments = _fragments_from_string(self.input_html)
        document = fragments[0].xpath('/*')[0] if len(fragments) else None
        return document

    def get_processed_html(self):
        return lxml.html.tostring(self.parsed_document, encoding='unicode')

    def upload_all_images(self, base_url=None):
        self._make_links_absoulte(base_url)
        images = self.parsed_document.xpath('.//img[@src]')
        for image in images:
            old_image_url = image.attrib.get('src')
            new_image_url = upload_image(old_image_url)
            image.attrib.update({'src': new_image_url})

    def _make_links_absoulte(self, base_url=None):

        body = self.parsed_document.body
        output_base = None
        document_base_url = self.parsed_document.base

        if base_url:
            urlformat = urlparse(base_url)
            url_without_path = urlformat.scheme + "://" + urlformat.netloc
            output_base = url_without_path + urlformat.path
        elif document_base_url:
            if urlparse(document_base_url).netloc:
                output_base = document_base_url
            else:
                # base url contains relative path only
                # we should print the warning
                pass
        else:
            # no base_url was passed, document_base_url is missing
            # put another warning?
            # setting invalid base_url will force to discard url, empty image then will be remove by the cleaner
            output_base = '//['

        body.make_links_absolute(output_base, handle_failures='discard')
