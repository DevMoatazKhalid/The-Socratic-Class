import { Routes, Route, Navigate } from "react-router-dom"
import Landing from "@/pages/Landing"
import ChooseSignup from "@/pages/auth/ChooseSignup"
import SignupStudent from "@/pages/auth/SignupStudent"
import SignupTeacher from "@/pages/auth/SignupTeacher"
import Login from "@/pages/auth/Login"
import Settings from "@/pages/Settings"
import NotFound from "@/pages/NotFound"

import StudentHome from "@/pages/student/Home"
import StudentCourses from "@/pages/student/Courses"
import StudentCourseDetail from "@/pages/student/CourseDetail"
import StudentMaterialDetail from "@/pages/student/MaterialDetail"
import StudentAssignmentDetail from "@/pages/student/AssignmentDetail"
import AiCoach from "@/pages/student/AiCoach"
import Verification from "@/pages/student/Verification"

import TeacherDashboard from "@/pages/teacher/Dashboard"
import TeacherCourses from "@/pages/teacher/Courses"
import TeacherCourseDetail from "@/pages/teacher/CourseDetail"
import TeacherAssignmentDetail from "@/pages/teacher/AssignmentDetail"
import TeacherMaterialDetail from "@/pages/teacher/MaterialDetail"

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/signup" element={<ChooseSignup />} />
      <Route path="/signup/student" element={<SignupStudent />} />
      <Route path="/signup/teacher" element={<SignupTeacher />} />
      <Route path="/login" element={<Login />} />

      <Route path="/student" element={<StudentHome />} />
      <Route path="/student/courses" element={<StudentCourses />} />
      <Route path="/student/courses/:courseId" element={<StudentCourseDetail />} />
      <Route path="/student/courses/:courseId/materials/:materialId" element={<StudentMaterialDetail />} />
      <Route path="/student/courses/:courseId/assignments/:assignmentId" element={<StudentAssignmentDetail />} />
      <Route path="/student/courses/:courseId/assignments/:assignmentId/coach" element={<AiCoach />} />
      <Route path="/student/courses/:courseId/assignments/:assignmentId/verify" element={<Verification />} />
      <Route path="/student/settings" element={<Settings role="student" />} />

      <Route path="/teacher" element={<TeacherDashboard />} />
      <Route path="/teacher/courses" element={<TeacherCourses />} />
      <Route path="/teacher/courses/:courseId" element={<TeacherCourseDetail />} />
      <Route path="/teacher/courses/:courseId/assignments/:assignmentId" element={<TeacherAssignmentDetail />} />
      <Route path="/teacher/courses/:courseId/materials/:materialId" element={<TeacherMaterialDetail />} />
      <Route path="/teacher/settings" element={<Settings role="teacher" />} />

      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
