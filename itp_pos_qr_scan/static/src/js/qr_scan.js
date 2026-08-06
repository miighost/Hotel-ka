/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { _t } from "@web/core/l10n/translation";

export async function handleScannedBarcode(pos, env, code) {
    if (!code) return false;
    const cleanCode = String(code).trim();
    if (!cleanCode) return false;

    let partner = false;

    // 1. Check local POS DB for matching partner by barcode, ref, phone, id, or name
    if (pos.db && typeof pos.db.get_partner_by_barcode === "function") {
        partner = pos.db.get_partner_by_barcode(cleanCode);
    }

    if (!partner && pos.db && typeof pos.db.get_partners_list === "function") {
        const partners = pos.db.get_partners_list() || [];
        partner = partners.find(
            (p) =>
                (p.barcode && String(p.barcode).trim() === cleanCode) ||
                (p.ref && String(p.ref).trim() === cleanCode) ||
                (p.phone && String(p.phone).trim() === cleanCode) ||
                (p.id && String(p.id) === cleanCode) ||
                (p.name && p.name.toLowerCase() === cleanCode.toLowerCase())
        );
    }

    if (!partner && pos.models && pos.models["res.partner"]) {
        const partnerRecords = Object.values(pos.models["res.partner"]);
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
    const orm = pos.orm || (env && env.services && env.services.orm);
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
                if (pos.db && typeof pos.db.add_partners === "function") {
                    pos.db.add_partners([partner]);
                }
            }
        } catch (err) {
            console.error("Error performing RPC partner search by barcode:", err);
        }
    }

    // 3. Set partner on active POS order and update POS state
    const currentOrder = typeof pos.get_order === "function" ? pos.get_order() : (pos.selectedOrder || null);

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

        if (typeof pos.setSelectedPartner === "function") {
            try {
                pos.setSelectedPartner(partner);
            } catch (_e) {}
        }

        const notification = env && env.services && env.services.notification;
        if (notification) {
            notification.add(
                _t("Customer set to %s", partner.name || partner.display_name),
                { type: "success" }
            );
        }
        return true;
    }

    // 4. Fallback to standard POS barcode reader for non-partner codes (e.g. products)
    if (pos.barcodeReader && typeof pos.barcodeReader.scan === "function") {
        pos.barcodeReader.scan(cleanCode);
    }
    return false;
}

if (ProductScreen && ProductScreen.prototype) {
    patch(ProductScreen.prototype, {
        setup() {
            super.setup();
            if (this.pos) {
                this.pos.handle_scanned_barcode = (code) => handleScannedBarcode(this.pos, this.env, code);
            }
        },
        async handle_scanned_barcode(code) {
            return await handleScannedBarcode(this.pos, this.env, code);
        },
    });
}
