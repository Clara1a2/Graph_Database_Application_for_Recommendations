from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "SuperPasswort"
driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))


def recommend_books(user_id):
    query = """
    MATCH (target:User {id: $userId})
    MATCH (target)-[:SIMILAR_TO]->(sim:User)-[r:RATED]->(book:Book)
    WHERE NOT (target)-[:RATED]->(book)
    WITH book, avg(r.rating) AS avgRating, count(*) AS votes
    ORDER BY avgRating DESC, votes DESC
    LIMIT 3
    RETURN book.title AS title, book.author AS author, avgRating, votes
    """
    with driver.session() as session:
        result = session.run(query, userId=user_id)
        return [record.data() for record in result]

def get_graph_data(user_id):
    query = """
    MATCH (target:User {id: $userId})

    // Bücher des Zielnutzers
    OPTIONAL MATCH (target)-[r1:RATED]->(b1:Book)

    // Ähnliche Nutzer über Embedding-KNN
    OPTIONAL MATCH (target)-[simRel:SIMILAR_TO]->(sim:User)

    // Bücher der ähnlichen Nutzer
    OPTIONAL MATCH (sim)-[r2:RATED]->(b2:Book)

    RETURN
        target AS u1,
        sim AS u2,
        b1 AS book1,
        r1.rating AS rating1,
        b2 AS book2,
        r2.rating AS rating2,
        simRel.similarity AS similarityScore
    """
    with driver.session() as session:
        return [record.data() for record in session.run(query, userId=user_id)]


def get_graph_data_a(user_id):
    query = """
    MATCH (target:User {id: $userId})-[:SIMILAR_TO]->(sim:User)
    OPTIONAL MATCH (sim)-[r:RATED]->(b:Book)
    RETURN target AS u1, sim AS u2, b, r.rating AS rating
    """
    with driver.session() as session:
        return [record.data() for record in session.run(query, userId=user_id)]