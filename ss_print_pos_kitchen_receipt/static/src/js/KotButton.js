/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { KitchenReceiptComponent } from "./KitchenReceiptComponent";
import { exportForKitchenPrinting } from "./utils";

const LAN_PRINTER_IPS = {
    KITCHEN: "192.168.13.40",
    BAR1: "192.168.13.50",
    BAR2: "192.168.13.60",
};

function getOrderLines(order) {
    if (!order) return [];
    if (typeof order.get_orderlines === "function") return order.get_orderlines() || [];
    if (typeof order.get_order_lines === "function") return order.get_order_lines() || [];
    return order.orderlines || [];
}

async function sendToLanPrinter(ip, ticketData) {
    if (!ip) return false;
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 1500);
        const response = await fetch(`http://${ip}:8008/cgi-bin/epos/service.cgi?devid=local_printer&timeout=60000`, {
            method: "POST",
            headers: { "Content-Type": "text/xml; charset=utf-8" },
            body: `<epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print"><text align="center">${ticketData.title || "KOT"}&#10;</text></epos-print>`,
            signal: controller.signal,
        });
        clearTimeout(timeoutId);
        return response.ok;
    } catch (_e) {
        return false;
    }
}

async function doPrintKitchenReceipt(posStore, currentOrder) {
    const pos = posStore;
    if (!pos) return;
    const order = currentOrder || (pos.get_order ? pos.get_order() : false);
    if (!order) return;

    const lines = getOrderLines(order);
    if (lines.length === 0 && !order.was_kot_printed) return;

    const categoriesToPrint = [];
    const foodData = exportForKitchenPrinting(pos, order, "Food");
    if (foodData && (foodData.has_new_items || !order.was_kot_printed) && foodData.orderlines.length > 0) {
        categoriesToPrint.push({ title: "KITCHEN", data: foodData, ips: [LAN_PRINTER_IPS.KITCHEN] });
    }

    const drinksData = exportForKitchenPrinting(pos, order, "Drinks");
    if (drinksData && (drinksData.has_new_items || !order.was_kot_printed) && drinksData.orderlines.length > 0) {
        categoriesToPrint.push({ title: "BAR", data: drinksData, ips: [LAN_PRINTER_IPS.BAR1, LAN_PRINTER_IPS.BAR2] });
    }

    if (categoriesToPrint.length === 0) {
        const fullData = exportForKitchenPrinting(pos, order);
        if (fullData && (fullData.has_new_items || !order.was_kot_printed) && fullData.orderlines.length > 0) {
            categoriesToPrint.push({ title: "KITCHEN", data: fullData, ips: [LAN_PRINTER_IPS.KITCHEN] });
        }
    }

    if (categoriesToPrint.length === 0) return;

    // 1. Non-blocking background LAN print to 192.168.13.40 (Kitchen), 192.168.13.50 (Bar1), 192.168.13.60 (Bar2)
    for (const item of categoriesToPrint) {
        const ips = item.ips || [];
        for (const targetIp of ips) {
            sendToLanPrinter(targetIp, item).catch(() => {});
        }
    }

    // 2. Direct web/hardware printer dialog
    if (pos.printer && typeof pos.printer.print === "function") {
        try {
            await pos.printer.print(
                KitchenReceiptComponent,
                { tickets: categoriesToPrint, data: categoriesToPrint[0].data },
                { webPrintFallback: true }
            );
        } catch (_e) {}
    } else if (pos.hardware_proxy && pos.hardware_proxy.printer) {
        try {
            await pos.hardware_proxy.printer.print_receipt(
                KitchenReceiptComponent,
                { data: categoriesToPrint[0].data }
            );
        } catch (_e) {}
    }

    if (pos.sendOrderInPreparation) {
        try {
            await pos.sendOrderInPreparation(order);
        } catch (_e) {}
    }

    // 3. Mark lines as printed so Order button hides immediately
    for (const line of lines) {
        const qtyNum = line.get_quantity ? line.get_quantity() : (line.quantity || line.qty || 1);
        line.printed_qty = qtyNum;
        line.saved_printed_qty = qtyNum;
        line.was_printed = true;
    }
    order.was_kot_printed = true;
}

async function doSendOrderToKitchenAndReturnToTables(posStore, currentOrder) {
    const pos = posStore;
    if (!pos) return;
    const order = currentOrder || (pos.get_order ? pos.get_order() : false);
    if (!order) return;

    try {
        await doPrintKitchenReceipt(pos, order);
    } catch (_e) {}
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
        const order = this.currentOrder || (this.props && this.props.order) || (this.pos && this.pos.get_order && this.pos.get_order());
        await doPrintKitchenReceipt(this.pos, order);
    },

    async onClickOrderButton() {
        const order = this.currentOrder || (this.props && this.props.order) || (this.pos && this.pos.get_order && this.pos.get_order());
        await doSendOrderToKitchenAndReturnToTables(this.pos, order);
        if (typeof this.render === "function") {
            this.render();
        }
    },

    async sendOrderAndReturnToTables() {
        const order = this.currentOrder || (this.props && this.props.order) || (this.pos && this.pos.get_order && this.pos.get_order());
        await doSendOrderToKitchenAndReturnToTables(this.pos, order);
        if (typeof this.render === "function") {
            this.render();
        }
    },

    async onClickManualKotButton() {
        const order = this.currentOrder || (this.props && this.props.order) || (this.pos && this.pos.get_order && this.pos.get_order());
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
            const order = this.currentOrder || (this.props && this.props.order) || (this.pos && this.pos.get_order && this.pos.get_order());
            if (!order) return false;
            const lines = getOrderLines(order);
            return lines && lines.length > 0;
        },

        get hasChangesToOrder() {
            const order = this.currentOrder || (this.props && this.props.order) || (this.pos && this.pos.get_order && this.pos.get_order());
            if (!order) return false;
            const lines = getOrderLines(order);
            if (!lines || lines.length === 0) return false;

            const food = exportForKitchenPrinting(this.pos, order, "Food");
            const drinks = exportForKitchenPrinting(this.pos, order, "Drinks");

            const newFood = (food && food.new_lines) ? food.new_lines.length : 0;
            const cancFood = (food && food.cancelled_lines) ? food.cancelled_lines.length : 0;
            const newDrinks = (drinks && drinks.new_lines) ? drinks.new_lines.length : 0;
            const cancDrinks = (drinks && drinks.cancelled_lines) ? drinks.cancelled_lines.length : 0;

            return (newFood > 0 || cancFood > 0 || newDrinks > 0 || cancDrinks > 0);
        },

        get changeSummary() {
            const order = this.currentOrder || (this.props && this.props.order) || (this.pos && this.pos.get_order && this.pos.get_order());
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
