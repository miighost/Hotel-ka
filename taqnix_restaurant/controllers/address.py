from odoo import http
from odoo.http import request
import json


class PosAddressController(http.Controller):

    @http.route('/api/pos/get_addresses', type='json', auth='user', methods=['POST'])
    def get_user_addresses(self, **kwargs):
        """ Fetch all delivery addresses for the logged-in user """
        try:
            partner = request.env.user.partner_id

            # We search for child partners of type 'delivery'
            addresses = request.env['res.partner'].sudo().search_read(
                domain=[
                    ('parent_id', '=', partner.id),
                    ('type', '=', 'delivery'),
                    ('active', '=', True)
                ],
                fields=['id', 'name', 'street', 'street2', 'city', 'phone', 'zip'],
                order='id desc'
            )

            return {'success': True, 'data': addresses}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/api/pos/add_address', type='json', auth='user', methods=['POST'])
    def add_user_address(self, name, street, street2=None, city=None, phone=None, zip_code=None):
        """ Create a new delivery address linked to the user's profile """
        try:
            partner = request.env.user.partner_id

            new_address = request.env['res.partner'].sudo().create({
                'parent_id': partner.id,
                'type': 'delivery',
                'name': name,  # e.g. "Home", "Office"
                'street': street,  # Street Name
                'street2': street2,  # Building/Apartment
                'city': city,
                'phone': phone,
                'zip': zip_code,
            })

            return {
                'success': True,
                'address_id': new_address.id,
                'message': 'Address saved successfully'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/api/pos/delete_address', type='json', auth='user', methods=['POST'])
    def delete_user_address(self, address_id):
        """ Archive an address (we use active=False to keep Odoo history intact) """
        try:
            partner = request.env.user.partner_id
            address = request.env['res.partner'].sudo().search([
                ('id', '=', address_id),
                ('parent_id', '=', partner.id)
            ])

            if not address:
                return {'success': False, 'error': 'Address not found'}

            # Archive instead of deleting to maintain database integrity
            address.active = False
            return {'success': True, 'message': 'Address removed'}
        except Exception as e:
            return {'success': False, 'error': str(e)}