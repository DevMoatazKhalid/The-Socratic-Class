import { useParams } from "react-router-dom"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { ErrorState } from "@/components/ui/States"
import { currentStudent, studentCourses, getCourse, getMaterial } from "@/data/mockData"

export default function StudentMaterialDetail() {
  const { courseId = "", materialId = "" } = useParams()
  const course = getCourse(courseId, "student")
  const material = getMaterial(materialId)

  if (!course || !material) {
    return (
      <AppShell role="student" userName={currentStudent.name} userEmail={currentStudent.email} courses={studentCourses} crumbs={[{ label: "Courses", to: "/student/courses" }, { label: "Not found" }]}>
        <ErrorState title="Material not found" description="This item may have been removed or the link is incorrect." />
      </AppShell>
    )
  }

  return (
    <AppShell
      role="student"
      userName={currentStudent.name}
      userEmail={currentStudent.email}
      courses={studentCourses}
      crumbs={[
        { label: "Courses", to: "/student/courses" },
        { label: course.name, to: `/student/courses/${course.id}` },
        { label: material.title },
      ]}
    >
      <Card className="max-w-2xl">
        <CardContent>
          <h1 className="text-lg font-semibold text-[var(--color-ink)]">{material.title}</h1>
          <p className="mt-1 text-sm text-[var(--color-ink-faint)]">{course.name}</p>
          <p className="mt-4 text-[var(--color-ink-soft)]">{material.summary}</p>
          <div className="mt-6 flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => history.back()}>
              Go back
            </Button>
            <Button variant="secondary">Preview</Button>
            <Button>Download</Button>
          </div>
        </CardContent>
      </Card>
    </AppShell>
  )
}
