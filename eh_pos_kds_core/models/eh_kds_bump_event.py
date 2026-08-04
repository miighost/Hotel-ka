from odoo import fields, models


class EhKdsBumpEvent(models.Model):
    """Append only log of everything that happens to a card.

    The record id is the monotonic sequence used to order updates across
    stations and to detect gaps on the client. Rows are never edited or deleted
    in normal operation; a reversal is a new ``recalled`` event.
    """

    _name = "eh.kds.bump.event"
    _description = "MiiG KDS Bump Event"
    _order = "id"

    card_id = fields.Many2one("eh.kds.card", required=True, ondelete="cascade", index=True)
    kind = fields.Selection(
        [
            ("placed", "Placed"),
            ("started", "Started"),
            ("bumped", "Bumped"),
            ("recalled", "Recalled"),
            ("voided", "Voided"),
            ("comped", "Comped"),
        ],
        required=True,
    )
    from_lane_id = fields.Many2one("eh.kds.lane", ondelete="set null")
    to_lane_id = fields.Many2one("eh.kds.lane", ondelete="set null")
    actor_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    reason = fields.Char(help="Free text reason, used for voids and comps.")
    note = fields.Char()
