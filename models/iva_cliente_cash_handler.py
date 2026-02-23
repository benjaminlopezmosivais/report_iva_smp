from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class ReportIvaClienteCashHandler(models.AbstractModel):
    _name = "report_iva_cliente_cash_handler"
    _inherit = "account.report.custom.handler"
    _description = "IVA por Cliente (Flujo Fiscal) - Handler"

    def _custom_options_initializer(self, report, options, previous_options=None):
        _logger.warning(">>> CUSTOM initializer ejecutado")
        return options

    # def _custom_get_lines(self, report, options, line_id=None):
    def _custom_line_postprocessor(self, report, options, lines):
        _logger.warning(">>> Entró a custom_line_postprocessor con %s líneas", len(lines))
        _logger.warning(">>> CUSTOM initializer ejecutado")
        # 1) fechas del filtro del reporte
        date_from = options.get("date", {}).get("date_from")
        date_to = options.get("date", {}).get("date_to")

        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "=", "paid"),
        ]
        if date_from:
            domain.append(("invoice_date", ">=", date_from))
        if date_to:
            domain.append(("invoice_date", "<=", date_to))

        moves = self.env["account.move"].search(domain, order="invoice_date asc, id asc")


        lines = []
        for mv in moves:
            # 2) Fecha de pago (para ejercicio: última fecha de pago conciliado)
            payment_date = self._get_last_payment_date(mv)
            #agregado
            vals = self._extract_tax_totals(mv) # <<--- aquí llamas tu método   

            # 3) Totales de impuestos (para ejercicio real: tax_totals)
            vals = self._extract_tax_totals(mv)

            # 4) ID parseable para XLSX
            #    OJO: si este método no existe en tu build, te digo cómo detectarlo con shell.
            line_id_ok = report._get_generic_line_id("account.move", mv.id)

            cols = [
                # Datos generales
                {"name": mv.partner_id.name or ""},  # partner
                {"name": mv.name or ""},             # num_fac
                {"name": mv.invoice_date and fields.Date.to_string(mv.invoice_date) or ""},  # fecha_fac
                {"name": payment_date and fields.Date.to_string(payment_date) or ""},        # fecha_pago

                # IVA trasladado
                {"name": vals.get("t_base_16", 0.0)},  # t_base_16
                {"name": vals.get("t_base_0", 0.0)},   # t_base_0
                {"name": vals.get("t_iva_16", 0.0)},   # t_iva_16
                {"name": vals.get("t_iva_0", 0.0)},    # t_iva_0
                # customer


                # IVA acreditable
                {"name": vals.get("a_base_16", 0.0)},      # a_base_16
                {"name": vals.get("a_base_8", 0.0)},       # a_base_8
                {"name": vals.get("a_base_0", 0.0)},       # a_base_0
                {"name": vals.get("a_base_exenta", 0.0)},  # a_base_exenta

                {"name": vals.get("a_iva_16", 0.0)},       # a_iva_16
                {"name": vals.get("a_iva_8", 0.0)},        # a_iva_8
                {"name": vals.get("a_iva_0", 0.0)},        # a_iva_0
                {"name": vals.get("a_iva_exento", 0.0)},   # a_iva_exento

                {"name": vals.get("a_iva_16_imp", 0.0)},   # a_iva_16_imp
                {"name": vals.get("a_no_deducible", 0.0)}, # a_no_deducible
                {"name": vals.get("a_no_objeto", 0.0)},    # a_no_objeto
                # vendor
                   #  gasto

                # Retenciones
                {"name": vals.get("riva_fletes_4", 0.0)},        # riva_fletes_4
                {"name": vals.get("riva_servprof_1067", 0.0)},   # riva_servprof_1067
                {"name": vals.get("riva_arr_1067", 0.0)},        # riva_arr_1067
                {"name": vals.get("risr_servprof_10", 0.0)},     # risr_servprof_10
                {"name": vals.get("risr_arr_10", 0.0)},          # risr_arr_10
                {"name": vals.get("risr_resico_125", 0.0)},      # risr_resico_125
                #vendor 
                   # gasto
                # Totales
                {"name": vals.get("precio_sin_iva", 0.0)},             # precio_sin_iva
                {"name": vals.get("iva", 0.0)},             # iva
                {"name": vals.get("total_neto", 0.0)},             # total_neto
            ]


            lines.append({
                "id": line_id_ok,
                "name": mv.partner_id.name or "Factura",
                "level": 2,
                "unfoldable": False,
                "columns": cols,
            })

        return lines

    def _get_last_payment_date(self, mv):
        """
        Intenta obtener la fecha del último pago conciliado.
        Para el ejercicio: suficiente con buscar pagos vinculados por reconciliación.
        """
        # movimientos conciliados en líneas por cobrar:
        receivable_lines = mv.line_ids.filtered(lambda l: l.account_id.account_type == "asset_receivable")
        dates = []

        # matched_credit_ids suelen apuntar a parcialidades/conciliaciones de pago
        for line in receivable_lines:
            for m in line.matched_credit_ids:
                if m.credit_move_id and m.credit_move_id.move_id:
                    dates.append(m.credit_move_id.move_id.date)
            for m in line.matched_debit_ids:
                if m.debit_move_id and m.debit_move_id.move_id:
                    dates.append(m.debit_move_id.move_id.date)

        return max(dates) if dates else False

    # def _extract_tax_totals(self, mv):
    #     """
    #     Para arrancar: usa mv.tax_totals (es lo más estable para UI/reporte).
    #     Luego refinamos a tu estructura exacta (16%, 8%, 0, exento, retenciones, etc.)
    #     """
    #     res = {
    #         "t_base_16": 0.0,
    #         "t_base_0": 0.0,
    #         "t_iva_16": 0.0,
    #         "t_iva_0": 0.0,
    #         "iva_neto": 0.0,
    #     }

    #     tax_totals = mv.tax_totals or {}
    #     amount_total = mv.amount_total or 0.0
    #     amount_untaxed = mv.amount_untaxed or 0.0
    #     amount_tax = amount_total - amount_untaxed

    #     # EJERCICIO: por ahora lo metemos como “IVA Neto” el total de impuesto
    #     res["iva_neto"] = amount_tax

    #     # Si quieres ya separar 16 vs 0, hay que mapear por taxes/tax groups (lo hacemos en el siguiente paso)
    #     return res

    def _extract_tax_totals(self, mv):
            """
            Extrae los impuestos reales de la factura y los acomoda en las columnas.
            """
            res = {
                # IVA trasladado
                "t_base_16": 0.0,
                "t_base_0": 0.0,
                "t_iva_16": 0.0,
                "t_iva_0": 0.0,

                # IVA acreditable
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

                # Retenciones
                "riva_fletes_4": 0.0,
                "riva_servprof_1067": 0.0,
                "riva_arr_1067": 0.0,
                "risr_servprof_10": 0.0,
                "risr_arr_10": 0.0,
                "risr_resico_125": 0.0,

                # Totales
                "precio_sin_iva": 0.0,
                "iva": 0.0,
                "total_neto": 0.0,     
            }

            #  Bases desde líneas de producto
            for line in mv.invoice_line_ids:
                base = line.price_subtotal
                for tax in line.tax_ids:
                    name = tax.name.lower()
                    amt = tax.amount
                    if amt == 16 and tax.type_tax_use == "sale":
                        res["t_base_16"] += base
                    elif amt == 0 and tax.type_tax_use == "sale":
                        res["t_base_0"] += base
                    elif "exento" in name:
                        res["a_base_exenta"] += base
                    elif amt == 8 and tax.type_tax_use == "sale":
                        res["a_base_8"] += base
                    elif amt == 16 and tax.type_tax_use == "purchase":
                        res["a_base_16"] += base

        #    # Bases desde líneas de producto
        #     for tax_line in mv.line_ids.filtered(lambda l: l.tax_line_id):
        #         tax = tax_line.tax_line_id
        #         name = tax.name.lower()
        #         amt = tax.amount

        #         if amt == 16 and tax.type_tax_use == "sale":
        #             res["t_iva_16"] += abs(tax_line.balance)   # aquí sí es el impuesto real
        #         elif amt == 0 and tax.type_tax_use == "sale":
        #             res["t_iva_0"] += abs(tax_line.balance)
        #         elif "exento" in name:
        #             res["a_iva_exento"] += abs(tax_line.balance)
        #         elif amt == 8 and tax.type_tax_use == "sale":
        #             res["a_iva_8"] += abs(tax_line.balance)
        #         elif amt == 16 and tax.type_tax_use == "purchase":
        #             res["a_iva_16"] += abs(tax_line.balance)


            # Importes reales desde líneas de impuestos
            for tax_line in mv.line_ids.filtered(lambda l: l.tax_line_id):
                tax = tax_line.tax_line_id
                name = tax.name.lower()
                amt = tax.amount

                # IVA trasladado
                if amt == 16 and tax.type_tax_use == "sale":
                    res["t_iva_16"] += tax_line.balance
                elif amt == 0 and tax.type_tax_use == "sale":
                    res["t_iva_0"] += tax_line.balance

                # IVA acreditable
                elif amt == 16 and tax.type_tax_use == "purchase":
                    res["a_iva_16"] += tax_line.balance
                elif amt == 8 and tax.type_tax_use == "purchase":
                    res["a_iva_8"] += tax_line.balance
                elif amt == 0 and tax.type_tax_use == "purchase":
                    res["a_iva_0"] += tax_line.balance
                elif "exento" in name:
                    res["a_iva_exento"] += tax_line.balance

                # Retenciones
                elif amt == -4:
                    res["riva_fletes_4"] += tax_line.balance
                elif abs(amt - -10.67) < 0.01:  # 10.67% retención
                    res["riva_servprof_1067"] += tax_line.balance
                elif amt == -10:
                    res["risr_servprof_10"] += tax_line.balance
                elif amt == -1.25:
                    res["risr_resico_125"] += tax_line.balance

            res["precio_sin_iva"] = mv.amount_untaxed

            # Neto = total factura
            res["iva"] = mv.amount_tax

            # total base + iva
            res["total_neto"] = mv.amount_total
            return res
