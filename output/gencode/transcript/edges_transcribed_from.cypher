
                CALL apoc.periodic.iterate(
                  "LOAD CSV WITH HEADERS FROM 'file:////home/developer/Desktop/projects/biocypher-kg/output/gencode/transcript/edges_transcribed_from.csv' AS row RETURN row",
                  "MATCH (source:Node {id: row.source_id})
                   MATCH (target:Node {id: row.target_id})
                   CALL apoc.create.relationship(
                     source, 
                     row.label, 
                     apoc.map.removeKeys(row, ['source_id', 'target_id', 'label']), 
                     target
                   ) YIELD rel
                   RETURN count(rel)",
                  {batchSize:500, parallel:false}
                )
                YIELD batches, total
                RETURN batches, total
                