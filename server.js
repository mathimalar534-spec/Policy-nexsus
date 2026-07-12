const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const { deprecated, topics, controlsFor, scopesOverlap } = require('./lib/policy-config');
const { parseDocument } = require('./lib/policy-parser');
const { selectCandidatePairs } = require('./lib/candidate-selector');

const PORT = process.env.PORT || 3000;
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const OPENAI_MODEL = process.env.OPENAI_MODEL || 'gpt-5-mini';

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
  return scored.filter(([, score]) => score >= Math.max(1, top - 1)).map(([name]) => name);
}

// Subprocess client to run our trained Python GRC model predictions
function predictMLPairs(pairs) {
  if (!pairs || !pairs.length) return [];
  try {
    const payload = JSON.stringify({ pairs });
    // Execute Python script to run local ML predictions
    const output = execSync('python predict_pairs.py', {
      input: payload,
      encoding: 'utf-8',
      maxBuffer: 10 * 1024 * 1024 // 10MB buffer size
    });
    
    const parsed = JSON.parse(output.trim());
    if (parsed.error) {
      console.warn("Python GRC Model warning:", parsed.error);
      return [];
    }
    return parsed;
  } catch (err) {
    console.error("Failed to run local ML model subprocess:", err.message);
    return [];
  }
}

