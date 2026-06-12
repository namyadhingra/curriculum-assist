import React, { useRef } from 'react';
import { parseExcel } from '../utils/parseExcel';

export default function ExcelUploader({ onUpload, isLoading, setIsLoading }) {
  const fileInputRef = useRef(null);

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setIsLoading(true);
    try {
      const data = await parseExcel(file);
      onUpload(data);
    } catch (err) {
      alert("Failed to parse Excel file. Please ensure it's a valid xlsx format.");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="card text-center">
      <h2 className="mb-4">Upload Offered Courses</h2>
      <p className="text-sm text-muted mb-4">Upload the Excel file containing all departments’ offered courses.</p>
      
      <input 
        type="file" 
        accept=".xlsx, .xls" 
        onChange={handleFileChange} 
        style={{ display: 'none' }} 
        ref={fileInputRef} 
      />
      
      <button onClick={() => fileInputRef.current.click()} disabled={isLoading}>
        {isLoading ? 'Parsing...' : 'Select Excel File'}
      </button>
    </div>
  );
}
