from odoo import http
from odoo.http import request


class RestoBannersController(http.Controller):

    @http.route('/api/v1/pos/banners', type='json', auth='public', methods=['POST'], csrf=False)
    def get_banners(self, **kw):
        lang_code = kw.get('lang') or 'en_US'
        pos_config_id = kw.get('pos_config_id')

        # Normalize Language
        if lang_code in ('ar', 'ar_SA'):
            odoo_lang = 'ar_001'
        elif lang_code == 'en':
            odoo_lang = 'en_US'
        else:
            odoo_lang = lang_code

        Banner = request.env['resto.app.banner'].sudo().with_context(lang=odoo_lang)

        # ✅ Domain: Show active banners that either belong to this branch OR have no branch assigned
        domain = [('active', '=', True)]
        if pos_config_id:
            domain += ['|', ('pos_config_id', '=', False), ('pos_config_id', '=', int(pos_config_id))]
        else:
            domain += [('pos_config_id', '=', False)]

        banners = Banner.search(domain)
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        data = []

        for b in banners:
            image_field = 'image_1920'
            if odoo_lang.startswith('ar') and b.image_ar_1920:
                image_field = 'image_ar_1920'

            has_image = getattr(b, image_field)
            image_url = f"{base_url}/web/image/resto.app.banner/{b.id}/{image_field}" if has_image else None

            data.append({
                'id': b.id,
                'title': b.name,
                'subtitle': b.subtitle or '',
                'image_url': image_url,
                'color': b.hex_color or '#FF5722',
                'action_type': b.click_action,
                'target_id': b.target_id or 0,
                'target_url': b.target_url or '',
            })

        return {'status': 'success', 'data': data}