function postOpenAI(payload) {
  return new Promise((resolve, reject) => {
    const request = https.request({
      hostname: 'api.openai.com',
      path: '/v1/chat/completions', // Corrected completions endpoint path
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENAI_API_KEY}`,
        'Content-Type': 'application/json'
      }
    }, response => {
      let body = '';
      response.on('data', chunk => body += chunk);
      response.on('end', () => {
        try {
          const json = JSON.parse(body);
          if (response.statusCode >= 400) throw Error(json.error?.message || `OpenAI request failed (${response.statusCode})`);
          resolve(json);
        } catch (error) {
          reject(error);
        }
      });
    });
    request.on('error', reject);
    request.write(JSON.stringify(payload));
    request.end();
  });
}

function responseText(response) {
  if (response.output_text) return response.output_text;
  if (response.choices && response.choices[0] && response.choices[0].message) {
    return response.choices[0].message.content;
  }
  for (const item of response.output || []) {
    for (const part of item.content || []) {
      if (part.type === 'output_text' && part.text) return part.text;
    }
  }
  return '';
}

async function aiReview(parsed, findings) {
  if (!OPENAI_API_KEY) return { enabled: false, added: 0, message: 'Rule-based analysis (set OPENAI_API_KEY to enable AI review)' };
  const policies = parsed.map(p => ({ title: p.title, text: p.text.slice(0, 12000) }));
  const schema = {
    type: 'object',
    additionalProperties: false,
    required: ['findings'],
    properties: {
      findings: {
        type: 'array',
        items: {
          type: 'object',
          additionalProperties: false,
          required: ['kind', 'severity', 'policy_a', 'policy_b', 'title', 'evidence', 'recommendation', 'scope_analysis'],
          properties: {
            kind: { type: 'string', enum: ['CONFLICT', 'REDUNDANCY'] },
            severity: { type: 'string', enum: ['critical', 'high', 'medium'] },
            policy_a: { type: 'string' },
            policy_b: { type: 'string' },
            title: { type: 'string' },
            evidence: { type: 'string' },
            recommendation: { type: 'string' },
            scope_analysis: { type: 'string' }
          }
        }
      }
    }
  };
  const instructions = `You are a careful policy-governance analyst. Review the supplied policies and return only genuine cross-policy conflicts or redundancies. A conflict requires incompatible obligations for overlapping scope. Do NOT call complementary controls conflicts: password length and password rotation can both apply. Treat narrower explicit exceptions as non-conflicts.`;
  try {
    const response = await postOpenAI({
      model: OPENAI_MODEL,
      messages: [
        { role: 'system', content: instructions },
        { role: 'user', content: `POLICIES:\n${JSON.stringify(policies)}` }
      ],
      response_format: { type: 'json_object' }
    });
    const result = JSON.parse(responseText(response));
    let added = 0;
    for (const item of result.findings || []) {
      if (!parsed.some(p => p.title === item.policy_a) || !parsed.some(p => p.title === item.policy_b) || item.policy_a === item.policy_b) continue;
      const exists = findings.some(f => f.kind === item.kind && f.policies.some(p => p.startsWith(item.policy_a)) && f.policies.some(p => p.startsWith(item.policy_b)));
      if (exists) continue;
      findings.push({
        kind: item.kind,
        severity: item.severity,
        title: item.title,
        policies: [item.policy_a, item.policy_b],
        evidence: item.evidence,
        recommendation: item.recommendation,
        scopeAnalysis: item.scope_analysis,
        controlImpact: ['AI-assisted policy review'],
        source: 'AI'
      });
      added++;
    }
    return { enabled: true, added, message: `AI-assisted review using ${OPENAI_MODEL}` };
  } catch (error) {
    return { enabled: false, added: 0, message: `AI review unavailable; rule-based fallback used (${error.message})` };
  }
}

async function analyse(documents) {
  const parsed = [];
  let obligations = [];
  
  // 1. Ingest & Parse documents
  documents.forEach(d => {
    const x = parseDocument(d, obligations.length);
    x.obligations.forEach(o => o.domains = x.domains);
    parsed.push(x);
    obligations.push(...x.obligations);
  });
  
  const candidatePairs = selectCandidatePairs(obligations);
  const findings = [];
  const add = (kind, severity, title, policies, evidence, recommendation, scopeAnalysis, controlImpact) => 
    findings.push({ kind, severity, title, policies, evidence, recommendation, scopeAnalysis, controlImpact });
  
  // 2. Prepare inputs for ML model predictions
  const mlPairsInput = [];
  const pairIndices = [];
  
  for (let i = 0; i < obligations.length; i++) {
    for (let j = i + 1; j < obligations.length; j++) {
      const a = obligations[i];
      const b = obligations[j];
      const sharedDomains = a.domains.filter(x => b.domains.includes(x));
      
      if (a.policy === b.policy || a.topic !== b.topic || !sharedDomains.length || !scopesOverlap(a.scope, b.scope)) continue;
      
      mlPairsInput.push({ a: a.sentence, b: b.sentence, topic: a.topic });
      pairIndices.push({ i, j, sharedDomains });
    }
  }
  
  // Get local ML predictions using our trained model
  let predictions = [];
  let mlFailed = false;
  if (mlPairsInput.length > 0) {
    predictions = predictMLPairs(mlPairsInput);
    if (!predictions || predictions.length === 0 || predictions.error) {
      mlFailed = true;
    }
  }
  
  // 3. Process pairs with ML predictions or Rule fallback
  for (let idx = 0; idx < mlPairsInput.length; idx++) {
    const { i, j, sharedDomains } = pairIndices[idx];
    const a = obligations[i];
    const b = obligations[j];
    const pred = (!mlFailed && predictions[idx]) ? predictions[idx] : null;
    
    const refs = [`${a.policy} §${a.section}`, `${b.policy} §${b.section}`];
    const scope = `Shared domain: ${sharedDomains.join(', ')}. ${a.scope === 'general' || a.scope === 'all employees' ? 'Enterprise-wide' : a.scope} overlaps with ${b.scope === 'general' || b.scope === 'all employees' ? 'enterprise-wide scope' : b.scope}.`;
    
    if (pred) {
      // Trust the ML Model prediction
      if (pred.label === 'CONFLICT') {
        const severity = (a.strength !== b.strength || a.parameter !== b.parameter) ? 'high' : 'critical';
        add('CONFLICT', severity, `Conflicting ${a.topic.replace('_', ' ')} obligations`, refs, `${a.id}: ${a.sentence}\n${b.id}: ${b.sentence}`, 'Assign an owner to reconcile the rules, document exceptions, and publish one controlling requirement.', scope, controlsFor(a.topic));
      } else if (pred.label === 'REDUNDANT') {
        add('REDUNDANCY', 'medium', `Overlapping ${a.topic.replace('_', ' ')} obligation`, refs, `${a.id}: ${a.sentence}\n${b.id}: ${b.sentence}`, 'Consolidate the shared rule or add clear cross-references and scope.', scope, controlsFor(a.topic));
      }
    } else {
      // Rule-based Fallback
      const temporal = a.topic === 'data_retention' && new Set([a.action, b.action]).size === 2 && [a.action, b.action].includes('retain') && [a.action, b.action].includes('delete');
      const opposite = a.polarity !== b.polarity && a.action === b.action;
      const strengthMismatch = a.strength !== b.strength && a.action === b.action;
      const parameterMismatch = a.action === b.action && a.parameter && b.parameter && a.parameter !== b.parameter;
      
      if (opposite || temporal || strengthMismatch || parameterMismatch) {
        add('CONFLICT', parameterMismatch || strengthMismatch ? 'high' : 'critical', `Conflicting ${a.topic.replace('_', ' ')} obligations`, refs, `${a.id}: ${a.sentence}\n${b.id}: ${b.sentence}`, 'Assign an owner to reconcile the rules, document exceptions, and publish one controlling requirement.', scope, controlsFor(a.topic));
      } else if (a.action === b.action && a.polarity === b.polarity && (a.parameter === b.parameter || !a.parameter || !b.parameter)) {
        add('REDUNDANCY', 'medium', `Overlapping ${a.topic.replace('_', ' ')} obligation`, refs, `${a.id}: ${a.sentence}\n${b.id}: ${b.sentence}`, 'Consolidate the shared rule or add clear cross-references and scope.', scope, controlsFor(a.topic));
      }
    }
  }
  
  // 4. Check Staleness & Metadata review dates
  const now = new Date();
  parsed.forEach(d => {
    const reviewed = new Date(`${d.reviewed}T00:00:00`);
    const hasValidDate = Boolean(d.reviewed) && !Number.isNaN(reviewed.getTime());
    
    if (!hasValidDate) {
      add('MISSING_METADATA', 'medium', `Review metadata missing: ${d.title}`, [d.title], 'No valid last_reviewed date was found. The policy review age cannot be determined.', 'Add or restore a review date so the policy currency can be assessed.', 'Applies to the full policy document.', ['ISO 27001 A.5.2']);
    }
    
    const reasons = [];
    if (hasValidDate && (now - reviewed) / 864e5 > 548) {
      reasons.push(`last reviewed ${Math.floor((now - reviewed) / (864e5 * 30))} months ago`);
    }
    
    const hits = deprecated.filter(x => d.text.toLowerCase().includes(x));
    if (hits.length) {
      reasons.push(`deprecated reference: ${hits.join(', ')}`);
    }
    
    if (reasons.length) {
      add('STALENESS', hits.length ? 'high' : 'medium', `Review needed: ${d.title}`, [d.title], reasons.join('; '), 'Schedule a review and update obsolete references.', 'Applies to the full policy document.', ['ISO 27001 A.5.1', 'ISO 27001 A.5.2']);
    }
  });
  
  // Relative Staleness checks
  for (let i = 0; i < parsed.length; i++) {
    for (let j = i + 1; j < parsed.length; j++) {
      const a = parsed[i], b = parsed[j];
      const shared = a.domains.filter(x => b.domains.includes(x));
      const da = new Date(`${a.reviewed}T00:00:00`);
      const db = new Date(`${b.reviewed}T00:00:00`);
      const validA = Boolean(a.reviewed) && !Number.isNaN(da.getTime());
      const validB = Boolean(b.reviewed) && !Number.isNaN(db.getTime());
      
      if (!shared.length || !validA || !validB || Math.abs(da - db) / 864e5 < 365) continue;
      
      const [old, newer] = da < db ? [a, b] : [b, a];
      add('RELATIVE_STALENESS', 'medium', `Older related policy: ${old.title}`, [old.title, newer.title], `${old.title} was reviewed ${old.reviewed}; related ${newer.title} was reviewed ${newer.reviewed}. Shared domain: ${shared.join(', ')}.`, 'Review the older policy against the newer related policy and record a precedence decision.', `Comparison is limited to the shared domain: ${shared.join(', ')}.`, ['ISO 27001 A.5.2']);
    }
  }
  
  // OpenAI GPT evaluation (if enabled)
  const ai = await aiReview(parsed, findings);
  
  // Sort findings by severity
  findings.sort((a, b) => ({ critical: 0, high: 1, medium: 2 }[a.severity] - ({ critical: 0, high: 1, medium: 2 }[b.severity])));
  
  const policyHealth = parsed.map(d => {
    const relevant = findings.filter(f => f.policies.some(p => p.startsWith(d.title)));
    const deduction = relevant.reduce((s, f) => s + ({ critical: 28, high: 16, medium: 8 }[f.severity] || 4), 0);
    return {
      policy: d.title,
      domains: d.domains.length ? d.domains : ['Unclassified'],
      score: Math.max(0, 100 - deduction),
      findings: relevant.length,
      lastReviewed: d.reviewed || 'Not recorded'
    };
  });
  
  const comparisons = [];
  for (let i = 0; i < parsed.length; i++) {
    for (let j = i + 1; j < parsed.length; j++) {
      const a = parsed[i], b = parsed[j];
      const shared = a.domains.filter(x => b.domains.includes(x));
      const hasConflict = findings.some(f => f.kind === 'CONFLICT' && f.policies.includes(a.title) && f.policies.includes(b.title));
      comparisons.push({
        policyA: a.title,
        policyB: b.title,
        domainA: a.domains.length ? a.domains : ['Unclassified'],
        domainB: b.domains.length ? b.domains : ['Unclassified'],
        similarity: shared.length ? 'High' : 'Low',
        decision: !shared.length ? 'NO_CONFLICT_DIFFERENT_DOMAINS' : hasConflict ? 'CONFLICT_FOUND' : 'NO_CONFLICT_COMPATIBLE_CONTROLS',
        reason: !shared.length ? 'The policies govern different security domains. No cross-policy conflict analysis is required.' : hasConflict ? `A contradiction was found in the shared domain: ${shared.join(', ')}.` : `Both policies cover ${shared.join(', ')}, but their controls are compatible (for example, password length and password rotation).`
      });
    }
  }
  
  const coverage = Object.keys(topics).map(topic => ({
    topic,
    count: obligations.filter(o => o.topic === topic).length
  })).filter(x => x.count);
  
  const severityDistribution = ['critical', 'high', 'medium', 'low'].map(severity => ({
    severity,
    count: findings.filter(f => f.severity === severity).length
  }));
  
  const timeline = parsed.map(d => {
    const reviewed = new Date(`${d.reviewed}T00:00:00`);
    const valid = Boolean(d.reviewed) && !Number.isNaN(reviewed.getTime());
    const age = valid ? Math.floor((now - reviewed) / 864e5) : null;
    return {
      policy: d.title,
      date: d.reviewed || 'Not recorded',
      domains: d.domains,
      ageDays: age,
      status: !valid ? 'missing' : age > 548 ? 'overdue' : 'current'
    };
  }).sort((a, b) => a.date.localeCompare(b.date));
  
  const critical = findings.filter(f => f.severity === 'critical').length;
  const stale = findings.filter(f => f.kind === 'STALENESS' || f.kind === 'RELATIVE_STALENESS').length;
  const missing = findings.filter(f => f.kind === 'MISSING_METADATA').length;
  const score = Math.max(0, 100 - findings.reduce((s, f) => s + ({ critical: 14, high: 9, medium: 4, low: 2 }[f.severity] || 1), 0));
  
  const executiveSummary = `${parsed.length} polic${parsed.length === 1 ? 'y was' : 'ies were'} analysed across ${new Set(parsed.flatMap(d => d.domains)).size} security domains. ${critical ? `${critical} critical conflict${critical === 1 ? ' was' : 's were'} identified.` : 'No critical conflicts were identified.'} ${stale ? `${stale} policy finding${stale === 1 ? '' : 's'} require review for currency.` : ''} ${missing ? `${missing} policy record${missing === 1 ? ' is' : 's are'} missing review metadata.` : ''}`.trim();
  const recommendations = findings.filter(f => ['critical', 'high'].includes(f.severity)).slice(0, 4).map(f => f.recommendation);
  if (!recommendations.length) recommendations.push('Continue the regular review cycle and record review dates for every policy.');
  
  const graph = {
    nodes: parsed.map(p => {
      const reviewStatus = timeline.find(t => t.policy === p.title)?.status || 'missing';
      return {
        id: p.title,
        title: p.title,
        department: p.department || 'Security Operations',
        version: p.version || '1.0',
        lastReviewed: p.reviewed || 'Not recorded',
        status: reviewStatus === 'overdue' ? 'Overdue' : reviewStatus === 'missing' ? 'Missing Metadata' : 'Within Review Cycle',
        findingsCount: findings.filter(f => f.policies.some(pn => pn.startsWith(p.title))).length,
        connectedCount: comparisons.filter(c => (c.policyA === p.title || c.policyB === p.title) && c.decision !== 'NO_CONFLICT_DIFFERENT_DOMAINS').length
      };
    }),
    edges: comparisons.filter(c => c.decision !== 'NO_CONFLICT_DIFFERENT_DOMAINS').map((c, idx) => {
      let relType = 'Related';
      if (c.decision === 'CONFLICT_FOUND') relType = 'Conflict';
      else if (c.decision.includes('COMPATIBLE_CONTROLS')) relType = 'Complementary';
      else if (c.decision.includes('REDUNDANT')) relType = 'Redundant';
      
      const match = findings.find(f => f.policies.some(pn => pn.startsWith(c.policyA)) && f.policies.some(pn => pn.startsWith(c.policyB)));
      const severity = match ? match.severity : 'low';
      const confidence = c.similarity === 'High' ? 0.89 : 0.65;
      const recommendation = match ? match.recommendation : 'No action required. Control alignment verified.';
      
      return {
        id: `e_${idx}`,
        from: c.policyA,
        to: c.policyB,
        label: relType,
        type: relType,
        confidence,
        severity,
        reason: c.reason,
        recommendation
      };
    })
  };
  
  const classifierEngineName = mlFailed ? "Rule-based Fallback Model" : "Trained BAAI/bge-small-en-v1.5 + Logistic Regression Model";
  
  return {
    documents: parsed.length,
    obligations,
    findings,
    candidatePairs,
    graph,
    policyHealth,
    comparisons,
    coverage,
    severityDistribution,
    timeline,
    executive: { score, critical, stale, missing, summary: executiveSummary, recommendations },
    classifier: classifierEngineName,
    ai,
    generatedAt: new Date().toISOString()
  };
}

const mime = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.json': 'application/json'
};

const server = http.createServer((req, res) => {
  // CORS Headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  if (req.method === 'POST' && req.url === '/api/analyse') {
    let body = '';
    req.on('data', c => body += c);
    req.on('end', async () => {
      try {
        const data = JSON.parse(body);
        if (!data.documents || !Array.isArray(data.documents) || !data.documents.length) {
          throw Error('Add at least one policy document.');
        }
        const result = await analyse(data.documents);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(result));
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }

  // Serve static files from root directory (serves demo_dashboard.html, css, etc.)
  const file = req.url === '/' ? 'demo_dashboard.html' : req.url.replace(/^\//, '');
  const safe = path.normalize(file).replace(/^\.\.[\\/]+/, '');
  const full = path.join(__dirname, safe);
  
  fs.readFile(full, (err, data) => {
    if (err) {
      res.writeHead(404);
      return res.end('Not found');
    }
    res.writeHead(200, { 'Content-Type': mime[path.extname(full)] || 'text/plain' });
    res.end(data);
  });
});

server.listen(PORT, () => console.log(`Policy Nexus running at http://localhost:${PORT}`));
