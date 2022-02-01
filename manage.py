from logging.config import dictConfig

from app.cli import cli
from app.config import LOGGING_CONFIG


dictConfig(LOGGING_CONFIG)


if __name__ == '__main__':
    cli()
