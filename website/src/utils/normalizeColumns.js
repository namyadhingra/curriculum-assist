export function normalizeColumns(headers) {
  const mapping = {
    code: ['course code', 'code', 'course no', 'courseno'],
    name: ['course name', 'course title', 'title', 'name of the course', 'course'],
    slot: ['slot', 'timing', 'schedule'],
    instructor: ['instructor', 'name of faculty', 'instructor/coordinator', 'instructor(s)', 'coordinator', 'faculty'],
    credits: ['credits', 'cr'],
    remarks: ['remarks', 'batch', 'program', 'offered for', 'comments', 'target audience'],
    ltp: ['l-t-p', 'ltp', 'l t p']
  };

  const normalized = {};

  headers.forEach((header) => {
    if (!header || typeof header !== 'string') return;
    const lowerHeader = header.toLowerCase().replace(/[^a-z0-9]/g, '');

    for (const [key, aliases] of Object.entries(mapping)) {
      if (normalized[key] !== undefined) continue;

      if (aliases.some(alias => lowerHeader.includes(alias.replace(/[^a-z0-9]/g, '')))) {
        normalized[key] = header;
        break;
      }
    }
  });

  return normalized;
}
