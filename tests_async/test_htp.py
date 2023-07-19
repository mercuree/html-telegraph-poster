# coding=utf8
import unittest
from html_telegraph_poster_async.upload_images import upload_image, _get_mimetype_from_response_headers
from html_telegraph_poster_async.upload_images import GetImageRequestError
from html_telegraph_poster_async import AsyncTelegraphPoster


class UploadImageTest(unittest.IsolatedAsyncioTestCase):

    async def test_upload(self):
        telegraph_url = await upload_image('http://httpbin.org/image/jpeg')
        self.assertIn('http://telegra.ph/file/', telegraph_url)

    async def test_upload_return_json(self):
        telegraph_response = await upload_image('http://httpbin.org/image/jpeg', return_json=True)
        self.assertIsInstance(telegraph_response, list)
        self.assertTrue(len(telegraph_response), 1)
        self.assertNotEqual(telegraph_response[0].get('src'), None)

    async def test_upload_from_file_object(self):
        b64file = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII='
        from io import BytesIO
        from base64 import b64decode
        with BytesIO(b64decode(b64file)) as file_to_upload:
            # emulate filename for mimetype detection
            file_to_upload.name = 'sample.png'
            telegraph_image_url = await upload_image(file_to_upload)
            self.assertIn('http://telegra.ph/file/', telegraph_image_url)

    def test_mime_headers(self):
        self.assertEqual('image/jpeg', _get_mimetype_from_response_headers({'Content-Type': 'image/jpg'}))
        self.assertEqual('image/jpeg', _get_mimetype_from_response_headers({'Content-Type': 'image/jpeg'}))

    async def test_get_delay_timeout(self):
        async def _upload():
            await upload_image('http://httpbin.org/delay/3', return_json=True, get_timeout=(2, 2))

        with self.assertRaises(GetImageRequestError):
            await _upload()


class TelegraphPosterNoApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_post(self):
        t = AsyncTelegraphPoster(use_api=False)
        result = await t.post('test_no_api0201', 'unit_test', '<p>first para</p>')
        self.assertTrue(
            'url' in result and
            'path' in result and
            'tph_uuid' in result and
            'page_id' in result
        )


class TelegraphPosterApiTest(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Access Token from telegra.ph/api page
        self.sandbox_access_token = 'd3b25feccb89e508a9114afb82aa421fe2a9712b963b387cc5ad71e58722'

    async def test_api_token(self):
        t = AsyncTelegraphPoster(use_api=True)
        result = await t.create_api_token('teleposter_test', 'tele_author_test')
        self.assertEqual(
            'teleposter_test',
            result['short_name']
        )
        self.assertEqual(
            'tele_author_test',
            result['author_name']
        )

    async def test_api(self):
        html = '<p>test paragraph</p>'
        t = AsyncTelegraphPoster(use_api=True, access_token=self.sandbox_access_token)
        result = await t.post('test_page0201', 'au', html)
        self.assertTrue('url' in result)
        self.assertTrue('path' in result)
        result2 = await t.edit('test_edit_page04', 'au_edit', '<p>edit test</p>')
        self.assertTrue('url' in result)
        self.assertTrue('path' in result)
        self.assertEqual(
            result['path'],
            result2['path']
        )

    async def test_api_non_default_server(self):
        html = '<p>test paragraph</p>'
        t = AsyncTelegraphPoster(use_api=True, access_token=self.sandbox_access_token,
                                 telegraph_api_url='https://api.graph.org')
        result = await t.post('test_page0201', 'au', html)
        self.assertTrue('url' in result)
        self.assertIn('https://graph.org/', result.get('url'))

    async def test_edit_with_path(self):
        html = '<p>test paragraph</p>'
        t1 = AsyncTelegraphPoster(use_api=True, access_token=self.sandbox_access_token)
        t2 = AsyncTelegraphPoster(use_api=True, access_token=self.sandbox_access_token)
        result = await t1.post('test_page0201', 'au', html)
        result2 = await t2.edit(title='test_page0201_edit', text='<p>test paragraph edited</p>', path=result['path'])

        self.assertTrue('url' in result)
        self.assertTrue('path' in result)
        self.assertEqual(
            result['path'],
            result2['path']
        )

    async def test_get_page(self):
        t = AsyncTelegraphPoster(use_api=True)
        page = await t.get_page('Test-html-telegraph-poster-Page-02-17', return_content=True)
        self.assertEqual(page['title'], 'Test html telegraph poster Page')
        self.assertEqual(page['path'], 'Test-html-telegraph-poster-Page-02-17')
        self.assertTrue('content' in page)
        self.assertTrue('html' in page)

    async def test_get_account_info(self):
        t = AsyncTelegraphPoster(use_api=True, access_token=self.sandbox_access_token)
        acc_info = await t.get_account_info(fields=['short_name', 'author_url', 'page_count'])
        self.assertTrue('page_count' in acc_info)
        self.assertIn('Sandbox', acc_info['short_name'])

    async def test_edit_account_info(self):
        t = AsyncTelegraphPoster(use_api=True)
        await t.create_api_token('SandboxTest', author_url='https://google.com/')
        acc_info = await t.edit_account_info(short_name='Sandbox', author_name='aaa',
                                             author_url='https://telegram.org/')
        self.assertEqual(acc_info['short_name'], 'Sandbox')
        self.assertEqual(acc_info['author_url'], 'https://telegram.org/')

    async def test_revoke_access_token(self):
        t = AsyncTelegraphPoster(use_api=True)
        await t.create_api_token('SandboxTest', author_url='https://google.com/')
        old_access_token = t.access_token
        await t.revoke_access_token()
        test_old_access_token = t.access_token
        self.assertNotEqual(old_access_token, test_old_access_token)

    async def test_get_views(self):
        t = AsyncTelegraphPoster(use_api=True)
        info = await t.get_views('api')
        self.assertTrue('views' in info)

    async def test_get_page_list(self):
        t = AsyncTelegraphPoster(use_api=True, access_token=self.sandbox_access_token)
        info = await t.get_page_list(offset=5, limit=19)
        self.assertTrue('pages' in info)
        self.assertEqual(19, len(info['pages']))


if __name__ == '__main__':
    unittest.main()
