/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { QRScanPopup } from "../../../Popups/QRScanPopup";

export async function openQRScanPopup(pos, env) {
    const popupService = (env && env.services && env.services.popup) || (pos && pos.popup) || (pos && pos.env && pos.env.services && pos.env.services.popup);
    const dialogService = (env && env.services && env.services.dialog) || (pos && pos.env && pos.env.services && pos.env.services.dialog);

    if (QRScanPopup) {
        if (popupService && typeof popupService.add === "function") {
            try { await popupService.add(QRScanPopup, {}); return; } catch (_e) {}
        }
        if (dialogService && typeof dialogService.add === "function") {
            try { await dialogService.add(QRScanPopup, {}); return; } catch (_e) {}
        }
    }

    if (pos && typeof pos.showPopup === "function") {
        try { await pos.showPopup("QRScanPopup"); return; } catch (_e) {}
    }
}

const qrMethods = {
    async onClickQRScan() {
        await openQRScanPopup(this.pos, this.env);
    },
};

patch(ProductScreen.prototype, {
    setup() {
        super.setup();
        if (this.pos) {
            this.pos.openQRScanPopup = () => openQRScanPopup(this.pos, this.env);
        }
    },
    ...qrMethods,
});

if (ControlButtons && ControlButtons.prototype) {
    patch(ControlButtons.prototype, qrMethods);
}

// Global Keyboard Shortcut Listener (Alt + Q or Option + Q)
window.addEventListener("keydown", (e) => {
    if (e.altKey && (e.key === "q" || e.key === "Q")) {
        e.preventDefault();
        if (window.posmodel) {
            openQRScanPopup(window.posmodel, window.posmodel.env);
        }
    }
});
