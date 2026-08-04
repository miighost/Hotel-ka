# Part of the MiiG POS Displays suite.
{
    'name': 'Kitchen Display Restaurant',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Free restaurant coursing and tables for the MiiG Kitchen Display on Odoo 19 Community: fire by course, table on every ticket, and table transfers that re-point the kitchen ticket.',
    'description': 'Adds restaurant service to the MiiG Kitchen Display. A line reaches the kitchen only once its course is fired, so starters and mains land in order, not all at once. Every ticket carries its table and shows it on the board, and a table transfer re-points the kitchen ticket so the pass always knows where the food goes. Requires the free Kitchen Display, and the Odoo 19 Community restaurant coursing it builds on.',
    'author': 'MiiG',
    'website': 'https://www.erpheritage.com.au',
    'license': 'OPL-1',
    'depends': ['eh_pos_kds', 'pos_restaurant'],
    'data': [],
    'installable': True,
    'application': False,
    'images': ['static/description/banner.gif'],
}
