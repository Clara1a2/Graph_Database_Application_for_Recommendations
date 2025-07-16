# Data Folder

This folder contains the raw dataset files, filtered outputs, and preprocessing scripts used in the Book Recommendation System project.

It also includes the `load_data.py` script, which imports the cleaned data into a **Neo4j graph database**. This script creates `User` and `Book` nodes, links them via `RATED` relationships, and enables the graph-based recommendation algorithms used later in the system.

---

## Dataset Source

The dataset used in this project comes from [Kaggle: Book Recommendation Dataset](https://www.kaggle.com/datasets/arashnic/book-recommendation-dataset) by **Arashnic**.

**License:** [CC0: Public Domain](https://creativecommons.org/publicdomain/zero/1.0/)  
You may use and distribute this dataset freely.

---

## Contents

### Raw CSV Files

| File           | Description                                |
|----------------|--------------------------------------------|
| `Books.csv`    | Metadata about books (title, author, etc.) |
| `Ratings.csv`  | User ratings for books                     |
| `Users.csv`    | User demographic information               |

---

### Filtered CSV Outputs

| File                   | Description                                               |
|------------------------|-----------------------------------------------------------|
| `filtered_ratings.csv` | Ratings with score > 0 (actual user input only)           |
| `filtered_users.csv`   | Users who provided valid (non-zero) ratings               |
| `filtered_books.csv`   | Books that have at least one valid rating                 |

---

## Preprocessing Scripts

### `ratings_filtering.py`
- Removes all entries from `Ratings.csv` with a rating of 0
- Saves cleaned data to `filtered_ratings.csv`

### `user_books_filtering.py`
- Uses `filtered_ratings.csv` to:
  - Filter users in `Users.csv` who actually rated books
  - Filter books in `Books.csv` that were actually rated
- Saves results to `filtered_users.csv` and `filtered_books.csv`

---

## Data Loading Script

### `load_data.py`
- Loads the cleaned datasets (`filtered_users.csv`, `filtered_books.csv`, `filtered_ratings.csv`) into a **Neo4j graph database**
- Creates `User` and `Book` nodes
- Establishes `RATED` relationships between users and books, including the rating value
- Uses batch processing for efficiency and scalability
- Optionally sets uniqueness constraints on node IDs to prevent duplicates

---

## Project Structure
.\
├── Books.csv\
├── Ratings.csv\
├── Users.csv\
├── ratings_filtering.py\
├── user_books_filtering.py\
├── filtered_ratings.csv\
├── filtered_users.csv\
├── filtered_books.csv
└── load_data.py

---

## How to Use

Run the scripts in this order to prepare the data:

`python data/ratings_filtering.py`\
`python data/user_books_filtering.py`

---

## Requirements
- Python 3.x
- No external dependencies (uses built-in `csv` module)

---

## Notes
- The scripts assume UTF-8 encoding for input/output.
- Field names in the CSV files must match exactly (e.g., `User-ID`, `ISBN`, `Book-Rating`).

---

## Dataset

This project uses the [Book Recommendation Dataset](https://www.kaggle.com/datasets/arashnic/book-recommendation-dataset) by **Arashnic**, made available on [Kaggle](https://www.kaggle.com/).

The dataset is licensed under [CC0: Public Domain](https://creativecommons.org/publicdomain/zero/1.0/), which permits use, modification, and distribution without restriction.  
Therefore, the dataset files (`Books.csv`, `Ratings.csv`, `Users.csv`) are included directly in this repository in compliance with that license.

> Please refer to the [original dataset page](https://www.kaggle.com/datasets/arashnic/book-recommendation-dataset) for any further context or metadata.