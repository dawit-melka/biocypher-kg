
            CALL apoc.periodic.iterate(
              "LOAD CSV WITH HEADERS FROM 'file:////home/developer/Desktop/projects/biocypher-kg/output/gencode/transcript/nodes.csv' AS row RETURN row",
              "MERGE (n:transcript {id: row.id})
               SET n += apoc.map.removeKeys(row, ['id'])",
              {batchSize:1000, parallel:false}
            )
            YIELD batches, total
            RETURN batches, total
            