from neo4j import GraphDatabase

# Verbindung zu Neo4j aufbauen
uri = "bolt://localhost:7687"
username = "neo4j"
password = "SuperPasswort"

driver = GraphDatabase.driver(uri, auth=(username, password))

def check_and_fix_features(tx):
    # check if all needed features exists for all nodes
    # 1. Durchschnittsalter berechnen
    avg_result = tx.run("""
    MATCH (u:User)
    WHERE u.age IS NOT NULL
    RETURN avg(u.age) AS avg_age
    """).single()

    average_age = int(avg_result["avg_age"]) if avg_result["avg_age"] is not None else 30

    # 2. Fehlende 'age' mit Durchschnitt setzen
    result_age = tx.run("MATCH (u:User) WHERE u.age IS NULL RETURN count(u) AS missing_age").single()["missing_age"]
    if result_age > 0:
        print(f"{result_age} User ohne 'age'. Setze Durchschnittswert {average_age}.")
        tx.run("MATCH (u:User) WHERE u.age IS NULL SET u.age = $avg", avg=average_age)
    else:
        print("Alle User haben 'age'.")

def project_graphsage_graph(tx):
    # Project a graph
    # Drop alte Projektion, wenn vorhanden
    tx.run("""
    CALL gds.graph.exists('sageGraph') YIELD exists
    WITH exists
    CALL apoc.do.when(
        exists,
        'CALL gds.graph.drop("sageGraph") YIELD graphName RETURN graphName',
        'RETURN "Not present" AS graphName',
        {}
    ) YIELD value RETURN value
    """)

    # GDS-Projektion mit User (mit age) + Book (ohne Property)
    tx.run("""
    CALL gds.graph.project(
        'sageGraph',
        {
            User: { properties: ['age'] },
            Book: { }
        },
        {
            RATED: {
                orientation: 'UNDIRECTED'
            }
        }
    )
    """)

def run_graphsage_train(tx):
    # calculate and create the embeddings
    tx.run("""
    CALL gds.beta.graphSage.train('sageGraph', {
      modelName: 'my-sage-model',
      nodeLabels: ['User'],
      featureProperties: ['age'],
      embeddingDimension: 128,
      epochs: 20,
      learningRate: 0.05,
      activationFunction: 'relu',
      sampleSizes: [25, 10] // 25 Nachbarn in 1.Ebene, 10 Nachbarn in 2. Ebene
    })
    YIELD modelInfo
    """)

def run_graphsage_write(tx):
    # saves the embeddings
    tx.run("""
    CALL gds.beta.graphSage.write('sageGraph', {
      modelName: 'my-sage-model',
      nodeLabels: ['User'],
      writeProperty: 'graphsageFeature'
    })
    YIELD nodePropertiesWritten
    """)

def run_knn_write(tx, top_k=5, similarity_cutoff=0.8):
    # calculation of knn
    # creating the relations 'similar_to'
    # to know which users are similar
    tx.run("""
    CALL gds.knn.write('userGraph', {
        nodeProperties: ['embedding'],
        topK: $topK,
        similarityCutoff: $cutoff,
        writeRelationshipType: 'SIMILAR_TO',
        writeProperty: 'similarity'
    })
    YIELD nodesCompared, relationshipsWritten;
    """, {"topK": top_k, "cutoff": similarity_cutoff})
