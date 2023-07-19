import sys, os
from .html_to_telegraph import AsyncTelegraphPoster


if len(sys.argv) > 1:
    t = AsyncTelegraphPoster()
    params = sys.argv[1:]
    await t.create_api_token(*params)

    with open('.env', 'a',) as f:
        f.write('\n\nTELEGRAPH_ACCESS_TOKEN=%s' % t.access_token)

    print("Access Token: {access_token}\n"
          "Account Name: {short_name}\n"
          "Author name: {author_name}\n"
          "Author url: {author_url}\n"
          "Authorization url: {auth_url}\n"
          "File .env generated".format(**t.account)
    )
else:
    print('Usage: '
          'Account Name (required)'
          'Author name (optional)'
          'Author url (optional)'
    )
