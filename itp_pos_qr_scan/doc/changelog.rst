`19.0.1.0.0`
------------

- **Migrated to Odoo 19.0 Community Edition**
- Native ES Modules conversion (`/** @odoo-module **/`).
- Owl 2 migration (`useState`, `useRef`, `onMounted`, `onWillUnmount`).
- Registered assets in `__manifest__.py` under `point_of_sale._assets_pos`.
- Added automatic MediaStream track cleanup on component unmount to free camera devices.

`1.0.2`
-------

- **Fix:** - Scanner didn't work due to "ReferenceError: gCtx is not defined"

`1.0.1`
-------

- **FIX** - Error when showing error if webcam couldn't be started

`1.0.0`
-------

- **Init version**
