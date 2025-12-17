{
    'name': 'Reservación de Canchas Deportivas',
    'version': '17.0.1.0.0',
    'category': 'Services/Booking',
    'summary': 'Sistema completo de reservación de canchas deportivas',
    'description': """
        Sistema de Reservación de Canchas Deportivas
        =============================================
        * Gestión de canchas y horarios
        * Reservas con validaciones automáticas
        * Tres roles: Admin, Staff y Usuario Externo
        * Portal web para clientes
        * Restricciones de negocio avanzadas
    """,
    'author': 'Tu Empresa',
    'website': 'https://tuempresa.com',
    'depends': ['base', 'mail', 'portal', 'website'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/sports_field_views.xml',
        'views/booking_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}