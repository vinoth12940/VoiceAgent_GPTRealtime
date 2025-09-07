#!/usr/bin/env python3
"""
Database Initialization Script for Voice Agent GPT Realtime

This script initializes the database with sample data for P&C insurance policies,
customers, and customer policies. It's safe to run multiple times and won't 
break existing data.

Usage:
    python init_db.py [--force]
    
Options:
    --force    Force re-seeding even if data already exists
"""

import os
import sys
import sqlite3
import argparse
from datetime import datetime

# Add backend directory to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from backend import db
    from backend.config import DB_PATH
except ImportError:
    print("❌ Error: Could not import backend modules. Make sure you're running from the project root.")
    sys.exit(1)

def check_existing_data():
    """Check if database already has data"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM policies")
        policies_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM customers") 
        customers_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM customer_policies")
        customer_policies_count = c.fetchone()[0]
        
        conn.close()
        
        return {
            'policies': policies_count,
            'customers': customers_count,
            'customer_policies': customer_policies_count
        }
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return None

def seed_sample_customers():
    """Seed sample customers for P&C insurance"""
    sample_customers = [
        {
            "full_name": "Heather Gray",
            "email": "maria92@example.com",
            "last4": "1234",
            "order_id": "POLICY-1632-Re"
        },
        {
            "full_name": "Judy Griffin", 
            "email": "benjamin77@example.org",
            "last4": "5419",
            "order_id": "POLICY-9334-rK"
        },
        {
            "full_name": "Patrick Jimenez",
            "email": "martinheather@example.org", 
            "last4": "7891",
            "order_id": "POLICY-4751-Mx"
        },
        {
            "full_name": "Jason Harrington",
            "email": "qcervantes@example.com",
            "last4": "3456",
            "order_id": "POLICY-8921-Tz"
        },
        {
            "full_name": "Jordan Graves",
            "email": "andrewstaylor@example.com",
            "last4": "9876",
            "order_id": "POLICY-2143-Qw"
        },
        {
            "full_name": "Sarah Mitchell",
            "email": "sarah.mitchell@example.com",
            "last4": "5432",
            "order_id": "POLICY-6789-Lp"
        },
        {
            "full_name": "Michael Chen",
            "email": "m.chen@example.org",
            "last4": "2468",
            "order_id": "POLICY-3571-Df"
        }
    ]
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    added = 0
    for customer in sample_customers:
        try:
            c.execute("""
            INSERT INTO customers(full_name, email, last4, order_id)
            VALUES(?,?,?,?)
            ON CONFLICT(email) DO UPDATE SET
              full_name=excluded.full_name,
              last4=excluded.last4,
              order_id=excluded.order_id
            """, (customer["full_name"], customer["email"].lower(), 
                  customer["last4"], customer["order_id"]))
            added += 1
        except Exception as e:
            print(f"⚠️  Warning: Could not add customer {customer['email']}: {e}")
    
    conn.commit()
    conn.close()
    return added

def initialize_database(force=False):
    """Initialize database with all sample data"""
    print("🚀 Initializing Voice Agent Database...")
    
    # Check if database file exists
    if not os.path.exists(DB_PATH):
        print(f"📁 Database file not found. Creating new database at: {DB_PATH}")
        
    # Initialize database schema
    print("📋 Creating database schema...")
    db.init_db()
    print("✅ Database schema created/verified")
    
    # Check existing data
    existing_data = check_existing_data()
    if existing_data is None:
        print("❌ Could not check existing data. Aborting.")
        return False
    
    print(f"📊 Current database contents:")
    print(f"   - Policies: {existing_data['policies']}")
    print(f"   - Customers: {existing_data['customers']}")
    print(f"   - Customer Policies: {existing_data['customer_policies']}")
    
    # Check if we should seed data
    has_data = any(count > 0 for count in existing_data.values())
    
    if has_data and not force:
        print("ℹ️  Database already contains data. Use --force to re-seed anyway.")
        print("✅ Database initialization complete (no changes made)")
        return True
    
    if force and has_data:
        print("🔄 Force flag enabled - re-seeding data...")
    else:
        print("🌱 Database is empty - seeding with sample data...")
    
    try:
        # Seed customers first
        print("👥 Adding sample customers...")
        customers_added = seed_sample_customers()
        print(f"✅ Added/updated {customers_added} customers")
        
        # Seed P&C policies
        print("📋 Adding P&C insurance policies...")
        db.seed_pc_policies()
        print("✅ P&C insurance policies added")
        
        # Seed customer policies
        print("🏠 Adding customer insurance policies...")
        db.seed_customer_policies()
        print("✅ Customer insurance policies added")
        
        # Verify final counts
        final_data = check_existing_data()
        if final_data:
            print(f"\n📊 Final database contents:")
            print(f"   - Policies: {final_data['policies']}")
            print(f"   - Customers: {final_data['customers']} ")
            print(f"   - Customer Policies: {final_data['customer_policies']}")
        
        print("\n🎉 Database initialization completed successfully!")
        print("\n💡 You can now run the application with:")
        print("   cd backend && python -m uvicorn main:app --reload")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during database seeding: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Initialize Voice Agent database with sample data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python init_db.py                 # Initialize if database is empty
  python init_db.py --force         # Force re-initialization
        """
    )
    parser.add_argument(
        '--force', 
        action='store_true',
        help='Force re-seeding even if data already exists'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  Voice Agent GPT Realtime - Database Initializer")
    print("=" * 60)
    
    success = initialize_database(force=args.force)
    
    if success:
        print("\n✅ Database initialization completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Database initialization failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
