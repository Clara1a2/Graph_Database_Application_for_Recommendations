import pandas as pd

books = pd.read_csv("Books.csv", encoding='ISO-8859-1', low_memory=False)
ratings = pd.read_csv("Ratings.csv", encoding='ISO-8859-1')
users = pd.read_csv("Users.csv", encoding='ISO-8859-1')

# Filter unnecessary or corrupted data
ratings = ratings[ratings['Book-Rating'] > 0]

