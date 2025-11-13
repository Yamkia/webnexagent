// Brand Switcher Component (for admin preview)
odoo.define('deployable_brand_theme.brand_switcher', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    const ajax = require('web.ajax');

    publicWidget.registry.BrandSwitcher = publicWidget.Widget.extend({
        selector: '.brand-switcher',
        events: {
            'change select[name="brand_id"]': '_onBrandChange',
            'click .preview-brand': '_onPreviewBrand',
        },

        start: function () {
            this._super.apply(this, arguments);
            this._loadBrands();
        },

        _loadBrands: function () {
            const self = this;
            ajax.jsonRpc('/brand/api/list', 'call', {}).then(function (brands) {
                self._renderBrandOptions(brands);
            });
        },

        _renderBrandOptions: function (brands) {
            const $select = this.$('select[name="brand_id"]');
            $select.empty();
            $select.append('<option value="">-- Select Brand --</option>');
            brands.forEach(function (brand) {
                $select.append(
                    $('<option>')
                        .val(brand.id)
                        .text(brand.name)
                        .data('brand', brand)
                );
            });
        },

        _onBrandChange: function (ev) {
            const brandId = parseInt($(ev.currentTarget).val());
            if (!brandId) return;

            this._applyBrand(brandId);
        },

        _applyBrand: function (brandId) {
            const self = this;
            ajax.jsonRpc('/brand/apply/' + brandId, 'call', {}).then(function (result) {
                if (result.success) {
                    self._showNotification('Brand Applied', `${result.brand_name} is now active!`);
                    setTimeout(() => window.location.reload(), 1000);
                } else {
                    self._showNotification('Error', result.error, 'danger');
                }
            });
        },

        _onPreviewBrand: function (ev) {
            const brandId = this.$('select[name="brand_id"]').val();
            if (!brandId) {
                this._showNotification('No Brand Selected', 'Please select a brand first', 'warning');
                return;
            }
            window.open('/brand/preview/' + brandId, '_blank');
        },

        _showNotification: function (title, message, type = 'success') {
            // Simple notification (can be enhanced with a library)
            const alertClass = `alert-${type}`;
            const $alert = $(`
                <div class="alert ${alertClass} alert-dismissible fade show position-fixed" 
                     style="top: 20px; right: 20px; z-index: 9999; min-width: 300px;" 
                     role="alert">
                    <strong>${title}</strong> ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `);
            $('body').append($alert);
            setTimeout(() => $alert.remove(), 3000);
        },
    });

    return publicWidget.registry.BrandSwitcher;
});
