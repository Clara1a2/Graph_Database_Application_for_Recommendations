import pandas as pd
from neo4j import GraphDatabase

# Load the datasets
# books_df = pd.read_csv("Books.csv", encoding='ISO-8859-1')
# ratings_df = pd.read_csv("Ratings.csv", encoding='ISO-8859-1')
# users_df = pd.read_csv("Users.csv", encoding='ISO-8859-1')
users_df = pd.read_csv("Users.csv", sep=",", encoding="latin-1").fillna("")
books_df = pd.read_csv("Books.csv", sep=",", encoding="latin-1", low_memory=False).fillna("")
ratings_df = pd.read_csv("filtered_ratings.csv", sep=",", encoding="latin-1").fillna("")

# pip install neo4j
# URI = "neo4j+ssc://b46b0418.databases.neo4j.io"  # cloud-based, no local host
URI = "bolt://127.0.0.1:7687" # local host bolt://localhost:7687
USERNAME = "neo4j"
PASSWORD = "BDA123B00k!"


# ---- BATCH LOADER FUNCTION ----
def load_users(tx, batch):
    query = """
    UNWIND $rows AS row
    MERGE (u:User {id: toInteger(row.`User-ID`)})
    SET u.location = row.Location, u.age = CASE row.Age WHEN '' THEN NULL ELSE toInteger(row.Age) END
    """
    tx.run(query, rows=batch)


def load_books(tx, batch):
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
    query = """
    UNWIND $rows AS row
    MATCH (u:User {id: toInteger(row.`User-ID`)})
    MATCH (b:Book {isbn: row.ISBN})
    MERGE (u)-[r:RATED]->(b)
    SET r.rating = toInteger(row.`Book-Rating`)
    """
    tx.run(query, rows=batch)


# ---- CHUNKING FUNCTION ----
def chunk_dataframe(df, size=100):
    for i in range(0, len(df), size):
        yield df.iloc[i:i + size].to_dict("records")


# ---- RUN THE UPLOAD ----
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

def create_graph(tx):
    tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
    tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (b:Book) REQUIRE b.isbn IS UNIQUE")


# Load data into the graph
def load_data(tx, users, books, ratings):
    for _, row in users.iterrows():
        tx.run("MERGE (u:User {id: $id, location: $location})", id=row['User-ID'], location=row['Location'])
    for _, row in books.iterrows():
        tx.run("MERGE (b:Book {isbn: $isbn, title: $title})", isbn=row['ISBN'], title=row['Book-Title'])
    for _, row in ratings.iterrows():
        tx.run("""
            MATCH (u:User {id: $user_id}), (b:Book {isbn: $isbn})
            MERGE (u)-[:RATED {rating: $rating}]->(b)
        """, user_id=row['User-ID'], isbn=row['ISBN'], rating=row['Book-Rating'])

# with driver.session() as session:
#     session.execute_write(create_graph)
#     session.execute_write(load_data, users_df, books_df, ratings_df)
