from odoo import models


class EhKdsCard(models.Model):
    _inherit = "eh.kds.card"

    def _kds_payload(self):
        """Add table and course to the card payload so the board can group and
        label restaurant tickets. Empty for non restaurant orders.
        """
        data = super()._kds_payload()
        item = self.item_id
        table = item.ticket_id.eh_table_id
        table_name = (getattr(table, "table_number", False) or getattr(table, "name", False) or (str(table.id) if table else False)) if table else False
        data["table"] = table_name
        data["course"] = item.eh_course_index if item.eh_course_id else False
        return data
