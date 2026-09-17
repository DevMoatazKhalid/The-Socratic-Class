import { useParams } from "react-router-dom"
import { AppShell } from "@/components/layout/AppShell"
import { AssignmentRow, MaterialRow } from "@/components/socratiq/ListRow"
import { Button } from "@/components/ui/Button"
import { EmptyState, ErrorState } from "@/components/ui/States"
import { Plus } from "lucide-react"
import { currentTeacher, teacherCourses, getCourse, getAssignmentsForCourse, getMaterialsForCourse } from "@/data/mockData"

export default function TeacherCourseDetail() {
  const { courseId = "" } = useParams()
  const course = getCourse(courseId, "teacher")
  const assignmentList = getAssignmentsForCourse(courseId)
  const materialList = getMaterialsForCourse(courseId)

  if (!course) {
    return (
      <AppShell role="teacher" userName={currentTeacher.name} userEmail={currentTeacher.email} courses={teacherCourses} crumbs={[{ label: "Courses", to: "/teacher/courses" }, { label: "Not found" }]}>
        <ErrorState title="Course not found" description="This course may have been removed or the link is incorrect." />
      </AppShell>
    )
  }

  return (
    <AppShell
      role="teacher"
      userName={currentTeacher.name}
      userEmail={currentTeacher.email}
      courses={teacherCourses}
      crumbs={[{ label: "Courses", to: "/teacher/courses" }, { label: course.name }]}
      search=""
    >
      <h1 className="text-xl font-semibold text-[var(--color-ink)]">{course.name}</h1>
      <p className="mt-1 text-sm text-[var(--color-ink-soft)]">{course.studentCount} students · {course.status}</p>

      <h2 className="mb-3 mt-7 text-sm font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">Assignments</h2>
      {assignmentList.length === 0 ? (
        <EmptyState title="No assignments yet" description="Create an assignment so students have something to work on." />
      ) : (
        <div className="space-y-2">
          {assignmentList.map((a) => (
            <AssignmentRow key={a.id} to={`/teacher/courses/${course.id}/assignments/${a.id}`} title={a.title} topic={a.topic} status={a.status} />
          ))}
        </div>
      )}

      <h2 className="mb-3 mt-8 text-sm font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">Materials</h2>
      {materialList.length === 0 ? (
        <EmptyState title="No materials yet" description="Upload a reading or slide deck for this course." />
      ) : (
        <div className="space-y-2">
          {materialList.map((m) => (
            <MaterialRow key={m.id} to={`/teacher/courses/${course.id}/materials/${m.id}`} title={m.title} summary={m.summary} />
          ))}
        </div>
      )}

      <Button variant="secondary" className="mt-5 gap-1.5">
        <Plus className="h-4 w-4" /> Add content
      </Button>
    </AppShell>
  )
}
