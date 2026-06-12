import React, { useState, useEffect } from 'react';
import curriculumData from './data/curriculum.json';
import ProgramSelector from './components/ProgramSelector';
import ExcelUploader from './components/ExcelUploader';
import ResultsTable from './components/ResultsTable';
import ExportControls from './components/ExportControls';
import { matchCourses } from './utils/matchCourses';
import { saveState, loadState, clearState } from './utils/storage';

function App() {
  const [selection, setSelection] = useState(null);
  const [offeredCourses, setOfferedCourses] = useState(null);
  const [matchedData, setMatchedData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const cachedSelection = loadState('curriculum_selection');
    const cachedCourses = loadState('offered_courses');
    
    if (cachedSelection) setSelection(cachedSelection);
    if (cachedCourses) setOfferedCourses(cachedCourses);
  }, []);

  useEffect(() => {
    if (selection && offeredCourses) {
      const result = matchCourses(offeredCourses, curriculumData, selection.program, selection.branch, selection.spec);
      setMatchedData(result);
    } else {
      setMatchedData(null);
    }
  }, [selection, offeredCourses]);

  const handleSelectionComplete = (sel) => {
    setSelection(sel);
    saveState('curriculum_selection', sel);
  };

  const handleExcelUpload = (courses) => {
    setOfferedCourses(courses);
    saveState('offered_courses', courses);
  };

  const handleClearAll = () => {
    clearState();
    setSelection(null);
    setOfferedCourses(null);
    setMatchedData(null);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1>Curriculum Assist</h1>
        {(selection || offeredCourses) && (
          <button onClick={handleClearAll} style={{ backgroundColor: '#e53e3e' }}>Clear All</button>
        )}
      </div>
      
      {!selection ? (
        <ProgramSelector curriculumData={curriculumData} onComplete={handleSelectionComplete} />
      ) : !offeredCourses ? (
        <ExcelUploader onUpload={handleExcelUpload} isLoading={isLoading} setIsLoading={setIsLoading} />
      ) : (
        <div>
          <div className="card mb-4 flex justify-between items-center flex-wrap gap-4">
            <div>
              <strong>Program:</strong> {selection.program} | <strong>Branch:</strong> {selection.branch} 
              {selection.spec !== 'NO' && ` | Spec: ${selection.spec}`}
            </div>
            <button onClick={() => { setSelection(null); setMatchedData(null); }} style={{ backgroundColor: '#718096' }}>Change Program</button>
          </div>
          
          {matchedData && (
            <>
              <ExportControls matchedData={matchedData} program={selection.program} branch={selection.branch} />
              <ResultsTable matchedData={matchedData} />
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
