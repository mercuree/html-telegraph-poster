# coding=utf8

from urllib.parse import urlparse, urljoin
import logging
from .upload_images import upload_image
from .converter import _fragments_from_string
import lxml.html

LOG = logging.getLogger(__name__)


class DocumentPreprocessor:
    def __init__(self, input_html):
        self.input_html = input_html
        self.parsed_document = self._parse_document()

    def get_processed_html(self):
        return lxml.html.tostring(self.parsed_document, encoding='unicode')

    def upload_all_images(self, base_url=None):
        self._make_links_absolute(base_url)
        images = self.parsed_document.xpath('.//img[@src][not(contains(@src, "//telegra.ph/file/")) and'
                                            ' not(contains(@src, "//graph.org/file/"))]')
        for image in images:
            old_image_url = image.attrib.get('src')
            new_image_url = upload_image(old_image_url)
            image.attrib.update({'src': new_image_url})

    def _parse_document(self):
        fragments = _fragments_from_string(self.input_html)
        document = fragments[0].xpath('/*')[0] if len(fragments) else None
        return document

    def _make_links_absolute(self, base_url=None):

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

        if output_base is None:
            # no base_url was passed, document_base_url is missing
            LOG.warning('Relative image/link urls were removed from the document')

        def link_replace(href):
            try:
                if output_base is None and not urlparse(href).netloc:
                    url = None
                else:
                    url = urljoin(output_base, href)
                return url
            except ValueError:
                return None

        body.rewrite_links(link_repl_func=link_replace, base_href=output_base)
