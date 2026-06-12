import React, { useState, useMemo } from 'react';

export default function ResultsTable({ matchedData }) {
  const [slotFilter, setSlotFilter] = useState('');
  const [deptFilter, setDeptFilter] = useState('');

  const allCourses = useMemo(() => {
    const arr = [];
    if (matchedData.PC) arr.push(...matchedData.PC.map(c => ({...c, category: 'PC'})));
    if (matchedData.PE) arr.push(...matchedData.PE.map(c => ({...c, category: 'PE'})));
    if (matchedData.SC) arr.push(...matchedData.SC.map(c => ({...c, category: 'SC'})));
    if (matchedData.SE) arr.push(...matchedData.SE.map(c => ({...c, category: 'SE'})));
    return arr;
  }, [matchedData]);

  const uniqueSlots = [...new Set(allCourses.map(c => c.slot).filter(Boolean))].sort();
  const uniqueDepts = [...new Set(allCourses.map(c => c.department).filter(Boolean))].sort();

  const renderTableSection = (title, data) => {
    const filtered = data.filter(c => {
      if (slotFilter && !String(c.slot).includes(slotFilter)) return false;
      if (deptFilter && c.department !== deptFilter) return false;
      return true;
    });

    if (filtered.length === 0) return null;

    return (
      <div className="mb-4">
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
                  <td>{c.name || c.originalCurriculumName}</td>
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
        {matchedData.PC && renderTableSection('Program Core (PC) Offered', matchedData.PC)}
        {matchedData.PE && renderTableSection('Program Elective (PE) Offered', matchedData.PE)}
        {matchedData.SC && renderTableSection('Specialization Core (SC) Offered', matchedData.SC)}
        {matchedData.SE && renderTableSection('Specialization Elective (SE) Offered', matchedData.SE)}

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
