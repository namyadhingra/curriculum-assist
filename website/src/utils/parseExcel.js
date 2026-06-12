import * as XLSX from 'xlsx';
import { normalizeColumns } from './normalizeColumns';

export async function parseExcel(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
        
        let allCourses = [];

        workbook.SheetNames.forEach(sheetName => {
          const sheet = workbook.Sheets[sheetName];
          const jsonData = XLSX.utils.sheet_to_json(sheet, { header: 1 });
          if (jsonData.length === 0) return;

          let headerRowIdx = jsonData.findIndex(row => row && row.length > 0);
          if (headerRowIdx === -1) return;

          // Try to find a row that has at least "course" or "code" in it to be sure it's a header
          let betterHeaderIdx = jsonData.findIndex((row, idx) => {
            if (idx < headerRowIdx) return false;
            return row.some(cell => typeof cell === 'string' && (cell.toLowerCase().includes('course') || cell.toLowerCase().includes('code')));
          });
          if (betterHeaderIdx !== -1) {
            headerRowIdx = betterHeaderIdx;
          }

          const headers = jsonData[headerRowIdx];
          const colMap = normalizeColumns(headers);

          const colIndices = {};
          for (const [key, origHeader] of Object.entries(colMap)) {
            colIndices[key] = headers.indexOf(origHeader);
          }

          for (let i = headerRowIdx + 1; i < jsonData.length; i++) {
            const row = jsonData[i];
            if (!row || row.length === 0) continue;
            
            const hasCode = colIndices.code !== undefined && row[colIndices.code];
            const hasName = colIndices.name !== undefined && row[colIndices.name];
            
            if (!hasCode && !hasName) continue;

            allCourses.push({
              department: sheetName,
              code: colIndices.code !== undefined && row[colIndices.code] ? String(row[colIndices.code]).trim() : '',
              name: colIndices.name !== undefined && row[colIndices.name] ? String(row[colIndices.name]).trim() : '',
              slot: colIndices.slot !== undefined && row[colIndices.slot] ? String(row[colIndices.slot]).trim() : '',
              instructor: colIndices.instructor !== undefined && row[colIndices.instructor] ? String(row[colIndices.instructor]).trim() : '',
              credits: colIndices.credits !== undefined && row[colIndices.credits] ? String(row[colIndices.credits]).trim() : '',
              remarks: colIndices.remarks !== undefined && row[colIndices.remarks] ? String(row[colIndices.remarks]).trim() : '',
              ltp: colIndices.ltp !== undefined && row[colIndices.ltp] ? String(row[colIndices.ltp]).trim() : ''
            });
          }
        });

        resolve(allCourses);
      } catch (err) {
        reject(err);
      }
    };
    reader.onerror = reject;
    reader.readAsArrayBuffer(file);
  });
}
