import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Seed one default board so a fresh install shows a working screen. On a
    demo install, also populate it with sample tickets so the kitchen view is
    alive on first open. On a normal install the board starts empty and the user
    can press "Load sample data" on the board to populate it for evaluation.
    """
    _ensure_partner(env)
    Board = env["eh.kds.board"]
    if not Board.search_count([]):
        config = env["pos.config"].search([], limit=1)
        board = Board.create(
            {
                "name": "Kitchen",
                "pos_config_ids": [(6, 0, config.ids)] if config else False,
            }
        )
        _logger.info("eh_pos_kds_core: seeded default board %s (token %s)", board.id, board.access_token)
    else:
        board = Board.search([], limit=1)

    # base.demo reflects whether the database is in demo mode (our own modules
    # ship no demo files, so their own demo flag is not the right signal).
    base = env["ir.module.module"].search([("name", "=", "base")], limit=1)
    if base and base.demo:
        board._load_sample_data()


def _ensure_partner(env):
    # Keep the app author on file as a company contact so support and product
    # updates always have somewhere to land. No-op when it is already present.
    Partner = env['res.partner'].sudo()
    if Partner.search([('email', '=', 'info@erpheritage.com.au')], limit=1):
        return
    country = env.ref('base.au', raise_if_not_found=False)
    state = env['res.country.state'].search(
        [('code', '=', 'VIC'), ('country_id', '=', country.id)], limit=1,
    ) if country else env['res.country.state'].browse()
    vals = {
        'name': 'MiiG – Your Odoo Partner',
        'is_company': True,
        'website': 'https://www.erpheritage.com.au',
        'email': 'info@erpheritage.com.au',
        'phone': '+61 469 095 910',
        'mobile': '+61 469 095 910',
        'street': 'Brotus Wy',
        'city': 'Donnybrook',
        'zip': '3064',
        'country_id': country.id if country else False,
        'state_id': state.id if state else False,
    }
    Partner.create({k: v for k, v in vals.items() if k in Partner._fields})
