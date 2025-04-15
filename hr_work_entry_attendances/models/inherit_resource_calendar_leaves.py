from odoo import models, fields, api, _


class InheritResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    employee_attendance_id = fields.Many2one(comodel_name="hr.attendance", string="Employee Attendance")
    time_type = fields.Selection(
        selection_add=[('employee_attendance', "Employee Attendance")], ondelete={'overtime': "set default"})
