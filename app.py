from flask import Flask, request, jsonify, render_template, send_from_directory, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import os
import requests
import uuid
import json
import random
from datetime import date
from dotenv import load_dotenv
import webbrowser
import threading
import time

# Load environment variables
load_dotenv()

# ========== MULTI-LANGUAGE SUPPORT ==========
class TranslationManager:
    def __init__(self, app):
        self.translations = {}
        self.app = app
        self.load_translations()
    
    def load_translations(self):
        """Load all translation files"""
        translation_dir = os.path.join(os.path.dirname(__file__), 'translations')
        if not os.path.exists(translation_dir):
            os.makedirs(translation_dir)
            print(f"📁 Created translations directory at: {translation_dir}")
        
        # Create default English file if it doesn't exist
        default_translation = {
            "app_name": "Smart Crop Advisory",
            "welcome": "Welcome to Smart Crop Advisory",
            "dashboard": "Dashboard",
            "weather": "Weather",
            "chatbot": "Ask the Assistant",
            "voice_input": "Speak your question",
            "submit": "Submit",
            "logout": "Logout",
            "login": "Login",
            "signup": "Sign Up",
            "profile": "Profile",
            "settings": "Settings",
            "language": "Language",
            "fertilizer": "Fertilizer Advice",
            "market_prices": "Market Prices",
            "crop_advice": "Crop Advice",
            "weather_forecast": "Weather Forecast",
            "farm_tasks": "Farm Tasks",
            "chat_history": "Chat History",
            "type_message": "Type your message...",
            "speak_now": "Speak now...",
            "listening": "Listening...",
            "send": "Send",
            "clear": "Clear",
            "save": "Save",
            "cancel": "Cancel",
            "edit": "Edit",
            "delete": "Delete",
            "view": "View",
            "home": "Home",
            "about": "About",
            "contact": "Contact",
            "help": "Help",
            "privacy": "Privacy",
            "terms": "Terms",
            "crop_selection": "Select Crop",
            "soil_type": "Soil Type",
            "irrigation": "Irrigation",
            "farm_size": "Farm Size",
            "location": "Location",
            "state": "State",
            "district": "District",
            "get_advice": "Get Advice",
            "loading": "Loading...",
            "error": "Error",
            "success": "Success",
            "warning": "Warning",
            "info": "Information",
            "price_trend": "Price Trend",
            "best_time": "Best Time to Sell",
            "nearby_markets": "Nearby Markets",
            "storage_advice": "Storage Advice",
            "government_schemes": "Government Schemes",
            "prediction": "Prediction",
            "personalized_advice": "Personalized Advice",
            "fertilizer_ratio": "Fertilizer Ratio",
            "quantity_per_acre": "Quantity per Acre",
            "total_required": "Total Required",
            "recommended_brands": "Recommended Brands",
            "application_schedule": "Application Schedule",
            "organic_alternatives": "Organic Alternatives",
            "estimated_cost": "Estimated Cost",
            "subsidies": "Subsidies",
            "soil_tips": "Soil Health Tips",
            "irrigation_tips": "Irrigation Tips",
            "voice_assistant": "Voice Assistant",
            "enable_voice": "Enable Voice",
            "disable_voice": "Disable Voice",
            "speak_response": "Speak Response",
            "stop_speaking": "Stop Speaking",
            "language_settings": "Language Settings",
            "select_language": "Select Language",
            "voice_settings": "Voice Settings",
            "toggle_voice": "Toggle Voice Input/Output",
            "change_language": "Change Language",
            "english": "English",
            "hindi": "Hindi",
            "telugu": "Telugu",
            "tamil": "Tamil",
            "marathi": "Marathi",
            "bengali": "Bengali",
            "current_language": "Current Language",
            "browser_language": "Browser Language",
            "auto_detect": "Auto Detect",
            "apply_language": "Apply Language",
            "language_changed": "Language Changed Successfully",
            "guest_user": "Guest User"
        }
        
        en_file = os.path.join(translation_dir, 'en.json')
        if not os.path.exists(en_file):
            with open(en_file, 'w', encoding='utf-8') as f:
                json.dump(default_translation, f, indent=2, ensure_ascii=False)
            print("✓ Created default English translation file")
        
        # Load all translation files
        for filename in os.listdir(translation_dir):
            if filename.endswith('.json'):
                lang_code = filename.replace('.json', '')
                try:
                    with open(os.path.join(translation_dir, filename), 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)
                    print(f"✓ Loaded translations for: {lang_code}")
                except Exception as e:
                    print(f"✗ Error loading {filename}: {e}")
    
    def get_text(self, key, lang='en'):
        """Get translated text for a key"""
        if lang not in self.translations:
            lang = 'en'
        return self.translations.get(lang, {}).get(key, key)
    
    def get_available_languages(self):
        """Get list of available language codes"""
        return list(self.translations.keys())

# Initialize translation manager (will be set later)
translation_manager = None

# ========== LANGUAGE DETECTION HELPERS ==========
def detect_browser_language(request):
    """
    Smart browser language detection prioritizing Indian languages.
    Industry-standard detection chain.
    """
    if not hasattr(request, 'accept_languages') or not request.accept_languages:
        return 'en'
    
    browser_langs = request.accept_languages
    
    # Priority order for Indian languages
    indian_languages = ['hi', 'te', 'ta', 'bn', 'mr', 'gu', 'kn', 'ml', 'pa', 'ur']
    all_supported = ['en'] + indian_languages
    
    # Check for exact matches first
    for lang in all_supported:
        if browser_langs.best_match([lang]):
            return lang
    
    # Check for regional variants (hi-IN, te-IN, etc.)
    for lang in indian_languages:
        regional_code = f"{lang}-IN"
        if browser_langs.best_match([regional_code]):
            return lang
    
    # Check for country codes (IN for India)
    if browser_langs.best_match(['en-IN', 'en-US', 'en-GB']):
        return 'en'
    
    # Default to English
    return 'en'

