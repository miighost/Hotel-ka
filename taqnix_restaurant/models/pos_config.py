from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # --- Existing Operational Fields ---
    is_active_for_mobile = fields.Boolean(string="Active for Mobile App", default=False)
    delivery_radius_km = fields.Float(string="Delivery Radius (KM)", default=5.0)
    branch_latitude = fields.Float(string="Latitude", digits=(10, 7))
    branch_longitude = fields.Float(string="Longitude", digits=(10, 7))
    minimum_order_amount = fields.Float(string="Min. Order Amount", default=0.0)
    preparation_time_minutes = fields.Integer(string="Prep Time (Minutes)", default=20)
    delivery_fee = fields.Float(string="Delivery Fee", default=0.0)
    branch_whatsapp = fields.Char(string="Branch WhatsApp")

    # --- NEW: Mobile App Branding & Social Fields ---
    mobile_app_bar_banner = fields.Binary(string="App Bar Banner Image")
    mobile_google_review_link = fields.Char(string="Google Review Link")
    mobile_google_business_link = fields.Char(string="Google My Business Link")
    mobile_instagram_link = fields.Char(string="Instagram Link")
    mobile_tiktok_link = fields.Char(string="TikTok Link")

    # ✅ Added Snapchat and Facebook
    mobile_snapchat_link = fields.Char(string="Snapchat Link", help="Crucial for GCC market engagement.")
    mobile_facebook_link = fields.Char(string="Facebook Link")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Existing location fields
    pos_is_active_for_mobile = fields.Boolean(related='pos_config_id.is_active_for_mobile', readonly=False)
    pos_delivery_radius_km = fields.Float(related='pos_config_id.delivery_radius_km', readonly=False)
    pos_branch_latitude = fields.Float(related='pos_config_id.branch_latitude', readonly=False)
    pos_branch_longitude = fields.Float(related='pos_config_id.branch_longitude', readonly=False)

    # Existing operational fields
    pos_minimum_order_amount = fields.Float(related='pos_config_id.minimum_order_amount', readonly=False)
    pos_preparation_time_minutes = fields.Integer(related='pos_config_id.preparation_time_minutes', readonly=False)
    pos_delivery_fee = fields.Float(related='pos_config_id.delivery_fee', readonly=False)
    pos_branch_whatsapp = fields.Char(related='pos_config_id.branch_whatsapp', readonly=False)

    # --- Related Branding & Social Fields ---
    pos_mobile_app_bar_banner = fields.Binary(related='pos_config_id.mobile_app_bar_banner', readonly=False)
    pos_mobile_google_review_link = fields.Char(related='pos_config_id.mobile_google_review_link', readonly=False)
    pos_mobile_google_business_link = fields.Char(related='pos_config_id.mobile_google_business_link', readonly=False)
    pos_mobile_instagram_link = fields.Char(related='pos_config_id.mobile_instagram_link', readonly=False)
    pos_mobile_tiktok_link = fields.Char(related='pos_config_id.mobile_tiktok_link', readonly=False)

    # ✅ Added Related Snapchat and Facebook
    pos_mobile_snapchat_link = fields.Char(related='pos_config_id.mobile_snapchat_link', readonly=False)
    pos_mobile_facebook_link = fields.Char(related='pos_config_id.mobile_facebook_link', readonly=False)