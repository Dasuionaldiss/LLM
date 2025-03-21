from vertexai.preview.generative_models import GenerativeModel, Image, SafetySetting
from vertexai.generative_models import HarmCategory, HarmBlockThreshold
import re
import json
import requests
from io import BytesIO

def load_image_from_file(image_path):
    if image_path.startswith("http"):  # Check if it's a URL
        response = requests.get(image_path)
        if response.status_code != 200:
            raise ValueError(f"Failed to download image. Status code: {response.status_code}")
        image_data = BytesIO(response.content)  # Convert image to a file-like object
    else:  # Assume it's a local file
        image_data = open(image_path, "rb")
    
    return Image.from_bytes(image_data.read())  # Read image bytes

def generate_pgn_and_json(image_path):
    chess_image = load_image_from_file(image_path)

    # Initialize the Gemini Vision Model
    model = GenerativeModel("gemini-pro-vision")

    # Define a refined prompt
    prompt = """
    Extract chess game details from the provided image and generate a PGN file.
    The details include event name, site, date, round, white player, black player, result, and the moves.
    Ensure that the output follows PGN format exactly and contains only chess-related information.
    """

    # Set safety settings correctly
    safety_settings = [
        SafetySetting(category=HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH),
        SafetySetting(category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH),
        SafetySetting(category=HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH),
        SafetySetting(category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH),
    ]

    # Send request to Gemini API
    response = model.generate_content(
        [chess_image, prompt],
        safety_settings=safety_settings,
    )

    # Error handling to check for blocked responses
    try:
        if not response or not response.candidates:
            raise ValueError("No valid response received. Content may be blocked.")

        pgn_output = response.text
        if not pgn_output.strip():
            raise ValueError("Empty response. Content was likely blocked by safety filters.")

        print("Generated PGN:\n", pgn_output)

    except ValueError as e:
        print(f"Error: {e}")
        return None

    def extract_pgn_details(pgn_output):
        # Pattern to match PGN headers
        pgn_pattern = re.compile(r'\[([A-Za-z]+)\s+"([^"]+)"\]')

        # Extract PGN headers
        pgn_headers = dict(re.findall(pgn_pattern, pgn_output))

        # Map extracted details
        extracted_details = {
            "Event": pgn_headers.get("Event", "Unknown"),
            "Site": pgn_headers.get("Site", "Unknown"),
            "Date": pgn_headers.get("Date", "Unknown"),
            "Round": pgn_headers.get("Round", "Unknown"),
            "White": pgn_headers.get("White", "Unknown"),
            "Black": pgn_headers.get("Black", "Unknown"),
            "Result": pgn_headers.get("Result", "Unknown"),
        }

        return extracted_details

    pgn_details = extract_pgn_details(pgn_output)
    print("\n Extracted PGN Details:\n", json.dumps(pgn_details, indent=4))

    # 🔹 Save PGN and extracted details to a JSON file
    json_data = {
        "PGN": pgn_output,
        "Details": pgn_details
    }

    # 🔹 Save as JSON file
    with open("chess_game.json", "w") as json_file:
        json.dump(json_data, json_file, indent=4)
    print("\n JSON file saved as chess_game.json")

    return json_data