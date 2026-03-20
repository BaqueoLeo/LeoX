"""Setup for the leox CLI command."""

from setuptools import setup, find_packages

setup(
    name="leox",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.1",
        "rich>=13.0",
        "httpx>=0.28",
    ],
    entry_points={
        "console_scripts": [
            "leox=cli.commands:cli",
        ],
    },
)
