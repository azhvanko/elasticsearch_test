import typing as t
from datetime import datetime
from functools import partial
from random import choice, randint, shuffle

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk as _bulk
from faker import Faker

from app.logging import logger


fake = Faker(['ru_RU', 'en_US',])  # noqa

CHUNK_SIZE: int = 1000
GENDERS: tuple[str, ...] = ('FEMALE', 'MALE',)

bulk: t.Callable = partial(_bulk, chunk_size=CHUNK_SIZE)


def create_index(
    client: Elasticsearch,
    index: str,
    index_config: dict[str, dict[str, t.Union[str, int, dict]]]
) -> None:
    settings = index_config['settings']
    mappings = index_config['mappings']

    result = client.indices.create(
        index=index,
        mappings=mappings,
        settings=settings
    )

    logger.info(result)


def generate_random_document(
    clothing_item_id: t.Union[int, str]
) -> dict[str, t.Any]:
    price_tier = _get_random_price_tier()

    return {
        'clothing_item_id': str(clothing_item_id),
        'time_created': datetime.utcnow(),
        'gender': _get_random_gender(),
        'partner_id': _get_random_partner_id(),
        'clothing_category_id': _get_random_clothing_category_id(),
        'price_tier': price_tier,
        'current_price': _get_random_price_by_price_tier(price_tier),
        'text': _get_random_text(),
        'sport': _get_random_sport_flag(),
        'plus_size': _get_random_plus_size_flag(),
        'new': _get_random_new_flag(),
        'priority': _get_random_priority(),
        'archetypes': _get_random_archetypes(),
        'color_types': _get_random_color_types(),
        'figure_type_id': _get_random_figure_type_id(),
        'figure_type_problem_id': _get_random_figure_type_problem_id(),
    }


def generate_random_search_query(
    filters_count: int = 5
) -> tuple[dict, t.Optional[dict]]:
    fields = [
        'partner_id',
        'clothing_category_id',
        'current_price',
        'sport',
        'plus_size',
        'new',
        'priority',
        'archetypes',
        'color_types',
        'figure_type_id',
        'figure_type_problem_id',
    ]

    query: dict[str, dict[str, t.Any]] = {
        'bool': {
            'filter': [],
        }
    }

    if not randint(0, 2):
        field = choice(
            (
                'figure_type_id',
                'figure_type_problem_id',
                'price_tier',
            )
        )
        sort = [
            {
                field: {
                    'order': ('asc', 'desc')[randint(0, 1)],
                }
            }
        ]
    else:
        sort = None

    # required fields
    price_tier = _get_random_price_tier()

    query['bool']['filter'].append({
        'term': {
            'gender': _get_random_gender(),
        }
    })
    query['bool']['filter'].append({
        'terms': {
            'price_tier': [i for i in range(price_tier + 1)],
        }
    })

    if not randint(0, 11):
        while 1:
            text = [i for i in _get_random_text().split() if len(i) > 5]
            if text:
                break

        query['bool']['filter'] = {
            'multi_match': {
                'query': choice(text),
                'fields': [
                    'text',
                    'text.english',
                    'text.russian',
                ],
                'type': 'most_fields',
            },
        }

        return query, sort

    # optional fields
    shuffle(fields)

    for index in range(filters_count - 2):  # gender + price tier
        field = fields[index]

        if field == 'partner_id':
            query['bool']['filter'].append({
                'term': {
                    field: _get_random_partner_id(),
                }
            })
        elif field == 'clothing_category_id':
            query['bool']['filter'].append({
                'term': {
                    field: _get_random_clothing_category_id(),
                }
            })
        elif field == 'current_price':
            min_val, max_val = _get_random_price_range_by_price_tier(price_tier)
            query['bool']['filter'].append({
                'range': {
                    field: {
                        'gte': min_val,
                        'lte': max_val,
                    },
                }
            })
        elif field == 'sport':
            query['bool']['filter'].append({
                'term': {
                    field: _get_random_sport_flag(),
                }
            })
        elif field == 'plus_size':
            query['bool']['filter'].append({
                'term': {
                    field: _get_random_plus_size_flag(),
                }
            })
        elif field == 'new':
            query['bool']['filter'].append({
                'term': {
                    field: _get_random_new_flag(),
                }
            })
        elif field == 'priority':
            query['bool']['filter'].append({
                'term': {
                    field: _get_random_priority(),
                }
            })
        elif field == 'archetypes':
            start = randint(0, 12)
            _range = randint(2, 4)
            query['bool']['filter'].append({
                'terms': {
                    field: [
                        i for i in range(start, start + _range)
                    ],
                }
            })
        elif field == 'color_types':
            start = randint(0, 7)
            _range = randint(2, 4)
            query['bool']['filter'].append({
                'terms': {
                    field: [
                        i for i in range(start, start + _range)
                    ],
                }
            })
        elif field == 'figure_type_id':
            query['bool']['filter'].append({
                'term': {
                    field: _get_random_figure_type_id(),
                }
            })
        elif field == 'figure_type_problem_id':
            query['bool']['filter'].append({
                'term': {
                    field: _get_random_figure_type_problem_id(),
                }
            })

    return query, sort


def _get_random_gender() -> str:
    return GENDERS[randint(1, 30) >= 20]


def _get_random_partner_id() -> int:
    return randint(1, 120)


def _get_random_clothing_category_id() -> int:
    return randint(1, 50)


def _get_random_price_tier() -> int:
    """
    0, 50 %, 10 - 100
    1, 25 %, 100 - 500
    2, 15 %, 500 - 1000
    3, 10 %, 1000+
    """
    flag = randint(1, 100)

    if flag <= 50:
        return 0
    if flag <= 75:
        return 1
    if flag <= 90:
        return 2

    return 3


def _get_random_price_by_price_tier(price_tier: int) -> float:
    if price_tier == 0:
        return randint(100, 1000) / 10
    if price_tier == 1:
        return randint(1001, 5000) / 10
    if price_tier == 2:
        return randint(5001, 10000) / 10
    if price_tier == 3:
        return randint(10001, 50000) / 10


def _get_random_price_range_by_price_tier(
    price_tier: int
) -> tuple[float, float]:
    max_val = randint(125, (1000, 5000, 10000, 50000)[price_tier])
    min_val = randint(100, max_val - 1)

    return min_val / 10, max_val / 10


def _get_random_text() -> str:
    return fake.text()


def _get_random_sport_flag() -> bool:
    return randint(1, 100) > 95


def _get_random_plus_size_flag() -> bool:
    return randint(1, 100) > 90


def _get_random_new_flag() -> bool:
    return randint(1, 100) > 80


def _get_random_priority() -> int:
    return randint(1, 10)


def _get_random_archetypes() -> list[int]:
    start = randint(0, 12)
    _range = randint(0, 4)

    return [i for i in range(start, start + _range)]


def _get_random_color_types() -> list[int]:
    start = randint(0, 8)
    _range = randint(0, 3)

    return [i for i in range(start, start + _range)]


def _get_random_figure_type_id() -> int:
    return randint(1, 5)


def _get_random_figure_type_problem_id() -> int:
    return randint(1, 20)
