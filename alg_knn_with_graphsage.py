from neo4j import GraphDatabase
# zeit messen, code separat, keine emoji

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
        print(f"⚠️  {result_age} User ohne 'age'. Setze Durchschnittswert {average_age}.")
        tx.run("MATCH (u:User) WHERE u.age IS NULL SET u.age = $avg", avg=average_age)
    else:
        print("✅ Alle User haben 'age'.")

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


def clean_embeddings_strict(tx):
    print("🧼 Bereinige 'graphsageFeature' → 'cleanedFeature'...")

    # Nur vollständig numerische, saubere Vektoren übernehmen
    tx.run("""
    MATCH (u:User)
    WHERE u.graphsageFeature IS NOT NULL
      AND size(u.graphsageFeature) >= 5
      AND NONE(x IN u.graphsageFeature WHERE x IS NULL)
      AND ALL(x IN u.graphsageFeature WHERE x + 0 = x)
    SET u.cleanedFeature = u.graphsageFeature
    """)

    # Und zusätzlich alle zu kurzen cleanedFeature löschen (Backup)
    tx.run("""
    MATCH (u:User)
    WHERE u.cleanedFeature IS NULL OR size(u.cleanedFeature) < 5
    REMOVE u.cleanedFeature
    """)


def project_knn_graph_a(tx):
    print("📦 Erstelle KNN-Projektion nur mit sauberen Vektoren...")

    tx.run("""
    CALL gds.graph.exists('userGraph') YIELD exists
    WITH exists
    CALL apoc.do.when(
        exists,
        'CALL gds.graph.drop("userGraph") YIELD graphName RETURN graphName',
        'RETURN "Kein Graph vorhanden" AS graphName',
        {}
    ) YIELD value RETURN value
    """)

    # ❗️ ACHTUNG: cleanedFeature verwenden, nicht graphsageFeature
    tx.run("""
    CALL gds.graph.project.cypher(
        'userGraph',
        'MATCH (u:User) WHERE u.cleanedFeature IS NOT NULL AND size(u.cleanedFeature) > 0 RETURN id(u) AS id, u.cleanedFeature AS graphsageFeature',
        'RETURN null AS source, null AS target'
    )
    """)

def project_knn_graph(tx):
    print("📦 Erstelle KNN-Projektion nur mit sauberen Vektoren...")

    # Bestehenden Graph löschen, falls vorhanden
    tx.run("""
    CALL gds.graph.exists('userGraph') YIELD exists
    WITH exists
    CALL apoc.do.when(
        exists,
        'CALL gds.graph.drop("userGraph") YIELD graphName RETURN graphName',
        'RETURN "Kein Graph vorhanden" AS graphName',
        {}
    ) YIELD value RETURN value
    """)

    # Projektion mit sicherem Filter + toFloat-Konvertierung
    tx.run("""
    CALL gds.graph.project.cypher(
        'userGraph',
        '
        MATCH (u:User)
        WHERE u.cleanedFeature IS NOT NULL 
          AND size(u.cleanedFeature) > 0 
          AND NONE(x IN u.cleanedFeature WHERE x IS NULL)
        RETURN id(u) AS id, [x IN u.cleanedFeature | toFloat(x)] AS graphsageFeature
        ',
        'RETURN null AS source, null AS target'
    )
    """)


def run_knn(tx):
    print("🔍 Starte KNN...")
    result = tx.run("""
    CALL gds.knn.write('userGraph', {
      nodeProperties: ['graphsageFeature'],
      topK: 5,
      similarityCutoff: 0.8,
      writeRelationshipType: 'SIMILAR_TO',
      writeProperty: 'similarity'
    })
    YIELD nodesCompared, relationshipsWritten
    RETURN nodesCompared, relationshipsWritten
    """).single()

    print(f"✅ {result['relationshipsWritten']} Beziehungen geschrieben ({result['nodesCompared']} Knoten verglichen).")


def main():
    with driver.session() as session:
        print("🔍 Prüfe und setze fehlende age-Werte...")
        session.execute_write(check_and_fix_features)

        print("📦 Projiziere Graph für GraphSAGE...")
        session.execute_write(project_graphsage_graph)

        print("🧠 Berechne Embeddings mit GraphSAGE: Trainieren...")
        # Falls bereits existiert: CALL gds.beta.model.drop('my-sage-model') in neo4j Browser
        session.execute_write(run_graphsage_train)

        print("🧠 Berechne Embeddings mit GraphSAGE: Schreiben...")
        session.execute_write(run_graphsage_write)

        print("📦 Projiziere Graph für KNN...")
        session.execute_write(clean_embeddings_strict)
        session.execute_write(project_knn_graph)

        print("🔍 Führe KNN aus...")
        session.execute_write(run_knn)

        print("✅ Fertig: Embeddings & Similarity-Kanten erzeugt.")

if __name__ == "__main__":
    main()
