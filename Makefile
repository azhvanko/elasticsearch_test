# custom variables
SHELL = /bin/bash

# SHORTCUTS

# docker
up_elasticsearch:
	docker-compose up --build elasticsearch_master_node elasticsearch_data_node_1 elasticsearch_data_node_2

up_monitoring:
	docker-compose up --build metricbeat kibana
