from odoo import http
from odoo.http import request
import json


class PosCartController(http.Controller):

    @http.route('/api/pos/place_order', type='json', auth='user', methods=['POST'])
    def place_pos_order(self, lines, config_id=None, amount_total=0.0, amount_tax=0.0, coupon_code=None,
                        use_wallet=False, delivery_fee=0.0, address_id=None, **kwargs):
        if not lines:
            return {'success': False, 'error': 'Cart is empty'}

        PosConfig = request.env['pos.config'].sudo()

        if config_id:
            config = PosConfig.browse(config_id)
        else:
            config = PosConfig.search([('is_active_for_mobile', '=', True), ('active', '=', True)], limit=1)

        if not config:
            return {'success': False, 'error': 'No mobile-enabled POS Configuration found in Odoo.'}

        session = config.current_session_id
        if not session or session.state != 'opened':
            session = request.env['pos.session'].sudo().search([
                ('config_id', '=', config.id),
                ('state', '=', 'opened')
            ], limit=1)

        if not session:
            return {'success': False,
                    'error': f'No open POS session found for {config.name}. Please open the register first.'}

        order_lines = []
        calculated_amount_tax = 0.0
        calculated_amount_total = 0.0

        # ==========================================
        # 1. PROCESS STANDARD CART ITEMS (DO THIS FIRST!)
        # ==========================================
        for item in lines:
            # ✅ FIX: Safely determine the actual product.product record
            variant_id = item.get('variant_id')
            template_id = item.get('template_id')
            fallback_id = item.get('product_id')

            product = request.env['product.product'].sudo()

            if variant_id:
                product = product.browse(variant_id)
            elif template_id:
                template = request.env['product.template'].sudo().browse(template_id)
                if template.exists():
                    product = template.product_variant_id  # Gets the default variant for this template
            elif fallback_id:
                product = product.browse(fallback_id)

            if not product or not product.exists():
                return {'success': False, 'error': f"Product not found for: {item.get('name')}"}

            qty = item.get('qty', 1)
            price_unit = item.get('price_unit', 0.0)

            taxes = product.taxes_id.filtered(lambda t: t.company_id.id == session.company_id.id)
            if config.default_fiscal_position_id:
                taxes = config.default_fiscal_position_id.map_tax(taxes)

            tax_res = taxes.compute_all(price_unit, session.currency_id, qty, product=product)
            price_subtotal = tax_res['total_excluded']
            price_subtotal_incl = tax_res['total_included']

            calculated_amount_total += price_subtotal_incl
            calculated_amount_tax += sum(t.get('amount', 0.0) for t in tax_res['taxes'])

            order_lines.append((0, 0, {
                'product_id': product.id,  # Now strictly a product.product ID
                'qty': qty,
                'price_unit': price_unit,
                'price_subtotal': price_subtotal,
                'price_subtotal_incl': price_subtotal_incl,
                'tax_ids': [(6, 0, taxes.ids)],
                'tax_ids_after_fiscal_position': [(6, 0, taxes.ids)],
                'full_product_name': item.get('name', product.name),
                'customer_note': item.get('instructions', ''),
            }))

        # ==========================================
        # 2. PROCESS DELIVERY FEE
        # ==========================================
        if delivery_fee > 0:
            delivery_product = request.env['product.product'].sudo().search([('name', '=', 'Delivery Fee')], limit=1)
            if not delivery_product:
                delivery_product = request.env['product.product'].sudo().create({
                    'name': 'Delivery Fee', 'type': 'service', 'available_in_pos': True, 'list_price': delivery_fee,
                    'taxes_id': False,
                })

            del_taxes = delivery_product.taxes_id.filtered(lambda t: t.company_id.id == session.company_id.id)
            if config.default_fiscal_position_id:
                del_taxes = config.default_fiscal_position_id.map_tax(del_taxes)

            del_tax_res = del_taxes.compute_all(delivery_fee, session.currency_id, 1, product=delivery_product)
            del_subtotal = del_tax_res['total_excluded']
            del_subtotal_incl = del_tax_res['total_included']

            calculated_amount_total += del_subtotal_incl
            calculated_amount_tax += sum(t.get('amount', 0.0) for t in del_tax_res['taxes'])

            order_lines.append((0, 0, {
                'product_id': delivery_product.id,
                'qty': 1,
                'price_unit': delivery_fee,
                'price_subtotal': del_subtotal,
                'price_subtotal_incl': del_subtotal_incl,
                'tax_ids': [(6, 0, del_taxes.ids)],
                'tax_ids_after_fiscal_position': [(6, 0, del_taxes.ids)],
                'full_product_name': 'Delivery Fee',
            }))

        # ==========================================
        # 3. APPLY COUPON DISCOUNT (After total is calculated)
        # ==========================================
        if coupon_code:
            coupon = request.env['loyalty.card'].sudo().search([('code', '=', coupon_code)], limit=1)
            if coupon and coupon.program_id.reward_ids:
                reward = coupon.program_id.reward_ids[0]
                discount_amt = 0.0
                if reward.discount_mode == 'percent':
                    discount_amt = calculated_amount_total * (reward.discount / 100)
                elif reward.discount_mode == 'per_order':
                    discount_amt = reward.discount

                if discount_amt > 0:
                    discount_amt = min(discount_amt, calculated_amount_total)
                    calculated_amount_total -= discount_amt

                    discount_product = reward.discount_line_product_id
                    if not discount_product:
                        discount_product = request.env['product.product'].sudo().search([('name', '=', 'Discount')],
                                                                                        limit=1)
                        if not discount_product:
                            discount_product = request.env['product.product'].sudo().create(
                                {'name': 'Discount', 'type': 'service', 'available_in_pos': True, 'list_price': 0.0,
                                 'taxes_id': False})

                    order_lines.append((0, 0, {
                        'product_id': discount_product.id,
                        'qty': 1,
                        'price_unit': -discount_amt,
                        'price_subtotal': -discount_amt,
                        'price_subtotal_incl': -discount_amt,
                        'tax_ids': [(5, 0, 0)],
                        'tax_ids_after_fiscal_position': [(5, 0, 0)],
                        'full_product_name': f'Discount ({coupon_code})',
                    }))

        # ==========================================
        # 4. APPLY WALLET PAYMENT
        # ==========================================
        if use_wallet:
            partner = request.env.user.partner_id
            wallets = request.env['loyalty.card'].sudo().search([
                ('partner_id', '=', partner.id),
                ('program_id.program_type', '=', 'ewallet')
            ])
            available_balance = sum(wallets.mapped('points'))

            if available_balance > 0:
                wallet_used = min(available_balance, calculated_amount_total)
                if wallets:
                    wallets[0].points -= wallet_used
                calculated_amount_total -= wallet_used

                wallet_product = request.env['product.product'].sudo().search([('name', '=', 'eWallet Pay')], limit=1)
                if not wallet_product:
                    wallet_product = request.env['product.product'].sudo().create(
                        {'name': 'eWallet Pay', 'type': 'service', 'available_in_pos': True, 'list_price': 0.0,
                         'taxes_id': False})

                order_lines.append((0, 0, {
                    'product_id': wallet_product.id,
                    'qty': 1,
                    'price_unit': -wallet_used,
                    'price_subtotal': -wallet_used,
                    'price_subtotal_incl': -wallet_used,
                    'tax_ids': [(5, 0, 0)],
                    'tax_ids_after_fiscal_position': [(5, 0, 0)],
                    'full_product_name': 'Paid via eWallet',
                }))

        # ==========================================
        # 5. CREATE ORDER
        # ==========================================
        try:
            order_vals = {
                'session_id': session.id,
                'partner_id': request.env.user.partner_id.id,
                'lines': order_lines,
                'amount_total': calculated_amount_total,
                'amount_tax': calculated_amount_tax,
                'amount_paid': 0.0,
                'amount_return': 0.0,
            }
            # if address_id:
            #     order_vals['partner_shipping_id'] = address_id

            order = request.env['pos.order'].sudo().create(order_vals)

            return {'success': True, 'order_id': order.id, 'order_reference': order.pos_reference}
        except Exception as e:
            return {'success': False, 'error': str(e)}