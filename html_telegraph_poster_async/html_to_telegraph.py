# encoding=utf8
import json
import os
import requests
import httpx
from requests_toolbelt import MultipartEncoder
from .errors import *
from .converter import convert_html_to_telegraph_format, convert_json_to_html, OutputFormat

base_url = 'http://telegra.ph'
save_url = 'https://edit.telegra.ph/save'
api_url = 'https://api.telegra.ph'
default_user_agent = 'Python_telegraph_poster/0.1'


async def _upload(title, author, text,
                  author_url='', tph_uuid=None, page_id=None, user_agent=default_user_agent, convert_html=True,
                  clean_html=True, telegraph_base_url=base_url):
    if not title:
        raise TitleRequiredError('Title is required')
    if not text:
        raise TextRequiredError('Text is required')

    content = convert_html_to_telegraph_format(text, clean_html) if convert_html else text
    cookies = dict(tph_uuid=tph_uuid) if tph_uuid and page_id else None

    fields = {
        'Data': ('content.html', content, 'plain/text'),
        'title': title,
        'author': author,
        'author_url': author_url,
        'page_id': page_id or '0',
        'save_hash': ''
    }

    m = MultipartEncoder(fields, boundary='TelegraPhBoundary21')

    headers = {
        'Content-Type': m.content_type,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'User-Agent': user_agent,
        'Origin': telegraph_base_url
    }
    timeout = httpx.Timeout(4.0)
    retries = httpx.Limits(max_keepalive_connections=3, max_connections=10)
    async with httpx.AsyncClient(timeout=timeout, limits=retries) as client:
        response = await client.post(save_url, headers=headers, cookies=cookies, content=m.to_string())
        result = json.loads(response.text)
        if 'path' in result:
            result['tph_uuid'] = response.cookies.get('tph_uuid') or tph_uuid
            result['url'] = telegraph_base_url + '/' + result['path']
            return result
        else:
            error_msg = result['error'] if 'error' in result else ''
            raise TelegraphError(error_msg)


