from pytz import UTC
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _


class InheritHrAttendance(models.Model):
    _name = "hr.attendance"
    _inherit = ["hr.attendance", "mail.activity.mixin"]
    ATTENDANCE_STATUSES = [('draft', "To confirm"), ('validate', "Validate"), ('cancel', "Cancel")]

    attendance_state = fields.Selection(selection=ATTENDANCE_STATUSES, string="State", tracking=True, default='draft')
    resource_calendar_id = fields.Many2one(
        comodel_name='resource.calendar', compute='_compute_resource_calendar_id', store=True, readonly=False,
        copy=False, string="Resource Calendar")
    to_confirm = fields.Boolean(string="To confirm", compute="_compute_to_confirm", store=True)

    @api.depends('check_in', 'check_out', 'employee_id', 'attendance_state')
    def _compute_to_confirm(self):
        for attendance in self:
            attendance.to_confirm = attendance.check_to_confirm()

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
        # send notify
        self.activity_update()

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
        # 4. send notify (if necessary)
        self.activity_update()

    def action_draft(self):
        """ update state to 'draft' """
        self.attendance_state = 'draft'
        self.activity_update()

    @api.model
    def create(self, vals):
        new_attendance = super(InheritHrAttendance, self).create(vals)
        if vals.get('check_out') and not new_attendance.check_to_confirm():
            new_attendance.action_validate()
        new_attendance.activity_update()
        return new_attendance

    def write(self, changes):
        res = super(InheritHrAttendance, self).write(changes)
        to_confirm = self.check_to_confirm()
        if changes.get('check_out') and not to_confirm:
            self.action_validate()
        return res

    def unlink(self):
        self.remove_related_resource_leaves()
        self.remove_related_work_entries()
        return super(InheritHrAttendance, self).unlink()

    def get_employee_calendar(self):
        return self.employee_id._get_calendar()

    def check_to_confirm(self):
        # check the attendance need to confirm
        self.ensure_one()
        to_confirm = False
        employee_calendar = self.get_employee_calendar()
        if not self.check_out or not self.check_in or not employee_calendar:
            return to_confirm
        start_dt = self.check_in
        end_dt = self.check_out
        if not start_dt.tzinfo:
            start_dt = start_dt.replace(tzinfo=UTC)
        if not end_dt.tzinfo:
            end_dt = end_dt.replace(tzinfo=UTC)
        work_time_per_day_list = self.employee_id.list_work_time_per_day(
            from_datetime=start_dt, to_datetime=end_dt, calendar=employee_calendar)
        # if any work-time per work-days is not enough, need a confirmation
        for work_date, work_time in work_time_per_day_list:
            matched_calendar_attendances = employee_calendar.attendance_ids.filtered(
                lambda ca: ca.dayofweek == work_date.weekday().__str__())
            duration_days = sum(matched_calendar_attendances.mapped('duration_days'))
            if duration_days > work_time:
                to_confirm = True
        return to_confirm

    def get_responsible_for_confirmation(self):
        # the responsible based on Employee's attendance_manager_id by default
        return self.employee_id.attendance_manager_id

    def activity_update(self):
        """ send notify to the responsible for confirmation (if necessary) """
        skip_notify = self.env.context.get('mail_activity_automation_skip')
        if skip_notify:
            return skip_notify
        to_clean = to_do = self.env['hr.attendance']
        today = fields.Date.today()
        confirm_activity = self.env.ref(xml_id='hr_work_entry_attendances.attendance_to_confirm_mail_act_type')
        for attendance in self:
            attendance_state = attendance.attendance_state
            if attendance_state == 'draft' and attendance.check_to_confirm():
                activity_type = confirm_activity
                note = _("The attendance of employee %(employee_name)s need to validate for some reasons. Please "
                         "check and make confirmation.", employee_name=attendance.employee_id.name or str())
                responsible_ids = attendance.get_responsible_for_confirmation().ids
                for responsible_id in responsible_ids:
                    date_deadline = today
                    if attendance.check_in:
                        date_deadline = (attendance.check_in - relativedelta(
                            **{activity_type.delay_unit: activity_type.delay_count or 0})).date()
                    attendance.with_context(short_name=False).activity_schedule(
                        activity_type_id=activity_type.id,
                        date_deadline=date_deadline,
                        note=note, user_id=responsible_id,
                    )
            if attendance_state == 'validate':
                to_do |= attendance
            if attendance_state == 'cancel':
                to_clean |= attendance
        if to_clean:
            to_clean.activity_unlink(['hr_work_entry_attendances.attendance_to_confirm_mail_act_type'])
        if to_do:
            to_do.activity_feedback(['hr_work_entry_attendances.attendance_to_confirm_mail_act_type'])
