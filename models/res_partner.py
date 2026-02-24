from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    
    def _default_activity_type(self):
        return "otros"

    activity_type = fields.Selection(
        [
            ("actividad_empresarial", "Actividad Empresarial"),
            ("servicios", "Servicios Profesionales"),
            ("arrendamiento", "Arrendamiento"),
            ("fletes", "Fletes"),
            ("otros", "Otros"),
        ],
        string="Tipo de Actividad Fiscal",
        default=_default_activity_type,
    )
