import os
import fitz  # PyMuPDF
import re
import pandas as pd


def transform_location(location):
    """
    Transforms the location so that 'Pacific Coast Hwy' appears before 'and', if both are present.
    Drops any part of the Location after 'and' if 'Pacific Coast Hwy' contains a street number
    or the part after 'and' is 'Private Property'.
    """
    # Check if location contains 'Pacific Coast Hwy'
    if "Pacific Coast Hwy" in location:
        parts = location.split(" and ")
        # Ensure 'Pacific Coast Hwy' appears first, rearrange if necessary
        if len(parts) > 1:
            pch_index = 0 if "Pacific Coast Hwy" in parts[0] else 1
            other_index = 1 - pch_index
            # If 'Pacific Coast Hwy' part contains a street number or other part is 'Private Property', drop the other part
            if re.search(r'\d', parts[pch_index]) or parts[other_index].strip() == "Private Property":
                location = parts[pch_index]
            # Otherwise, ensure 'Pacific Coast Hwy' is first
            elif pch_index != 0:
                location = "Pacific Coast Hwy and " + parts[0]
        # Address specific formatting if necessary
        # Example: Handling unexpected or complex patterns (not shown here)

    return location


def extract_details(pdf_path):
    """
    Extracts reporting districts along with the number of collisions and their locations
    from the 'Collisions by Reporting Districts' section, applying transformations and corrections.
    """
    details = []
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text("text")
        doc.close()

        # Correct common OCR parsing errors: 'I at' to '1 at'
        corrected_text = text.replace("I at", "1 at")

        # Find the relevant section
        pattern = r'Collisions by Reporting Districts(.*?)(?=Collision Occurred Most Frequently On:|$)'
        match = re.search(pattern, corrected_text, re.DOTALL)
        if match:
            section_text = match.group(1)
            # Extract details: district number, collisions, and location
            details_pattern = re.compile(r'^\s*(\d{4})\s*$(.*?)^(?=\d{4}\s*$|\Z)', re.MULTILINE | re.DOTALL)
            for district_match in details_pattern.finditer(section_text):
                district = district_match.group(1)
                collision_details = re.findall(r'(\d+) at (.+?)(?=\n\d+ at |\n\n|\Z)', district_match.group(2),
                                               re.DOTALL)
                for num_collisions, location in collision_details:
                    location = location.strip()
                    # Skip entries not containing 'Pacific Coast Hwy'
                    if "Pacific Coast Hwy" not in location:
                        continue
                    # Transform location string to ensure 'Pacific Coast Hwy' appears first
                    transformed_location = transform_location(location)
                    details.append((district, num_collisions, transformed_location))
        else:
            print(f"'Collisions by Reporting Districts' section not found or followed properly in {pdf_path}")
            return None

    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return None

    return details


def process_directory(directory_path):
    """
    Processes PDF files, extracting and summarizing collision details, applying transformations where necessary.
    Additionally, saves the details to an Excel file.
    """
    all_details = []

    for filename in sorted(os.listdir(directory_path)):
        if filename.lower().endswith('.pdf'):
            # Extract report period from filename
            report_period = re.search(r'\d{4}-\d{2}', filename).group(0)
            pdf_path = os.path.join(directory_path, filename)
            details = extract_details(pdf_path)
            if details is not None:
                for detail in details:
                    # Prepend the report period to each detail tuple
                    all_details.append((report_period,) + detail)

    # Convert the list of details to a DataFrame
    df = pd.DataFrame(all_details, columns=["ISO Date", "District", "Number of Collisions", "Location"])

    # Define the path for the output Excel file within a writable directory
    output_file_path = "/tmp/PCHcollisions.xlsx"

    # Save the DataFrame to an Excel file
    df.to_excel(output_file_path, index=False)

    print(f"The Excel file has been saved to: {output_file_path}")

# Correctly expands the tilde to the user's home directory and sets the path
directory_path = os.path.expanduser('')
process_directory(directory_path)
