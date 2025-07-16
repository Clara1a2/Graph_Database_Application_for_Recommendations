import csv

# Eingabedatei und Ausgabedatei definieren
input_file = 'Ratings.csv'
output_file = 'filtered_ratings.csv'

with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', newline='', encoding='utf-8') as outfile:
    reader = csv.reader(infile)
    writer = csv.writer(outfile)

    for row in reader:
        if row[2] != '0':  # Book-Rating ist in der dritten Spalte (Index 2)
            writer.writerow(row)
