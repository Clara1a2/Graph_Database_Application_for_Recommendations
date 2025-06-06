# Beispielproblem:
# Zwei Nutzer haben dieselben Bücher bewertet – aber einer gibt immer 5 Sterne,
# der andere 1 Stern → FastRP behandelt sie trotzdem als ähnlich.

# Ziel: Du möchtest für jeden User ähnlich bewertende User vorschlagen

##################### Version 3: mit FastRP #####################
from neo4j import GraphDatabase

uri = "bolt://localhost:7687"
user = "neo4j"
password = "SuperPasswort"  # Anpassen

driver = GraphDatabase.driver(uri, auth=(user, password))

# -------------------------
# 1. GRAPH SETUP
# -------------------------

def delete_existing_graph_2(tx, name="userGraph"):
    query = f"""
    CALL gds.graph.exists('{name}') YIELD exists
    WITH exists
    CALL apoc.do.when(
      exists,
      'CALL gds.graph.drop("{name}") YIELD graphName RETURN graphName',
      'RETURN "Graph was not present" AS graphName',
      {{}}
    ) YIELD value
    RETURN value.graphName;
    """
    return tx.run(query).data()

def create_projection_fastrp(tx, name="userGraph"):
    query = f"""
    CALL gds.graph.project(
      '{name}',
      ['User', 'Book'],
      {{
        RATED: {{
          type: 'RATED',
          orientation: 'UNDIRECTED',
          properties: ['rating']
        }}
      }}
    )
    YIELD graphName, nodeCount, relationshipCount;
    """
    return tx.run(query).data()

# -------------------------
# 2. FASTRP EMBEDDINGS
# -------------------------

def run_fastrp(tx, name="userGraph", dim=64):
    query = f"""
    CALL gds.fastRP.write('{name}', {{
      writeProperty: 'embedding',
      embeddingDimension: {dim},
      relationshipWeightProperty: 'rating'
    }})
    YIELD nodePropertiesWritten;
    """
    return tx.run(query).data()

# -------------------------
# 3. KNN AUSFÜHREN
# -------------------------

def run_knn_write(tx, name="userGraph", top_k=5, similarity_cutoff=None):
    if similarity_cutoff:
        query = f"""
        CALL gds.knn.write('{name}', {{
          nodeProperties: ['embedding'],
          topK: $topK,
          similarityCutoff: $cutoff,
          writeRelationshipType: 'SIMILAR_TO',
          writeProperty: 'similarity'
        }})
        YIELD nodesCompared, relationshipsWritten;
        """
        return tx.run(query, {"topK": top_k, "cutoff": similarity_cutoff}).data()
    else:
        query = f"""
        CALL gds.knn.write('{name}', {{
          nodeProperties: ['embedding'],
          topK: $topK,
          writeRelationshipType: 'SIMILAR_TO',
          writeProperty: 'similarity'
        }})
        YIELD nodesCompared, relationshipsWritten;
        """
        return tx.run(query, {"topK": top_k}).data()

# -------------------------
# 4. EMPFEHLUNG
# -------------------------

def get_recommended_books(tx, user_id=8, limit=10):
    query = """
    MATCH (target:User {id: $userId})
    MATCH (target)-[:SIMILAR_TO]->(sim:User)-[r:RATED]->(book:Book)
    WHERE NOT (target)-[:RATED]->(book)
    WITH book, avg(r.rating) AS avgRating, count(*) AS votes
    ORDER BY avgRating DESC, votes DESC
    LIMIT $limit
    RETURN book.title AS title, avgRating, votes;
    """
    return tx.run(query, {"userId": user_id, "limit": limit}).data()

# -------------------------
# 5. EVALUATION
# -------------------------

def evaluate_recommendations(tx, user_id=8, limit=10):
    recommendations = get_recommended_books(tx, user_id, limit)
    query = """
    MATCH (u:User {id: $userId})-[:RATED]->(b:Book)
    RETURN collect(b.title) AS groundTruth;
    """
    ground_truth = tx.run(query, {"userId": user_id}).single()["groundTruth"]
    recommended_titles = [rec["title"] for rec in recommendations]

    true_positives = set(recommended_titles) & set(ground_truth)
    precision = len(true_positives) / len(recommended_titles) if recommended_titles else 0
    recall = len(true_positives) / len(ground_truth) if ground_truth else 0

    return {
        "precision": precision,
        "recall": recall,
        "true_positives": list(true_positives)
    }

# -------------------------
# 6. AUSFÜHRUNGSSCHRITT
# -------------------------

