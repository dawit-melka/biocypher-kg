import os
import argparse
from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable
import time

NEO4J_URI = "neo4j://100.67.47.42:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "icog-bioai"

def get_driver():
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        return driver
    except AuthError as e:
        print(f"Authentication error: {e}")
        return None
    except ServiceUnavailable as e:
        print(f"Neo4j service unavailable: {e}")
        return None

def execute_cypher_batch(tx, cypher_batch):
    result = tx.run(cypher_batch)
    return result.consume().counters

def update_counters(total_counters, new_counters):
    if isinstance(new_counters, dict):
        for key, value in new_counters.items():
            total_counters[key] = total_counters.get(key, 0) + value
    else:  # Assume it's a SummaryCounters object
        total_counters['nodes_created'] = total_counters.get('nodes_created', 0) + new_counters.nodes_created
        total_counters['relationships_created'] = total_counters.get('relationships_created', 0) + new_counters.relationships_created
        total_counters['properties_set'] = total_counters.get('properties_set', 0) + new_counters.properties_set
        total_counters['labels_added'] = total_counters.get('labels_added', 0) + new_counters.labels_added
    return total_counters

def load_cypher_file_in_batches(session, file_path, batch_size=1000):
    total_counters = {}
    with open(file_path, 'r') as file:
        cypher_batch = []
        for line in file:
            if line.strip():  # Ignore empty lines
                cypher_batch.append(line.strip())
                if len(cypher_batch) >= batch_size:
                    counters = session.write_transaction(execute_cypher_batch, "\n".join(cypher_batch))
                    total_counters = update_counters(total_counters, counters)
                    cypher_batch = []
        
        if cypher_batch:
            counters = session.write_transaction(execute_cypher_batch, "\n".join(cypher_batch))
            total_counters = update_counters(total_counters, counters)
    
    return total_counters

def load_cypher_files(driver, root_dir, file_type, batch_size=1000):
    files_to_load = []
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file_type == 'nodes' and file.endswith('nodes.cypher'):
                files_to_load.append(os.path.join(subdir, file))
            elif file_type == 'edges' and file.endswith('edges.cypher'):
                files_to_load.append(os.path.join(subdir, file))
    
    total_counters = {}
    with driver.session() as session:
        for file_path in files_to_load:
            print(f"Loading {file_type} from {file_path}")
            start_time = time.time()
            counters = load_cypher_file_in_batches(session, file_path, batch_size)
            total_counters = update_counters(total_counters, counters)
            end_time = time.time()
            print(f"Finished loading {file_path} in {end_time - start_time:.2f} seconds")
    
    return total_counters

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load .cypher files into Neo4j.")
    parser.add_argument("directory", type=str, help="Root directory containing .cypher files")
    parser.add_argument("--batch-size", type=int, default=1000, help="Number of Cypher statements per batch")

    args = parser.parse_args()
    root_directory = args.directory
    batch_size = args.batch_size

    driver = get_driver()
    if driver:
        try:
            start_time = time.time()
            
            node_counters = load_cypher_files(driver, root_directory, 'nodes', batch_size)
            print("Node loading statistics:", node_counters)
            
            edge_counters = load_cypher_files(driver, root_directory, 'edges', batch_size)
            print("Edge loading statistics:", edge_counters)
            
            end_time = time.time()
            print(f"Total execution time: {end_time - start_time:.2f} seconds")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            driver.close()
    else:
        print("Failed to connect to Neo4j. Please check your credentials and connection settings.")