def get_user_language_from_request(request):
    """
    Industry-standard language detection chain.
    Priority: Query param → Session → Cookie → Logged-in user → Browser → Default
    """
    # 1. Query parameter (manual override) - ?lang=hi
    lang_param = request.args.get('lang')
    if lang_param:
        # Clean and validate
        lang_param = lang_param.lower().strip()
        if lang_param in ['en', 'hi', 'te', 'ta', 'bn', 'mr']:
            return lang_param
    
    # 2. Session (current visit preference)
    if 'user_language' in session:
        session_lang = session['user_language']
        if session_lang in ['en', 'hi', 'te', 'ta', 'bn', 'mr']:
            return session_lang
    
    # 3. Cookie (previous visits preference)
    cookie_lang = request.cookies.get('preferred_language')
    if cookie_lang and cookie_lang in ['en', 'hi', 'te', 'ta', 'bn', 'mr']:
        return cookie_lang
    
    # 4. Logged-in user preference
    if current_user.is_authenticated and current_user.preferred_language:
        return current_user.preferred_language
    
    # 5. Browser language detection
    browser_lang = detect_browser_language(request)
    if browser_lang in ['en', 'hi', 'te', 'ta', 'bn', 'mr']:
        return browser_lang
    
    # 6. Default
    return 'en'

# ========== FLASK APP INITIALIZATION ==========
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Session configuration for Flask-Login
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = "strong"

# Configure CORS properly
CORS(app, 
     resources={r"/*": {
         "origins": ["http://localhost:5500", "http://127.0.0.1:5500", 
                    "http://localhost:3000", "http://127.0.0.1:3000",
                    "http://localhost:8080", "http://127.0.0.1:8080",
                    "http://localhost:5000", "http://127.0.0.1:5000"],
         "supports_credentials": True,
         "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept"],
         "expose_headers": ["Set-Cookie", "Content-Type", "Authorization"],
         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
     }},
     supports_credentials=True)

# ========== API CONFIGURATION ==========
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
if not GROQ_API_KEY:
    print("⚠️  WARNING: GROQ_API_KEY environment variable not set!")
    print("⚠️  Chat functionality will not work without API key")
    print("⚠️  Set it in .env file: GROQ_API_KEY='your-key-here'")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ========== WEBSITE ROUTES ==========
@app.route('/')
def index():
    """Serve the main index page"""
    return render_template('index.html')

@app.route('/weather')
def weather_page():
    """Serve the weather page"""
    return render_template('weather.html')

@app.route('/<page_name>')
def serve_page(page_name):
    """Serve other HTML pages"""
    # List of valid HTML pages
    valid_pages = [
        'dashboard', 'weather', 'chatbot', 
        'features', 'login', 'signup', 
        'about', 'contact', 'fertilizer'
    ]
    
    if page_name in valid_pages:
        try:
            return render_template(f'{page_name}.html')
        except:
            return "Page not found", 404
    else:
        # Try with .html extension
        if page_name.endswith('.html') and page_name.replace('.html', '') in valid_pages:
            try:
                return render_template(page_name)
            except:
                return "Page not found", 404
    
    return "Page not found", 404

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory(app.static_folder, filename)

# ========== LOAD DISTRICTS DATA ==========
def load_districts_data():
    """Load districts data from JSON file"""
    try:
        with open('districts.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert to state->districts mapping
        state_districts = {}
        for item in data:
            state = item['state']
            district = item['district']
            if state not in state_districts:
                state_districts[state] = []
            state_districts[state].append(district)
        
        return state_districts
    except FileNotFoundError:
        print("⚠️  districts.json not found. Using fallback data.")
        return {
            "Telangana": ["Jogulamba Gadwal", "Hyderabad", "Warangal", "Karimnagar"],
            "Andhra Pradesh": ["Visakhapatnam", "Vijayawada", "Guntur"],
            "Karnataka": ["Bengaluru", "Mysuru", "Hubli"],
            "Maharashtra": ["Mumbai", "Pune", "Nagpur"],
            "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai"]
        }
    except Exception as e:
        print(f"Error loading districts data: {e}")
        return {}

stateDistricts = load_districts_data()

# ========== USER MODEL ==========
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    preferred_language = db.Column(db.String(10), default='en')
    voice_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Location fields
    state = db.Column(db.String(100), nullable=True)
    district = db.Column(db.String(100), nullable=True)
    
    # Farm size as Float
    farm_size = db.Column(db.Float, nullable=True)  # in acres
    
    # Agriculture fields
    primary_crop = db.Column(db.String(100), nullable=True)
    soil_type = db.Column(db.String(50), nullable=True)
    irrigation_type = db.Column(db.String(50), nullable=True)
    profile_completed = db.Column(db.Boolean, default=False)
    
    # Weather fields
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    last_weather_fetch = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'preferred_language': self.preferred_language,
            'voice_enabled': self.voice_enabled,
            'state': self.state,
            'district': self.district,
            'farm_size': self.farm_size,
            'primary_crop': self.primary_crop,
            'soil_type': self.soil_type,
            'irrigation_type': self.irrigation_type,
            'profile_completed': self.profile_completed,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'last_weather_fetch': self.last_weather_fetch.isoformat() if self.last_weather_fetch else None,
            'is_active': self.is_active
        }

