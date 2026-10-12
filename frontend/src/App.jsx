import { cloneElement, isValidElement, useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity, ArrowRight, Check, CircleAlert, Clock3, Code2, Command,
  Cpu, FileCode2, FolderGit2, LoaderCircle, Play, RefreshCw, ShieldCheck,
  Sparkles, Terminal, Workflow, Zap,
} from 'lucide-react';

const API_BASE = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001').replace(/\/$/, '');
const DEFAULT_TASK = 'Analyze this repository, explain its architecture, and identify the three highest-priority improvements. Do not modify any files.';

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed with HTTP ${response.status}`);
  return body;
}

function StatusPill({ tone = 'neutral', children }) {
  return <span className={`status-pill status-pill--${tone}`}><span className="status-dot" />{children}</span>;
}

function SectionTitle({ icon: Icon, title, trailing }) {
  return <div className="section-title"><div className="section-heading"><span className="section-icon"><Icon size={16} /></span><h2>{title}</h2></div>{trailing}</div>;
}


// NEXAPATCH_UNIVERSAL_LANGUAGE_V1
// NEXAPATCH_AUTO_UI_V2
// NEXAPATCH_LANG_V4_HINT
const NEXAPATCH_UI_LABELS = Array.from(new Set([
  'ENGINEERING WORKSPACE', 'Agent console', 'Repository', 'Run history', 'recent runs',
  'Read-only mode', 'Phase 1 can inspect and plan. It cannot edit or execute your project code.',
  'Workspace protected', 'Personal environment', 'Developer mode', 'Local build · v0.2.0',
  'Workspace', 'Local workspace', 'WORKSPACE', 'LOCAL ENVIRONMENT', 'AI SOFTWARE ENGINEERING',
  'Good work starts with understanding.',
  'Good work starts with', 'understanding.',
  'Inspect a real codebase, map its architecture, and turn your goal into an evidence-based implementation plan.',
  'Connected', 'Agent API', 'Operational', 'FastAPI · Port 8001', 'Configured', 'AI provider',
  'Groq API', 'Enforced', 'Execution policy', 'Read-only', 'Zero code modifications in Phase 1',
  'PERSISTENT', 'New agent task', 'What should NexaPatch investigate?',
  'Be specific for more relevant file discovery.', 'NexaPatch', 'Repository path validated by backend',
  'Local', 'Run repository analysis',
  'Selected source text is sent to the configured AI provider; review sensitive repositories first.',
  'Execution trace', 'READY', 'Your next task starts here',
  'Submit a task to inspect the configured repository. The trace will show what was actually scanned and whether AI planning ran.',
  'Inspect files', 'Plan changes', 'Report evidence', 'Recent runs', 'Refresh',
  'TASK', 'STATUS', 'MODEL', 'CREATED', 'planned', 'ai error',
  'NexaPatch · Phase 1 foundation', 'Phase 1 foundation', 'Built for responsible AI engineering.',
  'recent',
  'run',
  'runs',
  'Stored locally in SQLite',
  'Built for responsible AI engineering',
  'Running analysis...', 'Discovered files', 'Files in context', 'AI plan', 'Show all files',
  'Show fewer files', 'Repository summary', 'Prepared bounded AI context', 'AI plan generated',
  'Plan ready', 'Scan only', 'AI error', 'Failed', 'Ready', 'Submit', 'Cancel',
  'Loading...', 'Model',
  'Translating interface…',
  'Translation unavailable; English labels are shown.', 'No run history yet', 'No files were discovered',
  'Show more', 'Show less', 'Created', 'Status', 'Request', 'Files', 'Model unavailable',
  'View details',
  'No runs yet', 'No execution data available', 'Analysis complete', 'Analyzing repository',
  'Good morning',
  'Good afternoon',
  'Good evening',
  'Welcome to NexaPatch',
  'Namaste',
  'Local time',
  'Exit workspace',
  'Are you sure you want to exit NexaPatch?',
  'Your current run history will remain saved.',
  'Stay here',
  'Yes, exit',
  'Goodbye!',
  'NexaPatch is ready to close.',
  'You can close this browser tab manually when you are ready.',
  'Return to workspace',
]));

const NEXAPATCH_LANGUAGE_OPTIONS = [
  'English', 'Hindi', 'Spanish', 'French', 'German', 'Portuguese', 'Arabic',
  'Urdu', 'Bengali', 'Punjabi', 'Marathi', 'Tamil', 'Telugu',
  'Japanese', 'Chinese (Simplified)', 'Korean', 'Russian', 'Indonesian',
  'Turkish', 'Swahili', 'Persian', 'Hebrew', 'Italian', 'Dutch',
  'Vietnamese', 'Thai', 'Polish', 'Ukrainian', 'Nepali', 'Sinhala',
  'Gujarati', 'Kannada', 'Malayalam', 'Odia', 'Assamese', 'Filipino',
  'Greek', 'Romanian', 'Czech', 'Hungarian', 'Burmese', 'Khmer',
  'Lao', 'Serbian', 'Croatian', 'Bulgarian', 'Amharic', 'Zulu',
];

const NEXAPATCH_HTML_LANG_CODES = {
  English: 'en', Hindi: 'hi', Spanish: 'es', French: 'fr', German: 'de',
  Portuguese: 'pt', Arabic: 'ar', Urdu: 'ur', Bengali: 'bn', Punjabi: 'pa',
  Marathi: 'mr', Tamil: 'ta', Telugu: 'te', Japanese: 'ja',
  'Chinese (Simplified)': 'zh', Korean: 'ko', Russian: 'ru', Indonesian: 'id',
  Turkish: 'tr', Persian: 'fa', Hebrew: 'he', Italian: 'it', Dutch: 'nl',
  Vietnamese: 'vi', Thai: 'th', Polish: 'pl', Ukrainian: 'uk', Nepali: 'ne',
  Sinhala: 'si', Gujarati: 'gu', Kannada: 'kn', Malayalam: 'ml',
};

const NEXAPATCH_TRANSLATABLE_PROPS = new Set([
  'label', 'title', 'placeholder', 'aria-label', 'alt', 'tooltip', 'description', 'subtitle', 'eyebrow', 'kicker', 'text',
]);

function nexapatchReadPreference(key, fallback = '') {
  try {
    if (typeof window !== 'undefined') {
      return window.localStorage.getItem(key) ?? fallback;
    }
  } catch {
    // Private browsing or storage restrictions should not block the app.
  }
  return fallback;
}

// NEXAPATCH_LOCAL_HI_TRANSLATIONS_V1
// Built-in Hindi UI copy avoids external translation calls and Groq OTPM limits.
const NEXAPATCH_LOCAL_HI_TRANSLATIONS = {
  "ENGINEERING WORKSPACE": "इंजीनियरिंग वर्कस्पेस",
  "Agent console": "एजेंट कंसोल",
  "Repository": "रिपॉज़िटरी",
  "Run history": "रन इतिहास",
  "recent runs": "हाल के रन",
  "Read-only mode": "केवल-पठन मोड",
  "Phase 1 can inspect and plan. It cannot edit or execute your project code.": "चरण 1 में प्रोजेक्ट का निरीक्षण और योजना बनाई जा सकती है। यह आपके प्रोजेक्ट की फ़ाइलों में बदलाव या कोड निष्पादित नहीं कर सकता।",
  "Workspace protected": "वर्कस्पेस सुरक्षित है",
  "Personal environment": "व्यक्तिगत वातावरण",
  "Developer mode": "डेवलपर मोड",
  "Local build · v0.2.0": "लोकल बिल्ड · v0.2.0",
  "Workspace": "वर्कस्पेस",
  "Local workspace": "लोकल वर्कस्पेस",
  "WORKSPACE": "वर्कस्पेस",
  "LOCAL ENVIRONMENT": "लोकल वातावरण",
  "AI SOFTWARE ENGINEERING": "AI सॉफ़्टवेयर इंजीनियरिंग",
  "Good work starts with understanding.": "अच्छा काम सही समझ से शुरू होता है।",
  "Good work starts with": "अच्छा काम सही",
  "understanding.": "समझ से शुरू होता है।",
  "Inspect a real codebase, map its architecture, and turn your goal into an evidence-based implementation plan.": "वास्तविक कोडबेस की जाँच करें, उसकी संरचना समझें और अपने लक्ष्य को प्रमाण-आधारित कार्यान्वयन योजना में बदलें।",
  "Connected": "कनेक्टेड",
  "Agent API": "एजेंट API",
  "Operational": "सक्रिय",
  "FastAPI · Port 8001": "FastAPI · पोर्ट 8001",
  "Configured": "कॉन्फ़िगर किया गया",
  "AI provider": "AI प्रदाता",
  "Groq API": "Groq API",
  "Enforced": "लागू",
  "Execution policy": "निष्पादन नीति",
  "Read-only": "केवल-पठन",
  "Zero code modifications in Phase 1": "चरण 1 में कोड में कोई बदलाव नहीं",
  "PERSISTENT": "स्थायी",
  "New agent task": "नया एजेंट कार्य",
  "What should NexaPatch investigate?": "NexaPatch को किस चीज़ की जाँच करनी चाहिए?",
  "Be specific for more relevant file discovery.": "संबंधित फ़ाइलें बेहतर ढंग से खोजने के लिए स्पष्ट विवरण दें।",
  "NexaPatch": "NexaPatch",
  "Repository path validated by backend": "बैकएंड ने रिपॉज़िटरी पाथ की पुष्टि की",
  "Local": "लोकल",
  "Run repository analysis": "रिपॉज़िटरी विश्लेषण चलाएँ",
  "Selected source text is sent to the configured AI provider; review sensitive repositories first.": "चुना गया सोर्स टेक्स्ट कॉन्फ़िगर किए गए AI प्रदाता को भेजा जाता है; संवेदनशील रिपॉज़िटरी का उपयोग करने से पहले इसकी समीक्षा करें।",
  "Execution trace": "निष्पादन ट्रेस",
  "READY": "तैयार",
  "Your next task starts here": "आपका अगला कार्य यहाँ शुरू होता है",
  "Submit a task to inspect the configured repository. The trace will show what was actually scanned and whether AI planning ran.": "कॉन्फ़िगर की गई रिपॉज़िटरी की जाँच के लिए कार्य सबमिट करें। ट्रेस दिखाएगा कि वास्तव में क्या स्कैन हुआ और AI योजना बनी या नहीं।",
  "Inspect files": "फ़ाइलों की जाँच",
  "Plan changes": "बदलावों की योजना",
  "Report evidence": "प्रमाण रिपोर्ट",
  "Recent runs": "हाल के रन",
  "Refresh": "रीफ़्रेश करें",
  "TASK": "कार्य",
  "STATUS": "स्थिति",
  "MODEL": "मॉडल",
  "CREATED": "बनाया गया",
  "planned": "योजना तैयार",
  "ai error": "AI त्रुटि",
  "NexaPatch · Phase 1 foundation": "NexaPatch · चरण 1 की नींव",
  "Phase 1 foundation": "चरण 1 की नींव",
  "Built for responsible AI engineering.": "ज़िम्मेदार AI इंजीनियरिंग के लिए बनाया गया।",
  "Running analysis...": "विश्लेषण चल रहा है...",
  "Discovered files": "मिली हुई फ़ाइलें",
  "Files in context": "कॉन्टेक्स्ट में फ़ाइलें",
  "AI plan": "AI योजना",
  "Show all files": "सभी फ़ाइलें दिखाएँ",
  "Show fewer files": "कम फ़ाइलें दिखाएँ",
  "Repository summary": "रिपॉज़िटरी सारांश",
  "Prepared bounded AI context": "सीमित AI कॉन्टेक्स्ट तैयार किया गया",
  "AI plan generated": "AI योजना तैयार हुई",
  "Plan generated": "योजना तैयार हुई",
  "recent": "हाल के",
  "run": "रन",
  "runs": "रन",
  "Stored locally in SQLite": "SQLite में स्थानीय रूप से सहेजा गया",
  "Built for responsible AI engineering": "ज़िम्मेदार AI इंजीनियरिंग के लिए बनाया गया",
  "RUN TIMELINE": "रन टाइमलाइन",
  "events": "इवेंट",
  "Files changed": "बदली गई फ़ाइलें",
  "Inspectable files found": "जाँची जा सकने वाली फ़ाइलें मिलीं",
  "Plan ready": "योजना तैयार है",
  "Scan only": "केवल स्कैन",
  "AI error": "AI त्रुटि",
  "Failed": "विफल",
  "Ready": "तैयार",
  "Submit": "सबमिट करें",
  "Cancel": "रद्द करें",
  "Loading...": "लोड हो रहा है...",
  "Model": "मॉडल",
  "Translating interface…": "इंटरफ़ेस का अनुवाद हो रहा है…",
  "Translation unavailable; English labels are shown.": "अनुवाद उपलब्ध नहीं है; अंग्रेज़ी लेबल दिखाए जा रहे हैं।",
  "No run history yet": "अभी तक कोई रन इतिहास नहीं है",
  "No files were discovered": "कोई फ़ाइल नहीं मिली",
  "Show more": "और दिखाएँ",
  "Show less": "कम दिखाएँ",
  "Created": "बनाया गया",
  "Status": "स्थिति",
  "Request": "अनुरोध",
  "Files": "फ़ाइलें",
  "Model unavailable": "मॉडल उपलब्ध नहीं है",
  "View details": "विवरण देखें",
  "No runs yet": "अभी तक कोई रन नहीं है",
  "No execution data available": "निष्पादन डेटा उपलब्ध नहीं है",
  "Analysis complete": "विश्लेषण पूरा हुआ",
  "Analyzing repository": "रिपॉज़िटरी का विश्लेषण हो रहा है",
  "Example: Trace the login flow and identify the most important security gaps...": "उदाहरण: लॉगिन प्रक्रिया का पता लगाएँ और सबसे महत्वपूर्ण सुरक्षा कमियाँ पहचानें...",
  "Waiting for backend configuration": "बैकएंड कॉन्फ़िगरेशन की प्रतीक्षा है",
  "Inspecting repository...": "रिपॉज़िटरी की जाँच हो रही है...",
  "Good morning": "सुप्रभात",
  "Good afternoon": "नमस्कार",
  "Good evening": "शुभ संध्या",
  "Welcome to NexaPatch": "NexaPatch में आपका स्वागत है",
  "Namaste": "नमस्ते",
  "Local time": "स्थानीय समय",
  "Exit workspace": "NexaPatch से बाहर जाएँ",
  "Are you sure you want to exit NexaPatch?": "क्या आप वाकई NexaPatch से बाहर जाना चाहते हैं?",
  "Your current run history will remain saved.": "आपके मौजूदा रन का इतिहास सुरक्षित रहेगा।",
  "Stay here": "यहीं रहें",
  "Yes, exit": "हाँ, बाहर जाएँ",
  "Goodbye!": "फिर मिलेंगे!",
  "NexaPatch is ready to close.": "NexaPatch अब बंद करने के लिए तैयार है।",
  "You can close this browser tab manually when you are ready.": "तैयार होने पर आप इस ब्राउज़र टैब को स्वयं बंद कर सकते हैं।",
  "Return to workspace": "वर्कस्पेस पर वापस जाएँ",
};

function nexapatchBrowserLanguageName() {
  const candidates = (typeof navigator !== 'undefined')
    ? (Array.isArray(navigator.languages) && navigator.languages.length
      ? navigator.languages
      : [navigator.language || 'en'])
    : ['en'];
  const languageNames = {
    en: 'English', hi: 'Hindi', es: 'Spanish', fr: 'French', de: 'German',
    pt: 'Portuguese', ar: 'Arabic', ur: 'Urdu', bn: 'Bengali', pa: 'Punjabi',
    mr: 'Marathi', ta: 'Tamil', te: 'Telugu', ja: 'Japanese', zh: 'Chinese (Simplified)',
    ko: 'Korean', ru: 'Russian', id: 'Indonesian', tr: 'Turkish', fa: 'Persian',
    he: 'Hebrew', it: 'Italian', nl: 'Dutch', vi: 'Vietnamese', th: 'Thai',
    pl: 'Polish', uk: 'Ukrainian', ne: 'Nepali', si: 'Sinhala', gu: 'Gujarati',
    kn: 'Kannada', ml: 'Malayalam', or: 'Odia', as: 'Assamese', fil: 'Filipino',
    el: 'Greek', ro: 'Romanian', cs: 'Czech', hu: 'Hungarian', my: 'Burmese',
    km: 'Khmer', lo: 'Lao', sr: 'Serbian', hr: 'Croatian', bg: 'Bulgarian',
    am: 'Amharic', zu: 'Zulu',
  };
  for (const candidate of candidates) {
    const code = String(candidate || '').toLowerCase().split('-')[0];
    if (languageNames[code]) return languageNames[code];
  }
  return 'English';
}

function nexapatchDetectLanguageFromText(text) {
  const value = String(text || '').trim();
  if (!value) return null;
  if (/[\u3040-\u30ff]/.test(value)) return 'Japanese';
  if (/[\uac00-\ud7af]/.test(value)) return 'Korean';
  if (/[\u4e00-\u9fff]/.test(value)) return 'Chinese (Simplified)';
  if (/[\u0e00-\u0e7f]/.test(value)) return 'Thai';
  if (/[\u0d00-\u0d7f]/.test(value)) return 'Malayalam';
  if (/[\u0c80-\u0cff]/.test(value)) return 'Kannada';
  if (/[\u0c00-\u0c7f]/.test(value)) return 'Telugu';
  if (/[\u0b80-\u0bff]/.test(value)) return 'Tamil';
  if (/[\u0a80-\u0aff]/.test(value)) return 'Gujarati';
  if (/[\u0a00-\u0a7f]/.test(value)) return 'Punjabi';
  if (/[\u0980-\u09ff]/.test(value)) return 'Bengali';
  if (/[\u0900-\u097f]/.test(value)) {
    return /[ळऱ]/.test(value) ? 'Marathi' : 'Hindi';
  }
  if (/[\u0590-\u05ff]/.test(value)) return 'Hebrew';
  if (/[\u0400-\u04ff]/.test(value)) return 'Russian';
  if (/[\u0600-\u06ff]/.test(value)) {
    return /[ٹڈڑںھہے]/.test(value) ? 'Urdu' : 'Arabic';
  }
  if (/[\u1200-\u137f]/.test(value)) return 'Amharic';

  const lower = ` ${value.toLowerCase()} `;
  if (/\b(hola|gracias|por favor|necesito|quiero|¿qué|analiza|repositorio)\b/.test(lower)) return 'Spanish';
  if (/\b(bonjour|merci|s'il vous plaît|je voudrais|analyse|référentiel)\b/.test(lower)) return 'French';
  if (/\b(hallo|danke|bitte|ich möchte|analysiere|repository analysieren)\b/.test(lower)) return 'German';
  if (/\b(obrigado|obrigada|por favor|você|preciso|projeto|analisar)\b/.test(lower)) return 'Portuguese';
  if (/\b(ciao|grazie|per favore|vorrei|progetto|analizza)\b/.test(lower)) return 'Italian';
  if (/\b(bhai|mai|mujhe|aap|hum|hai|hain|ho|kya|kaise|samjhao|batao|bata|karna|karo|krdo|kyun|mera|meri|mere|iske|isko|chahiye|banao|kar|aur|nahi|nahin|theek|accha|achha)\b/.test(lower)) return 'Hindi';
  if (/\b(hello|please|thanks|the|this|that|can you|analyze|analyse|repository|project|explain|improve|fix|build)\b/.test(lower)) return 'English';

  // For scripts/languages that cannot be inferred confidently, use the browser locale.
  if (/^[\x00-\x7F\s\p{P}\p{N}]+$/u.test(value)) return 'English';
  return nexapatchBrowserLanguageName();
}

function nexapatchTranslateNode(node, translations) {
  // NEXAPATCH_TRIM_AWARE_TRANSLATION_V1
  if (typeof node === 'string') {
    const trimmedNode = node.trim();
    if (!trimmedNode) return node;
    const translatedNode = translations[trimmedNode];
    if (typeof translatedNode !== 'string' || !translatedNode) return node;
    const leadingWhitespace = node.match(/^\s*/u)?.[0] || '';
    const trailingWhitespace = node.match(/\s*$/u)?.[0] || '';
    return `${leadingWhitespace}${translatedNode}${trailingWhitespace}`;
  }
  if (Array.isArray(node)) {
    return node.map((child, index) => {
      const translatedChild = nexapatchTranslateNode(child, translations);
      if (isValidElement(translatedChild) && translatedChild.key == null) {
        return cloneElement(translatedChild, { key: `nexapatch-static-${index}` });
      }
      return translatedChild;
    });
  }
  if (!isValidElement(node)) return node;

  const nextProps = {};
  for (const [propName, propValue] of Object.entries(node.props || {})) {
    if (propName === 'children') {
      nextProps.children = nexapatchTranslateNode(propValue, translations);
    } else if (
      typeof propValue === 'string' &&
      NEXAPATCH_TRANSLATABLE_PROPS.has(propName)
    ) {
      nextProps[propName] = translations[propValue] || propValue;
    } else {
      nextProps[propName] = propValue;
    }
  }
  return cloneElement(node, nextProps);
}

// NEXAPATCH_AGENT_PLAN_MARKDOWN_V1
function nexapatchNormalizePlanMarkdown(value) {
  return String(value ?? "")
    .replace(/\\([\\`*_{}\[\]()#+\-.!|>~])/g, "$1")
    .replace(/\r\n?/g, "\n");
}

