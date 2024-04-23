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
