from odoo import http
from odoo.http import request
import json

class PosMobileProductsAPI(http.Controller):

    @http.route('/api/v1/pos/products', type='http', auth='public', methods=['GET', 'POST'], csrf=False, cors='*')
    def get_pos_products(self, **kwargs):
        """
        Fetches Product Templates available in the POS.
        Supports pagination (limit, offset), sorting, search, and strict category filtering.
        """
        try:
            base_url = request.httprequest.host_url.rstrip('/')

            # 1. Parse the JSON body from Flutter
            try:
                if request.httprequest.data:
                    data = json.loads(request.httprequest.data)
                    kwargs.update(data)
            except Exception:
                pass  # Fallback to URL query parameters

            # 2. Setup Language Translation
            lang = kwargs.get('lang', 'en_US')
            ProductEnv = request.env['product.template'].sudo().with_context(lang=lang)

            # ==========================================
            # ✅ FIX 1: Prevent Uncategorized Products
            # ==========================================
            domain = [
                ('sale_ok', '=', True),
                ('available_in_pos', '=', True),
                ('pos_categ_ids', '!=', False) # <--- This hides products with no category
            ]

            # ==========================================
            # ✅ FIX 2: Branch / Config Filter (Includes Sub-categories)
            # ==========================================
            config_id = kwargs.get('config_id')
            if config_id:
                try:
                    config = request.env['pos.config'].sudo().browse(int(config_id))
                    if config.exists() and config.limit_categories and config.iface_available_categ_ids:
                        # Grab allowed categories PLUS all their children
                        allowed_categories = request.env['pos.category'].sudo().search([
                            ('id', 'child_of', config.iface_available_categ_ids.ids)
                        ])
                        domain.append(('pos_categ_ids', 'in', allowed_categories.ids))
                except ValueError:
                    pass

            # ==========================================
            # ✅ FIX 3: Category Filter (Includes Sub-categories)
            # ==========================================
            category_id = kwargs.get('category_id')
            if category_id:
                try:
                    # If user clicks a parent category, show products from child categories too
                    target_categories = request.env['pos.category'].sudo().search([
                        ('id', 'child_of', int(category_id))
                    ])
                    domain.append(('pos_categ_ids', 'in', target_categories.ids))
                except ValueError:
                    pass

            # TAG FILTERS (By ID or Name)
            tag_id = kwargs.get('tag_id')
            if tag_id:
                try:
                    domain.append(('product_tag_ids', 'in', [int(tag_id)]))
                except ValueError:
                    pass

            tag_name = kwargs.get('tag_name')
            if tag_name:
                domain.append(('product_tag_ids.name', 'ilike', tag_name))

            # Search Bar Filter
            keyword = kwargs.get('keyword') or kwargs.get('search')
            if keyword:
                domain.append(('name', 'ilike', keyword))

            # 3. Apply Sorting
            sort_by = kwargs.get('sort_by', 'newest')
            order_string = 'create_date desc'  # Default (Newest)
            if sort_by == 'price_asc':
                order_string = 'list_price asc'
            elif sort_by == 'price_desc':
                order_string = 'list_price desc'
            elif sort_by == 'popular':
                order_string = 'create_date desc'

            # 4. Apply Pagination (Limit & Offset)
            limit = int(kwargs.get('limit', 20))
            offset = int(kwargs.get('offset', 0))

            # Fetch templates using the translated environment with sorting & pagination
            templates = ProductEnv.search(domain, order=order_string, limit=limit, offset=offset)

            product_data = []
            for tmpl in templates:
                has_image = False
                if hasattr(tmpl, 'image_128') and tmpl.image_128:
                    has_image = True
                elif hasattr(tmpl, 'has_image') and tmpl.has_image:
                    has_image = True

                image_url = f"{base_url}/web/image/product.template/{tmpl.id}/image_512" if has_image else None

                # Variants
                variants_list = []
                for variant in tmpl.product_variant_ids:
                    variants_list.append({
                        'product_id': variant.id,
                        'name': variant.display_name,
                        'price': variant.lst_price,
                    })

                # Combos
                combos_list = []
                is_combo = False
                if hasattr(tmpl, 'type') and tmpl.type == 'combo' and hasattr(tmpl, 'combo_ids'):
                    is_combo = True
                    for combo in tmpl.combo_ids:
                        choices = []
                        items = getattr(combo, 'combo_item_ids', [])
                        for item in items:
                            choices.append({
                                'combo_item_id': item.id,
                                'product_id': item.product_id.id,
                                'name': item.product_id.display_name,
                                'price_extra': getattr(item, 'extra_price', 0.0),
                            })
                        combos_list.append({
                            'combo_id': combo.id,
                            'name': combo.name,
                            'choices': choices
                        })

                product_data.append({
                    'template_id': tmpl.id,
                    'name': tmpl.name,
                    'base_price': tmpl.list_price,
                    'description': tmpl.description_sale or "",
                    'image_url': image_url,
                    'pos_category_ids': tmpl.pos_categ_ids.ids,
                    'has_variants': len(tmpl.product_variant_ids) > 1 and not is_combo,
                    'variants': variants_list,
                    'is_combo': is_combo,
                    'combos': combos_list
                })

            response_payload = {
                'status': 'success',
                'count': len(product_data),
                'data': product_data
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