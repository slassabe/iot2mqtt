import pathlib
from setuptools import setup

def _get_readme_content() -> str:
    """
    Returns the content of the README.md file.
    """
    _here = pathlib.Path(__file__).parent
    _readme_content = (_here / "README.md").read_text()
    return _readme_content

def _get_version() -> str:
    """
    Returns the version of the package.
    """
    _here = pathlib.Path(__file__).parent
    _file_content = (_here / "iot2mqtt" / "version.py").read_text()
    _line = _file_content.split("=")[1].strip()
    _version = _line.strip('"')
    print(_version)
    return _version

setup(
    name='iot2mqtt',
    version=_get_version(),
    description='Less is More - Powering Your IoT Solutions with MQTT integration',
    long_description=_get_readme_content(),
    long_description_content_type="text/markdown",
    license="MIT",
    author='Serge LASSABE',
    author_email='dev@lassabe.org',
    url="https://github.com/slassabe/iot2mqtt",
    packages=['iot2mqtt'],
    scripts=['bin/cli_iot2mqtt'],
    install_requires=['paho-mqtt', 'certifi', 'requests', 'pydantic'],
)