# ========== CHAT MODELS ==========
class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    title = db.Column(db.String(200), default="New Chat")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    __table_args__ = (db.UniqueConstraint('session_id', 'user_id', name='unique_user_session'),)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(10), default='en')
    was_spoken = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ========== FLASK-LOGIN USER LOADER ==========
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ========== HELPER FUNCTIONS ==========
def get_coordinates_from_json(state, district):
    """Get coordinates from districts.json file"""
    try:
        with open('districts.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data:
            if item['state'] == state and item['district'] == district:
                return item.get('lat'), item.get('lon')
        
        # Fallback if not found
        fallback_coords = {
            'telangana': (16.2300, 77.8000),  # Jogulamba Gadwal as default
            'andhra pradesh': (17.3850, 78.4867),
            'karnataka': (12.9716, 77.5946),
            'maharashtra': (19.0760, 72.8777),
            'tamil nadu': (13.0827, 80.2707)
        }
        
        state_lower = state.lower()
        for key, coords in fallback_coords.items():
            if key in state_lower:
                return coords
        
        return 16.2300, 77.8000  # Default to Jogulamba Gadwal
        
    except Exception as e:
        print(f"Error getting coordinates: {e}")
        return 16.2300, 77.8000

def get_or_create_chat_session(session_id, user_id=None):
    """Get or create a chat session"""
    try:
        if user_id is None:
            return {'session_id': session_id, 'user_id': None, 'title': "Guest Chat"}
        
        chat_session = ChatSession.query.filter_by(
            session_id=session_id, 
            user_id=user_id
        ).first()
        
        if not chat_session:
            chat_session = ChatSession(
                session_id=session_id,
                user_id=user_id,
                title="New Chat"
            )
            db.session.add(chat_session)
            db.session.commit()
        
        return chat_session
    except Exception as e:
        db.session.rollback()
        return None

def save_chat_message(session_id, user_id, role, content, language='en', was_spoken=False):
    """Save a chat message to database"""
    try:
        chat_message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            language=language,
            was_spoken=was_spoken,
            timestamp=datetime.utcnow()
        )
        db.session.add(chat_message)
        
        # Update or create chat session
        if user_id is not None:
            chat_session = ChatSession.query.filter_by(
                session_id=session_id, 
                user_id=user_id
            ).first()
            
            if not chat_session:
                chat_session = ChatSession(
                    session_id=session_id,
                    user_id=user_id,
                    title=content[:40] + '...' if len(content) > 40 else content
                )
                db.session.add(chat_session)
            else:
                chat_session.updated_at = datetime.utcnow()
                if role == 'user' and chat_session.title == "New Chat":
                    title = content[:40] + '...' if len(content) > 40 else content
                    chat_session.title = title
        
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        return False

def get_chat_history(session_id, user_id=None):
    """Get chat history for a session"""
    try:
        if user_id is None:
            messages = ChatMessage.query.filter_by(
                session_id=session_id, 
                user_id=None
            ).order_by(ChatMessage.timestamp.asc()).all()
        else:
            messages = ChatMessage.query.filter_by(
                session_id=session_id, 
                user_id=user_id
            ).order_by(ChatMessage.timestamp.asc()).all()
        
        return [{
            'role': msg.role,
            'content': msg.content,
            'language': msg.language,
            'was_spoken': msg.was_spoken,
            'timestamp': msg.timestamp.isoformat()
        } for msg in messages]
    except Exception as e:
        return []

def get_user_chat_sessions(user_id):
    """Get all chat sessions for a user"""
    try:
        if not user_id:
            return []
            
        sessions = ChatSession.query.filter_by(user_id=user_id)\
                                   .order_by(ChatSession.updated_at.desc())\
                                   .limit(20)\
                                   .all()
        
        return [{
            'session_id': s.session_id,
            'title': s.title,
            'created_at': s.created_at.isoformat(),
            'updated_at': s.updated_at.isoformat()
        } for s in sessions]
    except Exception as e:
        return []

# ========== LLM HELPER FUNCTIONS ==========
def create_market_prompt(user_data):
    """Create personalized market price prompt"""
    return f"""You are an agricultural market expert for India. Provide personalized market advice in JSON format.

FARMER PROFILE:
- Location: {user_data.get('state', 'Unknown')}, {user_data.get('district', 'Unknown')}
- Primary Crop: {user_data.get('primary_crop', 'Not specified')}
- Farm Size: {user_data.get('farm_size', 'Not specified')} acres
- Soil Type: {user_data.get('soil_type', 'Not specified')}
- Irrigation Type: {user_data.get('irrigation_type', 'Not specified')}
- Preferred Language: {user_data.get('preferred_language', 'en')}
- Current Date: {date.today().strftime('%B %d, %Y')}
- Current Season: {'Kharif' if date.today().month in [6,7,8,9,10] else 'Rabi'}

Provide this exact JSON structure:
{{
    "price": "₹ X,XXX per quintal",
    "trend": "up|down|stable",
    "trend_percentage": "X.X%",
    "trend_explanation": "Brief explanation",
    "best_time_to_sell": "Within X days",
    "nearby_mandis": [
        {{"name": "Market Name", "price": "₹ X,XXX", "distance": "XX km"}}
    ],
    "storage_advice": "If prices are low...",
    "government_schemes": "Available subsidies...",
    "prediction_next_week": "Price expected to...",
    "personalized_advice": "Based on your profile..."
}}

Make the data realistic for the location and crop. If crop is not specified, use 'Rice' as default."""

def create_fertilizer_prompt(user_data):
    """Create personalized fertilizer recommendation prompt"""
    return f"""You are an agricultural scientist specializing in Indian farming. Provide personalized fertilizer advice in JSON format.

FARMER PROFILE:
- Location: {user_data.get('state', 'Unknown')}, {user_data.get('district', 'Unknown')}
- Primary Crop: {user_data.get('primary_crop', 'Not specified')}
- Farm Size: {user_data.get('farm_size', 'Not specified')} acres
- Soil Type: {user_data.get('soil_type', 'Not specified')}
- Irrigation Type: {user_data.get('irrigation_type', 'Not specified')}
- Preferred Language: {user_data.get('preferred_language', 'en')}
- Current Date: {date.today().strftime('%B %d, %Y')}
- Current Season: {'Kharif' if date.today().month in [6,7,8,9,10] else 'Rabi'}

Provide this exact JSON structure:
{{
    "npk_ratio": "X:X:X",
    "quantity_per_acre": "XXX kg",
    "total_required": "XXX kg for your farm",
    "recommended_brands": ["Brand1", "Brand2", "Brand3"],
    "application_schedule": [
        {{"stage": "Basal", "timing": "At sowing", "quantity": "XX% of total"}},
        {{"stage": "Top Dressing", "timing": "After X days", "quantity": "XX% of total"}}
    ],
    "organic_alternatives": ["Alternative1", "Alternative2"],
    "estimated_cost": "₹ X,XXX",
    "government_subsidies": "XX% subsidy available under...",
    "soil_health_tips": "Based on your soil type...",
    "irrigation_tips": "Based on your irrigation method...",
    "personalized_advice": "Based on your profile..."
}}

Make recommendations realistic for the crop and location."""

