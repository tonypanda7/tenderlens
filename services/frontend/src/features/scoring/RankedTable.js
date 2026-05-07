import React, { useState, useEffect } from 'react';
import { getTenderRanking } from '../../api';

export default function RankedTable() {
  const [result, setResult] = useState('Loading evaluation...');

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const tenderId = urlParams.get('tender_id');
    
    if (tenderId) {
      getTenderRanking(tenderId)
        .then(res => {
          setResult(res.data.simple_result || 'No evaluation found for this tender.');
        })
        .catch(err => {
          setResult('Error loading evaluation from API.');
        });
    } else {
      setResult('No tender ID provided in URL.');
    }
  }, []);

  return (
    <div style={{ padding: '40px', maxWidth: '800px', margin: '0 auto', fontFamily: 'monospace', whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>
      {result}
    </div>
  );
}
