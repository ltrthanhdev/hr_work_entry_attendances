from odoo import models, fields, api


class InheritResCompany(models.Model):
    _inherit = "res.company"
    # const
    GENERATE_WORK_ENTRIES_MODES = [('auto', "Automatically"), ('manual', "Manually")]

    attendance_work_entry_type_id = fields.Many2one(
        comodel_name="hr.work.entry.type", string="Default Attendance Work Entry type",
        default=lambda self: self.env.ref(
            xml_id='hr_work_entry.work_entry_type_attendance', raise_if_not_found=False).id)
    generate_work_entries_mode = fields.Selection(
        selection=GENERATE_WORK_ENTRIES_MODES, string="Generate Work Entries mode", default='manual', required=True)