def call_llm_api(prompt):
    """Call LLM API (using Groq as in your existing code)"""
    try:
        if not GROQ_API_KEY:
            return generate_fallback_response(prompt)
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {
                    "role": "system", 
                    "content": "You are an agricultural expert. Always respond with valid JSON only, no additional text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 1024
        }
        
        response = requests.post(GROQ_API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        # Extract JSON from response
        reply = result['choices'][0]['message']['content']
        
        # Try to parse JSON
        try:
            # Extract JSON if wrapped in markdown
            if '```json' in reply:
                json_str = reply.split('```json')[1].split('```')[0].strip()
            elif '```' in reply:
                json_str = reply.split('```')[1].strip()
            else:
                json_str = reply.strip()
            
            return json.loads(json_str)
        except:
            # If JSON parsing fails, return fallback
            return generate_fallback_response(prompt)
            
    except Exception as e:
        print(f"LLM API Error: {e}")
        return generate_fallback_response(prompt)

def generate_fallback_response(prompt):
    """Generate fallback response when LLM fails"""
    if "market" in prompt.lower():
        return {
            "price": f"₹ {random.randint(1800, 3200):,} per quintal",
            "trend": random.choice(["up", "down", "stable"]),
            "trend_percentage": f"{random.uniform(0.5, 5.0):.1f}%",
            "trend_explanation": "Prices influenced by seasonal demand",
            "best_time_to_sell": "Within 7-10 days",
            "nearby_mandis": [
                {"name": "APMC Market", "price": f"₹ {random.randint(1850, 3100):,}", "distance": "15 km"},
                {"name": "Co-op Market", "price": f"₹ {random.randint(1750, 3000):,}", "distance": "25 km"}
            ],
            "storage_advice": "Store in dry place if prices are expected to rise",
            "government_schemes": "Check PM-KISAN for subsidy updates",
            "prediction_next_week": "Stable to slightly upward trend",
            "personalized_advice": "Monitor local mandi prices daily"
        }
    else:
        return {
            "npk_ratio": "10:26:26",
            "quantity_per_acre": "120 kg",
            "total_required": "600 kg for your farm",
            "recommended_brands": ["IFFCO", "Coromandel", "Nagarjuna"],
            "application_schedule": [
                {"stage": "Basal", "timing": "At sowing", "quantity": "50% of total"},
                {"stage": "Top Dressing", "timing": "After 30 days", "quantity": "50% of total"}
            ],
            "organic_alternatives": ["Vermicompost", "Neem cake", "Farmyard manure"],
            "estimated_cost": "₹ 8,400",
            "government_subsidies": "40% subsidy available under PM-KISAN",
            "soil_health_tips": "Add organic matter to improve soil structure",
            "irrigation_tips": "Use drip irrigation for water efficiency",
            "personalized_advice": "Get soil testing done for precise recommendations"
        }

def get_crop_stage(crop):
    """Get crop growth stage based on crop type"""
    stages = {
        'Rice': 'Vegetative',
        'Wheat': 'Tillering',
        'Maize': 'Silking',
        'Cotton': 'Flowering',
        'Sugarcane': 'Grand Growth'
    }
    return stages.get(crop, 'Growing')

def get_next_action(crop):
    """Get next action based on crop type"""
    actions = {
        'Rice': 'Fertilizer application',
        'Wheat': 'Weed control',
        'Maize': 'Harvest preparation',
        'Cotton': 'Pest monitoring',
        'Sugarcane': 'Irrigation'
    }
    return actions.get(crop, 'Regular monitoring')

# ========== CORS PREFLIGHT HANDLER ==========
@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        return "", 200

# ========== LANGUAGE ROUTES ==========
@app.route('/api/languages', methods=['GET'])
def get_languages():
    """Get available languages"""
    languages = [
        {'code': 'en', 'name': 'English', 'native': 'English'},
        {'code': 'hi', 'name': 'Hindi', 'native': 'हिन्दी'},
        {'code': 'te', 'name': 'Telugu', 'native': 'తెలుగు'},
        {'code': 'ta', 'name': 'Tamil', 'native': 'தமிழ்'},
        {'code': 'mr', 'name': 'Marathi', 'native': 'मराठी'},
        {'code': 'bn', 'name': 'Bengali', 'native': 'বাংলা'}
    ]
    return jsonify({'success': True, 'languages': languages})

@app.route('/api/set-language', methods=['POST'])
@login_required
def set_language():
    """Set user's preferred language"""
    try:
        data = request.get_json()
        language = data.get('language', 'en')
        
        # Validate language code
        valid_languages = ['en', 'hi', 'te', 'ta', 'mr', 'bn']
        if language not in valid_languages:
            return jsonify({
                'success': False,
                'message': 'Invalid language code'
            }), 400
        
        # Update user's language preference
        current_user.preferred_language = language
        db.session.commit()
        
        # Update session
        session['user_language'] = language
        
        return jsonify({
            'success': True,
            'message': f'Language updated to {language}',
            'language': language,
            'user_id': current_user.id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating language: {str(e)}'
        }), 500

@app.route('/api/set-guest-language', methods=['POST'])
def set_guest_language():
    """Set language preference for guest users"""
    try:
        data = request.get_json()
        language = data.get('language', 'en')
        
        # Validate language code
        valid_languages = ['en', 'hi', 'te', 'ta', 'mr', 'bn']
        if language not in valid_languages:
            language = 'en'
        
        # Store in session
        session['user_language'] = language
        session['is_guest'] = True
        
        # Create response with cookie
        response = jsonify({
            'success': True,
            'message': f'Language updated to {language}',
            'language': language,
            'is_guest': True
        })
        
        # Set cookie for persistence (1 year)
        response.set_cookie(
            'preferred_language',
            language,
            max_age=365*24*60*60,  # 1 year
            path='/',
            httponly=False,  # Allow JavaScript to read
            samesite='Lax'
        )
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error setting guest language: {str(e)}'
        }), 500

@app.route('/api/detect-language', methods=['GET'])
def detect_language():
    """Detect and suggest language based on browser"""
    try:
        browser_lang = detect_browser_language(request)
        
        # Get suggestion based on browser language
        suggestion = {
            'detected': browser_lang,
            'confidence': 'high',
            'suggested_language': browser_lang,
            'message': f'We detected your browser language as {browser_lang}. Would you like to use this language?'
        }
        
        return jsonify({
            'success': True,
            'suggestion': suggestion,
            'current_language': session.get('user_language', 'en')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error detecting language: {str(e)}'
        }), 500

