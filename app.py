from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from transformers import pipeline
import os
import requests
import numpy as np
import pandas as pd
from flask import send_from_directory
import json

from document_parser.excel_parser import ExcelParser
from document_parser.pdf_parser import PDFParser
from cache.cache import Cache
from search import google, efind

# Configuration
db = SQLAlchemy()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
efind_token = os.getenv('EFIND_TOKEN')

UPLOAD_FOLDER = './uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

description_cache = Cache()

db.init_app(app)

# Initialize the Hugging Face pipeline
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")


class DimGroup(db.Model):
    __tablename__ = 'dim_group'

    group_id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String())


    @staticmethod
    def get_group(group_id: int):
        row = DimGroup.query.filter_by(group_id=group_id).first()
        if row:
            return row.group_name

    @staticmethod
    def get_group_id(group_name):
        row = DimGroup.query.filter_by(group_name=group_name).first()
        if row:
            return row.group_id

    @staticmethod
    def get_all_groups():
        rows = DimGroup.query.all()
        return [row.group_id for row in rows]


class ComponentReliability(db.Model):
    __tablename__ = 'component_reliability'

    group_id = db.Column(db.Integer, db.ForeignKey('dim_group.group_id'), primary_key=True)
    reliability = db.Column(db.Float, nullable=False)


    @staticmethod
    def get_reliability_value(group_name):
        group_id = DimGroup.get_group_id(group_name)
        component = ComponentReliability.query.filter_by(group_id=group_id).first()

        if component:
            return {
                "component_group": group_name,
                "reliability": component.reliability,
            }
        else:
            return {}


class DimComponent(db.Model):
    __tablename__ = 'dim_component'

    component_name = db.Column(db.String(), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('dim_group.group_id'))


    @staticmethod
    def get_group(component_name):
        row = DimComponent.query.filter(DimComponent.component_name.contains(component_name)).first()
        if row:
            return row.group_id


class ClassComponent(db.Model):
    __tablename__ = 'class_component'

    class_name = db.Column(db.String(), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('dim_group.group_id'))


    @staticmethod
    def get_all_groups(class_name):
        rows = ClassComponent.query.filter_by(class_name=class_name).all()
        return [row.group_id for row in rows]


def get_group_names(class_name):
    if class_name:
        rows = ClassComponent.get_all_groups(class_name)
        return [DimGroup.get_group(row) for row in rows]
    else:
        return DimGroup.get_all_groups()

# API response helper
def api_response(res, status_code=200):
    return jsonify(res), status_code


def get_component_desc(component_name):
    desc, found = description_cache.get(component_name)
    if found:
        return desc
    
    component_desc = google.get_description(component_name)

    # component_desc = efind.get_description(component_name, efind_token)

    # if not component_desc:
    #     component_desc = google.get_description(component_name)

    if not component_desc:
        return None

    description_cache.set(component_name, component_desc)
    return component_desc


def search_db(component_name):
    print("SEARCHING DB:", component_name)
    # Try to find const group name
    component_group_id = DimComponent.get_group(component_name)
    component_group = DimGroup.get_group(component_group_id)

    if not component_group_id:
        print("NOT FOUND DB")
        return None
    
    print("COMPONENT GROUP:", component_group)
    res = ComponentReliability.get_reliability_value(component_group)
    if res:
        res["component_name"] = component_name
        return res
    
    print("NOT FOUND DB")
    return None

def get_reliability_by_name(component_name, component_class):
    print("SEARCHING:", component_name, component_class)

    all_groups = get_group_names(component_class)

    # Get the component_desc from the API
    component_desc = get_component_desc(component_name)

    print("DESCRIPTION:", component_desc)
    if not component_desc or not all_groups:
        return None

    out = classifier(component_desc, all_groups)
    ind = np.argmax(out['scores'])
    component_group = out['labels'][ind] 

    print("COMPONENT GROUP:", component_group)
    res = ComponentReliability.get_reliability_value(component_group)
    if res:
        res["component_name"] = component_name
        return res
    
    print("NOT FOUND")
    return None

def search_db_by_parts(full_name):
    res = search_db(full_name)
    if res:
        res["component_name"] = full_name
        return res

    name_part = list(filter(lambda x: len(x) > 3 and x.isupper(), full_name.split()))
    for component_name in name_part:
        res = {}
        if '-' in component_name:
            res = search_db(component_name[:component_name.find('-')+3])
        else:
            res = search_db(component_name)

        if res:
            res["component_name"] = full_name
            return res
        
    return None


def get_reliability_from_file(filename):
    file_path = app.config['UPLOAD_FOLDER'] + "/" + filename
    my_dict = {}
    if filename.endswith(".xls"):
        my_dict = ExcelParser(file_path).parse_excel()
    elif filename.endswith(".pdf"):
        my_dict = PDFParser(file_path).parse_pdf()
    
    print("FILE:", json.dumps(my_dict))

    result = []
    for full_name, component_class in my_dict.items():
        res = search_db_by_parts(full_name)
        if res:
            result.append(res)
            continue

        res = get_reliability_by_name(full_name, component_class)
        if res:
            result.append(res)        

    print(result)
    return result


# Routes
@app.route('/')
def home():
    return send_from_directory('static', 'index.html')


@app.route('/get_value', methods=['GET'])
def get_value():
    component_name = request.args.get('component_name')
    component_class = request.args.get('component_class')
    if not component_name:
        return api_response({"error": "Component name parameter missing"}, 400)

    res = search_db(component_name)
    if res:
        return api_response(res)
    
    res = get_reliability_by_name(component_name, component_class)
    if res:
        return api_response(res)
    
    return api_response({"error" : "not found"}, 404)


@app.route('/get_from_file', methods=['GET', 'POST'])
def get_from_file():
    if 'file' not in request.files:
        return api_response({"error": "No file"}, 400)
    file = request.files['file']
    # If the user does not select a file, the browser submits an empty file without a filename.
    if file.filename == '':
        return api_response({"error": "No file"}, 400)
    
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
    return api_response(get_reliability_from_file(file.filename))



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
