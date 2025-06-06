from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "SuperPasswort"
driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))


def recommend_books(user_id):
    query = """
    MATCH (targetUser:User {id: $userId})
    WITH targetUser, targetUser.community AS communityId
    MATCH (otherUser:User {community: communityId})
    WHERE otherUser.id <> $userId
    MATCH (otherUser)-[r:RATED]->(b:Book)
    WHERE r.rating >= 6 AND NOT (targetUser)-[:RATED]->(b)
    RETURN b.title AS title, b.author AS author, COUNT(*) AS recommendCount
    ORDER BY recommendCount DESC
    LIMIT 3
    """
    with driver.session() as session:
        result = session.run(query, userId=user_id)
        return [record.data() for record in result]


def get_graph_data(user_id):
    query = """
    MATCH (target:User {id: $userId})
    WITH target, target.community AS communityId
    MATCH (u:User {community: communityId})-[r:RATED]->(b:Book)
    RETURN u, b, r.rating AS rating
    """
    with driver.session() as session:
        return [record.data() for record in session.run(query, userId=user_id)]