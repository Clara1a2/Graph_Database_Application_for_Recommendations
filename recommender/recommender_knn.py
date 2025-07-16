from neo4j import GraphDatabase
from pyvis.network import Network

# Neo4j connection setup
URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "SuperPasswort"
driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))


def recommend_books(user_id):
    """
    Recommends books for a given user based on books rated by similar users.
    :param user_id (str): ID of the target user.
    :return: list[dict]: A list of up to 3 recommended books with average rating and number of votes.
    """
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


def get_similar_users(user_id):
    """
    Retrieves up to 3 users who are most similar to the given user.
    :param user_id (str): ID of the target user.
    :return: list[dict]: List of similar users with their IDs, location, and age.
    """
    query = """
            MATCH (u1:User {id: $userId})-[:SIMILAR_TO]->(u2:User)
            WHERE u1.id <> u2.id
            RETURN DISTINCT u2.id AS userId, u2.location AS location, u2.age AS age
            LIMIT 3
            """
    with driver.session() as session:
        result = session.run(query, userId=user_id)
        return [record.data() for record in result]


def get_graph_data(user_id):
    """
    Retrieves graph data for visualization, including:
    - target user
    - similar users
    - books rated by each
    :param user_id (str): ID of the target user.
    :return: list[dict]: Query results containing users, books, ratings, and similarity scores.
    """
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


def build_graph(graph_data):
    """
    Builds an interactive Pyvis network visualization of the user and their similar users,
    including the books they have rated.

    - Users are shown as circular nodes.
    - Books are shown as box-shaped nodes.
    - Node color reflects rating (red = low, yellow = medium, green = high).
    - Edges indicate rating relationships, with similarity values or ratings as tooltips.
    :param graph_data (list[dict]): The data used to construct the graph.
    :return: pyvis.Network: A Pyvis Network object ready to be rendered.
    """
    net = Network(height="600px", width="100%", notebook=False)
    net.barnes_hut()

    for record in graph_data:
        target = record.get("u1")
        sim_user = record.get("u2")
        book_self = record.get("book1")
        book_sim = record.get("book2")

        # Target user node
        if target:
            target_node = f"user_{target['id']}"
            net.add_node(
                target_node,
                label=f"User {target['id']}",
                shape="dot",
                title=f"User-ID: {target['id']}\nLocation: {target.get('location', '')}\nAge: {target.get('age', '')}"
            )

        # Similar user node
        if sim_user:
            sim_node = f"user_{sim_user['id']}"
            net.add_node(
                sim_node,
                label=f"User {sim_user['id']}",
                shape="dot",
                title=f"User-ID: {sim_user['id']}\nLocation: {sim_user.get('location', '')}\nAge: {sim_user.get('age', '')}"
            )

            # Edge: target user ↔ similar user
            if target:
                similarity = record.get("similarityScore", 0.0)
                scaled_sim = 1 + similarity * 9  # Scale to 1-10 for consistent edge thickness (like rating)
                net.add_edge(target_node, sim_node, title=f"similarity: {similarity:.2f}", value=scaled_sim)
                # The 'value' parameter affects how the edge is rendered in the Pyvis graph.
                # Higher value = thicker edge, lower value = thinner edge.

        # Book rated by the target user
        if book_self and target:
            book_node = book_self["isbn"]
            rating = record.get("rating1", 0)
            color = "red" if rating <= 4 else "yellow" if rating <= 7 else "green"
            net.add_node(
                book_node,
                label=book_self["title"],
                shape="box",
                color=color,
                title=f"Title: {book_self['title']}\nAuthor: {book_self['author']}\nISBN: {book_self['isbn']}\nPublisher: {book_self.get('publisher', '')}\nYear: {book_self.get('year', '')}"
            )
            net.add_edge(target_node, book_node, title=str(rating), value=rating)

        # Book rated by a similar user
        if book_sim and sim_user:
            book_node = book_sim["isbn"]
            rating = record.get("rating2", 0)
            color = "red" if rating <= 4 else "yellow" if rating <= 7 else "green"
            net.add_node(
                book_node,
                label=book_sim["title"],
                shape="box",
                color=color,
                title=f"Title: {book_sim['title']}\nAuthor: {book_sim['author']}\nISBN: {book_sim['isbn']}\nPublisher: {book_sim.get('publisher', '')}\nYear: {book_sim.get('year', '')}"
            )
            sim_node = f"user_{sim_user['id']}"
            net.add_edge(sim_node, book_node, title=str(rating), value=rating)
    return net