// lib/candidate-selector.js - Finds policy pairs that are candidate targets for GRC audits

function selectCandidatePairs(obligations) {
  const pairs = [];
  const visited = new Set();
  
  for (let i = 0; i < obligations.length; i++) {
    for (let j = i + 1; j < obligations.length; j++) {
      const a = obligations[i];
      const b = obligations[j];
      
      if (a.policy === b.policy) continue;
      
      // Select pairs if they share a specific security topic (excluding general topics)
      if (a.topic === b.topic && a.topic !== 'general') {
        const sortedPairKey = [a.policy, b.policy].sort().join('::');
        if (!visited.has(sortedPairKey)) {
          visited.add(sortedPairKey);
          pairs.push({
            policyA: a.policy,
            policyB: b.policy,
            ruleHint: `${a.topic.replace('_', ' ')} overlap`,
            similarity: 0.85
          });
        }
      }
    }
  }
  return pairs;
}

module.exports = {
  selectCandidatePairs
};
