#!/usr/bin/env python3
"""
Quick Start Script for Multi-Brand Odoo Setup

This script helps you quickly set up a multi-brand Odoo environment.
It will create sample brands and assign them to websites.

Usage:
    python quickstart.py --create-brands
    python quickstart.py --demo
"""

import argparse
import sys


SAMPLE_BRANDS = [
    {
        'name': 'GreenMotive',
        'code': 'greenmotive',
        'primary': '#34D399',
        'secondary': '#0f766e',
        'description': 'Eco-friendly automotive brand with modern green aesthetics'
    },
    {
        'name': 'TechPro Solutions',
        'code': 'techpro',
        'primary': '#3B82F6',
        'secondary': '#1E40AF',
        'description': 'Professional tech services with corporate blue theme'
    },
    {
        'name': 'LuxeBrand',
        'code': 'luxe',
        'primary': '#A855F7',
        'secondary': '#6B21A8',
        'description': 'Luxury lifestyle brand with premium purple palette'
    },
    {
        'name': 'OrangeWave',
        'code': 'orangewave',
        'primary': '#F97316',
        'secondary': '#C2410C',
        'description': 'Energetic and vibrant brand with warm orange tones'
    },
]


def print_banner():
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🎨 Multi-Brand Odoo White Label Setup                  ║
║                                                           ║
║   Quick start wizard for deployable_brand_theme          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")


def create_scss_brand_section(brand):
    """Generate SCSS for a brand."""
    return f"""
body.brand-{brand['code']} {{
  --brand-primary: {brand['primary']};
  --brand-secondary: {brand['secondary']};
  --brand-bg: #f7f7f7;
}}
"""


def create_brand_xml_record(brand):
    """Generate XML record for a brand."""
    return f"""
  <record id="brand_{brand['code']}" model="deployable.brand">
    <field name="name">{brand['name']}</field>
    <field name="code">{brand['code']}</field>
    <field name="primary_color">{brand['primary']}</field>
    <field name="secondary_color">{brand['secondary']}</field>
    <field name="logo_svg">/deployable_brand_theme/static/src/img/{brand['code']}-logo.svg</field>
    <field name="is_active" eval="True"/>
  </record>
"""


def show_demo_instructions():
    """Show instructions for demo mode."""
    print("\n" + "="*60)
    print("📚 DEMO MODE - Quick Start Instructions")
    print("="*60)
    
    print("\n1️⃣  Install the Module:")
    print("   - Open Odoo (http://localhost:8069)")
    print("   - Go to Apps → Update Apps List")
    print("   - Search for 'GreenMotive White Label Theme'")
    print("   - Click Install")
    
    print("\n2️⃣  View Available Brands:")
    print("   - Go to Website → Configuration → Brands")
    print("   - You'll see 3 pre-configured brands:")
    for brand in SAMPLE_BRANDS[:3]:
        print(f"     • {brand['name']} ({brand['code']})")
    
    print("\n3️⃣  Assign Brand to Website:")
    print("   - Go to Website → Configuration → Settings")
    print("   - Under 'Branding', select a brand")
    print("   - Save and refresh your website")
    
    print("\n4️⃣  Preview Brands:")
    print("   - Go to Website → Configuration → Brands")
    print("   - Click on any brand")
    print("   - Click 'Preview Brand' button")
    
    print("\n5️⃣  Create New Brand:")
    print("   - Go to Website → Configuration → Brands")
    print("   - Click 'Create'")
    print("   - Fill in name, code, colors, logo path")
    print("   - Add SCSS rules to static/src/scss/brand.scss:")
    print("     body.brand-yourcode {")
    print("       --brand-primary: #yourcolor;")
    print("       --brand-secondary: #yourcolor;")
    print("     }")
    
    print("\n6️⃣  Automated Deployment:")
    print("   python provision_brand.py --brand-code greenmotive --db-name mydb")
    
    print("\n" + "="*60)
    print("📖 For more info, see README.md and DEPLOYMENT.md")
    print("="*60 + "\n")


def show_brand_creation_code():
    """Show code snippets for creating brands."""
    print("\n" + "="*60)
    print("🔧 BRAND CREATION - Code Snippets")
    print("="*60)
    
    print("\n📝 1. Add to data/brand_data.xml:")
    print("-" * 60)
    for brand in SAMPLE_BRANDS:
        print(create_brand_xml_record(brand))
    
    print("\n🎨 2. Add to static/src/scss/brand.scss:")
    print("-" * 60)
    for brand in SAMPLE_BRANDS:
        print(create_scss_brand_section(brand))
    
    print("\n📁 3. Add logo files to static/src/img/:")
    print("-" * 60)
    for brand in SAMPLE_BRANDS:
        print(f"   • {brand['code']}-logo.svg")
    
    print("\n✅ After adding these:")
    print("   1. Restart Odoo")
    print("   2. Update the module: Apps → deployable_brand_theme → Update")
    print("   3. Brands will appear in Website → Configuration → Brands")
    print("="*60 + "\n")


def show_brand_table():
    """Display table of sample brands."""
    print("\n" + "="*60)
    print("🎨 Sample Brands Overview")
    print("="*60)
    
    header = f"{'Name':<20} {'Code':<15} {'Primary':<10} {'Secondary':<10}"
    print(header)
    print("-" * 60)
    
    for brand in SAMPLE_BRANDS:
        print(f"{brand['name']:<20} {brand['code']:<15} {brand['primary']:<10} {brand['secondary']:<10}")
    
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Quick start for multi-brand Odoo setup')
    parser.add_argument('--demo', action='store_true', help='Show demo instructions')
    parser.add_argument('--create-brands', action='store_true', help='Show code to create sample brands')
    parser.add_argument('--list', action='store_true', help='List sample brands')
    
    args = parser.parse_args()
    
    print_banner()
    
    if args.demo:
        show_demo_instructions()
    elif args.create_brands:
        show_brand_creation_code()
    elif args.list:
        show_brand_table()
    else:
        # Default: show everything
        show_brand_table()
        show_demo_instructions()
        print("\n💡 Run with --create-brands to see code snippets")
        print("💡 Run with --list to see brand overview table")


if __name__ == '__main__':
    main()
