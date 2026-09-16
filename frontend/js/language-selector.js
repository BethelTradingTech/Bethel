(() => {
  const STORAGE_KEY = 'bethel-language';
  const languages = {
    en: { label: 'English', dir: 'ltr' },
    fr: { label: 'Français', dir: 'ltr' },
    es: { label: 'Español', dir: 'ltr' },
    ar: { label: 'العربية', dir: 'rtl' },
    pt: { label: 'Português', dir: 'ltr' }
  };

  const translations = {
    fr: {
      'About Us':'À propos','Services':'Services','Performance':'Performance','Contact':'Contact','User Registration':'Inscription utilisateur',
      'Smart Trading Systems':'Systèmes de trading intelligents','Algorithmic Trading Technology for Modern Investors':'Technologie de trading algorithmique pour les investisseurs modernes',
      'Discipline-driven execution. Fully transparent algorithms. Rigorous institutional-grade risk management.':'Exécution disciplinée. Algorithmes entièrement transparents. Gestion rigoureuse des risques de niveau institutionnel.',
      'View Verified Performance':'Voir les performances vérifiées','Partner With Us':'Devenir partenaire','Create Account':'Créer un compte','Our Services':'Nos services','Verified Track Record':'Historique vérifié',
      "Let's Build the Future of Your Capital":"Construisons l’avenir de votre capital",'Direct Inquiries':'Demandes directes','Corporate Channels & Trust':'Canaux officiels et confiance',
      'Your Name':'Votre nom','Email Address':'Adresse e-mail','Your Message':'Votre message','Send Message':'Envoyer le message','All rights reserved.':'Tous droits réservés.'
    },
    es: {
      'About Us':'Nosotros','Services':'Servicios','Performance':'Rendimiento','Contact':'Contacto','User Registration':'Registro de usuario',
      'Smart Trading Systems':'Sistemas de trading inteligentes','Algorithmic Trading Technology for Modern Investors':'Tecnología de trading algorítmico para inversores modernos',
      'Discipline-driven execution. Fully transparent algorithms. Rigorous institutional-grade risk management.':'Ejecución disciplinada. Algoritmos totalmente transparentes. Gestión rigurosa del riesgo de nivel institucional.',
      'View Verified Performance':'Ver rendimiento verificado','Partner With Us':'Asóciese con nosotros','Create Account':'Crear cuenta','Our Services':'Nuestros servicios','Verified Track Record':'Historial verificado',
      "Let's Build the Future of Your Capital":'Construyamos el futuro de su capital','Direct Inquiries':'Consultas directas','Corporate Channels & Trust':'Canales corporativos y confianza',
      'Your Name':'Su nombre','Email Address':'Correo electrónico','Your Message':'Su mensaje','Send Message':'Enviar mensaje','All rights reserved.':'Todos los derechos reservados.'
    },
    ar: {
      'About Us':'من نحن','Services':'الخدمات','Performance':'الأداء','Contact':'اتصل بنا','User Registration':'تسجيل المستخدم',
      'Smart Trading Systems':'أنظمة تداول ذكية','Algorithmic Trading Technology for Modern Investors':'تقنية التداول الخوارزمي للمستثمرين المعاصرين',
      'Discipline-driven execution. Fully transparent algorithms. Rigorous institutional-grade risk management.':'تنفيذ منضبط. خوارزميات شفافة بالكامل. إدارة مخاطر صارمة بمعايير مؤسسية.',
      'View Verified Performance':'عرض الأداء الموثق','Partner With Us':'كن شريكاً معنا','Create Account':'إنشاء حساب','Our Services':'خدماتنا','Verified Track Record':'سجل أداء موثق',
      "Let's Build the Future of Your Capital":'لنبنِ مستقبل رأس مالك','Direct Inquiries':'استفسارات مباشرة','Corporate Channels & Trust':'القنوات الرسمية والثقة',
      'Your Name':'اسمك','Email Address':'البريد الإلكتروني','Your Message':'رسالتك','Send Message':'إرسال الرسالة','All rights reserved.':'جميع الحقوق محفوظة.'
    },
    pt: {
      'About Us':'Sobre nós','Services':'Serviços','Performance':'Desempenho','Contact':'Contacto','User Registration':'Registo de utilizador',
      'Smart Trading Systems':'Sistemas de negociação inteligentes','Algorithmic Trading Technology for Modern Investors':'Tecnologia de negociação algorítmica para investidores modernos',
      'Discipline-driven execution. Fully transparent algorithms. Rigorous institutional-grade risk management.':'Execução disciplinada. Algoritmos totalmente transparentes. Gestão rigorosa de risco de nível institucional.',
      'View Verified Performance':'Ver desempenho verificado','Partner With Us':'Seja nosso parceiro','Create Account':'Criar conta','Our Services':'Os nossos serviços','Verified Track Record':'Histórico verificado',
      "Let's Build the Future of Your Capital":'Vamos construir o futuro do seu capital','Direct Inquiries':'Contactos diretos','Corporate Channels & Trust':'Canais oficiais e confiança',
      'Your Name':'O seu nome','Email Address':'Endereço de e-mail','Your Message':'A sua mensagem','Send Message':'Enviar mensagem','All rights reserved.':'Todos os direitos reservados.'
    }
  };

  const originalText = new WeakMap();
  const translatableSelector = 'a,button,h1,h2,h3,p,span,label,small,strong';

  function translateElement(el, lang) {
    if (el.children.length) return;
    if (!originalText.has(el)) originalText.set(el, el.textContent);
    const original = originalText.get(el);
    const trimmed = original.trim();
    const replacement = lang === 'en' ? trimmed : (translations[lang]?.[trimmed] || trimmed);
    const lead = original.match(/^\s*/)?.[0] || '';
    const tail = original.match(/\s*$/)?.[0] || '';
    el.textContent = lead + replacement + tail;
  }

  function applyLanguage(lang) {
    if (!languages[lang]) lang = 'en';
    document.documentElement.lang = lang;
    document.documentElement.dir = languages[lang].dir;
    document.querySelectorAll(translatableSelector).forEach(el => translateElement(el, lang));
    const select = document.getElementById('bethel-language-select');
    if (select) select.value = lang;
    localStorage.setItem(STORAGE_KEY, lang);
  }

  function mountSelector() {
    const nav = document.querySelector('.nav-container');
    if (!nav || document.getElementById('bethel-language-select')) return;
    const wrap = document.createElement('div');
    wrap.className = 'language-selector';
    wrap.style.cssText = 'margin-left:1rem;display:flex;align-items:center;gap:.45rem;';
    wrap.innerHTML = '<span aria-hidden="true">🌐</span><select id="bethel-language-select" aria-label="Language" style="background:#111827;color:#f3f4f6;border:1px solid #1f2937;border-radius:8px;padding:.55rem .7rem;font:inherit;cursor:pointer"><option value="en">English</option><option value="fr">Français</option><option value="es">Español</option><option value="ar">العربية</option><option value="pt">Português</option></select>';
    nav.appendChild(wrap);
    wrap.querySelector('select').addEventListener('change', e => applyLanguage(e.target.value));
  }

  document.addEventListener('DOMContentLoaded', () => {
    mountSelector();
    const saved = localStorage.getItem(STORAGE_KEY);
    const browser = (navigator.language || 'en').slice(0,2).toLowerCase();
    applyLanguage(languages[saved] ? saved : (languages[browser] ? browser : 'en'));
  });
})();
