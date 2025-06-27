import pandas as pd
from neo4j import GraphDatabase

# --- Load filtered datasets ---
users_df = pd.read_csv("filtered_users.csv", sep=",", encoding="latin-1").fillna("")
books_df = pd.read_csv("filtered_books.csv", sep=",", encoding="latin-1", low_memory=False).fillna("")
ratings_df = pd.read_csv("filtered_ratings.csv", sep=",", encoding="latin-1").fillna("")


# --- Neo4j connection settings ---
URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "SuperPasswort"


# --- BATCH LOADER FUNCTIONS ---
def load_users(tx, batch):
    """
    Inserts or updates users in the Neo4j graph in batch mode.
    :param tx: Neo4j transaction
    :param batch (list[dict]): Batch of user data
    """
    query = """
            UNWIND $rows AS row
            MERGE (u:User {id: toInteger(row.`User-ID`)})
            SET u.location = row.Location, u.age = CASE row.Age WHEN '' THEN NULL ELSE toInteger(row.Age) END
            """
    tx.run(query, rows=batch)


def load_books(tx, batch):
    """
    Inserts or updates books in the Neo4j graph in batch mode.
    :param tx: Neo4j transaction
    :param batch (list[dict]): Batch of book data
    """
    query = """
            UNWIND $rows AS row
            MERGE (b:Book {isbn: row.ISBN})
            SET b.title = row.`Book-Title`,
                b.author = row.`Book-Author`,
                b.year = toInteger(row.`Year-Of-Publication`),
                b.publisher = row.Publisher
            """
    tx.run(query, rows=batch)


def load_ratings(tx, batch):
    """
    Creates relationships between users and books based on ratings.
    :param tx: Neo4j transaction
    :param batch (list[dict]): Batch of rating data
    """
    query = """
            UNWIND $rows AS row
            MATCH (u:User {id: toInteger(row.`User-ID`)})
            MATCH (b:Book {isbn: row.ISBN})
            MERGE (u)-[r:RATED]->(b)
            SET r.rating = toInteger(row.`Book-Rating`)
            """
    tx.run(query, rows=batch)


# --- CHUNKING FUNCTION ---
def chunk_dataframe(df, size=100):
    """
    Splits a DataFrame into chunks of given size for batch processing.
    :param df (pd.DataFrame): DataFrame to split
    :param size (int): Chunk size
    :Yields: list[dict]: Chunk of records as list of dicts
    """
    for i in range(0, len(df), size):
        yield df.iloc[i:i + size].to_dict("records")


# --- DATA UPLOAD ---
with GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD)) as driver:
    with driver.session() as session:
        print("✅ Connected to Neo4j.")

        for user_batch in chunk_dataframe(users_df):
            session.execute_write(load_users, user_batch)
        print("✅ Users uploaded.")

        for book_batch in chunk_dataframe(books_df):
            session.execute_write(load_books, book_batch)
        print("✅ Books uploaded.")

        for rating_batch in chunk_dataframe(ratings_df):
            session.execute_write(load_ratings, rating_batch)
        print("✅ Ratings uploaded.")


# --- OPTIONAL: Initial Graph Setup ---
def create_graph(tx):
    """
    Creates unique constraints on User and Book nodes.
    Ensures no duplicate users or books in the graph.
    """
    tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
    tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (b:Book) REQUIRE b.isbn IS UNIQUE")


def load_data(tx, users, books, ratings):
    """
    Load data into the graph.
    :param tx: Neo4j transaction
    :param users (pd.DataFrame)
    :param books (pd.DataFrame)
    :param ratings (pd.DataFrame)
    """
    for _, row in users.iterrows():
        tx.run("MERGE (u:User {id: $id, location: $location})", id=row['User-ID'], location=row['Location'])
    for _, row in books.iterrows():
        tx.run("MERGE (b:Book {isbn: $isbn, title: $title})", isbn=row['ISBN'], title=row['Book-Title'])
    for _, row in ratings.iterrows():
        tx.run("""
            MATCH (u:User {id: $user_id}), (b:Book {isbn: $isbn})
            MERGE (u)-[:RATED {rating: $rating}]->(b)
        """, user_id=row['User-ID'], isbn=row['ISBN'], rating=row['Book-Rating'])


# --- OPTIONAL: Manual execution of initial setup ---
# with driver.session() as session:
#     session.execute_write(create_graph)
#     session.execute_write(load_data, users_df, books_df, ratings_df)


# --- ARCHIVED / UNUSED CODE ---
# Filter unnecessary data
# ratings_df = ratings_df[ratings_df['Book-Rating'] > 0]

# with GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD)) as driver:
#     driver.verify_connectivity()

# driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD),
#                               connection_timeout=60,
#                               max_connection_lifetime=300,)


# def test_connection():
#     with driver.session() as session:
#         result = session.run("RETURN 'Aura connection successful!' AS message")
#         print(result.single()["message"])
#
# test_connection()