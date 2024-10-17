from setuptools import setup, find_packages

setup(
    name='vlm_parser',
    version='0.1',
    packages=find_packages(),
    install_requires=[],
    entry_points={
        'console_scripts': [
            'vlm_parser=vlm_parser.main:main'
        ],
    },
)
