import { whenReady } from "@odoo/owl";
import { mountComponent } from "@web/env";
import { installBrandGuard } from "@eh_pos_kds_core/app/brand_guard";
import { KdsBoard } from "./kds_board";

/**
 * Standalone mount for the kitchen board. mountComponent builds the Odoo env
 * with services (bus_service, rpc), so the board can subscribe to live updates.
 * The brand mark is already server rendered into the body; the OWL app mounts
 * into its own root and never owns the attribution.
 */
whenReady(() => {
    const target = document.querySelector(".o_eh_kds_root");
    if (target) {
        mountComponent(KdsBoard, target);
    }
    installBrandGuard();
    // Best effort shell caching on a secure origin only. On a plain http kiosk
    // the IndexedDB read cache covers offline instead.
    if (window.location.protocol === "https:" && "serviceWorker" in navigator) {
        navigator.serviceWorker.register("/eh_kds/sw.js", { scope: "/eh_kds/" }).catch(() => {});
    }
});
