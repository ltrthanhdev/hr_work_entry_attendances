{
    'name': 'Addons: Attendances to Work Entries',
    'version': '18.0.0.0.0',
    'category': 'Manage work entries',
    'summary': """ Synchronize Data between Attendances and Work Entries """,
    'description': 'This module will make Work Entries while employee check-in/check-out',
    'author': 'LTrThanh',
    'maintainer': 'LTrThanh',
    'depends': [
        'base',
        'hr_attendance',
        'mail',
        'hr_work_entry_holidays',
    ],
    'data': [
        # security

        # data

        # demo

        # wizard

        # views

    ],
    'assets': {
        'web.assets_backend': [

        ],
    },
    'images': [],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': '_validate_existing_work_entries',
}