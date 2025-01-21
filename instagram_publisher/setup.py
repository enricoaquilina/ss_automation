from setuptools import setup, find_packages

setup(
    name="instagram_publisher",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'httpx',
        'pymongo',
        'python-dotenv',
        'replicate',
        'requests'
    ],
    python_requires='>=3.8',
) 