# Copyright 2018 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# License MIT (https://opensource.org/licenses/MIT).
{
    "name": """QR-based payments in POS""",
    "summary": """Technical module to support qr-based payments like Alipay, WeChat""",
    "category": "Point of Sale",
    # "live_test_url": "",
    "images": [],
    "version": "19.0.1.0.0",
    "application": False,
    "author": "IT-Projects LLC",
    "support": "apps@it-projects.info",
    "website": "https://it-projects.info",
    "license": "Other OSI approved licence",  # MIT
    # "price": 13.00,
    # "currency": "EUR",
    "depends": ["point_of_sale"],
    "external_dependencies": {"python": [], "bin": []},
    "data": ["wizard/pos_payment_views.xml"],
    "assets": {
        "point_of_sale.assets_prod": [
            "itp_pos_qr_payments/static/src/js/itp_pos_qr_payments.js",
        ],
        "point_of_sale.assets": [
            "itp_pos_qr_payments/static/src/js/itp_pos_qr_payments.js",
        ],
        "point_of_sale.assets_pos": [
            "itp_pos_qr_payments/static/src/js/itp_pos_qr_payments.js",
        ],
        "point_of_sale._assets_pos": [
            "itp_pos_qr_payments/static/src/js/itp_pos_qr_payments.js",
        ],
    },


    "demo": [],
    "auto_install": False,
    "installable": True,
}

