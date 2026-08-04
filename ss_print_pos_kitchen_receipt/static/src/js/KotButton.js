/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { KitchenReceiptComponent } from "./KitchenReceiptComponent";
import { exportForKitchenPrinting } from "./utils";

function getOrderLines(order) {
    if (!order) {
        return [];
    }
    if (typeof order.get_orderlines === "function") {
        return order.get_orderlines() || [];
    }
    if (typeof order.get_order_lines === "function") {
        return order.get_order_lines() || [];
    }
    if (Array.isArray(order.orderlines)) {
        return order.orderlines;
    }
    if (Array.isArray(order.lines)) {
        return order.lines;
    }
    return [];
}

async function doPrintKitchenReceipt(posStore, currentOrder) {
    const pos = posStore;
    if (!pos) {
        return;
    }
    const order = currentOrder || (pos.get_order ? pos.get_order() : false);
    if (!order) {
        return;
    }
    const lines = getOrderLines(order);
    if (lines.length === 0 && !order.was_kot_printed) {
        return;
    }


    const categoriesToPrint = [];
    const foodData = exportForKitchenPrinting(pos, order, "Food");
    if (foodData && (foodData.has_new_items || !order.was_kot_printed) && foodData.orderlines.length > 0) {
        categoriesToPrint.push({ title: "KITCHEN", data: foodData });
    }

    const drinksData = exportForKitchenPrinting(pos, order, "Drinks");
    if (drinksData && (drinksData.has_new_items || !order.was_kot_printed) && drinksData.orderlines.length > 0) {
        categoriesToPrint.push({ title: "BAR", data: drinksData });
    }

    if (categoriesToPrint.length === 0) {
        const fullData = exportForKitchenPrinting(pos, order);
        if (fullData && (fullData.has_new_items || !order.was_kot_printed) && fullData.orderlines.length > 0) {
            categoriesToPrint.push({ title: "KITCHEN", data: fullData });
        }
    }


    const hasDirectPrinters = Boolean(
        (pos.config && (pos.config.is_order_printer || pos.config.module_pos_restaurant)) ||
        (pos.printers && pos.printers.length > 0) ||
        (pos.unregistered_printers && pos.unregistered_printers.length > 0) ||
        (pos.hardware_proxy && pos.hardware_proxy.printer)
    );

    let directSuccess = false;

    if (hasDirectPrinters) {
        // 1. Silent direct LAN ePOS printing to Jiko & Bar1
        if (pos.hardware_proxy && pos.hardware_proxy.printer) {
            for (const item of categoriesToPrint) {
                item.data.category_title = item.title;
                try {
                    const res = await pos.hardware_proxy.printer.print_receipt(
                        KitchenReceiptComponent,
                        { data: item.data }
                    );
                    if (res && res.result) {
                        directSuccess = true;
                    }
                } catch (_e) {}
            }
        }
        if (pos.sendOrderInPreparation) {
            try {
                const res = await pos.sendOrderInPreparation(order);
                if (res !== false && (!res || res.successful !== false)) {
                    directSuccess = true;
                }
            } catch (_e) {
                directSuccess = false;
            }
        }
    }


    // 2. Automatic Manual Fallback: If LAN printers fail or are offline, open browser print dialog
    if (!directSuccess && pos.printer && typeof pos.printer.print === "function") {
        try {
            await pos.printer.print(
                KitchenReceiptComponent,
                { tickets: categoriesToPrint, data: categoriesToPrint[0].data },
                { webPrintFallback: true }
            );
        } catch (_e) {}
    }


    if (categoriesToPrint.length > 0) {
        for (const line of lines) {
            const qtyNum = line.get_quantity ? line.get_quantity() : (line.quantity || line.qty || 1);
            line.printed_qty = qtyNum;
            line.saved_printed_qty = qtyNum;
            line.was_printed = true;
        }
        order.was_kot_printed = true;
    }
}



