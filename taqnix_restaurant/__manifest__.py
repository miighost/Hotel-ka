{
    'name': 'POS Mobile App API',

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "Taqnix",
    'website': "https://www.taqnix.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Point of Sale',
    'version': '0.1',
    "license": "LGPL-3",

    # any module necessary for this one to work correctly
    'depends': ['base','point_of_sale', 'taqnix_app_builder'],

    'images': ['static/description/banner.png'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/pos_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/banner_views.xml',
    ],
    'installable': True,
    'application': False,
}

