MATCH (a:snp) WITH a MATCH (b:gene) WHERE a.id = "rs10" AND b.id = "ensg00000105810" MERGE (a)-[:closest_gene { chr: "chr7", pos: 92754574, distance: -510121 }]->(b);
MATCH (a:snp) WITH a MATCH (b:gene) WHERE a.id = "rs10000003" AND b.id = "ensg00000171476" MERGE (a)-[:closest_gene { chr: "chr4", pos: 56695481, distance: 819404 }]->(b);
MATCH (a:snp) WITH a MATCH (b:gene) WHERE a.id = "rs10000006" AND b.id = "ensg00000164023" MERGE (a)-[:closest_gene { chr: "chr4", pos: 107905227, distance: 911482 }]->(b);
MATCH (a:snp) WITH a MATCH (b:gene) WHERE a.id = "rs10000007" AND b.id = "ensg00000145349" MERGE (a)-[:closest_gene { chr: "chr4", pos: 113632097, distance: 743570 }]->(b);
MATCH (a:snp) WITH a MATCH (b:gene) WHERE a.id = "rs10000008" AND b.id = "ensg00000174473" MERGE (a)-[:closest_gene { chr: "chr4", pos: 171855053, distance: 880678 }]->(b);
MATCH (a:snp) WITH a MATCH (b:gene) WHERE a.id = "rs10000009" AND b.id = "ensg00000109205" MERGE (a)-[:closest_gene { chr: "chr4", pos: 70183236, distance: 879024 }]->(b);
MATCH (a:snp) WITH a MATCH (b:gene) WHERE a.id = "rs1000001" AND b.id = "ensg00000179915" MERGE (a)-[:closest_gene { chr: "chr2", pos: 50484504, distance: -335423 }]->(b);
