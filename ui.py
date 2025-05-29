import streamlit as st
import pandas as pd
from pyvis.network import Network
import streamlit.components.v1 as components
from neo4j import GraphDatabase
import tempfile
import os

# --- Neo4j Connection Setup ---
URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "BDA123B00k!"
driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))


# --- Query Helpers ---
def get_users_in_large_communities():
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
    query = """
    MATCH (u:User {id: $userId})-[r:RATED]->(b:Book)
    RETURN b.title AS title, b.author AS author, r.rating AS rating
    ORDER BY r.rating DESC
    """
    with driver.session() as session:
        result = session.run(query, userId=user_id)
        return [record.data() for record in result]


def get_recommendations(user_id, algorithm):
    if algorithm == "Community":
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
    else:  # KNN (dummy logic placeholder)
        query = """
        MATCH (u:User {id: $userId})-[:RATED]->(b:Book)<-[:RATED]-(other:User)
        WITH other, COUNT(*) AS common
        ORDER BY common DESC
        LIMIT 10
        MATCH (other)-[r:RATED]->(rec:Book)
        WHERE NOT (u)-[:RATED]->(rec) AND r.rating >= 6
        RETURN rec.title AS title, rec.author AS author, COUNT(*) AS recommendCount
        ORDER BY recommendCount DESC
        LIMIT 3
        """
    with driver.session() as session:
        result = session.run(query, userId=user_id)
        return [record.data() for record in result]


def get_similar_users(user_id):
    query = """
    MATCH (u1:User {id: $userId})-[:RATED]->(b:Book)<-[:RATED]-(u2:User)
    WHERE u1.id <> u2.id
    WITH u2, COUNT(*) AS similarity
    ORDER BY similarity DESC
    RETURN u2.id AS userId, u2.location AS location, u2.age AS age
    LIMIT 3
    """
    with driver.session() as session:
        result = session.run(query, userId=user_id)
        return [record.data() for record in result]


def get_graph_data(user_id, algorithm):
    if algorithm == "Community":
        query = """
        MATCH (target:User {id: $userId})
        WITH target, target.community AS communityId
        MATCH (u:User {community: communityId})-[r:RATED]->(b:Book)
        RETURN u, b, r.rating AS rating
        """
    else:
        query = """
        MATCH (u1:User {id: $userId})-[:RATED]->(b:Book)<-[:RATED]-(u2:User)
        WHERE u1.id <> u2.id
        WITH u1, u2, b
        MATCH (u2)-[r:RATED]->(book:Book)
        RETURN u1 AS target, u2, book, r.rating AS rating
        """
    with driver.session() as session:
        return [record.data() for record in session.run(query, userId=user_id)]


def build_graph(user_id, graph_data):
    net = Network(height="600px", width="100%", notebook=False)
    net.barnes_hut()

    for record in graph_data:
        u = record.get("u") or record.get("u2")
        b = record.get("b") or record.get("book")
        rating = record["rating"]
        user_node = f"user_{u['id']}"
        book_node = b["isbn"]

        color = "red" if rating <= 4 else "yellow" if rating <= 7 else "green"
        net.add_node(user_node, label=f"User {u['id']}", shape="dot",
                     title=f"User-ID: {u['id']}\nLocation: {u.get('location', '')}\nAge: {u.get('age', '')}")
        net.add_node(book_node, label=b["title"], shape="box", color=color,
                     title=f"Title: {b['title']}\nAuthor: {b['author']}\nISBN: {b['isbn']}\nPublisher: {b.get('publisher', '')}\nYear: {b.get('year', '')}")
        net.add_edge(user_node, book_node, title=str(rating), value=rating)
    return net


# --- Streamlit App ---
st.set_page_config(layout="wide")
st.title("📚 Book Recommendation System")

users = get_users_in_large_communities()
user_options = {f"User {u['userId']} (Community {u['communityId']})": u for u in users}
selected = st.selectbox("Select a user:", options=list(user_options.keys()))
selected_user = user_options[selected]

st.subheader("👤 User Info")
st.write(f"**Location:** {selected_user['location']}")
st.write(f"**Age:** {selected_user['age']}")

rated_books = get_user_rated_books(selected_user['userId'])
st.subheader("📖 Books Rated by User")
st.table(pd.DataFrame(rated_books))

algo = st.selectbox("Choose recommendation algorithm:", ["KNN", "Community"], index=0)

if st.button("🚀 Recommend Books"):
    recs = get_recommendations(selected_user['userId'], algo)
    sims = get_similar_users(selected_user['userId'])
    st.subheader("📚 Top 3 Book Recommendations")
    st.table(pd.DataFrame(recs))

    st.subheader("👥 Top 3 Similar Users")
    st.table(pd.DataFrame(sims))

    st.subheader("🌐 Graph Visualization")
    graph_data = get_graph_data(selected_user['userId'], algo)
    net = build_graph(selected_user['userId'], graph_data)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        path = tmp_file.name
        net.show(path)
    with open(path, "r", encoding="utf-8") as f:
        html_content = f.read()
    components.html(html_content, height=700, scrolling=True)
    os.unlink(path)
