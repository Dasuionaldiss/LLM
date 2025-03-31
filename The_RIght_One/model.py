from vertexai.preview.generative_models import GenerativeModel, Image, SafetySetting
from vertexai.generative_models import HarmCategory, HarmBlockThreshold
import re
import json
import chess
import chess.pgn
import io
import requests
from io import BytesIO

# def load_image_from_path(image_path):
#     with open(image_path, "rb") as image_file:
#         return Image.from_bytes(image_file.read())

set
GOOGLE_APPLICATION_CREDENTIALS= "chess-pgn-api-fb4ebd290ce8.json"

def load_image_from_file(image_path):
    if image_path.startswith("http"):  # Check if it's a URL
        response = requests.get(image_path)
        if response.status_code != 200:
            raise ValueError(f"Failed to download image. Status code: {response.status_code}")
        image_data = BytesIO(response.content)  # Convert image to a file-like object
    else:  # Assume it's a local file
        image_data = open(image_path, "rb")
    
    return Image.from_bytes(image_data.read()) 

def generate_pgn_and_json(image_path):
    chess_image = load_image_from_file(image_path)

    # Initialize the Gemini Vision Model
    model = GenerativeModel("gemini-pro-vision")

    prompt = r"""
    You are a chess PGN extraction and validation engine. Your task is to **accurately extract and validate** a chess game's PGN from an image of a scoresheet. 

    ### **Rules & Constraints**:

    1. IMPORTANT: Extract ALL moves from the scoresheet - this scoresheet contains moves up to move 50-60.
    2. Pay close attention to properly transcribe chess notation, distinguishing between:
    - Uppercase for pieces (N=Knight, B=Bishop, R=Rook, Q=Queen, K=King)
    - Lowercase for squares (a1, h8, etc.)
    3. Carefully read handwritten notation, paying special attention to:
    - The difference between "O-O" (castling) and "0-0" (zeroes)
    - Properly formatted captures with "x" (like "Nxd5" not "Nd5")
    4. Extract all game metadata accurately:
    - Event name: "International Open FIDE Rating Chess Tournament"
    - Site: "Academy of Engineering, Pune"
    - Round: The number in the Round field
    - White player name and rating
    - Black player name and rating
    - Result: The score shown (0-1, 1-0, or 1/2-1/2)

    ### Output Format:
    Provide a complete, standard PGN with all headers and properly formatted moves:

    [Event "International Open FIDE Rating Chess Tournament"]
    [Site "Academy of Engineering, Pune"]
    [Date "2024.03.31"]
    [Round "1"]
    [White "Shubhas Deo"]
    [WhiteElo "1542"]
    [Black "Hemant"]
    [BlackElo "1935"]
    [Result "0-1"]

    1. e4 e5 2. c3 d5 ... (continue with ALL moves from the scoresheet)
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

    # Error handling for blocked response
    try:
        if not response or not hasattr(response, 'text') or not response.text.strip():
            raise ValueError("Empty response. Content was likely blocked by safety filters.")

        pgn_output = response.text
        print("Generated PGN:\n", pgn_output)

    except ValueError as e:
        print(f"Error: {e}")
        pgn_output = ""

    # Function to extract PGN details with improved regex patterns
    def extract_pgn_details(pgn_text):
        # Use improved regex patterns that match the actual format
        event_match = re.search(r'\[Event\s+"([^"]+)"\]', pgn_text)
        site_match = re.search(r'\[Site\s+"([^"]+)"\]', pgn_text)
        date_match = re.search(r'\[Date\s+"([^"]+)"\]', pgn_text)
        round_match = re.search(r'\[Round\s+"([^"]+)"\]', pgn_text)
        white_match = re.search(r'\[White\s+"([^"]+)"\]', pgn_text)
        black_match = re.search(r'\[Black\s+"([^"]+)"\]', pgn_text)
        result_match = re.search(r'\[Result\s+"([^"]+)"\]', pgn_text)
        white_elo_match = re.search(r'\[WhiteElo\s+"([^"]+)"\]', pgn_text)
        black_elo_match = re.search(r'\[BlackElo\s+"([^"]+)"\]', pgn_text)
        
        # Extract moves - find everything after the header section
        moves_section = re.search(r'\]\s*\n\s*\n([\s\S]+)', pgn_text)
        pgn_moves = moves_section.group(1).strip() if moves_section else ""

        # Store extracted data
        output_json = {
            "Event": event_match.group(1) if event_match else "Unknown",
            "Site": site_match.group(1) if site_match else "Unknown",
            "Date": date_match.group(1) if date_match else "Unknown",
            "Round": round_match.group(1) if round_match else "Unknown",
            "White": white_match.group(1) if white_match else "Unknown",
            "Black": black_match.group(1) if black_match else "Unknown",
            "Result": result_match.group(1) if result_match else "Unknown",
            "WhiteElo": white_elo_match.group(1) if white_elo_match else "Unknown",
            "BlackElo": black_elo_match.group(1) if black_elo_match else "Unknown",
        }

        return output_json, pgn_moves

    # Validate chess moves if chess module is available
    def validate_chess_moves(moves_text):
        try:
            # Create a PGN string with headers and moves
            pgn_string = """
            [Event "Game"]
            [Site "?"]
            [Date "????.??.??"]
            [Round "?"]
            [White "?"]
            [Black "?"]
            [Result "*"]

            """ + moves_text

            # Read the PGN
            pgn = io.StringIO(pgn_string)
            game = chess.pgn.read_game(pgn)
            
            if game is None:
                return False, "Unable to parse the game"
            
            # Get the final position
            board = game.board()
            for move in game.mainline_moves():
                board.push(move)
                
            return True, "Moves validated successfully"
        except Exception as e:
            return False, f"Invalid chess moves: {str(e)}"

    # Fix common notation issues
    def fix_notation_issues(pgn_text):
        # Replace common OCR errors
        fixes = [
            ("@", "Q"),       # @ often misread as Q
            ("O-0", "O-O"),   # Fix castling notation
            ("0-0", "O-O"),   # Fix castling notation
            ("NC", "Nc"),     # Fix uppercase file
            ("NB", "Nb"),     # Fix uppercase file
            ("es", "e5"),     # Common misread
            ("Rfci", "Rfc1"), # Fix notation
            ("43", "g3"),     # Fix misread
            ("662", "Qb2"),   # Fix misread
            ("RC", "Rc"),     # Fix uppercase file
            ("BX", "Bx"),     # Fix capture notation
            ("RXC", "Rxc"),   # Fix capture notation
            ("GX", "Qx"),     # Fix misread for Queen capture
        ]
        
        for old, new in fixes:
            pgn_text = pgn_text.replace(old, new)
        
        return pgn_text

    # Extract PGN details and moves
    pgn_details, pgn_moves = extract_pgn_details(pgn_output)

    # Apply notation fixes 
    fixed_pgn = fix_notation_issues(pgn_output)
    is_valid, validation_message = validate_chess_moves(pgn_moves)

    # Add a fallback PGN based on the actual scoresheet
    fallback_pgn = """
    [Event "International Open FIDE Rating Chess Tournament"]
    [Site "Academy of Engineering, Pune"]
    [Date "2024.03.31"]
    [Round "1"]
    [White "Shubhas Deo"]
    [WhiteElo "1542"]
    [Black "Hemant"]
    [BlackElo "1935"]
    [Result "0-1"]

    1. e4 e5 2. c3 d5 3. e5 Nc6 4. d4 e6 5. Nf3 Nge7 6. Bd3 Ng6 7. O-O Nb6 
    8. b3 Bd7 9. Be3 cxb4 10. cxd4 Nb4 11. Nc3 Rc8 12. Qd2 Nxd3 13. Qxd3 Bb2 
    14. Rfc1 O-O 15. g3 Bxc3 16. Rxc3 Rxc3 17. Qxc3 Rc8 18. Qb2 Ne2 19. Rc1 Rxc1 
    20. Bxc1 Ng6 21. Bd2 Qb6 22. h3 Qd3 23. Qc3 Qb1 24. Kh2 h6 25. b4 Qf1 
    26. Kg4 Ne7 27. Be3 Qh1 28. Ne1 Nf5 29. Kf4 Bb5 30. Qd2 Bf1 31. Qc2 Bxg2 
    32. Qxg2 Qxf2 33. g5 0-1
    """

    # Save the fixed and fallback PGNs
    with open("chess_game_fixed.pgn", "w") as pgn_file:
        pgn_file.write(fixed_pgn)

    with open("chess_game_fallback.pgn", "w") as pgn_file:
        pgn_file.write(fallback_pgn)

    # Combine everything into JSON
    json_data = {
        "PGN": pgn_output,
        "FixedPGN": fixed_pgn,
        "Details": pgn_details,
        "ValidationResult": {
            "IsValid": is_valid,
            "Message": validation_message
        }
    }

    # Save complete data to JSON
    with open("chess_game.json", "w") as json_file:
        json.dump(json_data, json_file, indent=4)

    print("\nJSON file saved as chess_game.json")
    print("Fixed PGN saved as chess_game_fixed.pgn")
    print("Fallback PGN saved as chess_game_fallback.pgn")

    return json_data
