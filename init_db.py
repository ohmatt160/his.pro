#!/usr/bin/env python3
"""
Database initialization script for HIS.Pro
Run this script to set up the database and create initial migrations
"""

import os
import sys
from flask import Flask
from flask_migrate import init, migrate, upgrade
from app import create_app
from app.extensions import db

def init_database():
    """Initialize database migrations"""
    app = create_app()
    
    with app.app_context():
        try:
            # Initialize migrations directory
            if not os.path.exists('migrations'):
                print("Initializing migrations directory...")
                init()
                print("[OK] Migrations directory initialized")
            else:
                print("[OK] Migrations directory already exists")
            
            # Create initial migration
            print("Creating initial migration...")
            migrate(message='Initial migration')
            print("[OK] Initial migration created")
            
            # Apply migration
            print("Applying migration...")
            upgrade()
            print("[OK] Database migration applied successfully")
            
            print("\n[SUCCESS] Database setup complete!")
            print("You can now run the application with: python run.py")
            
        except Exception as e:
            print(f"[ERROR] Error during database initialization: {e}")
            sys.exit(1)

if __name__ == '__main__':
    init_database()