function nexapatchRenderPlanInline(text, keyPrefix) {
  const tokenPattern = /(\*\*[\s\S]+?\*\*|~~[\s\S]+?~~|`[^`\n]+`|\*[^*\n]+\*)/g;
  return String(text).split(tokenPattern).filter((part) => part !== "").map((part, index) => {
    const key = `${keyPrefix}-inline-${index}`;
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={key}>{nexapatchRenderPlanInline(part.slice(2, -2), key)}</strong>;
    }
    if (part.startsWith("~~") && part.endsWith("~~")) {
      return <del key={key}>{nexapatchRenderPlanInline(part.slice(2, -2), key)}</del>;
    }
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
      return <em key={key}>{nexapatchRenderPlanInline(part.slice(1, -1), key)}</em>;
    }
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return <code className="plan-inline-code" key={key}>{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

function nexapatchPlanBlockStart(line) {
  return /^\s*```/.test(line)
    || /^\s*#{1,6}\s+/.test(line)
    || /^\s*[-*+]\s+/.test(line)
    || /^\s*\d+[.)]\s+/.test(line)
    || /^\s*>\s?/.test(line)
    || /^\s*(?:---+|___+|\*\*\*+)\s*$/.test(line);
}

function NexaPatchAgentPlanMarkdown({ content }) {
  const normalized = nexapatchNormalizePlanMarkdown(content);
  const lines = normalized.split("\n");
  const blocks = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }

    const fence = /^\s*```([\w.+-]*)\s*$/.exec(line);
    if (fence) {
      const codeLines = [];
      index += 1;
      while (index < lines.length && !/^\s*```\s*$/.test(lines[index])) {
        codeLines.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) index += 1;
      blocks.push({ type: "code", language: fence[1], text: codeLines.join("\n") });
      continue;
    }

    const heading = /^\s*(#{1,6})\s+(.+)$/.exec(line);
    if (heading) {
      blocks.push({ type: "heading", level: heading[1].length, text: heading[2] });
      index += 1;
      continue;
    }

    if (/^\s*(?:---+|___+|\*\*\*+)\s*$/.test(line)) {
      blocks.push({ type: "rule" });
      index += 1;
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      const quoteLines = [];
      while (index < lines.length && /^\s*>\s?/.test(lines[index])) {
        quoteLines.push(lines[index].replace(/^\s*>\s?/, ""));
        index += 1;
      }
      blocks.push({ type: "quote", text: quoteLines.join(" ") });
      continue;
    }

    if (/^\s*[-*+]\s+/.test(line)) {
      const items = [];
      while (index < lines.length && /^\s*[-*+]\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*[-*+]\s+/, ""));
        index += 1;
      }
      blocks.push({ type: "unordered", items });
      continue;
    }

    if (/^\s*\d+[.)]\s+/.test(line)) {
      const items = [];
      while (index < lines.length && /^\s*\d+[.)]\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*\d+[.)]\s+/, ""));
        index += 1;
      }
      blocks.push({ type: "ordered", items });
      continue;
    }

    const paragraphLines = [line.trim()];
    index += 1;
    while (index < lines.length && lines[index].trim() && !nexapatchPlanBlockStart(lines[index])) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    blocks.push({ type: "paragraph", text: paragraphLines.join(" ") });
  }

  return (
    <div className="plan-text plan-markdown">
      {blocks.map((block, blockIndex) => {
        const key = `plan-block-${blockIndex}`;
        if (block.type === "heading") {
          const HeadingTag = block.level <= 2 ? "h3" : block.level <= 4 ? "h4" : "h5";
          return <HeadingTag key={key}>{nexapatchRenderPlanInline(block.text, key)}</HeadingTag>;
        }
        if (block.type === "paragraph") {
          return <p key={key}>{nexapatchRenderPlanInline(block.text, key)}</p>;
        }
        if (block.type === "unordered" || block.type === "ordered") {
          const ListTag = block.type === "unordered" ? "ul" : "ol";
          return (
            <ListTag key={key}>
              {block.items.map((item, itemIndex) => (
                <li key={`${key}-item-${itemIndex}`}>{nexapatchRenderPlanInline(item, `${key}-item-${itemIndex}`)}</li>
              ))}
            </ListTag>
          );
        }
        if (block.type === "code") {
          return <pre className="plan-code" key={key}><code>{block.text}</code></pre>;
        }
        if (block.type === "quote") {
          return <blockquote key={key}>{nexapatchRenderPlanInline(block.text, key)}</blockquote>;
        }
        if (block.type === "rule") return <hr key={key} />;
        return null;
      })}
    </div>
  );
}

