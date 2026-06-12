import React, { useState } from 'react';

export default function ProgramSelector({ curriculumData, onComplete }) {
  const [program, setProgram] = useState('');
  const [branch, setBranch] = useState('');
  const [hasSpec, setHasSpec] = useState(null);
  const [spec, setSpec] = useState('');

  const supportedPrograms = ['BTECH', 'BS'];
  const allPrograms = ['BTECH', 'BS', 'MTECH', 'MSC', 'PHD', 'MS'];

  const handleProgramChange = (e) => {
    setProgram(e.target.value);
    setBranch('');
    setHasSpec(null);
    setSpec('');
  };

  const handleBranchChange = (e) => {
    setBranch(e.target.value);
    setHasSpec(null);
    setSpec('');
  };

  if (program && !supportedPrograms.includes(program)) {
    return (
      <div className="card text-center">
        <h2>Work in Progress!</h2>
        <p className="mb-4">Program coming soon! This section is still a work in progress — we’ll get to all programs soon :)</p>
        <button onClick={() => setProgram('')}>Go Back</button>
      </div>
    );
  }

  const availableBranches = program && curriculumData[program] ? Object.keys(curriculumData[program]) : [];
  
  const branchData = program && branch ? curriculumData[program][branch] : null;
  const availableSpecs = branchData && branchData.specializations ? Object.keys(branchData.specializations) : [];

  const handleComplete = () => {
    onComplete({ program, branch, spec: hasSpec === 'yes' ? spec : 'NO' });
  };

  const isReady = program && branch && (hasSpec === 'no' || (hasSpec === 'yes' && spec));

  return (
    <div className="card">
      <h2 className="mb-4">Select Your Curriculum</h2>
      
      <div className="flex-col gap-4">
        <div>
          <label className="text-sm font-semibold mb-2 block">Program</label>
          <select value={program} onChange={handleProgramChange} className="w-full">
            <option value="">-- Select Program --</option>
            {allPrograms.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>

        {program && supportedPrograms.includes(program) && (
          <div className="mt-4">
            <label className="text-sm font-semibold mb-2 block">Branch</label>
            <select value={branch} onChange={handleBranchChange} className="w-full">
              <option value="">-- Select Branch --</option>
              {availableBranches.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
        )}

        {branch && availableSpecs.length > 0 && (
          <div className="mt-4">
            <label className="text-sm font-semibold mb-2 block">Do you have a specialization?</label>
            <div className="flex gap-4">
              <label>
                <input type="radio" name="hasSpec" checked={hasSpec === 'yes'} onChange={() => setHasSpec('yes')} /> Yes
              </label>
              <label>
                <input type="radio" name="hasSpec" checked={hasSpec === 'no'} onChange={() => { setHasSpec('no'); setSpec(''); }} /> No
              </label>
            </div>
          </div>
        )}

        {branch && availableSpecs.length === 0 && (
           <div className="mt-4 text-sm text-muted">
             No specializations available for this branch.
           </div>
        )}

        {hasSpec === 'yes' && (
          <div className="mt-4">
            <label className="text-sm font-semibold mb-2 block">Specialization</label>
            <select value={spec} onChange={e => setSpec(e.target.value)} className="w-full">
              <option value="">-- Select Specialization --</option>
              {availableSpecs.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        )}

        <div className="mt-4">
          <button 
            disabled={!isReady && !(branch && availableSpecs.length === 0)}
            onClick={handleComplete}
            style={{ opacity: (!isReady && !(branch && availableSpecs.length === 0)) ? 0.5 : 1 }}
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  );
}
