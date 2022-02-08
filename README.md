# Catalog  

## Dependencies
* Elasticsearch 7.17.0
* Python 3.9
* Docker 20.10.12
* Docker-compose 2.2.3
## Setup
### System
##### First you need to increase the limits on mmap counts. See [virtual memory](https://www.elastic.co/guide/en/elasticsearch/reference/current/vm-max-map-count.html)
    sudo sysctl -w vm.max_map_count=262144
### Elasticsearch
##### Run `Elasticsearch` and sets the passwords for the built-in users
    make up_elasticsearch && make setup_passwords
##### Create `Elasticsearch` index and insert test data
    make setup_es_test_stand
##### To run random search
    make start_random_search
##### To run random insert / update / delete operations
    make start_random_operations
### Monitoring
##### Run `Metricbeat` and `Kibana`
    make up_monitoring
##### Go to http://localhost:5601/kibana, log in, open the main menu, and then click `Stack Monitoring`
### Teardown
    make drop_all
