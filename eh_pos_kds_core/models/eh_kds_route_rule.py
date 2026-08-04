from odoo import fields, models


class EhKdsRouteRule(models.Model):
    """A first class, queryable mapping from POS context to a board and lane.

    Rules are evaluated in order. An empty rule set on a board means the board
    catches everything (a global expo board). Optional attribute matching lets a
    line route to a specific station, for example a spice station, with a lane
    target. Because rules are rows, a manager can query which board makes what.
    """

    _name = "eh.kds.route.rule"
    _description = "MiiG KDS Routing Rule"
    _order = "sequence, id"

    board_id = fields.Many2one("eh.kds.board", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    pos_config_id = fields.Many2one("pos.config", help="Limit to one POS. Empty matches any.")
    category_id = fields.Many2one("pos.category", help="Limit to a product category. Empty matches any.")
    attribute_value_id = fields.Many2one(
        "product.template.attribute.value",
        help="Optional attribute match, for example a spicy variant.",
    )
    target_lane_id = fields.Many2one("eh.kds.lane", ondelete="set null", help="Force placement on this lane. Empty uses the first lane.")
    active = fields.Boolean(default=True)
