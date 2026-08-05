{
    'name': "Taqnix Mobile App Builder",

    'summary': "Generate Android APK and App Bundles (AAB) directly from your Odoo apps instantly.",

    'description': """
Taqnix Mobile App Builder
=========================
Transform your Odoo environment into fully functional mobile applications without writing a single line of code. The Taqnix App Builder allows you to seamlessly generate Android APKs and App Bundles (AAB) directly from your Odoo backend.

Whether you are running an e-commerce store, a car rental service, a real estate listing platform, or standard Odoo web apps, this module packages your existing features into a mobile experience ready for distribution.

Key Features:
-------------
* **Instant App Generation:** Build ready-to-deploy APK and AAB files in minutes.
* **Industry Versatility:** Perfectly tailored for E-commerce, Real Estate, Car Rental, and custom Odoo web apps.
* **Real-Time Synchronization:** Your mobile app syncs instantly with your Odoo database—no secondary backend required.
* **White-Label Ready:** Fully customize your app name, icon, splash screen, and branding elements.
* **Play Store Compliant:** Outputs optimized App Bundles (AAB) required for Google Play Store submission.

Stop worrying about complex mobile development cycles and API bridging. Build, download, and publish your Odoo mobile applications effortlessly with the Taqnix App Builder.
    """,

    'author': "Taqnix",
    'website': "https://www.taqnix.com",

    # Categories can be used to filter modules in modules listing
    'category': 'Tools',
    'version': '19.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base','mail'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/taqnix_app_builder_views.xml',
    ],

'assets': {
    'web.assets_frontend': [
        'taqnix_app_builder/static/src/css/module_presentation.css',
    ],
},

    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    # Odoo App Store Specifics
    'images': ['static/description/banner.png'],  # Required for a good App Store presentation
    'installable': True,
    'application': True,
    'license': 'OPL-1',  # Use 'OPL-1' for proprietary/paid apps, or 'LGPL-3' for free apps
}