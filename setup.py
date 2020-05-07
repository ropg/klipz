import setuptools
import re
from distutils.core import setup

# read the contents of your README file
from os import path

this_directory = path.abspath(path.dirname(__file__))

setup(
    name="klipz",
    version="0.0.1",
    description="Encrypted pastebuffer sharing between machines",
    long_description="",
    url="https://github.com/ropg/klipz",
    author="Rop Gonggrijp",
    license="MIT",
    classifiers=["Development Status :: 3 - Alpha", "Programming Language :: Python :: 3",],
    keywords="copy, paste, clipboard",
    project_urls={
        "Documentation": "https://github.com/ropg/klipz/README.md",
        "Source": "https://github.com/ropg/klipz",
        "Tracker": "https://github.com/ropg/klipz/issues",
    },
    packages=["klipz",],
    python_requires=">=3",
    setup_requires=["wheel"],
    install_requires=[
#        "pyqt5==5.14.0",
		"pyperclip",
    ],
    entry_points={
        "console_scripts": [
            # command = package.module:function
            "klipz = klipz.klipz:main",
            "klipzd = klipz.klipzd:main",
        ],
    },
)