def run_full_pipeline():
    with driver.session() as session:
        print("🚮 Lösche vorherige GDS-Projektion...")
        session.execute_write(delete_existing_graph_2)

        print("🧱 Erstelle Projektion für FastRP...")
        session.execute_write(create_projection_fastrp)

        print("🧠 Generiere FastRP Embeddings (dim=64)...")
        session.execute_write(run_fastrp, dim=64)

        print("📦 Neu-Projektion nur für Embedding-basierte KNN-Berechnung...")
        session.execute_write(delete_existing_graph)
        session.execute_write(lambda tx: tx.run("""
            CALL gds.graph.project.cypher(
              'userGraph',
              '
                MATCH (u:User)
                RETURN id(u) AS id,
                       coalesce([x IN u.embedding | coalesce(toFloat(x), 0.0)], [0.0, 0.0, 0.0, 0.0]) AS embedding
              ',
              'RETURN NULL AS source, NULL AS target',
              { validateRelationships: false }
            );
        """))

        print("🔍 Starte KNN mit Parametern: topK=10, cutoff=0.75")
        session.execute_write(run_knn_write, top_k=10, similarity_cutoff=0.75)

        print("📚 Empfohlene Bücher für User 8:")
        books = session.execute_read(get_recommended_books, user_id=8)
        for book in books:
            print("   ➤", book)

        print("📊 Evaluation:")
        eval_result = session.execute_read(evaluate_recommendations, user_id=8)
        print("   ➤ Precision:", eval_result["precision"])
        print("   ➤ Recall:   ", eval_result["recall"])
        print("   ➤ Treffer: ", eval_result["true_positives"])

    driver.close()

if __name__ == "__main__":
    run_full_pipeline()


###################### Version 2: mit Node2Vec #######################################
# from neo4j import GraphDatabase
#
# uri = "bolt://localhost:7687"
# user = "neo4j"
# password = "SuperPasswort"  # Anpassen
#
# driver = GraphDatabase.driver(uri, auth=(user, password))
#
# # -------------------------
# # 1. GRAPH SETUP
# # -------------------------
#
# def delete_existing_graph(tx, name="userGraph"):
#     query = f"""
#     CALL gds.graph.exists('{name}') YIELD exists
#     WITH exists
#     CALL apoc.do.when(
#       exists,
#       'CALL gds.graph.drop("{name}") YIELD graphName RETURN graphName',
#       'RETURN "Graph was not present" AS graphName',
#       {{}}
#     ) YIELD value
#     RETURN value.graphName;
#     """
#     return tx.run(query).data()
#
# def create_projection_node2vec(tx, name="userGraph"):
#     query = f"""
#     CALL gds.graph.project(
#       '{name}',
#       ['User', 'Book'],
#       {{
#         RATED: {{
#           type: 'RATED',
#           orientation: 'UNDIRECTED',
#           properties: ['rating']
#         }}
#       }}
#     )
#     YIELD graphName, nodeCount, relationshipCount;
#     """
#     return tx.run(query).data()
#
# # -------------------------
# # 2. NODE2VEC EMBEDDINGS
# # -------------------------
#
# def run_node2vec(tx, name="userGraph", dim=128, embedding_property="embedding"):
#     query = f"""
#     CALL gds.node2vec.write('{name}', {{
#       writeProperty: '{embedding_property}',
#       embeddingDimension: {dim},
#       relationshipWeightProperty: 'rating'
#     }})
#     YIELD nodePropertiesWritten;
#     """
#     return tx.run(query).data()
#
# # -------------------------
# # 3. KNN AUSFÜHREN
# # -------------------------
#
# def run_knn_write(tx, name="userGraph", top_k=5, similarity_cutoff=None):
#     if similarity_cutoff:
#         query = f"""
#         CALL gds.knn.write('{name}', {{
#           nodeProperties: ['embedding'],
#           topK: $topK,
#           similarityCutoff: $cutoff,
#           writeRelationshipType: 'SIMILAR_TO',
#           writeProperty: 'similarity'
#         }})
#         YIELD nodesCompared, relationshipsWritten;
#         """
#         return tx.run(query, {"topK": top_k, "cutoff": similarity_cutoff}).data()
#     else:
#         query = f"""
#         CALL gds.knn.write('{name}', {{
#           nodeProperties: ['embedding'],
#           topK: $topK,
#           writeRelationshipType: 'SIMILAR_TO',
#           writeProperty: 'similarity'
#         }})
#         YIELD nodesCompared, relationshipsWritten;
#         """
#         return tx.run(query, {"topK": top_k}).data()
#
# # -------------------------
# # 4. EMPFEHLUNG
# # -------------------------
#
# def get_recommended_books(tx, user_id=8, limit=10):
#     query = """
#     MATCH (target:User {id: $userId})
#     MATCH (target)-[:SIMILAR_TO]->(sim:User)-[r:RATED]->(book:Book)
#     WHERE NOT (target)-[:RATED]->(book)
#     WITH book, avg(r.rating) AS avgRating, count(*) AS votes
#     ORDER BY avgRating DESC, votes DESC
#     LIMIT $limit
#     RETURN book.title AS title, avgRating, votes;
#     """
#     return tx.run(query, {"userId": user_id, "limit": limit}).data()
#
# # -------------------------
# # 5. EVALUATION
# # -------------------------
#
# def evaluate_recommendations(tx, user_id=8, limit=10):
#     recommendations = get_recommended_books(tx, user_id, limit)
#     query = """
#     MATCH (u:User {id: $userId})-[:RATED]->(b:Book)
#     RETURN collect(b.title) AS groundTruth;
#     """
#     ground_truth = tx.run(query, {"userId": user_id}).single()["groundTruth"]
#     recommended_titles = [rec["title"] for rec in recommendations]
#
#     true_positives = set(recommended_titles) & set(ground_truth)
#     precision = len(true_positives) / len(recommended_titles) if recommended_titles else 0
#     recall = len(true_positives) / len(ground_truth) if ground_truth else 0
#
#     return {
#         "precision": precision,
#         "recall": recall,
#         "true_positives": list(true_positives)
#     }
#
# # -------------------------
# # 6. AUSFÜHRUNGSSCHRITT
# # -------------------------
#
# def run_full_pipeline():
#     with driver.session() as session:
#         print("🚮 Lösche vorherige GDS-Projektion...")
#         session.write_transaction(delete_existing_graph)
#
#         print("🧱 Erstelle Projektion für Node2Vec...")
#         session.write_transaction(create_projection_node2vec)
#
#         print("🧠 Generiere Node2Vec Embeddings...")
#         session.write_transaction(run_node2vec, dim=64)
#
#         print("📦 Neu-Projektion nur für Embedding-basierte KNN-Berechnung...")
#         session.write_transaction(delete_existing_graph)
#         session.write_transaction(lambda tx: tx.run("""
#             CALL gds.graph.project(
#               'userGraph',
#               {
#                 User: {
#                   properties: ['embedding']
#                 }
#               },
#               {}
#             );
#         """))
#
#         print("🔍 Starte KNN mit Parametern: topK=10, cutoff=0.75")
#         session.write_transaction(run_knn_write, top_k=10, similarity_cutoff=0.75)
#
#         print("📚 Empfohlene Bücher für User 8:")
#         books = session.read_transaction(get_recommended_books, user_id=8)
#         for book in books:
#             print("   ➤", book)
#
#         print("📊 Evaluation:")
#         eval_result = session.read_transaction(evaluate_recommendations, user_id=8)
#         print("   ➤ Precision:", eval_result["precision"])
#         print("   ➤ Recall:   ", eval_result["recall"])
#         print("   ➤ Treffer: ", eval_result["true_positives"])
#
#     driver.close()
#
# if __name__ == "__main__":
#     run_full_pipeline()
#


