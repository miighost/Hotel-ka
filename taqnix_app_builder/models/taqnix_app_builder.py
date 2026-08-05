import requests
import base64
import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TaqnixAppBuilder(models.Model):
    _name = 'taqnix.app.client'
    _description = 'Taqnix App Builder Client'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Add this line

    # Core Sync Fields
    site_url = fields.Char(string="Site URL", required=True, help="The target WordPress/WooCommerce website domain URL to pull app content from.", tracking=True)
    database_name = fields.Char(string="Database Name")
    license_key = fields.Char(string="License Key", required=True, help="Your active product license key provided by Taqnix.", tracking=True)
    remote_build_id = fields.Integer(string="Remote Build ID", readonly=True, help="Unique identifier assigned to this app configuration by the Taqnix remote compiler service.", tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], string="Remote Status", default='draft', readonly=True, help="Current build generation status on the cloud compilation server.", tracking=True)

    # App Details
    name = fields.Char(string="App Name", help="The display name of your application as seen on mobile devices.", tracking=True)
    package_name = fields.Char(string="Package Name", help="The unique application identifier globally recognized by Android systems (e.g., com.company.appname).", tracking=True)
    consumer_key = fields.Char(string="Consumer Key", help="WooCommerce REST API Consumer Key (ck_...) generated from your website settings.")
    consumer_secret = fields.Char(string="Consumer Secret", help="WooCommerce REST API Consumer Secret (cs_...) generated from your website settings.")
    google_maps_api_key = fields.Char(string="Google Maps API Key", help="API key provided by Google Cloud Platform to render maps and location features inside the app.")
    facebook_app_name = fields.Char(string="Facebook App Name", help="The name of the app registered in the Meta/Facebook Developer Portal.")
    facebook_app_id = fields.Char(string="Facebook App ID", help="The application ID assigned by the Facebook developers platform.")
    facebook_client_token = fields.Char(string="Facebook Client Token", help="The client token located under Settings > Advanced inside your Facebook App dashboard.")
    build_type = fields.Selection([
        ('apk', 'APK'),
        ('appbundle', 'App Bundle')
    ], string="Build Type", default='apk', help="Choose 'APK' for manual testing or 'App Bundle (AAB)' for production releases to the Google Play Store.")
    splash_background_color = fields.Char(string="Splash Background Color", default="#ffffff", help="Hex color code for the screen background shown when launching the application.")

    # Contact Details
    email = fields.Char(string="Email", help="Support contact email encoded within the app build files.")
    phone = fields.Char(string="Phone", help="Customer support helpline string for app profiles.")
    country_code = fields.Char(string="Country Code", help="Two-letter ISO region indicator identifier (e.g., US, IN, GB).")

    # Files (Binary in Odoo)
    logo_file = fields.Binary(string="Logo (Image)", help="High-resolution global branding app asset image.")
    logo_file_name = fields.Char()
    icon_file = fields.Binary(string="Icon (1024x1024)", help="Standard master launch icon sized exactly to 1024x1024 pixels for App Stores.")
    icon_file_name = fields.Char()
    splash_file = fields.Binary(string="Splash Image", help="Launch visual cover graphic stretched to fill application boot view screens.")
    splash_file_name = fields.Char()
    google_service_json = fields.Binary(string="Google Service JSON", help="The configuration file ('google-services.json') exported directly from Firebase to enable cloud messaging and push notifications.")
    google_service_json_name = fields.Char()

    def _call_api_json(self, endpoint, params):
        """Helper to send standard JSON-RPC requests to the API."""
        url = f"https://apps.taqnix.com/taqnix/{endpoint}"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
            "id": None
        }
        try:
            response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            raise UserError(_("API Connection Error: %s") % str(e))

        if not data:
            raise UserError(_("Unable to decode API response."))

        if data.get("result") and isinstance(data["result"], dict) and data["result"].get("error"):
            raise UserError(data["result"]["error"])

        return data.get("result", {})

    def action_fetch_details(self):
        """Pulls the latest snapshot directly from the API backend, including all binary files."""
        self.ensure_one()
        if not self.site_url or not self.license_key:
            raise UserError(_("Site URL and License Key are required to fetch details."))

        # 1. Call the JSON-RPC route on the server
        result = self._call_api_json("fetch_details", {
            'site_url': self.site_url,
            'license_key': self.license_key,
        })

        # 2. Build the dictionary for standard fields
        vals = {
            'remote_build_id': result.get('id'),
            'name': result.get('name') or self.name,
            'package_name': result.get('package_name') or self.package_name,
            'db_placeholder': self.database,
            'state': result.get('state'),
            'consumer_key': result.get('consumer_key') or self.consumer_key,
            'consumer_secret': result.get('consumer_secret') or self.consumer_secret,
            'google_maps_api_key': result.get('google_maps_api_key') or self.google_maps_api_key,
            'facebook_app_name': result.get('facebook_app_name') or self.facebook_app_name,
            'facebook_app_id': result.get('facebook_app_id') or self.facebook_app_id,
            'facebook_client_token': result.get('facebook_client_token') or self.facebook_client_token,
            'build_type': result.get('build_type') or self.build_type,
            'splash_background_color': result.get('splash_background_color') or self.splash_background_color,
            'email': result.get('email') or self.email,
            'phone': result.get('phone') or self.phone,
        }

        # 3. Extract the binary file assets directly from the JSON payload keys
        if result.get('logo_file'):
            vals['logo_file'] = result.get('logo_file')

        if result.get('icon_file'):
            vals['icon_file'] = result.get('icon_file')

        if result.get('splash_file'):
            vals['splash_file'] = result.get('splash_file')

        if result.get('google_service_json'):
            vals['google_service_json'] = result.get('google_service_json')

        # 4. Write all values to the local Odoo database record
        self.write(vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Details and media assets fetched successfully.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def action_refresh_status(self):
        """Express button targeting state validation sync."""
        self.ensure_one()
        return self.action_fetch_details()

    def action_save_details(self):
        """Saves values and pushes assets via multipart wrapper streams."""
        self.ensure_one()
        if not self.remote_build_id:
            raise UserError(_("Please fetch details first to get a valid Build ID."))

        params = {
            'id': self.remote_build_id,
            'name': self.name,
            'license_key': self.license_key,
            'package_name': self.package_name,
            'site_url': self.site_url,
            'db_placeholder':self.database,
            'consumer_key': self.consumer_key,
            'consumer_secret': self.consumer_secret,
            'google_maps_api_key': self.google_maps_api_key,
            'facebook_app_name': self.facebook_app_name,
            'facebook_app_id': self.facebook_app_id,
            'facebook_client_token': self.facebook_client_token,
            'build_type': self.build_type,
            'splash_background_color': self.splash_background_color,
            'email': self.email,
            'phone': self.phone,
            'country_code': self.country_code
        }

        result = self._call_api_json("save_details", params)
        message = result.get("message", "Details saved successfully")
        self._sync_files_to_api()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def action_build_android(self):
        """Triggers the remote shell compilers."""
        self.ensure_one()
        if not self.remote_build_id or not self.license_key:
            raise UserError(_("Build ID and License Key are required."))

        result = self._call_api_json("build_android", {
            "id": self.remote_build_id,
            "license_key": self.license_key
        })

        message = result.get("message", "Build initiated successfully")
        self.state = 'pending'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Build Started'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def _sync_files_to_api(self):
        if self.logo_file:
            self._upload_single_file('logo', self.logo_file, self.logo_file_name or 'logo.png')
        if self.icon_file:
            self._upload_single_file('icon', self.icon_file, self.icon_file_name or 'icon.png')
        if self.splash_file:
            self._upload_single_file('splash', self.splash_file, self.splash_file_name or 'splash.png')
        if self.google_service_json:
            self._upload_single_file('googleservices', self.google_service_json,
                                     self.google_service_json_name or 'google-services.json')

    def _upload_single_file(self, file_type, base64_data, filename):
        url = "https://apps.taqnix.com/taqnix/upload_file"
        file_content = base64.b64decode(base64_data)
        data = {
            'jsonrpc': '2.0',
            'method': 'call',
            'params': json.dumps({'type': file_type, 'id': self.remote_build_id, 'license_key': self.license_key}),
            'id': self.remote_build_id,
            'type': file_type,
            'license_key': self.license_key
        }
        files = {'file': (filename, file_content)}
        try:
            response = requests.post(url, data=data, files=files, timeout=30)
            response.raise_for_status()
        except Exception as e:
            raise UserError(_("File Upload Error: %s") % str(e))

    def _fetch_remote_file(self, remote_id, field_name, is_image=True):
        """Fetches binary files directly from the remote Odoo instance."""
        # Use 'image' controller for visual assets, 'content' for raw files like JSON
        controller = "image" if is_image else "content"
        url = f"https://apps.taqnix.com/web/{controller}?model=taqnix.app.build&id={remote_id}&field={field_name}"

        try:
            response = requests.get(url, timeout=15)

            # If successful and the file isn't empty
            if response.status_code == 200 and response.content:
                # Odoo sometimes returns a 1x1 transparent GIF (around 43 bytes) if an image is missing.
                # We do a quick length check to ensure we are getting actual file data.
                if len(response.content) > 100:
                    return base64.b64encode(response.content)
        except requests.exceptions.RequestException:
            # Fail silently so a missing image doesn't crash the entire detail sync
            pass

        return False