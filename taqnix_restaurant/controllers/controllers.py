# from odoo import http


# class TaqnixRestaurant(http.Controller):
#     @http.route('/taqnix_restaurant/taqnix_restaurant', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/taqnix_restaurant/taqnix_restaurant/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('taqnix_restaurant.listing', {
#             'root': '/taqnix_restaurant/taqnix_restaurant',
#             'objects': http.request.env['taqnix_restaurant.taqnix_restaurant'].search([]),
#         })

#     @http.route('/taqnix_restaurant/taqnix_restaurant/objects/<model("taqnix_restaurant.taqnix_restaurant"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('taqnix_restaurant.object', {
#             'object': obj
#         })

