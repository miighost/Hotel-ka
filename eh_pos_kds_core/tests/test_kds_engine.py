from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "eh_pos_kds")
class TestKdsEngine(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Isolate routing from the board the install hook seeds (a global catch all).
        cls.env["eh.kds.board"].search([]).write({"active": False})
        cls.board = cls.env["eh.kds.board"].create({"name": "Grill"})
        cls.grill = cls.env["pos.category"].create({"name": "Grill Cat"})
        cls.drinks = cls.env["pos.category"].create({"name": "Drinks Cat"})
        cls.burger = cls._mk_product("Burger", cls.grill)
        cls.cola = cls._mk_product("Cola", cls.drinks)

    @classmethod
    def _mk_product(cls, name, categ):
        product = cls.env["product.product"].create({"name": name})
        if "pos_categ_ids" in product._fields:
            product.pos_categ_ids = [(6, 0, categ.ids)]
        elif "pos_categ_id" in product._fields:
            product.pos_categ_id = categ.id
        return product

    def _new_card(self, product=None, lane=None):
        """Create a ticket/item/card the way intake would, for engine tests."""
        product = product or self.burger
        lane = lane or self.board.lane_ids[0]
        ticket = self.env["eh.kds.ticket"].create({"ticket_ref": "T-1"})
        item = self.env["eh.kds.ticket.item"].create(
            {"ticket_id": ticket.id, "product_id": product.id, "quantity": 2.0}
        )
        card = self.env["eh.kds.card"].create({"item_id": item.id, "lane_id": lane.id})
        card._log("placed", to_lane=lane, push=False)
        return ticket, item, card

    # -- structure -----------------------------------------------------------

    def test_default_lanes_created(self):
        self.assertEqual(len(self.board.lane_ids), 4)
        self.assertEqual(self.board.lane_ids[0].name, "Queued")
        self.assertEqual(self.board.lane_ids[-1].name, "Completed")
        self.assertTrue(self.board.access_token)

    def test_clear_interval_must_be_positive(self):
        from odoo.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.board.clear_time_interval = 0

    # -- routing -------------------------------------------------------------

    def test_route_fallback_by_category(self):
        self.board.category_ids = [(6, 0, self.grill.ids)]
        burger_routes = self.board._route_item(False, self.burger, [])
        cola_routes = self.board._route_item(False, self.cola, [])
        self.assertEqual([b.id for b, _l in burger_routes], [self.board.id])
        self.assertEqual(cola_routes, [], "Cola is not in the board category, must not route")

    def test_route_rule_targets_lane(self):
        target = self.board.lane_ids[1]
        self.env["eh.kds.route.rule"].create(
            {"board_id": self.board.id, "category_id": self.grill.id, "target_lane_id": target.id}
        )
        routes = self.board._route_item(False, self.burger, [])
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0][1], target)
        # A rule set that does not match means the board does not catch the line.
        self.assertEqual(self.board._route_item(False, self.cola, []), [])

    # -- bump workflow -------------------------------------------------------

    def test_advance_and_event_log(self):
        _t, _i, card = self._new_card()
        lane0, lane1 = self.board.lane_ids[0], self.board.lane_ids[1]
        self.assertEqual(card.lane_id, lane0)
        self.assertEqual(card.status, "placed")
        card.advance(1)
        self.assertEqual(card.lane_id, lane1)
        self.assertEqual(card.status, "bumped")
        kinds = card.bump_event_ids.sorted("id").mapped("kind")
        self.assertEqual(kinds, ["placed", "bumped"])

    def test_recall_reverses(self):
        _t, _i, card = self._new_card()
        card.advance(1)
        card.advance(-1)
        self.assertEqual(card.lane_id, self.board.lane_ids[0])
        self.assertEqual(card.status, "recalled")

    def test_advance_clamped_at_boundaries(self):
        _t, _i, card = self._new_card(lane=self.board.lane_ids[0])
        card.advance(-1)  # already first, no move
        self.assertEqual(card.lane_id, self.board.lane_ids[0])
        # walk to the last lane and try to go further
        for _ in range(10):
            card.advance(1)
        self.assertEqual(card.lane_id, self.board.lane_ids[-1])

    def test_void(self):
        _t, _i, card = self._new_card()
        card.void(reason="dropped")
        self.assertEqual(card.status, "voided")
        self.assertEqual(card.last_event_id.reason, "dropped")

    # -- ready + completion + buckets ---------------------------------------

    def test_ticket_marks_ready_and_completion(self):
        ticket, _i, card = self._new_card()
        ready_lane = self.board.lane_ids[-2]
        # advance until the card reaches the ready lane (index len-2 = 2)
        while self.board.lane_ids.ids.index(card.lane_id.id) < 2:
            card.advance(1)
        self.assertTrue(ticket.completion_time and ticket.completion_time >= 1)

    def test_status_buckets(self):
        # one preparing ticket, one ready ticket
        _t1, _i1, prep_card = self._new_card()
        ticket2, _i2, ready_card = self._new_card()
        while self.board.lane_ids.ids.index(ready_card.lane_id.id) < 2:
            ready_card.advance(1)
        data = self.board._kds_status_data()
        refs_ready = [r["ref"] for r in data["ready"]]
        self.assertIn(ticket2.ticket_ref, refs_ready)
        self.assertTrue(len(data["preparing"]) >= 1)

    def test_move_to_idempotent(self):
        _t, _i, card = self._new_card()
        card.move_to(2)
        self.assertEqual(self.board.lane_ids.ids.index(card.lane_id.id), 2)
        bumps_before = len(card.bump_event_ids)
        card.move_to(2)  # same target, must be a no op
        self.assertEqual(len(card.bump_event_ids), bumps_before)
        self.assertEqual(self.board.lane_ids.ids.index(card.lane_id.id), 2)

    def test_stats_shape(self):
        ticket, _i, card = self._new_card()
        while self.board.lane_ids.ids.index(card.lane_id.id) < 2:
            card.advance(1)
        stats = self.board._kds_stats()
        for key in ("completed", "avg_minutes", "p95_minutes", "queue_depth", "void_rate", "per_lane", "bottleneck"):
            self.assertIn(key, stats)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(len(stats["per_lane"]), 4)

    def test_notify_gate_no_order_is_safe(self):
        self.board.notify_on_ready = True
        ticket, _i, card = self._new_card()
        # no pos_order_id, so no email, and no crash
        while self.board.lane_ids.ids.index(card.lane_id.id) < 2:
            card.advance(1)
        self.assertTrue(ticket.completion_time and ticket.completion_time >= 1)

    def test_board_data_payload(self):
        self._new_card()
        data = self.board._kds_board_data()
        self.assertEqual(data["board"]["id"], self.board.id)
        self.assertEqual(len(data["board"]["lanes"]), 4)
        self.assertEqual(len(data["cards"]), 1)
        card = data["cards"][0]
        for key in ("id", "lane_id", "lane_index", "status", "ticket_ref", "product", "qty"):
            self.assertIn(key, card)
        self.assertEqual(card["product"], "Burger")
        self.assertEqual(card["qty"], 2.0)
