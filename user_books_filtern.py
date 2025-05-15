import csv

# Dateienamen
ratings_file = 'filtered_ratings.csv'
users_file = 'Users.csv'
books_file = 'Books.csv'

# Neue Dateien nach dem Filtern
filtered_users_file = 'filtered_users.csv'
filtered_books_file = 'filtered_books.csv'

# Schritt 1: Sammle gültige User-IDs und ISBNs aus ratings.csv
valid_user_ids = set()
valid_isbns = set()

with open(ratings_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        valid_user_ids.add(row['User-ID'])
        valid_isbns.add(row['ISBN'])

# Schritt 2: Filtere users.csv
with open(users_file, 'r', encoding='utf-8') as infile, \
     open(filtered_users_file, 'w', newline='', encoding='utf-8') as outfile:

    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        if row['User-ID'] in valid_user_ids:
            writer.writerow(row)

# Schritt 3: Filtere books.csv
with open(books_file, 'r', encoding='utf-8') as infile, \
     open(filtered_books_file, 'w', newline='', encoding='utf-8') as outfile:

    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        if row['ISBN'] in valid_isbns:
            writer.writerow(row)
