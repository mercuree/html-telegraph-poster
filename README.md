# Python html to telegra.ph poster

Simple python function to post plain html text to telegra.ph.
Telegra.ph allows `<p>, <a>, <img>, <strong>, <figure>, <figcaption>, <blockquote>` and more elements.

About telegram telegra.ph service https://telegram.org/blog/instant-view

## Requirements
* lxml
* requests

## Usage
```python
>>> from html_to_telegraph import convert_html_to_telegraph_format

>>> convert_html_to_telegraph_format('<p>Hello world!</p><p>Good Bye!</p>')
[{'c': [{'t': 'Hello world!'}], '_': 'p'}, {'c': [{'t': 'Good Bye!'}], '_': 'p'}]

```
Just pass html string to convert_html_to_telegraph_format()
