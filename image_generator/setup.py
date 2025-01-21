from setuptools import setup, find_packages

setup(
    name="image_generator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.1",
        "pymongo>=3.12.0",
        "python-dotenv>=0.19.0",
        "Pillow>=8.3.1",
        "tqdm>=4.62.2",
        "replicate>=0.8.0",
        "tenacity>=8.0.1"
    ],
    author="Silicon Sentiments",
    description="A package for generating images using various AI providers (Midjourney, Flux, Leonardo)",
    python_requires=">=3.8",
) 