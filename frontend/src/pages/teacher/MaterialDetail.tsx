import { useParams } from "react-router-dom"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { ErrorState } from "@/components/ui/States"
import { currentTeacher, teacherCourses, getCourse, getMaterial } from "@/data/mockData"

export default function TeacherMaterialDetail() {
  const { courseId = "", materialId = "" } = useParams()
  const course = getCourse(courseId, "teacher")
  const material = getMaterial(materialId)

  if (!course || !material) {
    return (
      <AppShell role="teacher" userName={currentTeacher.name} userEmail={currentTeacher.email} courses={teacherCourses} crumbs={[{ label: "Courses", to: "/teacher/courses" }, { label: "Not found" }]}>
        <ErrorState title="Material not found" description="This item may have been removed or the link is incorrect." />
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
        { label: material.title },
      ]}
    >
      <Card className="max-w-2xl">
        <CardContent>
          <h1 className="text-lg font-semibold text-[var(--color-ink)]">{material.title}</h1>
          <p className="mt-4 text-[var(--color-ink-soft)]">{material.summary}</p>
          <div className="mt-6 flex gap-2">
            <Button variant="outline">Replace file</Button>
            <Button variant="danger">Remove</Button>
          </div>
        </CardContent>
      </Card>
    </AppShell>
  )
}
