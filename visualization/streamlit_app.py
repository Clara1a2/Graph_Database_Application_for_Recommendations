import streamlit as st
import pandas as pd
from pyvis.network import Network
import streamlit.components.v1 as components
from neo4j import GraphDatabase
import tempfile
import os
import time

# Verbindung für allgemeine Queries
URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "SuperPasswort"
driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))


def get_users_in_large_communities():
    """
    Holt alle Nutzer, die in einer Community mit mehr als 1 Person sind.
    :return:
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
    Lädt alle Bücher, die ein bestimmter Nutzer bewertet hat – inklusive Bewertung, Autor, Titel.
    :param user_id:
    :return:
    """
    query = """
    MATCH (u:User {id: $userId})-[r:RATED]->(b:Book)
    RETURN b.title AS title, b.author AS author, r.rating AS rating
    ORDER BY r.rating DESC
    """
    with driver.session() as session:
        result = session.run(query, userId=user_id)
        return [record.data() for record in result]

def get_similar_users(user_id, algorithm):
    """
    Sucht andere Nutzer, die viele Bücher wie der aktuelle Nutzer bewertet haben (überlapptes Verhalten).
    :param user_id:
    :return:
    """
    if algorithm == "KNN":
        query = """
        MATCH (u1:User {id: $userId})-[:SIMILAR_TO]->(u2:User)
        WHERE u1.id <> u2.id
        RETURN DISTINCT u2.id AS userId, u2.location AS location, u2.age AS age
        LIMIT 3
        """
    elif algorithm == "Community":
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
    else:
        query = """
        MATCH (u1:User {id: $userId})-[:RATED]->(b:Book)<-[:RATED]-(u2:User)
        WHERE u1.id <> u2.id
        WITH u2, COUNT(*) AS similarity
        ORDER BY similarity DESC
        RETURN DISTINCT u2.id AS userId, u2.location AS location, u2.age AS age
        LIMIT 3
        """

    with driver.session() as session:
        result = session.run(query, userId=user_id)
        return [record.data() for record in result]

def build_graph(graph_data, algorithm):
    """
    Erstellt aus den übergebenen Daten eine interaktive Netzwerk-Visualisierung mit pyvis.
    Nutzerknoten = Punkte
    Bücherknoten = Boxen
    Farben = Bewertung (rot, gelb, grün)
    Kanten = Bewertung vom Nutzer zum Buch
    :param user_id:
    :param graph_data:
    :return:
    """
    # net.add_edge(target_node, sim_node, title=f"similarity: {similarity:.2f}", value=similarity)
    # Der value-Parameter steuert die Dicke (Stärke) der Kante.
    # Höherer Wert = dickerer Strich
    # Geringer Wert = dünnerer Strich

    if algorithm == "Community":
        net = Network(height="600px", width="100%", notebook=False)
        net.barnes_hut()
        for record in graph_data:
            u = record.get("u") or record.get("u2")
            b = record.get("b") or record.get("book")
            if not u or not b:
                continue
            rating = record["rating"]
            user_node = f"user_{u['id']}"
            book_node = b["isbn"]
            color = "red" if rating <= 4 else "yellow" if rating <= 7 else "green"
            net.add_node(user_node, label=f"User {u['id']}", shape="dot",
                         title=f"User-ID: {u['id']}\nLocation: {u.get('location', '')}\nAge: {u.get('age', '')}")
            net.add_node(book_node, label=b["title"], shape="box", color=color,
                         title=f"Title: {b['title']}\nAuthor: {b['author']}\nISBN: {b['isbn']}\nPublisher: {b.get('publisher', '')}\nYear: {b.get('year', '')}")
            net.add_edge(user_node, book_node, title=str(rating), value=rating)

    if algorithm == "KNN":
        net = Network(height="600px", width="100%", notebook=False)
        net.barnes_hut()

        for record in graph_data:
            target = record.get("u1")
            sim_user = record.get("u2")
            book_self = record.get("book1")
            book_sim = record.get("book2")

            # ➤ Zielnutzer-Knoten
            if target:
                target_node = f"user_{target['id']}"
                net.add_node(
                    target_node,
                    label=f"User {target['id']}",
                    shape="dot",
                    title=f"User-ID: {target['id']}\nLocation: {target.get('location', '')}\nAge: {target.get('age', '')}"
                )

            # ➤ Ähnlicher Nutzer-Knoten
            if sim_user:
                sim_node = f"user_{sim_user['id']}"
                net.add_node(
                    sim_node,
                    label=f"User {sim_user['id']}",
                    shape="dot",
                    title=f"User-ID: {sim_user['id']}\nLocation: {sim_user.get('location', '')}\nAge: {sim_user.get('age', '')}"
                )

                # ➤ Kante: Nutzer ↔ Ähnlicher Nutzer
                if target:
                    similarity = record.get("similarityScore", 0.0)
                    scaled_sim = 1 + similarity * 9  # Skalierung, sodass hier die similarity zwischen 1 und 10 liegen, wie bei ratings (einheitliche Visualisierung)

                    net.add_edge(target_node, sim_node, title=f"similarity: {similarity:.2f}", value=scaled_sim)

            # ➤ Buch, das der Nutzer selbst bewertet hat
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

            # ➤ Buch, das der ähnliche Nutzer bewertet hat
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


# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("Book Recommendation System")

users = get_users_in_large_communities()
user_options = {f"User {u['userId']} (Community {u['communityId']})": u for u in users}
selected = st.selectbox("Select a user:", options=list(user_options.keys()))
selected_user = user_options[selected]

st.subheader("👤 User Info")
st.write(f"**Location:** {selected_user['location']}")
st.write(f"**Age:** {selected_user['age']}")

rated_books = get_user_rated_books(selected_user['userId'])
st.subheader("Books Rated by User")
st.table(pd.DataFrame(rated_books))

algo = st.selectbox("Choose recommendation algorithm:", ["KNN", "Community"], index=0)

# Dynamischer Modulimport
if algo == "Community":
    import recommender_community as rec
else:
    import recommender_knn as rec

if st.button("Recommend Books"):
    start_time = time.time() # Startzeit
    recs = rec.recommend_books(selected_user['userId'])
    sims = get_similar_users(selected_user['userId'], algo)
    end_time = time.time() # Endzeit
    duration = end_time - start_time

    st.subheader("Top 3 Book Recommendations")
    st.table(pd.DataFrame(recs))

    st.subheader("Top 3 Similar Users")
    st.table(pd.DataFrame(sims))

    st.subheader("Graph Visualization")
    graph_data = rec.get_graph_data(selected_user['userId'])
    net = build_graph(selected_user['userId'], graph_data, algo)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        path = tmp_file.name
        net.show(path, notebook=False)
    with open(path, "r", encoding="utf-8") as f:
        html_content = f.read()
    components.html(html_content, height=700, scrolling=True)
    #os.unlink(path)

    st.success(f"Laufzeit für '{algo}'-Empfehlung: {duration:.2f} Sekunden") # Ausgabe der Laufzeit

###### Notes:
# funktioniert Node2Vec vielleicht bei Linh? (sonst rauslöschen)