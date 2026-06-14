import React from 'react';
import { getCurriculumLink } from '../data/curriculumLinks';

export default function CurriculumLinks({ program, branch }) {
  const curriculumLink = getCurriculumLink(program, branch);

  if (!curriculumLink) {
    return null;
  }

  return (
    <div className="card" style={{ backgroundColor: '#edf2f7', borderLeft: '4px solid #2b6cb0' }}>
      <h3 style={{ marginTop: 0, marginBottom: '12px', color: '#1a202c' }}>📚 Curriculum Resources</h3>
      <p style={{ marginBottom: '12px', color: '#4a5568', fontSize: '14px' }}>
        The matched courses are based on the {program} {branch} curriculum:
      </p>
      <a
        href={curriculumLink.url}
        target="_blank"
        rel="noopener noreferrer"
        style={{
          display: 'inline-block',
          padding: '10px 16px',
          backgroundColor: '#2b6cb0',
          color: 'white',
          textDecoration: 'none',
          borderRadius: '4px',
          fontSize: '14px',
          fontWeight: '500',
          transition: 'background-color 0.2s'
        }}
        onMouseOver={(e) => e.target.style.backgroundColor = '#1e4d7b'}
        onMouseOut={(e) => e.target.style.backgroundColor = '#2b6cb0'}
      >
        📄 View {curriculumLink.name} Curriculum
      </a>
    </div>
  );
}
