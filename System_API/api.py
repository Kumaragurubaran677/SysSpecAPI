#!/usr/bin/env python3
"""
Simple API to receive data from frontend and save to database
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import psycopg
from psycopg.rows import dict_row
import os
import json
from dotenv import load_dotenv
from datetime import datetime


load_dotenv()

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.getenv('DATABASE_URL')

@app.route('/')
def index():
    """Serve the admin dashboard"""
    try:
        # Assuming admin_dashboard.html is in the parent directory of this file (System_API/api.py)
        # However, in deployments, the CWD might be the repo root.
        # We will try current dir and parent dir
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        
        file_path = os.path.join(parent_dir, 'admin_dashboard.html')
        
        if not os.path.exists(file_path):
             # Try repo root if running from inside System_API
             file_path = 'admin_dashboard.html'
             
        return send_file(file_path)
    except Exception as e:
        return str(e), 404

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

@app.route('/api/data/<mac_address>', methods=['DELETE'])
def delete_device(mac_address):
    """Delete a device by MAC address"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('DELETE FROM device_data WHERE mac_address = %s RETURNING id', (mac_address,))
        deleted = cur.fetchone()
        
        conn.commit()
        cur.close()
        conn.close()
        
        if deleted:
            return jsonify({
                "success": True,
                "message": "Device deleted successfully"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Device not found"
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
        
@app.route('/api/data/<mac_address>/rename', methods=['PATCH'])
def rename_device(mac_address):
    """Update the device name/username"""
    try:
        data = request.get_json()
        new_name = data.get('name')
        
        if not new_name:
            return jsonify({"error": "Name is required"}), 400
            
        conn = get_db_connection()
        cur = conn.cursor()
        
        # We need to update the username column AND the provided_username inside json_data
        # PostgreSQL's jsonb_set can update keys inside the JSON
        cur.execute('''
            UPDATE device_data 
            SET 
                username = %s,
                json_data = jsonb_set(
                    CASE 
                        WHEN json_data->'user' IS NULL THEN jsonb_set(json_data, '{user}', '{}'::jsonb)
                        ELSE json_data 
                    END, 
                    '{user, provided_username}', 
                    to_jsonb(%s::text)
                ),
                updated_at = CURRENT_TIMESTAMP
            WHERE mac_address = %s
            RETURNING id, mac_address, username, json_data
        ''', (new_name, new_name, mac_address))
        
        updated_device = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        if updated_device:
            return jsonify({
                "success": True,
                "message": "Device renamed successfully",
                "data": dict(updated_device)
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Device not found"
            }), 404

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/devices/<mac_address>', methods=['PUT'])
def update_device(mac_address):
    """Update a device's JSON data and username"""
    try:
        data = request.get_json()
       
        if not data or 'json_data' not in data:
            return jsonify({"error": "json_data is required"}), 400
       
        json_data = data['json_data']
        username = data.get('username', None)
       
        conn = get_db_connection()
        cur = conn.cursor()
       
        cur.execute(
            'UPDATE device_data SET json_data = %s, username = %s, updated_at = CURRENT_TIMESTAMP WHERE mac_address = %s RETURNING id, mac_address, username, json_data, updated_at',
            (json.dumps(json_data), username, mac_address)
        )
       
        updated_device = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
       
        if updated_device:
            return jsonify({
                "message": "Device updated successfully",
                "device": dict(updated_device)
            }), 200
        else:
            return jsonify({"error": "Device not found"}), 404
           
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
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



