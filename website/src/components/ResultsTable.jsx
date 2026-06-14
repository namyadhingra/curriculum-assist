import React, { useState, useMemo } from 'react';

const CATEGORY_TITLES = {
  'PC': 'Program Core (PC)',
  'PE': 'Program Elective (PE)',
  'OE': 'Open Electives (OE)',
  'IS': 'Institute Science (IS)',
  'IE': 'Institute Engineering (IE)',
  'IH': 'Institute Humanities (IH)',
  'LS': 'Programme Linked Science (LS)',
  'PP': 'B.Tech. Project (PP)',
  'EC': 'Engineering Science Core (EC)',
  'EE': 'Engineering Science Elective (EE)',
  'NH': 'Non-Graded Humanities (NH)',
  'NE': 'Non-Graded Engineering (NE)',
  'ND': 'Design/Practical Experience (ND)'
};

export default function ResultsTable({ matchedData }) {
  const [slotFilter, setSlotFilter] = useState('');
  const [deptFilter, setDeptFilter] = useState('');

  const allCourses = useMemo(() => {
    const arr = [];
    Object.keys(matchedData).forEach(key => {
      arr.push(...matchedData[key].map(c => ({...c, category: key})));
    });
    return arr;
  }, [matchedData]);

  const uniqueSlots = [...new Set(allCourses.map(c => c.slot).filter(Boolean))].sort();
  const uniqueDepts = [...new Set(allCourses.map(c => c.department).filter(Boolean))].sort();

  const renderTableSection = (key, data) => {
    const filtered = data.filter(c => {
      if (slotFilter && !String(c.slot).includes(slotFilter)) return false;
      if (deptFilter && c.department !== deptFilter) return false;
      return true;
    });

    if (filtered.length === 0) return null;

    const title = CATEGORY_TITLES[key] ? `${CATEGORY_TITLES[key]} Offered` : `${key} Offered`;

    return (
      <div className="mb-4" key={key}>
        <h3>{title} ({filtered.length})</h3>
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Slot</th>
                <th>Dept</th>
                <th>Instructor</th>
                <th>Credits</th>
                <th>L-T-P</th>
                <th>Remarks</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c, i) => (
                <tr key={i}>
                  <td>{c.code || '-'}</td>
                  <td>
                    {c.name || c.originalCurriculumName}
                    {(c.currType === 'SC' || c.currType === 'SE') && (
                      <span style={{ fontSize: '0.85em', color: '#e53e3e', marginLeft: '8px' }}>(Specialization)</span>
                    )}
                  </td>
                  <td>{c.slot || '-'}</td>
                  <td>{c.department || '-'}</td>
                  <td>{c.instructor || '-'}</td>
                  <td>{c.credits || '-'}</td>
                  <td>{c.ltp || '-'}</td>
                  <td>{c.remarks || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="card" id="results-container">
      <h2 className="mb-4">Offered Curriculum Courses</h2>
      
      <div className="flex gap-4 mb-4" data-html2canvas-ignore>
        <select value={slotFilter} onChange={e => setSlotFilter(e.target.value)}>
          <option value="">All Slots</option>
          {uniqueSlots.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={deptFilter} onChange={e => setDeptFilter(e.target.value)}>
          <option value="">All Departments</option>
          {uniqueDepts.map(d => <option key={d} value={d}>{d}</option>)}
        </select>
      </div>

      <div id="capture-area" style={{ background: 'white', padding: '10px' }}>
        {Object.keys(CATEGORY_TITLES).map(key => {
          return matchedData[key] && renderTableSection(key, matchedData[key]);
        })}

        {allCourses.length === 0 && (
          <p className="text-muted text-center py-4">No matching courses found in the uploaded sheet.</p>
        )}
        
        <div className="mt-4 text-sm text-muted text-center" style={{ borderTop: '1px solid #e2e8f0', paddingTop: '1rem' }}>
          <p><strong>Disclaimer:</strong> Do not depend 100% on this output. The curriculum data may be outdated or incomplete.</p>
          <p>Please go through the offered courses sheet yourself for Open Electives offered :)</p>
          <p style={{fontSize: '0.8em', marginTop: '0.5rem'}}>CSE and AIDE curriculums used are from 2020. The 2026 onwards curriculums are not used here.<br/>
          This website is for 2nd year onwards students. Curriculums for ECE and Aerospace Engineering have not been updated.<br/>
          Last updated: June 2026.</p>
        </div>
      </div>
    </div>
  );
}
