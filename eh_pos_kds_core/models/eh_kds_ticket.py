from odoo import api, fields, models


class EhKdsTicket(models.Model):
    """One kitchen ticket per POS order seen by the kitchen.

    A ticket holds the items routed from a POS order. It is created by the
    intake engine (Phase 1) and never silently deleted: removed quantity is
    absorbed onto the item and logged as a bump event for audit.
    """

    _name = "eh.kds.ticket"
    _description = "MiiG KDS Ticket"
    _inherit = ["eh.kds.bus.mixin"]
    _order = "id desc"

    pos_order_id = fields.Many2one("pos.order", ondelete="cascade", index=True)
    ticket_ref = fields.Char(string="Reference", help="Tracking number or order name shown to staff and customers.")
    item_ids = fields.One2many("eh.kds.ticket.item", "ticket_id", string="Items")
    priority = fields.Selection(
        [
            ("normal", "Normal"),
            ("rush", "Rush"),
            ("vip", "VIP"),
        ],
        default="normal",
        required=True,
    )
    completion_time = fields.Integer(
        string="Completion time (minutes)",
        help="Derived from the bump event log when the ticket is fully completed.",
    )
    customer_note = fields.Char()
    internal_note = fields.Char()

    @api.model
    def _cron_gc(self):
        """Stub for the cleanup cron. Phase 1 prunes completed tickets older
        than a day. Kept as a no op so the cron definition is valid on install.
        """
        return True

    def _open_cards(self):
        self.ensure_one()
        return self.item_ids.card_ids.filtered(lambda c: c.status != "voided")

    def _maybe_mark_ready(self):
        """Stamp completion_time the first time every open card of the ticket has
        reached the ready lane (the one before last). Drives the ETA history.
        """
        self.ensure_one()
        if self.completion_time:
            return
        cards = self._open_cards()
        if not cards:
            return
        boards = cards.board_id
        for board in boards:
            lanes = list(board.lane_ids)
            if len(lanes) < 2:
                continue
            ready_index = len(lanes) - 2
            board_cards = cards.filtered(lambda c: c.board_id == board)
            if any(lanes.index(c.lane_id) < ready_index for c in board_cards):
                return
        first_event = cards.bump_event_ids.sorted("id")[:1]
        if first_event and first_event.create_date:
            delta = fields.Datetime.now() - first_event.create_date
            self.completion_time = max(1, int(delta.total_seconds() / 60))
        if any(b.notify_on_ready or b.notify_sms_on_ready or b.notify_webhook_url for b in boards):
            self._notify_ready(boards)

    def _notify_ready(self, boards):
        """Tell the order customer it is ready, across the channels the boards
        enable: email, SMS, and a bring-your-own webhook. Every channel is best
        effort and gracefully degrading: a missing address, a missing optional
        app, or a provider error never breaks the bump flow.
        """
        self.ensure_one()
        import logging

        _log = logging.getLogger(__name__)
        partner = self.pos_order_id.partner_id if self.pos_order_id else False
        ref = self.ticket_ref or str(self.id)

        if any(b.notify_on_ready for b in boards) and partner and partner.email:
            try:
                self.env["mail.mail"].sudo().create(
                    {
                        "subject": self.env._("Order %s is ready", ref),
                        "email_to": partner.email,
                        "body_html": self.env._(
                            "<p>Hello %(name)s,</p><p>Your order <strong>%(ref)s</strong> is ready for collection.</p>",
                            name=partner.name or "",
                            ref=ref,
                        ),
                        "auto_delete": True,
                    }
                ).send()
            except Exception:  # noqa: BLE001
                _log.exception("eh_pos_kds: ready email failed for ticket %s", self.id)

        if any(b.notify_sms_on_ready for b in boards) and partner and partner.mobile and "sms.sms" in self.env:
            try:
                self.env["sms.sms"].sudo().create(
                    {
                        "partner_id": partner.id,
                        "number": partner.mobile,
                        "body": self.env._("Your order %s is ready for collection.", ref),
                    }
                ).send()
            except Exception:  # noqa: BLE001
                _log.exception("eh_pos_kds: ready SMS failed for ticket %s", self.id)

        for url in {b.notify_webhook_url for b in boards if b.notify_webhook_url}:
            try:
                import requests

                requests.post(
                    url,
                    json={
                        "event": "order_ready",
                        "ref": ref,
                        "ticket_id": self.id,
                        "customer": partner.name if partner else None,
                        "mobile": partner.mobile if partner else None,
                        "email": partner.email if partner else None,
                    },
                    timeout=4,
                )
            except Exception:  # noqa: BLE001
                _log.exception("eh_pos_kds: ready webhook failed for ticket %s", self.id)
