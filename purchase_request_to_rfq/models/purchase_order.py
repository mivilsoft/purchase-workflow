# -*- coding: utf-8 -*-
# Copyright 2016 Eficent Business and IT Consulting Services S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, exceptions, fields, models

from datetime import datetime


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    document_count = fields.Integer(compute="_compute_document", string='# of Bills', copy=False, default=0)
    document_ids = fields.Many2many('account.invoice', compute="_compute_document", string='Bills', copy=False)
    dateState = fields.Date(
        'Fecha Aprox. de Arribo')

    landc_count = fields.Integer(compute="_compute_landc", string='# of Landed Cost', copy=False, default=0)
    landc_ids = fields.Many2many('stock.landed.cost', compute="_compute_landc", string='landed Cost', copy=False)
    @api.depends('invoice_ids','invoice_count')
    def _compute_document(self):
        for order in self:
            invoices = self.env['account.invoice'].search([('origin','=',order.name)])
        order.document_ids = invoices
        order.document_count = len(invoices)
    
    @api.depends('invoice_ids','invoice_count')
    def _compute_landc(self):
        for order in self:
            invoices = self.env['stock.picking'].search([('origin','=',order.name)])
            files = self.env['stock.landed.cost'].search([('picking_ids','=',invoices.name)])
        print("///////////////")
        print(invoices.name)
        order.landc_ids = files
        order.landc_count = len(files)
        
    @api.multi  
    def action_view_document(self):
        '''
        This function returns an action that display existing vendor bills of given purchase order ids.
        When only one found, show the vendor bill immediately.
        '''
        action = self.env.ref('account.action_invoice_tree2')
        result = action.read()[0]

        #override the context to get rid of the default filtering
        result['context'] = {'type': 'in_invoice', 'default_purchase_id': self.id}

        if not self.document_ids:
            # Choose a default account journal in the same currency in case a new invoice is created
            journal_domain = [
                ('type', '=', 'purchase'),
                ('company_id', '=', self.company_id.id),
                ('currency_id', '=', self.currency_id.id),
            ]
            default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)
            if default_journal_id:
                result['context']['default_journal_id'] = default_journal_id.id
        else:
            # Use the same account journal than a previous invoice
            result['context']['default_journal_id'] = self.document_ids[0].journal_id.id

        #choose the view_mode accordingly
        if len(self.document_ids) != 1:
            result['domain'] = "[('id', 'in', " + str(self.document_ids.ids) + ")]"
        elif len(self.document_ids) == 1:
            res = self.env.ref('account.invoice_supplier_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.document_ids.id
        return result

    @api.multi
    def action_view_landc(self):
        '''
        This function returns an action that display existing vendor bills of given purchase order ids.
        When only one found, show the vendor bill immediately.
        '''
        action = self.env.ref('stock_landed_costs.action_stock_landed_cost')
        result = action.read()[0]

        #override the context to get rid of the default filtering
        result['context'] = {'type': 'in_invoice', 'default_purchase_id': self.id}

        if not self.landc_ids:
            # Choose a default account journal in the same currency in case a new invoice is created
            journal_domain = [
                ('type', '=', 'purchase'),
                ('company_id', '=', self.company_id.id),
                ('currency_id', '=', self.currency_id.id),
            ]
            default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)
            if default_journal_id:
                result['context']['default_journal_id'] = default_journal_id.id
        else:
            # Use the same account journal than a previous invoice
            result['context']['default_journal_id'] = self.landc_ids[0].account_journal_id.id

        #choose the view_mode accordingly
        if len(self.landc_ids) != 1:
            result['domain'] = "[('id', 'in', " + str(self.landc_ids.ids) + ")]"
        elif len(self.landc_ids) == 1:
            res = self.env.ref('stock_landed_costs.view_stock_landed_cost_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.landc_ids.id
        return result

    def scheduler(self):
        purchase_orders = self.env['purchase.order'].search([])
        print(purchase_orders)
        for purchase_order_id in purchase_orders :
            if(purchase_order_id.dateState):
                aux = datetime.strptime(purchase_order_id.dateState, '%Y-%m-%d')
                resta=aux.date() - datetime.now().date()
                if (resta.days>=-2 and resta.days<=0):
                
                    # region PopUp
                    msg = u"Chequear Fecha Estimada de la Orden %s" % (purchase_order_id.name)

                    # Codigo para buscar a todos los Admin de Vehiculos
                    usuarios = self.env['res.groups'].search([('name', '=', 'Admin Vehículos')]).users
                    for user in usuarios:
                        print user.name
                        user.notify_info(msg, sticky=True)

    @api.multi
    def _purchase_request_confirm_message_content(self, request,
                                                  request_dict):
        self.ensure_one()
        if not request_dict:
            request_dict = {}
        title = _('Order confirmation %s for your Request %s') % (
            self.name, request.name)
        message = '<h3>%s</h3><ul>' % title
        message += _('The following requested items from Purchase Request %s '
                     'have now been confirmed in Purchase Order %s:') % (
            request.name, self.name)

        for line in request_dict.values():
            message += _(
                '<li><b>%s</b>: Ordered quantity %s %s, Planned date %s</li>'
            ) % (line['name'],
                 line['product_qty'],
                 line['product_uom'],
                 line['date_planned'],
                 )
        message += '</ul>'
        return message

    @api.multi
    def _purchase_request_confirm_message(self):
        request_obj = self.env['purchase.request']
        for po in self:
            requests_dict = {}
            for line in po.order_line:
                for request_line in line.sudo().purchase_request_lines:
                    request_id = request_line.request_id.id
                    if request_id not in requests_dict:
                        requests_dict[request_id] = {}
                    date_planned = "%s" % line.date_planned
                    data = {
                        'name': request_line.name,
                        'product_qty': line.product_qty,
                        'product_uom': line.product_uom.name,
                        'date_planned': date_planned,
                    }
                    requests_dict[request_id][request_line.id] = data
            for request_id in requests_dict:
                request = request_obj.sudo().browse(request_id)
                message = po._purchase_request_confirm_message_content(
                    request, requests_dict[request_id])
                request.message_post(body=message, subtype='mail.mt_comment')
        return True

    @api.multi
    def _purchase_request_line_check(self):
        for po in self:
            for line in po.order_line:
                for request_line in line.purchase_request_lines:
                    if request_line.sudo().purchase_state == 'done':
                        raise exceptions.Warning(
                            _('Purchase Request %s has already '
                              'been completed') % request_line.request_id.name)
        return True

    @api.multi
    def button_confirm(self):
        self._purchase_request_line_check()
        res = super(PurchaseOrder, self).button_confirm()
        self._purchase_request_confirm_message()
        return res


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    purchase_request_lines = fields.Many2many(
        'purchase.request.line',
        'purchase_request_purchase_order_line_rel',
        'purchase_order_line_id',
        'purchase_request_line_id',
        'Purchase Request Lines', readonly=True, copy=False)

    @api.multi
    def action_openRequestLineTreeView(self):
        """
        :return dict: dictionary value for created view
        """
        request_line_ids = []
        for line in self:
            request_line_ids += line.purchase_request_lines.ids

        domain = [('id', 'in', request_line_ids)]

        return {'name': _('Purchase Request Lines'),
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.request.line',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'domain': domain}
