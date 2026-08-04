/** @odoo-module */

import { Component } from "@odoo/owl";

export class KitchenReceiptComponent extends Component {
    static template = "ss_print_pos_kitchen_receipt.KitchenReceipt";
    static props = {
        data: { type: Object, optional: true },
        tickets: { type: Array, optional: true },
    };
}

