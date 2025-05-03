import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME', '@YourBotName')

SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.example.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 465))
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', 'your_email@example.com')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'your_password')
ZOO_EMAIL = os.getenv('ZOO_EMAIL', 'info@moscowzoo.ru')

ANIMALS_JSON = 'data/animals.json'
QUESTIONS_JSON = 'data/questions.json'
FEEDBACK_FILE = 'data/feedback.txt'