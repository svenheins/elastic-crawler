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
                
                # Search for document by file URL
                try:
                    # Use real path for logging
                    real_url = f"file://{os.path.abspath(file_path)}"
                    # Replace path for ES query
                    query_url = f"file:///tmp/es/{os.path.relpath(file_path, self.watch_path)}"
                    logger.info(f"Real path: {real_url}")
                    logger.info(f"Searching with URL: {query_url}")
                    
                    search_result = self.es_client.search(
                        index=self.index_name,
                        query={
                            "match_phrase": {
                                "file.url": query_url
                            }
                        }
                    )
                    
                    if search_result['hits']['total']['value'] > 0:
                        # Found the document
                        doc_id = search_result['hits']['hits'][0]['_id']
                        logger.info(f"Found document with URL {query_url}, id: {doc_id}")
                        
                        # Get and update the document
                        doc = self.es_client.get(index=self.index_name, id=doc_id)
                        if doc['found']:
                            doc_source = doc['_source']
                            doc_source['metadata'] = metadata
                            self.es_client.index(
                                index=self.index_name,
                                id=doc_id,
                                document=doc_source
                            )
                            logger.info(f"Updated metadata for {doc_id}")
                    else:
                        logger.warning(f"No document found with URL: {query_url}")
                except Exception as e:
                    logger.warning(f"Error processing {filename}: {str(e)}")

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('metadata_annotation.yaml'):
            logger.info(f"Processing new metadata annotation file: {event.src_path}")
            self.process_metadata_yaml(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('metadata_annotation.yaml'):
            logger.info(f"Processing modified metadata annotation file: {event.src_path}")
            self.process_metadata_yaml(event.src_path)

def scan_directory(event_handler, watch_path):
    """Perform a scan of the directory for metadata files."""
    logger.info("Scanning for metadata annotation files...")
    for root, _, files in os.walk(watch_path):
        for filename in files:
            if filename == 'metadata_annotation.yaml':
                yaml_path = os.path.join(root, filename)
                logger.info(f"Processing metadata annotation file: {yaml_path}")
                event_handler.process_metadata_yaml(yaml_path)

def main():
    # Elasticsearch configuration
    es_host = os.getenv('ELASTIC_HOST')
    es_user = os.getenv('ELASTIC_USERNAME')
    es_pass = os.getenv('ELASTIC_PASSWORD')
    watch_path = os.getenv('WATCH_PATH')
    index_name = os.getenv('ELASTIC_INDEX')
    scan_interval = int(os.getenv('SCAN_INTERVAL_SECONDS', '60'))

    # Validate required environment variables
    if not es_host:
        raise ValueError("ELASTIC_HOST environment variable must be set")
    if not es_user:
        raise ValueError("ELASTIC_USERNAME environment variable must be set")
    if not watch_path:
        raise ValueError("WATCH_PATH environment variable must be set")
    if not index_name:
        raise ValueError("ELASTIC_INDEX environment variable must be set")
    if not es_pass:
        raise ValueError("ELASTIC_PASSWORD environment variable must be set")

    logger.info(f"Starting annotation crawler with scan interval: {scan_interval} seconds")

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

    try:
        last_scan_time = 0
        ratio_info = {0.25: False, 0.5: False, 0.75: False}
        while True:
            current_time = time.time()
            ratio  = (current_time - last_scan_time) / scan_interval
            # print info if ratio surpasses 0.25, 0.5, 0.75, 1.0
            if ratio >= 0.75 and not ratio_info[0.75]:
                ratio_info[0.75] = True
                logger.info("Scan interval reached 75%")
            if ratio >= 0.5 and not ratio_info[0.5]:
                ratio_info[0.5] = True
                logger.info("Scan interval reached 50%")
            if ratio >= 0.25 and not ratio_info[0.25]:
                ratio_info[0.25] = True
                logger.info("Scan interval reached 25%")
            
            # Check if it's time for a new scan
            if current_time - last_scan_time >= scan_interval:
                scan_directory(event_handler, watch_path)
                ratio_info = {0.25: False, 0.5: False, 0.75: False}
                last_scan_time = current_time
                logger.info("Waiting for next scan..." + str(scan_interval) + " seconds")
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
