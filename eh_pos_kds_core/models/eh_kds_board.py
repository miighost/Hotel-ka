import uuid

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..utils.brand import brand_anchor

DEFAULT_LANES = [
    ("Queued", "#6B7280", 0),
    ("In Progress", "#7BCEA0", 6),
    ("Ready", "#34D399", 0),
    ("Completed", "#475569", 0),
]


class EhKdsBoard(models.Model):
    """A physical or logical kitchen screen, its lanes and its routing.

    A board is the unit a kitchen TV points at. It owns its lanes (columns), the
    POS configs and product categories it serves, and a private access token
    that keys its realtime channels and its public URLs.
    """

    _name = "eh.kds.board"
    _description = "MiiG KDS Board"
    _inherit = ["eh.kds.bus.mixin"]
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    access_token = fields.Char(
        default=lambda self: uuid.uuid4().hex,
        copy=False,
        index=True,
        readonly=True,
        required=True,
    )
    pos_config_ids = fields.Many2many("pos.config", string="Points of Sale")
    category_ids = fields.Many2many("pos.category", string="Product Categories")
    lane_ids = fields.One2many("eh.kds.lane", "board_id", string="Lanes")
    route_rule_ids = fields.One2many("eh.kds.route.rule", "board_id", string="Routing Rules")
    layout_mode = fields.Selection(
        [
            ("single", "Single column"),
            ("dual", "Two columns"),
            ("quad", "Four columns"),
            ("tv", "Wall display"),
        ],
        default="dual",
        required=True,
    )
    data_scope = fields.Selection(
        [
            ("all", "All Active Orders"),
            ("session", "Current Open POS Session Only"),
            ("today", "Today's Orders Only"),
        ],
        string="Data Scope",
        default="all",
        required=True,
        help="Control which order cards appear on this board: All active orders, current open POS session, or today's orders only.",
    )
    is_expo = fields.Boolean(
        string="Expo / All day board",
        help="An expo board aggregates items across every open ticket.",
    )
    auto_clear = fields.Boolean(
        help="Remove ready tickets from the order status screen after the interval."
    )
    clear_time_interval = fields.Integer(
        string="Auto clear interval (minutes)", default=10
    )
    notify_on_ready = fields.Boolean(
        string="Email customer when ready",
        help="Send a short email to the order customer when the order is ready, "
        "if the customer has an email address.",
    )
    notify_sms_on_ready = fields.Boolean(
        string="SMS customer when ready",
        help="Send an SMS to the order customer when ready, if the customer has "
        "a mobile number and the Odoo SMS app is installed. Uses your own SMS "
        "credits or gateway.",
    )
    notify_webhook_url = fields.Char(
        string="Ready webhook URL",
        help="Optional. When an order is ready, POST a small JSON payload to this "
        "URL. Bring your own SMS, push or messaging provider behind it.",
    )

    @api.constrains("clear_time_interval")
    def _check_clear_time_interval(self):
        for board in self:
            if board.clear_time_interval <= 0:
                raise ValidationError(
                    self.env._("The auto clear interval must be a positive number of minutes.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        boards = super().create(vals_list)
        for board in boards:
            if not board.lane_ids:
                board._seed_default_lanes()
        return boards

    def _seed_default_lanes(self):
        self.ensure_one()
        self.env["eh.kds.lane"].create(
            [
                {
                    "board_id": self.id,
                    "name": name,
                    "color": color,
                    "sla_minutes": sla,
                    "sequence": index,
                }
                for index, (name, color, sla) in enumerate(DEFAULT_LANES)
            ]
        )

    def _brand_anchor(self):
        return brand_anchor()

    # -- routing -------------------------------------------------------------

    def _lane_for(self, config, product, attr_value_ids):
        """Return the lane this product line lands on for this board, or empty.

        Route rules win and are ordered. A board with no rules falls back to its
        category and POS config fields. Empty everything means the board catches
        all lines (a global expo board).
        """
        self.ensure_one()
        categ_ids = product._eh_pos_categ_ids()
        rules = self.route_rule_ids.filtered("active")
        if rules:
            for rule in rules:
                if rule.pos_config_id and config and rule.pos_config_id != config:
                    continue
                if rule.category_id and rule.category_id.id not in categ_ids:
                    continue
                if rule.attribute_value_id and rule.attribute_value_id.id not in attr_value_ids:
                    continue
                return rule.target_lane_id or self.lane_ids[:1]
            return self.env["eh.kds.lane"]
        if self.pos_config_ids and config and config not in self.pos_config_ids:
            return self.env["eh.kds.lane"]
        if self.category_ids and not (set(self.category_ids.ids) & set(categ_ids)):
            return self.env["eh.kds.lane"]
        return self.lane_ids[:1]

    @api.model
    def _route_item(self, config, product, attr_value_ids):
        """Return a list of (board, lane) placements for one product line."""
        placements = []
        for board in self.search([("active", "=", True)]):
            lane = board._lane_for(config, product, attr_value_ids)
            if lane:
                placements.append((board, lane))
        return placements

    # -- data builders for the display pages ---------------------------------

    def _card_scope_domain(self):
        self.ensure_one()
        domain = [("board_id", "=", self.id)]
        if self.data_scope == "session":
            open_sessions = self.env["pos.session"].sudo().search([("state", "=", "opened")])
            domain.append(("ticket_id.pos_order_id.session_id", "in", open_sessions.ids))
        elif self.data_scope == "today":
            today_start = fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            domain.append(("create_date", ">=", today_start))
        return domain

    def _kds_board_data(self):
        self.ensure_one()
        cards = self.env["eh.kds.card"].sudo().search(self._card_scope_domain())
        open_cards = cards.filtered(lambda c: c.status != "voided" and c.lane_id)
        return {
            "board": {
                "id": self.id,
                "name": self.name,
                "layout_mode": self.layout_mode,
                "data_scope": self.data_scope,
                "lanes": [
                    {
                        "id": lane.id,
                        "name": lane.name,
                        "color": lane.color,
                        "sla_minutes": lane.sla_minutes,
                        "sequence": lane.sequence,
                    }
                    for lane in self.lane_ids
                ],
            },
            "cards": [c._kds_payload() for c in open_cards],
            "paper_alerts": self._eh_kds_paper_alerts(),
            "server_time": fields.Datetime.now().isoformat(),
            "brand": brand_anchor(),
        }

    def _eh_kds_paper_alerts(self):
        """Names of stations reporting a hardware alert (out of paper). Empty by
        default; the self-order add-on fills it from kiosk printers.
        """
        return []

    def _recent_completions(self):
        self.ensure_one()
        cards = self.env["eh.kds.card"].sudo().search(self._card_scope_domain())
        tickets = cards.ticket_id.filtered(lambda t: t.completion_time and t.completion_time > 0)
        tickets = tickets.sorted("id", reverse=True)[:10]
        return tickets.mapped("completion_time")

    def _eta_seconds(self):
        self.ensure_one()
        samples = self._recent_completions()
        if len(samples) < 3:
            return None
        ordered = sorted(samples)
        median = ordered[len(ordered) // 2]
        return int(median * 60)

    def _kds_status_data(self):
        self.ensure_one()
        cards = self.env["eh.kds.card"].sudo().search(self._card_scope_domain())
        open_cards = cards.filtered(lambda c: c.status != "voided" and c.lane_id)
        lanes = list(self.lane_ids)
        eta = self._eta_seconds()
        by_ticket = {}
        for card in open_cards:
            by_ticket.setdefault(card.ticket_id, self.env["eh.kds.card"])
            by_ticket[card.ticket_id] |= card
        preparing, ready_raw = [], []
        for ticket, tcards in by_ticket.items():
            ref = ticket.ticket_ref or str(ticket.id)
            idxs = [lanes.index(c.lane_id) for c in tcards if c.lane_id in lanes]
            if not idxs:
                continue
            if all(i == len(lanes) - 1 for i in idxs):
                continue  # collected, hide from the status screen
            if len(lanes) >= 2 and all(i >= len(lanes) - 2 for i in idxs):
                # seq = the latest bump event on this ticket, so the most recently
                # readied order is the one being served now.
                seq = max(tcards.bump_event_ids.ids or [0])
                ready_raw.append({"ref": ref, "ticket_id": ticket.id, "seq": seq})
            else:
                preparing.append({"ref": ref, "ticket_id": ticket.id, "eta_seconds": eta})
        ready_raw.sort(key=lambda r: r["seq"], reverse=True)
        ready = [{"ref": r["ref"], "ticket_id": r["ticket_id"]} for r in ready_raw]
        return {
            "board": {"id": self.id, "name": self.name, "layout_mode": self.layout_mode, "data_scope": self.data_scope},
            "now_serving": ready_raw[0]["ref"] if ready_raw else "",
            "preparing": preparing,
            "ready": ready,
            "server_time": fields.Datetime.now().isoformat(),
            "brand": brand_anchor(),
        }

    # -- analytics -----------------------------------------------------------

    def _kds_stats(self):
        """Live KPIs for the board: throughput, prep times, queue, voids,
        bottleneck lane. Real numbers, computed on demand, no Enterprise needed.
        """
        self.ensure_one()
        lanes = list(self.lane_ids)
        cards = self.env["eh.kds.card"].sudo().search(self._card_scope_domain())
        open_cards = cards.filtered(lambda c: c.status != "voided")
        voided = cards.filtered(lambda c: c.status == "voided")
        done = cards.ticket_id.filtered(lambda t: t.completion_time and t.completion_time > 0)
        comps = sorted(done.mapped("completion_time"))

        avg = round(sum(comps) / len(comps), 1) if comps else 0.0
        p95 = comps[min(len(comps) - 1, max(0, int(round(0.95 * len(comps))) - 1))] if comps else 0.0

        last_index = len(lanes) - 1 if lanes else 0
        queue = open_cards.filtered(lambda c: c.lane_id in lanes and lanes.index(c.lane_id) < last_index)

        per_lane = []
        bottleneck_name = "None"
        max_open = -1
        for lane in lanes:
            count = len(open_cards.filtered(lambda c: c.lane_id == lane))
            per_lane.append({"id": lane.id, "name": lane.name, "open": count})
            if count > max_open:
                max_open = count
                bottleneck_name = lane.name

        if max_open <= 0:
            bottleneck_name = "None"

        return {
            "completed": len(done),
            "avg_minutes": avg,
            "p95_minutes": p95,
            "queue_depth": len(queue),
            "void_count": len(voided),
            "void_rate": round(100.0 * len(voided) / (len(cards) or 1), 1),
            "per_lane": per_lane,
            "bottleneck": bottleneck_name,
            "samples": len(comps),
            "server_time": fields.Datetime.now().isoformat(),
        }

    # -- launch actions ------------------------------------------------------

    def action_open_board(self):
        self.ensure_one()
        if not self.access_token:
            self.access_token = uuid.uuid4().hex
        return {"type": "ir.actions.act_url", "url": "/eh_kds/board/%s" % self.access_token, "target": "new"}

    def action_open_status(self):
        self.ensure_one()
        if not self.access_token:
            self.access_token = uuid.uuid4().hex
        return {"type": "ir.actions.act_url", "url": "/eh_kds/status/%s" % self.access_token, "target": "new"}

    # -- sample data ---------------------------------------------------------

    _SAMPLE_TICKETS = [
        ("A31", [("Classic Burger", 2), ("Fries", 2)]),
        ("A32", [("Veggie Wrap", 1), ("Cola", 1)]),
        ("A33", [("Chicken Box", 3)]),
    ]

    def _load_sample_data(self):
        """Populate this board with a few sample tickets so the kitchen view is
        alive for evaluation. Used by the demo install hook and by the board
        button. A no op if the board already has tickets routed to it.
        """
        self.ensure_one()
        if not self.lane_ids:
            return
        if self.env["eh.kds.card"].sudo().search_count([("board_id", "=", self.id)]):
            return
        category = self.env["pos.category"].create({"name": "Kitchen Sample"})
        names = {name for _ref, items in self._SAMPLE_TICKETS for name, _q in items}
        products = {
            name: self.env["product.product"].create(
                {"name": name, "pos_categ_ids": [(6, 0, category.ids)], "available_in_pos": True}
            )
            for name in names
        }
        lane0 = self.lane_ids[0]
        lane1 = self.lane_ids[1] if len(self.lane_ids) > 1 else lane0
        for index, (ref, items) in enumerate(self._SAMPLE_TICKETS):
            ticket = self.env["eh.kds.ticket"].create({"ticket_ref": ref})
            lane = lane1 if index == 0 else lane0
            for name, qty in items:
                item = self.env["eh.kds.ticket.item"].create(
                    {"ticket_id": ticket.id, "product_id": products[name].id, "quantity": qty}
                )
                card = self.env["eh.kds.card"].create({"item_id": item.id, "lane_id": lane.id})
                card._log("placed", to_lane=lane, push=False)
        return True

    def action_load_sample(self):
        self.ensure_one()
        self._load_sample_data()
        return {"type": "ir.actions.client", "tag": "reload"}