function NexaPatchLocalizedTree({ children, translations }) {
  return <>{nexapatchTranslateNode(children, translations)}</>;
}

function NexaPatchLanguageSwitcher({
  languageMode,
  setLanguageMode,
  responseLanguage,
  setResponseLanguage,
  customLanguage,
  setCustomLanguage,
  translations,
  translationLoading,
}) {
  const t = (label) => translations[label] || label;
  const isPreset = NEXAPATCH_LANGUAGE_OPTIONS.includes(responseLanguage);
  const selectedValue = languageMode === 'auto'
    ? 'auto'
    : (isPreset ? responseLanguage : '__other__');

  const onLanguageChange = (event) => {
    const value = event.target.value;
    if (value === 'auto') {
      setLanguageMode('auto');
      return;
    }
    if (value === '__other__') {
      setLanguageMode('manual');
      setResponseLanguage('');
      setCustomLanguage('');
      return;
    }
    setLanguageMode('manual');
    setResponseLanguage(value);
    setCustomLanguage('');
  };

  return (
    <aside
      aria-label={t('Language')}
      style={{
        position: 'fixed', top: 12, right: 16, zIndex: 1000,
        display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
        maxWidth: 'min(560px, calc(100vw - 24px))',
        padding: '8px 10px', borderRadius: 12,
        border: '1px solid #334155', background: 'rgba(15, 23, 42, 0.96)',
        boxShadow: '0 8px 28px rgba(0,0,0,.28)', color: '#e2e8f0',
        fontFamily: 'inherit', fontSize: 12,
      }}
    >
      <span style={{ fontWeight: 700, whiteSpace: 'nowrap' }}>🌐 {t('Language')}</span>
      <select
        aria-label={t('Select language')}
        value={selectedValue}
        onChange={onLanguageChange}
        style={{
          maxWidth: 205, padding: '7px 9px', borderRadius: 8,
          border: '1px solid #475569', background: '#111827', color: '#f8fafc',
          fontSize: 12,
        }}
      >
        <option value="auto">{t('Auto-detect')}</option>
        {NEXAPATCH_LANGUAGE_OPTIONS.map((language) => (
          <option key={language} value={language}>{language}</option>
        ))}
        <option value="__other__">{t('Other language…')}</option>
      </select>
      {selectedValue === '__other__' && (
        <input
          aria-label={t('Type a language name')}
          placeholder={t('Type a language name')}
          value={customLanguage}
          onChange={(event) => {
            const value = event.target.value.slice(0, 80);
            setCustomLanguage(value);
            setResponseLanguage(value);
            setLanguageMode('manual');
          }}
          style={{
            width: 145, padding: '7px 9px', borderRadius: 8,
            border: '1px solid #475569', background: '#111827', color: '#f8fafc',
            fontSize: 12,
          }}
        />
      )}
      {translationLoading && (
        <span aria-live="polite" style={{ color: '#94a3b8' }}>
          {t('Translating interface…')}
        </span>
      )}
    </aside>
  );
}

