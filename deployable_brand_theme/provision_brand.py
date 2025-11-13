#!/usr/bin/env python3
"""
Environment Provisioning Script for Multi-Brand Odoo Deployments

This script automates brand assignment when spinning up new Odoo environments.
It can be called during deployment or CI/CD pipelines.

Usage:
    python provision_brand.py --brand-code greenmotive --db-name production_db
    python provision_brand.py --brand-code techpro --db-name staging_db --website-domain staging.techpro.com
"""

import argparse
import xmlrpc.client
import os


def get_odoo_credentials():
    """Load Odoo credentials from environment variables."""
    return {
        'url': os.getenv('ODOO_URL', 'http://localhost:8069'),
        'db': os.getenv('ODOO_DB', 'odoo'),
        'username': os.getenv('ODOO_USER', 'admin'),
        'password': os.getenv('ODOO_PASSWORD', 'admin')
    }


def connect_odoo(url, db, username, password):
    """Establish connection to Odoo via XML-RPC."""
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    if not uid:
        raise ValueError("Authentication failed")
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    return models, uid


def assign_brand_to_website(models, uid, db, password, brand_code, website_domain=None):
    """Assign a brand to a website by brand code."""
    # Search for the brand
    brand_ids = models.execute_kw(
        db, uid, password,
        'deployable.brand', 'search',
        [[['code', '=', brand_code]]]
    )
    
    if not brand_ids:
        print(f"❌ Brand with code '{brand_code}' not found!")
        return False
    
    brand_id = brand_ids[0]
    
    # Find or create website
    if website_domain:
        website_ids = models.execute_kw(
            db, uid, password,
            'website', 'search',
            [[['domain', '=', website_domain]]]
        )
    else:
        # Default to first website
        website_ids = models.execute_kw(
            db, uid, password,
            'website', 'search',
            [[]], {'limit': 1}
        )
    
    if not website_ids:
        print(f"❌ No website found!")
        return False
    
    website_id = website_ids[0]
    
    # Update website with brand
    models.execute_kw(
        db, uid, password,
        'website', 'write',
        [[website_id], {'brand_id': brand_id}]
    )
    
    print(f"✅ Successfully assigned brand '{brand_code}' to website (ID: {website_id})")
    return True


def main():
    parser = argparse.ArgumentParser(description='Provision Odoo environment with specific brand')
    parser.add_argument('--brand-code', required=True, help='Brand code (e.g., greenmotive, techpro, luxe)')
    parser.add_argument('--db-name', help='Database name (overrides ODOO_DB env var)')
    parser.add_argument('--website-domain', help='Website domain to assign brand to')
    parser.add_argument('--odoo-url', help='Odoo URL (overrides ODOO_URL env var)')
    
    args = parser.parse_args()
    
    # Get credentials
    creds = get_odoo_credentials()
    
    # Override with CLI args if provided
    if args.db_name:
        creds['db'] = args.db_name
    if args.odoo_url:
        creds['url'] = args.odoo_url
    
    print(f"🚀 Provisioning brand '{args.brand_code}' for database '{creds['db']}'...")
    
    try:
        models, uid = connect_odoo(creds['url'], creds['db'], creds['username'], creds['password'])
        success = assign_brand_to_website(
            models, uid, creds['db'], creds['password'],
            args.brand_code, args.website_domain
        )
        
        if success:
            print("🎉 Brand provisioning completed successfully!")
        else:
            print("⚠️ Brand provisioning encountered issues.")
            exit(1)
            
    except Exception as e:
        print(f"❌ Error during provisioning: {e}")
        exit(1)


if __name__ == '__main__':
    main()
