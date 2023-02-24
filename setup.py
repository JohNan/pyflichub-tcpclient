import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyflichub-tcpclient",
    version="0.1.0",
    author="JohNan",
    author_email="johan.nanzen@gmail.com",
    description="Asynchronous Python TCP Client for FlicHub",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JohNan/pyflichub-tcpclient",
    packages=setuptools.find_packages(),
    classifiers=[
        "Framework :: AsyncIO",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires='>=3',
)
