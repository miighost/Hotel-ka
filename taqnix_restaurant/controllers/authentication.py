# -*- coding: utf-8 -*-
from ast import literal_eval
from odoo import http, _
from odoo.http import request, Response
from odoo.addons.auth_signup.models.res_partner import SignupError
import json
import hashlib

def _portal_template_user(env):
    template_user_id = literal_eval(
        env['ir.config_parameter'].sudo().get_param('base.template_portal_user_id', 'False')
    )
    if not template_user_id:
        return None
    template_user = env['res.users'].sudo().browse(template_user_id)
    return template_user if template_user.exists() else None


def _payload(kwargs):
    """
    Works for:
    - type='json' (Odoo JSON routes)
    - type='http' with JSON body or form/query params
    """
    data = dict(kwargs or {})
    if not data:
        try:
            data = request.httprequest.get_json(silent=True) or {}
        except Exception:
            data = {}
    return data.get('params', data)


def _current_db():
    try:
        return request.env.cr.dbname
    except Exception:
        pass
    return getattr(request.session, 'db', None) or getattr(request, 'db', None)


def _session_authenticate(login, password):
    """
    Authenticate current HTTP session using the Odoo 19 style:

        request.session.authenticate(request.env, credential_dict)

    Returns the full auth_info dict (with uid, etc.) if available,
    or whatever authenticate() returns.
    """
    credential = {
        'login': login,
        'password': password,
        'type': 'password',  # same as auth_signup style
    }
    auth_info = request.session.authenticate(request.env, credential)
    return auth_info