@app.route('/api/translate', methods=['POST'])
def translate_text():
    """Translate text (for dynamic content)"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        target_lang = data.get('language', 'en')
        
        if not text:
            return jsonify({'success': False, 'message': 'No text provided'}), 400
        
        # For now, return the same text (we'll add actual translation later)
        # You can integrate with Google Translate API or another service here
        translated = f"{text} [{target_lang}]"
        
        return jsonify({
            'success': True,
            'original': text,
            'translated': translated,
            'language': target_lang
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Translation error: {str(e)}'
        }), 500

# ========== VOICE FEATURE ROUTES ==========
@app.route('/api/voice/settings', methods=['POST'])
@login_required
def update_voice_settings():
    """Update user's voice preferences"""
    try:
        data = request.get_json()
        
        voice_enabled = data.get('voice_enabled', True)
        current_user.voice_enabled = voice_enabled
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Voice settings updated',
            'voice_enabled': voice_enabled
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating voice settings: {str(e)}'
        }), 500

@app.route('/api/voice/speak', methods=['POST'])
def text_to_speech():
    """Convert text to speech (server-side if needed)"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        language = data.get('language', 'en')
        
        if not text:
            return jsonify({'success': False, 'message': 'No text provided'}), 400
        
        # For server-side TTS, you could use gTTS or other libraries
        # For now, we'll return success (client-side will handle it)
        return jsonify({
            'success': True,
            'message': 'Text ready for speech synthesis',
            'text_length': len(text),
            'language': language
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'TTS error: {str(e)}'
        }), 500

# ========== CONTEXT PROCESSOR FOR TEMPLATES ==========
@app.context_processor
def inject_user_and_language():
    """Inject user and language info into all templates"""
    context = {}
    
    # Get current language using detection chain
    current_lang = get_user_language_from_request(request)
    
    # Store in session for future requests
    session['user_language'] = current_lang
    
    if current_user.is_authenticated:
        context['current_user'] = current_user
        context['user_language'] = current_user.preferred_language or current_lang
        context['voice_enabled'] = current_user.voice_enabled
        context['is_guest'] = False
        
        # Sync if different (user changed language while logged in)
        if current_user.preferred_language != current_lang:
            current_user.preferred_language = current_lang
            try:
                db.session.commit()
            except:
                db.session.rollback()
    else:
        context['current_user'] = None
        context['user_language'] = current_lang
        context['voice_enabled'] = True
        context['is_guest'] = True
    
    # Make translation function available
    if translation_manager:
        context['t'] = translation_manager.get_text
    else:
        context['t'] = lambda key, lang='en': key
    
    # Add list of available languages for templates
    context['available_languages'] = [
        {'code': 'en', 'name': 'English', 'native': 'English'},
        {'code': 'hi', 'name': 'Hindi', 'native': 'हिन्दी'},
        {'code': 'te', 'name': 'Telugu', 'native': 'తెలుగు'},
        {'code': 'ta', 'name': 'Tamil', 'native': 'தமிழ்'},
        {'code': 'mr', 'name': 'Marathi', 'native': 'मराठी'},
        {'code': 'bn', 'name': 'Bengali', 'native': 'বাংলা'}
    ]
    
    # Add browser language detection info
    context['browser_language'] = detect_browser_language(request)
    
    return context

# ========== AUTHENTICATION ROUTES ==========
@app.route('/signup', methods=['POST'])
def signup():
    """User registration"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Required fields
        required_fields = ['username', 'email', 'password']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()
        
        # Basic validation
        if len(username) < 3:
            return jsonify({
                'success': False,
                'message': 'Username must be at least 3 characters'
            }), 400
        
        if '@' not in email or '.' not in email:
            return jsonify({
                'success': False,
                'message': 'Invalid email format'
            }), 400
        
        if len(password) < 6:
            return jsonify({
                'success': False,
                'message': 'Password must be at least 6 characters'
            }), 400
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            return jsonify({
                'success': False,
                'message': 'Email already registered'
            }), 400

        if User.query.filter_by(username=username).first():
            return jsonify({
                'success': False,
                'message': 'Username already taken'
            }), 400

        # Create new user with detected language
        browser_lang = detect_browser_language(request)
        new_user = User(
            username=username,
            email=email,
            preferred_language=browser_lang,  # Auto-detect from browser
            voice_enabled=data.get('voice_enabled', True)
        )
        new_user.set_password(password)
        
        # Set optional profile fields if provided
        if data.get('state'):
            new_user.state = data['state'].strip()
        if data.get('district'):
            new_user.district = data['district'].strip()
        if data.get('primary_crop'):
            new_user.primary_crop = data['primary_crop'].strip()
        
        # Calculate coordinates if location provided
        if new_user.state and new_user.district:
            latitude, longitude = get_coordinates_from_json(new_user.state, new_user.district)
            new_user.latitude = latitude
            new_user.longitude = longitude
            new_user.profile_completed = True
        
        db.session.add(new_user)
        db.session.commit()
        
        # Log the user in
        login_user(new_user, remember=True)
        
        # Set session language
        session['user_language'] = browser_lang
        
        return jsonify({
            'success': True,
            'message': 'Account created successfully!',
            'user': new_user.to_dict(),
            'detected_language': browser_lang
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error creating account: {str(e)}'
        }), 500

@app.route('/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({
                'success': False,
                'message': 'Email and password are required'
            }), 400

        email = data.get('email').strip().lower()
        password = data.get('password')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if user.is_active:
                login_user(user, remember=True)
                
                # Set session language to user's preference
                session['user_language'] = user.preferred_language or 'en'
                
                return jsonify({
                    'success': True,
                    'message': 'Login successful!',
                    'user': user.to_dict()
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': 'Account is deactivated'
                }), 400
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid email or password'
            }), 401

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Login error: {str(e)}'
        }), 500

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    """User logout"""
    logout_user()
    # Keep guest language preference
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    }), 200

