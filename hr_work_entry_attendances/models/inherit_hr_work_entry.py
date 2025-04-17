from odoo import models, fields


class InheritHrWorkEntry(models.Model):
    _inherit = "hr.work.entry"
    _rec_name = "code"

    employee_attendance_id = fields.Many2one(comodel_name="hr.attendance", string="Employee Attendance")

    def _is_duration_computed_from_calendar(self):
        return super()._is_duration_computed_from_calendar() or bool(
            not self.work_entry_type_id and self.employee_attendance_id)

    def write(self, vals):
        if 'state' in vals and vals['state'] == 'cancelled':
            self.mapped('employee_attendance_id').filtered(lambda ha: ha.state != 'refuse').action_cancel()
        return super().write(vals)

    def _reset_conflicting_state(self):
        super()._reset_conflicting_state()
        attendances = self.filtered(lambda w: w.work_entry_type_id and not w.work_entry_type_id.is_leave)
        attendances.write({'employee_attendance_id': False})

    def _check_if_error(self):
        res = super()._check_if_error()
        conflict_with_leaves = self._compute_conflicts_attendances_to_approve()
        return res or conflict_with_leaves

    def _compute_conflicts_attendances_to_approve(self):
        if not self:
            return False

        self.flush_recordset(['date_start', 'date_stop', 'employee_id', 'active'])
        self.env['hr.attendance'].flush_model(['check_in', 'check_out', 'attendance_state', 'employee_id'])

        query = """
            SELECT
                b.id AS work_entry_id,
                ha.id AS employee_attendance_id
            FROM hr_work_entry b
            INNER JOIN hr_attendance ha ON b.employee_id = ha.employee_id
            WHERE
                b.active = TRUE AND
                b.id IN %s AND
                ha.check_in < b.date_stop AND
                ha.check_out > b.date_start AND
                ha.check_out < b.date_stop AND
                ha.attendance_state IN ('draft');
        """
        self.env.cr.execute(query, [tuple(self.ids)])
        conflicts = self.env.cr.dictfetchall()
        for res in conflicts:
            self.browse(res.get('work_entry_id')).write({
                'state': 'conflict',
                'employee_attendance_id': res.get('employee_attendance_id')
            })
        return bool(conflicts)
