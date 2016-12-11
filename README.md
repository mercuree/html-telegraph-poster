# Python html to telegra.ph poster

Simple python function to post plain html text to telegra.ph.
Telegra.ph allows `<p>, <a>, <img>, <strong>, <figure>, <figcaption>, <blockquote>` and more elements.

About telegram telegra.ph service https://telegram.org/blog/instant-view

## Requirements
* lxml
* requests
* requests_toolbelt

## Usage
Simple way:

```python
>>> from html_telegraph_poster import upload_to_telegraph

>>> upload_to_telegraph(title='Kill all humans?', author='Bill Gates', text='<p>Hello world!</p><p>Good Bye!</p>')
{'url': u'https://telegra.ph/Kill-all-humans-12-05', u'path': u'Kill-all-humans-12-05', 'tph_uuid': 'FzsYQzhx7LKdG1dx********', u'page_id': u'9e7732a45e**********'}

```
Hard way:
```python
>>> from html_telegraph_poster import TelegraphPoster
>>> t = TelegraphPoster()
>>> t.post(title='Just another funny joke', author='by me', text='<blockquote>Really hard way</blockquote>')
{'url': u'https://telegra.ph/Just-another-funny-joke-12-05', u'path': u'Just-another-funny-joke-12-05', 'tph_uuid': '4gFlYHCFiIBAxk***********', u'page_id': u'a38*************'}

# We can modify this article later
>>> t.edit(text=t.text + '<p>some text at the end</p>')
{'url': u'https://telegra.ph/Just-another-funny-joke-12-05', u'path': u'Just-another-funny-joke-12-05', 'tph_uuid': '4gFlYHCF*********', u'page_id': u'a381b2********'}

```
