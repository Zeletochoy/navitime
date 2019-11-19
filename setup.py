from setuptools import find_packages, setup


VERSION = "0.0.1"


setup(
    name='navitime',
    version=VERSION,
    description='Library to interact with Navitime bicycle',
    author='Antoine Lecubin',
    author_email='antoinelecubin@msn.com',
    packages=find_packages(),
    license="beerware",
    install_requires=[
        'requests>=2.21.0',
        'beautifulsoup4>=4.7.1',
        'click>=7.0',
    ],
    entry_points={
        "console_scripts": [
            "navitime-route=navitime.cli:find_bicycle_route",
            "navitime-save=navitime.cli:save_address",
        ],
    },
)
