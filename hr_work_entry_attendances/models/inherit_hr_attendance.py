from odoo import models, fields, api, _


class InheritHrAttendance(models.Model):
    _inherit = "hr.attendance"
    ATTENDANCE_STATUSES = [('draft', "To confirm"), ('validate', "Validate"), ('cancel', "Cancel")]

    attendance_state = fields.Selection(selection=ATTENDANCE_STATUSES, string="State", tracking=True, default='draft')
    resource_calendar_id = fields.Many2one(
        comodel_name='resource.calendar', compute='_compute_resource_calendar_id', store=True, readonly=False,
        copy=False, string="Resource Calendar")

    @api.depends('employee_id')
    def _compute_resource_calendar_id(self):
        for attendance in self:
            calendar = attendance.employee_id.resource_calendar_id
            range_stop = attendance.check_out
            if not range_stop:
                attendance.resource_calendar_id = False
                continue
            if 'hr.attendance' in self.env and attendance.employee_id:
                contracts = self.env['hr.contract'].search([
                    '|', ('state', 'in', ['open', 'close']),
                    '&', ('state', '=', 'draft'),
                    ('kanban_state', '=', 'done'),
                    ('employee_id', '=', attendance.employee_id.id),
                    ('date_start', '<=', attendance.check_in.date()),
                    '|', ('date_end', '=', False),
                    ('date_end', '>=', attendance.check_out.date()),
                ])
                if contracts:
                    # If there are more than one contract they should all have the
                    # same calendar, otherwise a constraint is violated.
                    calendar = contracts[:1].resource_calendar_id
            attendance.resource_calendar_id = calendar or self.env.company.resource_calendar_id

    def action_validate(self):
        # make Work Entries
        self.create_resource_leaves()
        self.generate_attendance_work_entries()
        # set state 'validate'
        self.attendance_state = 'validate'

    def generate_attendance_work_entries(self):
        """
               Creates a leave work entry for each hr.attendance in self.
        """
        if not self:
            return
        #  Create a work entry for each attendance
        attendance_work_entries_vals = []
        for attendance in self:
            contracts = attendance.employee_id.sudo()._get_contracts(
                date_from=attendance.check_in.date(), date_to=attendance.check_out.date(), states=['open', 'close'])
            attendance_work_entries_vals += contracts._get_work_entries_values(
                        date_start=attendance.check_in, date_stop=attendance.check_out)
        new_attendance_work_entries = self.env['hr.work.entry'].create(attendance_work_entries_vals)
        if new_attendance_work_entries:
            # 2. Fetch overlapping work entries, grouped by employees
            start = min(self.mapped('check_in'), default=False)
            stop = max(self.mapped('check_out'), default=False)
            work_entry_groups = self.env['hr.work.entry']._read_group([
                ('date_start', '<', stop),
                ('date_stop', '>', start),
                ('employee_id', 'in', self.employee_id.ids),
            ], ['employee_id'], ['id:recordset'])
            work_entries_by_employee = {
                employee.id: work_entries for employee, work_entries in work_entry_groups
            }

            # 3. Archive work entries included in leaves
            included = self.env['hr.work.entry']
            overlappping = self.env['hr.work.entry']
            for work_entries in work_entries_by_employee.values():
                # Work entries for this employee
                new_employee_work_entries = work_entries & new_attendance_work_entries
                previous_employee_work_entries = work_entries - new_attendance_work_entries

                # Build intervals from work entries
                leave_intervals = new_employee_work_entries._to_intervals()
                conflicts_intervals = previous_employee_work_entries._to_intervals()

                # Compute intervals completely outside any leave
                # Intervals are outside, but associated records are overlapping.
                outside_intervals = conflicts_intervals - leave_intervals

                overlappping |= self.env['hr.work.entry']._from_intervals(outside_intervals)
                included |= previous_employee_work_entries - overlappping
            overlappping.write({'employee_attendance_id': False})
            included.write({'active': False})

    def create_resource_leaves(self):
        """ This method will create entry in resource calendar attendance object at the time of attendances validated
        """
        work_entries_vals = [attendance.prepare_resource_leave_vals() for attendance in self]
        return self.env['resource.calendar.leaves'].sudo().create(work_entries_vals)

    def prepare_resource_leave_vals(self):
        """ Hook method for others to inject data """
        self.ensure_one()
        return {
            'name': _("%s: Attendance", self.employee_id.name),
            'date_from': self.check_in,
            'date_to': self.check_out,
            'employee_attendance_id': self.id,
            'resource_id': self.employee_id.resource_id.id,
            'calendar_id': self.resource_calendar_id.id,
            'time_type': 'employee_attendance',
            'work_entry_type_id': self.employee_id.company_id.attendance_work_entry_type_id.id
        }

    def remove_related_resource_leaves(self):
        resource_leaves = self.env['resource.calendar.leaves']
        resource_leaves.search(domain=[
            ('employee_attendance_id', 'in', self.ids), ('time_type', '=', 'employee_attendance')]).unlink()
        return resource_leaves

    def remove_related_work_entries(self):
        work_entries = self.env['hr.work.entry']
        work_entries.search(domain=[('employee_attendance_id', 'in', self.ids)]).unlink()
        return work_entries

    def action_cancel(self):
        """ make Attendances cancelled -> unlink <resource.calendar.leaves> """
        # 1. unlink <resource.calendar.leaves>
        self.remove_related_resource_leaves()
        # 2. remove related Work Entries
        self.remove_related_work_entries()
        # 3. Update state to 'cancel'
        self.attendance_state = 'cancel'

    def action_draft(self):
        """ update state to 'draft' """
        self.attendance_state = 'draft'

    @api.model
    def create(self, vals):
        new_attendance = super(InheritHrAttendance, self).create(vals)

        return new_attendance

    def write(self, changes):
        res = super(InheritHrAttendance, self).write(changes)

        return res

    def unlink(self):
        self.remove_related_resource_leaves()
        self.remove_related_work_entries()
        return super(InheritHrAttendance, self).unlink()
