from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class ReportIvaClienteCashHandler(models.AbstractModel):
    _name = "report_iva_cliente_cash_handler"
    _inherit = "account.report.custom.handler"
    _description = "IVA por Cliente (Flujo Fiscal) - Handler"

    def _custom_options_initializer(self, report, options, previous_options=None):
        return options

    def _custom_line_postprocessor(self, report, options, lines):

        date_from = options.get("date", {}).get("date_from")
        date_to = options.get("date", {}).get("date_to")

        domain = [
            ("move_type", "in", ["out_invoice", "in_invoice","in_refund","out_refund"]),
            ("state", "=", "posted"),
            ("payment_state", "=", "paid"),
        ]

        moves = self.env["account.move"].search(domain, order="invoice_date asc")

        result_lines = lines[:1]

        currency = self.env.company.currency_id

        for mv in moves:

            payment_date = self._get_last_payment_date(mv)

            # 🔥 FILTRO POR FECHA DE PAGO (FLUJO REAL)
            if date_from:
                if not payment_date or payment_date < fields.Date.from_string(date_from):
                    continue

            if date_to:
                if not payment_date or payment_date > fields.Date.from_string(date_to):
                    continue

            vals = self._extract_tax_totals(mv)
            line_id_ok = report._get_generic_line_id("account.move", mv.id)

            cols = [
                {"name": mv.partner_id.name or ""},
                {"name": mv.partner_id.vat or ""},
                {"name": dict(mv._fields["move_type"].selection).get(mv.move_type)},  # 
                {"name": mv.name or ""},
                {"name": fields.Date.to_string(mv.invoice_date) if mv.invoice_date else ""},
                {"name": fields.Date.to_string(payment_date) if payment_date else ""},
                {"name": currency.round(vals["t_base_16"]), "class": "number"},
                {"name": currency.round(vals["t_base_8"]), "class": "number"},
                {"name": currency.round(vals["t_base_0"]), "class": "number"},
                {"name": currency.round(vals["t_iva_16"]), "class": "number"},
                {"name": currency.round(vals["t_iva_8"]), "class": "number"},
                {"name": currency.round(vals["t_iva_0"]), "class": "number"},

                {"name": currency.round(vals["a_base_16"]), "class": "number"},
                {"name": currency.round(vals["a_base_8"]), "class": "number"},
                {"name": currency.round(vals["a_base_0"]), "class": "number"},
                {"name": currency.round(vals["a_base_exenta"]), "class": "number"},

                {"name": currency.round(vals["a_iva_16"]), "class": "number"},
                {"name": currency.round(vals["a_iva_8"]), "class": "number"},
                {"name": currency.round(vals["a_iva_0"]), "class": "number"},
                {"name": currency.round(vals["a_iva_exento"]), "class": "number"},

                {"name": currency.round(vals["a_iva_16_imp"]), "class": "number"},
                {"name": currency.round(vals["a_no_deducible"]), "class": "number"},
                {"name": currency.round(vals["a_no_objeto"]), "class": "number"},

                {"name": currency.round(vals["riva_fletes_4"]), "class": "number"},
                {"name": currency.round(vals["riva_servprof_1067"]), "class": "number"},
                {"name": currency.round(vals["riva_arr_1067"]), "class": "number"},
                {"name": currency.round(vals["risr_servprof_10"]), "class": "number"},
                {"name": currency.round(vals["risr_arr_10"]), "class": "number"},
                {"name": currency.round(vals["risr_resico_125"]), "class": "number"},

                {"name": currency.round(vals["precio_sin_iva"]), "class": "number"},
                {"name": currency.round(vals["iva"]), "class": "number"},
                {"name": currency.round(vals["total_neto"]), "class": "number"},
            ]

            result_lines.append({
                "id": line_id_ok,
                "name": "",
                "level": 2,
                "unfoldable": False,
                "columns": cols,
            })

        return result_lines

    # ----------------------------------------------------------
    # FECHA DE PAGO
    # ----------------------------------------------------------

    def _get_last_payment_date(self, mv):

        account_types = []

        if mv.move_type in ("out_invoice", "out_refund"):
            account_types = ["asset_receivable"]

        elif mv.move_type in ("in_invoice", "in_refund"):
            account_types = ["liability_payable"]

        lines = mv.line_ids.filtered(
            lambda l: l.account_id.account_type in account_types
        )

        dates = []

        for line in lines:
            for m in line.matched_credit_ids:
                if m.credit_move_id and m.credit_move_id.move_id:
                    dates.append(m.credit_move_id.move_id.date)

            for m in line.matched_debit_ids:
                if m.debit_move_id and m.debit_move_id.move_id:
                    dates.append(m.debit_move_id.move_id.date)

        return max(dates) if dates else False

    # ----------------------------------------------------------
    # EXTRACCIÓN COMPLETA CORREGIDA
    # ----------------------------------------------------------

    def _extract_tax_totals(self, mv):
        res = {
            "t_base_16": 0.0,
            "t_base_8": 0.0,
            "t_base_0": 0.0,
            "t_iva_16": 0.0,
            "t_iva_8": 0.0,
            "t_iva_0": 0.0,

            "a_base_16": 0.0,
            "a_base_8": 0.0,
            "a_base_0": 0.0,
            "a_base_exenta": 0.0,
            "a_iva_16": 0.0,
            "a_iva_8": 0.0,
            "a_iva_0": 0.0,
            "a_iva_exento": 0.0,
            "a_iva_16_imp": 0.0,
            "a_no_deducible": 0.0,
            "a_no_objeto": 0.0,

            "riva_fletes_4": 0.0,
            "riva_servprof_1067": 0.0,
            "riva_arr_1067": 0.0,
            "risr_servprof_10": 0.0,
            "risr_arr_10": 0.0,
            "risr_resico_125": 0.0,

            "precio_sin_iva": 0.0,
            "iva": 0.0,
            "total_neto": 0.0,
        }

        # ----------------------------------
        # IVA TRASLADADO (VENTAS)
        # ----------------------------------
        res["t_base_16"] , res["t_iva_16"] = self._get_tax_base_and_amount(
            mv,
            tax_type="sale",
            tax_rate=16
        )

        res["t_base_8"] ,res["t_iva_8"]= self._get_tax_base_and_amount(
            mv,
            tax_type="sale",
            tax_rate=8
        )

        res["t_base_0"] , res["t_iva_0"] = self._get_tax_base_and_amount(
            mv,
            tax_type="sale",
            tax_rate=0
        )

        # ----------------------------------
        # IVA ACREDITABLE (COMPRAS)
        # ----------------------------------

        res["a_base_16"], res["a_iva_16"] = self._get_tax_base_and_amount(
            mv,
            tax_type="purchase",
            tax_rate=16
        )

        res["a_base_8"], res["a_iva_8"] = self._get_tax_base_and_amount(
            mv,
            tax_type="purchase",
            tax_rate=8
        )

        res["a_base_0"], res["a_iva_0"] = self._get_tax_base_and_amount(
            mv,
            tax_type="purchase",
            tax_rate=0
        )

        res["a_no_deducible"] = self._get_tax_amount_by_external_id(
            mv,
            "iva_cliente_cash_report.tax_no_deducible_16"
        )
        
        res["a_base_exenta"] = self._get_tax_amount_by_external_id(
            mv,
            "iva_cliente_cash_report.tax_a_base_exenta"
        )
        
        res["a_no_objeto"] = self._get_tax_amount_by_external_id(
            mv,
            "iva_cliente_cash_report.tax_a_no_objeto"
        )

        res["_iva_16_imp"]= self._get_tax_amount_for_account(mv, "118.02.01")

        # ----------------------------------
        # RETENCIONES (un solo loop)
        # ----------------------------------

        for tax_line in mv.line_ids.filtered(lambda l: l.tax_line_id):
            tax = tax_line.tax_line_id
            amount = abs(tax_line.balance)

            if tax.type_tax_use == "sale":
                activity = mv.partner_id.activity_type

                if activity == "fletes":
                    res["riva_fletes_4"] += amount * .04

                elif activity == "servicios":
                    res["riva_servprof_1067"] += amount * .1067

                elif activity == "arrendamiento":
                    res["riva_arr_1067"] += amount * .1067
                    res["risr_arr_10"] += amount* .10

                elif activity == "actividad_empresarial":
                    res["risr_servprof_10"] += amount * .10

                elif activity == "otros":
                    res["risr_resico_125"] += amount * .0125


        # ----------------------------------
        # TOTALES MULTIMONEDA
        # ----------------------------------

        res["precio_sin_iva"] = mv.amount_untaxed_signed
        res["iva"] = mv.amount_tax_signed
        res["total_neto"] = mv.amount_total_signed

        return res

    def _get_tax_base_and_amount(self, mv, tax_type="sale" , tax_rate=None):

        base = 0.0
        amount = 0.0

        # BASE
        for line in mv.line_ids:
            if line.account_id.account_type in ("income", "expense"):

                for tax in line.tax_ids:
                    if tax.type_tax_use == tax_type:

                        if tax_rate is None or tax.amount == tax_rate:
                            base += abs(line.balance)

        # IMPUESTO
        for line in mv.line_ids.filtered(lambda l: l.tax_line_id):

            tax = line.tax_line_id

            if tax.type_tax_use == tax_type:

                if tax_rate is None or tax.amount == tax_rate:
                    amount += abs(line.balance)

        return base, amount

    def _get_tax_by_external_id(self, mv, tax_external_id):

        tax = self.env.ref(tax_external_id, raise_if_not_found=False)

        if not tax:
            return 0.0, 0.0

        base = 0.0
        amount = 0.0

        for line in mv.line_ids:
            if tax in line.tax_ids:
                base += abs(line.balance)

        for line in mv.line_ids.filtered(lambda l: l.tax_line_id == tax):
            amount += abs(line.balance)

        return base, amount



    def _get_tax_amount_by_external_id(self, mv, tax_external_id):

        tax = self.env.ref(tax_external_id, raise_if_not_found=False)

        if not tax:
            return 0.0

        amount = 0.0
        for line in mv.line_ids:
            if tax in line.tax_ids:
                amount += abs(line.balance)

        for line in mv.line_ids.filtered(lambda l: l.tax_line_id == tax):
            amount += abs(line.balance)

        return amount



    ##Importacion
    def _get_tax_amount_for_account(self, mv, account_code):
        target_account = self.env['account.account'].search([('code', '=', account_code)], limit=1)
        amount = 0.0
        if target_account:
            for line in mv.line_ids.filtered(lambda l: l.tax_line_id and l.account_id == target_account):
                amount += abs(line.balance)
        return amount
