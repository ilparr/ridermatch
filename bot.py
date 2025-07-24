import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ridermatch.settings')
django.setup()

def main():
    from apps.telegram_bot.complete_bot import RiderMatchBot
    
    try:
        bot = RiderMatchBot()
        bot.run_polling()
    except KeyboardInterrupt:
        print("\n🛑 Bot fermato dall'utente")
    except Exception as e:
        print(f"❌ Errore critico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()