#!/usr/bin/env python3

import os
import yaml
import time
from elasticsearch import Elasticsearch
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetadataHandler(FileSystemEventHandler):
    def __init__(self, es_client, watch_path, index_name="test"):
        self.es_client = es_client
        self.watch_path = os.path.abspath(watch_path)
        self.index_name = index_name

    def process_metadata_yaml(self, yaml_path):
        """Process an metadata annotation YAML file and update related files in Elasticsearch."""
        try:
            with open(yaml_path, 'r') as f:
                metadata = yaml.safe_load(f)
            
            if not metadata:
                return

            # Get the directory containing the YAML file
            yaml_dir = os.path.dirname(yaml_path)
            
            # Recursively process all files in this directory and subdirectories
            self.update_files_with_metadata(yaml_dir, metadata)
            
        except Exception as e:
            logger.error(f"Error processing YAML file {yaml_path}: {str(e)}")

    def update_files_with_metadata(self, directory, metadata):
        """Recursively update all files in directory with the metadata."""
        for root, _, files in os.walk(directory):
            for filename in files:
                if filename == 'metadata_annotation.yaml':
                    continue  # Skip the annotation file itself
                
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, self.watch_path)
                
                # Get existing document from Elasticsearch
                try:
                    doc = self.es_client.get(index=self.index_name, id=relative_path)
                    if doc['found']:
                        # Update existing document with metadata
                        doc_source = doc['_source']
                        doc_source['metadata'] = metadata
                        self.es_client.index(
                            index=self.index_name,
                            id=relative_path,
                            document=doc_source
                        )
                        logger.info(f"Updated metadata for {relative_path}")
                except Exception as e:
                    logger.warning(f"Could not update metadata for {relative_path}: {str(e)}")

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('metadata_annotation.yaml'):
            logger.info(f"Processing new metadata annotation file: {event.src_path}")
            self.process_metadata_yaml(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('metadata_annotation.yaml'):
            logger.info(f"Processing modified metadata annotation file: {event.src_path}")
            self.process_metadata_yaml(event.src_path)

def main():
    # Elasticsearch configuration
    es_host = os.getenv('ELASTIC_HOST', 'http://elasticsearch:9200')
    es_user = os.getenv('ELASTIC_USERNAME', 'elastic')
    es_pass = os.getenv('ELASTIC_PASSWORD')
    watch_path = os.getenv('WATCH_PATH', '/tmp/es')
    index_name = os.getenv('ELASTIC_INDEX', 'test')

    if not es_pass:
        raise ValueError("ELASTIC_PASSWORD environment variable must be set")

    # Initialize Elasticsearch client
    es = Elasticsearch(
        es_host,
        basic_auth=(es_user, es_pass),
        verify_certs=False
    )

    # Initialize the event handler and observer
    event_handler = MetadataHandler(es, watch_path, index_name)
    observer = Observer()
    observer.schedule(event_handler, watch_path, recursive=True)
    observer.start()

    # Initial scan for existing metadata_annotation.yaml files
    logger.info("Performing initial scan for metadata annotation files...")
    for root, _, files in os.walk(watch_path):
        for filename in files:
            if filename == 'metadata_annotation.yaml':
                yaml_path = os.path.join(root, filename)
                logger.info(f"Processing existing metadata annotation file: {yaml_path}")
                event_handler.process_metadata_yaml(yaml_path)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
