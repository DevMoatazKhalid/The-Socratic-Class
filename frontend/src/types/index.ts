export type Role = "student" | "teacher"

export interface User {
  id: string
  name: string
  email: string
  role: Role
}

export interface Course {
  id: string
  code: string
  name: string
  description: string
  teacher: string
  status: "Active" | "Archived"
  color: "plum" | "slate" | "teal" | "clay"
  materialCount: number
  assignmentCount: number
  studentCount?: number
}

export interface Material {
  id: string
  courseId: string
  title: string
  summary: string
  kind: "reading" | "slides" | "video" | "dataset"
}

export type AssignmentStatus = "not_started" | "in_progress" | "submitted" | "verified"

export interface Assignment {
  id: string
  courseId: string
  title: string
  topic: string
  prompt: string
  status: AssignmentStatus
  dueDate: string
}

export interface ChatMessage {
  id: string
  role: "coach" | "student"
  content: string
  kind?: "hint" | "question" | "explanation"
}

export interface StudentRow {
  id: string
  name: string
  taskSubmission: number
  socraticAiUsage: number
  externalAiUsage: number
  mastery: "Strong" | "Moderate" | "Weak"
}
