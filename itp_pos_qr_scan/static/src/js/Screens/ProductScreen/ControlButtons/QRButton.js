/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

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

// 1. Web registry registration
registry.category("control_buttons").add("QRButton", {
    component: QRButton,
    condition: () => true,
});

// 2. Multi-strategy patching for ProductScreen & ControlButtons
function applyQRButtonPatch() {
    if (!window.odoo || !window.odoo.loader || !window.odoo.loader.modules) return;

    for (const [name, mod] of window.odoo.loader.modules) {
        if (name.includes("product_screen") && mod && mod.ProductScreen) {
            const ProductScreen = mod.ProductScreen;

            if (typeof ProductScreen.addControlButton === "function") {
                try {
                    ProductScreen.addControlButton({
                        name: "QRButton",
                        component: QRButton,
                        condition: () => true,
                    });
                } catch (e) {}
            }

            if (ProductScreen.prototype && !ProductScreen.prototype._qrButtonPatched) {
                ProductScreen.prototype._qrButtonPatched = true;
                patch(ProductScreen.prototype, {
                    get controlButtons() {
                        const buttons = super.controlButtons ? [...super.controlButtons] : [];
                        if (!buttons.some((b) => b.name === "QRButton" || b.component === QRButton)) {
                            buttons.push({
                                name: "QRButton",
                                component: QRButton,
                                condition: () => true,
                            });
                        }
                        return buttons;
                    },
                });
            }
        }

        if (name.includes("control_buttons") && mod && mod.ControlButtons) {
            const ControlButtons = mod.ControlButtons;
            if (ControlButtons.prototype && !ControlButtons.prototype._qrButtonPatched) {
                ControlButtons.prototype._qrButtonPatched = true;
                patch(ControlButtons.prototype, {
                    get controlButtons() {
                        const buttons = super.controlButtons ? [...super.controlButtons] : [];
                        if (!buttons.some((b) => b.name === "QRButton" || b.component === QRButton)) {
                            buttons.push({
                                name: "QRButton",
                                component: QRButton,
                                condition: () => true,
                            });
                        }
                        return buttons;
                    },
                });
            }
        }
    }
}

// 3. Global Keyboard Shortcut Listener (Alt + Q or Option + Q)
window.addEventListener("keydown", (e) => {
    if (e.altKey && (e.key === "q" || e.key === "Q")) {
        e.preventDefault();
        let QRScanPopup = null;
        if (window.odoo && window.odoo.loader && window.odoo.loader.modules) {
            for (const [name, mod] of window.odoo.loader.modules) {
                if ((name.includes("QRScanPopup") || name.includes("qr_scan_popup")) && mod && mod.QRScanPopup) {
                    QRScanPopup = mod.QRScanPopup;
                    break;
                }
            }
        }
        if (QRScanPopup && window.posmodel) {
            const popupService = window.posmodel.env && window.posmodel.env.services && window.posmodel.env.services.popup;
            if (popupService) {
                popupService.add(QRScanPopup, {});
            }
        }
    }
});

if (document.readyState === "complete" || document.readyState === "interactive") {
    setTimeout(applyQRButtonPatch, 100);
    setTimeout(applyQRButtonPatch, 500);
} else {
    window.addEventListener("DOMContentLoaded", () => {
        setTimeout(applyQRButtonPatch, 100);
        setTimeout(applyQRButtonPatch, 500);
    });
}






