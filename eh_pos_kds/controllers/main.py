import base64
import json

from odoo import http
from odoo.http import request
from odoo.tools import consteq
from odoo.tools.misc import file_path

from markupsafe import Markup

from odoo.addons.eh_pos_kds_core.utils.brand import brand_anchor, brand_position


def _boot_blob(token, name, mode="board"):
    """The display boot config, carried only inside the brand element so the
    attribution is load bearing: remove it and the app has no token to load.
    """
    return base64.b64encode(json.dumps({"token": token, "name": name, "mode": mode}).encode()).decode()


def _get_csrf():
    try:
        return request.csrf_token()
    except Exception:
        try:
            return request.csrf_token(None)
        except Exception:
            return ""


def _session_info():
    IrHttp = request.env["ir.http"]
    if hasattr(IrHttp, "session_info"):
        return IrHttp.session_info()
    if hasattr(IrHttp, "get_frontend_session_info"):
        return IrHttp.get_frontend_session_info()
    return {}


class EhKdsBoardPage(http.Controller):
    """Serve the kitchen board page for a board access token.

    The brand mark is rendered into the page body server side, before any
    JavaScript runs. The token is the only secret, checked in constant time.
    """

    @http.route("/eh_kds/board/<token>", auth="public", type="http", website=False)
    def board_page(self, token, **kw):
        board = request.env["eh.kds.board"].sudo().search(
            [("access_token", "=", token)], limit=1
        )
        if not board or not consteq(board.access_token, token):
            raise request.not_found()
        session_info = _session_info()
        odoo_json = Markup(
            json.dumps(
                {
                    "csrf_token": _get_csrf(),
                    "__session_info__": session_info,
                }
            )
        )
        return request.render(
            "eh_pos_kds.board_index",
            {
                "session_info": session_info,
                "odoo_json": odoo_json,
                "brand": brand_anchor(),
                "brand_pos": brand_position(request.env),
                "boot": _boot_blob(board.access_token, board.name, mode="board"),
            },
        )

    def _board(self, token):
        board = request.env["eh.kds.board"].sudo().search(
            [("access_token", "=", token)], limit=1
        )
        if not board or not consteq(board.access_token, token):
            raise request.not_found()
        return board

    def _json_board(self, token):
        if not token:
            return False
        board = request.env["eh.kds.board"].sudo().search(
            [("access_token", "=", token)], limit=1
        )
        if not board or not consteq(board.access_token, token):
            return False
        return board

    @http.route("/eh_kds/status/<token>", auth="public", type="http", website=False)
    def status_page(self, token, **kw):
        """Serve the public order status page."""
        board = self._board(token)
        session_info = _session_info()
        odoo_json = Markup(
            json.dumps(
                {
                    "csrf_token": _get_csrf(),
                    "__session_info__": session_info,
                }
            )
        )
        return request.render(
            "eh_pos_kds.board_index",
            {
                "session_info": session_info,
                "odoo_json": odoo_json,
                "brand": brand_anchor(),
                "brand_pos": brand_position(request.env),
                "boot": _boot_blob(board.access_token, board.name, mode="status"),
            },
        )

    @http.route("/eh_kds/board/data", auth="public", type="jsonrpc")
    def board_data(self, token, **kw):
        """Full board snapshot for first paint and for reconnect."""
        board = self._json_board(token)
        if not board:
            return {"error": "not_found", "ok": False}
        return board._kds_board_data()

    @http.route("/eh_kds/status/data", auth="public", type="jsonrpc")
    def status_data(self, token, **kw):
        """Status screen JSON snapshot for now serving / preparing."""
        board = self._json_board(token)
        if not board:
            return {"error": "not_found", "ok": False}
        return board._kds_status_data()

    @http.route("/eh_kds/board/op", auth="public", type="jsonrpc")
    def board_op(self, token, action, card_ids, reason=None, to_index=None, **kw):
        board = self._json_board(token)
        if not board:
            return {"ok": False, "reason": "not_found"}
        cards = (
            request.env["eh.kds.card"].sudo().browse(card_ids).exists().filtered(
                lambda c: c.board_id == board
            )
        )
        if not cards:
            return {"ok": False, "reason": "no cards"}
        if action == "move" and to_index is not None:
            cards.move_to(int(to_index))
        elif action == "advance":
            cards.advance(1)
        elif action == "recall":
            cards.advance(-1)
        elif action == "void":
            cards.void(reason=reason)
        else:
            return {"ok": False, "reason": "unknown action"}
        return {"ok": True, "cards": [c._kds_payload() for c in cards.exists()]}

    @http.route("/eh_kds/board/stats", auth="public", type="jsonrpc")
    def board_stats(self, token, **kw):
        """Live analytics KPIs for the board metrics panel."""
        board = self._json_board(token)
        if not board:
            return {"error": "not_found", "ok": False}
        return board._kds_stats()

    @http.route("/eh_kds/sw.js", auth="public", type="http")
    def service_worker(self, **kw):
        """Serve the board service worker from a broad scope so it can cache the
        board page. Best effort: the browser only uses it on a secure origin.
        """
        try:
            with open(file_path("eh_pos_kds/static/src/sw/sw.js"), encoding="utf-8") as fp:
                content = fp.read()
        except (FileNotFoundError, ValueError):
            return request.not_found()
        return request.make_response(
            content,
            headers=[
                ("Content-Type", "application/javascript"),
                ("Service-Worker-Allowed", "/eh_kds/"),
            ],
        )
