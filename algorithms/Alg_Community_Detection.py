from neo4j import GraphDatabase

# Connection configuration
URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "SuperPasswort"

class CommunityDetectionLouvain:
    def __init__(self, uri, username, password):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self):
        self.driver.close()

    def create_user_similarity_projection(self):
        """
        Creates a weighted user-user graph based on shared positively rated books (ratings ≥ 6)
        using Cypher and the Neo4j Graph Data Science library.
        """
        query = """
        CALL gds.graph.project.cypher(
            'userSimilarityGraph',
            'MATCH (u:User) RETURN id(u) AS id',
            '
            MATCH (u1:User)-[r1:RATED]->(b:Book)<-[r2:RATED]-(u2:User)
            WHERE u1 <> u2 AND r1.rating >= 6 AND r2.rating >= 6
            RETURN id(u1) AS source, id(u2) AS target, COUNT(*) AS weight
            '
        )
        """
        with self.driver.session() as session:
            result = session.run(query)
            print("Graph projection created.")
            print(result.single())

    def run_louvain_algorithm(self):
        """
        Executes the Louvain algorithm on the projected graph and writes the 'community' property to User nodes.
        """
        query = """
        CALL gds.louvain.write('userSimilarityGraph', {
            writeProperty: 'community',
            relationshipWeightProperty: 'weight'
        })
        YIELD communityCount, modularity
        """
        with self.driver.session() as session:
            result = session.run(query)
            for record in result:
                print(f"Louvain completed: {record['communityCount']} communities, modularity = {record['modularity']:.4f}")

# Main runner
if __name__ == "__main__":
    detector = CommunityDetectionLouvain(URI, USERNAME, PASSWORD)

    try:
        detector.create_user_similarity_projection()
        detector.run_louvain_algorithm()
    finally:
        detector.close()
