import setuptools
from distutils.core import setup

setup(
    name="klipz",
    version="0.1.3",
    description="Clipboard history, manipulation of individual clippings.",
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
		"pyperclip",
    ],
    entry_points={
        "console_scripts": [
            # command = package.module:function
            "klipz = klipz.klipz:main",
        ],
    },
)
