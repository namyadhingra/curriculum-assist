// Curriculum links data organized by program and branch
export const curriculumLinks = {
  BTECH: {
    CSE: {
      name: "Computer Science and Engineering",
      url: "https://iitj.ac.in/PageImages/Gallery/07-2025/Curriculum-BTech-CSE.pdf"
    },
    EE: {
      name: "Electrical Engineering",
      url: "https://iitj.ac.in/PageImages/Gallery/06-2026/UG-EE-Curriculum-639165301621059694.pdf"
    },
    ME: {
      name: "Mechanical Engineering",
      url: "https://www.iitj.ac.in/PageImages/Gallery/03-2025/2-year-BTech-Mechanical-Engineering-638772016845439168.pdf"
    },
    CM: {
      name: "AI and Data Science",
      url: "https://iitj.ac.in/PageImages/Gallery/07-2025/Curriculum-BTech-AIDS.pdf"
    },
    CE: {
      name: "Chemical Engineering",
      url: "https://www.iitj.ac.in/PageImages/Gallery/06-2026/Undergraduate-Program-Course-Curriculum-Chemical-Engineering-639165131726233367.pdf"
    },
    MT: {
      name: "Materials Engineering",
      url: "https://www.iitj.ac.in/PageImages/Gallery/02-2025/BTech-Materials-Engineering-638756573578780359.pdf"
    },
    BB: {
      name: "Biotechnology",
      url: "https://www.iitj.ac.in/PageImages/Gallery/03-2025/biocurr2-638769681404313393.pdf"
    },
    CI: {
      name: "Civil and Infrastructure Engineering",
      url: "https://iitj.ac.in/Office-of-Academics/en/B.Tech.-Civil-and-Infrastructure-Engineering"
    }
  },
  BS: {
    PH: {
      name: "Physics with Specialization",
      url: "https://iitj.ac.in/PageImages/Gallery/02-2025/Curriculum1-638755740799615537.pdf"
    },
    CY: {
      name: "Chemistry with Specialization",
      url: "https://www.iitj.ac.in/office-of-academics/en/BS-(Chemistry)-with-Specialization"
    },
    MC: {
      name: "Mathematics & Computing",
      url: "https://www.iitj.ac.in/PageImages/Gallery/06-2026/Concept-Note-BS-Mathematics-Computing-639161752393828689.pdf"
    }
  }
};

/**
 * Get curriculum link for a given program and branch
 */
export const getCurriculumLink = (program, branch) => {
  return curriculumLinks[program]?.[branch];
};
