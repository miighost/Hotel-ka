from odoo import http
from odoo.http import request
import json


class PosPromotionController(http.Controller):

    # ==========================================
    # PRODUCTION ROUTES (For Flutter App)
    # ==========================================

    @http.route('/api/pos/wallet_balance', type='json', auth='user', methods=['POST'])
    def get_wallet_balance(self, **kwargs):
        """ Fetches the eWallet balance for the logged-in user """
        try:
            partner = request.env.user.partner_id
            wallets = request.env['loyalty.card'].sudo().search([
                ('partner_id', '=', partner.id),
                ('program_id.program_type', '=', 'ewallet')
            ])
            balance = sum(wallets.mapped('points'))
            return {'success': True, 'balance': balance}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/api/pos/validate_coupon', type='json', auth='user', methods=['POST'])
    def validate_coupon(self, code, config_id):
        """ Validates a promo code """
        try:
            coupon = request.env['loyalty.card'].sudo().search([('code', '=', code)], limit=1)
            if not coupon or not coupon.program_id.active:
                return {'success': False, 'message': 'Invalid or expired coupon code.'}

            program = coupon.program_id
            if program.pos_config_ids and int(config_id) not in program.pos_config_ids.ids:
                return {'success': False, 'message': 'Coupon not valid for this branch.'}

            reward = program.reward_ids[0] if program.reward_ids else None
            if not reward:
                return {'success': False, 'message': 'Coupon has no defined rewards.'}

            return {
                'success': True,
                'data': {
                    'code': coupon.code,
                    'type': reward.reward_type,
                    'discount': reward.discount,
                    'discount_mode': reward.discount_mode,
                    'name': program.name
                }
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ==========================================
    # BROWSER TESTING ROUTES (GET Methods)
    # ==========================================

    @http.route('/api/pos/test/wallet_balance', type='http', auth='user', methods=['GET'])
    def test_get_wallet_balance(self, **kwargs):
        """ Browser test for eWallet balance """
        try:
            partner = request.env.user.partner_id
            wallets = request.env['loyalty.card'].sudo().search([
                ('partner_id', '=', partner.id),
                ('program_id.program_type', '=', 'ewallet')
            ])
            balance = sum(wallets.mapped('points'))

            response_data = {'success': True, 'balance': balance}
        except Exception as e:
            response_data = {'success': False, 'error': str(e)}

        # For HTTP routes, you MUST format the response manually
        return request.make_response(
            json.dumps(response_data),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/api/pos/test/validate_coupon', type='http', auth='user', methods=['GET'])
    def test_validate_coupon(self, **kwargs):
        """ Browser test for Coupon Validation """

        # Extract query parameters from the URL (e.g. ?code=SALE10&config_id=1)
        code = kwargs.get('code')
        config_id = kwargs.get('config_id')

        if not code or not config_id:
            return request.make_response(
                json.dumps({'success': False, 'message': 'Missing ?code= or &config_id= parameters in URL.'}),
                headers=[('Content-Type', 'application/json')]
            )

        try:
            coupon = request.env['loyalty.card'].sudo().search([('code', '=', code)], limit=1)

            if not coupon or not coupon.program_id.active:
                response_data = {'success': False, 'message': 'Invalid or expired coupon code.'}
            else:
                program = coupon.program_id
                if program.pos_config_ids and int(config_id) not in program.pos_config_ids.ids:
                    response_data = {'success': False, 'message': 'Coupon not valid for this branch.'}
                else:
                    reward = program.reward_ids[0] if program.reward_ids else None
                    if not reward:
                        response_data = {'success': False, 'message': 'Coupon has no defined rewards.'}
                    else:
                        response_data = {
                            'success': True,
                            'data': {
                                'code': coupon.code,
                                'type': reward.reward_type,
                                'discount': reward.discount,
                                'discount_mode': reward.discount_mode,
                                'name': program.name
                            }
                        }
        except Exception as e:
            response_data = {'success': False, 'message': str(e)}

        # Return as HTTP JSON Response
        return request.make_response(
            json.dumps(response_data),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/api/pos/test/add_balance', type='http', auth='user', methods=['GET'])
    def test_add_wallet_balance(self, amount=100.0, **kwargs):
        """ Browser test to instantly add funds to the logged-in user's wallet """
        try:
            # Convert amount from URL to float
            amount_to_add = float(amount)
            partner = request.env.user.partner_id

            # 1. Find the active eWallet program in Odoo
            program = request.env['loyalty.program'].sudo().search([
                ('program_type', '=', 'ewallet')
            ], limit=1)

            if not program:
                return request.make_response(
                    json.dumps({'success': False,
                                'message': 'No eWallet program exists. Create one in POS > Products > eWallets.'}),
                    headers=[('Content-Type', 'application/json')]
                )

            # 2. Find the user's wallet, or create one if it doesn't exist
            wallet = request.env['loyalty.card'].sudo().search([
                ('partner_id', '=', partner.id),
                ('program_id', '=', program.id)
            ], limit=1)

            if not wallet:
                wallet = request.env['loyalty.card'].sudo().create({
                    'partner_id': partner.id,
                    'program_id': program.id,
                    'points': 0.0,
                })

            # 3. Add the funds
            wallet.points += amount_to_add

            response_data = {
                'success': True,
                'message': f'Successfully added {amount_to_add} to wallet!',
                'new_balance': wallet.points
            }

        except Exception as e:
            response_data = {'success': False, 'error': str(e)}

        return request.make_response(
            json.dumps(response_data),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/api/pos/wallet_history', type='json', auth='user', methods=['POST'])
    def get_wallet_history(self, **kwargs):
        """ Fetches the eWallet transaction history (Orders where wallet was used) """
        try:
            partner = request.env.user.partner_id

            # Find order lines where the wallet was used as payment
            # (Matches the 'eWallet Pay' product we created in place_order)
            wallet_lines = request.env['pos.order.line'].sudo().search([
                ('order_id.partner_id', '=', partner.id),
                ('product_id.name', 'in', ['eWallet Pay', 'eWallet Topup'])
            ], order='create_date desc', limit=20)

            history = []
            for line in wallet_lines:
                # In our place_order, eWallet Pay was a negative amount.
                # So we flip the sign for display purposes.
                amount = line.price_subtotal_incl
                is_deduction = amount < 0

                history.append({
                    'id': line.id,
                    'date': line.create_date.strftime('%b %d, %Y - %I:%M %p'),
                    'order_ref': line.order_id.pos_reference,
                    'amount': abs(amount),  # Make it positive for the UI
                    'type': 'Spent' if is_deduction else 'Added',
                    'description': 'Order Payment' if is_deduction else 'Wallet Top-up'
                })

            return {
                'success': True,
                'history': history,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}