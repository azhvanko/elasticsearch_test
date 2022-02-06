# read and export the environment variables from '.env'
include ./.env
export

# custom variables
SHELL = /bin/bash
ES_MASTER_NODE_CONTAINER = catalog_elasticsearch_master_node
MB_CONTAINER = catalog_metricbeat
KB_CONTAINER = catalog_kibana
ES_MASTER_NODE_ADDRESS = ${ES_MASTER_NODE_HOST}:${ES_MASTER_NODE_PORT}
ES_CREDENTIALS = ${ES_USER}:${ES_USER_PASSWORD}

# SHORTCUTS

# docker
up_elasticsearch:
	docker-compose up --build elasticsearch_master_node elasticsearch_data_node_1 elasticsearch_data_node_2 elasticsearch_ingest_node

up_monitoring:
	docker-compose up --build metricbeat kibana

down:
	docker-compose down -v --rmi all

elasticsearch_master_node:
	docker exec -it $(ES_MASTER_NODE_CONTAINER) bash

metricbeat:
	docker exec -it $(MB_CONTAINER) bash

kibana:
	docker exec -it $(KB_CONTAINER) bash

# elasticsearch
setup_passwords:
	# initiating the setup of passwords for reserved users
	docker exec -it $(ES_MASTER_NODE_CONTAINER) bash -c "echo "Y" | bin/elasticsearch-setup-passwords auto -u "http://localhost:9200"" > .passwords
	# update passwords in config files
	python manage.py update_configs

setup_es_test_stand:
	python manage.py create_es_index
	python manage.py insert_test_data

delete_es_catalog_index:
	curl -u $(ES_CREDENTIALS) -X DELETE "$(ES_MASTER_NODE_ADDRESS)/${ES_CATALOG_INDEX_NAME}"

es_catalog_index_mapping:
	curl -u $(ES_CREDENTIALS) -X GET "$(ES_MASTER_NODE_ADDRESS)/${ES_CATALOG_INDEX_NAME}/_mapping?pretty"

es_catalog_index_stat:
	curl -u $(ES_CREDENTIALS) -X GET "$(ES_MASTER_NODE_ADDRESS)/${ES_CATALOG_INDEX_NAME}/_stats?pretty"

es_list_indices:
	curl -u $(ES_CREDENTIALS) -X GET "$(ES_MASTER_NODE_ADDRESS)/_cat/indices?pretty"
