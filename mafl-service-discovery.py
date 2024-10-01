import docker
import yaml
import time
from threading import Thread
from pprint import pprint
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import os
import re

def replace_env_variables(config):
    pattern = re.compile(r'\$\{(\w+)\}')
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, str):
                matches = pattern.findall(value)
                for match in matches:
                    env_value = os.getenv(match, '')
                    value = value.replace(f'${{{match}}}', env_value)
                config[key] = value
            elif isinstance(value, dict):
                replace_env_variables(value)
            elif isinstance(value, list):
                for i in range(len(value)):
                    if isinstance(value[i], str):
                        matches = pattern.findall(value[i])
                        for match in matches:
                            env_value = os.getenv(match, '')
                            value[i] = value[i].replace(f'${{{match}}}', env_value)
                    elif isinstance(value[i], dict):
                        replace_env_variables(value[i])
    return config

def get_mafl_services():
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)
        mafl_services = {}

        for container in containers:
            if container.status == 'running':
                labels = container.attrs['Config'].get('Labels', {})
                
                if labels.get('mafl.enable') == 'true':
                    group = labels.get('mafl.group', 'Miscellaneous')
                    
                    if group not in mafl_services:
                        mafl_services[group] = []
                    
                    service = {
                        'title': labels.get('mafl.title', container.name),
                        'description': labels.get('mafl.description', ''),
                        'link': labels.get('mafl.link', ''),
                        'icon': {
                            'name': labels.get('mafl.icon.name', ''),
                            'url': labels.get('mafl.icon.url', ''),
                            'wrap': labels.get('mafl.icon.wrap', 'true').lower() == 'true',
                        }
                    }
                    
                    if 'mafl.icon.color' in labels:
                        service['icon']['color'] = labels['mafl.icon.color']
                    
                    if 'mafl.status.enabled' in labels:
                        service['status'] = {
                            'enabled': labels['mafl.status.enabled'].lower() == 'true',
                            'interval': int(labels.get('mafl.status.interval', 60))
                        }
                        
                    for main_key in list(service.keys()):
                        if isinstance(service[main_key], dict):
                            for sub_key in list(service[main_key].keys()):
                                if service[main_key][sub_key] == '':
                                    del service[main_key][sub_key]
                            if not service[main_key]:
                                del service[main_key]

                    for key in list(service.keys()):
                        if service[key] == '' and key != 'icon':
                            del service[key]
                        
                    if group not in mafl_services:
                        mafl_services[group] = []

                    mafl_services[group].append(service)

                    # print(f"Group {group}:")
                    # pprint(service)

        return mafl_services

    except Exception as e:
        print(f"An error occurred: {e}")
        return {}

def update_config_yaml(mafl_services):

    with open('config/base.yml', 'r') as file:
        base_config = yaml.safe_load(file)
        base_config = replace_env_variables(base_config)
    
    for group, services in mafl_services.items():
        if group not in base_config['services']:
            base_config['services'][group] = []
        
        base_config['services'][group].extend(services)
    
    with open('config/config.yml', 'r') as file:
        current_config = yaml.safe_load(file)
    
    if current_config != base_config:
        with open('config/config.yml', 'w') as file:
            yaml.dump(base_config, file, sort_keys=False)

def monitor_docker_events():
    try:
        client = docker.from_env()

        def event_stream():
            for event in client.events(decode=True):
                yield event

        for event in event_stream():
            if event['Type'] in ['container', 'service']:
                mafl_services = get_mafl_services()
                update_config_yaml(mafl_services)
                # print("config.yml has been updated due to Docker event.")

    except Exception as e:
        print(f"An error occurred: {e}")

class BaseYamlHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('base.yml'):
            print("base.yml has been modified. Rebuilding config.yml...")
            mafl_services = get_mafl_services()
            update_config_yaml(mafl_services)

def watch_base_yaml():
    event_handler = BaseYamlHandler()
    observer = Observer()
    observer.schedule(event_handler, path='config', recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    mafl_services = get_mafl_services()
    update_config_yaml(mafl_services)
    print("Initial config.yml has been created with MAFL services.")

    # Start a separate thread to monitor Docker events
    event_monitor_thread = Thread(target=monitor_docker_events)
    event_monitor_thread.start()

    # Start a separate thread to watch base.yml
    base_yaml_watcher_thread = Thread(target=watch_base_yaml)
    base_yaml_watcher_thread.start()

    # Keep the main thread running to prevent the program from exiting
    while True:
        time.sleep(1)
