MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000111704" AND b.id = "ensg00000107984" MERGE (a)-[:regulates { evidence: ["pubmed:19148141", "pubmed:29087512", "pubmed:29126285", "pubmed:27924024"], databases: ["GTRD", "ReMap", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000132170" AND b.id = "ensg00000077092" MERGE (a)-[:regulates { evidence: ["pubmed:17202159", "pubmed:12839938", "pubmed:29087512", "pubmed:27924024"], databases: ["GTRD", "TRED", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000118513" AND b.id = "ensg00000185591" MERGE (a)-[:regulates { evidence: ["pubmed:29126285", "pubmed:27924024", "pubmed:17202159"], databases: ["GTRD", "ReMap", "TRED"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000078399" AND b.id = "ensg00000115738" MERGE (a)-[:regulates { evidence: ["pubmed:29087512", "pubmed:20565746"], databases: ["TRRUST"], evidence_type: "small_scale_evidence", detection_method: "inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000091831" AND b.id = "ensg00000171223" MERGE (a)-[:regulates { evidence: ["pubmed:29126285", "pubmed:18971253", "pubmed:27924024", "pubmed:11477071", "pubmed:17202159", "pubmed:29087512"], databases: ["GTRD", "PAZAR", "ReMap", "TRED", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000141510" AND b.id = "ensg00000153933" MERGE (a)-[:regulates { evidence: ["pubmed:29126285", "pubmed:27924024", "pubmed:17202159"], databases: ["GTRD", "ReMap", "TRED"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000172819" AND b.id = "ensg00000177606" MERGE (a)-[:regulates { evidence: ["pubmed:17202159"], databases: ["TRED"], evidence_type: "small_scale_evidence", detection_method: "inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000123268" AND b.id = "ensg00000140538" MERGE (a)-[:regulates { evidence: ["pubmed:27924024", "pubmed:17202159"], databases: ["GTRD", "TRED"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000101665" AND b.id = "ensg00000108821" MERGE (a)-[:regulates { evidence: ["pubmed:11279127", "pubmed:22761861"], databases: ["TFactS_via_DoRothea"], evidence_type: "small_scale_evidence", detection_method: "inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000197933" AND b.id = "ensg00000169429" MERGE (a)-[:regulates { evidence: ["pubmed:29087512", "pubmed:21593445"], databases: ["TRRUST"], evidence_type: "small_scale_evidence", detection_method: "inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000100811" AND b.id = "ensg00000073921" MERGE (a)-[:regulates { evidence: ["pubmed:22951020", "pubmed:29126285", "pubmed:27924024", "pubmed:26578589"], databases: ["GTRD", "ORegAnno", "ReMap"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000081189" AND b.id = "ensg00000205560" MERGE (a)-[:regulates { evidence: ["pubmed:15356291", "pubmed:29087512"], databases: ["TRRUST"], evidence_type: "small_scale_evidence", detection_method: "inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000113580" AND b.id = "ensg00000145113" MERGE (a)-[:regulates { evidence: ["pubmed:29087512", "pubmed:11418607", "pubmed:27924024"], databases: ["GTRD", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000169083" AND b.id = "ensg00000118137" MERGE (a)-[:regulates { evidence: ["pubmed:17202159"], databases: ["TRED"], evidence_type: "small_scale_evidence", detection_method: "inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000169083" AND b.id = "ensg00000163565" MERGE (a)-[:regulates { evidence: ["pubmed:16494870", "pubmed:29126285", "pubmed:20610535", "pubmed:27924024", "pubmed:29087512", "pubmed:22900683"], databases: ["GTRD", "HTRI", "ReMap", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation array;chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000185591" AND b.id = "ensg00000100170" MERGE (a)-[:regulates { evidence: ["pubmed:27924024", "pubmed:17202159"], databases: ["GTRD", "TRED"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000173039" AND b.id = "ensg00000180871" MERGE (a)-[:regulates { evidence: ["pubmed:19156404", "pubmed:18555777", "pubmed:29087512", "pubmed:27924024"], databases: ["GTRD", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000159216" AND b.id = "ensg00000163737" MERGE (a)-[:regulates { evidence: ["pubmed:21129147", "pubmed:29126285", "pubmed:17150917", "pubmed:29087512", "pubmed:23848403"], databases: ["ReMap", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000148737" AND b.id = "ensg00000081059" MERGE (a)-[:regulates { evidence: ["pubmed:29126285", "pubmed:22761861", "pubmed:27924024", "pubmed:10489374", "pubmed:15473860"], databases: ["GTRD", "ReMap", "TFactS_via_DoRothea"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000173473" AND b.id = "ensg00000039068" MERGE (a)-[:regulates { evidence: ["pubmed:27924024", "pubmed:24234451", "pubmed:24434208"], databases: ["GTRD", "IntAct_via_DoRothEA"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000101412" AND b.id = "ensg00000147853" MERGE (a)-[:regulates { evidence: ["pubmed:29126285", "pubmed:26578589", "pubmed:18971253", "pubmed:27924024", "pubmed:17202159"], databases: ["GTRD", "ORegAnno", "PAZAR", "ReMap", "TRED"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000136997" AND b.id = "ensg00000137409" MERGE (a)-[:regulates { evidence: ["pubmed:29126285", "pubmed:27924024", "pubmed:17202159"], databases: ["GTRD", "ReMap", "TRED"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000172216" AND b.id = "ensg00000163220" MERGE (a)-[:regulates { evidence: ["pubmed:29126285", "pubmed:9706399", "pubmed:27924024", "pubmed:29087512", "pubmed:22900683"], databases: ["GTRD", "HTRI", "ReMap", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;electrophoretic mobility shift assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000133895" AND b.id = "ensg00000130522" MERGE (a)-[:regulates { evidence: ["pubmed:29087512", "pubmed:27924024", "pubmed:22327296"], databases: ["GTRD", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000100146" AND b.id = "ensg00000204248" MERGE (a)-[:regulates { evidence: ["pubmed:12783851", "pubmed:29087512"], databases: ["TRRUST"], evidence_type: "small_scale_evidence", detection_method: "inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000144852" AND b.id = "ensg00000006327" MERGE (a)-[:regulates { evidence: ["pubmed:29087512", "pubmed:21072196"], databases: ["TRRUST"], evidence_type: "small_scale_evidence", detection_method: "inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000141510" AND b.id = "ensg00000197579" MERGE (a)-[:regulates { evidence: ["pubmed:29126285", "pubmed:27924024", "pubmed:17202159"], databases: ["GTRD", "ReMap", "TRED"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000141646" AND b.id = "ensg00000168036" MERGE (a)-[:regulates { evidence: ["pubmed:27924024", "pubmed:17202159"], databases: ["GTRD", "TRED"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000169083" AND b.id = "ensg00000104368" MERGE (a)-[:regulates { evidence: ["pubmed:29126285", "pubmed:20610535", "pubmed:27924024", "pubmed:17202159", "pubmed:22900683"], databases: ["GTRD", "HTRI", "ReMap", "TRED"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation array;chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000112182" AND b.id = "ensg00000100219" MERGE (a)-[:regulates { evidence: ["pubmed:29087512", "pubmed:24821775", "pubmed:29126285"], databases: ["ReMap", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000124440" AND b.id = "ensg00000116016" MERGE (a)-[:regulates { evidence: ["pubmed:29087512", "pubmed:27924024", "pubmed:19755485"], databases: ["GTRD", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000091831" AND b.id = "ensg00000126561" MERGE (a)-[:regulates { evidence: ["pubmed:27924024", "pubmed:17202159"], databases: ["GTRD", "TRED"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000115966" AND b.id = "ensg00000232810" MERGE (a)-[:regulates { evidence: ["pubmed:10748079", "pubmed:29126285", "pubmed:10688670", "pubmed:20068037", "pubmed:27924024", "pubmed:10913190", "pubmed:17202159", "pubmed:29087512"], databases: ["GTRD", "ReMap", "TRED", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000137203" AND b.id = "ensg00000173801" MERGE (a)-[:regulates { evidence: ["pubmed:29126285", "pubmed:27924024", "pubmed:17202159"], databases: ["GTRD", "ReMap", "TRED"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000185591" AND b.id = "ensg00000133315" MERGE (a)-[:regulates { evidence: ["pubmed:29126285", "pubmed:18206366", "pubmed:26578589", "pubmed:27924024", "pubmed:15691879", "pubmed:29087512"], databases: ["GTRD", "ORegAnno", "ReMap", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000179583" AND b.id = "ensg00000204287" MERGE (a)-[:regulates { evidence: ["pubmed:11429551", "pubmed:10886240", "pubmed:9300692", "pubmed:27924024", "pubmed:11889043", "pubmed:29087512", "pubmed:9600954"], databases: ["GTRD", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000253293" AND b.id = "ensg00000115738" MERGE (a)-[:regulates { evidence: ["pubmed:29087512", "pubmed:20565746"], databases: ["TRRUST"], evidence_type: "small_scale_evidence", detection_method: "inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000001167" AND b.id = "ensg00000203883" MERGE (a)-[:regulates { evidence: ["pubmed:18496767", "pubmed:29087512"], databases: ["TRRUST"], evidence_type: "small_scale_evidence", detection_method: "inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000179583" AND b.id = "ensg00000117560" MERGE (a)-[:regulates { evidence: ["pubmed:29087512", "pubmed:14563113"], databases: ["TRRUST"], evidence_type: "small_scale_evidence", detection_method: "inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000104825" AND b.id = "ensg00000171855" MERGE (a)-[:regulates { evidence: ["pubmed:29087512", "pubmed:10074115"], databases: ["TRRUST"], evidence_type: "small_scale_evidence", detection_method: "inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000095794" AND b.id = "ensg00000114013" MERGE (a)-[:regulates { evidence: ["pubmed:24234451", "pubmed:29126285", "pubmed:27924024", "pubmed:19299714"], databases: ["GTRD", "IntAct_via_DoRothEA", "ReMap"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000185591" AND b.id = "ensg00000103342" MERGE (a)-[:regulates { evidence: ["pubmed:29087512", "pubmed:22580340", "pubmed:29126285", "pubmed:27924024"], databases: ["GTRD", "ReMap", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000205250" AND b.id = "ensg00000134871" MERGE (a)-[:regulates { evidence: ["pubmed:27924024", "pubmed:17202159"], databases: ["GTRD", "TRED"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000179284" AND b.id = "ensg00000177030" MERGE (a)-[:regulates { evidence: ["pubmed:29126285", "pubmed:29087512", "pubmed:8055899"], databases: ["ReMap", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000151702" AND b.id = "ensg00000102145" MERGE (a)-[:regulates { evidence: ["pubmed:17202159", "pubmed:10523830", "pubmed:29087512", "pubmed:12724402"], databases: ["TRED", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000122877" AND b.id = "ensg00000128342" MERGE (a)-[:regulates { evidence: ["pubmed:29087512", "pubmed:24007274"], databases: ["TRRUST"], evidence_type: "small_scale_evidence", detection_method: "inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000125618" AND b.id = "ensg00000152804" MERGE (a)-[:regulates { evidence: ["pubmed:15062550", "pubmed:20211142"], databases: ["FANTOM4_via_DoRothEA"], evidence_type: "small_scale_evidence", detection_method: "inferred by curator" }]->(b);
MATCH (a:gene) WITH a MATCH (b:gene) WHERE a.id = "ensg00000173039" AND b.id = "ensg00000100889" MERGE (a)-[:regulates { evidence: ["pubmed:29126285", "pubmed:27924024", "pubmed:20137375", "pubmed:17202159", "pubmed:29087512"], databases: ["GTRD", "ReMap", "TRED", "TRRUST"], evidence_type: "small_scale_evidence", detection_method: "chromatin immunoprecipitation assay;inferred by curator" }]->(b);