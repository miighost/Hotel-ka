import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { readBoot } from "@eh_pos_kds_core/app/brand_guard";
import { OfflineStore } from "./offline";

/**
 * Live kitchen board. Loads a snapshot over a token guarded route, then keeps
 * itself current from the board's private bus channel. Bumps go back through the
 * token guarded op route as absolute lane moves, so an offline replay is
 * idempotent. When the network drops the board shows its cached state and queues
 * bumps, replaying them in order on reconnect.
 */
export class KdsBoard extends Component {
    static template = "eh_pos_kds.KdsBoard";
    static props = {};

    setup() {
        // Boot config (the token) comes only from the server rendered brand
        // element. No brand element means no token, so the board cannot load:
        // the attribution is load bearing.
        const boot = readBoot();
        this.token = boot ? boot.token : null;
        this.mode = boot ? (boot.mode || "board") : "board";
        const savedStatusView = this.token ? (localStorage.getItem("eh_kds_status_view_" + this.token) || "both") : "both";
        const savedLaneFilter = this.token ? (localStorage.getItem("eh_kds_lane_filter_" + this.token) || "all") : "all";
        this.bus = useService("bus_service");
        this.offline = new OfflineStore(this.token);
        this.state = useState({
            mode: this.mode,
            statusView: savedStatusView,
            selectedLaneFilter: savedLaneFilter,
            printTickets: [],
            board: { name: boot ? boot.name : "Kitchen", lanes: [] },
            configMissing: !boot,
            cards: [],
            statusData: null,
            paperOut: [],
            connected: false,
            offline: false,
            queued: 0,
            lastSync: null,
            view: "lanes",
            selectedId: null,
            showMetrics: false,
            stats: null,
        });
        this.tick = useState({ now: this._clientNow() });
        this.serverOffset = 0;
        this.alerted = new Set();

        onWillStart(async () => {
            if (!this.token) {
                return; // no boot config: degraded, render the config-missing notice
            }
            await this.load();
            this.subscribe();
        });

        this.timer = setInterval(() => {
            this.tick.now = this._clientNow();
            this.scanSla();
        }, 1000);
        this.metricsTimer = setInterval(() => {
            if (this.state.showMetrics) {
                this.loadStats();
            }
        }, 30000);
        this.onKey = (ev) => this.handleKey(ev);
        this.onOnline = () => this.reconnect();
        this.onOffline = () => (this.state.offline = true);
        window.addEventListener("keydown", this.onKey);
        window.addEventListener("online", this.onOnline);
        window.addEventListener("offline", this.onOffline);
        onWillUnmount(() => {
            clearInterval(this.timer);
            clearInterval(this.metricsTimer);
            window.removeEventListener("keydown", this.onKey);
            window.removeEventListener("online", this.onOnline);
            window.removeEventListener("offline", this.onOffline);
        });
    }

    // -- data ----------------------------------------------------------------

    async load() {
        if (this.state.mode === "status") {
            try {
                const data = await rpc("/eh_kds/status/data", { token: this.token });
                this.state.board = data.board;
                this.state.statusData = data;
                this.serverOffset = this._parse(data.server_time) - this._clientNow();
                this.state.offline = false;
                this.state.lastSync = new Date();
            } catch (_e) {
                this.state.offline = true;
            }
            return;
        }

        try {
            const data = await rpc("/eh_kds/board/data", { token: this.token });
            this.state.board = data.board;
            this.state.cards = data.cards;
            this.state.paperOut = data.paper_alerts || [];
            this.serverOffset = this._parse(data.server_time) - this._clientNow();
            this.state.offline = false;
            this.state.lastSync = new Date();
            this.offline.saveSnapshot(data);
        } catch (_e) {
            // server unreachable: fall back to the cached snapshot, read mostly
            const row = await this.offline.loadSnapshot();
            if (row && row.data) {
                this.state.board = row.data.board;
                this.state.cards = row.data.cards;
                this.state.lastSync = new Date(row.at);
            }
            this.state.offline = true;
        }
        await this._refreshQueueCount();
    }

