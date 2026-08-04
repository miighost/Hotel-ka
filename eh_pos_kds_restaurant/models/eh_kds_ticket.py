from odoo import fields, models


class EhKdsTicket(models.Model):
    _inherit = "eh.kds.ticket"

    eh_table_id = fields.Many2one("restaurant.table", string="Table", index="btree_not_null")
