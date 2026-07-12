// lib/policy-config.js - Configuration configurations for security topics, control frameworks, deprecated tech, and scope checking

const deprecated = ["des", "sha-1", "ssl", "tls 1.0", "wep", "windows server 2012"];

const topics = {
  'password': ['password', 'credential', 'passphrase', 'mfa', 'authentication', 'login'],
  'encryption': ['encryption', 'encrypt', 'aes', 'rsa', 'tls', 'ssl', 'cipher', 'cryptographic'],
  'access_control': ['role', 'rbac', 'permission', 'authorization', 'privilege', 'least privilege'],
  'network_security': ['firewall', 'vpn', 'ids', 'ips', 'network', 'segmentation'],
  'backup_recovery': ['backup', 'restore', 'recovery', 'disaster recovery'],
  'incident_response': ['incident', 'breach', 'escalation', 'containment'],
  'data_retention': ['retention', 'retain', 'delete', 'deletion', 'dispose']
};

function controlsFor(topic) {
  const mapping = {
    'password': ['ISO 27001 A.9.4.3', 'NIST SP 800-63B'],
    'encryption': ['ISO 27001 A.10.1.1', 'NIST SP 800-53 SC-13'],
    'access_control': ['ISO 27001 A.9.1.1', 'ISO 27001 A.9.2.1'],
    'network_security': ['ISO 27001 A.13.1.1', 'NIST SP 800-53 SC-7'],
    'backup_recovery': ['ISO 27001 A.12.3.1', 'NIST SP 800-53 CP-9'],
    'incident_response': ['ISO 27001 A.16.1.1', 'NIST SP 800-53 IR-4'],
    'data_retention': ['ISO 27001 A.8.2.3', 'GDPR Article 5(1)(e)']
  };
  return mapping[topic] || ['ISO 27001 General'];
}

function scopesOverlap(scopeA, scopeB) {
  if (!scopeA || !scopeB) return true;
  const a = scopeA.toLowerCase().trim();
  const b = scopeB.toLowerCase().trim();
  
  if (a === b) return true;
  
  const globals = ['general', 'all', 'all employees', 'everyone'];
  if (globals.includes(a) || globals.includes(b)) return true;
  
  // Check partial intersections
  if (a.includes(b) || b.includes(a)) return true;
  
  return false;
}

module.exports = {
  deprecated,
  topics,
  controlsFor,
  scopesOverlap
};