################################### Version 1 (ohne Berechnung von Embedding) ###########
# from neo4j import GraphDatabase
#
# uri = "bolt://localhost:7687"  # Anpassen
# user = "neo4j"
# password = "SuperPasswort"     # Anpassen
#
# driver = GraphDatabase.driver(uri, auth=(user, password))
#
# def run_query(tx, query, parameters=None):
#     return list(tx.run(query, parameters or {}))
#
# with driver.session() as session:
#     # 1. Lösche bestehenden GDS-Graphen
#     session.run("""
#     CALL gds.graph.exists('userGraph') YIELD exists
#     WITH exists
#     CALL apoc.do.when(
#       exists,
#       'CALL gds.graph.drop("userGraph") YIELD graphName RETURN graphName',
#       'RETURN "Graph was not present" AS graphName',
#       {}
#     ) YIELD value
#     RETURN value.graphName;
#     """)
#
#     # 2. GDS-Projektion erstellen
#     session.run("""
#     CALL gds.graph.project(
#       'userGraph',
#       {
#         User: {
#           properties: ['embedding']
#         }
#       },
#       {}
#     );
#     """)
#
#     # 3. KNN schreiben (ohne Threshold)
#     session.run("""
#     CALL gds.knn.write('userGraph', {
#       nodeProperties: ['embedding'],
#       topK: 5,
#       writeRelationshipType: 'SIMILAR_TO',
#       writeProperty: 'similarity'
#     })
#     YIELD nodesCompared, relationshipsWritten;
#     """)
#
#     # Optional: Alternative mit Threshold
#     session.run("""
#     CALL gds.knn.write('userGraph', {
#       nodeProperties: ['embedding'],
#       topK: 5,
#       similarityCutoff: 0.8,
#       writeRelationshipType: 'SIMILAR_TO',
#       writeProperty: 'similarity'
#     })
#     YIELD nodesCompared, relationshipsWritten;
#     """)
#
#     # Ausgabe ähnlicher Bücher für Nutzer mit id=8
#     books = session.run("""
#     MATCH (target:User {id: 8})
#     MATCH (target)-[:SIMILAR_TO]->(sim:User)-[r:RATED]->(book:Book)
#     WHERE NOT (target)-[:RATED]->(book)
#     WITH book, avg(r.rating) AS avgRating, count(*) AS votes
#     ORDER BY avgRating DESC, votes DESC
#     LIMIT 10
#     RETURN book.title AS title, avgRating, votes;
#     """)
#     print("Ähnliche Bücher:")
#     for record in books:
#         print(record)
#
# driver.close()