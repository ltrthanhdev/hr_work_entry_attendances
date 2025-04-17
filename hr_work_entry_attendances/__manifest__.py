{
    'name': 'Addons: Attendances to Work Entries',
    'version': '17.0.0.0.1',
    'category': 'Human Resources',
    'summary': """ Making Attendances to Work Entries """,
    'description': 'This module will make Work Entries while employee check-in/check-out',
    'author': 'L.Tr.Thanh',
    'maintainer': 'L.Tr.Thanh',
    'depends': ['base', 'hr_attendance', 'mail', 'hr_work_entry_contract'],
    'data': [
        # security

        # data

        # demo

        # wizard
        'wizard/inherit_res_config_settings_views.xml',

        # views
        'views/inherit_hr_attendance_views.xml',
        'views/inherit_resource_calendar_leaves_views.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'hr_work_entry_attendances/static/src/xml/gantt_renderer.xml'
        ],
    },
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
    'price': 14.98,
    'currency': 'USD',
    'post_init_hook': '_validate_existing_work_entries',
}
