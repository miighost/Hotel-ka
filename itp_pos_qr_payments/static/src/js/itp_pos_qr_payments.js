/** @odoo-module **/

/* Copyright 2018 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
   License MIT (https://opensource.org/licenses/MIT). */

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

function patchPosStore() {
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
        setup() {
            super.setup(...arguments);
            this.hidden_payment_methods = this.hidden_payment_methods || [];
        },

        show_warning(warning_message) {
            console.info("error", warning_message);
            if (this.env && this.env.services && this.env.services.popup) {
                this.env.services.popup.add("ErrorPopup", {
                    title: _t("Warning"),
                    body: warning_message,
                });
            } else if (this.env && this.env.services && this.env.services.notification) {
                this.env.services.notification.add(warning_message, { type: "warning" });
            }
        },

        add_qr_payment(order_uid, journal_id, amount, payment_vals, validate) {
            const orders = typeof this.get_open_orders === "function" ? this.get_open_orders() : (this.orders || []);
            const order = orders.find((item) => item.uid === order_uid);

            if (order) {
                const allMethods = (this.hidden_payment_methods || []).concat(this.payment_methods || []);
                const creg = allMethods.find(
                    (r) => r.journal_id && (Array.isArray(r.journal_id) ? r.journal_id[0] === journal_id : r.journal_id === journal_id)
                );

                let newPaymentline = null;
                if (creg && typeof order.add_paymentline === "function") {
                    newPaymentline = order.add_paymentline(creg);
                }

                if (newPaymentline) {
                    if (typeof newPaymentline.set_amount === "function") {
                        newPaymentline.set_amount(amount);
                    } else {
                        newPaymentline.amount = amount;
                    }
                    if (payment_vals) {
                        Object.assign(newPaymentline, payment_vals);
                    }
                }

                if (validate && typeof order.is_paid === "function" && order.is_paid()) {
                    if (typeof this.validateOrder === "function") {
                        this.validateOrder();
                    }
                }
                return order;
            }

            console.log("error", "Order is not found");
            return false;
        },
    });
}

if (document.readyState === "complete" || document.readyState === "interactive") {
    setTimeout(patchPosStore, 100);
} else {
    window.addEventListener("DOMContentLoaded", () => setTimeout(patchPosStore, 100));
}


