# Graph-Based Recommendation Algorithms

This module contains two algorithm scripts used in a book recommendation system powered by **Neo4j** and the **Graph Data Science (GDS)** library.

---

## Files Included

#### `Alg_Community_Detection.py`  
  Runs the **Louvain community detection** algorithm based on user co-rating behavior.

#### `Alg_KNN_FastRP.py`  
  Projects user-book interactions, calculates **FastRP embeddings**, and applies **k-Nearest Neighbors (KNN)** to connect similar users via a `SIMILAR_TO` relationship.

---

## Requirements

- Neo4j (with GDS and APOC installed)
- Python libraries:
  - `neo4j`

Install Python requirements:

`pip install neo4j`
