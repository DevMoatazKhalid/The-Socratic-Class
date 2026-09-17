import { AppShell } from "@/components/layout/AppShell"
import { CourseCard, JoinCourseCard } from "@/components/socratiq/CourseCard"
import { currentTeacher, teacherCourses } from "@/data/mockData"

export default function TeacherCourses() {
  return (
    <AppShell
      role="teacher"
      userName={currentTeacher.name}
      userEmail={currentTeacher.email}
      courses={teacherCourses}
      crumbs={[{ label: "Courses" }]}
      search=""
    >
      <h1 className="text-xl font-semibold text-[var(--color-ink)]">Your courses</h1>
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {teacherCourses.map((c) => (
          <div key={c.id} className="flex flex-col">
            <CourseCard course={c} to={`/teacher/courses/${c.id}`} />
            <p className="mt-2 px-1 text-xs text-[var(--color-ink-faint)]">{c.studentCount} students</p>
          </div>
        ))}
        <JoinCourseCard label="Add course" />
      </div>
    </AppShell>
  )
}
