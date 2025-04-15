from odoo import models, fields


class InheritHrWorkEntry(models.Model):
    _inherit = "hr.work.entry"
    _rec_name = "code"

    employee_attendance_id = fields.Many2one(comodel_name="hr.attendance", string="Employee Attendance")

    def _reset_conflicting_state(self):
        super()._reset_conflicting_state()
        attendances = self.filtered(lambda w: w.work_entry_type_id and not w.work_entry_type_id.is_leave)
        attendances.write({'employee_attendance_id': False})
