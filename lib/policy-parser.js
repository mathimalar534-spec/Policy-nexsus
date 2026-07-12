// lib/policy-parser.js - Policy document parsing helper

const { topics } = require('./policy-config');

const domains = {
  'Password Management': ['password', 'credential', 'passphrase', 'mfa', 'authentication', 'login'],
  'Encryption': ['encryption', 'encrypt', 'aes', 'rsa', 'tls', 'ssl', 'cipher', 'cryptographic'],
  'Access Control': ['role', 'rbac', 'permission', 'authorization', 'privilege', 'least privilege'],
  'Network Security': ['firewall', 'vpn', 'ids', 'ips', 'network', 'segmentation'],
  'Backup & Recovery': ['backup', 'restore', 'recovery', 'disaster recovery'],
  'Incident Response': ['incident', 'breach', 'escalation', 'containment'],
  'Data Retention': ['retention', 'retain', 'delete', 'deletion', 'dispose']
};

function classifyDomains(text) {
  const low = text.toLowerCase();
  const scored = Object.entries(domains)
    .map(([name, words]) => [name, words.reduce((n, w) => n + (low.includes(w) ? 1 : 0), 0)])
    .filter(([, score]) => score);
  
  const top = Math.max(0, ...scored.map(([, score]) => score));
  return scored
    .filter(([, score]) => score >= Math.max(1, top - 1))
    .map(([name]) => name);
}

function parseDocument(doc, start) {
  let title = doc.name.replace(/\.(md|txt)$/i, '');
  let reviewed = '';
  let department = 'Security Operations';
  let version = '1.0';
  let text = doc.text || '';
  
  // Parse frontmatter
  const front = text.match(/^---\s*\n([\s\S]*?)\n---\s*\n?/);
  if (front) {
    front[1].split('\n').forEach(line => {
      const parts = line.split(':');
      if (parts.length < 2) return;
      const k = parts[0].trim();
      const v = parts.slice(1).join(':').trim();
      if (k === 'title') title = v;
      if (k === 'last_reviewed') reviewed = v;
      if (k === 'department') department = v;
      if (k === 'version') version = v;
    });
    text = text.slice(front[0].length);
  }
  
  // Parse review date patterns
  if (!reviewed) {
    const match = text.match(/last\s+reviewed\s*:\s*(\d{4}(?:-\d{2}-\d{2})?)/i);
    if (match) {
      reviewed = match[1].length === 4 ? `${match[1]}-01-01` : match[1];
    }
  }
  
  // Parse header
  const header = text.match(/^#\s+(.+)$/m);
  if (header) title = header[1].trim();
  
  // Parse obligation statements
  const obligations = text.split(/(?<=[.!?])\s+|\n/)
    .filter(s => /\b(must not|shall not|may not|prohibited|must|shall|required|should|recommended|expected|optional)\b/i.test(s))
    .map((sentence, i) => {
      const low = sentence.toLowerCase();
      const topic = Object.entries(topics).find(([, words]) => words.some(w => low.includes(w)))?.[0] || 'general';
      const polarity = /\b(must not|shall not|may not|prohibited|do not|never)\b/.test(low) ? 'negative' : 'positive';
      const strength = /\b(must|shall|required|must not|shall not|may not|prohibited|mandatory)\b/.test(low) ? 'mandatory' : 'advisory';
      
      let action = /rotat|expire/.test(low) ? 'rotate' : Object.entries({
        retain: 'retain',
        delete: 'delete',
        encrypt: 'encrypt',
        reuse: 'reuse',
        report: 'report',
        use: 'use',
        enforce: 'enforce',
        bypass: 'bypass',
        log: 'log',
        backup: 'backup'
      }).find(([k]) => low.includes(k))?.[1] || topic;
      
      if (topic === 'password' && /\b(?:character|characters|letter|letters|length)\b/.test(low)) action = 'length';
      if (topic === 'mfa') action = 'mfa';
      if (topic === 'encryption' && /aes/.test(low)) action = 'algorithm';
      if (topic === 'encryption' && /tls|ssl/.test(low)) action = 'transport';
      if (topic === 'encryption' && /key/.test(low) && /rotat/.test(low)) action = 'key_rotation';
      if (topic === 'incident_response' && /report/.test(low)) action = 'report';
      
      const parameter = (low.match(/\b\d+\s*(?:character|characters|letter|letters|day|days|year|years|month|months|hour|hours)\b|\b(?:aes[- ]?\d+|tls\s*\d(?:\.\d)?|sha-?1)\b/g) || []).join(' ');
      const scope = ['all employees', 'cloud', 'personal data', 'developers', 'systems', 'databases'].find(x => low.includes(x)) || (/(?:^|\W)eu(?:$|\W)/.test(low) ? 'eu' : 'general');
      const section = sentence.match(/(?:section|§)\s*(\d+(?:\.\d+)*)/i)?.[1] || `Clause ${i + 1}`;
      
      return {
        id: `O${String(start + i + 1).padStart(3, '0')}`,
        policy: title,
        section,
        sentence: sentence.trim(),
        topic,
        strength,
        polarity,
        action,
        parameter,
        scope
      };
    });
    
  return {
    title,
    reviewed,
    department,
    version,
    text,
    domains: classifyDomains(text),
    obligations
  };
}

module.exports = {
  parseDocument
};
