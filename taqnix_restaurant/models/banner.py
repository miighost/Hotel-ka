from odoo import models, fields

class RestoAppBanner(models.Model):
    _name = 'resto.app.banner'
    _description = 'Restaurant Mobile App Banner'
    _order = 'sequence, id'

    name = fields.Char(string='Title', required=True, translate=True)
    subtitle = fields.Char(string='Subtitle', translate=True)

    # ✅ NEW: Link banner to a specific POS Branch
    pos_config_id = fields.Many2one(
        'pos.config',
        string='POS Branch',
        help="Select a branch. Leave empty to show this banner to all users."
    )

    image_1920 = fields.Image(string='Banner Image (Default)')
    image_ar_1920 = fields.Image(string='Banner Image (Arabic)', help="Optional specific image for Arabic users")

    hex_color = fields.Char(string='Hex Color', default='#FF5722') # Default Restaurant Orange
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    click_action = fields.Selection([
        ('none', 'No Action'),
        ('category', 'Open Category'),
        ('product', 'Open Product Detail'),
        ('url', 'Open Web URL')
    ], string='On Click', default='none')

    target_id = fields.Integer(string='Target ID')
    target_url = fields.Char(string='Web URL')