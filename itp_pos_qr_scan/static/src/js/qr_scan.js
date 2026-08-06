/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";

if (PosStore && PosStore.prototype) {
    patch(PosStore.prototype, {
        async setup() {
            await super.setup(...arguments);
        },

        async handle_scanned_barcode(code) {
            if (!code) return false;
            const cleanCode = String(code).trim();
            if (!cleanCode) return false;

            let partner = false;

            // 1. Check local POS DB for matching partner by barcode, ref, phone, id, or name
            if (this.db && typeof this.db.get_partner_by_barcode === "function") {
                partner = this.db.get_partner_by_barcode(cleanCode);
            }

            if (!partner && this.db && typeof this.db.get_partners_list === "function") {
                const partners = this.db.get_partners_list() || [];
                partner = partners.find(
                    (p) =>
                        (p.barcode && String(p.barcode).trim() === cleanCode) ||
                        (p.ref && String(p.ref).trim() === cleanCode) ||
                        (p.phone && String(p.phone).trim() === cleanCode) ||
                        (p.id && String(p.id) === cleanCode) ||
                        (p.name && p.name.toLowerCase() === cleanCode.toLowerCase())
                );
            }

            if (!partner && this.models && this.models["res.partner"]) {
                const partnerRecords = Object.values(this.models["res.partner"]);
                partner = partnerRecords.find(
                    (p) =>
                        (p.barcode && String(p.barcode).trim() === cleanCode) ||
                        (p.ref && String(p.ref).trim() === cleanCode) ||
                        (p.phone && String(p.phone).trim() === cleanCode) ||
                        (p.id && String(p.id) === cleanCode) ||
                        (p.name && p.name.toLowerCase() === cleanCode.toLowerCase())
                );
            }

            // 2. RPC search fallback if not cached locally
            const orm = this.orm || (this.env && this.env.services && this.env.services.orm);
            if (!partner && orm) {
                try {
                    const domain = [
                        "|", "|", "|",
                        ["barcode", "=", cleanCode],
                        ["ref", "=", cleanCode],
                        ["phone", "=", cleanCode],
                        ["name", "ilike", cleanCode]
                    ];
                    const results = await orm.searchRead(
                        "res.partner",
                        domain,
                        ["id", "name", "barcode", "ref", "email", "phone"]
                    );
                    if (results && results.length > 0) {
                        partner = results[0];
                        if (this.db && typeof this.db.add_partners === "function") {
                            this.db.add_partners([partner]);
                        }
                    }
                } catch (err) {
                    console.error("Error performing RPC partner search by barcode:", err);
                }
            }

            // 3. Set partner on active POS order and update POS state
            const currentOrder = typeof this.get_order === "function" ? this.get_order() : (this.selectedOrder || null);

            if (partner && currentOrder) {
                if (typeof currentOrder.set_partner === "function") {
                    currentOrder.set_partner(partner);
                } else if (typeof currentOrder.setPartner === "function") {
                    currentOrder.setPartner(partner);
                } else if (typeof currentOrder.set_partner_id === "function") {
                    currentOrder.set_partner_id(partner);
                } else {
                    currentOrder.partner = partner;
                }

                if (typeof this.setSelectedPartner === "function") {
                    try {
                        this.setSelectedPartner(partner);
                    } catch (_e) {}
                }

                const notification = this.env && this.env.services && this.env.services.notification;
                if (notification) {
                    notification.add(
                        _t("Customer set to %s", partner.name || partner.display_name),
                        { type: "success" }
                    );
                }
                return true;
            }

            // 4. Fallback to standard POS barcode reader for non-partner codes (e.g. products)
            if (this.barcodeReader && typeof this.barcodeReader.scan === "function") {
                this.barcodeReader.scan(cleanCode);
            }
            return false;
        },
    });
}
