import os.path
from pathlib import Path

import click
import yaml

import app.config as c
from app.elasticsearch.session import ElasticsearchClient
from app.elasticsearch.utils import create_index
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
        'kibana': (
            c.BASE_DIR / 'docker' / 'kibana' / 'kibana.yml'
        ),
        'metricbeat': (
            c.BASE_DIR / 'docker' / 'metricbeat' / 'metricbeat.yml'
        ),
        'elasticsearch_xpack': (
            c.BASE_DIR / 'docker' / 'metricbeat' / 'modules' / 'elasticsearch-xpack.yml'
        )
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
