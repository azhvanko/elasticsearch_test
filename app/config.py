import typing as t
from pathlib import Path

from environs import Env


BASE_DIR = Path(__file__).resolve().parent.parent

env = Env()
env.read_env(path=str(BASE_DIR / '.env'), recurse=False)

# logging
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': (
                '[%(asctime)s] [%(levelname)-8s] %(message)s'
            ),
            'datefmt': '%d/%m/%Y %H:%M:%S',
        },
        'verbose': {
            'format': (
                '[%(asctime)s] [%(levelname)-8s] '
                '[%(module)-10s %(lineno)-4d %(funcName)-16s] %(message)s'
            ),
            'datefmt': '%d/%m/%Y %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'stream': 'ext://sys.stdout',
        },
        'elasticsearch': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': BASE_DIR / 'logs' / 'elasticsearch.log',
            'encoding': 'utf-8',
            'maxBytes': 1024 * 1024 * 1024,  # (1GB)
            'backupCount': 30,
            'delay': True,
        },
        'catalog': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': BASE_DIR / 'logs' / 'catalog.log',
            'encoding': 'utf-8',
            'maxBytes': 1024 * 1024 * 1024,  # (1GB)
            'backupCount': 30,
            'delay': True,
        },
    },
    'loggers': {
        'elasticsearch': {
            'handlers': ['elasticsearch',],
            'propagate': False,
            'level': 'INFO',
        },
        'catalog': {
            'handlers': ['console', 'catalog',],
            'propagate': False,
            'level': 'DEBUG',
        },
    },
}


# ES cluster
ES_MASTER_NODE_HOST: str = env.str('ES_MASTER_NODE_HOST', default='localhost')
ES_MASTER_NODE_PORT: int = env.int('ES_MASTER_NODE_PORT', default=9200)
ES_USER: str = env.str('ES_USER')
ES_USER_PASSWORD: str = env.str('ES_USER_PASSWORD')
# ES index
ES_CATALOG_INDEX_NAME: str = env.str('ES_CATALOG_INDEX_NAME', default='catalog')
ES_CATALOG_DOCUMENTS_COUNT: int = env.int(
    'ES_CATALOG_DOCUMENTS_COUNT',
    default=3_000_000
)
ES_CATALOG_INDEX_CONFIG: dict[str, dict[str, t.Any]] = {
    'settings': {
        'number_of_shards': 5,  # FIXME need to benchmark this in your specific use case
        'number_of_replicas': 1,
        'index': {
            'refresh_interval': '60s',
            'sort.field': ['time_created', 'priority',],
            'sort.order': ['desc', 'asc',],
        }
    },
    'mappings': {
        'dynamic': 'strict',
        'properties': {
            'clothing_item_id': {
                'type': 'integer',
                'doc_values': False,
            },
            'time_created': {
                'type': 'date',
                'index': False,
                'format': 'strict_date_optional_time',
            },
            'gender': {
                'type': 'keyword',
                'norms': False,
                'doc_values': False,
            },
            'partner_id': {
                'type': 'short',
                'doc_values': False,
            },
            'clothing_category_id': {
                'type': 'short',
                'doc_values': False,
            },
            'price_tier': {
                'type': 'byte',
            },
            'current_price': {
                'type': 'float',
            },
            'text': {
                'type': 'text',
                'index_options': 'docs',
                'fields': {
                    'english': {
                        'type': 'text',
                        'index_options': 'docs',
                        'analyzer': 'english',
                    },
                    'russian': {
                        'type': 'text',
                        'index_options': 'docs',
                        'analyzer': 'russian',
                    }
                }
            },
            'sport': {
                'type': 'boolean',
            },
            'plus_size': {
                'type': 'boolean',
            },
            'new': {
                'type': 'boolean',
            },
            'priority': {
                'type': 'byte',
            },
            'archetypes': {
                'type': 'byte',
            },
            'color_types': {
                'type': 'byte',
            },
            'figure_type_id': {
                'type': 'byte',
            },
            'figure_type_problem_id': {
                'type': 'byte',
            },
        }
    },
}
