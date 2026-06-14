import Fuse from 'fuse.js';

const CATEGORY_KEYS = ['PC', 'PE', 'OE', 'IS', 'IE', 'IH', 'LS', 'PP', 'EC', 'EE', 'NH', 'NE', 'ND'];

export function matchCourses(offeredCourses, curriculumData, program, branch, spec) {
  const categoryMap = {};
  CATEGORY_KEYS.forEach(k => categoryMap[k] = []);
  let sc = [];
  let se = [];
  
  try {
    const branchData = curriculumData[program] && curriculumData[program][branch];
    if (branchData && branchData.semesters) {
      for (const sem of Object.values(branchData.semesters)) {
        CATEGORY_KEYS.forEach(key => {
          if (sem[key]) categoryMap[key].push(...sem[key].map(c => ({...c, currType: key})));
        });
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

  // Merge SC into PC (as requested: specialization core/compulsory appear with other core/compulsory)
  categoryMap['PC'].push(...sc);
  categoryMap['PE'].push(...se);

  const uniqueByCodeOrName = (arr) => {
    const seen = new Set();
    return arr.filter(item => {
      const key = item.code ? item.code.trim().toUpperCase() : (item.name ? item.name.trim().toLowerCase() : Math.random());
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  };

  CATEGORY_KEYS.forEach(key => {
    categoryMap[key] = uniqueByCodeOrName(categoryMap[key]);
  });

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
        let bestMatch = results[0].item;
        let bestScore = results[0].score;
        
        // Prioritize courses offered by the student's department if multiple similar matches exist
        const candidateResults = results.filter(r => r.score - bestScore < 0.1);
        if (candidateResults.length > 1) {
          const branchDept = branch ? branch.toLowerCase() : '';
          const preferred = candidateResults.find(r => r.item.department && r.item.department.toLowerCase().includes(branchDept));
          if (preferred) {
            return preferred.item;
          }
        }
        return bestMatch;
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

  const result = {};
  CATEGORY_KEYS.forEach(key => {
    const matched = mapMatched(categoryMap[key]);
    if (matched.length > 0) {
      result[key] = matched;
    }
  });

  return result;
}
