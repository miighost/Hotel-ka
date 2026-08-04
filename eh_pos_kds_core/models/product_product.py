from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _eh_pos_categ_ids(self):
        """POS category ids for routing, across versions: pos_categ_ids (v17+,
        many) or pos_categ_id (v16, single).
        """
        self.ensure_one()
        if "pos_categ_ids" in self._fields:
            return self.pos_categ_ids.ids
        if "pos_categ_id" in self._fields:
            return self.pos_categ_id.ids
        return []
