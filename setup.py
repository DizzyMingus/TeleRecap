
from setuptools import setup

setup(
    name="telegram-bot",
    version="0.1.0",
    py_modules=["main", "generate_session"],
    install_requires=[
        "python-dotenv>=1.0.1",
        "python-telegram-bot[job-queue]>=20.0",
        "telethon>=1.25.0",
    ],
)
