import os
import argparse
from neo4j import GraphDatabase
from neo4j.exceptions import AuthError

# Define Neo4j connection details
NEO4J_URI = "neo4j://0.0.0.0:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "icog-bioai"  # Change this to your Neo4j password

# Initialize the Neo4j driver
def get_driver():
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        return driver
    except AuthError as e:
        print(f"Authentication error: {e}")
        return None

def execute_cypher_batch(session, cypher_batch):
    session.run(cypher_batch)

def load_cypher_file_in_batches(session, file_path, batch_size=1000):
    with open(file_path, 'r') as file:
        cypher_batch = ""
        count = 0

        for line in file:
            cypher_batch += line
            count += 1
            if count >= batch_size:
                execute_cypher_batch(session, cypher_batch)
                cypher_batch = ""
                count = 0
        
        if cypher_batch:
            execute_cypher_batch(session, cypher_batch)

def load_cypher_files(driver, root_dir, file_type, batch_size=1000):
    files_to_load = []
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file_type == 'nodes' and file.endswith('nodes.cypher'):
                files_to_load.append(os.path.join(subdir, file))
            elif file_type == 'edges' and file.endswith('edges.cypher'):
                files_to_load.append(os.path.join(subdir, file))
    
    with driver.session() as session:
        for file_path in files_to_load:
            print(f"Loading {file_type} from {file_path}")
            load_cypher_file_in_batches(session, file_path, batch_size)

if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Load .cypher files into Neo4j.")
    parser.add_argument("directory", type=str, help="Root directory containing .cypher files")
    parser.add_argument("--batch-size", type=int, default=1000, help="Number of Cypher statements per batch")

    args = parser.parse_args()
    root_directory = args.directory
    batch_size = args.batch_size

    driver = get_driver()
    if driver:
        # Load all nodes first
        load_cypher_files(driver, root_directory, 'nodes', batch_size)

        # Load all edges after nodes
        load_cypher_files(driver, root_directory, 'edges', batch_size)

        driver.close()
    else:
        print("Failed to connect to Neo4j. Please check your credentials and connection settings.")
