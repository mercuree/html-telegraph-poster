# Python html to telegra.ph converter

Simple python function to convert plain html text to telegra.ph format, which you can then post to telegraph.
Telegra.ph allows `<p>, <img>, <strong>, <figure>, <figcaption>, <blockquote>` and more elements.

About telegram telegra.ph service https://telegram.org/blog/instant-view

## Requirements
* lxml

## Usage
```python
>>> from html_to_telegraph import convert_html_to_telegraph_format

>>> convert_html_to_telegraph_format('<p>Hello world!</p><p>Good Bye!</p>')
[{'c': [{'t': 'Hello world!'}], '_': 'p'}, {'c': [{'t': 'Good Bye!'}], '_': 'p'}]

```
Just pass html string to convert_html_to_telegraph_format()


### Note
Please, note that text nodes outside html tags will be ignored.
```html
this text will be ignored
<p>
   hello 
   <a href="https://telegram.org/">Telegram</a>!
</p>
and this text will be ignored too
```