// NEXAPATCH_GREETING_MOTION_V2
const NEXAPATCH_GREETING_PROFILES = {
  IN: {
    name: "India", namaste: true, icon: "🙏",
    morning: ["सुप्रभात", "Good morning"], afternoon: ["नमस्कार", "Good afternoon"], evening: ["शुभ संध्या", "Good evening"],
    farewell: ["फिर मिलेंगे!", "Goodbye!"],
  },
  US: { name: "United States", icon: "👋", morning: ["Good morning"], afternoon: ["Good afternoon"], evening: ["Good evening"], farewell: ["Goodbye!"] },
  GB: { name: "United Kingdom", icon: "👋", morning: ["Good morning"], afternoon: ["Good afternoon"], evening: ["Good evening"], farewell: ["Cheerio!", "Goodbye!"] },
  CA: { name: "Canada", icon: "🍁", morning: ["Good morning"], afternoon: ["Hello"], evening: ["Good evening"], farewell: ["See you soon!"] },
  AU: { name: "Australia", icon: "🦘", morning: ["Good morning"], afternoon: ["G’day"], evening: ["Good evening"], farewell: ["See you soon!"] },
  JP: { name: "Japan", icon: "🌸", morning: ["おはようございます"], afternoon: ["こんにちは"], evening: ["こんばんは"], farewell: ["さようなら"], ui: { "Welcome to NexaPatch": "NexaPatchへようこそ", "Local time": "現地時間", "Exit workspace": "ワークスペースを終了", "Are you sure you want to exit NexaPatch?": "NexaPatchを終了してもよろしいですか？", "Your current run history will remain saved.": "実行履歴は保存されます。", "Stay here": "ここに残る", "Yes, exit": "終了する", "Goodbye!": "さようなら", "NexaPatch is ready to close.": "NexaPatchを終了できます。", "You can close this browser tab manually when you are ready.": "準備ができたら、このブラウザータブを閉じてください。", "Return to workspace": "ワークスペースに戻る" } },
  FR: { name: "France", icon: "👋", morning: ["Bonjour"], afternoon: ["Bonjour"], evening: ["Bonsoir"], farewell: ["Au revoir !"], ui: { "Welcome to NexaPatch": "Bienvenue sur NexaPatch", "Local time": "Heure locale", "Exit workspace": "Quitter l’espace", "Are you sure you want to exit NexaPatch?": "Voulez-vous vraiment quitter NexaPatch ?", "Your current run history will remain saved.": "L’historique de vos exécutions sera conservé.", "Stay here": "Rester ici", "Yes, exit": "Oui, quitter", "Goodbye!": "Au revoir !", "NexaPatch is ready to close.": "NexaPatch est prêt à se fermer.", "You can close this browser tab manually when you are ready.": "Vous pourrez fermer cet onglet manuellement lorsque vous serez prêt.", "Return to workspace": "Retour à l’espace de travail" } },
  DE: { name: "Deutschland", icon: "👋", morning: ["Guten Morgen"], afternoon: ["Guten Tag"], evening: ["Guten Abend"], farewell: ["Auf Wiedersehen!"], ui: { "Welcome to NexaPatch": "Willkommen bei NexaPatch", "Local time": "Ortszeit", "Exit workspace": "Arbeitsbereich verlassen", "Are you sure you want to exit NexaPatch?": "Möchtest du NexaPatch wirklich verlassen?", "Your current run history will remain saved.": "Dein bisheriger Verlauf bleibt gespeichert.", "Stay here": "Hier bleiben", "Yes, exit": "Ja, verlassen", "Goodbye!": "Auf Wiedersehen!", "NexaPatch is ready to close.": "NexaPatch kann jetzt geschlossen werden.", "You can close this browser tab manually when you are ready.": "Du kannst diesen Browser-Tab schließen, sobald du bereit bist.", "Return to workspace": "Zum Arbeitsbereich zurückkehren" } },
  ES: { name: "España", icon: "👋", morning: ["Buenos días"], afternoon: ["Buenas tardes"], evening: ["Buenas noches"], farewell: ["¡Hasta luego!"], ui: { "Welcome to NexaPatch": "Te damos la bienvenida a NexaPatch", "Local time": "Hora local", "Exit workspace": "Salir del espacio de trabajo", "Are you sure you want to exit NexaPatch?": "¿Seguro que quieres salir de NexaPatch?", "Your current run history will remain saved.": "El historial de ejecuciones se conservará.", "Stay here": "Quedarme", "Yes, exit": "Sí, salir", "Goodbye!": "¡Hasta luego!", "NexaPatch is ready to close.": "NexaPatch está listo para cerrarse.", "You can close this browser tab manually when you are ready.": "Puedes cerrar esta pestaña del navegador cuando quieras.", "Return to workspace": "Volver al espacio de trabajo" } },
  IT: { name: "Italia", icon: "👋", morning: ["Buongiorno"], afternoon: ["Buon pomeriggio"], evening: ["Buonasera"], farewell: ["Arrivederci!" ] },
  BR: { name: "Brasil", icon: "👋", morning: ["Bom dia"], afternoon: ["Boa tarde"], evening: ["Boa noite"], farewell: ["Até logo!"], ui: { "Welcome to NexaPatch": "Boas-vindas ao NexaPatch", "Local time": "Horário local", "Exit workspace": "Sair do espaço de trabalho", "Are you sure you want to exit NexaPatch?": "Tem certeza de que deseja sair do NexaPatch?", "Your current run history will remain saved.": "Seu histórico de execuções será mantido.", "Stay here": "Ficar aqui", "Yes, exit": "Sim, sair", "Goodbye!": "Até logo!", "NexaPatch is ready to close.": "O NexaPatch está pronto para ser fechado.", "You can close this browser tab manually when you are ready.": "Você pode fechar esta aba do navegador quando estiver pronto.", "Return to workspace": "Voltar ao espaço de trabalho" } },
  CN: { name: "中国", icon: "👋", morning: ["早上好"], afternoon: ["你好"], evening: ["晚上好"], farewell: ["再见！"], ui: { "Welcome to NexaPatch": "欢迎使用 NexaPatch", "Local time": "当地时间", "Exit workspace": "退出工作区", "Are you sure you want to exit NexaPatch?": "确定要退出 NexaPatch 吗？", "Your current run history will remain saved.": "当前运行历史将会保留。", "Stay here": "留在这里", "Yes, exit": "确认退出", "Goodbye!": "再见！", "NexaPatch is ready to close.": "NexaPatch 已准备好关闭。", "You can close this browser tab manually when you are ready.": "准备好后，你可以手动关闭此浏览器标签页。", "Return to workspace": "返回工作区" } },
  KR: { name: "대한민국", icon: "👋", morning: ["좋은 아침입니다"], afternoon: ["안녕하세요"], evening: ["좋은 저녁입니다"], farewell: ["안녕히 가세요"] },
  ID: { name: "Indonesia", icon: "👋", morning: ["Selamat pagi"], afternoon: ["Selamat siang"], evening: ["Selamat malam"], farewell: ["Sampai jumpa!"] },
  TH: { name: "ประเทศไทย", icon: "👋", morning: ["อรุณสวัสดิ์"], afternoon: ["สวัสดี"], evening: ["สวัสดีตอนเย็น"], farewell: ["แล้วพบกันใหม่"] },
  SA: { name: "السعودية", icon: "👋", morning: ["صباح الخير"], afternoon: ["مرحباً"], evening: ["مساء الخير"], farewell: ["إلى اللقاء"] },
  AE: { name: "الإمارات", icon: "👋", morning: ["صباح الخير"], afternoon: ["مرحباً"], evening: ["مساء الخير"], farewell: ["إلى اللقاء"] },
  RU: { name: "Россия", icon: "👋", morning: ["Доброе утро"], afternoon: ["Здравствуйте"], evening: ["Добрый вечер"], farewell: ["До свидания!"] },
  PK: { name: "پاکستان", icon: "👋", morning: ["صبح بخیر"], afternoon: ["السلام علیکم"], evening: ["شام بخیر"], farewell: ["اللہ حافظ"] },
  BD: { name: "বাংলাদেশ", icon: "👋", morning: ["সুপ্রভাত"], afternoon: ["শুভ অপরাহ্ণ"], evening: ["শুভ সন্ধ্যা"], farewell: ["আবার দেখা হবে"] },
  MX: { name: "México", icon: "👋", morning: ["Buenos días"], afternoon: ["Buenas tardes"], evening: ["Buenas noches"], farewell: ["¡Hasta luego!"] },
};

