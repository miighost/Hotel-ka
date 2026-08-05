/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { QRScanPopup } from "../../Popups/QRScanPopup";

export class QRButton extends Component {
    static template = "itp_pos_qr_scan.QRButton";

    setup() {
        super.setup();
        this.popup = useService("popup");
    }

    async onClick() {
        let popupComp = QRScanPopup;
        if (!popupComp && window.odoo && window.odoo.loader && window.odoo.loader.modules) {
            for (const [name, mod] of window.odoo.loader.modules) {
                if ((name.includes("QRScanPopup") || name.includes("qr_scan_popup")) && mod && mod.QRScanPopup) {
                    popupComp = mod.QRScanPopup;
                    break;
                }
            }
        }

        if (popupComp && this.popup) {
            await this.popup.add(popupComp, {});
        }
    }
}

// Register QRButton component on ProductScreen & ControlButtons for OWL 2 template resolution
if (ProductScreen) {
    ProductScreen.components = ProductScreen.components || {};
    ProductScreen.components.QRButton = QRButton;
}

if (ControlButtons) {
    ControlButtons.components = ControlButtons.components || {};
    ControlButtons.components.QRButton = QRButton;
}

// Registry registration for control_buttons
registry.category("control_buttons").add("QRButton", {
    component: QRButton,
    condition: () => true,
});

// Multi-strategy patching fallback
function applyQRButtonPatch() {
    if (ProductScreen && ProductScreen.prototype && !ProductScreen.prototype._qrButtonPatched) {
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

    if (ControlButtons && ControlButtons.prototype && !ControlButtons.prototype._qrButtonPatched) {
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

// Global Keyboard Shortcut Listener (Alt + Q or Option + Q)
window.addEventListener("keydown", (e) => {
    if (e.altKey && (e.key === "q" || e.key === "Q")) {
        e.preventDefault();
        let popupComp = QRScanPopup;
        if (!popupComp && window.odoo && window.odoo.loader && window.odoo.loader.modules) {
            for (const [name, mod] of window.odoo.loader.modules) {
                if ((name.includes("QRScanPopup") || name.includes("qr_scan_popup")) && mod && mod.QRScanPopup) {
                    popupComp = mod.QRScanPopup;
                    break;
                }
            }
        }
        if (popupComp && window.posmodel) {
            const popupService = window.posmodel.env && window.posmodel.env.services && window.posmodel.env.services.popup;
            if (popupService) {
                popupService.add(popupComp, {});
            }
        }
    }
});

applyQRButtonPatch();