class PosAuthController(http.Controller):

    # ---------------------------------------------------------------------
    # REGISTER (type='json' – same logic as test_register, no groups_id)
    # ---------------------------------------------------------------------
    # ---------------------------------------------------------------------
    # REGISTER (HTTP endpoint, JSON body & JSON response)
    # ---------------------------------------------------------------------
    # ---------------------------------------------------------------------
    # REGISTER (JSON-RPC for Flutter callRPC)
    # ---------------------------------------------------------------------
    @http.route('/pos/api/auth/signup', type='json', auth='public', methods=['POST'], csrf=False)
    def register(self, **kw):
        # When type='json', Odoo automatically parses params into 'kw'
        try:
            # 1. Extract Data
            name = kw.get('name')
            # Flutter sends 'email', Odoo uses it as 'login'
            login = kw.get('email') or kw.get('login')
            password = kw.get('password')
            phone = kw.get('phone')
            lang = kw.get('lang', 'en_US')

            # 2. Validation
            if not name or not login or not password:
                return {'success': False, 'message': _('Missing name, email, or password.')}

            if '@' not in login:
                return {'success': False, 'message': _('Invalid email format.')}

            User = request.env['res.users'].sudo()
            if User.search([('login', '=', login)], limit=1):
                return {'success': False, 'message': _('Email already exists.')}

            # 3. Get Template User
            template_user = _portal_template_user(request.env)
            if not template_user:
                return {'success': False, 'message': _('Portal template not configured.')}

            # 4. Prepare Values
            values = {
                'name': name,
                'login': login,
                'email': login,
                'password': password,
                'lang': lang,
                'active': True,
            }
            if phone:
                values['phone'] = phone

            # 5. Create User
            try:
                with request.env.cr.savepoint():
                    new_user = template_user.with_context(no_reset_password=True).copy(values)
            except Exception as e:
                return {'success': False, 'message': str(e)}

            # 6. Auto Login (Get Session ID)
            uid = _session_authenticate(login, password)

            if uid:
                return {
                    'success': True,
                    'message': 'User registered successfully',
                    'session_id': request.session.sid,  # Important for Flutter
                    'user': {
                        'id': new_user.id,
                        'name': new_user.name,
                        'login': new_user.login,
                    }
                }
            else:
                return {'success': False, 'message': 'User created but login failed.'}

        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ---------------------------------------------------------------------
    # LOGIN (uses _session_authenticate with request.env + credential dict)
    # ---------------------------------------------------------------------
    # ---------------------------------------------------------------------
    # LOGIN (HTTP endpoint, JSON body & JSON response)
    # ---------------------------------------------------------------------
    @http.route('/pos/api/auth/login', type='http', auth='public', csrf=False, methods=['POST'])
    def login(self, **kw):
        payload = _payload(kw)
        try:
            # Flutter sends "username" + "password"
            login_val = (payload.get('username') or '').strip()
            password = payload.get('password') or ''

            if not login_val or not password:
                data = {'success': False, 'message': _('Username and password are required.')}
                return Response(json.dumps(data), status=200,
                                headers=[('Content-Type', 'application/json; charset=utf-8')])

            user = request.env['res.users'].sudo().search([('login', '=', login_val)], limit=1)
            if not user:
                data = {'success': False, 'message': _('User not found')}
                return Response(json.dumps(data), status=200,
                                headers=[('Content-Type', 'application/json; charset=utf-8')])

            auth_info = _session_authenticate(login_val, password)
            uid = auth_info.get('uid') if isinstance(auth_info, dict) else auth_info

            if uid:
                data = {
                    'success': True,
                    'message': _('Login successful'),
                    'user': {
                        'id': user.id,
                        'name': user.name,
                        'email': user.email,
                        'login': user.login,
                    },
                    'session_id': request.session.sid,
                }
            else:
                data = {'success': False, 'message': _('Invalid credentials')}

        except Exception as e:
            data = {'success': False, 'message': _('Error: %s') % str(e)}

        return Response(
            json.dumps(data),
            status=200,
            headers=[('Content-Type', 'application/json; charset=utf-8')]
        )

    @http.route('/pos/api/auth/logout', type='http', methods=['GET'], csrf=False, auth="none")
    def logout(self, **kw):
        """
        HTTP endpoint to log out the current user.

        Returns a JSON response indicating whether the user was successfully logged out.

        Example Response:
            {
                "success": True,
                "message": "Logged out successfully"
            }
        """
        try:
            # Log out the current session.
            request.session.logout()
            result = {
                'success': True,
                'message': 'Logged out successfully'
            }
        except Exception as e:
            result = {
                'success': False,
                'message': 'Error during logout: ' + str(e)
            }
        return request.make_response(
            json.dumps(result),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/pos/api/auth/current_user', type='http', methods=['GET'], auth='none', csrf=False)
    def user_info(self, **kw):
        """
        HTTP endpoint to get information about the currently logged in user,
        returning user info in the same format as the login endpoint.

        Success Response:
        {
            "id": 1,
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "administrator",
            "username": "user@example.com",
            "billing": {
                "first_name": "John",
                "last_name": "Doe",
                "company": "",
                "address_1": "Street name",
                "address_2": "Apartment number",
                "city": "City",
                "postcode": "12345",
                "country": "US",
                "state": "CA",
                "email": "user@example.com",
                "phone": "+11234567890"
            },
            "shipping": {
                "first_name": "",
                "last_name": "",
                "company": "",
                "address_1": "",
                "address_2": "",
                "city": "",
                "postcode": "",
                "country": "",
                "state": "",
                "phone": ""
            },
            "is_paying_customer": false,
            "orders_count": 6,
            "total_spent": "4037.86",
            "avatar_url": "https://secure.gravatar.com/avatar/60a49d8ac134e1eda4aeec76229e7cbb?s=96&d=mm&r=g",
            "nonce": {"woo_wallet_topup": "f227e715d7"},
            "balance": 1520
        }

        Error Response (if no user is logged in):
        {"success": false, "data": {"message": "User not logged in"}}
        """
        # Check if the session has a logged in user.
        if not request.session.uid:
            error_response = {"success": False, "data": {"message": "User not logged in"}}
            return request.make_response(
                json.dumps(error_response),
                status=400,
                headers=[('Content-Type', 'application/json')]
            )

        uid = request.session.uid
        user = request.env['res.users'].sudo().browse(uid)
        if not user.exists():
            error_response = {"success": False, "data": {"message": "User not found"}}
            return request.make_response(
                json.dumps(error_response),
                status=404,
                headers=[('Content-Type', 'application/json')]
            )

        # Build the user data in the same format as the login endpoint.
        email = user.email or user.login
        partner = user.partner_id

        # Derive first and last names from partner name (if available).
        if partner.name:
            names = partner.name.split(' ', 1)
            first_name = names[0]
            last_name = names[1] if len(names) > 1 else ''
        else:
            first_name = ''
            last_name = ''

        # Determine role based on group membership.
        role = "administrator" if user.has_group('base.group_system') else "customer"
        username = user.login

        billing = {
            'first_name': first_name,
            'last_name': last_name,
            'company': partner.parent_id.name if partner.parent_id else '',
            'address_1': partner.street or '',
            'address_2': partner.street2 or '',
            'city': partner.city or '',
            'postcode': partner.zip or '',
            'country': partner.country_id.code if partner.country_id else '',
            'state': partner.state_id.code if partner.state_id else '',
            'email': partner.email or email,
            'phone': partner.phone or '',
        }

        shipping = {
            'first_name': '',
            'last_name': '',
            'company': '',
            'address_1': '',
            'address_2': '',
            'city': '',
            'postcode': '',
            'country': '',
            'state': '',
            'phone': '',
        }

        # Retrieve sale orders in 'sale' or 'done' states.
        orders = request.env['sale.order'].sudo().search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['sale', 'done'])
        ])
        orders_count = len(orders)
        total_spent = sum(order.amount_total for order in orders)
        total_spent_str = "{:.2f}".format(total_spent)

        # Compute avatar URL using Gravatar.
        email_lower = email.lower().strip().encode('utf-8')
        gravatar_hash = hashlib.md5(email_lower).hexdigest()
        avatar_url = f"https://secure.gravatar.com/avatar/{gravatar_hash}?s=96&d=mm&r=g"

        nonce = {"woo_wallet_topup": "f227e715d7"}
        balance = getattr(partner, 'wallet_balance', 0)

        response_data = {
            "id": user.id,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "role": role,
            "username": username,
            "billing": billing,
            "shipping": shipping,
            "is_paying_customer": False,
            "orders_count": orders_count,
            "total_spent": total_spent_str,
            "avatar_url": avatar_url,
            "nonce": nonce,
            "balance": balance,
        }

        return Response(
            json.dumps(response_data),
            status=200,
            headers=[('Content-Type', 'application/json; charset=utf-8')]
        )

    @http.route('/pos/api/auth/update', type='http', methods=['POST'], auth='user', csrf=False)
    def update_user(self, **kw):
        """
        HTTP endpoint to update the current user's information.

        Expected POST parameters:
            - name (optional): New name for the user.
            - email (optional): New email address.
            - phone (optional): New phone number.
            - mobile (optional): New mobile number.
            - password (optional): New password.

        Returns:
            JSON response indicating success or failure.

        Example Successful Response:
            {
                "success": True,
                "message": "User updated successfully"
            }
        """
        uid = request.session.uid
        user = request.env['res.users'].sudo().browse(uid)
        if not user.exists():
            return request.make_response(
                json.dumps({'success': False, 'message': 'User not found'}),
                headers=[('Content-Type', 'application/json')],
                status=404
            )

        # Gather fields from POST request to update.
        update_vals = {}
        name = kw.get('name')
        email = kw.get('email')
        phone = kw.get('phone')
        mobile = kw.get('mobile')
        password = kw.get('password')

        if name:
            update_vals['name'] = name
        if email:
            update_vals['email'] = email
        if phone:
            update_vals['phone'] = phone
        if mobile:
            update_vals['mobile'] = mobile
        if password:
            update_vals['password'] = password

        if not update_vals:
            return request.make_response(
                json.dumps({'success': False, 'message': 'No fields to update provided'}),
                headers=[('Content-Type', 'application/json')],
                status=400
            )

        try:
            # Update the user record.
            user.sudo().write(update_vals)

            # Optionally update the partner record's email if email was updated.
            if email:
                user.partner_id.sudo().write({'email': email})

            result = {'success': True, 'message': 'User updated successfully'}
            return request.make_response(
                json.dumps(result),
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            result = {'success': False, 'message': 'Error: ' + str(e)}
            return request.make_response(
                json.dumps(result),
                headers=[('Content-Type', 'application/json')],
                status=400
            )