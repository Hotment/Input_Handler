from setuptools import setup, find_packages

with open("README.md", "r") as f:
    description = f.read()

setup(
    name="cli_ih",
    version = "0.5.3.4",
    packages=find_packages(),
    install_requires = [
        'logging>=0.4.9.6'
    ],
    long_description=description,
    long_description_content_type="text/markdown"
)