    subscribe() {
        if (!this.token) {
            return;
        }
        this.bus.addChannel(this.token);
        this.bus.subscribe("kds.card", (payload) => this.onCardEvent(payload));
        this.bus.subscribe("kds.ticket", () => this.load());
        this.bus.subscribe("kds.status", () => this.load());
        this.bus.subscribe("kds.paper", (payload) => {
            this.state.paperOut = (payload && payload.stations) || [];
        });
        this.bus.subscribe("BUS:RECONNECT", () => this.reconnect());
        this.state.connected = true;
    }

    async reconnect() {
        await this.replayQueue();
        await this.load();
    }

    onCardEvent(payload) {
        const cards = this.state.cards;
        const idx = cards.findIndex((c) => c.id === payload.id);
        if (idx >= 0 && cards[idx].event_id > payload.event_id) {
            return; // stale echo, a newer event already applied
        }
        if (payload.status === "voided" || !payload.lane_id || payload.lane_index < 0) {
            if (idx >= 0) {
                cards.splice(idx, 1);
            }
            return;
        }
        if (idx >= 0) {
            cards[idx] = payload;
        } else {
            cards.push(payload);
        }
    }

    // -- ops (optimistic, offline aware) -------------------------------------

    async op(action, cardIds, extra = {}) {
        if (!cardIds.length) {
            return;
        }
        this._applyLocal(action, cardIds, extra);
        try {
            const res = await rpc("/eh_kds/board/op", {
                token: this.token,
                action,
                card_ids: cardIds,
                ...extra,
            });
            if (res && res.ok && res.cards) {
                res.cards.forEach((c) => this.onCardEvent(c));
            }
            this.state.offline = false;
        } catch (_e) {
            await this.offline.enqueue({ action, card_ids: cardIds, ...extra });
            this.state.offline = true;
            await this._refreshQueueCount();
        }
    }

    _applyLocal(action, cardIds, extra) {
        const lanes = this.state.board.lanes || [];
        for (const id of cardIds) {
            const card = this.state.cards.find((c) => c.id === id);
            if (!card) {
                continue;
            }
            if (action === "void") {
                const i = this.state.cards.indexOf(card);
                this.state.cards.splice(i, 1);
            } else if (action === "move" && extra.to_index !== undefined) {
                const t = extra.to_index;
                if (t >= lanes.length) {
                    const i = this.state.cards.indexOf(card);
                    this.state.cards.splice(i, 1);
                } else {
                    const clamped = Math.max(0, t);
                    card.lane_index = clamped;
                    card.lane_id = lanes[clamped] ? lanes[clamped].id : card.lane_id;
                }
            }
        }
    }

    async replayQueue() {
        const pending = await this.offline.pending();
        for (const row of pending) {
            try {
                await rpc("/eh_kds/board/op", { token: this.token, ...row.op });
                await this.offline.drop(row.key);
            } catch (_e) {
                break; // still offline, keep the rest for the next reconnect
            }
        }
        await this._refreshQueueCount();
    }

    async _refreshQueueCount() {
        this.state.queued = (await this.offline.pending()).length;
    }

    bump(card) {
        this.op("move", [card.id], { to_index: card.lane_index + 1 });
    }

    recall(card) {
        this.op("move", [card.id], { to_index: card.lane_index - 1 });
    }

    voidCard(card) {
        this.op("void", [card.id]);
    }

    // -- metrics -------------------------------------------------------------

    async toggleMetrics() {
        this.state.showMetrics = !this.state.showMetrics;
        if (this.state.showMetrics) {
            await this.loadStats();
        }
    }

    async loadStats() {
        try {
            this.state.stats = await rpc("/eh_kds/board/stats", { token: this.token });
        } catch (_e) {
            // keep the last stats if the server is briefly unreachable
        }
    }

    // -- derived views -------------------------------------------------------

    dataScopeLabel() {
        const scope = this.state.board ? this.state.board.data_scope : "all";
        if (scope === "session") {
            return "POS SESSION";
        }
        if (scope === "today") {
            return "TODAY";
        }
        return "ALL ORDERS";
    }

