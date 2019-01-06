from setuptools import setup


setup(
    name="pycart",
    version="0.1",
    url="https://github.com/chaudum/pycart",
    author="Christian Haudum",
    author_email="developer@christianhaudum.at",
    description="Audio Cart Machine",
    long_description="",
    license="Apache License 2.0",
    entry_points={"console_scripts": ["pycart = pycart:main"]},
    python_requires=">=3.6",
    install_requires=[
        "simpleaudio",
    ]
)
