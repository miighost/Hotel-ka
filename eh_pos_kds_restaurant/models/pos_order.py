import logging

from odoo import models

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    """Restaurant coursing and tables for the kitchen display.

    Restaurant orders stay draft until end of meal, and lines are fired course
    by course. So intake runs on every sync (not only on payment) and only
    routes lines whose course has been fired. Tickets carry the table, and a
    table transfer re-points the kitchen ticket.
    """

    _inherit = "pos.order"

    def _is_eh_kds_restaurant(self):
        self.ensure_one()
        return bool(self.config_id.module_pos_restaurant)

    # -- routing seams -------------------------------------------------------

    def _eh_kds_routable_lines(self):
        self.ensure_one()
        if not self._is_eh_kds_restaurant():
            return super()._eh_kds_routable_lines()
        # a line reaches the kitchen only once its course is fired; lines with
        # no course (a la carte) fire immediately
        return self.lines.filtered(lambda l: (not getattr(l, "course_id", False)) or getattr(l.course_id, "fired", True))

    def _eh_kds_ticket_vals(self):
        vals = super()._eh_kds_ticket_vals()
        table = getattr(self, "table_id", False)
        if self._is_eh_kds_restaurant() and table:
            vals["eh_table_id"] = table.id
        return vals

    def _eh_kds_item_vals(self, line):
        vals = super()._eh_kds_item_vals(line)
        course = getattr(line, "course_id", False)
        if course:
            vals["eh_course_id"] = course.id
        return vals

    def _eh_kds_ref(self):
        ref = super()._eh_kds_ref()
        if self._is_eh_kds_restaurant() and self.table_id:
            table_ref = getattr(self.table_id, "table_number", False) or getattr(self.table_id, "name", False) or str(self.table_id.id)
            return "T%s %s" % (table_ref, ref)
        return ref

    # -- intake on every sync for restaurant (course firing) -----------------

    def _process_order(self, order, existing_order):
        order_id = super()._process_order(order, existing_order)
        po = self.env["pos.order"].browse(order_id)
        if po and po._is_eh_kds_restaurant():
            try:
                po.sudo()._eh_kds_intake()
            except Exception:  # noqa: BLE001
                _logger.exception("eh_pos_kds_restaurant: intake failed for pos.order %s", order_id)
        return order_id

    # -- re-point on table transfer -----------------------------------------

    def write(self, vals):
        res = super().write(vals)
        if "table_id" in vals:
            Ticket = self.env["eh.kds.ticket"].sudo()
            for order in self:
                if not order._is_eh_kds_restaurant():
                    continue
                ticket = Ticket.search([("pos_order_id", "=", order.id)], limit=1)
                if ticket and order.table_id:
                    ticket.eh_table_id = order.table_id.id
                    ticket.ticket_ref = order._eh_kds_ref()
                    for board in ticket.item_ids.card_ids.board_id:
                        board._kds_push(
                            board.access_token,
                            "kds.ticket",
                            {"ticket_id": ticket.id, "ticket_ref": ticket.ticket_ref, "event": "retable"},
                        )
        return res