    printCard(card, bumpAfter = false) {
        this.state.printTickets = [card];
        setTimeout(() => {
            window.print();
            if (bumpAfter) {
                this.bump(card);
            }
        }, 100);
    }

    isFirstLane(laneId) {
        const lanes = this.state.board.lanes || [];
        return lanes.length > 0 && String(lanes[0].id) === String(laneId);
    }

    printLatestInStage(laneId) {
        const cards = this.cardsInLane(laneId);
        if (!cards.length) {
            return;
        }
        const latestCard = cards[cards.length - 1];
        this.printCard(latestCard, false);
    }

    printStage(laneId) {
        const cards = this.cardsInLane(laneId);
        if (!cards.length) {
            return;
        }
        this.state.printTickets = cards;
        setTimeout(() => {
            window.print();
        }, 100);
    }

    setLaneFilter(laneId) {
        this.state.selectedLaneFilter = laneId;
        if (this.token) {
            localStorage.setItem("eh_kds_lane_filter_" + this.token, String(laneId));
        }
    }

    isLaneFilterActive(laneId) {
        return String(this.state.selectedLaneFilter) === String(laneId);
    }

    visibleLanes() {
        const lanes = this.state.board.lanes || [];
        if (!this.state.selectedLaneFilter || this.state.selectedLaneFilter === "all") {
            return lanes;
        }
        const filtered = lanes.filter((l) => String(l.id) === String(this.state.selectedLaneFilter));
        return filtered.length ? filtered : lanes;
    }

    setStatusView(mode) {
        this.state.statusView = mode;
        if (this.token) {
            localStorage.setItem("eh_kds_status_view_" + this.token, mode);
        }
    }

    formatRef(ref) {
        if (!ref) {
            return { table: "", number: "" };
        }
        const str = String(ref).trim();
        if (str.startsWith("T") && str.includes(" ")) {
            const parts = str.split(" ");
            return { table: parts[0], number: parts.slice(1).join(" ") };
        }
        return { table: "", number: str };
    }

    laneById(id) {
        return this.state.board.lanes.find((l) => l.id === id);
    }

    cardsInLane(laneId) {
        return this.state.cards
            .filter((c) => c.lane_id === laneId)
            .sort((a, b) => this._priorityRank(a) - this._priorityRank(b) || a.id - b.id);
    }

    get orderedCards() {
        const order = this.state.board.lanes.map((l) => l.id);
        return [...this.state.cards].sort(
            (a, b) => order.indexOf(a.lane_id) - order.indexOf(b.lane_id) || a.id - b.id
        );
    }

    get allDay() {
        const counts = {};
        for (const c of this.state.cards) {
            counts[c.product] = (counts[c.product] || 0) + c.qty;
        }
        return Object.entries(counts)
            .map(([product, qty]) => ({ product, qty }))
            .sort((a, b) => b.qty - a.qty);
    }

    get heatmap() {
        // open cards bucketed by the minute they were placed, last 12 minutes
        const buckets = new Array(12).fill(0);
        const now = this._serverNow();
        for (const c of this.state.cards) {
            const ago = Math.floor((now - this._parse(c.placed_at)) / 60000);
            if (ago >= 0 && ago < 12) {
                buckets[11 - ago] += 1;
            }
        }
        const max = Math.max(1, ...buckets);
        return buckets.map((count, index) => {
            const minAgo = 11 - index;
            const label = minAgo === 0 ? "Now" : `-${minAgo}m`;
            const pct = Math.round((100 * count) / max);
            return { index, count, label, pct, h: Math.max(8, pct) };
        });
    }

    _priorityRank(card) {
        const rank = { vip: 0, rush: 1, normal: 2 }[card.priority];
        return rank !== undefined && rank !== null ? rank : 2;
    }

    // -- timing + SLA --------------------------------------------------------

    _clientNow() {
        return new Date().getTime();
    }

    _parse(iso) {
        return iso ? new Date(iso.endsWith("Z") ? iso : iso + "Z").getTime() : 0;
    }

    _serverNow() {
        return this.tick.now + this.serverOffset;
    }

