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