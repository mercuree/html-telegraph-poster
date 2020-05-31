from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name='html_telegraph_poster',
      version='0.1.54',
      description='Posts your html to telegra.ph blogging service',
      long_description=long_description,
      long_description_content_type="text/markdown",
      keywords='telegra.ph post html telegram',
      url='https://github.com/mercuree/html-telegraph-poster',
      author='Garry G',
      author_email='mercuree.lab@gmail.com',
      license='MIT',
      packages=['html_telegraph_poster'],
      install_requires=['lxml', 'requests', 'requests_toolbelt'],
      classifiers=['Operating System :: OS Independent', 'Programming Language :: Python :: 3',
                   'License :: OSI Approved :: MIT License']
)
