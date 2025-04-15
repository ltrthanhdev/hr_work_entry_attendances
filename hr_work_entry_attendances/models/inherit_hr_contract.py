from odoo import models, api, _
from odoo.osv.expression import OR


class InheritHrContract(models.Model):
    _inherit = "hr.contract"

    def _get_more_vals_leave_interval(self, interval, leaves):
        more_vals_leave_interval = super()._get_more_vals_leave_interval(interval, leaves)
        for resource_leave in leaves:
            if interval[0] >= resource_leave[0] and interval[1] <= resource_leave[1]:
                more_vals_leave_interval.append(('employee_attendance_id', resource_leave[2].employee_attendance_id.id))
        return more_vals_leave_interval

    def _get_sub_leave_domain(self):
        domain = super()._get_sub_leave_domain()
        return OR([
            domain,
            [('employee_attendance_id.employee_id', 'in', self.employee_id.ids),
             ('time_type', '=', 'employee_attendance')]
        ])
