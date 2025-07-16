# Recommendation Modules

This directory contains two core Python modules that implement and visualize book recommendations based on user similarity — one using **community detection** and the other using **KNN embeddings** from a Neo4j graph database.

---

## Dependencies

Both modules require:

- `neo4j` — for database connection and Cypher queries
- `pyvis` — for interactive graph visualization in the browser

Install them via:

`pip install neo4j pyvis`
