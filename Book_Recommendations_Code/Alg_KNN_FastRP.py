from neo4j import GraphDatabase

# Neo4j connection settings
uri = "bolt://localhost:7687"
user = "neo4j"
password = "SuperPasswort"
driver = GraphDatabase.driver(uri, auth=(user, password))


def delete_existing_graph(tx, name="userGraph"):
    """
    Deletes an existing GDS (Graph Data Science) projection if it exists.
    :param tx: Neo4j transaction
    :param name (str): Name of the graph projection to delete
    """
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


def create_projection_fastrp(tx, name="userGraph"):
    """
    Projects a graph with 'User' and 'Book' nodes and 'RATED' relationships
    for FastRP embedding calculation.
    :param tx: Neo4j transaction
    :param name (str): Name for the graph projection
    :return: list[dict]: Metadata about the projected graph
    """
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


def run_fastrp(tx, name="userGraph", dim=64):
    """
    Calculates FastRP embeddings on the projected graph and writes them to the nodes.
    :param tx: Neo4j transaction
    :param name (str): Name of the graph
    :param dim (int): Embedding dimension
    :return: list[dict]: Number of node properties written
    """
    # calculate and create the embeddings
    query = f"""
    CALL gds.fastRP.write('{name}', {{
      writeProperty: 'embedding',
      embeddingDimension: {dim},
      relationshipWeightProperty: 'rating'
    }})
    YIELD nodePropertiesWritten;
    """
    return tx.run(query).data()


def create_graph_with_dummy_relation(tx):
    """
    Creates a user-only graph projection with dummy relationships,
    enabling KNN comparison based on embeddings.
    :param tx: Neo4j transaction
    """
    # project a new graph
    # create dummy relations between the users
    # add the embeddings
    # we need relations between the users to compare them
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
    """
    Performs k-Nearest Neighbors on the user graph using embeddings.
    Writes 'SIMILAR_TO' relationships between users.
    :param tx: Neo4j transaction
    :param top_k (int): Number of nearest neighbors
    :param similarity_cutoff (float): Minimum similarity threshold
    """
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
    """
    Recommends books rated by similar users that the target user hasn't read yet.
    :param tx: Neo4j transaction
    :param user_id (int): Target user ID
    :param limit (int): Maximum number of book recommendations
    :return: list[dict]: Recommended books with average rating and vote count
    """
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


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    with driver.session() as session:
        print("Removing existing GDS projection if present...")
        session.execute_write(delete_existing_graph)

        print("Creating FastRP projection...")
        session.execute_write(create_projection_fastrp)

        print("Generating FastRP embeddings...")
        session.execute_write(run_fastrp)

        print("\nCleaning up old GDS graph...")
        session.execute_write(delete_existing_graph)

        print("Projecting user-only graph with dummy relationships and embeddings...")
        session.execute_write(create_graph_with_dummy_relation)

        print("Running KNN algorithm (topK=20, cutoff=0.8)...")
        session.execute_write(run_knn_write, top_k=20)

        print("Recommended books for user 19:")
        books = session.execute_read(get_similar_books, user_id=19) # 11676
        for book in books:
            print(f"   ➤ {book['title']} ({book['avgRating']:.2f}, {book['votes']} votes)")
    driver.close()