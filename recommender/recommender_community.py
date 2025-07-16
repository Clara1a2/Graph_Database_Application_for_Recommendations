from neo4j import GraphDatabase
from pyvis.network import Network

# Neo4j connection setup
URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "SuperPasswort"
driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))


def recommend_books(user_id):
    """
    Recommends books based on the community of the given user.
    Books are selected from other users in the same community with a rating ≥ 6,
    excluding those the target user has already rated.
    :param user_id (str): ID of the target user.
    :return: list[dict]: Top 3 recommended books with title, author, and count of recommendations.
    """
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


def get_similar_users(user_id):
    """
    Retrieves users from the same community, excluding the target user.
    These are considered 'similar' based on shared community membership.
    :param user_id (str): ID of the target user.
    :return: list[dict]: Up to 3 users with their ID, location, and age.
    """
    query = """
            MATCH (u1:User {id: $userId})
            WITH u1.community AS communityId
            MATCH (u2:User {community: communityId})
            WHERE u2.id <> $userId
            WITH DISTINCT u2.id AS userId
            LIMIT 3
            MATCH (u:User {id: userId})
            RETURN u.id AS userId, u.location AS location, u.age AS age
            ORDER BY u.id
            """
    with driver.session() as session:
        result = session.run(query, userId=user_id)
        return [record.data() for record in result]


def get_graph_data(user_id):
    """
    Retrieves users and book-rating relationships within the same community
    as the target user, to be used for graph visualization.
    :param user_id (str): ID of the target user.
    :return: list[dict]: Each record contains a user, a book, and the rating given.
    """
    query = """
            MATCH (target:User {id: $userId})
            WITH target, target.community AS communityId
            MATCH (u:User {community: communityId})-[r:RATED]->(b:Book)
            RETURN u, b, r.rating AS rating
            """
    with driver.session() as session:
        return [record.data() for record in session.run(query, userId=user_id)]


def build_graph(graph_data):
    """
    Builds an interactive Pyvis network visualization showing:
    - Users as circle-shaped nodes
    - Books as box-shaped nodes
    - Colors indicating rating: red (low), yellow (medium), green (high)
    - Edges showing ratings between users and books
    :param graph_data (list[dict]): A list of user-book-rating records.
    :return: pyvis.Network: A ready-to-render network graph.
    """
    net = Network(height="600px", width="100%", notebook=False)
    net.barnes_hut()

    for record in graph_data:
        u = record.get("u") or record.get("u2")
        b = record.get("b") or record.get("book")

        # Skip if either user or book is missing
        if not u or not b:
            continue

        rating = record["rating"]
        user_node = f"user_{u['id']}"
        book_node = b["isbn"]

        # Set color based on rating
        color = "red" if rating <= 4 else "yellow" if rating <= 7 else "green"

        # Add user node (circle)
        net.add_node(user_node, label=f"User {u['id']}", shape="dot",
                     title=f"User-ID: {u['id']}\nLocation: {u.get('location', '')}\nAge: {u.get('age', '')}")

        # Add book node (box)
        net.add_node(book_node, label=b["title"], shape="box", color=color,
                     title=f"Title: {b['title']}\nAuthor: {b['author']}\nISBN: {b['isbn']}\nPublisher: {b.get('publisher', '')}\nYear: {b.get('year', '')}")

        # Add edge between user and book
        net.add_edge(user_node, book_node, title=str(rating), value=rating)
        # The 'value' parameter determines the thickness of the edge when rendered.
        # Higher value = thicker line, lower value = thinner line.
    return net