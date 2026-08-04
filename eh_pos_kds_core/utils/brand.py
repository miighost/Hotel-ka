"""Single source of truth for the MiiG attribution mark.

The brand anchor is rendered server side into both display pages and is also
attached to every realtime payload. It is intentionally small and dependency
free so any model or controller can reach it. Removing or altering the
attribution is a breach of the module licence. See README_BRAND_PROTECTION.md.
"""

BRAND_COMPANY = "MiiG"
BRAND_LOGO_URI = "/eh_pos_kds_core/static/src/img/brand_mark.png"
BRAND_OWNER_KEY = "erpheritage.com.au"


def brand_anchor():
    """Return the attribution payload embedded in pages and bus messages."""
    return {
        "company": BRAND_COMPANY,
        "logo": BRAND_LOGO_URI,
        "owner": BRAND_OWNER_KEY,
    }


def brand_position(env):
    """Placement of the brand mark. Default is the standard bar. Relocating it
    is a paid, sanctioned option (the Pro add-on writes this parameter); the
    mark itself always shows, per the licence.
    """
    return env["ir.config_parameter"].sudo().get_param("eh_pos_kds.brand_position", "bar")
