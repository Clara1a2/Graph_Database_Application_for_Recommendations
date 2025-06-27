import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from neo4j import GraphDatabase
import tempfile
import os
import time

# Connection configuration for Neo4j
URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "SuperPasswort"
driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))


def get_users_in_large_communities():
    """
    Retrieves all users who belong to a community with more than one member.
    :return: list[dict]: A list of dictionaries containing userId, location, age, and communityId.
    """
    query = """
            MATCH (u:User)
            WITH u.community AS communityId, COLLECT(u) AS users, COUNT(u) AS size
            WHERE size > 1
            UNWIND users AS user
            RETURN user.id AS userId, user.location AS location, user.age AS age, communityId
            ORDER BY communityId, userId
            """
    with driver.session() as session:
        result = session.run(query)
        return [record.data() for record in result]


def get_user_rated_books(user_id):
    """
    Retrieves all books rated by a specific user, including title, author, and rating.
    :param user_id (str): The ID of the user.
    :return: list[dict]: A list of rated books with title, author, and rating.
    """
    query = """
            MATCH (u:User {id: $userId})-[r:RATED]->(b:Book)
            RETURN b.title AS title, b.author AS author, r.rating AS rating
            ORDER BY r.rating DESC
            """
    with driver.session() as session:
        result = session.run(query, userId=user_id)
        return [record.data() for record in result]


# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("Book Recommendation System")

# Load users and prepare selection options
users = get_users_in_large_communities()
user_options = {f"User {u['userId']} (Community {u['communityId']})": u for u in users}
selected = st.selectbox("Select a user:", options=list(user_options.keys()))
selected_user = user_options[selected]

# Display selected user information
st.subheader("👤 User Info")
st.write(f"**Location:** {selected_user['location']}")
st.write(f"**Age:** {selected_user['age']}")

# Show rated books
rated_books = get_user_rated_books(selected_user['userId'])
st.subheader("Books Rated by User")
st.table(pd.DataFrame(rated_books))

# Choose recommendation algorithm
algo = st.selectbox("Choose recommendation algorithm:", ["KNN", "Community"], index=0)

# Dynamically import the appropriate recommendation module
if algo == "Community":
    import recommender_community as rec
else:
    import recommender_knn as rec

# Run recommendation when button is clicked
if st.button("Recommend Books"):
    start_time = time.time() # Start timer

    # Get recommendations and similar users
    recs = rec.recommend_books(selected_user['userId'])
    sims = rec.get_similar_users(selected_user['userId'])

    end_time = time.time() # End timer
    duration = end_time - start_time

    # Display recommended books
    st.subheader("Top 3 Book Recommendations")
    st.table(pd.DataFrame(recs))

    # Display similar users
    st.subheader("Top 3 Similar Users")
    st.table(pd.DataFrame(sims))

    # Display graph visualization
    st.subheader("Graph Visualization")
    graph_data = rec.get_graph_data(selected_user['userId'])
    net = rec.build_graph(graph_data)

    # Create temporary HTML file for graph visualization
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        path = tmp_file.name
        net.show(path, notebook=False)
    with open(path, "r", encoding="utf-8") as f:
        html_content = f.read()
    components.html(html_content, height=700, scrolling=True)

    # Optional: Delete temp file after use
    # os.unlink(path)

    # Display execution time for the algorithm
    st.success(f"Execution time for '{algo}' recommendation: {duration:.2f} seconds")