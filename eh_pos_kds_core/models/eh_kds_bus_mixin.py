from odoo import models

from ..utils.brand import brand_anchor


class EhKdsBusMixin(models.AbstractModel):
    """Original realtime backbone for the KDS suite.

    Channels are private and keyed by a board access token, one channel per
    topic: ``f"{token}-{topic}"``. Every payload carries the brand anchor so the
    attribution travels with the data, and a monotonic ``event_id`` is left to
    the caller (the bump event id) so clients can apply updates in order and
    detect gaps. This is our own protocol, not a wrapper over any other module.
    """

    _name = "eh.kds.bus.mixin"
    _description = "MiiG KDS Bus Mixin"

    def _kds_push(self, token, topic, payload=None):
        """Send one delta message of type ``topic`` on the board's private
        channel, which is the board access token itself.

        Client side subscribes with ``bus.addChannel(token)`` then
        ``bus.subscribe(topic, cb)``. The token is the only secret, so the raw
        token is a safe channel name.
        """
        if not token:
            return
        message = dict(payload or {})
        message.setdefault("brand", brand_anchor())
        self.env["bus.bus"]._sendone(token, topic, message)
