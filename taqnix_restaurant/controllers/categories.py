from odoo import http
from odoo.http import request
import json

class PosMobileCategoriesAPI(http.Controller):

    @http.route('/api/v1/pos/categories', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_pos_categories(self, **kwargs):
        """
        Fetches POS categories in a hierarchical tree.
        Translates names based on the ?lang= parameter.
        """
        try:
            base_url = request.httprequest.host_url.rstrip('/')

            # 1. Catch the language parameter from Flutter (default to English)
            lang = kwargs.get('lang', 'en_US')

            # 2. Inject the language into the Odoo Environment Context
            # This is the magic line that translates the 'name' field automatically
            CategoryEnv = request.env['pos.category'].sudo().with_context(lang=lang)

            # Check for config_id (Branch filtering)
            config_id = kwargs.get('config_id')
            is_limited = False
            allowed_category_ids = []

            if config_id:
                try:
                    config = request.env['pos.config'].sudo().browse(int(config_id))
                    if config.exists() and config.limit_categories and config.iface_available_categ_ids:
                        is_limited = True
                        allowed_category_ids = config.iface_available_categ_ids.ids
                except ValueError:
                    pass

            domain = [('parent_id', '=', False)]
            if is_limited:
                domain.append(('id', 'in', allowed_category_ids))

            # Use our translated CategoryEnv
            top_categories = CategoryEnv.search(domain)

            def build_category_tree(category):
                has_image = False
                if hasattr(category, 'image_128') and category.image_128:
                    has_image = True
                elif hasattr(category, 'has_image') and category.has_image:
                    has_image = True

                image_url = f"{base_url}/web/image/pos.category/{category.id}/image_512" if has_image else None

                child_domain = [('parent_id', '=', category.id)]
                if is_limited:
                    child_domain.append(('id', 'in', allowed_category_ids))

                child_categories = CategoryEnv.search(child_domain)

                return {
                    'id': category.id,
                    'name': category.name,  # This will now be in Arabic if lang=ar_001
                    'image_url': image_url,
                    'subcategories': [build_category_tree(child) for child in child_categories]
                }

            category_data = [build_category_tree(cat) for cat in top_categories]

            response_payload = {
                'status': 'success',
                'data': category_data
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