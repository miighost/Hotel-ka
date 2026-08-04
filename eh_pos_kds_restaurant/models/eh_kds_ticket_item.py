from odoo import fields, models


class EhKdsTicketItem(models.Model):
    _inherit = "eh.kds.ticket.item"

    eh_course_id = fields.Many2one("restaurant.order.course", string="Course", ondelete="set null")
    eh_course_index = fields.Integer(related="eh_course_id.index", store=True)
