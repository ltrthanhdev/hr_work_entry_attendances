from odoo import models


class InheritHrLeave(models.Model):
    _inherit = "hr.leave"

    def _cancel_work_entry_conflict(self):
        # generate work entries if Company set `Generate Work Entries mode` manual
        work_entries_vals_list = []
        for leave in self:
            contracts = leave.employee_id.sudo()._get_contracts(
                date_from=leave.date_from, date_to=leave.date_to, states=['open', 'close'])
            work_entries_vals_list += contracts.filtered(
                    func=lambda hc: hc.employee_id.company_id.generate_work_entries_mode == 'manual'
            )._get_work_entries_values(date_start=leave.date_from, date_stop=leave.date_to)
        return super(InheritHrLeave, self)._cancel_work_entry_conflict()
