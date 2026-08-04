from odoo import api, fields, models

CARD_KINDS = [
    ("placed", "Placed"),
    ("started", "Started"),
    ("bumped", "Bumped"),
    ("recalled", "Recalled"),
    ("voided", "Voided"),
    ("comped", "Comped"),
]


class EhKdsCard(models.Model):
    """The placement of one item on one lane: the unit staff bump.

    A card has no mutable status flag. Its current lane and state are the
    projection of its latest bump event, which gives a durable audit trail and
    lets concurrent bumps be ordered by the server assigned event id rather than
    by comparing client clocks.
    """

    _name = "eh.kds.card"
    _description = "MiiG KDS Card"
    _order = "id"

    item_id = fields.Many2one("eh.kds.ticket.item", required=True, ondelete="cascade", index=True)
    lane_id = fields.Many2one("eh.kds.lane", required=True, ondelete="cascade", index=True)
    board_id = fields.Many2one(related="lane_id.board_id", store=True, index=True)
    ticket_id = fields.Many2one(related="item_id.ticket_id", store=True, index=True)
    bump_event_ids = fields.One2many("eh.kds.bump.event", "card_id", string="Bump Events")
    last_event_id = fields.Many2one("eh.kds.bump.event", compute="_compute_last_event")
    status = fields.Selection(CARD_KINDS, compute="_compute_last_event", string="Current status")

    @api.depends("bump_event_ids")
    def _compute_last_event(self):
        for card in self:
            last = card.bump_event_ids.sorted("id")[-1:] if card.bump_event_ids else card.bump_event_ids
            card.last_event_id = last
            card.status = last.kind if last else "placed"

    # -- event log -----------------------------------------------------------

    def _log(self, kind, from_lane=None, to_lane=None, reason=None, push=True):
        """Append a bump event for each card and optionally push it live."""
        Event = self.env["eh.kds.bump.event"].sudo()
        for card in self:
            Event.create(
                {
                    "card_id": card.id,
                    "kind": kind,
                    "from_lane_id": from_lane.id if from_lane else False,
                    "to_lane_id": (to_lane or card.lane_id).id if (to_lane or card.lane_id) else False,
                    "reason": reason,
                }
            )
            if push:
                card._push()
        return True

    # -- bump workflow -------------------------------------------------------

    def move_to(self, index, kind=None):
        """Move each card to an absolute lane index, clamped to the board.

        Absolute (not relative) so an offline replay converges: re applying the
        same target is a no op, which keeps a queued bump idempotent. Marks the
        ticket ready and stamps completion the first time every card reaches the
        ready lane. Bumping past the final lane clears the card off the board.
        """
        for card in self:
            order = list(card.board_id.lane_ids)
            if not order:
                continue
            current = order.index(card.lane_id) if card.lane_id in order else 0
            target = int(index)
            if target >= len(order):
                from_lane = card.lane_id
                card.lane_id = False
                card._log("bumped", from_lane=from_lane, to_lane=False, push=False)
                card._push()
                card.ticket_id._maybe_mark_ready()
                continue
            if target < 0:
                target = 0
            if target == current and card.lane_id:
                continue
            from_lane = card.lane_id
            card.lane_id = order[target]
            kind = kind or ("bumped" if target > current else "recalled")
            card._log(kind, from_lane=from_lane, to_lane=card.lane_id, push=False)
            card._push()
            card.ticket_id._maybe_mark_ready()
        return True

    def advance(self, direction=1):
        """Move each card one lane forward (1) or back (-1)."""
        for card in self:
            order = list(card.board_id.lane_ids)
            if order and card.lane_id in order:
                card.move_to(order.index(card.lane_id) + direction)
        return True

    def void(self, reason=None):
        for card in self:
            card._log("voided", reason=reason, push=True)
        return True

    # -- realtime ------------------------------------------------------------

    def _push(self):
        self.ensure_one()
        board = self.board_id
        if not board:
            return
        token = board.access_token
        board._kds_push(token, "kds.card", self._kds_payload())
        board._kds_push(token, "kds.status", {"ticket_ref": self.ticket_id.ticket_ref})

    def _placed_at(self):
        self.ensure_one()
        first = self.bump_event_ids.sorted("id")[:1]
        return first.create_date.isoformat() if first and first.create_date else False

    def _changed_at(self):
        self.ensure_one()
        last = self.bump_event_ids.sorted("id")[-1:]
        return last.create_date.isoformat() if last and last.create_date else False

    def _kds_payload(self):
        """Flat dict the board frontend renders. No reactivity, plain values."""
        self.ensure_one()
        item = self.item_id
        lanes = list(self.board_id.lane_ids)
        return {
            "id": self.id,
            "event_id": self.last_event_id.id or 0,
            "lane_id": self.lane_id.id if self.lane_id else False,
            "lane_index": lanes.index(self.lane_id) if self.lane_id and self.lane_id in lanes else -1,
            "status": self.status,
            "ticket_id": self.ticket_id.id,
            "ticket_ref": self.ticket_id.ticket_ref or str(self.ticket_id.id),
            "priority": self.ticket_id.priority,
            "product": item.product_id.display_name or "",
            "qty": item.quantity - item.cancelled,
            "note": item.customer_note or item.note or "",
            "allergen": item.allergen_flag,
            "is_combo_parent": bool(item.child_ids),
            "parent_item_id": item.parent_id.id or False,
            "placed_at": self._placed_at(),
            "changed_at": self._changed_at(),
        }
