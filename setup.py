from setuptools import setup, find_packages

setup(
    name="playground",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'pandas',
        'absl-py',
        'tqdm',
        'jinja2',
        'requests',
        'marko',
        'pyyaml'
    ]
)
