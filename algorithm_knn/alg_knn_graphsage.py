from neo4j import GraphDatabase

# Verbindung zu Neo4j aufbauen
uri = "bolt://localhost:7687"
username = "neo4j"
password = "SuperPasswort"

driver = GraphDatabase.driver(uri, auth=(username, password))

def check_and_fix_features(tx):
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
    tx.run("""
    CALL gds.beta.graphSage.write('sageGraph', {
      modelName: 'my-sage-model',
      nodeLabels: ['User'],
      writeProperty: 'graphsageFeature'
    })
    YIELD nodePropertiesWritten
    """)
