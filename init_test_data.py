#!/usr/bin/env python
"""Script to initialize test data in the database"""
import os
import sys

# Change to project root to ensure .env is found
os.chdir('C:/Users/mattw/Downloads/new-his')
sys.path.insert(0, 'C:/Users/mattw/Downloads/new-his')

# Load .env explicitly
from dotenv import load_dotenv
load_dotenv()

print(f"DEV_DATABASE_URL: {os.getenv('DEV_DATABASE_URL')}")

# Import app first to initialize everything
from app import create_app
from app.extensions import db
from app.models.billing import Invoice, InvoiceItem, Payment, InsuranceProvider, InsuranceClaim
from app.models.user import User
from app.models.facility import Facility

app = create_app('development')
with app.app_context():
    # Check if we have any facilities
    facilities = Facility.query.all()
    print(f"Found {len(facilities)} facilities")
    print(f'Current facilities: {len(facilities)}')
    
    if not facilities:
        # Create test facility
        facility = Facility(
            name='Sunrise Medical Center',
            type='hospital',
            slug='sunrise',
            country='Nigeria',
            address='123 Health Street, Lagos',
            phone='+2348012345678',
            email='contact@sunrise.med',
            modules=['patients', 'appointments', 'billing', 'lab', 'pharmacy', 'dashboard'],
            is_active=True
        )
        db.session.add(facility)
        
        # Create admin user
        admin = User(
            username='admin',
            email='admin@sunrise.med',
            role='ADMIN',
            facility_slug='sunrise',
            first_name='System',
            last_name='Admin'
        )
        admin.set_password('Admin123!')
        db.session.add(admin)
        
        db.session.commit()
        print('Created test facility: sunrise')
        print('Created admin user: admin / Admin123!')
    else:
        for f in facilities:
            print(f'Facility: {f.name} ({f.slug})')
    
    print('Done!')