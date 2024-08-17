
CALL apoc.periodic.iterate(
    "LOAD CSV WITH HEADERS FROM 'file:////home/developer/Desktop/projects/biocypher-kg/output/gencode/transcript/edges_transcribed_to.csv' AS row FIELDTERMINATOR '|' RETURN row",
    "MATCH (source:gene {id: row.source_id})
    MATCH (target:transcript {id: row.target_id})
    MERGE (source)-[r:transcribed_to]->(target)
    SET r += apoc.map.removeKeys(row, ['source_id', 'target_id', 'label'])",
    {batchSize:1000, parallel:true, concurrency:4}
)
YIELD batches, total
RETURN batches, total;
                