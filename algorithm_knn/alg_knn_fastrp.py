from neo4j import GraphDatabase

uri = "bolt://localhost:7687"
user = "neo4j"
password = "SuperPasswort"

driver = GraphDatabase.driver(uri, auth=(user, password))

def create_projection_fastrp(tx, name="userGraph"):
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
    query = f"""
    CALL gds.fastRP.write('{name}', {{
      writeProperty: 'embedding',
      embeddingDimension: {dim},
      relationshipWeightProperty: 'rating'
    }})
    YIELD nodePropertiesWritten;
    """
    return tx.run(query).data()
