/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class QRButton extends Component {
    static template = "itp_pos_qr_scan.QRButton";

    setup() {
        super.setup();
        this.popup = useService("popup");
    }

    async onClick() {
        let QRScanPopup = null;
        if (window.odoo && window.odoo.loader && window.odoo.loader.modules) {
            for (const [name, mod] of window.odoo.loader.modules) {
                if ((name.includes("QRScanPopup") || name.includes("qr_scan_popup")) && mod && mod.QRScanPopup) {
                    QRScanPopup = mod.QRScanPopup;
                    break;
                }
            }
        }

        if (QRScanPopup && this.popup) {
            await this.popup.add(QRScanPopup, {});
        }
    }
}

function registerQRButton() {
    let ProductScreen = null;
    if (window.odoo && window.odoo.loader && window.odoo.loader.modules) {
        for (const [name, mod] of window.odoo.loader.modules) {
            if (name.includes("product_screen") && mod && mod.ProductScreen) {
                ProductScreen = mod.ProductScreen;
                break;
            }
        }
    }

    if (ProductScreen && typeof ProductScreen.addControlButton === "function") {
        ProductScreen.addControlButton({
            component: QRButton,
            condition: function () {
                return true;
            },
        });
    }
}

if (document.readyState === "complete" || document.readyState === "interactive") {
    setTimeout(registerQRButton, 100);
} else {
    window.addEventListener("DOMContentLoaded", () => setTimeout(registerQRButton, 100));
}



