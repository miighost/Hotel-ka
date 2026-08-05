

=========================
 QR Code Scanning in POS
=========================

Scans QR codes via device's camera.

Usage
=====

To subscribe to scanning event use following code in js::

    var core = require('web.core');
    core.bus.on('qr_scanned', this, function(value){
        // your handler here
    })


Questions?
==========

To get an assistance on this module contact us by email apps@it-projects.info

Contributors
============
* `Kolushov Alexandr <https://it-projects.info/team/KolushovAlexandr>`__


Further information
===================

Odoo Apps Store: https://apps.odoo.com/apps/modules/14.0/itp_pos_qr_scan/


