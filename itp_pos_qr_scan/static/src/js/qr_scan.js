/** @odoo-module **/

/* Copyright 2018 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
   Copyright 2018 Kolushov Alexandr <https://it-projects.info/team/KolushovAlexandr>
   License MIT (https://opensource.org/licenses/MIT). */

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

function patchPosStoreQRScan() {
    let PosStore = null;
    if (window.odoo && window.odoo.loader && window.odoo.loader.modules) {
        for (const [name, mod] of window.odoo.loader.modules) {
            if (name.includes("pos_store") && mod && mod.PosStore) {
                PosStore = mod.PosStore;
                break;
            }
        }
    }

    if (!PosStore) return;

    patch(PosStore.prototype, {
        async setup() {
            await super.setup(...arguments);
            if (this.env && this.env.bus) {
                this.env.bus.addEventListener("qr_scanned", (event) => {
                    const code = typeof event === "string" ? event : (event.detail || event);
                    if (code) {
                        this.handle_scanned_barcode(code);
                    }
                });
            }
        },

        hide_payment_method(payment_method_filter) {
            this.payment_methods = this.payment_methods || [];
            this.hidden_payment_methods = this.hidden_payment_methods || [];

            let payment_methods = this.payment_methods.filter(payment_method_filter);
            let payment_method = false;

            if (payment_methods.length) {
                if (payment_methods.length > 1) {
                    console.log(
                        "error",
                        "More than one payment method to hide is found",
                        payment_methods
                    );
                }
                payment_method = payment_methods[0];
            } else {
                return false;
            }

            this.payment_methods = this.payment_methods.filter((r) => {
                if (r.id === payment_method.id) {
                    this.hidden_payment_methods.push(r);
                    return false;
                }
                return true;
            });

            return payment_method;
        },

        async handle_scanned_barcode(code) {
            if (!code) return false;

            let partner = false;

            // 1. Check local POS DB for matching partner by barcode or ref
            if (this.db && typeof this.db.get_partner_by_barcode === "function") {
                partner = this.db.get_partner_by_barcode(code);
            }

            if (!partner && this.db && typeof this.db.get_partners_list === "function") {
                const partners = this.db.get_partners_list() || [];
                partner = partners.find(
                    (p) => (p.barcode && p.barcode === code) || (p.ref && p.ref === code)
                );
            }

            if (!partner && this.models && this.models["res.partner"]) {
                const partnerRecords = Object.values(this.models["res.partner"]);
                partner = partnerRecords.find(
                    (p) => (p.barcode && p.barcode === code) || (p.ref && p.ref === code)
                );
            }

            // 2. RPC search fallback if not cached locally
            const orm = this.orm || (this.env && this.env.services && this.env.services.orm);
            if (!partner && orm) {
                try {
                    const results = await orm.searchRead(
                        "res.partner",
                        ["|", ["barcode", "=", code], ["ref", "=", code]],
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

            // 3. Set partner on active POS order
            const currentOrder = typeof this.get_order === "function" ? this.get_order() : (this.selectedOrder || null);

            if (partner && currentOrder) {
                if (typeof currentOrder.set_partner === "function") {
                    currentOrder.set_partner(partner);
                } else if (typeof currentOrder.set_partner_id === "function") {
                    currentOrder.set_partner_id(partner);
                } else {
                    currentOrder.partner = partner;
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

            // 4. Fallback to standard POS barcode reader for non-partner codes
            if (this.barcodeReader && typeof this.barcodeReader.scan === "function") {
                this.barcodeReader.scan(code);
            }
            return false;
        },
    });
}

if (document.readyState === "complete" || document.readyState === "interactive") {
    setTimeout(patchPosStoreQRScan, 100);
} else {
    window.addEventListener("DOMContentLoaded", () => setTimeout(patchPosStoreQRScan, 100));
}



