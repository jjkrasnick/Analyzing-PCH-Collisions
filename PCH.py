# -*- coding: utf-8 -*-

# -- Sheet --



!pip install --upgrade pip
!pip install PyMuPDF
!pip install beautifulsoup4
!pip install pandas
!pip install numpy
!pip install folium
!pip install openpyxl

import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
import re  # Import regex module to use regular expressions

# URL where the PDFs are located
base_url = "https://www.malibucity.org/Archive.aspx?AMID=73"

# Make a request to the website
response = requests.get(base_url)
soup = BeautifulSoup(response.text, 'html.parser')

# Find all links on the webpage
links = soup.find_all('a')

# Directory to save the PDFs
save_dir = "downloaded_pdfs"
if not os.path.exists(save_dir):
    os.makedirs(save_dir)

# Regular expression to match "Month YYYY" format
pattern = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s\d{4}$")

# Loop through all links to find PDFs, download, and rename them
for link in links:
    href = link.get('href')
    pdf_name = link.text.strip()

    # Check if the PDF name matches the "Month YYYY" format
    if href and pattern.match(pdf_name):
        # Convert PDF name to ISO format YYYY-MM.pdf
        try:
            month, year = pdf_name.split()
            month_number = {
                "January": "01", "February": "02", "March": "03",
                "April": "04", "May": "05", "June": "06",
                "July": "07", "August": "08", "September": "09",
                "October": "10", "November": "11", "December": "12"
            }[month]
            iso_name = f"{year}-{month_number}.pdf"
        except ValueError:
            # Skip if the format is unexpected
            print(f"Skipping {pdf_name}: format is unexpected")
            continue

        # Full URL of the PDF
        pdf_url = urljoin(base_url, href)
        # Path to save the PDF
        save_path = os.path.join(save_dir, iso_name)
        # Download and save the PDF
        with requests.get(pdf_url, stream=True) as r:
            r.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Downloaded {iso_name}")

print("All PDFs have been downloaded and renamed.")

import csv
import os
import re
import fitz  # PyMuPDF


def adjust_location(location):
    """
    Adjusts the location string to ensure 'Pacific Coast Hwy' is first in intersections
    and replaces " and " with " & ".
    """
    if " and " in location:
        roads = location.split(" and ")
        if "Pacific Coast Hwy" in roads[1]:
            roads[0], roads[1] = roads[1], roads[0]  # Swap roads if PCH is second
        location = " & ".join(roads)
    return location


def parse_pdf_text(text, iso_date):
    data = []
    pattern = r"(\d{4})\s+(?=\d)"
    district_starts = [match.start() for match in re.finditer(pattern, text, re.MULTILINE)]

    district_starts.append(len(text))  # Add end of text as a split point

    for i in range(len(district_starts) - 1):
        district_text = text[district_starts[i]:district_starts[i + 1]]
        district_lines = district_text.splitlines()
        if len(district_lines) < 2:
            continue

        reporting_district = district_lines[0].strip()
        for line in district_lines[1:]:
            line_match = re.match(r"(\d+|I) at (.+)", line)
            if line_match:
                count, location = line_match.groups()
                location = re.sub(r" \((N|S|E|W)\)", "", location)  # Remove directional modifiers
                location = location.replace(" and Private Property", "")  # Remove " and Private Property"
                location = adjust_location(location)  # Adjust location for intersections

                if 'Pacific Coast Hwy' not in location:
                    continue  # Skip record if PCH is not in location
                count = 1 if count == "I" else int(count)  # Correct OCR error

                data.append({
                    "ISO Date": iso_date,
                    "Reporting District": reporting_district,
                    "Count": count,
                    "Location": location
                })

    return data


def process_pdf_files(directory, output_csv):
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    pdf_files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    pdf_files.sort()

    with open(output_csv, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=["ISO Date", "Reporting District", "Count", "Location"])
        writer.writeheader()

        for pdf_file in pdf_files:
            iso_date = pdf_file[:-4]
            filepath = os.path.join(directory, pdf_file)
            print(f"Processing file: {pdf_file}")

            try:
                doc = fitz.open(filepath)
                text = ""
                for page in doc:
                    text += page.get_text()

                if "Collisions by Reporting Districts" not in text:
                    print(f"Required section not found in {pdf_file}. Skipping.")
                    continue

                data = parse_pdf_text(text, iso_date)
                for record in data:
                    writer.writerow(record)

            except Exception as e:
                print(f"Failed to process {pdf_file}: {str(e)}")

            finally:
                doc.close()


# Process the PDF files and output the data to a CSV file
process_pdf_files('downloaded_pdfs', 'analysis/PCHdata.csv')



!pip install scikit-learn matplotlib
!pip install folium

import folium
import pandas as pd
from sklearn.cluster import DBSCAN

# Load the Excel file
df = pd.read_excel('analysis/PCHcollisions.xlsx', sheet_name='Collisions')

# Create a ndarray with latitude and longitude
coordinates = df[['Lat', 'Lon']].values

# Use the DBSCAN clustering algorithm to cluster close locations
# we use eps=0.01 as the maximum distance between two samples, 
# and min_samples=5 as the number of samples in a neighborhood for a point to be considered as a core point.
dbscan = DBSCAN(eps=0.01, min_samples=5)
clusters = dbscan.fit_predict(coordinates)

# Add the clusters to the DataFrame as 'Cluster Location'
df['Cluster Location'] = clusters

clustered_locations = df.groupby('Cluster Location').agg({'Number of Collisions': 'sum', 'Lat': 'first', 'Lon': 'first', 'District': 'first'})

# Create a map for clustered locations centered at Malibu
clustered_map = folium.Map(location=[34.0259, -118.7798], zoom_start=13)

# Define a color map for the Districts
districts = df['District'].unique()
colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'pink', 'lightblue', 'lightgreen', 'gray', 'black']
color_map = dict(zip(districts, colors))

# Add a circle marker for each clustered location
for index, row in clustered_locations.iterrows():
    folium.CircleMarker(
        location=[row['Lat'], row['Lon']],
        radius=row['Number of Collisions'] / 1,  # scale down to avoid oversized circles
        color=color_map[row['District']],
        fill=True,
        fill_color=color_map[row['District']],
        fill_opacity=0.6,
        popup=f"Cluster Location: {index}, Collisions: {row['Number of Collisions']}"
    ).add_to(clustered_map)

# Display the map
clustered_map