    lastSyncLabel() {
        if (!this.state.lastSync) {
            return "";
        }
        const s = Math.floor((this._clientNow() - this.state.lastSync.getTime()) / 1000);
        if (s < 60) {
            return `${s}s ago`;
        }
        return `${Math.floor(s / 60)}m ago`;
    }

    isLastLane(card) {
        const lane = this.laneById(card.lane_id);
        const lanes = this.state.board.lanes;
        return lane && lanes && lanes.length > 0 && lane.id === lanes[lanes.length - 1].id;
    }

    ageLabel(card) {
        if (this.isLastLane(card)) {
            // Completed card: freeze timer at static total prep time (placed_at to completed timestamp)
            const start = this._parse(card.placed_at);
            const end = this._parse(card.changed_at || card.placed_at);
            const secs = Math.max(0, Math.floor((end - start) / 1000));
            const m = Math.floor(secs / 60);
            const s = secs % 60;
            const sStr = s < 10 ? "0" + s : "" + s;
            return "✓ " + m + ":" + sStr;
        }
        const timestamp = card.changed_at || card.placed_at;
        const secs = Math.max(0, Math.floor((this._serverNow() - this._parse(timestamp)) / 1000));
        const m = Math.floor(secs / 60);
        const s = secs % 60;
        const sStr = s < 10 ? "0" + s : "" + s;
        return "" + m + ":" + sStr;
    }


    slaClass(card) {
        if (this.isLastLane(card)) {
            return ""; // Completed cards never trigger SLA warnings
        }
        const lane = this.laneById(card.lane_id);
        if (!lane || !lane.sla_minutes) {
            return "";
        }
        const mins = (this._serverNow() - this._parse(card.changed_at)) / 60000;
        const r = mins / lane.sla_minutes;
        if (r >= 1) {
            return "is-danger";
        }
        if (r >= 0.8) {
            return "is-coral";
        }
        if (r >= 0.5) {
            return "is-warn";
        }
        return "";
    }

    scanSla() {
        for (const card of this.state.cards) {
            if (!this.isLastLane(card) && this.slaClass(card) === "is-danger" && !this.alerted.has(card.id)) {
                this.alerted.add(card.id);
                this._beep();
            }
        }
    }

    _beep() {
        try {
            const Ctx = window.AudioContext || window.webkitAudioContext;
            if (!Ctx) {
                return;
            }
            const ctx = (this._audio = this._audio || new Ctx());
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.frequency.value = 660;
            gain.gain.value = 0.05;
            osc.connect(gain).connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.15);
        } catch (_e) {
            // sound is a nicety, never fatal
        }
    }

    // -- interactions --------------------------------------------------------

    select(cardId) {
        this.state.selectedId = cardId;
    }

    _selected() {
        return this.state.cards.find((c) => c.id === this.state.selectedId);
    }

    advanceSelected(direction) {
        const card = this._selected();
        if (card) {
            this.op("move", [card.id], { to_index: card.lane_index + direction });
        }
    }

    voidSelected() {
        const card = this._selected();
        if (card) {
            this.voidCard(card);
            this.state.selectedId = null;
        }
    }

    moveSelection(step) {
        const list = this.orderedCards;
        if (!list.length) {
            return;
        }
        const idx = list.findIndex((c) => c.id === this.state.selectedId);
        const next = idx < 0 ? 0 : Math.max(0, Math.min(list.length - 1, idx + step));
        this.state.selectedId = list[next].id;
    }

    handleKey(ev) {
        switch (ev.key) {
            case "ArrowRight":
            case "Enter":
            case " ":
                this.advanceSelected(1);
                ev.preventDefault();
                break;
            case "ArrowLeft":
            case "Backspace":
                this.advanceSelected(-1);
                ev.preventDefault();
                break;
            case "ArrowDown":
                this.moveSelection(1);
                ev.preventDefault();
                break;
            case "ArrowUp":
                this.moveSelection(-1);
                ev.preventDefault();
                break;
            case "Delete":
                this.voidSelected();
                ev.preventDefault();
                break;
            case "a":
            case "A":
                this.state.view = this.state.view === "allday" ? "lanes" : "allday";
                break;
            case "m":
            case "M":
                this.toggleMetrics();
                break;
        }
    }
}