async function doSendOrderToKitchenAndReturnToTables(posStore, currentOrder) {
    const pos = posStore;
    if (!pos) {
        return;
    }
    const order = currentOrder || (pos.get_order ? pos.get_order() : false);
    if (!order) {
        return;
    }
    const lines = getOrderLines(order);
    if (lines.length === 0 && !order.was_kot_printed) {
        // Empty order: Navigate back to floor screen directly
        if (pos.router && typeof pos.router.navigate === "function") {
            try { pos.router.navigate("floor"); return; } catch (_e) {}
        }
        if (pos.showScreen) {
            try { pos.showScreen("FloorScreen"); return; } catch (_e) {}
        }
        return;
    }



    // 1. Auto print separate KOT tickets for Food vs Drinks (no duplicates)
    try {
        await doPrintKitchenReceipt(pos, order);
    } catch (_e) {
        // ignore
    }

    // 2. Send/sync to preparation printers & KDS backend
    if (typeof pos.sendOrderInPreparation === "function") {
        try {
            await pos.sendOrderInPreparation(order);
        } catch (_e) {
            // ignore
        }
    } else if (typeof pos.push_single_order === "function") {
        try {
            await pos.push_single_order(order);
        } catch (_e) {
            // ignore
        }
    } else if (typeof pos.sync_orders === "function") {
        try {
            await pos.sync_orders();
        } catch (_e) {
            // ignore
        }
    }

    // 3. Return to FloorScreen / Tables map (/pos/ui/<config_id>/floor)
    let navigated = false;
    if (pos.router && typeof pos.router.navigate === "function") {
        try {
            pos.router.navigate("floor");
            navigated = true;
        } catch (_e) {}
    }
    if (!navigated && pos.showScreen) {
        try {
            pos.showScreen("FloorScreen");
            navigated = true;
        } catch (_e) {}
    }
    if (!navigated && pos.showScreen) {
        try {
            pos.showScreen("floor");
        } catch (_e) {}
    }
    if (typeof pos.set_table === "function") {
        try {
            pos.set_table(null);
        } catch (_e) {}
    }
}


async function doForceBrowserPrintDialog(posStore, currentOrder) {
    const pos = posStore;
    if (!pos) return;
    const order = currentOrder || (pos.get_order ? pos.get_order() : false);
    if (!order) return;

    const categoriesToPrint = [];
    const foodData = exportForKitchenPrinting(pos, order, "Food");
    if (foodData && foodData.orderlines && foodData.orderlines.length > 0) {
        categoriesToPrint.push({ title: "KITCHEN", data: foodData });
    }

    const drinksData = exportForKitchenPrinting(pos, order, "Drinks");
    if (drinksData && drinksData.orderlines && drinksData.orderlines.length > 0) {
        categoriesToPrint.push({ title: "BAR", data: drinksData });
    }

    if (categoriesToPrint.length === 0) {
        const fullData = exportForKitchenPrinting(pos, order);
        if (fullData && fullData.orderlines && fullData.orderlines.length > 0) {
            categoriesToPrint.push({ title: "KITCHEN", data: fullData });
        }
    }

    if (categoriesToPrint.length === 0) return;

    if (pos.printer && typeof pos.printer.print === "function") {
        try {
            await pos.printer.print(
                KitchenReceiptComponent,
                { tickets: categoriesToPrint, data: categoriesToPrint[0].data },
                { webPrintFallback: true }
            );
        } catch (_e) {}
    }
}


const commonMethods = {
    async printKitchenReceipt() {
        const order = this.currentOrder || (this.pos && this.pos.get_order && this.pos.get_order());
        await doPrintKitchenReceipt(this.pos, order);
    },

    async onClickOrderButton() {
        const order = this.currentOrder || (this.pos && this.pos.get_order && this.pos.get_order());
        await doSendOrderToKitchenAndReturnToTables(this.pos, order);
    },

    async sendOrderAndReturnToTables() {
        const order = this.currentOrder || (this.pos && this.pos.get_order && this.pos.get_order());
        await doSendOrderToKitchenAndReturnToTables(this.pos, order);
    },

    async onClickManualKotButton() {
        const order = this.currentOrder || (this.pos && this.pos.get_order && this.pos.get_order());
        await doForceBrowserPrintDialog(this.pos, order);
    },
};

