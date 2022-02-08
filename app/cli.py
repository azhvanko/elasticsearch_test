import os.path
from collections import Counter
from pathlib import Path
from random import choice, randint
from time import time, time_ns

import click
import yaml
from elasticsearch import Elasticsearch

import app.config as c
from app.elasticsearch.session import ElasticsearchClient
from app.elasticsearch.utils import (
    bulk,
    CHUNK_SIZE,
    create_index,
    generate_random_document,
    generate_random_search_query
)
from app.logging import logger


@click.group()
def cli() -> None:
    pass


@cli.command('update_configs')
def update_configs() -> None:
    def update_yaml_config(
        file_path: Path,
        items: tuple[tuple[str, tuple[str, ...]]],
        passwords: dict[str, str]
    ) -> None:
        with open(file_path, 'r') as f:
            data: dict = yaml.load(f, Loader=yaml.FullLoader)

        for item in items:
            username, keys = item[0], item[1]
            if isinstance(data, dict):
                tmp = [data,]
            elif isinstance(data, list):
                tmp = data
            else:
                continue

            for l in tmp:
                tmp_dict = l
                for key in keys:
                    tmp_dict = tmp_dict[key]

                if tmp_dict['username'] == username:
                    tmp_dict['password'] = passwords[username]

        with open(file_path, 'w') as f:
            yaml.dump(data, f)

    # config files
    config_files: dict[str, Path] = {
        'env': c.BASE_DIR / '.env',
        'passwords': c.BASE_DIR / '.passwords',
        'elasticsearch_master_node': (
            c.BASE_DIR / 'docker' / 'elasticsearch' / 'elasticsearch_master_node.yml'
        ),
        'elasticsearch_data_node_1': (
                c.BASE_DIR / 'docker' / 'elasticsearch' / 'elasticsearch_data_node_1.yml'
        ),
        'elasticsearch_data_node_2': (
                c.BASE_DIR / 'docker' / 'elasticsearch' / 'elasticsearch_data_node_2.yml'
        ),
        'elasticsearch_ingest_node': (
                c.BASE_DIR / 'docker' / 'elasticsearch' / 'elasticsearch_ingest_node.yml'
        ),
        'kibana': (
            c.BASE_DIR / 'docker' / 'kibana' / 'kibana.yml'
        ),
        'metricbeat': (
            c.BASE_DIR / 'docker' / 'metricbeat' / 'metricbeat.yml'
        ),
        'elasticsearch_xpack': (
            c.BASE_DIR / 'docker' / 'metricbeat' / 'modules' / 'elasticsearch-xpack.yml'
        ),
    }

    # checks
    for key, value in config_files.items():
        assert os.path.exists(value), (
            f'{key} file does not exists, full path - {value}'
        )

    passwords: dict[str, str] = {}

    with open(config_files['passwords'], 'r') as file:
        for line in file.readlines():
            line = line.strip()
            if line.startswith('PASSWORD '):
                user, password = line.replace('PASSWORD ', '').split(' = ')
                passwords[user] = password

    # update default elasticsearch user password
    lines: list[str] = []
    with open(config_files['env'], 'r') as file:
        for line in file.readlines():
            if 'ES_USER_PASSWORD' in line:
                password = passwords['elastic']
                line = f'ES_USER_PASSWORD={password}\n'

            lines.append(line)

    with open(config_files['env'], 'w') as file:
        file.writelines(lines)

    # update yaml configs
    # kibana
    update_yaml_config(
        config_files['kibana'],
        (
            ('kibana_system', ('elasticsearch',),),
        ),
        passwords
    )
    # metricbeat
    update_yaml_config(
        config_files['metricbeat'],
        (
            ('elastic', ('output', 'elasticsearch',),),
        ),
        passwords
    )
    # elasticsearch xpack (metricbeat module)
    update_yaml_config(
        config_files['elasticsearch_xpack'],
        (
            ('remote_monitoring_user', tuple(),),
        ),
        passwords
    )

    # rewrite passwords file
    with open(config_files['passwords'], 'w') as file:
        for user in sorted(passwords.keys()):
            file.write(f'{user}={passwords[user]}\n')

    logger.info('Configs update successfully')


@cli.command('create_es_index')
@click.option('--index', type=str, default=c.ES_CATALOG_INDEX_NAME)
def create_es_index(index: str) -> None:
    with ElasticsearchClient() as es_client:
        if es_client.indices.exists(index=index):
            raise RuntimeError(f'Index "{index}" already exists') from None

        create_index(
            es_client,
            index,
            c.ES_CATALOG_INDEX_CONFIG
        )

        logger.info(f'Index "{index}" created successfully')


@cli.command('insert_test_data')
@click.option('--index', type=str, default=c.ES_CATALOG_INDEX_NAME)
@click.option(
    '--documents_count',
    type=int,
    default=c.ES_CATALOG_DOCUMENTS_COUNT
)
def insert_test_data(index: str, documents_count: int) -> None:
    with ElasticsearchClient(es_node_type='ingest') as es_client:
        documents: list[dict] = list()
        start = es_client.count(index=index)['count'] + 1
        stop = start + documents_count
        total_inserted = 0

        for document_id in range(start, stop):
            document = generate_random_document(document_id)
            document['_op_type'] = 'create'

            documents.append(document)
            total_inserted += 1

            if (
                len(documents) == CHUNK_SIZE or
                document_id == stop - 1 and documents
            ):
                _ = bulk(es_client, documents, index=index)
                documents.clear()
                logger.info(f'total inserted: {total_inserted}')


