# Graph Database Application for Book Recommendation

This project implements a personalized book recommendation system using a **Neo4j graph database**, community detection, and KNN-based similarity. It integrates data preprocessing, graph algorithms, and a visual recommendation interface built with **Streamlit**.

---

## Project Highlights

- **Graph Algorithms**: Louvain Community Detection and FastRP + KNN for finding similar users.
- **Neo4j Integration**: Uses Neo4j and its Graph Data Science library to store and analyze user-book interaction graphs.
- **Interactive UI**: A Streamlit front end for selecting a user and visualizing personalized recommendations.
- **Graph Visualization**: Built-in network views via Pyvis to explore how recommendations are made.

---

## Folder Structure

Graph_Database_Application_for_Book_Recommendation/\
├── algorithms/\
│ ├── Alg_Community_Detection.py\
│ ├── Alg_KNN_FastRP.py\
│ └── README.md\
├── data/\
│ ├── Books.csv\
│ ├── Ratings.csv\
│ ├── Users.csv\
│ ├── filtered_books.csv\
│ ├── filtered_ratings.csv\
│ ├── filtered_users.csv\
│ ├── ratings_filtering.py\
│ ├── user_books_filtering.py\
│ ├── load_data.py\
│ └── README.md\
├── recommender/\
│ ├── recommender_community.py\
│ ├── recommender_knn.py\
│ └── README.md\
├── assets/\
│ ├── classicRec.png\
│ ├── DeepRec.png\
│ ├── Final_Book_Recommendation_Krieger_Pham.pptx\
│ └── recsys_taxonomy.png\
├── streamlit_app.py\
└── README.md

---

## Technologies Used

- Python (pandas, neo4j, pyvis, streamlit)
- Neo4j (APOC + Graph Data Science)
- Pyvis for interactive graph visualization
- Streamlit for web-based UI
- CSV-based dataset from Kaggle

---

## How to Run

### 1. Install requirements
`pip install pandas streamlit neo4j pyvis`

### 2. Load data into Neo4j
`cd data/`\
`python ratings_filtering.py`\
`python user_books_filtering.py`\
`python load_data.py`

### 3. Run graph algorithms
`cd algorithms/`\
`python Alg_Community_Detection.py`\
`python Alg_KNN_FastRP.py`

### 4. Launch the Streamlit app
`streamlit run streamlit_app.py`

---

## Dataset

This project uses the [Book Recommendation Dataset](https://www.kaggle.com/datasets/arashnic/book-recommendation-dataset) by Arashnic, released under [CC0: Public Domain](https://creativecommons.org/publicdomain/zero/1.0/).

**Dataset files:**
- `Books.csv`
- `Ratings.csv`
- `Users.csv`

**Filtered versions:**
- `filtered_books.csv`
- `filtered_ratings.csv`
- `filtered_users.csv`

---

## Visual Assets

Stored in the `assets/` folder:

- `classicRec.png` — Classical Recommendation Algorithms
- `DeepRec.png` — Deep Learning Recommendation Algorithms
- `recsys_taxonomy.png` — Taxonomy of Recommendation Systems
- `Final_Book_Recommendation_Krieger_Pham.pptx` — Project-specific presentation

---

## License

This project is licensed under a **Custom Non-Commercial License**.

You may use, modify, and share this code for **personal and educational purposes only**.  
**Commercial use is strictly prohibited** without explicit permission.

---

## Author
Built with ❤️ by Clara Krieger, Thuy Linh Pham.
For educational and academic purposes.