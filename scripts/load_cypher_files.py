import os
import argparse
from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable
import time
from tqdm import tqdm
import concurrent.futures

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

def execute_cypher_batch(tx, statements):
    results = []
    for stmt in statements:
        result = tx.run(stmt)
        results.append(result.consume().counters)
    return results

def update_counters(total_counters, new_counters):
    for counter in new_counters:
        for key, value in counter.items():
            total_counters[key] = total_counters.get(key, 0) + value
    return total_counters

def load_cypher_file_in_batches(driver, file_path, batch_size=1000):
    total_counters = {}
    total_lines = sum(1 for _ in open(file_path, 'r'))
    
    with driver.session() as session, open(file_path, 'r') as file:
        statements = []
        pbar = tqdm(total=total_lines, desc=f"Loading {os.path.basename(file_path)}", unit="lines")
        for line in file:
            if line.strip():  # Ignore empty lines
                statements.append(line.strip())
                if len(statements) >= batch_size:
                    counters = session.write_transaction(execute_cypher_batch, statements)
                    total_counters = update_counters(total_counters, counters)
                    statements = []
                    pbar.update(batch_size)
        
        if statements:
            counters = session.write_transaction(execute_cypher_batch, statements)
            total_counters = update_counters(total_counters, counters)
            pbar.update(len(statements))
        
        pbar.close()
    
    return total_counters

def process_file(args):
    driver, file_path, batch_size = args
    print(f"\nProcessing {file_path}")
    start_time = time.time()
    counters = load_cypher_file_in_batches(driver, file_path, batch_size)
    end_time = time.time()
    print(f"Finished loading {file_path} in {end_time - start_time:.2f} seconds")
    return counters

def load_cypher_files(driver, root_dir, file_type, batch_size=1000):
    files_to_load = []
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file_type == 'nodes' and file.endswith('nodes.cypher'):
                files_to_load.append(os.path.join(subdir, file))
            elif file_type == 'edges' and file.endswith('edges.cypher'):
                files_to_load.append(os.path.join(subdir, file))
    
    total_counters = {}
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = [executor.submit(process_file, (driver, file_path, batch_size)) for file_path in files_to_load]
        for future in concurrent.futures.as_completed(futures):
            counters = future.result()
            total_counters = update_counters(total_counters, [counters])
    
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