@cli.command('start_random_search')
@click.option('--index', type=str, default=c.ES_CATALOG_INDEX_NAME)
@click.option('--offset', type=int, default=0)
@click.option('--size', type=int, default=100)
@click.option('--filters_count', type=int, default=7)
def start_random_search(
    index: str,
    offset: int,
    size: int,
    filters_count: int
) -> None:

    def start(
        index: str,
        client: Elasticsearch,
        _avg: dict[str, list[float]],
        from_: int = 0,
        size: int = 100
    ) -> None:
        flag = 0
        threshold = 1000
        s_counter = Counter()
        o_counter = Counter()
        start_time = time()

        while 1:
            flag += 1
            query, sort = generate_random_search_query(filters_count=filters_count)

            start_time_ns = time_ns()

            response: dict = client.search(
                query=query,
                index=index,
                from_=from_,
                size=size,
                request_timeout=30,
                sort=sort,
                _source_includes=['clothing_item_id', ]
            )

            search_time = response['took']
            end_time = time() - start_time
            end_time_ns = (time_ns() - start_time_ns) // 1_000_000

            s_counter[search_time] += 1
            o_counter[end_time_ns] += 1

            if flag == threshold:
                s_total = 0
                o_total = 0

                for ms, cnt in s_counter.items():
                    s_total += ms * cnt

                for ms, cnt in o_counter.items():
                    o_total += ms * cnt

                s_avg = s_total / flag
                o_avg = o_total / flag - s_avg

                _avg['s_avg'].append(s_avg)
                _avg['o_avg'].append(o_avg)

                s_counter.clear()
                o_counter.clear()
                flag = 0
                start_time = time()

                logger.info(
                    f'total time: {end_time:>5.2f} s, '
                    f'avg search time: {s_avg:>5.2f} ms, '
                    f'avg overhead time: {o_avg:>5.2f} ms'
                )

    with ElasticsearchClient() as es_client:
        _avg: dict[str, list[float]] = {
            's_avg': [],
            'o_avg': [],
        }

        try:
            start_time = time()
            start(index, es_client, _avg, offset, size)
        except KeyboardInterrupt:
            s_avg = sum(_avg['s_avg']) / len(_avg['s_avg'])
            o_avg = sum(_avg['o_avg']) / len(_avg['o_avg'])
            end_time = time() - start_time

            logger.info(
                f'\ntotal time: {end_time:>21.2f} s'
                f'\ntotal avg search time: {s_avg:>9.2f} ms'
                f'\ntotal avg overhead time: {o_avg:>7.2f} ms'
            )


@cli.command('start_random_operations')
@click.option('--index', type=str, default=c.ES_CATALOG_INDEX_NAME)
def start_random_operations(index: str) -> None:

    operations: tuple[str, ...] = (
        'create',
        'update',
        'delete',
    )
    updated_documents: dict[str, str] = dict()
    deleted_documents: set[str] = set()

    with ElasticsearchClient() as es_client:
        documents_count = es_client.count(index=index)['count']
        logger.info(f'documents count - {documents_count}')

        while 1:
            operation = choice(operations)
            logger.info(f'operation type - "{operation}"')

            document_ids: list[str] = list()
            documents: list[dict] = list()

            if operation == 'create':
                start = documents_count + 1
                stop = documents_count + randint(50, 100) + 1

                for document_id in range(start, stop):
                    document = generate_random_document(document_id)
                    document['_op_type'] = operation

                    documents.append(document)

                _ = bulk(es_client, documents, index=index)
                logger.info(f'total inserted: {len(documents)}')
                documents_count += len(documents)
            elif operation == 'update':
                _count = randint(50, 100)
                query, _ = generate_random_search_query(filters_count=4)

                response: dict = es_client.search(
                    query=query,
                    index=index,
                    from_=0,
                    size=1000,
                    _source_includes=['clothing_item_id',]   # noqa
                )

                for item in response['hits']['hits']:
                    _id = item['_id']
                    clothing_item_id = item['_source']['clothing_item_id']
                    if (
                        _id not in updated_documents and
                        _id not in deleted_documents
                    ):
                        document_ids.append(_id)
                        updated_documents[_id] = clothing_item_id
                        _count -= 1

                        if not _count:
                            break

                for document_id in document_ids:
                    clothing_item_id = updated_documents[document_id]
                    document = generate_random_document(clothing_item_id)

                    documents.append({
                        '_op_type': operation,
                        '_id': document_id,
                        'doc': document,
                    })

                _ = bulk(es_client, documents, index=index)
                logger.info(f'total updated: {len(document_ids)}')
            elif operation == 'delete':
                _count = randint(50, 75)
                query, _ = generate_random_search_query(filters_count=4)

                response: dict = es_client.search(
                    query=query,
                    index=index,
                    from_=0,
                    size=1000,
                    _source=False
                )

                for item in response['hits']['hits']:
                    _id = item['_id']
                    if _id not in deleted_documents:
                        document_ids.append(_id)
                        deleted_documents.add(_id)
                        _count -= 1

                        if not _count:
                            break

                for document_id in document_ids:
                    documents.append({
                        '_op_type': operation,
                        '_id': document_id,
                    })

                _ = bulk(es_client, documents, index=index, ignore_status=(404,))
                logger.info(f'total deleted: {len(document_ids)}')

            # cleanup
            documents.clear()
            document_ids.clear()