// NEXAPATCH_GREETING_JOIN_BOW_V3
// NEXAPATCH_SIMPLE_EMOJI_GREETING_V5
function NexaPatchGreetingGesture({ kind, icon = "👋", goodbye = false }) {
  // Keep the visual intentionally simple and native-looking: use a greeting emoji,
  // not a drawn/cartoon character. Country profile logic remains in the parent.
  const greetingEmoji = kind === "namaste" ? "🙏" : kind === "bow" ? "🙇" : "👋";
  return (
    <div
      className={`nx-simple-emoji-scene${goodbye ? " nx-simple-emoji-scene-goodbye" : ""}`}
      aria-hidden="true"
    >
      <span className={`nx-simple-greeting-emoji${kind === "namaste" ? " nx-simple-greeting-namaste" : ""}`}>
        {greetingEmoji || icon}
      </span>
    </div>
  );
}

function NexaPatchWelcomeAndExit({ translations = {} }) {
  const [clockNow, setClockNow] = useState(() => new Date());
  const [exitView, setExitView] = useState("welcome");
  const [greetingVisible, setGreetingVisible] = useState(true);

  useEffect(() => {
    const timer = window.setInterval(() => setClockNow(new Date()), 60_000);
    return () => window.clearInterval(timer);
  }, []);

  // Show the welcome motion once per component mount, then remove it from the page.
  useEffect(() => {
    const timer = window.setTimeout(() => setGreetingVisible(false), 5_350);
    return () => window.clearTimeout(timer);
  }, []);

  const browserLocales = typeof navigator === "undefined"
    ? ["en-US"]
    : [...(navigator.languages || []), navigator.language].filter(Boolean);
  const primaryLocale = String(browserLocales[0] || "en-US");
  const primaryLanguage = primaryLocale.split(/[-_]/)[0].toLowerCase();
  let timeZone = "";
  try { timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch { timeZone = ""; }

  const timezoneCountry = (() => {
    if (timeZone === "Asia/Kolkata" || timeZone === "Asia/Calcutta") return "IN";
    if (timeZone === "Asia/Tokyo") return "JP";
    if (timeZone === "Asia/Seoul") return "KR";
    if (["Asia/Shanghai", "Asia/Chongqing", "Asia/Urumqi", "Asia/Hong_Kong"].includes(timeZone)) return "CN";
    if (timeZone === "Asia/Jakarta" || timeZone === "Asia/Makassar" || timeZone === "Asia/Jayapura") return "ID";
    if (timeZone === "Asia/Bangkok") return "TH";
    if (timeZone === "Asia/Riyadh") return "SA";
    if (timeZone === "Asia/Dubai") return "AE";
    if (timeZone === "Asia/Karachi") return "PK";
    if (timeZone === "Asia/Dhaka") return "BD";
    if (timeZone === "Europe/Paris") return "FR";
    if (["Europe/Berlin", "Europe/Vienna"].includes(timeZone)) return "DE";
    if (timeZone === "Europe/Madrid") return "ES";
    if (timeZone === "Europe/Rome") return "IT";
    if (timeZone === "Europe/Moscow") return "RU";
    if (timeZone === "Europe/London") return "GB";
    if (timeZone.startsWith("Australia/")) return "AU";
    if (["America/Toronto", "America/Vancouver", "America/Winnipeg", "America/Edmonton", "America/Halifax"].includes(timeZone)) return "CA";
    if (timeZone === "America/Mexico_City" || timeZone.startsWith("America/Cancun")) return "MX";
    if (["America/Sao_Paulo", "America/Fortaleza", "America/Recife"].includes(timeZone)) return "BR";
    if (timeZone.startsWith("America/")) return "US";
    return "";
  })();
  const localeCountry = browserLocales.map((locale) => {
    const match = String(locale).match(/[-_]([A-Za-z]{2})(?:[-_]|$)/);
    return match ? match[1].toUpperCase() : "";
  }).find((country) => Boolean(NEXAPATCH_GREETING_PROFILES[country])) || "";
  let country = timezoneCountry || localeCountry || "US";
  if (country === "CA" && primaryLanguage === "fr") country = "FR";
  const profile = NEXAPATCH_GREETING_PROFILES[country] || NEXAPATCH_GREETING_PROFILES.US;
  // NEXAPATCH_SIMPLE_EMOJI_GREETING_V5_1_CHINA_BOW
  const gestureKind = profile.namaste ? "namaste" : ["JP", "KR", "CN"].includes(country) ? "bow" : "wave";

  const uiLanguage = (typeof document !== "undefined" ? document.documentElement.lang : "en").toLowerCase();
  const translatedWelcome = String(translations["Welcome to NexaPatch"] || "");
  const translatedExit = String(translations["Exit workspace"] || "");
  const isHindi = uiLanguage === "hi" || uiLanguage.startsWith("hi-") || /[\u0900-\u097f]/.test(translatedWelcome + translatedExit);
  const hindiFallback = {
    "Welcome to NexaPatch": "NexaPatch में आपका स्वागत है", "Local time": "स्थानीय समय", "Exit workspace": "NexaPatch से बाहर जाएँ",
    "Are you sure you want to exit NexaPatch?": "क्या आप वाकई NexaPatch से बाहर जाना चाहते हैं?", "Your current run history will remain saved.": "आपके मौजूदा रन का इतिहास सुरक्षित रहेगा।",
    "Stay here": "यहीं रहें", "Yes, exit": "हाँ, बाहर जाएँ", "Goodbye!": "फिर मिलेंगे!", "NexaPatch is ready to close.": "NexaPatch अब बंद करने के लिए तैयार है।",
    "You can close this browser tab manually when you are ready.": "तैयार होने पर आप इस ब्राउज़र टैब को स्वयं बंद कर सकते हैं।", "Return to workspace": "वर्कस्पेस पर वापस जाएँ", "Namaste": "नमस्ते",
  };
  const t = (key) => {
    const translated = translations[key];
    if (translated && translated !== key) return translated;
    if (isHindi && hindiFallback[key]) return hindiFallback[key];
    return (profile.ui && profile.ui[key]) || key;
  };

  const hour = clockNow.getHours();
  const period = hour < 12 ? "morning" : hour < 17 ? "afternoon" : "evening";
  const periodGreeting = profile.namaste
    ? (isHindi ? profile[period][0] : profile[period][1])
    : (profile[period]?.[0] || "Hello");
  const greetingText = profile.namaste ? (isHindi ? "नमस्ते" : "Namaste") : "";
  let formattedTime = "";
  try {
    formattedTime = new Intl.DateTimeFormat(primaryLocale, { hour: "numeric", minute: "2-digit" }).format(clockNow);
  } catch { formattedTime = clockNow.toLocaleTimeString(); }

  return (
    <>
      {greetingVisible && (
        <div className={`nx-greeting-intro ${profile.namaste ? "nx-greeting-intro-india" : ""}`} role="status" aria-live="polite">
          <NexaPatchGreetingGesture kind={gestureKind} icon={profile.icon} />
          <p className="nx-intro-period">{periodGreeting}</p>
          {profile.namaste && <p className="nx-intro-namaste">{greetingText}</p>}
        </div>
      )}

      <section className="nx-welcome-strip" aria-label={t("Welcome to NexaPatch")}>
        <div className="nx-welcome-copy">
          <div className="nx-welcome-text">
            <p className="nx-welcome-greeting">{profile.name} · {t("Local time")}: {formattedTime}</p>
            <h2>{t("Welcome to NexaPatch")}</h2>
          </div>
        </div>
        <button className="nx-exit-trigger" type="button" onClick={() => setExitView("confirm")}>{t("Exit workspace")}</button>
      </section>

      {exitView === "confirm" && (
        <div className="nx-exit-overlay" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setExitView("welcome");
        }}>
          <section className="nx-exit-dialog" role="dialog" aria-modal="true" aria-labelledby="nx-exit-title">
            <div className="nx-exit-symbol" aria-hidden="true">↗</div>
            <h2 id="nx-exit-title">{t("Are you sure you want to exit NexaPatch?")}</h2>
            <p>{t("Your current run history will remain saved.")}</p>
            <div className="nx-exit-actions">
              <button type="button" className="nx-exit-secondary" onClick={() => setExitView("welcome")}>{t("Stay here")}</button>
              <button type="button" className="nx-exit-primary" onClick={() => setExitView("goodbye")}>{t("Yes, exit")}</button>
            </div>
          </section>
        </div>
      )}

      {exitView === "goodbye" && (
        <div className="nx-goodbye-screen" role="dialog" aria-modal="true" aria-labelledby="nx-goodbye-title">
          <NexaPatchGreetingGesture kind={gestureKind} icon={profile.icon} goodbye />
          <p className="nx-welcome-greeting">{isHindi && profile.namaste ? "फिर मिलेंगे!" : profile.farewell[0]}</p>
          <h1 id="nx-goodbye-title">{t("NexaPatch is ready to close.")}</h1>
          <p>{t("You can close this browser tab manually when you are ready.")}</p>
          <button type="button" className="nx-exit-primary" onClick={() => setExitView("welcome")}>{t("Return to workspace")}</button>
        </div>
      )}
    </>
  );
}

