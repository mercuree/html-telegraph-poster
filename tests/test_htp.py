# coding=utf8
import unittest
from html_telegraph_poster.upload_images import upload_image, _get_mimetype_from_response_headers
from html_telegraph_poster.upload_images import GetImageRequestError
from html_telegraph_poster import TelegraphPoster


class UploadImageTest(unittest.TestCase):

    def test_upload(self):
        telegraph_url = upload_image('http://httpbin.org/image/jpeg')
        self.assertIn('http://telegra.ph/file/', telegraph_url)

    def test_upload_return_json(self):
        telegraph_response = upload_image('http://httpbin.org/image/jpeg', return_json=True)
        self.assertIsInstance(telegraph_response, list)
        self.assertTrue(len(telegraph_response), 1)
        self.assertNotEqual(telegraph_response[0].get('src'), None)

    def test_upload_from_file_object(self):
        b64file = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII='
        from io import BytesIO
        from base64 import b64decode
        with BytesIO(b64decode(b64file)) as file_to_upload:
            # emulate filename for mimetype detection
            file_to_upload.name = 'sample.png'
            telegraph_image_url = upload_image(file_to_upload)
            self.assertIn('http://telegra.ph/file/', telegraph_image_url)

    def test_mime_headers(self):
        self.assertEqual('image/jpeg', _get_mimetype_from_response_headers({'Content-Type': 'image/jpg'}))
        self.assertEqual('image/jpeg', _get_mimetype_from_response_headers({'Content-Type': 'image/jpeg'}))

    def test_get_delay_timeout(self):
        def _upload():
            upload_image('http://httpbin.org/delay/3', return_json=True, get_timeout=(2, 2))
        self.assertRaises(GetImageRequestError, _upload)


class TelegraphPosterNoApiTest(unittest.TestCase):
    def test_post(self):
        t = TelegraphPoster()
        result = t.post('test_no_api0201', 'unit_test', '<p>first para</p>')
        self.assertTrue(
            'url' in result and
            'path' in result and
            'tph_uuid' in result and
            'page_id' in result
        )


class TelegraphPosterApiTest(unittest.TestCase):

    def setUp(self):
        # Access Token from telegra.ph/api page
        self.sandbox_access_token = 'b968da509bb76866c35425099bc0989a5ec3b32997d55286c657e6994bbb'

    def test_api_token(self):
        t = TelegraphPoster(use_api=True)
        result = t.create_api_token('teleposter_test', 'tele_author_test')
        self.assertEqual(
            'teleposter_test',
            result['short_name']
        )
        self.assertEqual(
            'tele_author_test',
            result['author_name']
        )

    def test_api(self):
        html = '<p>test paragraph</p>'
        t = TelegraphPoster(use_api=True, access_token=self.sandbox_access_token)
        result = t.post('test_page0201', 'au', html)
        self.assertTrue('url' in result)
        self.assertTrue('path' in result)
        result2 = t.edit('test_edit_page04', 'au_edit', '<p>edit test</p>')
        self.assertTrue('url' in result)
        self.assertTrue('path' in result)
        self.assertEqual(
            result['path'],
            result2['path']
        )

    def test_edit_with_path(self):
        html = '<p>test paragraph</p>'
        t1 = TelegraphPoster(use_api=True, access_token=self.sandbox_access_token)
        t2 = TelegraphPoster(use_api=True, access_token=self.sandbox_access_token)
        result = t1.post('test_page0201', 'au', html)
        result2 = t2.edit(title='test_page0201_edit', text='<p>test paragraph edited</p>', path=result['path'])

        self.assertTrue('url' in result)
        self.assertTrue('path' in result)
        self.assertEqual(
            result['path'],
            result2['path']
        )

    def test_get_page(self):
        t = TelegraphPoster(use_api=True)
        page = t.get_page('Test-html-telegraph-poster-Page-02-17', return_content=True)
        self.assertEqual(page['title'], 'Test html telegraph poster Page')
        self.assertEqual(page['path'], 'Test-html-telegraph-poster-Page-02-17')
        self.assertTrue('content' in page)
        self.assertTrue('html' in page)

    def test_get_account_info(self):
        t = TelegraphPoster(use_api=True, access_token=self.sandbox_access_token)
        acc_info = t.get_account_info(fields=['short_name', 'author_url', 'page_count'])
        self.assertTrue('page_count' in acc_info)
        self.assertEqual(acc_info['short_name'], 'Sandbox')

    def test_edit_account_info(self):
        t = TelegraphPoster(use_api=True)
        t.create_api_token('SandboxTest', author_url='https://google.com/')
        acc_info = t.edit_account_info(short_name='Sandbox', author_name='aaa', author_url='https://telegram.org/')
        self.assertEqual(acc_info['short_name'], 'Sandbox')
        self.assertEqual(acc_info['author_url'], 'https://telegram.org/')

    def test_revoke_access_token(self):
        t = TelegraphPoster(use_api=True)
        t.create_api_token('SandboxTest', author_url='https://google.com/')
        old_access_token = t.access_token
        t.revoke_access_token()
        self.assertNotEqual(old_access_token, t.access_token)

    def test_get_views(self):
        t = TelegraphPoster(use_api=True)
        info = t.get_views('api')
        self.assertTrue('views' in info)

    def test_get_page_list(self):
        t = TelegraphPoster(use_api=True, access_token=self.sandbox_access_token)
        info = t.get_page_list(offset=5, limit=19)
        self.assertTrue('pages' in info)
        self.assertEqual(19, len(info['pages']))


if __name__ == '__main__':
    unittest.main()
