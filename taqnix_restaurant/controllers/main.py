from odoo import http
from odoo.http import request
import json


class PosMobileAPI(http.Controller):

    @http.route('/api/v1/pos/branches', type='http', auth='public', methods=['GET', 'POST'], csrf=False, cors='*')
    def get_active_branches(self, **kwargs):
        """
        Fetches all POS configurations marked as active for the mobile app.
        Returns a JSON payload with branch details, coordinates, operational rules,
        branding, and social media links.
        """
        try:
            # sudo() is used because auth='public' means the user is not logged in yet.
            configs = request.env['pos.config'].sudo().search([
                ('is_active_for_mobile', '=', True)
            ])

            # Get the base URL of your Odoo server to construct full image links
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')

            branch_data = []
            for config in configs:

                if config.status != 'active':
                    continue
                # Generate a clean image URL instead of sending heavy Base64 data
                banner_url = ""
                if config.mobile_app_bar_banner:
                    banner_url = f"{base_url}/web/image/pos.config/{config.id}/mobile_app_bar_banner"

                branch_data.append({
                    'config_id': config.id,
                    'name': config.name,
                    'status': config.status,
                    # Routing & Location
                    'latitude': config.branch_latitude,
                    'longitude': config.branch_longitude,
                    'radius_km': config.delivery_radius_km,

                    # Operational Rules
                    'min_order_amount': config.minimum_order_amount,
                    'delivery_fee': config.delivery_fee,
                    'prep_time_minutes': config.preparation_time_minutes,
                    'whatsapp': config.branch_whatsapp or "",

                    # Branding & Social Links
                    'app_bar_banner_image_url': banner_url,
                    'social_links': {
                        'google_review': config.mobile_google_review_link or "",
                        'google_business': config.mobile_google_business_link or "",
                        'instagram': config.mobile_instagram_link or "",
                        'tiktok': config.mobile_tiktok_link or "",
                        'snapchat': config.mobile_snapchat_link or "",
                        'facebook': config.mobile_facebook_link or "",
                    }
                })

            response_payload = {
                'status': 'success',
                'data': branch_data
            }

            return request.make_response(
                json.dumps(response_payload),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            return request.make_response(
                json.dumps({
                    'status': 'error',
                    'message': str(e)
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )