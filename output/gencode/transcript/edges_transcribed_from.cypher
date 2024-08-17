
CALL apoc.periodic.iterate(
    "LOAD CSV WITH HEADERS FROM 'file:///edges_transcribed_from.csv' AS row FIELDTERMINATOR '|' RETURN row",
    "MATCH (source:transcript {id: row.source_id})
    MATCH (target:gene {id: row.target_id})
    MERGE (source)-[r:transcribed_from]->(target)
    SET r += apoc.map.removeKeys(row, ['source_id', 'target_id', 'label'])",
    {batchSize:1000, parallel:true, concurrency:4}
)
YIELD batches, total
RETURN batches, total;
                