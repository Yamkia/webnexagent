from odoo import http
from odoo.http import request


class BrandPreviewController(http.Controller):
    
    @http.route('/brand/preview/<int:brand_id>', type='http', auth='user', website=True)
    def brand_preview(self, brand_id, **kwargs):
        """Render a preview page with the selected brand applied."""
        brand = request.env['deployable.brand'].browse(brand_id)
        if not brand.exists():
            return request.not_found()
        
        # Temporarily override website brand for preview
        website = request.website
        original_brand = website.brand_id
        
        try:
            # Set preview brand
            website.brand_id = brand
            
            values = {
                'brand': brand,
                'preview_mode': True,
                'original_brand': original_brand,
            }
            
            return request.render('deployable_brand_theme.brand_preview_template', values)
        finally:
            # Restore original brand
            website.brand_id = original_brand
    
    @http.route('/brand/api/list', type='json', auth='user')
    def brand_list(self):
        """Return list of all brands (JSON API)."""
        brands = request.env['deployable.brand'].search([('is_active', '=', True)])
        return [{
            'id': b.id,
            'name': b.name,
            'code': b.code,
            'primary_color': b.primary_color,
            'secondary_color': b.secondary_color,
            'logo_svg': b.logo_svg,
        } for b in brands]
    
    @http.route('/brand/apply/<int:brand_id>', type='json', auth='user')
    def apply_brand(self, brand_id):
        """Apply a brand to the current website."""
        brand = request.env['deployable.brand'].browse(brand_id)
        if not brand.exists():
            return {'success': False, 'error': 'Brand not found'}
        
        website = request.website
        website.brand_id = brand
        
        return {
            'success': True,
            'brand_code': brand.code,
            'brand_name': brand.name
        }
