import { AppShell } from "@/components/layout/AppShell"
import { CourseCard, JoinCourseCard } from "@/components/socratiq/CourseCard"
import { currentStudent, studentCourses } from "@/data/mockData"

export default function StudentHome() {
  return (
    <AppShell
      role="student"
      userName={currentStudent.name}
      userEmail={currentStudent.email}
      courses={studentCourses}
      crumbs={[{ label: "Home" }]}
      search=""
    >
      <h1 className="text-xl font-semibold text-[var(--color-ink)]">
        Welcome back, {currentStudent.name.split(" ")[0]}
      </h1>
      <p className="mt-1 text-sm text-[var(--color-ink-soft)]">Pick up where you left off, or explore a course.</p>

      <h2 className="mb-3 mt-8 text-sm font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
        Your courses
      </h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {studentCourses.map((c) => (
          <CourseCard key={c.id} course={c} to={`/student/courses/${c.id}`} />
        ))}
        <JoinCourseCard />
      </div>
    </AppShell>
  )
}
