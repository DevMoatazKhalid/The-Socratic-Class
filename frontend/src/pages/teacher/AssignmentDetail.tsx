import { useParams } from "react-router-dom"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent } from "@/components/ui/Card"
import { Badge } from "@/components/ui/Badge"
import { ErrorState } from "@/components/ui/States"
import { currentTeacher, teacherCourses, getCourse, getAssignment } from "@/data/mockData"

export default function TeacherAssignmentDetail() {
  const { courseId = "", assignmentId = "" } = useParams()
  const course = getCourse(courseId, "teacher")
  const assignment = getAssignment(assignmentId)

  if (!course || !assignment) {
    return (
      <AppShell role="teacher" userName={currentTeacher.name} userEmail={currentTeacher.email} courses={teacherCourses} crumbs={[{ label: "Courses", to: "/teacher/courses" }, { label: "Not found" }]}>
        <ErrorState title="Assignment not found" description="This assignment may have been removed or the link is incorrect." />
      </AppShell>
    )
  }

  return (
    <AppShell
      role="teacher"
      userName={currentTeacher.name}
      userEmail={currentTeacher.email}
      courses={teacherCourses}
      crumbs={[
        { label: "Courses", to: "/teacher/courses" },
        { label: course.name, to: `/teacher/courses/${course.id}` },
        { label: assignment.title },
      ]}
    >
      <Card className="max-w-2xl">
        <CardContent>
          <div className="flex items-start justify-between gap-3">
            <h1 className="text-lg font-semibold text-[var(--color-ink)]">{assignment.title}</h1>
            <Badge tone="teal">{assignment.topic}</Badge>
          </div>
          <p className="mt-4 text-[var(--color-ink-soft)]">{assignment.prompt}</p>
          <p className="mt-6 text-sm text-[var(--color-ink-faint)]">
            Submission analytics and learning-evidence review for this assignment will appear here once students submit.
          </p>
        </CardContent>
      </Card>
    </AppShell>
  )
}
