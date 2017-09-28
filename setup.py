from setuptools import setup

setup(name='html_telegraph_poster',
      version='0.1.26',
      description='Posts your html to telegra.ph blogging service',
      keywords='telegra.ph post html telegram',
      url='https://github.com/mercuree/html-telegraph-poster',
      author='Garry G',
      author_email='mercuree.lab@gmail.com',
      license='MIT',
      packages=['html_telegraph_poster'],
      install_requires=['lxml', 'requests', 'requests_toolbelt'],
      zip_safe=False)
