import typing as t
from types import TracebackType

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ElasticsearchException

from app import config as c
from app.logging import logger


class ElasticsearchClient:
    _es_client: Elasticsearch = None
    _es_node_types: dict[str, dict[str, str]] = {
        'master': {
            'host': c.ES_MASTER_NODE_HOST,
            'port': c.ES_MASTER_NODE_PORT,
        },
        'ingest': {
            'host': c.ES_INGEST_NODE_HOST,
            'port': c.ES_INGEST_NODE_PORT,
        }
    }
    _es_host: str = None
    _es_port: str = None
    _es_user: str = None
    _es_user_password: str = None

    def __init__(
        self,
        es_host: t.Optional[str] = None,
        es_port: t.Optional[str] = None,
        es_user: t.Optional[str] = None,
        es_user_password: t.Optional[str] = None,
        es_node_type: str = 'master'
    ) -> None:
        if es_host is None or es_port is None:
            es_host = self._es_node_types[es_node_type]['host']
            es_port = self._es_node_types[es_node_type]['port']

        self._es_host = es_host
        self._es_port = es_port
        self._es_user = es_user or c.ES_USER
        self._es_user_password = es_user_password or c.ES_USER_PASSWORD

    def __enter__(self) -> Elasticsearch:
        self._es_client = self._session_maker()
        return self._es_client

    def __exit__(
        self,
        exc_type: t.Optional[type],
        exc_val: t.Optional[ElasticsearchException],
        exc_tb: t.Optional[TracebackType]
    ) -> None:
        if exc_val is not None:
            logger.exception(exc_val)
        self._es_client.close()

    def _session_maker(self) -> Elasticsearch:
        client: Elasticsearch = Elasticsearch(
            f'http://{self._es_host}:{self._es_port}',
            http_auth=(self._es_user, self._es_user_password),
        )

        return client
