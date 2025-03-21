# app/app.py

from flask import Flask, request, jsonify
from model import generate_pgn_and_json

app = Flask(__name__)

# Route to process the uploaded image and generate PGN + JSON
@app.route("/generate_pgn", methods=["POST"])
def generate_pgn():
    # Check if the request contains an image file
    if "image" not in request.json:
        return jsonify({"error": "No image file provided."}), 400

    # Get the image file from the request
    image_file = request.json["image"]

    # Process the image using the model
    result = generate_pgn_and_json(image_file)

    # Handle errors if they occur
    if "error" in result:
        return jsonify({"error": result["error"]}), 500

    # Return the JSON response
    return jsonify(result)


# Run the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)