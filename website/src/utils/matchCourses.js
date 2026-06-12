import Fuse from 'fuse.js';

export function matchCourses(offeredCourses, curriculumData, program, branch, spec) {
  let pc = [];
  let pe = [];
  let sc = [];
  let se = [];
  
  try {
    const branchData = curriculumData[program] && curriculumData[program][branch];
    if (branchData && branchData.semesters) {
      for (const sem of Object.values(branchData.semesters)) {
        if (sem.PC) pc.push(...sem.PC.map(c => ({...c, currType: 'PC'})));
        if (sem.PE) pe.push(...sem.PE.map(c => ({...c, currType: 'PE'})));
        if (sem.SC) sc.push(...sem.SC.map(c => ({...c, currType: 'SC'})));
        if (sem.SE) se.push(...sem.SE.map(c => ({...c, currType: 'SE'})));
      }
    }
    
    if (spec && spec !== 'NO' && branchData && branchData.specializations && branchData.specializations[spec]) {
      const specData = branchData.specializations[spec];
      if (specData.core) sc.push(...specData.core.map(c => ({...c, currType: 'SC'})));
      if (specData.electives) se.push(...specData.electives.map(c => ({...c, currType: 'SE'})));
    }
  } catch (e) {
    console.error("Error extracting curriculum data", e);
  }

  const uniqueByCodeOrName = (arr) => {
    const seen = new Set();
    return arr.filter(item => {
      const key = item.code ? item.code.trim().toUpperCase() : (item.name ? item.name.trim().toLowerCase() : Math.random());
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  };

  pc = uniqueByCodeOrName(pc);
  pe = uniqueByCodeOrName(pe);
  sc = uniqueByCodeOrName(sc);
  se = uniqueByCodeOrName(se);

  const fuseOptions = {
    keys: ['name'],
    threshold: 0.3,
    includeScore: true
  };

  const fuseOffered = new Fuse(offeredCourses, fuseOptions);

  const findMatch = (currCourse) => {
    if (currCourse.code) {
      const exact = offeredCourses.find(c => c.code && c.code.replace(/\s+/g,'').toUpperCase() === currCourse.code.replace(/\s+/g,'').toUpperCase());
      if (exact) return exact;
    }
    if (currCourse.name) {
      const results = fuseOffered.search(currCourse.name);
      if (results.length > 0 && results[0].score < 0.4) {
        return results[0].item;
      }
    }
    return null;
  };

  const mapMatched = (list) => {
    return list.map(c => {
      const matched = findMatch(c);
      if (matched) {
        return { ...matched, currType: c.currType, originalCurriculumName: c.name };
      }
      return null;
    }).filter(Boolean);
  };

  return {
    PC: mapMatched(pc),
    PE: mapMatched(pe),
    SC: mapMatched(sc),
    SE: mapMatched(se)
  };
}
