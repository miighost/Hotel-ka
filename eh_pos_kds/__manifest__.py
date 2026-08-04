# Part of the MiiG POS Displays suite.
{
    'name': 'Kitchen Display',
    'version': '19.0.1.0.5',
    'category': 'Point of Sale',
    'summary': 'Free offline ready kitchen display for Odoo 19 Community Point of Sale: order lanes, live SLA timers with sound, all day view, recall and void audit, multi station routing, keyboard and bump bar, live throughput analytics, paired public order status screen.',
    'description': 'A free, offline ready kitchen display system for Odoo Community Point of Sale. Orders flow across configurable lanes with live age timers and a four tier SLA colour ramp with sound. An all day view aggregates item counts across every open order with a load heatmap, recall and void are kept in a durable audit log, products route to the right board and lane by point of sale, category or attribute, and the whole board runs with no mouse using the keyboard or a bump bar. It keeps working through a network drop and pairs with a public order status screen. Builds only on Odoo Community, never on Enterprise.',
    'author': 'MiiG',
    'website': 'https://www.erpheritage.com.au',
    'license': 'OPL-1',
    'depends': ['eh_pos_kds_core'],
    'data': ['views/eh_kds_board_page.xml'],
    'assets': {
        'eh_pos_kds.board_assets': [
            ('include', 'point_of_sale.base_app'),
            'eh_pos_kds_core/static/src/scss/eh_kds_variables.scss',
            'eh_pos_kds_core/static/src/app/brand_guard.js',
            'eh_pos_kds/static/src/app/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'images': ['static/description/banner.gif', 'static/description/kds_01_board.png', 'static/description/kds_02_metrics.png', 'static/description/kds_03_allday.png', 'static/description/kds_04_status.png'],
}
