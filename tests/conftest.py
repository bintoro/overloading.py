import sys


def pytest_addoption(parser):
    parser.addoption('--typing', action='store', default='typing')


def pytest_configure(config):
    if config.option.typing == 'no':
        sys.modules['typing'] = None
    elif config.option.typing != 'typing':
        sys.modules['typing'] = __import__(config.option.typing)

