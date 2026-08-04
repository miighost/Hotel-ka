/**
 * Offline store for the kitchen board. A read cache keeps the last board
 * snapshot so a network blip shows known state instead of a blank screen, and a
 * replay queue holds bumps made while offline so they sync, in order, on
 * reconnect. Bump ops are absolute (move to a lane index), so replaying a queued
 * op is idempotent and converges.
 *
 * Original implementation. IndexedDB is used directly to avoid any dependency.
 */

const DB_NAME = "eh_kds";
const DB_VERSION = 1;
const SNAP = "snapshot";
const QUEUE = "queue";

function _open() {
    return new Promise((resolve, reject) => {
        if (!window.indexedDB) {
            reject(new Error("no indexeddb"));
            return;
        }
        const req = window.indexedDB.open(DB_NAME, DB_VERSION);
        req.onupgradeneeded = () => {
            const db = req.result;
            if (!db.objectStoreNames.contains(SNAP)) {
                db.createObjectStore(SNAP, { keyPath: "token" });
            }
            if (!db.objectStoreNames.contains(QUEUE)) {
                db.createObjectStore(QUEUE, { keyPath: "key", autoIncrement: true });
            }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
    });
}

function _tx(db, store, mode) {
    return db.transaction(store, mode).objectStore(store);
}

function _wrap(request) {
    return new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

export class OfflineStore {
    constructor(token) {
        this.token = token;
        this.ok = !!window.indexedDB;
    }

    async _db() {
        if (!this._dbp) {
            this._dbp = _open().catch(() => null);
        }
        return this._dbp;
    }

    async saveSnapshot(data) {
        const db = await this._db();
        if (!db) {
            return;
        }
        try {
            await _wrap(_tx(db, SNAP, "readwrite").put({ token: this.token, data, at: Date.now() }));
        } catch (_e) {
            // cache write failures are non fatal
        }
    }

    async loadSnapshot() {
        const db = await this._db();
        if (!db) {
            return null;
        }
        try {
            const row = await _wrap(_tx(db, SNAP, "readonly").get(this.token));
            return row || null;
        } catch (_e) {
            return null;
        }
    }

    async enqueue(op) {
        const db = await this._db();
        if (!db) {
            return;
        }
        try {
            await _wrap(_tx(db, QUEUE, "readwrite").add({ token: this.token, op, at: Date.now() }));
        } catch (_e) {
            // if we cannot queue, the op is simply lost; the board still works
        }
    }

    async pending() {
        const db = await this._db();
        if (!db) {
            return [];
        }
        try {
            const all = await _wrap(_tx(db, QUEUE, "readonly").getAll());
            return all.filter((row) => row.token === this.token).sort((a, b) => a.key - b.key);
        } catch (_e) {
            return [];
        }
    }

    async drop(key) {
        const db = await this._db();
        if (!db) {
            return;
        }
        try {
            await _wrap(_tx(db, QUEUE, "readwrite").delete(key));
        } catch (_e) {
            // ignore
        }
    }
}
