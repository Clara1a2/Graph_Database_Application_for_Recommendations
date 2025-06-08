from neo4j import GraphDatabase
from Graph_Database_Application_for_Recommendations.algorithm_knn.alg_knn_fastrp import create_projection_fastrp, run_fastrp
from Graph_Database_Application_for_Recommendations.algorithm_knn.alg_knn_graphsage import check_and_fix_features, project_graphsage_graph, run_graphsage_train, run_graphsage_write
from Graph_Database_Application_for_Recommendations.algorithm_knn.alg_knn_node2vec import create_projection_node2vec, run_node2vec

uri = "bolt://localhost:7687"
user = "neo4j"
password = "SuperPasswort"

driver = GraphDatabase.driver(uri, auth=(user, password))

embedding_dimension = 64

def delete_existing_graph(tx, name="userGraph"):
    tx.run(f"""
    CALL gds.graph.exists('{name}') YIELD exists
    WITH exists
    CALL apoc.do.when(
        exists,
        'CALL gds.graph.drop("{name}") YIELD graphName RETURN graphName',
        'RETURN "Graph was not present" AS graphName',
        {{}}
    ) YIELD value RETURN value.graphName;
    """)

def create_graph_with_dummy_relation(tx):
    tx.run(f"""
    CALL gds.graph.project(
        'userGraph',
        ['User'],
        {{
            DUMMY: {{
                type: 'DUMMY',
                orientation: 'UNDIRECTED'
            }}
        }},
        {{
            nodeProperties: ['embedding']
        }}
    );
    """)

def run_knn_write(tx, top_k=5, similarity_cutoff=0.8):
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

def get_similar_books(tx, user_id=8, limit=10):
    result = tx.run("""
    MATCH (target:User {id: $userId})
    MATCH (target)-[:SIMILAR_TO]->(sim:User)-[r:RATED]->(book:Book)
    WHERE NOT (target)-[:RATED]->(book)
    WITH book, avg(r.rating) AS avgRating, count(*) AS votes
    ORDER BY avgRating DESC, votes DESC
    LIMIT $limit
    RETURN book.title AS title, avgRating, votes;
    """, {"userId": user_id, "limit": limit})
    return result.data()

def check_embedding_lengths(tx, expected_len=embedding_dimension):
    result = tx.run(f"""
    MATCH (u:User)
    RETURN size(u.embedding) AS len, count(*) AS count
    ORDER BY len;
    """)
    return result.data()

def run_pipeline(algorithm="fastrp"):
    with driver.session() as session:
        if algorithm == "fastrp":
            ################# FastRP ###################
            print("Lösche vorherige GDS-Projektion...")
            session.execute_write(delete_existing_graph)
            print("Erstelle Projektion für FastRP...")
            session.execute_write(create_projection_fastrp)
            print("Generiere FastRP Embeddings (dim=64)...")
            session.execute_write(run_fastrp, dim=64)

        if algorithm == "graphsage":
            ################# GraphSAGE ###################
            print("Prüfe und setze fehlende age-Werte...")
            session.execute_write(check_and_fix_features)
            print("Projiziere Graph für GraphSAGE...")
            session.execute_write(project_graphsage_graph)
            print("Berechne Embeddings mit GraphSAGE: Trainieren...")
            # Falls bereits existiert: CALL gds.beta.model.drop('my-sage-model') in neo4j Browser
            session.execute_write(run_graphsage_train)
            print("Berechne Embeddings mit GraphSAGE: Schreiben...")
            session.execute_write(run_graphsage_write)

        if algorithm == "node2vec":
            ################# Node2Vec ###################
            print("Lösche vorherige GDS-Projektion...")
            session.execute_write(delete_existing_graph)
            print("Erstelle Projektion für Node2Vec...")
            session.execute_write(create_projection_node2vec)
            print("Generiere Node2Vec Embeddings...")
            session.execute_write(run_node2vec, dim=64)

        print("Überprüfe Länge der Embeddings:")
        stats = session.execute_read(check_embedding_lengths)
        for row in stats:
            print(f"   ➤ Länge: {row['len']} → {row['count']} Nutzer")
        print("\nLösche alten GDS-Graphen:")
        session.execute_write(delete_existing_graph)
        print("Projiziere User-Graph mit Dummy-Relation und Embeddings:")
        session.execute_write(create_graph_with_dummy_relation)
        print("Führe KNN aus (topK=20, cutoff=0.8):")
        session.execute_write(run_knn_write, top_k=20)

        print("Empfohlene Bücher für Nutzer 19:")
        books = session.execute_read(get_similar_books, user_id=19) # 11676
        for book in books:
            print(f"   ➤ {book['title']} ({book['avgRating']:.2f}, {book['votes']} Stimmen)")

    driver.close()

if __name__ == "__main__":
    run_pipeline("graphsage")
    # run_pipeline("fastrp")
    # run_pipeline("node2vec") # <-- zu hoher Arbeitsspeicher-Nutzung

# Eine Dummy-Beziehung vorab einfügen:
# MATCH (a:User), (b:User)
# WHERE a <> b
# WITH a, b LIMIT 1
# MERGE (a)-[:DUMMY]->(b);

# Falls my-sage-model bereits existiert:
# CALL gds.beta.model.drop('my-sage-model')
