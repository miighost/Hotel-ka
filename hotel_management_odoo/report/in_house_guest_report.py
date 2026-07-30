# -*- coding: utf-8 -*-
from odoo import api, models


class ReportInHouseGuest(models.AbstractModel):
    """Abstract model for generating the In-House Guest List QWeb PDF Report."""

    _name = 'report.hotel_management_odoo.report_in_house_guest'
    _description = 'In-House Guest List Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Fetch all currently checked-in room bookings ordered from newest to oldest."""
        if docids:
            docs = self.env['room.booking'].browse(docids)
        else:
            docs = self.env['room.booking'].search([('state', '=', 'check_in')], order='checkin_date desc, date_order desc, id desc')

        if not docs:
            docs = self.env['room.booking'].search([('state', '=', 'check_in')], order='checkin_date desc, date_order desc, id desc')
        else:
            docs = docs.sorted(key=lambda r: (r.checkin_date or r.date_order, r.id), reverse=True)

        return {
            'doc_ids': docs.ids,
            'doc_model': 'room.booking',
            'docs': docs,
        }
