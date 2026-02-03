#!/usr/bin/env python3
"""
Simple API to receive data from frontend and save to database
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg.rows import dict_row
import os
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    """Create a database connection"""
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    return conn

@app.route('/api/data', methods=['POST'])
def save_data():
    """
    Receive data from frontend and save to database
    Expected JSON format:
    {
        "mac_address": "XX:XX:XX:XX:XX:XX",
        "username": "user_name",
        "json_data": {...}
    }
    """
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Extract fields
        mac_address = data.get('mac_address')
        username = data.get('username')
        json_data = data.get('json_data', {})
        
        # Validate required fields
        if not mac_address:
            return jsonify({"error": "mac_address is required"}), 400
        
        # Connect to database
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Insert or update data
        cur.execute('''
            INSERT INTO device_data (mac_address, username, json_data, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (mac_address) 
            DO UPDATE SET 
                username = EXCLUDED.username,
                json_data = EXCLUDED.json_data,
                updated_at = EXCLUDED.updated_at
            RETURNING id, mac_address, username, json_data, created_at, updated_at
        ''', (mac_address, username, json.dumps(json_data), datetime.now(), datetime.now()))
        
        result = cur.fetchone()
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Data saved successfully",
            "data": dict(result)
        }), 201
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/data', methods=['GET'])
def get_data():
    """Get all data from database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('SELECT * FROM device_data ORDER BY created_at DESC')
        results = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "count": len(results),
            "data": [dict(row) for row in results]
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }), 200

if __name__ == '__main__':
    # Initialize database table on startup
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS device_data (
                id SERIAL PRIMARY KEY,
                mac_address VARCHAR(17) UNIQUE NOT NULL,
                username VARCHAR(255),
                json_data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

