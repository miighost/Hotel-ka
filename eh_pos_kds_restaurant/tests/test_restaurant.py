from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "eh_pos_kds")
class TestKdsRestaurant(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["eh.kds.board"].search([]).write({"active": False})
        cls.board = cls.env["eh.kds.board"].create({"name": "Pass"})
        cls.config = cls.env["pos.config"].create({"name": "Resto", "module_pos_restaurant": True})
        cls.config.open_ui()
        cls.session = cls.config.current_session_id
        cls.table = cls.env["restaurant.table"].create({"table_number": 5})
        cls.product = cls.env["product.product"].create({"name": "Steak", "available_in_pos": True, "list_price": 20})

    def _order_with_course(self, fired=False):
        order = self.env["pos.order"].create({
            "session_id": self.session.id,
            "company_id": self.env.company.id,
            "table_id": self.table.id,
            "amount_total": 20, "amount_tax": 0, "amount_paid": 0, "amount_return": 0,
            "lines": [(0, 0, {
                "product_id": self.product.id, "qty": 1,
                "price_unit": 20, "price_subtotal": 20, "price_subtotal_incl": 20,
            })],
        })
        course = self.env["restaurant.order.course"].create({"order_id": order.id, "index": 1, "fired": fired})
        order.lines.course_id = course
        return order, course

    def test_routable_lines_gated_by_fire(self):
        order, course = self._order_with_course(fired=False)
        self.assertFalse(order._eh_kds_routable_lines(), "unfired course must not route")
        course.fired = True
        self.assertEqual(order._eh_kds_routable_lines(), order.lines, "fired course routes its lines")

    def test_intake_after_fire_sets_table(self):
        order, course = self._order_with_course(fired=False)
        order.sudo()._eh_kds_intake()
        self.assertFalse(self.env["eh.kds.card"].search([("board_id", "=", self.board.id)]), "nothing before fire")
        course.fired = True
        order.sudo()._eh_kds_intake()
        cards = self.env["eh.kds.card"].search([("board_id", "=", self.board.id)])
        self.assertTrue(cards, "cards created after fire")
        ticket = self.env["eh.kds.ticket"].search([("pos_order_id", "=", order.id)], limit=1)
        self.assertEqual(ticket.eh_table_id, self.table)
        self.assertIn("T5", ticket.ticket_ref)