@app.route('/check-auth', methods=['GET'])
def check_auth():
    """Check if user is authenticated"""
    if current_user.is_authenticated:
        return jsonify({
            'success': True,
            'authenticated': True,
            'user': current_user.to_dict()
        }), 200
    
    return jsonify({
        'success': True,
        'authenticated': False,
        'guest_language': session.get('user_language', 'en')
    }), 200

# ========== PROFILE ROUTES ==========
@app.route('/user/profile', methods=['GET'])
@login_required
def get_user_profile():
    """Get user profile"""
    try:
        return jsonify({
            'success': True,
            'user': current_user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching profile: {str(e)}'
        }), 500

@app.route('/save-profile', methods=['POST'])
@login_required
def save_profile():
    """Save user profile"""
    try:
        data = request.get_json()
        user = current_user
        
        # Update fields if provided
        update_fields = ['state', 'district', 'primary_crop', 'soil_type', 'irrigation_type', 'preferred_language', 'voice_enabled']
        
        for field in update_fields:
            if field in data:
                if field == 'voice_enabled':
                    setattr(user, field, bool(data[field]))
                elif field == 'preferred_language' and data[field]:
                    setattr(user, field, data[field].strip())
                    # Update session language
                    session['user_language'] = data[field].strip()
                elif data[field]:
                    setattr(user, field, data[field].strip())
        
        # Update farm_size with validation
        if 'farm_size' in data:
            try:
                farm_size = float(data['farm_size'])
                if farm_size > 0:
                    user.farm_size = farm_size
            except (ValueError, TypeError):
                pass
        
        # Update coordinates if location changed
        if 'state' in data or 'district' in data:
            if user.state and user.district:
                latitude, longitude = get_coordinates_from_json(user.state, user.district)
                user.latitude = latitude
                user.longitude = longitude
        
        user.profile_completed = True
        user.last_weather_fetch = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Profile saved successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error saving profile: {str(e)}'
        }), 500

