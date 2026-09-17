import type { Assignment, Course, Material, StudentRow, ChatMessage } from "@/types"

export const currentStudent = {
  id: "s1",
  name: "Amina K.",
  email: "amina.k@student.tanta.edu.eg",
  role: "student" as const,
}

export const currentTeacher = {
  id: "t1",
  name: "Dr. Yasmin Farouk",
  email: "y.farouk@tanta.edu.eg",
  role: "teacher" as const,
}

export const studentCourses: Course[] = [
  {
    id: "math-sec-2",
    code: "MATH 214",
    name: "Math — Section 2",
    description: "Gradient Descent & Linear Regression",
    teacher: "Dr. Hassan Adel",
    status: "Active",
    color: "plum",
    materialCount: 5,
    assignmentCount: 4,
  },
  {
    id: "physics-sec-1",
    code: "PHYS 108",
    name: "Physics — Section 1",
    description: "Electronics module",
    teacher: "Dr. Yasmin Farouk",
    status: "Active",
    color: "slate",
    materialCount: 6,
    assignmentCount: 3,
  },
  {
    id: "mech-sec-1",
    code: "MECH 201",
    name: "Mechanics — Section 1",
    description: "Statics & dynamics",
    teacher: "Dr. Omar Said",
    status: "Active",
    color: "teal",
    materialCount: 4,
    assignmentCount: 2,
  },
]

export const teacherCourses: Course[] = [
  {
    id: "physics-sec-1",
    code: "PHYS 108",
    name: "Physics — Section 1",
    description: "5 materials · 4 assignments",
    teacher: "Dr. Yasmin Farouk",
    status: "Active",
    color: "slate",
    materialCount: 5,
    assignmentCount: 4,
    studentCount: 28,
  },
  {
    id: "physics-sec-2",
    code: "PHYS 109",
    name: "Physics — Section 2",
    description: "Electronics module",
    teacher: "Dr. Yasmin Farouk",
    status: "Active",
    color: "plum",
    materialCount: 5,
    assignmentCount: 4,
    studentCount: 24,
  },
  {
    id: "physics-sec-3",
    code: "PHYS 110",
    name: "Physics — Section 3",
    description: "Communication unit",
    teacher: "Dr. Yasmin Farouk",
    status: "Active",
    color: "teal",
    materialCount: 3,
    assignmentCount: 2,
    studentCount: 22,
  },
]

export const materials: Material[] = [
  {
    id: "m5",
    courseId: "math-sec-2",
    title: "Material 5 — Setting up Gradient Descent",
    summary:
      "This reading covers the core setup needed before the gradient descent assignment: notation for feature vectors, targets, and the mean-squared-error cost function.",
    kind: "reading",
  },
  {
    id: "m4",
    courseId: "math-sec-2",
    title: "Material 4 — Cost Functions",
    summary: "An overview of convex cost functions and why gradient descent converges toward a minimum.",
    kind: "slides",
  },
  {
    id: "m3",
    courseId: "math-sec-2",
    title: "Material 3 — Vectors & Notation",
    summary: "Refresher on vector and matrix notation used throughout the linear regression unit.",
    kind: "reading",
  },
]

export const assignments: Assignment[] = [
  {
    id: "a4",
    courseId: "math-sec-2",
    title: "Implement Gradient Descent for Linear Regression",
    topic: "Linear Regression · Gradient Descent",
    prompt:
      "Write a function that fits a single-variable linear regression model using batch gradient descent. Given feature vector x, target vector y, an initial theta, a learning rate alpha, and a number of iterations, return the learned parameters. Your function should update theta on every iteration using the gradient of the mean-squared-error cost function.",
    status: "in_progress",
    dueDate: "2026-09-24",
  },
  {
    id: "a3",
    courseId: "math-sec-2",
    title: "Assignment 3 — Cost Function Derivation",
    topic: "Linear Regression",
    prompt: "Derive the mean-squared-error cost function and its gradient with respect to theta.",
    status: "submitted",
    dueDate: "2026-09-17",
  },
  {
    id: "a2",
    courseId: "math-sec-2",
    title: "Assignment 2 — Vector Operations",
    topic: "Linear Algebra Refresher",
    prompt: "Implement dot product, matrix-vector multiplication, and normalization from scratch.",
    status: "verified",
    dueDate: "2026-09-10",
  },
  {
    id: "a1",
    courseId: "math-sec-2",
    title: "Assignment 1 — Setting Up the Environment",
    topic: "Tooling",
    prompt: "Set up your Python environment and submit a short reflection.",
    status: "verified",
    dueDate: "2026-09-03",
  },
]

export const chatHistory: ChatMessage[] = [
  {
    id: "c1",
    role: "coach",
    kind: "question",
    content: "I notice the loop body doesn't update theta yet. What should happen inside each iteration?",
  },
  {
    id: "c2",
    role: "student",
    content: "I think I need to compute the error, then subtract alpha times the gradient from theta.",
  },
  {
    id: "c3",
    role: "coach",
    kind: "question",
    content: 'Good instinct — what exactly is "the gradient" here, in terms of x, y, and theta?',
  },
  {
    id: "c4",
    role: "student",
    content: "The average of (prediction − y) times x, I believe.",
  },
]

export const studentRows: StudentRow[] = [
  { id: "st1", name: "Amina K.", taskSubmission: 88, socraticAiUsage: 23, externalAiUsage: 3, mastery: "Strong" },
  { id: "st2", name: "Youssef T.", taskSubmission: 82, socraticAiUsage: 9, externalAiUsage: 21, mastery: "Moderate" },
  { id: "st3", name: "Nourhan S.", taskSubmission: 94, socraticAiUsage: 40, externalAiUsage: 8, mastery: "Moderate" },
  { id: "st4", name: "Karim H.", taskSubmission: 61, socraticAiUsage: 31, externalAiUsage: 2, mastery: "Weak" },
  { id: "st5", name: "Laila M.", taskSubmission: 90, socraticAiUsage: 18, externalAiUsage: 12, mastery: "Moderate" },
]

export function getCourse(id: string, forRole: "student" | "teacher" = "student") {
  const list = forRole === "student" ? studentCourses : teacherCourses
  return list.find((c) => c.id === id)
}

export function getMaterialsForCourse(courseId: string) {
  return materials.filter((m) => m.courseId === courseId)
}

export function getAssignmentsForCourse(courseId: string) {
  return assignments.filter((a) => a.courseId === courseId)
}

export function getAssignment(id: string) {
  return assignments.find((a) => a.id === id)
}

export function getMaterial(id: string) {
  return materials.find((m) => m.id === id)
}