def _prepare_page_upload_params(params):
    # significantly reduce size of request body
    return json.dumps(params, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


async def _upload_via_api(title, author, text, author_url='', access_token=None, user_agent=default_user_agent,
                          convert_html=True, clean_html=True, path=None, telegraph_api_url=api_url):
    if not title:
        raise TitleRequiredError('Title is required')
    if not text:
        raise TextRequiredError('Text is required')
    if not access_token:
        raise APITokenRequiredError('API token is required')
    if not author:
        author = ''  # author is optional
    if not author_url:
        author_url = ''  # author_url is optional

    content = convert_html_to_telegraph_format(text, clean_html,
                                               output_format=OutputFormat.PYTHON_LIST) if convert_html else text
    method = '/createPage' if not path else '/editPage'

    params = {
        'access_token': access_token,
        'title': title[:256],
        'author_name': author[:128],
        'author_url': author_url[:512],
        'content': content,
    }
    request_headers = {
        'User-Agent': user_agent,
        'Content-Type': 'application/json'
    }
    if path:
        params.update({'path': path})
    async with httpx.AsyncClient() as client:
        resp = await client.post(telegraph_api_url + method, content=_prepare_page_upload_params(params),
                                 headers=request_headers)
    # resp = requests.post(telegraph_api_url + method, data=_prepare_page_upload_params(params), headers=request_headers).json()
    resp = resp.json()
    if resp['ok'] is True:
        return resp.get('result')
    else:
        error_msg = resp['error'] if 'error' in resp else ''
        raise TelegraphError(error_msg)


async def create_api_token(short_name, author_name=None, author_url=None, user_agent=default_user_agent):
    params = {
        'short_name': short_name,
    }
    if author_name:
        params.update({'author_name': author_name})
    if author_url:
        params.update({'author_url': author_url})
    async with httpx.AsyncClient() as client:
        resp = await client.get(api_url + '/createAccount', params=params, headers={'User-Agent': user_agent})
    # resp = requests.get(api_url+'/createAccount', params, headers={'User-Agent': user_agent})
    json_data = resp.json()
    return json_data['result']


async def upload_to_telegraph(title, author, text, author_url='', tph_uuid=None, page_id=None,
                              user_agent=default_user_agent):
    result = await _upload(title, author, text, author_url, tph_uuid, page_id, user_agent)
    return result


class AsyncTelegraphPoster(object):
    def __init__(self, tph_uuid=None, page_id=None, user_agent=default_user_agent, clean_html=True, convert_html=True,
                 use_api=False, access_token=None, telegraph_api_url=api_url, telegraph_base_url=base_url):
        self.title = None
        self.author = None
        self.author_url = None
        self.text = None
        self.path = None
        self.tph_uuid = tph_uuid
        self.page_id = page_id
        self.user_agent = user_agent
        self.clean_html = clean_html
        self.convert_html = convert_html
        self.access_token = access_token or os.getenv('TELEGRAPH_ACCESS_TOKEN', None)
        self.account = None
        self.use_api = use_api
        self.telegraph_api_url = telegraph_api_url
        self.telegraph_base_url = telegraph_base_url
        if self.access_token:
            # use api anyway
            self.use_api = True

    async def _api_request(self, method, params=None):
        params = params or {}
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        if self.access_token:
            params['access_token'] = self.access_token
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.telegraph_api_url + '/' + method,
                                    params=params,
                                    headers={'User-Agent': self.user_agent})
        return resp.json()

    async def post(self, title, author, text, author_url=''):
        self.path = None
        self.title = title
        self.author = author
        self.author_url = author_url
        self.text = text
        result = await self.edit()
        if not self.use_api:
            self.tph_uuid = result['tph_uuid']
            self.page_id = result['page_id']
        return result

    async def edit(self, title=None, author=None, text=None, author_url='', path=None):
        params = {
            'title': title or self.title,
            'author': author or self.author,
            'text': text or self.text,
            'author_url': author_url or self.author_url,
            'user_agent': self.user_agent,
            'clean_html': self.clean_html,
            'convert_html': self.convert_html
        }
        if self.use_api:
            params['telegraph_api_url'] = self.telegraph_api_url
            result = await _upload_via_api(access_token=self.access_token, path=path or self.path, **params)
            self.path = result['path']
            return result
        else:
            result = await _upload(
                tph_uuid=self.tph_uuid,
                page_id=self.page_id,
                **params
            )
            return result

    async def get_account_info(self, fields=None):
        """
        Use this method to get information about a Telegraph account.
        :param fields: (Array of String, default = ['short_name','author_name','author_url'])
        List of account fields to return. Available fields: short_name, author_name, author_url, auth_url, page_count.
        :return: Returns an Account object on success.
        """
        if not self.access_token:
            raise Exception('Access token is required')
        result = await self._api_request('getAccountInfo', {
            'fields': json.dumps(fields) if fields else ''
        })
        return result.get('result')

    async def edit_account_info(self, short_name, author_name='', author_url=''):
        """
            Use this method to update information about a Telegraph account.
            Pass only the parameters that you want to edit
        :param short_name: (String, 1-32 characters) New account name.
        :param author_name: (String, 0-128 characters) New default author name used when creating new articles.
        :param author_url: (String, 0-512 characters) New default profile link, opened when users click on the
            author's name below the title.
            Can be any link, not necessarily to a Telegram profile or channel.
        :return:  Account object with the default fields.
        """
        if not self.access_token:
            raise Exception('Access token is required')
        params = {
            'short_name': short_name
        }
        if author_name:
            params['author_name'] = author_name
        if author_url:
            params['author_url'] = author_url
        result = await self._api_request('editAccountInfo', params)
        return result.get('result')

    async def get_page(self, path, return_content=False):
        """
        Use this method to get a Telegraph page. Returns a Page object on success.
        :param path:  (String) Required. Path to the Telegraph page (in the format Title-12-31, i.e.
            everything that comes after http://telegra.ph/).
        :param return_content: (Boolean, default = false) If true, content field will be returned in Page object.
        :return: Returns a Page object on success
        """
        json_response = await self._api_request('getPage', {
            'path': path,
            'return_content': return_content
        })
        if return_content:
            json_response['result']['html'] = convert_json_to_html(json_response['result']['content'],
                                                                   self.telegraph_base_url)
        return json_response.get('result')

    async def get_page_list(self, offset=0, limit=50):
        """
            Use this method to get a list of pages belonging to a Telegraph account.
        :param offset: Sequential number of the first page to be returned.
        :param limit: Limits the number of pages to be retrieved.
        :return: PageList object, sorted by most recently created pages first.
        """
        json_response = await self._api_request('getPageList', {
            'offset': offset,
            'limit': limit
        })
        return json_response.get('result')

    async def get_views(self, path, year=None, month=None, day=None, hour=None):
        """
            Use this method to get the number of views for a Telegraph article.
        :param path: Required. Path to the Telegraph page (in the format Title-12-31, where 12 is the month and 31 the
            day the article was first published).
        :param year: Required if month is passed. If passed, the number of page views for the requested year will be
            returned.
        :param month: Required if day is passed. If passed, the number of page views for the requested month will be
            returned.
        :param day: Required if hour is passed. If passed, the number of page views for the requested day will be
            returned.
        :param hour: If passed, the number of page views for the requested hour will be returned.
        :return: Returns a PageViews object on success. By default, the total number of page views will be returned.
        """
        result = await self._api_request('getViews', {
            'path': path,
            'year': year,
            'month': month,
            'day': day,
            'hour': hour
        })
        return result.get('result')

    async def create_api_token(self, short_name, author_name=None, author_url=None):
        """
            Use this method to create a new Telegraph account.
            Most users only need one account, but this can be useful for channel administrators who would like to keep
            individual author names and profile links for each of their channels.
        :param short_name: Account name, helps users with several accounts remember which they are currently using.
            Displayed to the user above the "Edit/Publish" button on Telegra.ph, other users don't see this name.
        :param author_name: Default author name used when creating new articles.
        :param author_url: Default profile link, opened when users click on the author's name below the title.
            Can be any link, not necessarily to a Telegram profile or channel.
        :return: Account object with the regular fields and an additional access_token field.
        """
        token_data = await create_api_token(short_name, author_name, author_url, self.user_agent)
        self.use_api = True
        self.account = token_data
        self.access_token = token_data['access_token']
        return token_data

    async def revoke_access_token(self):
        """
            Use this method to revoke access_token and generate a new one, for example, if the user would like to reset
            all connected sessions, or you have reasons to believe the token was compromised
        :return: Account object with new access_token and auth_url fields.
        """
        if not self.access_token:
            raise Exception('Access token is required')

        json_response = await self._api_request('revokeAccessToken')
        if json_response['ok'] is True:
            self.access_token = json_response['result']['access_token']

        return json_response['result']

    async def create_page(self, *args, **kwargs):
        """
            Shortcut method for post()
        """
        result = await self.post(*args, **kwargs)
        return result

    async def edit_page(self, *args, **kwargs):
        """
            Shortcut method for edit()
        """
        result = await self.edit(*args, **kwargs)
        return result

    async def create_account(self, *args, **kwargs):
        """
            Shortcut method for create_api_token()
        """
        result = await self.create_api_token(*args, **kwargs)
        return result
