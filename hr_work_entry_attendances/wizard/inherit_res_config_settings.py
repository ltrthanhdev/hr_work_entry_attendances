from odoo import models, fields


class InheritResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    attendance_work_entry_type_id = fields.Many2one(
        comodel_name="hr.work.entry.type", string="Default Attendance Work Entry type",
        related="company_id.attendance_work_entry_type_id", readonly=False, store=True)
