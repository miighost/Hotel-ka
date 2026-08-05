/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { QRScanPopup } from "../../Popups/QRScanPopup";

export async function openQRScanPopup(pos, env) {
    let popupComp = QRScanPopup;
    if (!popupComp && window.odoo && window.odoo.loader && window.odoo.loader.modules) {
        for (const [name, mod] of window.odoo.loader.modules) {
            if ((name.includes("QRScanPopup") || name.includes("qr_scan_popup")) && mod && mod.QRScanPopup) {
                popupComp = mod.QRScanPopup;
                break;
            }
        }
    }

    const popupService = (env && env.services && env.services.popup) || (pos && pos.env && pos.env.services && pos.env.services.popup);
    if (popupComp && popupService) {
        await popupService.add(popupComp, {});
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
