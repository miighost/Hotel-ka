from odoo import fields, models


class EhKdsLane(models.Model):
    """One column on a board. The pipeline of lanes defines the workflow.

    Lane position is relative: the first lane is where work enters, the last is
    completed, the one before last is the service handoff. Timing is derived
    from movement across these positions in Phase 1.
    """

    _name = "eh.kds.lane"
    _description = "MiiG KDS Lane"
    _order = "sequence, id"

    name = fields.Char(required=True)
    board_id = fields.Many2one("eh.kds.board", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    color = fields.Char(default="#6B7280")
    sla_minutes = fields.Integer(
        string="SLA target (minutes)",
        help="Cards older than this in this lane escalate. Zero disables the alert.",
    )
    alert_sound = fields.Selection(
        [
            ("none", "Silent"),
            ("chime", "Chime"),
            ("bell", "Bell"),
            ("urgent", "Urgent"),
        ],
        default="chime",
        required=True,
    )

    def lane_position(self):
        """Return the zero based forward index of this lane within its board."""
        self.ensure_one()
        return list(self.board_id.lane_ids).index(self)
