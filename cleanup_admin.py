#!/usr/bin/env python
"""Script to delete the default admin user from the database"""
import os
import sys

os.chdir('C:/Users/mattw/Downloads/new-his')
sys.path.insert(0, 'C:/Users/mattw/Downloads/new-his')

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models.user import User
from app.models.facility import Facility
from app.extensions import db

app = create_app('development')
with app.app_context():
    # Delete admin users
    deleted_count = 0
    
    # Find all users with username 'admin'
    admin_users = User.query.filter_by(username='admin').all()
    for user in admin_users:
        print(f"Deleting user: {user.username} (email: {user.email}, facility: {user.facility_slug})")
        db.session.delete(user)
        deleted_count += 1
    
    db.session.commit()
    print(f"\nDeleted {deleted_count} admin user(s)")
    
    # Also list remaining users
    remaining_users = User.query.all()
    print(f"\nRemaining users ({len(remaining_users)}):")
    for u in remaining_users:
        print(f"  - {u.username} ({u.email})")