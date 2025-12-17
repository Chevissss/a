from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class SportsBooking(models.Model):
    _name = 'sports.booking'
    _description = 'Reserva de Cancha'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'booking_date desc, start_time desc'

    name = fields.Char(
        string='Número de Reserva',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nuevo')
    )
    
    field_id = fields.Many2one(
        'sports.field',
        string='Cancha',
        required=True,
        tracking=True,
        domain=[('active', '=', True)]
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        tracking=True
    )
    
    booking_date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    
    start_time = fields.Float(
        string='Hora Inicio',
        required=True,
        help='Formato 24 horas (ej: 14.5 = 2:30 PM)'
    )
    
    end_time = fields.Float(
        string='Hora Fin',
        required=True,
        help='Formato 24 horas'
    )
    
    duration = fields.Float(
        string='Duración (horas)',
        compute='_compute_duration',
        store=True
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmada'),
        ('in_progress', 'En Progreso'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
    ], string='Estado', default='draft', required=True, tracking=True)
    
    total_amount = fields.Float(
        string='Monto Total',
        compute='_compute_total_amount',
        store=True
    )
    
    notes = fields.Text(string='Notas')
    
    phone = fields.Char(
        string='Teléfono',
        related='partner_id.phone',
        readonly=True
    )
    
    email = fields.Char(
        string='Email',
        related='partner_id.email',
        readonly=True
    )
    
    participants = fields.Integer(
        string='Número de Participantes',
        default=1
    )
    
    payment_status = fields.Selection([
        ('pending', 'Pendiente'),
        ('partial', 'Parcial'),
        ('paid', 'Pagado'),
    ], string='Estado de Pago', default='pending', tracking=True)
    
    # Campos relacionados para vistas
    sport_type = fields.Selection(
        related='field_id.sport_type',
        string='Deporte',
        store=True
    )
    
    hourly_rate = fields.Float(
        related='field_id.hourly_rate',
        string='Tarifa/Hora'
    )

    _sql_constraints = [
        ('check_dates', 'CHECK(end_time > start_time)', 
         'La hora de fin debe ser posterior a la hora de inicio.'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', _('Nuevo')) == _('Nuevo'):
            vals['name'] = self.env['ir.sequence'].next_by_code('sports.booking') or _('Nuevo')
        return super(SportsBooking, self).create(vals)

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for rec in self:
            rec.duration = rec.end_time - rec.start_time if rec.end_time > rec.start_time else 0

    @api.depends('duration', 'field_id.hourly_rate')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.duration * rec.field_id.hourly_rate

    @api.constrains('booking_date', 'start_time', 'end_time')
    def _check_booking_datetime(self):
        for rec in self:
            # 1. No permitir reservas en el pasado
            now = fields.Datetime.now()
            booking_datetime = datetime.combine(rec.booking_date, datetime.min.time())
            booking_datetime = booking_datetime.replace(
                hour=int(rec.start_time),
                minute=int((rec.start_time % 1) * 60)
            )
            
            if booking_datetime < now:
                raise ValidationError(
                    'No se pueden hacer reservas en fechas u horas pasadas.\n'
                    f'Fecha/hora de reserva: {booking_datetime.strftime("%Y-%m-%d %H:%M")}\n'
                    f'Fecha/hora actual: {now.strftime("%Y-%m-%d %H:%M")}'
                )
            
            # 2. Validar que la reserva sea con al menos X horas de anticipación
            min_advance_hours = 2
            if booking_datetime < (now + timedelta(hours=min_advance_hours)):
                raise ValidationError(
                    f'Las reservas deben hacerse con al menos {min_advance_hours} horas de anticipación.'
                )

    @api.constrains('start_time', 'end_time')
    def _check_time_range(self):
        for rec in self:
            if rec.start_time < 0 or rec.start_time >= 24:
                raise ValidationError('La hora de inicio debe estar entre 0:00 y 23:59.')
            if rec.end_time <= 0 or rec.end_time > 24:
                raise ValidationError('La hora de fin debe estar entre 0:01 y 24:00.')

    @api.constrains('duration')
    def _check_duration(self):
        for rec in self:
            # Duración mínima: 1 hora
            if rec.duration < 1:
                raise ValidationError('La duración mínima de una reserva es 1 hora.')
            # Duración máxima: 4 horas
            if rec.duration > 4:
                raise ValidationError('La duración máxima de una reserva es 4 horas.')
            # Solo permitir bloques de 0.5 horas
            if (rec.duration * 2) % 1 != 0:
                raise ValidationError('Las reservas solo pueden ser en bloques de 30 minutos (0.5, 1.0, 1.5, etc.).')

    @api.constrains('booking_date', 'field_id')
    def _check_field_availability_day(self):
        for rec in self:
            if not rec.field_id or not rec.booking_date:
                continue
            
            # Verificar que la cancha esté abierta ese día
            weekday = rec.booking_date.weekday()  # 0=Lunes, 6=Domingo
            day_fields = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            
            if not rec.field_id[day_fields[weekday]]:
                day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                raise ValidationError(
                    f'La cancha {rec.field_id.name} no está disponible los {day_names[weekday]}.'
                )

    @api.constrains('start_time', 'end_time', 'field_id')
    def _check_field_hours(self):
        for rec in self:
            if not rec.field_id:
                continue
            
            if rec.start_time < rec.field_id.opening_time:
                raise ValidationError(
                    f'La cancha {rec.field_id.name} abre a las {rec._format_time(rec.field_id.opening_time)}. '
                    f'No puede reservar antes de esa hora.'
                )
            
            if rec.end_time > rec.field_id.closing_time:
                raise ValidationError(
                    f'La cancha {rec.field_id.name} cierra a las {rec._format_time(rec.field_id.closing_time)}. '
                    f'No puede reservar después de esa hora.'
                )

    @api.constrains('booking_date', 'start_time', 'end_time', 'field_id', 'state')
    def _check_overlapping_bookings(self):
        for rec in self:
            if rec.state == 'cancelled':
                continue
            
            # Buscar reservas que se traslapen
            overlapping = self.search([
                ('id', '!=', rec.id),
                ('field_id', '=', rec.field_id.id),
                ('booking_date', '=', rec.booking_date),
                ('state', 'not in', ['cancelled']),
                '|',
                '&', ('start_time', '<', rec.end_time), ('end_time', '>', rec.start_time),
                '&', ('start_time', '<', rec.start_time), ('end_time', '>', rec.start_time),
            ])
            
            if overlapping:
                raise ValidationError(
                    f'Ya existe una reserva para la cancha {rec.field_id.name} '
                    f'el {rec.booking_date.strftime("%d/%m/%Y")} en el horario seleccionado.\n'
                    f'Reserva conflictiva: {overlapping[0].name} '
                    f'({self._format_time(overlapping[0].start_time)} - {self._format_time(overlapping[0].end_time)})'
                )

    @api.constrains('participants', 'field_id')
    def _check_participants(self):
        for rec in self:
            if rec.participants < 1:
                raise ValidationError('Debe haber al menos 1 participante.')
            if rec.participants > rec.field_id.capacity:
                raise ValidationError(
                    f'La cancha {rec.field_id.name} tiene una capacidad máxima de '
                    f'{rec.field_id.capacity} jugadores. Has indicado {rec.participants}.'
                )

    def _format_time(self, time_float):
        """Convierte tiempo float a formato HH:MM"""
        hours = int(time_float)
        minutes = int((time_float % 1) * 60)
        return f'{hours:02d}:{minutes:02d}'

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Solo se pueden confirmar reservas en borrador.')
            rec.state = 'confirmed'
            rec.message_post(body='Reserva confirmada')

    def action_start(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError('Solo se pueden iniciar reservas confirmadas.')
            rec.state = 'in_progress'
            rec.message_post(body='Reserva iniciada')

    def action_complete(self):
        for rec in self:
            if rec.state != 'in_progress':
                raise UserError('Solo se pueden completar reservas en progreso.')
            rec.state = 'completed'
            rec.message_post(body='Reserva completada')

    def action_cancel(self):
        for rec in self:
            if rec.state == 'completed':
                raise UserError('No se pueden cancelar reservas completadas.')
            rec.state = 'cancelled'
            rec.message_post(body='Reserva cancelada')

    def action_set_to_draft(self):
        for rec in self:
            if rec.state not in ['cancelled']:
                raise UserError('Solo se pueden reactivar reservas canceladas.')
            rec.state = 'draft'
            rec.message_post(body='Reserva reactivada a borrador')