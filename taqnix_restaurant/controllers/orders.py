from odoo import http
from odoo.http import request


class AppPosController(http.Controller):

    # ... (Keep your existing place_order endpoint here) ...

    @http.route('/api/v1/pos/my_orders', type='json', auth='user', methods=['POST'])
    def get_my_orders(self, **kwargs):
        try:
            partner = request.env.user.partner_id
            orders = request.env['pos.order'].sudo().search(
                [('partner_id', '=', partner.id)],
                order='date_order desc',
                limit=50
            )

            order_data = []
            for order in orders:
                item_summary = []
                lines_data = []  # ✅ NEW: Store individual items

                for line in order.lines:
                    item_summary.append(f"{int(line.qty)}x {line.product_id.name}")
                    lines_data.append({
                        'product_id': line.product_id.id,
                        'product_name': line.product_id.name,
                        'qty': float(line.qty),
                        'price_unit': float(line.price_unit),
                        'price_subtotal_incl': float(line.price_subtotal_incl),
                        'instructions': line.customer_note or "",
                    })

                status = "Processing"
                if order.state in ['paid', 'done', 'invoiced']:
                    status = "Completed"
                elif order.state == 'cancel':
                    status = "Cancelled"

                date_str = order.date_order.strftime("%d %b %Y, %I:%M %p") if order.date_order else "Unknown Date"

                order_data.append({
                    'id': order.id,
                    'reference': order.pos_reference or order.name or f"Order #{order.id}",
                    'date': date_str,
                    'total': float(order.amount_total),
                    'tax': float(order.amount_tax),  # ✅ NEW: Needed for receipt
                    'status': status,
                    'items_summary': ", ".join(item_summary) if item_summary else "Custom Items",
                    'item_count': len(order.lines),
                    'lines': lines_data  # ✅ NEW: Pass lines to Flutter
                })

            return {'success': True, 'data': order_data}

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"MY ORDERS API ERROR: {str(e)}")
            return {'success': False, 'error': str(e)}