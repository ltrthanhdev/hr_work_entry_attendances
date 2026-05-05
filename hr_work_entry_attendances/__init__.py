from . import models


def _validate_existing_work_entries(env):
    env['hr.work.entry'].search(domain=[])._check_if_error()
