from flask import Flask, request, jsonify, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from transformers import pipeline
import os
import requests
import numpy as np
from flask import send_from_directory
from werkzeug.utils import secure_filename
from document_parser.excel_parser import ExcelParser
from document_parser.pdf_parser import PDFParser


# Configuration
db = SQLAlchemy()
app = Flask(__name__)
UPLOAD_FOLDER = './uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
efind_token = os.getenv('EFIND_TOKEN')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

db.init_app(app)

# Initialize the Hugging Face pipeline
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")


# Database model
class Component(db.Model):
    __tablename__ = 'components_characteristics'
    group_name = db.Column(db.String, primary_key=True)
    reliability = db.Column(db.Float)

    @staticmethod
    def get_all_groups():
        return [x.group_name for x in Component.query.all()]

    @staticmethod
    def get_reliability_value(group_name):
        component = Component.query.filter_by(group_name=group_name).first()
        if component:
            return {"component_group": group_name,
                    "probability": component.reliability,
                    # "all groups": Component.get_all_groups()
                    }
        else:
            return {"error": "Component not found"}


# API response helper
def api_response(res, status_code=200):
    return jsonify(res), status_code


def get_component_desc(component_name):
    # Define the API endpoint
    endpoint = f"https://efind.ru/api/search/{component_name}"

    # Define the query parameters
    params = {
        "access_token": efind_token,
        # "stock": 1,
        # "hp": 1,
        # "cur": "rur",
    }

    def get_most_informative_note(response):
        max_length = 0
        most_informative_note = ""

        for item in response:
            for row in item["rows"]:
                note = row.get("note", "")
                if len(note) > max_length:
                    max_length = len(note)
                    most_informative_note = note

        return most_informative_note

    # Send a GET request to the API endpoint
    response = requests.get(endpoint, params=params)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        # Extract the component_desc from the data
        if len(data) != 0:
            component_desc = get_most_informative_note(data)
        else:
            print(f"Error: Cant find component {component_name} in the database")
            return None

        return component_desc

    else:
        print(f"Error: Received status code {response.status_code}")
        return None


def get_reliability_by_name(component_name):
    # Get the component_desc from the API
    component_desc = get_component_desc(component_name)
    out = classifier(component_desc, Component.get_all_groups())
    ind = np.argmax(out['scores'])
    component_group = out['labels'][ind]

    return Component.get_reliability_value(component_group)


def get_components_from_file(filename):
    file_path = app.config['UPLOAD_FOLDER'] + "/" + filename
    my_dict = {}
    if filename.endswith(".xls"):
        my_dict = ExcelParser(file_path).parse_pdf()
    elif filename.endswith(".pdf"):
        my_dict = PDFParser(file_path).parse_pdf()
    
    result = []
    for component_name, cl in my_dict.items():
        result.append(get_reliability_by_name(component_name))

    return result


@app.route('/')
def home():
    return send_from_directory('static', 'index.html')


# Routes
@app.route('/get_value', methods=['GET'])
def get_value():
    component_name = request.args.get('component_name')
    if not component_name:
        return api_response({"error": "Component name parameter missing"}, 400)

    return api_response(get_reliability_by_name(component_name))


@app.route('/get_from_file', methods=['GET', 'POST'])
def get_from_file():
    # check if the post request has the file part
    if 'file' not in request.files:
        return api_response({"error": "No file"}, 400)
    file = request.files['file']
    # If the user does not select a file, the browser submits an empty file without a filename.
    if file.filename == '':
        return api_response({"error": "No file"}, 400)
    
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return api_response(get_components_from_file(filename))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return api_response({'error': 'Not found'}, 404)


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return api_response({'error': 'Internal server error'}, 500)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