export default function App() {
  const [health, setHealth] = useState(null);
  // NEXAPATCH_SESSION_TOKEN_UI_V1
  // Keep credentials in React memory only, never in browser storage.
  const [apiToken, setApiToken] = useState('');
  const [apiTokenInput, setApiTokenInput] = useState('');
  const [authMessage, setAuthMessage] = useState('');
  const [task, setTask] = useState(DEFAULT_TASK);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);
  const [showAllFiles, setShowAllFiles] = useState(false);

  const [languageMode, setLanguageMode] = useState('auto');
  const [responseLanguage, setResponseLanguage] = useState('');
  const [customLanguage, setCustomLanguage] = useState('');
  const [autoUiLanguage] = useState(() => nexapatchBrowserLanguageName());
  const [translations, setTranslations] = useState({});
  const [translationLoading, setTranslationLoading] = useState(false);

  useEffect(() => {
    try {
      window.localStorage.setItem('nexapatch.languageMode', 'auto');
      window.localStorage.removeItem('nexapatch.responseLanguage');
      window.localStorage.removeItem('nexapatch.customLanguage');
    } catch {
      // Storage is optional; language selection still works for this session.
    }
  }, [languageMode, responseLanguage, customLanguage]);

  useEffect(() => {
    let cancelled = false;
    const targetLanguage = languageMode === 'manual'
      ? responseLanguage.trim()
      : autoUiLanguage;

    if (!targetLanguage) {
      setTranslations({});
      setTranslationLoading(false);
      document.documentElement.dir = 'ltr';
      document.documentElement.lang = 'en';
      return undefined;
    }

    const normalizedLanguage = targetLanguage.toLowerCase().replaceAll('_', '-');
    const baseLanguage = normalizedLanguage.split(/[-\s]/)[0];
    const targetCode = NEXAPATCH_HTML_LANG_CODES[targetLanguage] || baseLanguage;
    if (baseLanguage === 'en' || normalizedLanguage === 'english') {
      setTranslations({});
      setTranslationLoading(false);
      document.documentElement.dir = 'ltr';
      document.documentElement.lang = 'en';
      return undefined;
    }

    const controller = new AbortController();
    const labels = Object.fromEntries(NEXAPATCH_UI_LABELS.map((label) => [label, label]));
    const cacheKey = `nexapatch.uiTranslations.v3:${normalizedLanguage}`;

    if (baseLanguage === 'hi' || normalizedLanguage === 'hindi') {
      const bundledHindi = Object.fromEntries(
        NEXAPATCH_UI_LABELS.map((label) => [
          label,
          NEXAPATCH_LOCAL_HI_TRANSLATIONS[label] || label,
        ])
      );
      setTranslations(bundledHindi);
      setTranslationLoading(false);
      document.documentElement.dir = 'ltr';
      document.documentElement.lang = 'hi';
      try {
        window.localStorage.setItem(cacheKey, JSON.stringify(bundledHindi));
      } catch {
        // Built-in translations work even when local storage is unavailable.
      }
      return undefined;
    }

    setTranslationLoading(true);

    (async () => {
      try {
        try {
          const cachedRaw = window.localStorage.getItem(cacheKey);
          if (cachedRaw) {
            const cached = JSON.parse(cachedRaw);
            if (cached && typeof cached === 'object' && Object.keys(cached).length > 10) {
              if (cancelled) return;
              setTranslations(cached);
              document.documentElement.dir = ['ar', 'he', 'fa', 'ur', 'ps', 'sd', 'ug', 'yi'].includes(baseLanguage) ? 'rtl' : 'ltr';
              document.documentElement.lang = targetCode;
              return;
            }
          }
        } catch {
          // Invalid or unavailable cache should only cause a network fallback.
        }

        const response = await fetch(`${API_BASE}/api/localize-ui`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json; charset=utf-8',
            ...(apiToken ? { Authorization: `Bearer ${apiToken}` } : {}),
          },
          body: JSON.stringify({ target_language: targetLanguage, labels }),
          signal: controller.signal,
        });
        if (!response.ok) throw new Error(`Localization failed (${response.status})`);
        const localized = await response.json();
        if (cancelled) return;
        const localizedLabels = localized.labels && typeof localized.labels === 'object'
          ? localized.labels
          : {};
        setTranslations(localizedLabels);
        document.documentElement.dir = localized.direction === 'rtl' ? 'rtl' : 'ltr';
        document.documentElement.lang = targetCode;
        if (!localized.translation_warning && Object.keys(localizedLabels).length > 10) {
          try {
            window.localStorage.setItem(cacheKey, JSON.stringify(localizedLabels));
          } catch {
            // Local storage is optional; current-page translations still work.
          }
        }
      } catch (error) {
        if (!cancelled && error.name !== 'AbortError') {
          setTranslations({});
          document.documentElement.dir = 'ltr';
          document.documentElement.lang = 'en';
        }
      } finally {
        if (!cancelled) setTranslationLoading(false);
      }
    })();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [languageMode, responseLanguage, autoUiLanguage, apiToken]);
  // NEXAPATCH_UI_LANGUAGE_INDEPENDENT_V1
  // Do not switch the whole interface based on task text. The UI language stays based on the browser locale
  // (or an explicit UI language choice); runAgent detects the task language separately for the AI response.


  const loadHealth = useCallback(async () => {
    try {
      const response = await fetchJson(`${API_BASE}/api/health`);
      setHealth(response);
    } catch (err) {
      setHealth({ status: 'offline', error: err.message });
    }
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const response = await fetchJson(`${API_BASE}/api/runs?limit=6`, {
        headers: apiToken ? { Authorization: `Bearer ${apiToken}` } : {},
      });
      setHistory(response.runs || []);
      if (apiToken) setAuthMessage('Access token accepted.');
    } catch (err) {
      setHistory([]);
      if (apiToken) {
        setAuthMessage(err.message || 'Backend access was denied.');
      }
    }
  }, [apiToken]);

  useEffect(() => { loadHealth(); loadHistory(); }, [loadHealth, loadHistory]);

  const runAgent = async (event) => {
    event.preventDefault();
    if (task.trim().length < 5 || loading) return;
    if (health?.auth_required && !apiToken) {
      setError('Enter the backend access token above before running analyses.');
      return;
    }
    setLoading(true);
    setError('');
    setResult(null);
    setShowAllFiles(false);
    try {
      const response = await fetchJson(`${API_BASE}/api/run-agent`, {
        method: 'POST',
        headers: apiToken ? { Authorization: `Bearer ${apiToken}` } : {},
        body: JSON.stringify({ request_text: task.trim(), detected_language: nexapatchDetectLanguageFromText(task.trim()) || nexapatchBrowserLanguageName(), language_mode: languageMode, response_language: languageMode === 'manual' ? (responseLanguage.trim() || 'English') : null }),
      });
      setResult(response);
      await Promise.all([loadHealth(), loadHistory()]);
    } catch (err) {
      setError(err.message || 'The request failed. Confirm the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const visibleFiles = useMemo(() => {
    const files = result?.discovered_files || [];
    return showAllFiles ? files : files.slice(0, 12);
  }, [result, showAllFiles]);

  const apiOnline = health?.status === 'ok';
  const aiReady = Boolean(health?.ai_configured);
  const resultTone = result?.status === 'planned' ? 'success' : result?.status === 'scan_only' ? 'warning' : 'danger';
  const resultLabel = result?.status === 'planned' ? 'Plan generated' : result?.status === 'scan_only' ? 'Scan only · API key needed' : 'AI planning issue';

  return (
    <NexaPatchLocalizedTree translations={translations}>
<div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#top" aria-label="NexaPatch home">
          <span className="brand-mark"><Workflow size={22} /></span>
          <span className="brand-copy"><strong>Nexa<span>Patch</span></strong><small>ENGINEERING WORKSPACE</small></span>
        </a>
        <div className="workspace-switcher">
          <div className="workspace-avatar">CV</div>
          <div className="workspace-label"><strong>Local workspace</strong><span>Personal environment</span></div>
          <span className={`online-indicator ${apiOnline ? 'is-online' : ''}`} title={apiOnline ? 'API connected' : 'API offline'} />
        </div>
        <p className="nav-label">WORKSPACE</p>
        <nav className="main-nav" aria-label="Main navigation">
          <a className="nav-item active" href="#agent"><Command size={17} /><span>Agent console</span><span className="nav-shortcut">⌘ 1</span></a>
          <a className="nav-item" href="#repository"><FolderGit2 size={17} /><span>Repository</span></a>
          <a className="nav-item" href="#activity"><Activity size={17} /><span>Run history</span></a>
        </nav>
        <div className="sidebar-spacer" />
        <div className="safety-card">
          <div className="safety-icon"><ShieldCheck size={17} /></div>
          <strong>Read-only mode</strong>
          <p>Phase 1 can inspect and plan. It cannot edit or execute your project code.</p>
          <span className="safety-tag"><span /> Workspace protected</span>
        </div>
        <div className="sidebar-footer"><span className="avatar">BU</span><div><strong>Developer mode</strong><span>Local build · v0.2.0</span></div><span className="footer-dots">•••</span></div>
      </aside>

      <main className="main-content" id="top">
        <header className="topbar">
          <div className="breadcrumbs"><span>Workspace</span><span className="crumb-separator">/</span><strong>Agent console</strong></div>
          <div className="topbar-actions"><span className="environment-chip"><span /> LOCAL ENVIRONMENT</span><button className="icon-button" onClick={() => { loadHealth(); loadHistory(); }} aria-label="Refresh status" title="Refresh status"><RefreshCw size={16} /></button></div>
        </header>

        <div className="page-container">
          {health?.auth_required && (
            <section
              aria-label="Backend access"
              style={{
                marginBottom: 18,
                padding: 14,
                border: '1px solid #d6deea',
                borderRadius: 12,
                background: '#ffffff',
                color: '#182230',
              }}
            >
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  const candidate = apiTokenInput.trim();
                  if (!candidate) {
                    setAuthMessage('Paste the backend access token first.');
                    return;
                  }
                  setApiToken(candidate);
                  setApiTokenInput('');
                  setAuthMessage('Checking access...');
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  flexWrap: 'wrap',
                }}
              >
                <label htmlFor="nexapatch-api-token"
                  style={{ fontSize: 13, fontWeight: 600 }}>
                  Backend access token
                </label>
                <input
                  id="nexapatch-api-token"
                  type="password"
                  value={apiTokenInput}
                  onChange={(event) => setApiTokenInput(event.target.value)}
                  autoComplete="off"
                  spellCheck={false}
                  placeholder="Paste deployment token"
                  style={{
                    flex: '1 1 220px',
                    minWidth: 0,
                    maxWidth: '100%',
                    padding: '10px 12px',
                    border: '1px solid #c7d0dc',
                    borderRadius: 8,
                    color: '#182230',
                    background: '#ffffff',
                  }}
                />
                <button type="submit" disabled={!apiTokenInput.trim()}
                  style={{
                    padding: '10px 14px',
                    border: 0,
                    borderRadius: 8,
                    background: '#182230',
                    color: '#ffffff',
                    cursor: 'pointer',
                  }}>
                  Connect
                </button>
                {apiToken && (
                  <button
                    type="button"
                    onClick={() => {
                      setApiToken('');
                      setApiTokenInput('');
                      setHistory([]);
                      setAuthMessage('Access token cleared from this tab.');
                    }}
                    style={{
                      padding: '10px 14px',
                      border: '1px solid #c7d0dc',
                      borderRadius: 8,
                      background: '#ffffff',
                      color: '#182230',
                      cursor: 'pointer',
                    }}>
                    Disconnect
                  </button>
                )}
              </form>
              <p role="status" style={{ margin: '10px 0 0', fontSize: 13 }}>
                {authMessage || 'Enter your backend access token to use protected API features.'}
              </p>
              <p style={{ margin: '6px 0 0', color: '#526174', fontSize: 12 }}>
                The token stays in page memory and is not saved to browser storage. Reloading the page clears it.
              </p>
            </section>
          )}
          <NexaPatchWelcomeAndExit translations={translations} />
            <section className="welcome-row">
            <div><div className="eyebrow"><Sparkles size={14} /> AI SOFTWARE ENGINEERING</div><h1>Good work starts with <span>understanding.</span></h1><p className="page-subtitle">Inspect a real codebase, map its architecture, and turn your goal into an evidence-based implementation plan.</p></div>
            <div className="hero-orbit" aria-hidden="true"><div className="orbit-ring orbit-ring-one" /><div className="orbit-ring orbit-ring-two" /><div className="orbit-core"><Cpu size={27} /></div><span className="orbit-node orbit-node-one" /><span className="orbit-node orbit-node-two" /><span className="orbit-node orbit-node-three" /></div>
          </section>

          <section className="metric-grid" aria-label="System status">
            <div className="metric-card"><div className="metric-top"><span className="metric-icon violet"><Workflow size={17} /></span><StatusPill tone={apiOnline ? 'success' : 'danger'}>{apiOnline ? 'Connected' : 'Offline'}</StatusPill></div><span className="metric-label">Agent API</span><strong>{apiOnline ? 'Operational' : 'Unavailable'}</strong><small>{apiOnline ? 'FastAPI · Port 8001' : 'Start the backend server'}</small></div>
            <div className="metric-card"><div className="metric-top"><span className="metric-icon blue"><Sparkles size={17} /></span><StatusPill tone={aiReady ? 'success' : 'warning'}>{aiReady ? 'Configured' : 'Setup needed'}</StatusPill></div><span className="metric-label">AI provider</span><strong>{aiReady ? 'Groq API' : 'Not connected'}</strong><small>{health?.model || 'Configure GROQ_MODEL'}</small></div>
            <div className="metric-card"><div className="metric-top"><span className="metric-icon green"><ShieldCheck size={17} /></span><StatusPill tone="success">Enforced</StatusPill></div><span className="metric-label">Execution policy</span><strong>Read-only</strong><small>Zero code modifications in Phase 1</small></div>
            <div className="metric-card"><div className="metric-top"><span className="metric-icon amber"><Clock3 size={17} /></span><span className="metric-overline">PERSISTENT</span></div><span className="metric-label">Run history</span><strong>{history.length} recent {history.length === 1 ? 'run' : 'runs'}</strong><small>Stored locally in SQLite</small></div>
          </section>

          {!apiOnline && <div className="notice notice-danger"><CircleAlert size={18} /><div><strong>Backend connection unavailable</strong><p>Run the FastAPI server on <code>127.0.0.1:8001</code>, then refresh this page.</p></div></div>}
          {apiOnline && !aiReady && <div className="notice notice-warning"><CircleAlert size={18} /><div><strong>Repository scan works; AI planning needs a key</strong><p>Add your Groq API key to the local <code>.env</code> file and restart the backend. Never place the key in frontend code.</p></div></div>}

          <div className="workspace-grid">
            <section className="panel task-panel" id="agent">
              <SectionTitle icon={Command} title="New agent task" trailing={<span className="step-chip">STEP 01 <ArrowRight size={12} /> 02</span>} />
              <form onSubmit={runAgent}>
                <label className="field-label" htmlFor="task-input">What should NexaPatch investigate?</label>
                <textarea id="task-input" value={task} onChange={(event) => setTask(event.target.value)} maxLength={6000} placeholder="Example: Trace the login flow and identify the most important security gaps..." rows={7} disabled={loading}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                      event.preventDefault();
                      if (task.trim().length >= 5 && !loading && apiOnline) {
                        event.currentTarget.form?.requestSubmit();
                      }
                    }
                  }}
                />
                <div className="prompt-meta"><span>Be specific for more relevant file discovery.</span><span>{task.length.toLocaleString()} / 6,000</span></div>
                <div className="task-context"><div className="context-icon"><FolderGit2 size={16} /></div><div className="context-copy"><strong>{health?.workspace_name || 'Configured repository'}</strong><span>{health?.workspace_configured ? 'Repository path validated by backend' : 'Waiting for backend configuration'}</span></div><span className="context-badge"><Check size={12} /> Local</span></div>
                <button className="primary-button" type="submit" disabled={loading || !apiOnline || task.trim().length < 5}>{loading ? <><LoaderCircle className="spin" size={17} /> Inspecting repository...</> : <><Play size={16} fill="currentColor" /> Run repository analysis <ArrowRight size={16} /></>}</button>
                <p className="privacy-note"><ShieldCheck size={13} /> Selected source text is sent to the configured AI provider; review sensitive repositories first.</p>
              </form>
              {error && <div className="inline-error"><CircleAlert size={16} /><span>{error}</span></div>}
            </section>

            <section className="panel result-panel" id="repository">
              <SectionTitle icon={Terminal} title="Execution trace" trailing={result ? <StatusPill tone={resultTone}>{resultLabel}</StatusPill> : <span className="idle-label"><span /> {translations['READY'] || 'READY'}</span>} />
              {!result && !loading && <div className="empty-state"><div className="empty-illustration"><div className="empty-illustration-ring" /><Terminal size={29} /><span className="empty-spark spark-one" /><span className="empty-spark spark-two" /></div><h3>Your next task starts here</h3><p>Submit a task to inspect the configured repository. The trace will show what was actually scanned and whether AI planning ran.</p><div className="empty-steps"><span><i>01</i> Inspect files</span><ArrowRight size={13} /><span><i>02</i> Plan changes</span><ArrowRight size={13} /><span><i>03</i> Report evidence</span></div></div>}
              {loading && <div className="loading-state"><div className="loader-graphic"><LoaderCircle size={30} className="spin" /></div><h3>Inspecting your codebase</h3><p>Finding relevant source files and preparing safe context for analysis.</p><div className="loading-line"><span /></div><span className="loading-caption">This can take a few seconds...</span></div>}
              {result && <div className="result-content">
                <div className={`result-banner ${resultTone}`}><div className="result-banner-icon">{result.status === 'planned' ? <Check size={18} /> : <CircleAlert size={18} />}</div><div><strong>{result.status === 'planned' ? 'AI-generated plan is ready' : result.status === 'scan_only' ? 'Repository scan completed' : 'AI planning needs attention'}</strong><p>{result.repository_summary}</p></div></div>
                <div className="trace-list"><div className="trace-heading"><span>RUN TIMELINE</span><span>{result.steps?.length || 0} events</span></div>{(result.steps || []).map((step, index) => <div className="trace-item" key={`${step}-${index}`}><span className={`trace-dot ${index === (result.steps?.length || 1) - 1 ? 'trace-dot-last' : ''}`} /><span>{step}</span><Check size={14} /></div>)}</div>
                <div className="mini-stats"><div><span>Files discovered</span><strong>{result.total_files_found}</strong></div><div><span>Files in context</span><strong>{result.files_in_context?.length || 0}</strong></div><div><span>Files changed</span><strong>0</strong></div></div>
                <div className="files-section"><div className="subsection-head"><span><FileCode2 size={15} /> Discovered files</span><span>{result.inventory_truncated ? 'First 600' : `${result.discovered_files?.length || 0} total`}</span></div><div className="file-list">{visibleFiles.map((file) => <div className="file-row" key={file}><FileCode2 size={14} /><span>{file}</span>{result.files_in_context?.includes(file) && <span className="context-label">IN CONTEXT</span>}</div>)}</div>{(result.discovered_files?.length || 0) > 12 && <button className="text-button" onClick={() => setShowAllFiles((current) => !current)} type="button">{showAllFiles ? 'Show fewer files' : `Show all ${result.discovered_files.length} files`}</button>}</div>
                <div className="plan-section"><div className="subsection-head"><span><Zap size={15} /> Analysis & implementation plan</span><span>{result.ai_used ? result.model : 'AI not used'}</span></div><NexaPatchAgentPlanMarkdown content={result.execution_plan} /></div>
                <div className="read-only-footer"><ShieldCheck size={15} /><span>Verified policy: read-only inspection · 0 modifications · no project code executed</span></div>
              </div>}
            </section>
          </div>

          <section className="panel history-panel" id="activity">
            <SectionTitle icon={Activity} title={translations['Recent runs'] || 'Recent runs'} trailing={<button className="quiet-button" onClick={loadHistory} type="button"><RefreshCw size={13} /> {translations['Refresh'] || 'Refresh'}</button>} />
            {history.length === 0 ? <div className="history-empty">Your completed analyses will appear here after the first run.</div> : <div className="history-table-wrap"><table className="history-table"><thead><tr><th>TASK</th><th>WORKSPACE</th><th>STATUS</th><th>MODEL</th><th>CREATED</th></tr></thead><tbody>{history.map((run) => <tr key={run.id}><td><span className="run-id">#{run.id}</span><span className="run-request">{run.user_request}</span></td><td>{run.workspace_name}</td><td><StatusPill tone={run.status === 'planned' ? 'success' : run.status === 'scan_only' ? 'warning' : 'danger'}>{run.status.replaceAll('_', ' ')}</StatusPill></td><td>{run.model || '—'}</td><td>{new Date(run.created_at).toLocaleString()}</td></tr>)}</tbody></table></div>}
          </section>
          <footer className="page-footer"><span>NexaPatch <span className="footer-dot">·</span> Phase 1 foundation</span><span className="developer-credit">Developed by Bhanuday Urmaliya — Full Stack Developer</span></footer>
        </div>
      </main>
    </div>
    </NexaPatchLocalizedTree>
  );
}
