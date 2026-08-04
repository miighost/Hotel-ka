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
            ["id", "name", "partner_id", "room_line_ids", "board_type"]
        );

        if (bookings.length === 0) {
            this.env.services.notification.add(_t("No active hotel bookings found."), { type: 'warning' });
            return;
        }

        const allLineIds = bookings.flatMap(b => b.room_line_ids || []);
        let roomLineMap = {};
        if (allLineIds.length > 0) {
            const roomLines = await this.orm.searchRead("room.booking.line",
                [["id", "in", allLineIds]],
                ["id", "booking_id", "room_id"]
            );
            for (const line of roomLines) {
                const bId = line.booking_id[0];
                if (!roomLineMap[bId]) {
                    roomLineMap[bId] = [];
                }
                if (line.room_id) {
                    roomLineMap[bId].push(line.room_id[1]);
                }
            }
        }

        const boardLabels = {
            'ro': 'Room Only (RO)',
            'bb': 'Bed & Breakfast (BB)',
            'hb': 'Half Board (HB)',
            'fb': 'Full Board (FB)',
        };

        for (const b of bookings) {
            const roomNames = roomLineMap[b.id] ? roomLineMap[b.id].join(", ") : "";
            b.display_name = roomNames || b.name;
            b.room_numbers = roomNames || b.name;
            b.board_type_display = boardLabels[b.board_type] || b.board_type || "Room Only (RO)";
        }

        const selectedBooking = await makeAwaitable(this.dialog, HotelRoomPopup, {
            title: _t("Room Information"),
            bookings: bookings,
        });

        if (selectedBooking) {
            const order = this.pos.getOrder();
            order?.setBooking(selectedBooking);
            if (selectedBooking.partner_id && selectedBooking.partner_id[0]) {
                const partnerId = selectedBooking.partner_id[0];
                let partner = this.pos.models["res.partner"]?.getBy?.("id", partnerId) ||
                              this.pos.models["res.partner"]?.get?.(partnerId);
                if (!partner) {
                    try {
                        const [pData] = await this.orm.read("res.partner", [partnerId], []);
                        if (pData) {
                            partner = this.pos.models["res.partner"].insert(pData);
                        }
                    } catch (e) {
                        console.warn("Could not load partner for room booking", e);
                    }
                }
                if (partner && order) {
                    if (typeof order.setPartner === 'function') {
                        order.setPartner(partner);
                    } else if (typeof order.set_partner === 'function') {
                        order.set_partner(partner);
                    }
                }
            }
        }
    }
});
