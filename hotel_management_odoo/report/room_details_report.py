# -*- coding: utf-8 -*-
from odoo import api, models


class ReportRoomDetails(models.AbstractModel):
    """Abstract model for generating the Room Details QWeb PDF Report grouped by Room Type."""

    _name = 'report.hotel_management_odoo.report_room_details'
    _description = 'Room Details Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Fetch hotel rooms and group them by Room Type."""
        if docids:
            docs = self.env['hotel.room'].browse(docids)
        else:
            docs = self.env['hotel.room'].search([], order='room_type asc, name asc')

        if not docs:
            docs = self.env['hotel.room'].search([], order='room_type asc, name asc')

        # Room type selection dictionary mapping
        room_type_dict = dict(self.env['hotel.room']._fields['room_type'].selection)

        # Group rooms into sections by Room Type label
        grouped_rooms = {}
        for room in docs:
            r_type = room.room_type or 'other'
            type_label = room_type_dict.get(r_type, r_type.replace('_', ' ').upper())
            if type_label not in grouped_rooms:
                grouped_rooms[type_label] = []
            grouped_rooms[type_label].append(room)

        return {
            'doc_ids': docs.ids,
            'doc_model': 'hotel.room',
            'docs': docs,
            'grouped_rooms': grouped_rooms,
        }
