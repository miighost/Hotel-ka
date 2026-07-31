# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ReportRoomStatus(models.AbstractModel):
    """Abstract model for generating the Room Status QWeb PDF Report."""

    _name = 'report.hotel_management_odoo.report_room_status'
    _description = 'Room Status Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Fetch active room bookings and calculate today's accrued running balance."""
        if docids:
            docs = self.env['room.booking'].browse(docids)
        else:
            docs = self.env['room.booking'].search([('state', 'in', ['reserved', 'check_in'])], order='checkin_date desc, id desc')

        if not docs:
            docs = self.env['room.booking'].search([('state', 'in', ['reserved', 'check_in'])], order='checkin_date desc, id desc')

        today = fields.Date.context_today(self)
        booking_data = []
        for o in docs:
            # Agreed nightly rate for this booking
            nightly_rate = sum(line.price_unit for line in o.room_line_ids) if o.room_line_ids else 0.0

            # Calculate elapsed stay days up to today
            checkin_d = fields.Date.to_date(o.checkin_date) if o.checkin_date else today
            if checkin_d and checkin_d <= today:
                elapsed_days = (today - checkin_d).days + 1
            else:
                elapsed_days = 1

            max_days = o.duration or 1
            elapsed_days = max(1, min(elapsed_days, max_days))

            # Today's accrued balance
            todays_balance = elapsed_days * nightly_rate

            booking_data.append({
                'booking': o,
                'nightly_rate': nightly_rate,
                'todays_balance': todays_balance,
                'elapsed_days': elapsed_days,
            })

        return {
            'doc_ids': docs.ids,
            'doc_model': 'room.booking',
            'docs': docs,
            'booking_data': booking_data,
        }
