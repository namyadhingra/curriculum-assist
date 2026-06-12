import React from 'react';
import * as XLSX from 'xlsx';
import { toPng } from 'html-to-image';

export default function ExportControls({ matchedData, program, branch }) {
  
  const handleExportExcel = () => {
    const wb = XLSX.utils.book_new();
    
    const formatData = (data) => data.map(c => ({
      Category: c.currType,
      Code: c.code,
      Name: c.name || c.originalCurriculumName,
      Slot: c.slot,
      Department: c.department,
      Instructor: c.instructor,
      Credits: c.credits,
      LTP: c.ltp,
      Remarks: c.remarks
    }));

    let allRows = [];
    if (matchedData.PC) allRows.push(...formatData(matchedData.PC));
    if (matchedData.PE) allRows.push(...formatData(matchedData.PE));
    if (matchedData.SC) allRows.push(...formatData(matchedData.SC));
    if (matchedData.SE) allRows.push(...formatData(matchedData.SE));

    const ws = XLSX.utils.json_to_sheet(allRows);
    XLSX.utils.book_append_sheet(wb, ws, "Offered Courses");

    const filename = `${program}_${branch}_FilteredCourses.xlsx`;
    XLSX.writeFile(wb, filename);
  };

  const handleExportImage = async () => {
    const node = document.getElementById('capture-area');
    if (!node) return;
    try {
      const dataUrl = await toPng(node, { backgroundColor: '#ffffff' });
      const link = document.createElement('a');
      link.download = `${program}_${branch}_FilteredCourses.png`;
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error("Error capturing image", err);
      alert("Failed to capture image.");
    }
  };

  const handleCopyClipboard = () => {
    const node = document.getElementById('capture-area');
    if (!node) return;
    try {
      const html = node.innerHTML;
      const blob = new Blob([html], { type: 'text/html' });
      const data = [new ClipboardItem({ 'text/html': blob })];
      navigator.clipboard.write(data).then(() => {
        alert("Copied to clipboard!");
      });
    } catch (err) {
      console.error("Error copying", err);
      alert("Failed to copy. Your browser might not support this feature.");
    }
  };

  return (
    <div className="flex gap-4 mb-4" data-html2canvas-ignore>
      <button onClick={handleExportExcel}>Download Excel</button>
      <button onClick={handleExportImage}>Download Image</button>
      <button onClick={handleCopyClipboard}>Copy to Clipboard</button>
    </div>
  );
}
