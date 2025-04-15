from odoo import models, fields


class InheritResCompany(models.Model):
    _inherit = "res.company"

    attendance_work_entry_type_id = fields.Many2one(
        comodel_name="hr.work.entry.type", string="Default Attendance Work Entry type")
