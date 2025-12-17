from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SportsField(models.Model):
    _name = 'sports.field'
    _description = 'Cancha Deportiva'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Nombre',
        required=True,
        tracking=True
    )
    
    code = fields.Char(
        string='Código',
        required=True,
        copy=False,
        tracking=True
    )
    
    sport_type = fields.Selection([
        ('football', 'Fútbol'),
        ('basketball', 'Basketball'),
        ('tennis', 'Tenis'),
        ('volleyball', 'Volleyball'),
        ('paddle', 'Paddle'),
        ('multipurpose', 'Multiuso'),
    ], string='Tipo de Deporte', required=True, tracking=True)
    
    surface_type = fields.Selection([
        ('grass', 'Césped Natural'),
        ('synthetic', 'Césped Sintético'),
        ('concrete', 'Concreto'),
        ('parquet', 'Parquet'),
        ('clay', 'Arcilla'),
    ], string='Tipo de Superficie', required=True)
    
    capacity = fields.Integer(
        string='Capacidad (jugadores)',
        required=True,
        default=10
    )
    
    hourly_rate = fields.Float(
        string='Tarifa por Hora',
        required=True,
        tracking=True
    )
    
    active = fields.Boolean(
        string='Activa',
        default=True,
        tracking=True
    )
    
    description = fields.Text(string='Descripción')
    
    # Horarios de disponibilidad
    opening_time = fields.Float(
        string='Hora de Apertura',
        required=True,
        default=7.0,
        help='Formato 24 horas (ej: 7.0 = 7:00 AM, 14.5 = 2:30 PM)'
    )
    
    closing_time = fields.Float(
        string='Hora de Cierre',
        required=True,
        default=22.0,
        help='Formato 24 horas'
    )
    
    # Días laborales
    monday = fields.Boolean(string='Lunes', default=True)
    tuesday = fields.Boolean(string='Martes', default=True)
    wednesday = fields.Boolean(string='Miércoles', default=True)
    thursday = fields.Boolean(string='Jueves', default=True)
    friday = fields.Boolean(string='Viernes', default=True)
    saturday = fields.Boolean(string='Sábado', default=True)
    sunday = fields.Boolean(string='Domingo', default=True)
    
    # Estadísticas
    booking_count = fields.Integer(
        string='Total Reservas',
        compute='_compute_booking_stats'
    )
    
    booking_ids = fields.One2many(
        'sports.booking',
        'field_id',
        string='Reservas'
    )
    
    image = fields.Image(string='Imagen', max_width=1024, max_height=1024)
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'El código de la cancha debe ser único.'),
    ]

    @api.constrains('capacity')
    def _check_capacity(self):
        for rec in self:
            if rec.capacity < 2:
                raise ValidationError('La capacidad debe ser al menos 2 jugadores.')

    @api.constrains('opening_time', 'closing_time')
    def _check_hours(self):
        for rec in self:
            if rec.opening_time < 0 or rec.opening_time >= 24:
                raise ValidationError('La hora de apertura debe estar entre 0 y 23:59.')
            if rec.closing_time < 0 or rec.closing_time > 24:
                raise ValidationError('La hora de cierre debe estar entre 0 y 24:00.')
            if rec.closing_time <= rec.opening_time:
                raise ValidationError('La hora de cierre debe ser posterior a la hora de apertura.')

    @api.constrains('hourly_rate')
    def _check_rate(self):
        for rec in self:
            if rec.hourly_rate <= 0:
                raise ValidationError('La tarifa debe ser mayor a 0.')

    @api.depends('booking_ids')
    def _compute_booking_stats(self):
        for rec in self:
            rec.booking_count = len(rec.booking_ids)

    def action_view_bookings(self):
        self.ensure_one()
        return {
            'name': _('Reservas de %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'sports.booking',
            'view_mode': 'tree,form,calendar',
            'domain': [('field_id', '=', self.id)],
            'context': {'default_field_id': self.id}
        }