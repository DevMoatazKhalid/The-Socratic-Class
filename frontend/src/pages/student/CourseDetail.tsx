import { useParams } from "react-router-dom"
import { AppShell } from "@/components/layout/AppShell"
import { AssignmentRow, MaterialRow } from "@/components/socratiq/ListRow"
import { EmptyState, ErrorState } from "@/components/ui/States"
import { currentStudent, studentCourses, getCourse, getAssignmentsForCourse, getMaterialsForCourse } from "@/data/mockData"

export default function StudentCourseDetail() {
  const { courseId = "" } = useParams()
  const course = getCourse(courseId, "student")
  const assignmentList = getAssignmentsForCourse(courseId)
  const materialList = getMaterialsForCourse(courseId)

  if (!course) {
    return (
      <AppShell role="student" userName={currentStudent.name} userEmail={currentStudent.email} courses={studentCourses} crumbs={[{ label: "Courses", to: "/student/courses" }, { label: "Not found" }]}>
        <ErrorState title="Course not found" description="This course may have been removed or the link is incorrect." />
      </AppShell>
    )
  }

  return (
    <AppShell
      role="student"
      userName={currentStudent.name}
      userEmail={currentStudent.email}
      courses={studentCourses}
      crumbs={[{ label: "Courses", to: "/student/courses" }, { label: course.name }]}
      search=""
    >
      <h1 className="text-xl font-semibold text-[var(--color-ink)]">{course.name}</h1>
      <p className="mt-1 text-sm text-[var(--color-ink-soft)]">{course.description} · {course.teacher}</p>

      <h2 className="mb-3 mt-7 text-sm font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">Assignments</h2>
      {assignmentList.length === 0 ? (
        <EmptyState title="No assignments yet" description="Your instructor hasn't posted an assignment for this course." />
      ) : (
        <div className="space-y-2">
          {assignmentList.map((a) => (
            <AssignmentRow key={a.id} to={`/student/courses/${course.id}/assignments/${a.id}`} title={a.title} topic={a.topic} status={a.status} />
          ))}
        </div>
      )}

      <h2 className="mb-3 mt-8 text-sm font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">Materials</h2>
      {materialList.length === 0 ? (
        <EmptyState title="No materials yet" description="Course readings and slides will show up here once posted." />
      ) : (
        <div className="space-y-2">
          {materialList.map((m) => (
            <MaterialRow key={m.id} to={`/student/courses/${course.id}/materials/${m.id}`} title={m.title} summary={m.summary} />
          ))}
        </div>
      )}
    </AppShell>
  )
}