# ========== PERSONALIZED RECOMMENDATION ROUTES ==========
@app.route('/api/personalized-market', methods=['POST'])
@login_required
def personalized_market():
    """Get personalized market prices"""
    try:
        user_data = request.json
        
        # Get user data if not provided
        if not user_data:
            user_data = current_user.to_dict()
        
        # Create prompt
        prompt = create_market_prompt(user_data)
        
        # Call LLM
        market_data = call_llm_api(prompt)
        
        # Add timestamp
        market_data['timestamp'] = datetime.utcnow().isoformat()
        market_data['user_crop'] = user_data.get('primary_crop', current_user.primary_crop)
        market_data['user_location'] = f"{user_data.get('state', current_user.state)}, {user_data.get('district', current_user.district)}"
        
        return jsonify({
            'success': True,
            'market_data': market_data,
            'user': {
                'crop': user_data.get('primary_crop', current_user.primary_crop),
                'location': f"{user_data.get('state', current_user.state)}, {user_data.get('district', current_user.district)}"
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting market data: {str(e)}',
            'fallback_data': generate_fallback_response("market")
        }), 500

@app.route('/api/fertilizer-recommendation', methods=['POST'])
@login_required
def fertilizer_recommendation():
    """Get personalized fertilizer recommendations"""
    try:
        user_data = request.json
        
        # Get user data if not provided
        if not user_data:
            user_data = current_user.to_dict()
        
        # Create prompt
        prompt = create_fertilizer_prompt(user_data)
        
        # Call LLM
        fertilizer_data = call_llm_api(prompt)
        
        # Add timestamp and user info
        fertilizer_data['timestamp'] = datetime.utcnow().isoformat()
        fertilizer_data['user_crop'] = user_data.get('primary_crop', current_user.primary_crop)
        fertilizer_data['farm_size'] = user_data.get('farm_size', current_user.farm_size)
        
        return jsonify({
            'success': True,
            'fertilizer_data': fertilizer_data,
            'user': {
                'crop': user_data.get('primary_crop', current_user.primary_crop),
                'farm_size': user_data.get('farm_size', current_user.farm_size)
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting fertilizer data: {str(e)}',
            'fallback_data': generate_fallback_response("fertilizer")
        }), 500

@app.route('/api/quick-recommendations', methods=['GET'])
@login_required
def quick_recommendations():
    """Get quick personalized recommendations for dashboard"""
    try:
        user = current_user
        
        # Create simple prompts for quick responses
        market_prompt = f"Current market price for {user.primary_crop} in {user.district}, {user.state} in JSON: {{'price': '₹ X,XXX', 'trend': 'up/down'}}"
        fertilizer_prompt = f"Brief fertilizer for {user.primary_crop} on {user.soil_type} soil in JSON: {{'npk': 'X:X:X', 'quantity': 'XXX kg/acre'}}"
        
        # Get quick responses
        market_response = call_llm_api(market_prompt)
        fertilizer_response = call_llm_api(fertilizer_prompt)
        
        return jsonify({
            'success': True,
            'market': market_response,
            'fertilizer': fertilizer_response,
            'user': {
                'crop': user.primary_crop,
                'location': f"{user.state}, {user.district}",
                'farm_size': user.farm_size
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'market': {'price': '₹ 2,100', 'trend': 'stable'},
            'fertilizer': {'npk': '10:26:26', 'quantity': '120 kg/acre'}
        }), 200

# ========== TASK-BASED RECOMMENDATIONS ==========
@app.route('/api/task-recommendation/<task_type>', methods=['GET'])
@login_required
def task_recommendation(task_type):
    """Get specific task-based recommendations"""
    try:
        user = current_user
        
        task_prompts = {
            'soil_prep': f"Soil preparation for {user.primary_crop} in {user.state} with {user.soil_type} soil. JSON format.",
            'pest_control': f"Pest control for {user.primary_crop} in current season. JSON with methods and products.",
            'irrigation': f"Irrigation schedule for {user.primary_crop} with {user.irrigation_type} irrigation. JSON format.",
            'harvesting': f"Harvesting tips for {user.primary_crop} with expected yield. JSON format."
        }
        
        if task_type not in task_prompts:
            return jsonify({
                'success': False,
                'message': 'Invalid task type'
            }), 400
        
        prompt = task_prompts[task_type]
        recommendation = call_llm_api(prompt)
        
        return jsonify({
            'success': True,
            'task_type': task_type,
            'recommendation': recommendation,
            'user_crop': user.primary_crop
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# ========== DASHBOARD ROUTE ==========
@app.route('/dashboard-data', methods=['GET'])
def dashboard_data():
    """Get dashboard data"""
    try:
        if not current_user.is_authenticated:
            return jsonify({
                'success': True,
                'authenticated': False,
                'profile_completed': False
            }), 200
            
        user = current_user
        
        # Get chat statistics
        chat_sessions = ChatSession.query.filter_by(user_id=user.id).count()
        total_messages = ChatMessage.query.filter_by(user_id=user.id).count()
        
        # Generate personalized market data using LLM
        user_data = user.to_dict()
        market_prompt = f"Current market price for {user.primary_crop} in {user.district} in JSON format."
        
        try:
            market_response = call_llm_api(market_prompt)
            market_data = {
                'crop': user.primary_crop or 'Rice',
                'price': market_response.get('price', '₹ 2,100'),
                'unit': 'per quintal',
                'trend': market_response.get('trend', 'stable'),
                'trend_percentage': market_response.get('trend_percentage', '1.2%'),
                'location': f"{user.state}, {user.district}"
            }
        except:
            # Fallback if LLM fails
            market_data = {
                'crop': user.primary_crop or 'Rice',
                'price': '₹ 2,100',
                'unit': 'per quintal',
                'trend': 'up',
                'trend_percentage': '1.2%',
                'location': f"{user.state}, {user.district}"
            }
        
        # Generate crop status
        crop_status = {
            'stage': get_crop_stage(user.primary_crop),
            'progress': random.randint(30, 80),
            'next_action': get_next_action(user.primary_crop),
            'days_to_harvest': random.randint(30, 120)
        }
        
        # Generate farm updates
        farm_updates = [
            {
                'type': 'weather',
                'title': 'Weather Update',
                'message': 'Clear skies expected for next 3 days',
                'icon': 'fa-cloud-sun',
                'priority': 'info'
            },
            {
                'type': 'crop',
                'title': 'Crop Health',
                'message': f'{user.primary_crop} growing well',
                'icon': 'fa-seedling',
                'priority': 'success'
            },
            {
                'type': 'market',
                'title': 'Price Alert',
                'message': 'Market prices trending upward',
                'icon': 'fa-chart-line',
                'priority': 'warning'
            }
        ]
        
        return jsonify({
            'success': True,
            'authenticated': True,
            'user': user_data,
            'stats': {
                'chat_sessions': chat_sessions,
                'total_messages': total_messages,
                'farm_size': user.farm_size,
                'crop_age': '45 days'
            },
            'market': market_data,
            'crop_status': crop_status,
            'farm_updates': farm_updates,
            'quick_tips': [
                f"Apply fertilizer for {user.primary_crop} this week",
                "Check soil moisture before next irrigation",
                "Monitor for pest activity"
            ]
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error loading dashboard: {str(e)}'
        }), 500

# ========== CHAT ROUTES ==========
@app.route('/chat/init', methods=['POST'])
def init_chat():
    """Initialize chat session"""
    try:            
        data = request.get_json()
        session_id = data.get('session_id', str(uuid.uuid4()))
        title = data.get('title', 'New Chat')
        
        user_id = current_user.id if current_user.is_authenticated else None
        
        if user_id is not None:
            chat_session = ChatSession.query.filter_by(
                session_id=session_id, 
                user_id=user_id
            ).first()
            
            if not chat_session:
                chat_session = ChatSession(
                    session_id=session_id,
                    user_id=user_id,
                    title=title
                )
                db.session.add(chat_session)
                db.session.commit()
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'user_authenticated': bool(user_id),
            'message': 'Chat session initialized'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error initializing chat: {str(e)}'
        }), 500

@app.route('/chat/<session_id>/messages', methods=['GET'])
def get_session_messages(session_id):
    """Get chat messages for a session"""
    try:
        user_id = current_user.id if current_user.is_authenticated else None
        
        messages = get_chat_history(session_id, user_id)
        
        return jsonify({
            'success': True,
            'messages': messages,
            'session_id': session_id,
            'user_authenticated': bool(user_id)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error loading messages: {str(e)}'
        }), 500

@app.route("/chat", methods=["POST"])
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        user_msg = data.get("message", "")
        session_id = data.get("session_id")
        
        if not user_msg:
            return jsonify({
                'success': False,
                'message': 'Message is required'
            }), 400

        if not session_id:
            return jsonify({
                'success': False, 
                'message': 'Session ID is required'
            }), 400

        user_id = current_user.id if current_user.is_authenticated else None
        
        # Get user language for saving message
        user_language = get_user_language_from_request(request)
        
        # Save user message
        save_chat_message(session_id, user_id, 'user', user_msg, language=user_language)

        # Check if API key is available
        if not GROQ_API_KEY:
            reply = "Chat functionality is currently unavailable. Please check the server configuration."
            save_chat_message(session_id, user_id, 'assistant', reply, language=user_language)
            
            return jsonify({
                'success': True,
                'reply': reply,
                'session_id': session_id,
                'saved_to_db': True
            }), 200

        # Call Groq API
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        # Get chat history for context
        history = get_chat_history(session_id, user_id)
        
        # Prepare messages for AI with personalized context
        user_info = ""
        if current_user.is_authenticated:
            user = current_user
            user_info = f"""
            Farmer Profile:
            - Location: {user.state or 'Unknown'}, {user.district or 'Unknown'}
            - Crop: {user.primary_crop or 'Not specified'}
            - Farm Size: {user.farm_size or 'Not specified'} acres
            - Soil: {user.soil_type or 'Not specified'}
            - Irrigation: {user.irrigation_type or 'Not specified'}
            - Preferred Language: {user.preferred_language or 'en'}
            
            Please personalize your advice for this farmer.
            If the user's preferred language is not English, you can include some phrases
            in their language while keeping the main response in English for consistency.
            """
        
        ai_messages = [{"role": "system", "content": f"""You are an agricultural expert for Indian farmers. {user_info}
Provide practical, actionable advice. Consider local conditions, cost-effectiveness, and sustainability.
Always mention if advice is specific to the farmer's location or crop.
If you don't know something, admit it and suggest where to find accurate information."""}]
        
        # Add recent history
        for msg in history[-10:]:
            ai_messages.append({"role": msg['role'], "content": msg['content']})
        
        # Add current message
        ai_messages.append({"role": "user", "content": user_msg})

        data = {
            "model": "llama-3.1-8b-instant",
            "messages": ai_messages,
            "temperature": 0.7,
            "max_tokens": 1024
        }

        response = requests.post(GROQ_API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        reply = result['choices'][0]['message']['content']

        # Save AI response
        save_chat_message(session_id, user_id, 'assistant', reply, language=user_language)

        return jsonify({
            'success': True,
            'reply': reply,
            'session_id': session_id,
            'saved_to_db': True,
            'user_language': user_language
        }), 200
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'message': f'Error connecting to AI service: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Chat error: {str(e)}'
        }), 500

@app.route('/user/chat-sessions', methods=['GET'])
@login_required
def get_chat_sessions():
    """Get user's chat sessions"""
    try:
        sessions = get_user_chat_sessions(current_user.id)
        
        return jsonify({
            'success': True,
            'sessions': sessions
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error loading chat sessions: {str(e)}'
        }), 500

# ========== DATA ROUTES ==========
@app.route('/states-districts.json', methods=['GET'])
def get_states_districts_json():
    """Return states-districts data as JSON"""
    try:
        return jsonify(stateDistricts), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/user/data', methods=['GET'])
@login_required
def get_user_data():
    """Get user data"""
    try:
        return jsonify({
            'success': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'state': current_user.state,
                'district': current_user.district,
                'farm_size': current_user.farm_size,
                'primary_crop': current_user.primary_crop,
                'profile_completed': current_user.profile_completed,
                'preferred_language': current_user.preferred_language,
                'voice_enabled': current_user.voice_enabled
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching user data: {str(e)}'
        }), 500

# ========== TEST & DEBUG ROUTES ==========
@app.route('/test', methods=['GET'])
def test():
    """Test endpoint"""
    return jsonify({
        'success': True,
        'message': 'Flask server is running!',
        'endpoints': [
            'POST /signup',
            'POST /login',
            'POST /logout',
            'POST /save-profile',
            'GET /user/profile',
            'GET /dashboard-data',
            'GET /check-auth',
            'GET /states-districts.json',
            'POST /chat',
            'GET /user/chat-sessions',
            'POST /chat/init',
            'GET /chat/<session_id>/messages',
            'POST /api/personalized-market',
            'POST /api/fertilizer-recommendation',
            'GET /api/quick-recommendations',
            'GET /api/task-recommendation/<task_type>',
            'GET /api/languages',
            'POST /api/set-language',
            'POST /api/set-guest-language',
            'GET /api/detect-language',
            'POST /api/translate',
            'POST /api/voice/settings',
            'POST /api/voice/speak'
        ],
        'language_info': {
            'current_language': get_user_language_from_request(request),
            'browser_language': detect_browser_language(request),
            'session_language': session.get('user_language'),
            'user_authenticated': current_user.is_authenticated,
            'user_language': current_user.preferred_language if current_user.is_authenticated else None
        }
    })

# ========== CORS HEADERS ==========
@app.after_request
def after_request(response):
    """Add CORS headers to all responses"""
    origin = request.headers.get('Origin', '')
    
    allowed_origins = [
        'http://localhost:5500', 'http://127.0.0.1:5500',
        'http://localhost:3000', 'http://127.0.0.1:3000',
        'http://localhost:8080', 'http://127.0.0.1:8080',
        'http://localhost:5000', 'http://127.0.0.1:5000'
    ]
    
    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
    
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,DELETE,OPTIONS,PATCH')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# ========== AUTO-OPEN BROWSER FUNCTION ==========
def open_browser():
    """Automatically open browser when server starts"""
    time.sleep(2)  # Wait for server to fully start
    url = "http://localhost:5001"
    print(f"\n🌐 Opening browser to: {url}")
    
    try:
        # Try to open in default browser
        webbrowser.open(url)
        print("✅ Browser opened successfully!")
        print("\n📝 Quick Start Guide:")
        print("   1. Index page: http://localhost:5001")
        print("   2. Dashboard: http://localhost:5001/dashboard")
        print("   3. Chat: http://localhost:5001/chatbot")
        print("   4. Weather: http://localhost:5001/weather")
        print("\n🛑 Press Ctrl+C to stop the server")
    except Exception as e:
        print(f"⚠️  Could not open browser automatically: {e}")
        print(f"\n📱 Please manually open: {url}")

# ========== INITIALIZE DATABASE & TRANSLATIONS ==========
with app.app_context():
    db.create_all()
    
    # Initialize translation manager
    translation_manager = TranslationManager(app)
    
    print("=" * 60)
    print("✅ Database initialized!")
    print("🌍 Translation manager loaded")
    print(f"📚 Available languages: {', '.join(translation_manager.get_available_languages())}")
    print("🚀 Smart Crop Advisory System Ready!")
    print("📊 SQLite database: users.db")
    print("🌐 Server: http://localhost:5001")
    print("🔐 Flask-Login Authentication")
    print("📍 Districts data loaded from districts.json")
    print(f"📝 States available: {len(stateDistricts)}")
    print("🔄 CORS configured for local development")
    print("🤖 LLM-Powered Personalized Recommendations")
    print("💰 Personalized Market Prices API")
    print("🌱 Personalized Fertilizer Recommendations API")
    print("🗣️  Voice Features Enabled")
    print("🌍 Multi-Language Support Available")
    print("📱 Industry-standard language detection")
    print("👤 Guest user language persistence")
    print("🔗 Context processor provides {{ user_language }} and {{ t() }}")
    print("=" * 60)
    
    if not GROQ_API_KEY:
        print("⚠️  IMPORTANT: Set GROQ_API_KEY in .env file for chat functionality")

if __name__ == "__main__":
    # Start browser in background thread
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)