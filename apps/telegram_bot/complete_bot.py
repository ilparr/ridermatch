#!/usr/bin/env python3
"""
Bot RiderMatch Completo
- Registrazione rider via Telegram
- Gestione disponibilità via bot
- Matching automatico turni
- Notifiche in tempo reale
"""

import os
import django
import json
import re
from datetime import datetime, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ridermatch.settings')
django.setup()

import requests
from django.conf import settings
from django.contrib.auth.models import User
from apps.riders.models import Rider, RiderAvailability
from apps.shifts.models import Shift, ShiftAssignment
from apps.pizzerias.models import Pizzeria

class RiderMatchBot:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        # Stati utente per conversation flow
        self.user_states = {}
    
    def send_message(self, chat_id, text, reply_markup=None):
        """Invia un messaggio"""
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        
        try:
            response = requests.post(url, data=data)
            return response.json()
        except Exception as e:
            print(f"Errore invio messaggio: {e}")
            return None
    
    def get_rider_by_telegram_id(self, telegram_id):
        """Trova rider dal Telegram ID"""
        try:
            return Rider.objects.get(telegram_id=telegram_id)
        except Rider.DoesNotExist:
            return None
    
    def handle_start(self, chat_id, telegram_id, user_name):
        """Gestisce comando /start"""
        rider = self.get_rider_by_telegram_id(telegram_id)
        
        if rider:
            # Rider già registrato
            message = f"""
🍕 <b>Benvenuto {rider.user.first_name}!</b> 🏍️

Sei registrato come <b>{rider.get_transport_type_display()}</b>
📱 {rider.phone}
📍 Distanza max: {rider.max_distance_km}km
⭐ Rating: {rider.rating}/5.00

<b>Cosa vuoi fare?</b>
            """
            
            keyboard = {
                'inline_keyboard': [
                    [{'text': '📅 Gestisci Disponibilità', 'callback_data': 'manage_availability'}],
                    [{'text': '🍕 I Miei Turni', 'callback_data': 'my_shifts'}],
                    [{'text': '🆓 Turni Disponibili', 'callback_data': 'available_shifts'}],
                    [{'text': '👤 Il Mio Profilo', 'callback_data': 'my_profile'}]
                ]
            }
        else:
            # Nuovo utente - registrazione
            message = f"""
🍕 <b>Benvenuto in RiderMatch, {user_name}!</b> 🏍️

Non sei ancora registrato come rider.

<b>RiderMatch</b> è il sistema che collega rider e pizzerie per turni di consegna.

<b>Come rider potrai:</b>
• 📅 Impostare le tue disponibilità
• 🍕 Ricevere turni automaticamente
• 💰 Guadagnare con consegne
• ⭐ Costruire la tua reputazione

<b>Vuoi registrarti?</b>
            """
            
            keyboard = {
                'inline_keyboard': [
                    [{'text': '✅ Registrati come Rider', 'callback_data': 'register_rider'}],
                    [{'text': '❓ Più Informazioni', 'callback_data': 'more_info'}]
                ]
            }
        
        self.send_message(chat_id, message, keyboard)
    
    def handle_register_rider(self, chat_id, telegram_id, user_name):
        """Inizia processo registrazione rider"""
        message = """
📝 <b>REGISTRAZIONE RIDER</b>

Per registrarti ho bisogno di alcune informazioni:

<b>Inviami il tuo numero di telefono</b>
Esempio: +393331234567

Oppure usa il pulsante qui sotto per condividerlo automaticamente.
        """
        
        keyboard = {
            'keyboard': [
                [{'text': '📱 Condividi Numero', 'request_contact': True}]
            ],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        # Salva stato utente
        self.user_states[telegram_id] = {
            'state': 'waiting_phone',
            'user_name': user_name
        }
        
        self.send_message(chat_id, message, keyboard)
    
    def handle_phone_received(self, chat_id, telegram_id, phone):
        """Gestisce numero telefono ricevuto"""
        message = f"""
✅ <b>Numero salvato:</b> {phone}

<b>Che mezzo di trasporto usi?</b>
        """
        
        keyboard = {
            'inline_keyboard': [
                [{'text': '🚲 Bicicletta', 'callback_data': 'transport_bike'}],
                [{'text': '🛵 Scooter', 'callback_data': 'transport_scooter'}],
                [{'text': '🚗 Auto', 'callback_data': 'transport_car'}]
            ]
        }
        
        # Aggiorna stato
        self.user_states[telegram_id]['state'] = 'waiting_transport'
        self.user_states[telegram_id]['phone'] = phone
        
        self.send_message(chat_id, message, keyboard)
    
    def handle_transport_selected(self, chat_id, telegram_id, transport):
        """Gestisce selezione mezzo trasporto"""
        transport_names = {
            'bike': '🚲 Bicicletta',
            'scooter': '🛵 Scooter', 
            'car': '🚗 Auto'
        }
        
        message = f"""
✅ <b>Mezzo di trasporto:</b> {transport_names[transport]}

<b>Qual è la distanza massima che vuoi percorrere?</b>
(in chilometri)
        """
        
        keyboard = {
            'inline_keyboard': [
                [{'text': '5 km', 'callback_data': 'distance_5'}],
                [{'text': '10 km', 'callback_data': 'distance_10'}],
                [{'text': '15 km', 'callback_data': 'distance_15'}],
                [{'text': '20 km', 'callback_data': 'distance_20'}],
                [{'text': '25+ km', 'callback_data': 'distance_25'}]
            ]
        }
        
        # Aggiorna stato
        self.user_states[telegram_id]['state'] = 'waiting_distance'
        self.user_states[telegram_id]['transport'] = transport
        
        self.send_message(chat_id, message, keyboard)
    
    def handle_distance_selected(self, chat_id, telegram_id, distance):
        """Completa registrazione rider"""
        user_data = self.user_states[telegram_id]
        
        try:
            # Crea utente Django
            django_user, created = User.objects.get_or_create(
                username=f"telegram_{telegram_id}",
                defaults={
                    'first_name': user_data['user_name'][:30],
                    'last_name': '',
                }
            )
            
            # Crea Rider
            rider = Rider.objects.create(
                user=django_user,
                telegram_id=telegram_id,
                phone=user_data['phone'],
                transport_type=user_data['transport'],
                max_distance_km=distance
            )
            
            transport_names = {
                'bike': '🚲 Bicicletta',
                'scooter': '🛵 Scooter', 
                'car': '🚗 Auto'
            }
            
            message = f"""
🎉 <b>REGISTRAZIONE COMPLETATA!</b>

<b>I tuoi dati:</b>
👤 {django_user.first_name}
📱 {user_data['phone']}
🚗 {transport_names[user_data['transport']]}
📍 Distanza max: {distance}km
⭐ Rating iniziale: 5.00/5

<b>Prossimo passo:</b> Imposta le tue disponibilità per ricevere turni automaticamente!
            """
            
            keyboard = {
                'inline_keyboard': [
                    [{'text': '📅 Imposta Disponibilità', 'callback_data': 'manage_availability'}],
                    [{'text': '🏠 Menu Principale', 'callback_data': 'main_menu'}]
                ]
            }
            
            # Pulisci stato
            if telegram_id in self.user_states:
                del self.user_states[telegram_id]
            
            self.send_message(chat_id, message, keyboard)
            
        except Exception as e:
            print(f"Errore registrazione: {e}")
            self.send_message(chat_id, "❌ Errore durante la registrazione. Riprova più tardi.")
    
    def handle_manage_availability(self, chat_id, telegram_id):
        """Gestisce disponibilità rider"""
        rider = self.get_rider_by_telegram_id(telegram_id)
        if not rider:
            self.send_message(chat_id, "❌ Devi prima registrarti come rider!")
            return
        
        # Mostra disponibilità attuali
        availabilities = RiderAvailability.objects.filter(rider=rider)
        
        message = "<b>📅 LA TUA DISPONIBILITÀ</b>\n\n"
        
        days = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
        
        for i, day in enumerate(days):
            day_avail = availabilities.filter(day_of_week=i)
            message += f"<b>{day}:</b> "
            
            if day_avail.exists():
                for avail in day_avail:
                    pref = "⭐" if avail.is_preferred else ""
                    message += f"{avail.start_time.strftime('%H:%M')}-{avail.end_time.strftime('%H:%M')}{pref} "
            else:
                message += "Non disponibile"
            message += "\n"
        
        message += "\n⭐ = Orario preferito (priorità alta)"
        
        keyboard = {
            'inline_keyboard': [
                [{'text': '➕ Aggiungi Disponibilità', 'callback_data': 'add_availability'}],
                [{'text': '🗑️ Cancella Disponibilità', 'callback_data': 'remove_availability'}],
                [{'text': '🏠 Menu Principale', 'callback_data': 'main_menu'}]
            ]
        }
        
        self.send_message(chat_id, message, keyboard)
    
    def handle_add_availability(self, chat_id, telegram_id):
        """Aggiunge disponibilità"""
        message = """
📅 <b>AGGIUNGI DISPONIBILITÀ</b>

<b>Seleziona il giorno:</b>
        """
        
        keyboard = {
            'inline_keyboard': [
                [{'text': 'Lunedì', 'callback_data': 'day_0'}],
                [{'text': 'Martedì', 'callback_data': 'day_1'}],
                [{'text': 'Mercoledì', 'callback_data': 'day_2'}],
                [{'text': 'Giovedì', 'callback_data': 'day_3'}],
                [{'text': 'Venerdì', 'callback_data': 'day_4'}],
                [{'text': 'Sabato', 'callback_data': 'day_5'}],
                [{'text': 'Domenica', 'callback_data': 'day_6'}],
                [{'text': '🔙 Indietro', 'callback_data': 'manage_availability'}]
            ]
        }
        
        self.user_states[telegram_id] = {'state': 'selecting_day'}
        self.send_message(chat_id, message, keyboard)
    
    def handle_day_selected(self, chat_id, telegram_id, day_num):
        """Giorno selezionato per disponibilità"""
        days = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
        
        message = f"""
📅 <b>DISPONIBILITÀ {days[day_num].upper()}</b>

<b>Invia l'orario nel formato:</b>
<code>HH:MM-HH:MM</code>

<b>Esempi:</b>
• <code>19:00-23:00</code> (sera)
• <code>12:00-14:30</code> (pranzo)
• <code>18:30-22:00</code> (sera)

<b>Per orario preferito aggiungi *:</b>
• <code>19:00-23:00*</code> (priorità alta)
        """
        
        self.user_states[telegram_id] = {
            'state': 'waiting_time',
            'day': day_num
        }
        
        self.send_message(chat_id, message)
    
    def handle_time_received(self, chat_id, telegram_id, time_text):
        """Gestisce orario ricevuto"""
        rider = self.get_rider_by_telegram_id(telegram_id)
        user_data = self.user_states[telegram_id]
        day_num = user_data['day']
        
        try:
            # Parse orario
            is_preferred = time_text.endswith('*')
            if is_preferred:
                time_text = time_text[:-1]
            
            # Regex per HH:MM-HH:MM
            match = re.match(r'(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})', time_text.strip())
            if not match:
                raise ValueError("Formato non valido")
            
            start_hour, start_min, end_hour, end_min = map(int, match.groups())
            start_time = time(start_hour, start_min)
            end_time = time(end_hour, end_min)
            
            # Crea disponibilità
            availability = RiderAvailability.objects.create(
                rider=rider,
                day_of_week=day_num,
                start_time=start_time,
                end_time=end_time,
                is_preferred=is_preferred
            )
            
            days = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
            pref_text = " (⭐ Preferito)" if is_preferred else ""
            
            message = f"""
✅ <b>Disponibilità aggiunta!</b>

<b>{days[day_num]}:</b> {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}{pref_text}

Ora puoi ricevere turni automaticamente in questo orario!
            """
            
            keyboard = {
                'inline_keyboard': [
                    [{'text': '➕ Aggiungi Altro Orario', 'callback_data': 'add_availability'}],
                    [{'text': '📅 Vedi Disponibilità', 'callback_data': 'manage_availability'}],
                    [{'text': '🏠 Menu Principale', 'callback_data': 'main_menu'}]
                ]
            }
            
            # Pulisci stato
            if telegram_id in self.user_states:
                del self.user_states[telegram_id]
            
            self.send_message(chat_id, message, keyboard)
            
            # Triggera matching automatico
            self.check_automatic_matching(rider)
            
        except Exception as e:
            print(f"Errore parsing orario: {e}")
            self.send_message(chat_id, 
                "❌ Formato orario non valido!\n\n"
                "Usa il formato: <code>HH:MM-HH:MM</code>\n"
                "Esempio: <code>19:00-23:00</code>")
    
    def handle_my_shifts(self, chat_id, telegram_id):
        """Mostra turni del rider"""
        rider = self.get_rider_by_telegram_id(telegram_id)
        if not rider:
            return
        
        assignments = ShiftAssignment.objects.filter(
            rider=rider,
            shift__status__in=['assigned', 'confirmed']
        ).order_by('shift__date', 'shift__start_time')
        
        if not assignments.exists():
            message = """
📋 <b>I MIEI TURNI</b>

Non hai turni assegnati al momento.

<b>Suggerimenti:</b>
• Controlla che la tua disponibilità sia aggiornata
• I turni vengono assegnati automaticamente
• Controlla i turni disponibili
            """
            
            keyboard = {
                'inline_keyboard': [
                    [{'text': '📅 Aggiorna Disponibilità', 'callback_data': 'manage_availability'}],
                    [{'text': '🆓 Turni Disponibili', 'callback_data': 'available_shifts'}]
                ]
            }
        else:
            message = "<b>📋 I MIEI TURNI</b>\n\n"
            
            for assignment in assignments:
                shift = assignment.shift
                status_emoji = "✅" if assignment.confirmed_by_rider else "⏳"
                
                message += f"{status_emoji} <b>{shift.pizzeria.name}</b>\n"
                message += f"   📅 {shift.date.strftime('%d/%m/%Y')}\n"
                message += f"   ⏰ {shift.start_time.strftime('%H:%M')} - {shift.end_time.strftime('%H:%M')}\n"
                message += f"   💰 €{shift.hourly_rate}/ora\n"
                message += f"   📍 {shift.pizzeria.address}\n"
                
                if not assignment.confirmed_by_rider:
                    message += "   ⚠️ <b>DA CONFERMARE</b>\n"
                
                message += "\n"
            
            keyboard = {
                'inline_keyboard': [
                    [{'text': '✅ Conferma Turni', 'callback_data': 'confirm_shifts'}],
                    [{'text': '🔄 Aggiorna', 'callback_data': 'my_shifts'}]
                ]
            }
        
        keyboard['inline_keyboard'].append([{'text': '🏠 Menu Principale', 'callback_data': 'main_menu'}])
        self.send_message(chat_id, message, keyboard)
    
    def check_automatic_matching(self, rider=None):
        """Esegue matching automatico"""
        from apps.shifts.matching import ShiftMatcher
        
        try:
            matcher = ShiftMatcher()
            assignments = matcher.batch_assign_shifts()
            
            if assignments > 0:
                print(f"🎯 Matching automatico: {assignments} turni assegnati")
                # Notifica i rider che hanno ricevuto nuovi turni
                self.notify_new_assignments()
            
        except Exception as e:
            print(f"Errore matching automatico: {e}")
    
    def notify_new_assignments(self):
        """Notifica rider di nuove assegnazioni"""
        try:
            # Trova assegnazioni recenti non ancora confermate
            from datetime import timedelta
            from django.utils import timezone
            
            recent_assignments = ShiftAssignment.objects.filter(
                assigned_at__gte=timezone.now() - timedelta(minutes=5),
                confirmed_by_rider=False
            )
            
            for assignment in recent_assignments:
                rider = assignment.rider
                shift = assignment.shift
                
                message = f"""
🎉 <b>NUOVO TURNO ASSEGNATO!</b>

<b>🍕 {shift.pizzeria.name}</b>
📅 {shift.date.strftime('%d/%m/%Y')}
⏰ {shift.start_time.strftime('%H:%M')} - {shift.end_time.strftime('%H:%M')}
💰 €{shift.hourly_rate}/ora
📍 {shift.pizzeria.address}

⚠️ <b>Conferma entro 30 minuti</b> o il turno verrà riassegnato!
                """
                
                keyboard = {
                    'inline_keyboard': [
                        [{'text': '✅ Accetto il Turno', 'callback_data': f'accept_shift_{assignment.id}'}],
                        [{'text': '❌ Rifiuta Turno', 'callback_data': f'reject_shift_{assignment.id}'}],
                        [{'text': '📋 I Miei Turni', 'callback_data': 'my_shifts'}]
                    ]
                }
                
                self.send_message(rider.telegram_id, message, keyboard)
                
        except Exception as e:
            print(f"Errore notifica assegnazioni: {e}")
    
    def handle_callback(self, chat_id, telegram_id, message_id, callback_data, user_name):
        """Gestisce callback dei bottoni"""
        
        if callback_data == 'main_menu':
            self.handle_start(chat_id, telegram_id, user_name)
        
        elif callback_data == 'register_rider':
            self.handle_register_rider(chat_id, telegram_id, user_name)
        
        elif callback_data.startswith('transport_'):
            transport = callback_data.replace('transport_', '')
            self.handle_transport_selected(chat_id, telegram_id, transport)
        
        elif callback_data.startswith('distance_'):
            distance = int(callback_data.replace('distance_', ''))
            self.handle_distance_selected(chat_id, telegram_id, distance)
        
        elif callback_data == 'manage_availability':
            self.handle_manage_availability(chat_id, telegram_id)
        
        elif callback_data == 'add_availability':
            self.handle_add_availability(chat_id, telegram_id)
        
        elif callback_data.startswith('day_'):
            day_num = int(callback_data.replace('day_', ''))
            self.handle_day_selected(chat_id, telegram_id, day_num)
        
        elif callback_data == 'my_shifts':
            self.handle_my_shifts(chat_id, telegram_id)
        
        elif callback_data == 'available_shifts':
            self.handle_available_shifts(chat_id, telegram_id)
        
        elif callback_data.startswith('accept_shift_'):
            assignment_id = int(callback_data.replace('accept_shift_', ''))
            self.handle_accept_shift(chat_id, telegram_id, assignment_id)
        
        elif callback_data.startswith('reject_shift_'):
            assignment_id = int(callback_data.replace('reject_shift_', ''))
            self.handle_reject_shift(chat_id, telegram_id, assignment_id)
    
    def handle_available_shifts(self, chat_id, telegram_id):
        """Mostra turni disponibili"""
        shifts = Shift.objects.filter(status='open')[:5]
        
        if not shifts.exists():
            message = """
🔍 <b>TURNI DISPONIBILI</b>

Nessun turno disponibile al momento.

I turni vengono assegnati automaticamente in base alla tua disponibilità.
            """
        else:
            message = "<b>🆓 TURNI DISPONIBILI</b>\n\n"
            
            for i, shift in enumerate(shifts, 1):
                message += f"<b>{i}. 🍕 {shift.pizzeria.name}</b>\n"
                message += f"   📅 {shift.date.strftime('%d/%m/%Y')}\n"
                message += f"   ⏰ {shift.start_time.strftime('%H:%M')} - {shift.end_time.strftime('%H:%M')}\n"
                message += f"   💰 €{shift.hourly_rate}/ora\n"
                message += f"   📍 {shift.pizzeria.address}\n\n"
            
            message += "ℹ️ I turni vengono assegnati automaticamente in base alla disponibilità e posizione."
        
        keyboard = {
            'inline_keyboard': [
                [{'text': '🔄 Aggiorna Lista', 'callback_data': 'available_shifts'}],
                [{'text': '📅 La Mia Disponibilità', 'callback_data': 'manage_availability'}],
                [{'text': '🏠 Menu Principale', 'callback_data': 'main_menu'}]
            ]
        }
        
        self.send_message(chat_id, message, keyboard)
    
    def handle_accept_shift(self, chat_id, telegram_id, assignment_id):
        """Accetta un turno assegnato"""
        try:
            assignment = ShiftAssignment.objects.get(
                id=assignment_id,
                rider__telegram_id=telegram_id
            )
            
            assignment.confirmed_by_rider = True
            assignment.save()
            
            shift = assignment.shift
            
            message = f"""
✅ <b>TURNO CONFERMATO!</b>

<b>🍕 {shift.pizzeria.name}</b>
📅 {shift.date.strftime('%d/%m/%Y')}
⏰ {shift.start_time.strftime('%H:%M')} - {shift.end_time.strftime('%H:%M')}
💰 €{shift.hourly_rate}/ora
📍 {shift.pizzeria.address}
📞 {shift.pizzeria.phone}

<b>Il turno è confermato!</b>
La pizzeria è stata notificata.
            """
            
            keyboard = {
                'inline_keyboard': [
                    [{'text': '📋 I Miei Turni', 'callback_data': 'my_shifts'}],
                    [{'text': '🏠 Menu Principale', 'callback_data': 'main_menu'}]
                ]
            }
            
            self.send_message(chat_id, message, keyboard)
            
        except Exception as e:
            print(f"Errore accettazione turno: {e}")
            self.send_message(chat_id, "❌ Errore nell'accettazione del turno.")
    
    def handle_reject_shift(self, chat_id, telegram_id, assignment_id):
        """Rifiuta un turno assegnato"""
        try:
            assignment = ShiftAssignment.objects.get(
                id=assignment_id,
                rider__telegram_id=telegram_id
            )
            
            shift = assignment.shift
            shift.status = 'open'  # Torna disponibile
            shift.save()
            
            assignment.delete()  # Rimuovi assegnazione
            
            message = """
❌ <b>TURNO RIFIUTATO</b>

Il turno è stato rimosso e tornerà disponibile per altri rider.

⚠️ <b>Attenzione:</b> Rifiutare troppi turni può influire sul tuo rating.
            """
            
            keyboard = {
                'inline_keyboard': [
                    [{'text': '🆓 Altri Turni Disponibili', 'callback_data': 'available_shifts'}],
                    [{'text': '🏠 Menu Principale', 'callback_data': 'main_menu'}]
                ]
            }
            
            self.send_message(chat_id, message, keyboard)
            
            # Triggera nuovo matching
            self.check_automatic_matching()
            
        except Exception as e:
            print(f"Errore rifiuto turno: {e}")
            self.send_message(chat_id, "❌ Errore nel rifiuto del turno.")
    
    def process_update(self, update_data):
        """Processa un aggiornamento da Telegram"""
        try:
            if 'message' in update_data:
                message = update_data['message']
                chat_id = message['chat']['id']
                telegram_id = message['from']['id']
                user_name = message['from'].get('first_name', 'Utente')
                text = message.get('text', '')
                
                # Gestisci contatto condiviso
                if 'contact' in message:
                    phone = message['contact']['phone_number']
                    self.handle_phone_received(chat_id, telegram_id, phone)
                    return
                
                # Gestisci stati conversazione
                if telegram_id in self.user_states:
                    state = self.user_states[telegram_id]['state']
                    
                    if state == 'waiting_time':
                        self.handle_time_received(chat_id, telegram_id, text)
                        return
                
                # Comandi standard
                if text.startswith('/start'):
                    self.handle_start(chat_id, telegram_id, user_name)
                elif text.startswith('/menu'):
                    self.handle_start(chat_id, telegram_id, user_name)
                elif text.startswith('/disponibilita'):
                    self.handle_manage_availability(chat_id, telegram_id)
                elif text.startswith('/turni'):
                    self.handle_my_shifts(chat_id, telegram_id)
                elif text.startswith('/help'):
                    self.handle_start(chat_id, telegram_id, user_name)
                # Gestisci numero telefono manuale
                elif telegram_id in self.user_states and self.user_states[telegram_id]['state'] == 'waiting_phone':
                    self.handle_phone_received(chat_id, telegram_id, text)
                else:
                    self.send_message(chat_id, 
                        "🤖 Comando non riconosciuto.\n\n"
                        "Usa /start per il menu principale.")
            
            elif 'callback_query' in update_data:
                callback = update_data['callback_query']
                chat_id = callback['message']['chat']['id']
                telegram_id = callback['from']['id']
                user_name = callback['from'].get('first_name', 'Utente')
                message_id = callback['message']['message_id']
                callback_data = callback['data']
                
                self.handle_callback(chat_id, telegram_id, message_id, callback_data, user_name)
                
                # Conferma callback
                callback_id = callback['id']
                requests.post(f"{self.base_url}/answerCallbackQuery", 
                            data={'callback_query_id': callback_id})
        
        except Exception as e:
            print(f"Errore processamento update: {e}")
    
    def get_updates(self, offset=None):
        """Recupera aggiornamenti"""
        url = f"{self.base_url}/getUpdates"
        params = {'timeout': 30}
        if offset:
            params['offset'] = offset
        
        try:
            response = requests.get(url, params=params)
            return response.json()
        except Exception as e:
            print(f"Errore get updates: {e}")
            return None
    
    def run_polling(self):
        """Avvia il bot"""
        print("🤖 RiderMatch Bot COMPLETO avviato!")
        print(f"🔗 Token: {self.token[:10]}...")
        print("📱 Funzionalità attive:")
        print("   • Registrazione rider automatica")
        print("   • Gestione disponibilità via bot")
        print("   • Matching automatico turni")
        print("   • Notifiche in tempo reale")
        print("⚠️  Per fermare: Ctrl+C")
        
        offset = None
        
        try:
            while True:
                updates = self.get_updates(offset)
                
                if updates and updates.get('ok'):
                    for update in updates['result']:
                        self.process_update(update)
                        offset = update['update_id'] + 1
                
        except KeyboardInterrupt:
            print("\n🛑 Bot fermato!")
        except Exception as e:
            print(f"❌ Errore bot: {e}")

if __name__ == "__main__":
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == 'your_telegram_bot_token_here':
        print("❌ ERRORE: Token Telegram non configurato!")
        print("🔧 Configura TELEGRAM_BOT_TOKEN nel file .env")
        exit(1)
    
    bot = RiderMatchBot()
    bot.run_polling()