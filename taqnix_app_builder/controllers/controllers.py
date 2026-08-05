# from odoo import http


# class TaqnixAppBuilder(http.Controller):
#     @http.route('/taqnix_app_builder/taqnix_app_builder', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/taqnix_app_builder/taqnix_app_builder/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('taqnix_app_builder.listing', {
#             'root': '/taqnix_app_builder/taqnix_app_builder',
#             'objects': http.request.env['taqnix_app_builder.taqnix_app_builder'].search([]),
#         })

#     @http.route('/taqnix_app_builder/taqnix_app_builder/objects/<model("taqnix_app_builder.taqnix_app_builder"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('taqnix_app_builder.object', {
#             'object': obj
#         })

