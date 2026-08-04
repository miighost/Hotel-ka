from odoo import fields, models


class EhKdsTicketItem(models.Model):
    """One product line on a ticket, with combo children nested under a parent.

    Removed quantity is absorbed into ``cancelled`` rather than deleting the
    row, so re adds are detected and the history stays intact.
    """

    _name = "eh.kds.ticket.item"
    _description = "MiiG KDS Ticket Item"
    _order = "id"

    ticket_id = fields.Many2one("eh.kds.ticket", required=True, ondelete="cascade", index=True)
    product_id = fields.Many2one("product.product", index=True)
    quantity = fields.Float(default=1.0)
    cancelled = fields.Float(default=0.0, help="Quantity voided. Never deleted, kept for audit.")
    pos_order_line_id = fields.Many2one("pos.order.line", ondelete="set null")
    pos_order_line_uuid = fields.Char(index=True, help="Stable key used to match re adds without duplicating.")
    note = fields.Char()
    customer_note = fields.Char()
    attribute_value_ids = fields.Many2many("product.template.attribute.value")
    parent_id = fields.Many2one("eh.kds.ticket.item", string="Combo Parent", ondelete="cascade")
    child_ids = fields.One2many("eh.kds.ticket.item", "parent_id", string="Combo Items")
    card_ids = fields.One2many("eh.kds.card", "item_id", string="Cards")
    allergen_flag = fields.Boolean(help="Highlighted in the board when set, for kitchen attention.")
    dietary_tag_ids = fields.Many2many("pos.category", relation="eh_kds_item_dietary_rel", string="Dietary Tags")