patch(ProductScreen.prototype, {
    setup() {
        super.setup();
        if (this.pos) {
            this.pos.printKitchenReceipt = (order) =>
                doPrintKitchenReceipt(this.pos, order || this.currentOrder || (this.pos.get_order && this.pos.get_order()));
            this.pos.sendOrderAndReturnToTables = (order) =>
                doSendOrderToKitchenAndReturnToTables(this.pos, order || this.currentOrder || (this.pos.get_order && this.pos.get_order()));
            this.pos.forceBrowserPrintDialog = (order) =>
                doForceBrowserPrintDialog(this.pos, order || this.currentOrder || (this.pos.get_order && this.pos.get_order()));
        }
    },
    ...commonMethods,
});


if (ActionpadWidget && ActionpadWidget.prototype) {
    patch(ActionpadWidget.prototype, {
        get hasOrderItems() {
            const order = this.currentOrder || (this.pos && this.pos.get_order && this.pos.get_order());
            if (!order) return false;
            const lines = getOrderLines(order);
            return lines && lines.length > 0;
        },

        get hasChangesToOrder() {

            const order = this.currentOrder || (this.pos && this.pos.get_order && this.pos.get_order());
            if (!order) return false;
            const food = exportForKitchenPrinting(this.pos, order, "Food");
            const drinks = exportForKitchenPrinting(this.pos, order, "Drinks");

            const newFood = (food && food.new_lines) ? food.new_lines.length : 0;
            const cancFood = (food && food.cancelled_lines) ? food.cancelled_lines.length : 0;
            const newDrinks = (drinks && drinks.new_lines) ? drinks.new_lines.length : 0;
            const cancDrinks = (drinks && drinks.cancelled_lines) ? drinks.cancelled_lines.length : 0;

            const nativeHasChanges = typeof order.hasChangesToPrint === "function" ? order.hasChangesToPrint() : false;
            return (newFood > 0 || cancFood > 0 || newDrinks > 0 || cancDrinks > 0 || nativeHasChanges);
        },

        get changeSummary() {
            const order = this.currentOrder || (this.pos && this.pos.get_order && this.pos.get_order());
            if (!order) return null;
            const food = exportForKitchenPrinting(this.pos, order, "Food");
            const drinks = exportForKitchenPrinting(this.pos, order, "Drinks");

            const newFood = (food && food.new_lines) ? food.new_lines.reduce((a, l) => a + (l.qty_num || 0), 0) : 0;
            const cancFood = (food && food.cancelled_lines) ? food.cancelled_lines.reduce((a, l) => a + (l.qty_num || 0), 0) : 0;
            const newDrinks = (drinks && drinks.new_lines) ? drinks.new_lines.reduce((a, l) => a + (l.qty_num || 0), 0) : 0;
            const cancDrinks = (drinks && drinks.cancelled_lines) ? drinks.cancelled_lines.reduce((a, l) => a + (l.qty_num || 0), 0) : 0;

            const parts = [];
            if (newFood > 0) parts.push(`Food +${newFood}`);
            else if (cancFood > 0) parts.push(`Food -${cancFood}`);

            if (newDrinks > 0) parts.push(`Drinks +${newDrinks}`);
            else if (cancDrinks > 0) parts.push(`Drinks -${cancDrinks}`);

            return parts.length > 0 ? parts.join(" | ") : null;
        },
        ...commonMethods,
    });
}

if (ControlButtons && ControlButtons.prototype) {
    patch(ControlButtons.prototype, commonMethods);
}






