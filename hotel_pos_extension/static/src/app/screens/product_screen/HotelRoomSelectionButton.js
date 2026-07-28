/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { patch } from "@web/core/utils/patch";
import { HotelRoomPopup } from "@hotel_pos_extension/js/HotelRoomPopup";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    },

    get currentBookingName() {
        const order = this.pos.getOrder();
        return order?.uiState?.roomName || _t("Add Room");
    },

    async onClickAddRoom() {
        const bookings = await this.orm.searchRead("room.booking",
            [["state", "=", "check_in"]],
            ["id", "name", "partner_id", "room_line_ids"]
        );

        if (bookings.length === 0) {
            this.env.services.notification.add(_t("No active hotel bookings found."), { type: 'warning' });
            return;
        }

        const bookingIds = bookings.map(b => b.id);
        const roomLines = await this.orm.searchRead("room.booking.line",
            [["booking_id", "in", bookingIds]],
            ["booking_id", "room_id"]
        );

        for (const booking of bookings) {
            const lines = roomLines.filter(l => l.booking_id && l.booking_id[0] === booking.id);
            const roomNames = lines
                .map(l => (Array.isArray(l.room_id) ? l.room_id[1] : ""))
                .filter(Boolean);
            booking.room_name = roomNames.length > 0 ? roomNames.join(", ") : booking.name;
        }

        const selectedBooking = await makeAwaitable(this.dialog, HotelRoomPopup, {
            title: _t("Room Information"),
            bookings: bookings,
        });

        if (selectedBooking) {
            const order = this.pos.getOrder();
            order?.setBooking(selectedBooking);
            if (selectedBooking.partner_id) {
                const partner = this.pos.models["res.partner"].get(selectedBooking.partner_id[0]);
                if (partner) {
                    order.setPartner(partner);
                }
            }
        }
    }
});
