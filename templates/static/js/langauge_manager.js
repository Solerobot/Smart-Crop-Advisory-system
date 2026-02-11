// static/js/language_manager.js
class LanguageManager {
    constructor() {
        console.log('LanguageManager initialized');
        this.currentLang = document.documentElement.lang || 'en';
    }
    
    changeLanguage(lang) {
        console.log('Changing language to:', lang);
        const url = new URL(window.location);
        url.searchParams.set('lang', lang);
        window.location.href = url.toString();
    }
    
    getCurrentLanguage() {
        return this.currentLang;
    }
}

window.languageManager = new LanguageManager();